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
to become a valid key first -- see ``project/reference/planned/root-key``.
Without it a store mounted at ``ref`` would have no way to answer for the
document or the title *at* ``ref``, and a survey could not say what the mount
is.

A mount may be **read-only**, which is where the whole feature was pointed: a
shared read-mostly reference base beside a local read-write store. The refusal
lives here, in the routing, and is checked before the store is called at all --
``Store`` knows nothing about it, and the database file is not opened any
differently. So this refuses writes *through this server*; it does not make the
file read-only to anything else.

Configuration only, and only at startup: nothing here adds or removes a mount
on a running server, and nothing marks one read-only after it. See
``project/reference/planned/mounts`` for the questions that are deliberately
still open, chief among them where a write to a new key goes.
"""

from __future__ import annotations

import contextlib
import dataclasses
import os
from collections.abc import Callable, Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import eventlog, keys
from . import store as store_module
from .errors import OutrageError
from .eventlog import EventLog
from .store import (
    DEFAULT_BULK_MAX_CHARS,
    DEFAULT_MAX_CHARS,
    EVERYTHING,
    UNBOUNDED,
    AuditRow,
    BackendError,
    Backup,
    BoundedSubtree,
    Entry,
    Excerpt,
    KeyNotFoundError,
    KeyRange,
    MissingMeta,
    Page,
    ReadOnlyStoreError,
    Store,
    store_file,
)

if TYPE_CHECKING:
    # Only in the signatures of the maintenance methods this table refuses. A
    # runtime import would be a cycle, for the reason ``store`` gives.
    from .maintenance import Repaired, Report

#: Separates a mount point from its store file in a ``--mount`` argument.
#: ``=`` rather than ``:`` because a Windows path holds a colon and no key can
#: hold an ``=`` any less than it can hold anything else -- but a key with one
#: in it is vanishingly rare, and a drive letter is not.
SPEC_DELIMITER = "="

#: The ``kind`` a listing reports for a key that is a mount point. A fourth
#: kind beside 'document', 'metadata' and 'implicit', because a mount point is
#: none of the three: it may hold content, and it always has a store behind it.
#: A caller that does not know the word still learns that the key exists, which
#: is the part that matters for navigating to it.
MOUNT_KIND = "mount"

#: The ``kind`` for a mount point whose store refuses writes. A separate kind
#: rather than a ``read_only`` field on :class:`~outrage.store.Entry`, because a
#: field would appear on *every* entry in every listing as a null -- and a
#: result grows a field only when there is something to say, which is decision
#: 5 in ``context/20/decisions``. The kind is already the field that says what
#: a key is, only one key in a listing is a mount at all, and the words carry
#: their own meaning to a caller who has never read any of this.
#:
#: This is also the only place the fact is announced. The instructions do not
#: mention mounts -- see ``instructions`` on why a mounted store's readme is
#: not carried -- so, exactly like the existence of a mount, being read-only
#: costs nothing until somebody looks at the listing.
READ_ONLY_MOUNT_KIND = "read-only mount"


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
        the sum always parses. This used to be able to fail, and every listing
        carried a path for dropping the keys it failed on; halving the bound on
        2026-08-20 abolished the case rather than reporting it.

        The check stays as an assertion, because what it now guards is an
        arithmetic relationship between two constants and a store's contents,
        and a store written before the bound was halved can still hold a key
        too deep for it. Raising names the mount and the key; returning a
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

#: A sort position past every key there is. :func:`keys.sort_subtree_end`
#: refuses the root, because everything is beneath it and nothing can be
#: appended to the empty sort form that a descendant would sort below -- but a
#: bound naming the root still has to be *compared* against a mount's stretch,
#: so the comparison gets the position the refusal denies it. Above every sort
#: form by construction, since a sort form is built from segment characters and
#: the three low markers.
_PAST_EVERYTHING = "\uffff"

#: Every :class:`~outrage.store.KeyRange` bound: whether it cuts from below,
#: whether the cut keeps what sits exactly on it, and where in the order the
#: cut falls. The same six rows as ``store_sqlite._range_clauses`` and
#: ``store_parquet._span``, and meant to be read against them -- what differs
#: between the bounds is only which key the cut is taken at and which side of
#: it survives.
#:
#: Written down once because a range crossing a boundary asks two questions of
#: every bound and that one position answers both: does this bound touch the
#: mounted store at all, and what does it say once it does.
_BOUNDS: tuple[tuple[str, bool, bool, Callable[[str], str]], ...] = (
    ("after_inclusive", True, True, keys.sort_form),
    ("after", True, False, keys.sort_form),
    ("after_subtree", True, True, keys.sort_subtree_end),
    ("before", False, False, keys.sort_form),
    ("before_inclusive", False, True, keys.sort_form),
    ("final_subtree", False, False, keys.sort_subtree_end),
)


def _cut(key: str, at: Callable[[str], str]) -> str:
    """Where a bound naming ``key`` falls in the order."""
    if at is keys.sort_subtree_end:
        parsed = keys.parse(key, max_segments=keys.MAX_JOINED_SEGMENTS)
        if parsed.key == keys.ROOT:
            return _PAST_EVERYTHING
    return at(key)


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
    for name, is_lower, inclusive, at in _BOUNDS:
        named = getattr(key_range, name)
        if named is None:
            continue
        cut = _cut(named, at)
        if is_lower and (position < cut or (not inclusive and position == cut)):
            return False
        if not is_lower and (position > cut or (not inclusive and position == cut)):
            return False
    return True


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
    live defect, ``project/reference/planned/error-naming``, and it was fixed at
    the MCP boundary; done here instead it is fixed for every front end at once,
    including the command line, which used to have no mount table to fix it
    with.

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
                mount.outer(value)
                if detail in _NAMED_DETAILS and isinstance(value, str)
                else value
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

    Total, since the bounds were halved: a mount point and a key inside a store
    are each capped at ``keys.MAX_SEGMENTS`` and the joined namespace allows
    twice that, so every key a mounted store returns has a name here. This used
    to drop and count the ones that did not, and every listing carried a
    ``dropped`` field and a note to say so.
    """
    return [
        dataclasses.replace(item, key=found.mount.outer(item.key))  # type: ignore[arg-type]
        for item in items
    ]


def _outward_keys(found: Resolved, names: list[str]) -> list[str]:
    """:func:`_outward_items` for a plain list of keys."""
    return [found.mount.outer(name) for name in names]


def _rows_at(store: Store, key: str, key_range: KeyRange) -> int:
    """The rows sitting *at* ``key``: its document, and its own metadata.

    :meth:`~outrage.store.Store.descendant_count` counts neither of them -- a
    key's metadata does not lie beneath the key -- so a caller measuring the
    stretch from *outside* the store has to put them back. They are asked of a
    level rather than of a count because that is where metadata appears, and
    tested against the range here rather than by the store because a level takes
    no range: this named the keys, so it can say which of them the range keeps.
    """
    at = [key] if store.exists(key) else []
    at += [entry.key for entry in store.list_keys(key).items if entry.kind == "metadata"]
    return sum(1 for name in at if _in_range(name, key_range))


def _kept_below(segment: Segment, found: Resolved) -> int:
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
    """
    counted = segment.store.descendant_count(segment.subtree.key, key_range=segment.key_range)
    if segment.mount is found.mount:
        return counted
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
        # Deliberately not `Store.__init__`: that settles where a store's file
        # is, and this one has none. The log is null rather than absent because
        # every mounted store already records what it was asked, under the key
        # it knows -- a second record here would double every event and spell
        # the key twice.
        self._log = eventlog.NULL

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
        report documents that reading by key refuses -- the defect in
        ``planned/mounts/shadow-leak``, of which this is the general form.

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

    def _segments(
        self, mount: Mount, inner: str, outer: str, budget: int | None
    ) -> list[Segment]:
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
        encoding: str | None = None,
    ) -> str:
        found = self.resolve(key, allow_wildcard=True).writable()
        with _renamed(found.mount):
            written = found.store.store_document(
                found.key, content, format, title=title, encoding=encoding
            )
        # The key actually written, which is how an allocated number gets back
        # to the caller -- and it has to come back in the caller's namespace,
        # since the store that allocated it has never heard of the prefix.
        return found.mount.outer(written)

    def retrieve_document(
        self,
        key: str,
        *,
        offset: int = 0,
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
        beneath = 0 if keys.parse(key).is_metadata else self.descendant_count(key)
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

    def descendant_count(self, key: str, *, key_range: KeyRange = UNBOUNDED) -> int:
        found = self.resolve(key)
        return sum(
            _kept_below(segment, found)
            for segment in self.segments(found.outer, key_range=key_range)
        )

    def delete(
        self, key: str, recursive: bool = False, *, key_range: KeyRange = UNBOUNDED
    ) -> list[str]:
        """As :meth:`~outrage.store.Store.delete`, and it **crosses**.

        Deliberate, and the one place crossing makes the system more dangerous
        rather than less: a delete that stopped at a boundary while every other
        call crossed one would leave a caller to learn the rule from what
        survived. ``project/reference/planned/mounts/crossing`` records the call.

        A read-only mount below the key is **skipped rather than fatal**, since
        one such mount deep in a subtree should not veto a delete that is legal
        everywhere else in it. What it kept back is not returned here -- this
        answers with the keys that went -- and a front end that has to say so
        asks :meth:`read_only_below`.
        """
        found = self.resolve(key).writable("delete")
        if not recursive:
            # The key itself, and nothing else. It lives in the store that
            # answers for it and nowhere else -- a mount at that key would have
            # taken over answering for it -- so this crosses nothing.
            inward = _inward_range(found.mount, key_range)
            if inward is None:
                return []
            with _renamed(found.mount):
                return _outward_keys(found, found.store.delete(found.key, key_range=inward))

        removed: list[str] = []
        for segment in self.segments(found.outer, key_range=key_range):
            if segment.mount.read_only:
                continue
            with _renamed(segment.mount):
                gone = segment.store.delete(
                    segment.subtree.key, recursive=True, key_range=segment.key_range
                )
            removed += _named_keys(segment, gone)
        return removed

    def list_keys(
        self,
        key: str | None = None,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> Page[Entry]:
        """As :meth:`~outrage.store.Store.list_keys`, with the mounts spliced in.

        A mount point is a key no store knows about: the store beneath it has no
        row there, and the store above it cannot see where it was mounted. Put
        in here or a mounted store is invisible to anyone who does not already
        know its prefix.
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
        # backwards is the mirror image of ``planned/mounts/shadow-leak``: there
        # a survey offered keys that reading refused, here a listing hid a key
        # that reading returns, with no size, no format and no timestamp.
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
        items = ordered[:limit] if cut else ordered

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

    # -- what a table has no file to answer with ---------------------------

    @property
    def directory(self) -> Path:  # type: ignore[override]
        raise BackendError("mount-has-no-file", asked="directory")

    @property
    def path(self) -> Path:  # type: ignore[override]
        raise BackendError("mount-has-no-file", asked="path")

    @property
    def stored_format_version(self) -> int:
        raise BackendError("mount-has-no-file", asked="stored_format_version")

    def backup(
        self,
        destination: str | os.PathLike[str] | None = None,
        *,
        overwrite: bool = False,
    ) -> Backup:
        raise BackendError("mount-has-no-file", asked="backup")

    def backup_path(
        self, destination: str | os.PathLike[str] | None, *, overwrite: bool
    ) -> Path:
        raise BackendError("mount-has-no-file", asked="backup")

    def audit_rows(self) -> Iterator[AuditRow]:
        raise BackendError("mount-has-no-file", asked="audit_rows")

    def check_file(self, report: Report) -> None:
        raise BackendError("mount-has-no-file", asked="check")

    def repair(self) -> list[Repaired]:
        raise BackendError("mount-has-no-file", asked="repair")

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


def parse_spec(spec: str) -> tuple[str, Path]:
    """Split a ``KEY=FILE`` mount argument, or say why it is not one.

    ``FILE`` is a store file **relative to the store directory**, not a
    directory of its own: every mount a server holds lives in the one directory
    ``--dir`` names, as a file beside the root mount. ``store_file`` is the
    rule, and it is applied when the store is opened rather than here, so that
    this stays a parse of the argument and touches nothing.

    The key is validated here rather than when the store is opened, so a
    misspelled mount point is refused before a database is created for it --
    ``Store`` makes its file on the way in, and a typo would otherwise leave an
    empty store behind as evidence of a server that never started.
    """
    # The key is parsed with the default bound, ``keys.MAX_SEGMENTS``, which is
    # half what the joined namespace allows. Load bearing here rather than
    # incidental: a mount point admitted at the wider bound could name keys the
    # namespace above it could not.
    prefix, delimiter, path = spec.partition(SPEC_DELIMITER)
    if not delimiter:
        raise MountError("mount-spec-malformed", spec=spec)
    if not path:
        raise MountError("mount-spec-has-no-file", spec=spec)
    parsed = keys.parse(prefix)
    if parsed.key == keys.ROOT:
        raise MountError("mount-spec-at-root", spec=spec)
    return parsed.key, Path(path)


def open_mounts(
    directory: str | os.PathLike[str] | None,
    specs: Sequence[str] = (),
    read_only_specs: Sequence[str] = (),
    *,
    root_mount: str | os.PathLike[str] | None = None,
    log: EventLog | None = None,
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
    """
    writable = [parse_spec(spec) for spec in specs]
    refusing = [parse_spec(spec) for spec in read_only_specs]
    # Resolved once, here, because the read-only check below and the stores
    # themselves have to agree about where a mount's file is; asking twice is
    # how they would come to disagree.
    base = store_module.resolve_directory(directory)
    for prefix, path in refusing:
        database = store_file(base, path)
        if not database.exists():
            raise MountError(
                "mount-read-only-missing", mount=prefix, path=str(database)
            )

    opened: dict[str, Store] = {}
    try:
        opened[keys.ROOT] = store_module.default_store(base, filename=root_mount, log=log)
        for prefix, path in [*writable, *refusing]:
            if prefix in opened:
                raise MountError("mount-duplicate", mount=prefix)
            opened[prefix] = store_module.default_store(base, filename=path, log=log)
        return MountedStore(opened, read_only=[prefix for prefix, _ in refusing])
    except Exception:
        for store in opened.values():
            store.close()
        raise


__all__ = [
    "MOUNT_KIND",
    "READ_ONLY_MOUNT_KIND",
    "SPEC_DELIMITER",
    "Mount",
    "MountError",
    "MountedStore",
    "ReadOnlyMountError",
    "Resolved",
    "Segment",
    "open_mounts",
    "parse_spec",
]
