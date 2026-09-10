"""Routing one key namespace across more than one backing store.

A mount table maps a key prefix to a :class:`~outrage.store.Store`. The longest
prefix matching a key owns it, exactly the way a filesystem mount table works,
and the root mount owns everything no other mount claims -- so every key
resolves, and the single store case is just a table with one entry.

Two translations happen at the boundary and nothing else does:

* **inward**, a key loses the prefix of the mount that owns it, so the mounted
  store is asked about a key in its own namespace and never learns where it was
  mounted. That is what makes a store relocatable: the same database answers
  the same way at ``ref`` as at ``lib/ref``.
* **outward**, every key a mounted store returns regains that prefix, so a
  caller only ever sees the one namespace.

The mount point itself is the inner store's **root**, which is why the root had
to become a valid key first. Without it a store mounted at ``ref`` would have
no way to answer for the
document or the title *at* ``ref``, and a survey could not say what the mount
is.

A mount may be **read-only**, which is where the whole feature was pointed: a
shared read-mostly reference base beside a local read-write store. The refusal
lives here, in the routing, and is checked before the store is called at all --
``Store`` knows nothing about it, and the database file is not opened any
differently. So this refuses writes *through this server*; it does not make the
file read-only to anything else.

A table is **immutable**: it has no mutable state after ``__init__``, and a
change is a *new* table built by :meth:`MountedStore.remounted` rather than an
edit to this one. That is what makes a mount table changeable on a running
server at all -- a call holds the table it started with for its whole duration,
so no traversal can see two -- and everything about serving one, swapping it and
owning the stores that fall out of it lives in :mod:`outrage.remount`, not here.
Some questions are deliberately still open, chief among them where a write to a
new key goes.
"""

from __future__ import annotations

import contextlib
import dataclasses
import os
from collections.abc import Callable, Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from . import keys
from . import store as store_module
from .errors import OutrageError
from .eventlog import EventLog
from .store import (
    _BOUNDS,
    DEFAULT_BULK_MAX_CHARS,
    DEFAULT_MAX_CHARS,
    EVERYTHING,
    UNBOUNDED,
    BoundedSubtree,
    Entry,
    Excerpt,
    KeyNotFoundError,
    KeyRange,
    MissingMeta,
    Page,
    ReadOnlyStoreError,
    Store,
    SubtreeTotals,
    _cut,
    _document_change,
    _later,
    _metadata_change,
    _with_descendants,
    _within,
    check_unchanged,
    entry_kind,
    store_file,
)

#: Separates a mount point from its store file in a ``--mount`` argument.
#: ``=`` rather than ``:`` because a Windows path holds a colon and no key can
#: hold an ``=`` any less than it can hold anything else -- but a key with one
#: in it is vanishingly rare, and a drive letter is not.
SPEC_DELIMITER = "="

#: Separates the store file from an option, and one option from the next:
#: ``KEY=FILE,NAME=VALUE``. ``mount(8)``'s own ``-o`` vocabulary, and chosen
#: for what it does to *precedence*: an option written inside the value keeps
#: one mount one option occurrence, so a later ``--mount`` at that point
#: replaces the entry and everything said about it, and
#: ``outrage.mountfile._overridden`` needs no sentence about half-overridden
#: mounts. A second flag keyed by mount point would have needed one.
#:
#: The price is a comma, which a store file may no longer hold: it is refused
#: by :func:`parse_options` on the way in and by :func:`unparse` on the way
#: out, rather than being quietly the first option's name.
OPTION_DELIMITER = ","

#: Separates an option's name from its value, and the same character the mount
#: point uses for the same reason. ``type=files`` is one option and there is
#: currently one option; the grammar is what is general, not the list.
OPTION_ASSIGNMENT = "="

#: The option that says which backend keeps this store, overriding what the
#: file name implies. The value is a backend's own name --
#: :attr:`outrage.store.FileStore.backend_name`, the word a report already uses
#: -- so ``type=files`` names :class:`outrage.store_files.FilesystemStore` and
#: is not a second vocabulary for the same three classes.
#:
#: **Why the option exists at all.** Which backend keeps a store follows from
#: the store file's extension, and a directory of files has no extension to
#: read: without a way to say so, a tree is not mountable and a mount table
#: cannot describe one. See :data:`outrage.store._BY_EXTENSION`.
TYPE_OPTION = "type"

#: The option that says how a tree's file names line up with keys, for the one
#: backend that keeps its store as a directory. The value is a mode from
#: :data:`outrage.bulk.EXTENSION_MODES` -- ``strip``, which is the mapping this
#: package writes, or ``keep``, which makes a file name and a key segment the
#: same string.
#:
#: **Why a mount says it rather than the tree.** How to read a corpus is a
#: property of the corpus and there is nowhere in a plain directory to record
#: one: a marker file would be a file in the tree that is not a document, in
#: the one backend whose contents somebody else is expected to be editing. So
#: it is said where the store is named, beside the ``type`` that had to be said
#: for the same kind of reason.
#:
#: A backend that keeps its store in a file has no such question, and refuses
#: this rather than ignoring it -- :meth:`outrage.store.FileStore.in_directory`.
EXTENSIONS_OPTION = "extensions"

#: Every option a spec may carry. Anything else is refused rather than ignored,
#: which is the rule ``mounts.toml`` already follows for a field it does not
#: know: a mount that quietly did something other than what it says is the
#: failure a mount configuration is least able to notice.
OPTIONS = (TYPE_OPTION, EXTENSIONS_OPTION)

#: The ``kind`` a listing reports for a key that is a mount point. A fourth
#: kind beside 'document', 'metadata' and 'implicit', because a mount point is
#: none of the three: it may hold content, and it always has a store behind it.
#: A caller that does not know the word still learns that the key exists, which
#: is the part that matters for navigating to it.
MOUNT_KIND = "mount"

#: The ``kind`` for a mount point whose store refuses writes. A separate kind
#: rather than a ``read_only`` field on :class:`~outrage.store.Entry`, because a
#: field would appear on *every* entry in every listing as a null, and a
#: result grows a field only when there is something to say. The kind is
#: already the field that says what
#: a key is, only one key in a listing is a mount at all, and the words carry
#: their own meaning to a caller who has never read any of this.
#:
#: This is also the only place the fact is announced. The instructions do not
#: mention mounts -- see ``instructions`` on why a mounted store's readme is
#: not carried -- so, exactly like the existence of a mount, being read-only
#: costs nothing until somebody looks at the listing.
READ_ONLY_MOUNT_KIND = "read-only mount"

#: What a report calls the mount that answers for every key no other mount
#: claims. Not a ``kind`` any listing uses -- the root is never an entry in one,
#: since it is the level everything else is listed *below* -- so it is spelled
#: here rather than on :attr:`Mount.kind`, and used by the reports that put the
#: root in a table beside the mounts.
ROOT_KIND = "root"


class MountError(OutrageError, ValueError):
    """Raised when a mount table cannot be built as described."""


class ReadOnlyMountError(OutrageError, PermissionError):
    """Raised when a write is routed to a mount that was mounted read-only.

    Separate from :class:`MountError`, which is about a table that cannot be
    *built*: this one is about a request, and the table it names is working as
    configured.

    ``PermissionError`` is the builtin it keeps, following the rule in
    ``errors.py`` that each subclass keeps the builtin it already inherited --
    a caller that catches ``OSError`` around a write goes on working.
    """


@dataclass(frozen=True, slots=True)
class Mount:
    """One store, and the prefix it answers for."""

    prefix: str
    """The key this store is mounted at, normalised. The root mount's is ``""``."""

    store: Store

    read_only: bool = False
    """Whether this server refuses writes routed here.

    Defaults to False so that every existing construction of a ``Mount`` means
    what it meant before, and so the single store case cannot become read-only
    by accident.
    """

    @property
    def kind(self) -> str:
        """What a listing calls this mount point."""
        return READ_ONLY_MOUNT_KIND if self.read_only else MOUNT_KIND

    @property
    def name(self) -> str:
        """The mount point as written for a person to read; the root is ``/``."""
        return keys.displayed(self.prefix)

    @property
    def is_root(self) -> bool:
        return self.prefix == keys.ROOT

    def inner(self, key: str) -> str | None:
        """``key`` as this store names it, or None if this mount does not hold it."""
        return keys.strip_prefix(self.prefix, key)

    def outer(self, key: str) -> str:
        """``key`` as the whole namespace names it. Total, by construction.

        A mount point and a key inside a store are each bounded at
        ``keys.MAX_SEGMENTS``, and the joined namespace allows twice that, so
        the sum always parses. That bound is what abolishes the case rather than
        reporting it: without it a listing needs a path for dropping the keys
        that will not fit.

        The check stays as an assertion, because what it guards is an
        arithmetic relationship between two constants and a store's contents,
        and a store written by an earlier outrage can still hold a key too deep
        for it. Raising names the mount and the key; returning a
        string that will not parse would fail one layer away, which is the
        failure this project keeps finding. ``outrage check`` reports such keys
        before anything mounts the store.
        """
        name = keys.with_prefix(self.prefix, key)
        if not keys.fits(name):
            raise MountError("mount-key-too-deep", key=key, mount=self.prefix)
        return name


@dataclass(frozen=True, slots=True)
class Segment:
    """One stretch of one store, as part of reading across a mount boundary.

    A subtree spanning mounts is not one query and cannot be: the rows live in
    different databases. It is a *sequence* of these, in key order, each naming
    the store to ask, which part of that store's hierarchy is in scope, and
    which stretch of its order. Concatenate their answers and the totals add,
    which is what lets a traversal answer as though the subtree were one thing.

    ``subtree`` and ``key_range`` are both in the mounted store's **own**
    namespace: a mounted store never learns where it was mounted, so the
    translation happens here and the results are put back by ``mount.outer``.
    """

    mount: Mount
    subtree: BoundedSubtree
    key_range: KeyRange

    @property
    def store(self) -> Store:
        """The store to ask for this segment, which is not necessarily the one
        the caller's key named.

        A segment is a stretch of *one* store, and a traversal crossing a mount
        boundary produces several. ``subtree`` and ``key_range`` beside it are
        in this store's own namespace, never the outer one.
        """
        return self.mount.store

    def resume_from(self, after: str | None) -> tuple[str | None, bool]:
        """This segment's own cursor, and whether the page already passed it.

        A cursor names a key in the one namespace, so it means something
        different to each store a traversal crosses, and recomputing it at
        every boundary is the only way it keeps meaning the same *place*.
        Three answers, and all three are needed:

        * a key **inside this segment's store** -- the cursor falls here, so
          the store resumes from it;
        * ``None`` with ``False`` -- the cursor lies before this segment, which
          therefore starts at its own beginning;
        * ``None`` with ``True`` -- this segment lies entirely **behind** the
          cursor, so an earlier page has already returned it.

        The last is what a single store never needed: within one store a
        cursor and a range are ANDed and a stretch before the cursor comes back
        empty on its own. Across stores the cursor cannot even be spelled in
        the namespace of a store it does not name, so being behind it has to be
        an answer rather than an empty result. Such a segment is still
        *counted* -- totals describe the whole collection and have never
        depended on where the reader had got to.
        """
        if after is None:
            return None, False
        inner = self.mount.inner(after)
        if inner is not None:
            return inner, False
        # Not a key this store can name, so the whole of it lies on one side of
        # the cursor: a subtree occupies one contiguous stretch of the order,
        # and the cursor is not in it.
        position = keys.sort_form(keys.parse(after, max_segments=keys.MAX_JOINED_SEGMENTS).key)
        return None, position >= keys.sort_subtree_end(self.mount.prefix)


@dataclass(frozen=True, slots=True)
class Resolved:
    """Which store owns a key, and what that store calls it."""

    mount: Mount
    key: str
    """The key inside the mounted store."""

    outer: str
    """The key as it was asked for, normalised."""

    @property
    def store(self) -> Store:
        """The store that owns the key: the longest mount prefix matching it.

        Not "the root store unless something is mounted" -- the root is itself
        a mount, so a lone store is a table of one and takes the same path. Ask
        this store for :attr:`key`, which is the inner spelling; asking it for
        the key the caller passed would be asking for a key it has never heard
        of.
        """
        return self.mount.store

    @property
    def read_only(self) -> bool:
        """Whether the mount that owns the key refuses writes."""
        return self.mount.read_only

    def writable(self, action: str = "write") -> Resolved:
        """This, or raise if the mount that owns the key refuses writes.

        Returns itself so a caller reads as one expression and cannot resolve a
        key, forget to check it, and write anyway -- the failure this guards is
        precisely a refusal that arrives too late to matter, so the shape that
        makes forgetting awkward is worth the small strangeness of a method
        that returns its own receiver.

        ``action`` is the verb for the message, because "cannot write" reads
        wrongly for a delete and a caller reading a refusal should not have to
        translate it back into what they asked for.

        The message names the mount rather than only the key, because the key
        looks perfectly ordinary and the reason it was refused is somewhere the
        caller cannot see: the command line the server was started with.

        **Which of the two refusals this is matters, and the store is what
        knows.** A mount refuses because of how it was started, and the message
        says so and tells the caller which flag to drop. A *backend* refuses
        because a parquet file is not updated in place, and no flag would make
        the same call succeed -- so the mount's advice would be wrong, and
        wrong in the way that costs someone a restart to find out. The two are
        both real and they compose: a SQLite store is read-write or read-only
        according to how it was mounted, and a parquet store is read-only
        either way. Found by mounting one and writing to it, which is what a
        live test is for.
        """
        if not self.read_only:
            return self
        if not type(self.mount.store).writable:
            raise ReadOnlyStoreError(
                "store-read-only",
                key=self.outer,
                path=str(self.mount.store.path),
                action=action,
            )
        raise ReadOnlyMountError(
            "mount-read-only", key=self.outer, mount=self.mount.prefix, action=action
        )


# -- a range, and a page, on the far side of a boundary ---------------------


def _inward_range(mount: Mount, key_range: KeyRange) -> KeyRange | None:
    """``key_range`` as ``mount``'s store spells it, or None if it excludes it.

    None is an answer a single store never needs. Within one store a bound
    outside the selection simply selects nothing; here the store cannot be
    asked at all, because a key outside its namespace has no name it would
    recognise and asking with the bound dropped would return everything.

    Three answers per bound, the same shape :meth:`Segment.resume_from` gives a
    cursor. The bound falls **inside** this store's stretch, and is translated
    and kept; it falls in front of the whole stretch, and constrains nothing
    here, so it is dropped; or it falls behind it, and there is nothing here to
    ask about. Which of the three is decided by comparing the bound's cut with
    the stretch, and the stretch is exactly ``sort_form(prefix)`` up to
    ``sort_subtree_end(prefix)`` -- a subtree is a contiguous run of the order,
    which is the same fact ``store_parquet._subtree_range`` rests on.

    A bound that survives that comparison names a key at or below the mount
    point, by construction: its cut lies inside the mount's stretch, and the
    only keys whose cuts do are the mount point and its descendants. So
    :meth:`Mount.inner` is total here and never returns None.
    """
    if mount.is_root:
        return key_range
    low = keys.sort_form(mount.prefix)
    high = keys.sort_subtree_end(mount.prefix)
    inward: dict[str, str] = {}
    for name, is_lower, inclusive, at in _BOUNDS:
        named = getattr(key_range, name)
        if named is None:
            continue
        key = keys.parse(named, max_segments=keys.MAX_JOINED_SEGMENTS).key
        cut = _cut(key, at)
        if is_lower:
            if cut >= high:
                return None
            if cut < low or (inclusive and cut == low):
                continue
        else:
            if cut < low or (not inclusive and cut == low):
                return None
            if cut >= high:
                continue
        inner = mount.inner(key)
        assert inner is not None  # noqa: S101 - see the docstring: total by construction
        inward[name] = inner
    return KeyRange(**inward)


def _in_range(key: str, key_range: KeyRange) -> bool:
    """Whether ``key`` falls inside ``key_range``.

    A range is cuts in the order and nothing else, so anything holding a key can
    decide this for itself. Here because a *level* takes no range -- reading one
    is not reading a stretch -- and yet a table counting a stretch that crosses a
    boundary has to ask a level for the rows that sit at a key, then say which of
    them the range keeps. See :func:`_rows_at`.
    """
    position = keys.sort_form(keys.parse(key, max_segments=keys.MAX_JOINED_SEGMENTS).key)
    return _within(key_range)(position)


def _intersect(first: KeyRange, second: KeyRange) -> KeyRange:
    """The stretch both ranges name.

    Every bound ANDs with every other, so two ranges intersect bound by bound:
    where only one names a cut it survives untouched, and where both do the
    tighter one wins. Comparable because the two cuts of a given bound are
    taken at the same place in the order -- which is what :data:`_BOUNDS`
    records.
    """
    both: dict[str, str] = {}
    for name, is_lower, _inclusive, at in _BOUNDS:
        one, two = getattr(first, name), getattr(second, name)
        if one is None or two is None:
            chosen = two if one is None else one
        else:
            pick = max if is_lower else min
            chosen = pick((one, two), key=lambda key: _cut(key, at))
        if chosen is not None:
            both[name] = chosen
    return KeyRange(**both)


#: The two codes a store raises when it holds nothing at a key. Both count what
#: lies beneath it, and a store can only count as far as its own edge, so both
#: have to be asked again of the table. See
#: :meth:`MountedStore._nothing_there`.
_NOTHING_THERE = ("key-not-found", "key-is-a-container")


#: The details of an error that name a key, and so have to regain a mount's
#: prefix on the way out. Every other detail is a fact about the store rather
#: than a name in the namespace -- a path, a count, a backend -- and means the
#: same thing on both sides of the boundary.
_NAMED_DETAILS = ("key", "parent", "cursor")


@contextlib.contextmanager
def _renamed(mount: Mount) -> Iterator[None]:
    """Re-raise an error from ``mount``'s store naming its keys from outside.

    A store refuses a key by the name it knows, which is the name with the
    mount's prefix taken off -- so a failed read of ``ref/python/nope`` reported
    ``'python/nope'``, a key in no namespace anybody can pass back. That was a
    live defect, and fixing it here rather than at the MCP boundary fixes it for
    every front end at once -- including the command line, which has no mount
    table of its own to fix it with.

    Only *which* key, never how it is spelled: the error still carries a code
    and facts, and :mod:`outrage.messages` and the front end still decide the
    sentence. That is the rule this must not break.
    """
    if mount.is_root:
        # Nothing to add, and re-raising an identical error would only lose the
        # original traceback.
        yield
        return
    try:
        yield
    except OutrageError as exc:
        named = {
            detail: (
                mount.outer(value) if detail in _NAMED_DETAILS and isinstance(value, str) else value
            )
            for detail, value in exc.details.items()
        }
        if named == dict(exc.details):
            raise
        raise type(exc)(exc.code, **named) from exc


def _inward_cursor(found: Resolved, after: str | None) -> str | None:
    """A caller's cursor as the answering store names it.

    A cursor is a key, so it crosses the boundary the same way every other key
    does. One that names nothing under the mount being read is refused rather
    than dropped: silently ignoring it would restart the collection from the
    beginning, and a caller paging a large listing would loop over the first
    page forever without anything ever reporting an error.
    """
    if after is None:
        return None
    inner = found.mount.inner(after)
    if inner is None:
        raise keys.InvalidKeyError(
            "cursor-outside-subtree", cursor=after, mount=found.mount.prefix, key=found.outer
        )
    return inner


def _outward_items[T](found: Resolved, items: list[T]) -> list[T]:
    """``items`` renamed into the whole namespace.

    Total, by the bound: a mount point and a key inside a store are each capped
    at ``keys.MAX_SEGMENTS`` and the joined namespace allows twice that, so
    every key a mounted store returns has a name here. That is what spares every
    listing a ``dropped`` field and a note to explain it.
    """
    return [
        dataclasses.replace(item, key=found.mount.outer(item.key))  # type: ignore[arg-type]
        for item in items
    ]


def _outward_keys(found: Resolved, names: list[str]) -> list[str]:
    """:func:`_outward_items` for a plain list of keys."""
    return [found.mount.outer(name) for name in names]


def _document_row_at(store: Store, key: str, key_range: KeyRange) -> int:
    """The one row sitting *at* ``key``: its document, if it holds one.

    Split out of :func:`_rows_at` because a count taken with ``whole_subtree``
    already holds the metadata half of that answer, and adding the whole of it
    back would count the unit twice.
    """
    return 1 if store.exists(key) and _in_range(key, key_range) else 0


def _document_chars_at(store: Store, key: str) -> int:
    """How long the document at ``key`` is, without reading it.

    The root row of a mounted store is counted from outside by
    :func:`_document_row_at`, and a character total has to measure the same row.
    ``max_chars=1`` is what asks: an excerpt states the size of the whole it
    came from, so one character comes back and ``total`` is the answer -- the
    same trick :meth:`~outrage.store.Store.find_documents` uses to walk
    candidates without reading them.
    """
    return store.retrieve_document(key, max_chars=1).total


def _rows_at(store: Store, key: str, key_range: KeyRange) -> int:
    """The rows sitting *at* ``key``: its document, and its whole metadata subtree.

    :meth:`~outrage.store.Store.descendant_count` counts none of them -- it
    reports what a plain delete would keep, and a plain delete takes the key's
    metadata unit with it -- so a caller measuring the stretch from *outside*
    the store has to put them back.

    **Recursive, because a metadata namespace has a subtree.** ``a/!changelog``
    may hold notes, and those are inside the unit too; what a walk into one
    leaves out is exactly what ``descendant_count`` there does count, so the
    two add up to everything at and below it. Asked of a level rather than of a
    count because that is where metadata appears, and tested against the range
    here rather than by the store because a level takes no range: this named
    the keys, so it can say which of them the range keeps.

    By the segment, not by ``kind``: a metadata namespace holding only things
    below it is an *implicit* entry, and is no less part of the unit for it.
    """
    at = _document_row_at(store, key, key_range)
    for entry in store.list_keys(key).items:
        if entry_kind(entry.key) == "metadata":
            at += _rows_at(store, entry.key, key_range)
            at += store.descendant_count(entry.key, key_range=key_range)
    return at


def _newest_at(segment: Segment, *, whole_subtree: bool = False) -> str | None:
    """When the row sitting *at* a deeper mount's root was last written.

    The timestamp half of what :func:`_kept_below` puts back: a store mounted
    below the key answers about its own root as though it were the top of the
    world, and from outside that root is a key beneath the one asked about.

    Under ``whole_subtree`` the inner answer already covers the root's metadata
    unit, so only its document row is left; otherwise the unit is missing too,
    and :func:`outrage.store.check_unchanged`'s own helper is what reads it.
    A one-character read, as :func:`_document_row_at` is an ``exists``.
    """
    newest = _document_change(segment.store, segment.subtree.key, segment.key_range)
    if whole_subtree:
        return newest
    return _later(newest, _metadata_change(segment.store, segment.subtree.key, segment.key_range))


def _kept_below(segment: Segment, found: Resolved, *, whole_subtree: bool = False) -> int:
    """How many rows this segment holds below the key a count was asked about.

    Two shapes of the same question, because "below" is measured from the key
    and a segment is not always rooted at it. In the store answering for the
    key, below means strictly below -- the key's own row is not beneath itself,
    and neither is its metadata.

    In a store mounted further down, **everything it holds is below**, its own
    root row included, because that row is the mount point and the mount point
    is beneath the key. So the two rows a count taken from the inside leaves out
    -- the root document and the root's metadata -- are exactly the two a count
    taken from the outside has to include.

    Under ``whole_subtree`` the inner count already holds the root's metadata
    unit, so the root document row is the only one left to put back. Reaching
    for :func:`_rows_at` there would count that unit twice.
    """
    counted = segment.store.descendant_count(
        segment.subtree.key, key_range=segment.key_range, whole_subtree=whole_subtree
    )
    if segment.mount is found.mount:
        return counted
    if whole_subtree:
        return counted + _document_row_at(segment.store, segment.subtree.key, segment.key_range)
    return counted + _rows_at(segment.store, segment.subtree.key, segment.key_range)


def _named_items[T](segment: Segment, items: list[T]) -> list[T]:
    """``items`` from one segment, renamed into the whole namespace.

    Per segment rather than per call, which is the difference crossing makes:
    the items in one answer now come from several stores and each knows its
    keys by a different name. Total, since the key bounds were halved -- a
    mount point and a key inside a store are each capped at
    ``keys.MAX_SEGMENTS`` and the joined namespace allows twice that, so every
    key a mounted store returns has a name here.
    """
    return [
        dataclasses.replace(item, key=segment.mount.outer(item.key))  # type: ignore[arg-type]
        for item in items
    ]


def _named_keys(segment: Segment, names: list[str]) -> list[str]:
    """:func:`_named_items` for a plain list of keys."""
    return [segment.mount.outer(name) for name in names]


def _across_segments[T](
    segments: list[Segment],
    read: Callable[..., Page[T]],
    *,
    after: str | None,
    limit: int | None,
    max_total_chars: int | None,
    named: Callable[[Segment, list[T]], list[T]],
    key_of: Callable[[T], str],
    size_of: Callable[[T], int],
) -> Page[T]:
    """Read a subtree as a sequence of segments and answer as though it were one.

    The segments are disjoint and in key order, so the items concatenate and
    the totals add: each counts its own stretch, and the stretches tile the
    subtree. That is why the range bounds belong to the store's *selection*
    rather than to its page -- a count taken per segment is the only kind that
    can be summed.

    A segment is a stretch of one store, and consecutive ones may be stretches
    of **different** stores: the outer store's windows between the mounts below
    it, and the mounted stores' own subtrees, in the order the one namespace
    puts them. Nothing here knows which is which. That is the whole trick --
    crossing a mount boundary is the same operation as stepping over one, with
    a different list of segments.

    Every segment is read, even after the page is full, because ``total`` and
    ``total_chars`` describe the whole collection and not the part returned.
    Those later reads take ``limit=0``: they cost a count and fetch nothing,
    and a non-zero total in one of them is what says there is another page.

    The cursor is the last key **emitted**, in the emitting store's namespace;
    it is renamed before it leaves. A segment that stopped part way through
    gives one that already says so, since a store's cursor is its own last
    emitted key; what this must not do is take a cursor from a segment further
    on, or let a page that filled up exactly at a segment's edge report no
    cursor at all while a later segment still holds something. The second is
    why every segment is counted even after the page is full.

    Nothing is carried back about *which* segment covered what. A second
    question asked about the same page -- what a metadata survey could not
    see -- is bounded by naming the page's own stretch, ``after`` the cursor
    that opened it and ``before_inclusive`` the one it closed with, and letting
    that range cross the boundaries the same way every other one does.
    """
    items: list[T] = []
    total = 0
    total_chars = 0
    spent = 0
    cursor: str | None = None
    more = False
    stopped = False

    for segment in segments:
        # Recomputed here rather than carried inward once: the same cursor
        # names a different key in every store it crosses, and a segment
        # already behind it cannot name it at all.
        inward, behind = segment.resume_from(after)
        quiet = stopped or behind
        bounds: dict[str, Any] = {"key_range": segment.key_range, "cursor": inward}
        # A limit of None is no limit at all, and a segment past the end of a
        # page still has to be counted -- so the two cases are not the same
        # number and cannot be written as one expression.
        if quiet:
            bounds["limit"] = 0
        elif limit is not None:
            bounds["limit"] = limit - len(items)
        # Only when the caller has a character budget at all. A collection of
        # keys has none, and passing one it does not take would be a decision
        # about its shape taken here rather than by the tool that has it.
        if max_total_chars is not None:
            bounds["max_total_chars"] = max_total_chars - spent
        page = read(segment, **bounds)
        total += page.total
        total_chars += page.total_chars

        if quiet:
            # Counted, never emitted. Behind the cursor it was returned by an
            # earlier page; past the end of this one, anything it holds is
            # another page still to come.
            more = more or (stopped and page.total > 0)
            continue

        # Renamed as they arrive, so everything from here out -- the items, the
        # cursor, the fallback taken from the last item -- is in the one
        # namespace the caller sees, and no later step has to remember which
        # store a given item came from.
        items += named(segment, page.items)
        spent += sum(size_of(item) for item in page.items)
        if page.next_cursor is not None:
            cursor, more, stopped = segment.mount.outer(page.next_cursor), True, True
        else:
            stopped = (limit is not None and len(items) >= limit) or (
                max_total_chars is not None and spent >= max_total_chars
            )

    if more and cursor is None:
        cursor = key_of(items[-1]) if items else None
    return Page(
        items=items,
        returned=len(items),
        total=total,
        total_chars=total_chars,
        next_cursor=cursor,
    )


class MountedStore(Store):
    """Several stores behind one key namespace, presented as one store.

    A mount table *is* a :class:`~outrage.store.Store`: it answers every call in
    the same vocabulary, over keys spelled the way a caller spells them, and
    routes, steps over, crosses and merges underneath. That is what lets one
    live in front of the MCP server, the command line, or another table, with
    none of them holding routing code of their own -- and it is the reason
    ``Store`` was written as a vocabulary rather than as a database.

    What it is **not** is a file. It has no path, no format version of its own,
    nothing to back up and nothing to repair, and it says so rather than
    answering for its root mount: a check of a three-store table that silently
    reported one store would be worse than a refusal.
    """

    #: A table can be written when its root mount can, which
    #: :meth:`__init__` requires of every table -- so this is always true, and
    #: stated rather than inherited because a backend that forgets to say
    #: inherits ``True`` and would be reporting it by accident.
    writable = True

    #: What a refusal calls this when it has to name what it is talking to.
    #: Not an extension, because no file is kept here; see the class docstring.
    backend_name = "mounts"

    def __init__(self, stores: Mapping[str, Store], *, read_only: Collection[str] = ()) -> None:
        # The base's own, which settles nothing but the log -- where a store's
        # file is belongs to `FileStore`, and this one has none. The log is
        # null because every mounted store already records what it was asked,
        # under the key it knows: a second record here would double every event
        # and spell the key twice.
        super().__init__()

        # Normalised before anything is compared against it, so that a mount
        # point spelled one way in `stores` and another way here still names
        # the same mount. A read-only flag that silently applied to nothing
        # would be the worst of the available failures.
        refusing = set()
        for prefix in read_only:
            parsed = keys.parse(prefix)
            if parsed.key == keys.ROOT:
                raise MountError("mount-root-read-only")
            refusing.add(parsed.key)

        by_prefix: dict[str, Mount] = {}
        for prefix, store in stores.items():
            parsed = keys.parse(prefix)
            if parsed.is_metadata:
                raise MountError("mount-point-is-metadata", mount=parsed.key)
            if parsed.key in by_prefix:
                raise MountError("mount-duplicate", mount=parsed.key)
            # A backend that cannot be written is read-only here whether or not
            # a flag said so. The flag records a *decision* about a store that
            # could be written; this records what the storage is, and a mount
            # that reported itself writable because nobody passed --mount-ro
            # would be telling every caller something no write could make true.
            storage = not type(store).writable
            if storage and parsed.key == keys.ROOT:
                # Same reason the flag is refused at the root, one layer down:
                # the root owns every key no mount claims, so a root that
                # cannot be written is a namespace with nowhere to put
                # anything. Mount it at a prefix instead -- or, to simply read
                # one, open it directly, which is what the command line does.
                raise MountError("mount-root-not-writable", backend=type(store).__name__)
            by_prefix[parsed.key] = Mount(
                prefix=parsed.key,
                store=store,
                read_only=storage or parsed.key in refusing,
            )

        # A read-only flag naming a mount point nothing is mounted at is a
        # typo, and the kind that reads as if it worked: the server would start,
        # every mount would be writable, and nothing would say why. Refused
        # rather than ignored.
        unmatched = sorted(refusing - set(by_prefix), key=keys.sort_form)
        if unmatched:
            raise MountError("mount-read-only-unmatched", mounts=unmatched)

        if keys.ROOT not in by_prefix:
            raise MountError("mount-table-has-no-root")

        # Ordered the way a listing is, so anything built by walking this comes
        # out in key order without a second sort.
        self._mounts = sorted(by_prefix.values(), key=lambda m: keys.sort_form(m.prefix))
        self._by_prefix = by_prefix

    @classmethod
    def single(cls, store: Store) -> MountedStore:
        """A table holding only ``store``, at the root.

        The single store case stated as a mount table rather than as a separate
        path through the server, so there is one set of behaviour to test and
        no second code path that only runs when nothing is mounted.
        """
        return cls({keys.ROOT: store})

    def remounted(
        self,
        *,
        mount: Mapping[str, Store] = MappingProxyType({}),
        read_only: Collection[str] = (),
        unmount: Collection[str] = (),
    ) -> MountedStore:
        """This table with mounts removed and added, as a new table.

        Pure table algebra: no file is opened, no directory is consulted, and
        nothing here knows where a store came from. The caller opens what it
        wants mounted and passes the open stores in ``mount``, keyed by the
        prefix each is to answer for; ``unmount`` names prefixes to drop, and
        removals are applied before additions, so one call can move a store.
        A prefix in ``mount`` that something already holds **replaces** it.

        Every surviving mount is copied whole, so **a shared store keeps its
        prefix by construction** -- which is the whole of why sharing is safe,
        since :attr:`~outrage.store.Store.mount_point` is the only thing a
        store knows about its own mounting. A mount at a *new* prefix takes a
        newly opened store, and this cannot silently do otherwise: the stores
        it mounts are the ones it was handed.

        A surviving mount keeps its read-only flag; a replaced one does not,
        since a replacement states what it is. The result goes through
        :meth:`__init__`, so every invariant a table has is re-checked here
        rather than restated -- a metadata mount point, a duplicate, a root
        that must exist and be writable, a read-only flag matching nothing.

        The root is refused in both arguments. It owns every key no mount
        claims, so a table without one has nowhere to put anything, and
        ``server.instructions()`` is built once from its ``readme`` -- a root
        that cannot change is what keeps a connection's delivered instructions
        honest for as long as it lasts.

        This says nothing about *when* a table is swapped, or who then owns the
        stores that fell out of it. That is :mod:`outrage.remount`, which is
        where the mutable state and the lock live.
        """
        removing = set()
        for prefix in unmount:
            parsed = keys.parse(prefix)
            if parsed.key == keys.ROOT:
                raise MountError("mount-unmount-at-root")
            if parsed.key not in self._by_prefix:
                # The same argument `open_mounts` makes for an unmatched
                # read-only flag: what a mistyped unmount leaves behind is the
                # mount it was meant to take away.
                raise MountError("mount-unmount-unmatched", mount=parsed.key)
            removing.add(parsed.key)

        adding: dict[str, Store] = {}
        for prefix, store in mount.items():
            parsed = keys.parse(prefix)
            if parsed.key == keys.ROOT:
                raise MountError("mount-remount-at-root")
            # Two spellings of one prefix would otherwise collapse into one
            # entry here and reach `__init__` as a single mount, which is the
            # one duplicate its own check cannot see.
            if parsed.key in adding:
                raise MountError("mount-duplicate", mount=parsed.key)
            adding[parsed.key] = store

        stores = {m.prefix: m.store for m in self._mounts if m.prefix not in removing}
        refusing = {
            m.prefix
            for m in self._mounts
            if m.read_only and m.prefix in stores and m.prefix not in adding
        }
        stores.update(adding)
        refusing.update(keys.parse(prefix).key for prefix in read_only)
        return MountedStore(stores, read_only=sorted(refusing, key=keys.sort_form))

    @property
    def root(self) -> Mount:
        """The mount at the empty prefix, which every table is required to have.

        The store a key falls to when nothing longer claims it, and so the only
        one whose ``readme`` is delivered and the only one a caller can reach
        without naming a mount. Its prefix being empty is what makes
        :meth:`resolve` total: there is always a longest match.
        """
        return self._by_prefix[keys.ROOT]

    @property
    def read_only(self) -> list[Mount]:
        """The mounts that refuse writes, in key order."""
        return [m for m in self._mounts if m.read_only]

    @property
    def multiple(self) -> bool:
        """Whether anything is mounted besides the root."""
        return len(self._mounts) > 1

    def __len__(self) -> int:
        return len(self._mounts)

    def __iter__(self) -> Iterator[Mount]:
        return iter(self._mounts)

    def resolve(self, key: str | None, *, allow_wildcard: bool = False) -> Resolved:
        """The store owning ``key``, and the name it knows it by.

        Longest prefix wins, and the root always matches, so this cannot fail
        to find a mount for a key that parses. A mount **shadows** whatever the
        store behind it holds at the same keys: the outer store is never
        consulted for a key a mount claims, so a document left behind at a key
        that later became a mount point is unreachable rather than merged. That
        is the mount table rule, and the alternative -- merging two stores that
        disagree about one key -- has no answer that is not arbitrary.

        ``allow_wildcard`` is passed straight through to the parse and needs
        no handling of its own: a mount prefix is literal text, so a ``?``
        segment can never match one, and a key allocating a segment routes by
        the segments around it exactly as the finished key will.
        """
        # The only parse in the codebase that takes the joined bound: this is
        # the one place a key spanning a mount point and a store is seen whole.
        outer = keys.parse(
            keys.ROOT if key is None else key,
            allow_wildcard=allow_wildcard,
            max_segments=keys.MAX_JOINED_SEGMENTS,
        ).key
        best = self.root
        for mount in self._mounts:
            if mount.inner(outer) is not None and len(mount.prefix) > len(best.prefix):
                best = mount
        inner = best.inner(outer)
        assert inner is not None  # the root matches every key
        return Resolved(mount=best, key=inner, outer=outer)

    def below(self, key: str | None) -> list[Mount]:
        """The mounts strictly beneath ``key``, in key order.

        Every mount below ``key``, nested ones included, which is what makes
        this the wrong list to traverse with: use ``directly_below``, or
        ``segments``, which is built on it. This one answers "which stores does
        this subtree touch", for a caller reporting rather than reading.
        """
        outer = keys.parse(
            keys.ROOT if key is None else key, max_segments=keys.MAX_JOINED_SEGMENTS
        ).key
        # `strip_prefix(outer, prefix)`, not `mount.inner(outer)`: the question
        # is whether the mount point lies below the key, which is the opposite
        # direction from the one routing asks. Empty means the mount is *at*
        # `key` rather than below it, and answers for it rather than being
        # missed by it.
        return [m for m in self._mounts if keys.strip_prefix(outer, m.prefix)]

    def directly_below(self, key: str | None) -> list[Mount]:
        """The mounts beneath ``key`` that no other mount beneath it contains.

        The ones a traversal of ``key`` meets *first*, in key order. A mount
        nested inside another is left out because it is not reached from here:
        it is reached from the mount containing it, one level further down, and
        that is what makes nesting fall out of recursion rather than needing a
        case of its own.

        Taking them in search order is what makes the test local. An ancestor
        sorts immediately before its descendants, so a mount is nested exactly
        when the last one kept is a prefix of it, and nothing further back can
        contain it.
        """
        kept: list[Mount] = []
        for mount in self.below(key):
            if kept and keys.strip_prefix(kept[-1].prefix, mount.prefix):
                continue
            kept.append(mount)
        return kept

    def segments(
        self,
        key: str | None,
        depth: int | None = None,
        *,
        key_range: KeyRange = UNBOUNDED,
    ) -> list[Segment]:
        """``key``'s subtree as the stretches of each store that make it up.

        In key order, disjoint, and covering every key at or below ``key`` that
        any store answers for -- so a traversal that reads each in turn reads
        the subtree, mounts included, and one that reads only the first behaves
        as it did before mounts existed.

        The store answering for ``key`` contributes the stretches *between* the
        mounts below it, named from both sides: ``before`` ends the stretch in
        front of a mount point and ``after_subtree`` starts the one behind it.
        That is not only an optimisation. The outer store still holds every row
        a mount shadows, so a traversal that did not step over them would
        report documents that reading by key refuses -- a survey offering keys
        a read denies, of which this is the general form.

        A mount past the depth budget is stepped over but not descended into:
        its stretch is still cut out of the store above, since those rows are
        unreachable whether or not anything asked for them.
        """
        at = self.resolve(key)
        parts = self._segments(at.mount, at.key, at.outer, depth)
        if key_range == UNBOUNDED:
            return parts
        # A caller's range is spelled in the one namespace and every segment
        # answers in its own, so it is translated per segment and intersected
        # with the stretch that segment already was. A segment the range
        # excludes is dropped rather than asked with the bound quietly
        # missing, which is what would hand back the whole of it.
        narrowed = []
        for segment in parts:
            inward = _inward_range(segment.mount, key_range)
            if inward is None:
                continue
            narrowed.append(
                dataclasses.replace(segment, key_range=_intersect(segment.key_range, inward))
            )
        return narrowed

    def _segments(self, mount: Mount, inner: str, outer: str, budget: int | None) -> list[Segment]:
        """``segments`` for one store, recursing into the mounts it contains."""
        subtree = BoundedSubtree(inner, budget)
        found: list[Segment] = []
        lo: str | None = None

        for below in self.directly_below(outer):
            # As the store answering here names it: the stretch to be cut out
            # is a range in *this* store's order, and this store has never
            # heard of the prefix it was mounted at.
            edge = mount.inner(below.prefix)
            assert edge is not None  # `directly_below` returns only keys under `outer`
            found.append(Segment(mount, subtree, KeyRange(after_subtree=lo, before=edge)))

            left = keys.remaining_depth(budget, outer, below.prefix)
            if left is None or left >= 0:
                # The mount point is the inner store's root, so a descent
                # always starts a subtree over again from its own beginning.
                found += self._segments(below, keys.ROOT, below.prefix, left)
            lo = edge

        found.append(Segment(mount, subtree, KeyRange(after_subtree=lo)))
        return found

    def children(self, parent: str | None) -> list[Entry]:
        """The keys immediately below ``parent`` that exist because a mount does.

        A mount at ``lib/ref`` puts ``lib`` into the root listing and ``ref``
        into ``lib``'s, neither of which any store knows about: the outer store
        has no rows there and the inner one cannot see where it was mounted.
        Without this a mounted store is invisible to anyone who does not
        already know its prefix, which is the same failure as a document with
        no title.
        """
        outer = keys.parse(
            keys.ROOT if parent is None else parent, max_segments=keys.MAX_JOINED_SEGMENTS
        ).key
        found: dict[str, Entry] = {}
        for mount in self._mounts:
            # How far the mount point lies below `parent` -- the opposite
            # direction from routing, which asks how far a key lies below a
            # mount. None means elsewhere in the namespace; empty means the
            # mount is `parent` itself, and a mount is not a child of the key
            # it is mounted at.
            under = keys.strip_prefix(outer, mount.prefix)
            if not under:
                continue
            child = keys.with_prefix(outer, under.split(keys.DELIMITER)[0])
            if child in found:
                continue
            found[child] = self._mount_entry(mount) if child == mount.prefix else _implicit(child)
        return [found[key] for key in sorted(found, key=keys.sort_form)]

    def last_child(self, key: str | None) -> str | None:
        """The final segment of the last key immediately below ``key``.

        :meth:`outrage.store.Store.last_child` asked of the whole namespace, so
        that ``?last`` resolves to what a listing of that level would actually
        end with -- a mount point included. Without the second half, ``?last``
        at a level a mount stands in would name a key the caller can see and
        skip the one they are looking at.

        The two halves compare as bare segments and need no translation between
        namespaces: routing changes what lies *above* a level, never the name
        of a key within it, so the answering store's last child is spelled the
        same from outside as from in.
        """
        found = self.resolve(key)
        mounted = self.children(found.outer)
        names = [
            name
            for name in (
                found.store.last_child(found.key),
                mounted[-1].key.rpartition(keys.DELIMITER)[2] if mounted else None,
            )
            if name is not None
        ]
        return max(names, key=keys.sort_form) if names else None

    def shadowing(self) -> list[Mount]:
        """The mounts whose mount point the store beneath them already holds.

        A mount shadows: the store that would otherwise own those keys is never
        consulted for them, so a document left at a key that later became a
        mount point becomes unreachable rather than merged. That is quiet
        enough to be worth saying out loud once, at startup, while somebody can
        still move the document or the mount.

        The check is the key and its subtree, which misses one corner: a mount
        point the outer store holds *only* metadata for. Metadata sits at the
        key rather than below it, so neither question finds it. Worth naming
        rather than chasing -- both are misconfigurations, and this catches the
        ones anybody actually creates.
        """
        return [m for m in self._mounts if not m.is_root and self._shadows(m)]

    def _shadows(self, mount: Mount) -> bool:
        beneath = self._covering(mount)
        inner = beneath.inner(mount.prefix)
        assert inner is not None  # the root covers every mount point
        return beneath.store.exists(inner) or beneath.store.descendant_count(inner) > 0

    def _covering(self, mount: Mount) -> Mount:
        """The mount that would own ``mount``'s prefix if ``mount`` were not there."""
        best = self.root
        for other in self._mounts:
            if other is mount or other.is_root:
                continue
            if other.inner(mount.prefix) is not None and len(other.prefix) > len(best.prefix):
                best = other
        return best

    def read_only_below(self, key: str | None = None) -> list[str]:
        """The mounts below ``key`` that refuse a write, in key order.

        Not part of what a store is, and deliberately not folded into
        :meth:`delete`'s answer: that returns the keys that went, and a mount
        that refused is not a key. This is what a front end needs in order to
        say *which* part of a subtree a delete will never reach -- which is a
        sentence, and a sentence is the front end's business.
        """
        return [mount.prefix for mount in self.below(key) if mount.read_only]

    def read_only_at_or_below(self, key: str | None = None) -> list[str]:
        """The mounts that refuse a write anywhere at or below ``key``, in key order.

        :meth:`read_only_below` and, in front of it, the mount that owns ``key``
        itself when that one refuses. The difference is the whole question for a
        caller writing *into* a subtree rather than clearing one out: a delete
        names the top of what it is removing, so every mount that can refuse it
        is underneath, while a copy names where documents will land, and the
        mount that refuses them is as often the one they are landing inside.

        Asked by :func:`outrage.server.build_server`'s copy, which reported
        twenty failures and named no mount at all while it asked the other
        question -- each failure carrying the whole read-only refusal, so the
        one fact arrived five times as a sample and never once as a sentence.
        """
        owner = self.resolve(key)
        below = self.read_only_below(key)
        if not owner.read_only:
            return below
        return sorted({owner.mount.prefix, *below}, key=keys.sort_form)

    def _replaced(self, found: Resolved, outer_key: str) -> Entry | None:
        """The entry a mount point displaces from the answering store's level.

        Asked only of the keys a mount contributes to a listing, and only so the
        level totals describe what the listing shows. A mount point the store
        beneath it also holds is a misconfiguration -- :meth:`shadowing` reports
        it at startup -- but the totals have to be right for every listing
        after, and a mount **replaces** what it shadows rather than adding to
        it: one position in the level, and the characters are the mount's, not
        the ones underneath it that nothing can now read.
        """
        inner = found.mount.inner(outer_key)
        return None if inner is None else found.store.level_entry(inner)

    def _mount_entry(self, mount: Mount) -> Entry:
        """A listing entry for a mount point, described by the inner root.

        The inner store's root document is what a mount holds *at* its mount
        point, so this is where a mounted reference base gets to say what it is
        rather than appearing as a bare name. Read at one character: the size
        and the format are wanted, the content is not.
        """
        try:
            root = mount.store.retrieve_document(keys.ROOT, max_chars=1)
        except KeyNotFoundError:
            return Entry(key=mount.prefix, kind=mount.kind, size=None, format=None, updated_at=None)
        return Entry(
            key=mount.prefix,
            kind=mount.kind,
            size=root.total,
            format=root.format,
            updated_at=root.updated_at,
        )

    # -- what a store is, asked of the whole table -------------------------

    def store_document(
        self,
        key: str,
        content: str,
        format: str | None = None,
        *,
        title: str | None = None,
        contents: str | None = None,
        encoding: str | None = None,
        updated_at: str | None = None,
    ) -> str:
        found = self.resolve(key, allow_wildcard=True).writable()
        with _renamed(found.mount):
            written = found.store.store_document(
                found.key,
                content,
                format,
                title=title,
                contents=contents,
                encoding=encoding,
                updated_at=updated_at,
            )
        # The key actually written, which is how an allocated number gets back
        # to the caller -- and it has to come back in the caller's namespace,
        # since the store that allocated it has never heard of the prefix.
        return found.mount.outer(written)

    def _check_writable(self, key: str) -> None:
        """Refuse a write routed into a read-only mount before it is attempted."""
        self.resolve(key).writable()

    def retrieve_document(
        self,
        key: str,
        *,
        offset: int = 0,
        byte_offset: int | None = None,
        length: int | None = None,
        pattern: str | None = None,
        occurrence: int = 0,
        max_chars: int = DEFAULT_MAX_CHARS,
    ) -> Excerpt:
        found = self.resolve(key)
        try:
            with _renamed(found.mount):
                excerpt = found.store.retrieve_document(
                    found.key,
                    offset=offset,
                    byte_offset=byte_offset,
                    length=length,
                    pattern=pattern,
                    occurrence=occurrence,
                    max_chars=max_chars,
                )
        except KeyNotFoundError as exc:
            if exc.code not in _NOTHING_THERE:
                raise
            raise self._nothing_there(found.outer) from exc
        return dataclasses.replace(excerpt, key=found.outer)

    def _nothing_there(self, key: str) -> KeyNotFoundError:
        """Say what the *table* holds at a key no single store holds anything at.

        Both codes in :data:`_NOTHING_THERE` are answers about a subtree, and a
        store answers them from its own rows: it counts to its own edge and
        stops. So a mount below the key was missing from the count, and where
        the store answering had no row there at all -- an implicit ancestor of
        a mount point, which the merge invents and no store knows -- a key with
        a whole store beneath it came back as ``key-not-found``, whose sentence
        is "nothing is stored at or below", and which was then simply untrue.

        Counting across is what a table is for, so the table raises both codes
        itself rather than repairing the count in the one it caught. The same
        rule as :meth:`level_entry`: where the answer is about the namespace
        rather than about a store, only the table can give it.
        """
        beneath = self.descendant_count(key)
        if beneath:
            return KeyNotFoundError("key-is-a-container", key=key, beneath=beneath)
        return KeyNotFoundError("key-not-found", key=key)

    def exists(self, key: str) -> bool:
        found = self.resolve(key)
        return found.store.exists(found.key)

    def level_entry(self, key: str) -> Entry | None:
        """As :meth:`~outrage.store.Store.level_entry`, mount points included.

        A mount point is a key no store knows about, so asking the store behind
        it would answer about whatever the mount shadows -- which is exactly the
        row a listing has just declined to show. Answered here instead, from the
        inner store's root, the same way :meth:`children` describes one.
        """
        found = self.resolve(key)
        if not found.mount.is_root and found.key == keys.ROOT:
            return self._mount_entry(found.mount)
        entry = found.store.level_entry(found.key)
        if entry is None:
            # An implicit ancestor of a mount point: a mount at `lib/deep` puts
            # `lib` in the root listing through :meth:`children`, and no store
            # holds a row there to describe it. Answering None said the key a
            # listing had just offered was not on the level it came from, which
            # is the disagreement `test_level_entry_agrees_with_the_listing_it
            # _describes` exists to catch -- the same fault as a mount shadowing
            # a document, in the one direction that had no row to win it.
            return _implicit(found.outer) if self.children(found.outer) else None
        return dataclasses.replace(entry, key=found.outer)

    def descendant_count(
        self, key: str, *, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False
    ) -> int:
        found = self.resolve(key)
        return sum(
            _kept_below(segment, found, whole_subtree=whole_subtree)
            for segment in self.segments(found.outer, key_range=key_range)
        )

    def subtree_totals(
        self, key: str, *, key_range: KeyRange = UNBOUNDED, chars: bool = False
    ) -> SubtreeTotals:
        """The three totals summed over the segments, as the count is.

        :meth:`descendant_count`'s merge with two more numbers riding along:
        the same segments, the same ranges cutting out what each mount shadows,
        and the same asymmetry about what "below" means from outside a store.
        Deliberately the same shape rather than a fresh traversal, because the
        one property worth having here is that ``keys`` agrees with
        ``descendant_count(key, whole_subtree=True)`` -- a listing that reported
        a different number of descendants from the count beside it would be a
        second definition of the subtree wearing the first one's name.

        The asymmetry, in this selection: a store mounted further down
        contributes its **root document row** as well as everything below it,
        because that row is the mount point and the mount point is beneath the
        key. Its root metadata unit needs no putting back -- unlike the plain
        count, this selection already holds it.

        **What it does not count is a key only a mount table knows about.** A
        mount at ``lib/ref`` puts ``lib`` in a listing, and no store holds a row
        there; :meth:`descendant_count` has never counted those either, and
        answering differently here is precisely the disagreement above.
        """
        found = self.resolve(key)
        counted = 0
        documents = 0
        measured = 0
        for segment in self.segments(found.outer, key_range=key_range):
            # The whole segment inside the rename, not just the aggregate:
            # measuring the root row reads it, and a row deleted between the
            # test and the read raises. Outside this, that error would name the
            # key as the mounted store spells it, which is a name the caller
            # has never seen.
            with _renamed(segment.mount):
                root = segment.subtree.key
                totals = segment.store.subtree_totals(
                    root, key_range=segment.key_range, chars=chars
                )
                at = (
                    0
                    if segment.mount is found.mount
                    else _document_row_at(segment.store, root, segment.key_range)
                )
                measured += totals.chars or 0
                if chars and at:
                    measured += _document_chars_at(segment.store, root)
            counted += totals.keys + at
            documents += totals.documents + at
        return SubtreeTotals(keys=counted, documents=documents, chars=measured if chars else None)

    def latest_change(
        self, key: str, *, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False
    ) -> str | None:
        """The newest change any mount the range touches holds below ``key``.

        The maximum over the segments, where a count is the sum over them: the
        merge differs by the aggregate and the segments are the same ones. Each
        store answers about its own stretch, and a store mounted further down
        contributes its root row too, because everything it holds is below the
        key -- the asymmetry :func:`_kept_below` exists for, in the shape a
        maximum needs.

        None when no mount the range touches holds anything, which is what
        every empty selection answers here.
        """
        found = self.resolve(key)
        newest: str | None = None
        for segment in self.segments(found.outer, key_range=key_range):
            with _renamed(segment.mount):
                newest = _later(
                    newest,
                    segment.store.latest_change(
                        segment.subtree.key,
                        key_range=segment.key_range,
                        whole_subtree=whole_subtree,
                    ),
                )
                if segment.mount is not found.mount:
                    newest = _later(newest, _newest_at(segment, whole_subtree=whole_subtree))
        return newest

    def delete(
        self,
        key: str,
        recursive: bool = False,
        *,
        key_range: KeyRange = UNBOUNDED,
        unchanged_since: str | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        """As :meth:`~outrage.store.Store.delete`, and it **crosses**.

        Deliberate, and the one place crossing makes the system more dangerous
        rather than less: a delete that stopped at a boundary while every other
        call crossed one would leave a caller to learn the rule from what
        survived.

        A read-only mount below the key is **skipped rather than fatal**, since
        one such mount deep in a subtree should not veto a delete that is legal
        everywhere else in it. What it kept back is not returned here -- this
        answers with the keys that went -- and a front end that has to say so
        asks :meth:`read_only_below`.

        ``unchanged_since`` is checked **here, over the whole table**, and is
        not passed inward. A recursive delete is one store's call at a time, so
        a watermark handed to each of them in turn would let the third mount
        refuse a run the first two had already carried out -- which is the half
        finished outcome the precondition exists to prevent. Asked of the table
        it is one aggregate per mount and the refusal comes before any of them
        is asked to delete anything.

        ``dry_run`` is passed inward, to every segment: a preview of a crossing
        delete has to name what each store would take, and a table that
        previewed only its own stretch would report a fraction of the answer as
        though it were all of it. A read-only mount is skipped in a preview
        exactly as it is skipped in the delete, which is what makes the two
        lists the same list.
        """
        check_unchanged(
            self,
            key,
            unchanged_since,
            action="delete",
            subtree=recursive,
            key_range=key_range,
        )
        found = self.resolve(key).writable("delete")
        if not recursive:
            # The key itself, and nothing else. It lives in the store that
            # answers for it and nowhere else -- a mount at that key would have
            # taken over answering for it -- so this crosses nothing.
            inward = _inward_range(found.mount, key_range)
            if inward is None:
                return []
            with _renamed(found.mount):
                return _outward_keys(
                    found, found.store.delete(found.key, key_range=inward, dry_run=dry_run)
                )

        removed: list[str] = []
        for segment in self.segments(found.outer, key_range=key_range):
            if segment.mount.read_only:
                continue
            with _renamed(segment.mount):
                gone = segment.store.delete(
                    segment.subtree.key,
                    recursive=True,
                    key_range=segment.key_range,
                    dry_run=dry_run,
                )
            removed += _named_keys(segment, gone)
        return removed

    def list_keys(
        self,
        key: str | None = None,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        descendant_counts: bool = False,
        descendant_chars: bool = False,
    ) -> Page[Entry]:
        """As :meth:`~outrage.store.Store.list_keys`, with the mounts spliced in.

        A mount point is a key no store knows about: the store beneath it has no
        row there, and the store above it cannot see where it was mounted. Put
        in here or a mounted store is invisible to anyone who does not already
        know its prefix.

        **The descendant flags are answered here and not passed inward**, which
        is the whole reason they compose. A store asked about its own subtree
        cannot see a mount below it: it would count rows the mount shadows and
        reading by key refuses, and leave out everything the mounted store
        holds -- wrong in both directions at once, and quietly. So the page is
        filled by :meth:`subtree_totals` over the *table*, which is the same
        merge :meth:`descendant_count` makes, and a mount point reports what the
        store mounted there holds rather than the nothing its own row says.

        Filled after the cut, so a level wider than the page costs the page.
        """
        found = self.resolve(key)
        inward = _inward_cursor(found, cursor)
        with _renamed(found.mount):
            listing = found.store.list_keys(found.key, limit=limit, cursor=inward)
        entries = _outward_items(found, listing.items)

        children = self.children(found.outer)
        bound = None if cursor is None else keys.sort_form(cursor)
        ahead = [e for e in children if bound is None or keys.sort_form(e.key) > bound]

        # The store counted its whole level, and a key a mount contributes may
        # already be in it. Asked of the store rather than of the page, since
        # the page is a page: the row a mount stands in front of can sit well
        # past the cursor and still have to come out of the totals.
        replaced = {e.key: self._replaced(found, e.key) for e in children}

        # A mount **point** wins a collision, because a mount shadows: the same
        # rule the routing follows, so a listing cannot show a key that reading
        # it would not reach.
        #
        # A key that merely has a mount somewhere *below* it shadows nothing.
        # The store's own row there is still read by key, so the synthesised
        # implicit entry must not stand in front of it -- it exists only to say
        # that a level nothing lists has something underneath. Getting this
        # backwards is the mirror image of a shadowing leak: there a survey
        # offers keys that reading refuses, here a listing hides a key that
        # reading returns, with no size, no format and no timestamp.
        merged = {e.key: e for e in entries}
        for child in ahead:
            if child.kind == MOUNT_KIND or child.kind == READ_ONLY_MOUNT_KIND:
                merged[child.key] = child
            elif replaced[child.key] is None:
                merged[child.key] = child
        ordered = sorted(merged.values(), key=lambda e: keys.sort_form(e.key))

        # Both halves are merged before either is cut, for the reason the store
        # merges its own two halves first: cutting separately lets whichever
        # half is denser near the cursor push the other's keys over the edge,
        # and a cursor never looks back.
        cut = limit is not None and len(ordered) > limit
        items = _with_descendants(
            self,
            ordered[:limit] if cut else ordered,
            counts=descendant_counts,
            chars=descendant_chars,
        )

        # Where to resume. When the page was cut, the last key emitted -- never
        # the store's own cursor, which lies past the rows the cut withheld and
        # would skip them. When it was not, the later of the two.
        marks = [items[-1].key] if items else []
        if not cut and listing.next_cursor is not None:
            marks.append(found.mount.outer(listing.next_cursor))
        more = cut or listing.next_cursor is not None

        # A mount point **replaces** the position it stands in front of rather
        # than joining it, so the displaced entry comes back out of the totals
        # before the mount's own goes in -- otherwise the level reports the
        # characters of a document the same listing has just declined to show.
        # A key that only has a mount below it displaces nothing and is already
        # in the store's count, so it adds a position only where the store has
        # no row of its own.
        total = listing.total
        total_chars = listing.total_chars
        for child in children:
            stood_in_front_of = replaced[child.key]
            if child.kind == "implicit":
                if stood_in_front_of is None:
                    total += 1
                continue
            if stood_in_front_of is None:
                total += 1
            else:
                total_chars -= stood_in_front_of.size or 0
            total_chars += child.size or 0
        return Page(
            items=items,
            returned=len(items),
            total=total,
            total_chars=total_chars,
            next_cursor=max(marks, key=keys.sort_form) if more and marks else None,
        )

    def get_documents(
        self,
        subtree: BoundedSubtree = EVERYTHING,
        *,
        key_range: KeyRange = UNBOUNDED,
        cursor: str | None = None,
        meta_name: str | Sequence[str] | None = None,
        max_chars: int = DEFAULT_BULK_MAX_CHARS,
        limit: int | None = None,
        max_total_chars: int | None = None,
    ) -> Page[Excerpt]:
        found = self.resolve(subtree.key)
        _inward_cursor(found, cursor)  # refuses a cursor from outside the subtree
        return _across_segments(
            self.segments(found.outer, subtree.depth, key_range=key_range),
            lambda segment, **bounds: segment.store.get_documents(
                segment.subtree, meta_name=meta_name, max_chars=max_chars, **bounds
            ),
            after=cursor,
            limit=limit,
            max_total_chars=max_total_chars,
            named=_named_items,
            key_of=lambda excerpt: excerpt.key,
            size_of=lambda excerpt: excerpt.returned,
        )

    def keys_missing_meta(
        self,
        subtree: BoundedSubtree = EVERYTHING,
        *,
        key_range: KeyRange = UNBOUNDED,
        cursor: str | None = None,
        meta_name: str | Sequence[str] = "title",
        limit: int | None = None,
    ) -> Page[str]:
        found = self.resolve(subtree.key)
        _inward_cursor(found, cursor)  # refuses a cursor from outside the subtree
        return _across_segments(
            self.segments(found.outer, subtree.depth, key_range=key_range),
            lambda segment, **bounds: segment.store.keys_missing_meta(
                segment.subtree, meta_name=meta_name, **bounds
            ),
            after=cursor,
            limit=limit,
            # A collection of keys has no character budget, and handing it one
            # it does not take would be a decision about its shape taken here.
            max_total_chars=None,
            named=_named_keys,
            key_of=lambda name: name,
            size_of=lambda _name: 0,
        )

    def missing_meta_stats(
        self,
        subtree: BoundedSubtree = EVERYTHING,
        *,
        key_range: KeyRange = UNBOUNDED,
        window: KeyRange = UNBOUNDED,
        meta_name: str | Sequence[str] = "title",
        sample: int = 0,
    ) -> MissingMeta:
        """What a metadata survey could not see, summed across the boundary.

        The counts add for the same reason the pages concatenate: the segments
        are disjoint and tile the subtree, and each store counts only its own
        stretch. ``window`` crosses like any other range -- a segment it
        excludes is not asked at all, which is what makes a caller's windows
        tile as they page.
        """
        found = self.resolve(subtree.key)
        total = 0
        total_chars = 0
        names: list[str] = []
        for segment in self.segments(found.outer, subtree.depth, key_range=key_range):
            inward = _inward_range(segment.mount, window)
            if inward is None:
                continue
            gap = segment.store.missing_meta_stats(
                segment.subtree,
                key_range=segment.key_range,
                window=inward,
                meta_name=meta_name,
                sample=sample,
            )
            total += gap.total
            total_chars += gap.total_chars
            names += _named_keys(segment, gap.sample)
        return MissingMeta(total=total, total_chars=total_chars, sample=names[:sample])

    # A table has no ``path``, ``directory``, ``backup``, ``audit_rows``,
    # ``check_file`` or ``repair``, and does not answer them at all: it is a
    # `Store` and not a `FileStore`, which is what those members belong to.
    # Until 2026-08-27 they were declared here to raise `mount-has-no-file`,
    # which was a class saying in eight sentences what its base class now says
    # once. A caller holding a table and wanting a file is holding the wrong
    # thing, and `isinstance(store, FileStore)` is how it asks.

    def close(self) -> None:
        """Close this thread's connection to every mounted store."""
        for mount in self._mounts:
            mount.store.close()

    def __enter__(self) -> MountedStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def _implicit(key: str) -> Entry:
    return Entry(key=key, kind="implicit", size=None, format=None, updated_at=None)


@dataclass(frozen=True, slots=True)
class Spec:
    """A store as an argument names it: which file, and how to open it.

    The value half of ``--mount KEY=FILE,type=NAME``, and the whole of
    ``--root-mount FILE,type=NAME``, which is why it is a thing of its own
    rather than a pair returned beside a mount point: the root takes the same
    grammar and has no mount point to be returned beside.

    ``path`` is relative to the store directory, as every store file is;
    ``store_file`` applies that when the store is opened rather than here, so
    this stays a parse of the argument and touches nothing.
    """

    path: Path
    type: str | None = None
    """The backend, when the argument named one, else None for the file to say."""
    extensions: str | None = None
    """How file names line up with keys, when the argument said; else the
    backend's own default. Only a tree has an answer -- see
    :data:`EXTENSIONS_OPTION`."""

    def opened(
        self,
        directory: str | os.PathLike[str] | None = None,
        *,
        log: EventLog | None = None,
        mount_point: str | None = None,
    ) -> store_module.FileStore:
        """The store this spec names, opened in ``directory``.

        **The one place a spec becomes a store**, and a method rather than a
        line repeated wherever one is opened. Every field here is something an
        argument said about *how to open it*, so a caller taking them apart by
        hand has to be revisited each time the grammar grows one -- and the
        failure when it is not is silent in the worst way: the option parses,
        the mount succeeds, and the store opens under something nobody asked
        for. Nothing raises and no suite goes red, so the only thing that finds
        it is somebody reading the keys.
        """
        return store_module.default_store(
            directory,
            filename=self.path,
            backend=self.type,
            extensions=self.extensions,
            log=log,
            mount_point=mount_point,
        )


def parse_options(value: str, *, spec: str | None = None) -> Spec:
    """Split ``FILE[,NAME=VALUE]...``, or say why it is not one.

    The value half of a mount spec, and a ``--root-mount`` whole. ``spec`` is
    what the reader actually wrote, when there is a longer argument to quote
    back at them.

    **An unknown option name is refused**, and so is a repeat of a known one.
    The first is the rule ``mounts.toml`` already follows for a field it does
    not recognise, for the reason a mount configuration exists: it is read
    later, by somebody who is not watching, and an option that silently did
    nothing is the failure least likely to be noticed -- a mount that is not
    the store it says is a store that reads as simply empty. The second is the
    same refusal a duplicate mount point earns, one level down.

    The *value* of an option is not checked here. ``type=nonsense`` is a
    backend that does not exist, which :func:`outrage.store._backend_for`
    refuses in its own words when the store is opened; a second list of
    backend names kept here to refuse it a moment earlier is exactly the
    duplicate vocabulary this grammar is written to avoid.
    """
    quoted = value if spec is None else spec
    file, _, rest = value.partition(OPTION_DELIMITER)
    if not file:
        raise MountError("mount-spec-has-no-file", spec=quoted)
    options: dict[str, str] = {}
    while rest:
        option, _, rest = rest.partition(OPTION_DELIMITER)
        name, assigned, setting = option.partition(OPTION_ASSIGNMENT)
        if not assigned or not name:
            raise MountError(
                "mount-option-malformed",
                spec=quoted,
                option=option,
                assignment=OPTION_ASSIGNMENT,
            )
        if name not in OPTIONS:
            raise MountError("mount-option-unknown", spec=quoted, option=name, known=list(OPTIONS))
        if name in options:
            raise MountError("mount-option-repeated", spec=quoted, option=name)
        options[name] = setting
    return Spec(Path(file), options.get(TYPE_OPTION), options.get(EXTENSIONS_OPTION))


def unparse(spec: Spec) -> str:
    """``spec`` as the argument it was read from: the inverse of
    :func:`parse_options`.

    What a mount table renders into when it is spliced into a command line,
    which is the whole mechanism by which a file has any effect at all -- so
    the two functions are here together, where they can be read as one grammar
    and tested as a round trip.

    A store file holding the option delimiter is refused *here* as well as on
    the way in, because this is the direction a file reaches: an entry written
    as ``{ path = "a,b" }`` in TOML never passed through a spec, and rendering
    it would produce an argument that parses back as something else.
    """
    file = str(spec.path)
    if OPTION_DELIMITER in file:
        raise MountError("mount-file-unspellable", file=file, delimiter=OPTION_DELIMITER)
    # In :data:`OPTIONS` order rather than in the order they were written,
    # which a parsed spec no longer knows: what has to round-trip is what the
    # options *say*, and one settled order is what makes two specs meaning the
    # same thing render the same way.
    written = [(TYPE_OPTION, spec.type), (EXTENSIONS_OPTION, spec.extensions)]
    return file + "".join(
        f"{OPTION_DELIMITER}{name}{OPTION_ASSIGNMENT}{value}"
        for name, value in written
        if value is not None
    )


def _root_spec(root_mount: str | os.PathLike[str] | Spec | None) -> Spec | None:
    """``--root-mount``'s value as a :class:`Spec`, whatever shape it arrived in."""
    if root_mount is None or isinstance(root_mount, Spec):
        return root_mount
    if isinstance(root_mount, str):
        return parse_options(root_mount)
    return Spec(Path(root_mount))


def parse_spec(spec: str) -> tuple[str, Spec]:
    """Split a ``KEY=FILE[,NAME=VALUE]...`` mount argument, or say why it is
    not one.

    ``FILE`` is a store file **relative to the store directory**, not a
    directory of its own: every mount a server holds lives in the one directory
    ``--dir`` names, as a file beside the root mount. ``store_file`` is the
    rule, and it is applied when the store is opened rather than here, so that
    this stays a parse of the argument and touches nothing.

    The key is validated here rather than when the store is opened, so a
    misspelled mount point is refused before a database is created for it --
    ``Store`` makes its file on the way in, and a typo would otherwise leave an
    empty store behind as evidence of a server that never started.

    The options after the file are :func:`parse_options`'s, and everything a
    mount can say beyond *where* it is goes there. One flag remains one mount,
    which is what keeps overriding an entry from a mount configuration a matter
    of replacing it whole -- see :data:`OPTION_DELIMITER`.
    """
    prefix, delimiter, value = spec.partition(SPEC_DELIMITER)
    if not delimiter:
        raise MountError("mount-spec-malformed", spec=spec)
    if not value:
        raise MountError("mount-spec-has-no-file", spec=spec)
    return mount_point(prefix, spec=spec), parse_options(value, spec=spec)


def mount_point(prefix: str, *, spec: str | None = None) -> str:
    """Validate a mount point, however it was written down.

    Split out of :func:`parse_spec` so that a mount table read from a file
    reaches exactly these refusals rather than growing a second set: a config
    file that had its own idea of what a key is would be a second grammar over
    the same namespace, and the project has one. ``spec`` is what the reader
    wrote, when there is a spec to quote back at them; a file quotes the key it
    used as its own field name.
    """
    # The key is parsed with the default bound, ``keys.MAX_SEGMENTS``, which is
    # half what the joined namespace allows. Load bearing here rather than
    # incidental: a mount point admitted at the wider bound could name keys the
    # namespace above it could not.
    parsed = keys.parse(prefix)
    if parsed.key == keys.ROOT:
        raise MountError("mount-spec-at-root", spec=spec if spec is not None else prefix)
    # Here as well as in ``MountedStore.__init__``, which is the invariant for
    # a table built directly, and here for the reason above: ``open_mounts``
    # creates a store per spec *before* it builds the table, so a mount point
    # refused only there leaves a database behind named after the mistake.
    if parsed.is_metadata:
        raise MountError("mount-point-is-metadata", mount=parsed.key)
    return parsed.key


def open_mounts(
    directory: str | os.PathLike[str] | None,
    specs: Sequence[str] = (),
    read_only_specs: Sequence[str] = (),
    *,
    root_mount: str | os.PathLike[str] | Spec | None = None,
    log: EventLog | None = None,
    attached: Mapping[str, Store] = MappingProxyType({}),
) -> MountedStore:
    """Open every store in ``directory``, as one table.

    **One directory, several files.** ``directory`` holds them all: the root
    mount, named by ``root_mount``, and one file per ``KEY=FILE`` spec. That is
    what makes a mount configuration relocatable -- only the directory is an
    absolute path, and the stores in it are named relative to it -- and it is
    the shape a backend other than SQLite would slot into, since what varies
    between backends is the file, not the directory around it.

    ``specs`` are mounted read-write and ``read_only_specs`` read-only; the two
    share one namespace, so mounting the same key in both is the same collision
    as mounting it twice in either. Two mounts naming the same *file* is not a
    collision this checks: they would be two stores over one database, which
    SQLite handles and which no configuration has a reason to ask for.

    Every spec is parsed before any store is opened, so a table that cannot be
    described is refused without half of it existing. A failure part way
    through the opening closes what was already open, since a process that
    exits without doing so leaves a WAL behind.

    A read-only mount must already exist. ``Store`` creates its file and
    migrates a database on the way in, so without this check a mistyped name
    would be *created*, mount as an empty store, and read as though the
    reference base were simply empty -- while the flag that was supposed to
    protect it made it impossible to notice by writing. That is the same
    argument ``parse_spec`` makes for validating a mount point early, one step
    further along.

    ``attached`` is the one way in for a store this call did not open: already
    open, mounted read-only at the key it is given, and **not** subject to the
    relative-to-``directory`` rule above, which it could not obey. That rule is
    load bearing rather than incidental -- it is what makes a table relocatable
    -- so the exception is a separate argument rather than an absolute path
    quietly admitted into a spec. What needs it is a store shipped inside the
    installed package, which lives in ``site-packages`` and is not expressible
    as a ``KEY=FILE`` at all: :mod:`outrage.shipped`. It is mounted read-only
    because the caller is lending a store rather than handing one over, and
    everything else about it -- precedence, shadowing, how it lists -- is an
    ordinary mount's. Duplicates are refused across all three sources together;
    which of two claims at one point survives is settled before this, in
    :func:`outrage.mountfile._overridden`.

    A store passed here is closed with the table, like every other, so a caller
    hands one over and does not close it twice -- and a failure part way
    through closes it as well.
    """
    writable = [parse_spec(spec) for spec in specs]
    refusing = [parse_spec(spec) for spec in read_only_specs]
    # The root takes the same grammar as a mount, so a string is parsed for
    # options here rather than by each front end. A ``Path`` is a path and not
    # an argument -- a caller holding one has nothing to say about backends --
    # and a ``Spec`` is one already parsed.
    root = _root_spec(root_mount)
    lent = {mount_point(prefix): store for prefix, store in attached.items()}
    # Resolved once, here, because the read-only check below and the stores
    # themselves have to agree about where a mount's file is; asking twice is
    # how they would come to disagree.
    base = store_module.resolve_directory(directory)
    for prefix, spec in refusing:
        database = store_file(base, spec.path)
        if not database.exists():
            raise MountError("mount-read-only-missing", mount=prefix, path=str(database))

    # Lent stores go in first, so that anything opened here is closed by the
    # failure path below whatever order the duplicate is found in -- and so
    # that a second claim on a lent point is the same refusal as a second claim
    # on any other.
    opened: dict[str, Store] = dict(lent)
    try:
        # The root is never among the lent stores: ``mount_point`` refuses it
        # above, as it does for a spec, so this cannot overwrite one.
        # A root nobody named is the default store file under the default
        # backend, which is what a bare `Spec(Path(...))` would not say: the
        # filename has to stay None for `default_store` to answer it.
        opened[keys.ROOT] = (
            store_module.default_store(base, log=log, mount_point=keys.ROOT)
            if root is None
            else root.opened(base, log=log, mount_point=keys.ROOT)
        )
        for prefix, spec in [*writable, *refusing]:
            if prefix in opened:
                raise MountError("mount-duplicate", mount=prefix)
            opened[prefix] = spec.opened(base, log=log, mount_point=prefix)
        return MountedStore(opened, read_only=[prefix for prefix, _ in refusing] + list(lent))
    except Exception:
        for store in opened.values():
            store.close()
        raise


__all__ = [
    "EXTENSIONS_OPTION",
    "MOUNT_KIND",
    "OPTIONS",
    "OPTION_ASSIGNMENT",
    "OPTION_DELIMITER",
    "READ_ONLY_MOUNT_KIND",
    "ROOT_KIND",
    "SPEC_DELIMITER",
    "TYPE_OPTION",
    "Mount",
    "MountError",
    "MountedStore",
    "ReadOnlyMountError",
    "Resolved",
    "Segment",
    "Spec",
    "mount_point",
    "open_mounts",
    "parse_options",
    "parse_spec",
    "unparse",
]
