"""Routing one key namespace across more than one backing store.

A mount table maps a key prefix to a :class:`~rage.store.Store`. The longest
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

import os
from collections.abc import Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from . import keys
from . import store as store_module
from .errors import RageError
from .eventlog import EventLog
from .store import (
    DB_FILENAME,
    BoundedSubtree,
    Entry,
    KeyNotFoundError,
    KeyRange,
    Store,
    store_file,
)

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
#: rather than a ``read_only`` field on :class:`~rage.store.Entry`, because a
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


class MountError(RageError, ValueError):
    """Raised when a mount table cannot be built as described."""


class ReadOnlyMountError(RageError, PermissionError):
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
        failure this project keeps finding. ``rage check`` reports such keys
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
        return self.mount.store

    @property
    def read_only(self) -> bool:
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
        """
        if not self.read_only:
            return self
        raise ReadOnlyMountError(
            "mount-read-only", key=self.outer, mount=self.mount.prefix, action=action
        )


class Mounts:
    """The mount table: a prefix to store map, and the routing over it."""

    def __init__(self, stores: Mapping[str, Store], *, read_only: Collection[str] = ()) -> None:
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
            by_prefix[parsed.key] = Mount(
                prefix=parsed.key, store=store, read_only=parsed.key in refusing
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
    def single(cls, store: Store) -> Mounts:
        """A table holding only ``store``, at the root.

        The single store case stated as a mount table rather than as a separate
        path through the server, so there is one set of behaviour to test and
        no second code path that only runs when nothing is mounted.
        """
        return cls({keys.ROOT: store})

    @property
    def root(self) -> Mount:
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

    def segments(self, key: str | None, depth: int | None = None) -> list[Segment]:
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
        return self._segments(at.mount, at.key, at.outer, depth)

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

    def close(self) -> None:
        """Close this thread's connection to every mounted store."""
        for mount in self._mounts:
            mount.store.close()

    def __enter__(self) -> Mounts:
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
    root_mount: str | os.PathLike[str] = DB_FILENAME,
    log: EventLog | None = None,
) -> Mounts:
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
        return Mounts(opened, read_only=[prefix for prefix, _ in refusing])
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
    "Mounts",
    "ReadOnlyMountError",
    "Resolved",
    "Segment",
    "open_mounts",
    "parse_spec",
]
