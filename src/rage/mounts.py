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

Configuration only, and only at startup: nothing here adds or removes a mount
on a running server. See ``project/reference/planned/mounts`` for the questions
that are deliberately still open, chief among them what a read-only mount is
and where a write to a new key goes.
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from . import keys
from .errors import RageError
from .eventlog import EventLog
from .store import Entry, KeyNotFoundError, Store

#: Separates a mount point from its store directory in a ``--mount`` argument.
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


class MountError(RageError, ValueError):
    """Raised when a mount table cannot be built as described."""


@dataclass(frozen=True, slots=True)
class Mount:
    """One store, and the prefix it answers for."""

    prefix: str
    """The key this store is mounted at, normalised. The root mount's is ``""``."""

    store: Store

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
            raise MountError(
                f"{keys.displayed(key)!r} in the store mounted at {self.name!r} has no "
                f"name in this namespace: joined it exceeds "
                f"{keys.MAX_JOINED_SEGMENTS} segments. The store holds a key deeper "
                f"than {keys.MAX_SEGMENTS} segments, which `rage check` reports; it "
                f"predates that bound and has to be moved before the store can be "
                f"mounted here."
            )
        return name


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


class Mounts:
    """The mount table: a prefix to store map, and the routing over it."""

    def __init__(self, stores: Mapping[str, Store]) -> None:
        by_prefix: dict[str, Mount] = {}
        for prefix, store in stores.items():
            parsed = keys.parse(prefix)
            if parsed.is_metadata:
                raise MountError(
                    f"cannot mount at {keys.displayed(parsed.key)!r}: a mount point may not "
                    f"be metadata, since everything below one is metadata too"
                )
            if parsed.key in by_prefix:
                raise MountError(
                    f"more than one store is mounted at {keys.displayed(parsed.key)!r}"
                )
            by_prefix[parsed.key] = Mount(prefix=parsed.key, store=store)

        if keys.ROOT not in by_prefix:
            raise MountError(
                "a mount table needs a store at the root, since it is what owns "
                "every key no other mount claims"
            )

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

        What a subtree read of ``key`` does not cover. Queries and surveys do
        not cross a mount boundary yet, so this is how they say what they did
        not look at rather than returning a partial answer that reads like a
        whole one.
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
            return Entry(key=mount.prefix, kind=MOUNT_KIND, size=None, format=None, updated_at=None)
        return Entry(
            key=mount.prefix,
            kind=MOUNT_KIND,
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
    """Split a ``KEY=PATH`` mount argument, or say why it is not one.

    The key is validated here rather than when the store is opened, so a
    misspelled mount point is refused before a database is created for it --
    ``Store`` makes its directory on the way in, and a typo would otherwise
    leave an empty store behind as evidence of a server that never started.
    """
    # The key is parsed with the default bound, ``keys.MAX_SEGMENTS``, which is
    # half what the joined namespace allows. Load bearing here rather than
    # incidental: a mount point admitted at the wider bound could name keys the
    # namespace above it could not.
    prefix, delimiter, path = spec.partition(SPEC_DELIMITER)
    if not delimiter:
        raise MountError(
            f"mount {spec!r} is not in KEY{SPEC_DELIMITER}PATH form, "
            f"as in ref{SPEC_DELIMITER}/srv/reference/.rage"
        )
    if not path:
        raise MountError(f"mount {spec!r} names no directory")
    parsed = keys.parse(prefix)
    if parsed.key == keys.ROOT:
        raise MountError(
            f"mount {spec!r} has no mount point; the store at the root is the one --dir names"
        )
    return parsed.key, Path(path).expanduser()


def open_mounts(
    root: str | os.PathLike[str] | None,
    specs: Sequence[str] = (),
    *,
    log: EventLog | None = None,
) -> Mounts:
    """Open the root store and every ``KEY=PATH`` mount, as one table.

    Every spec is parsed before any store is opened, so a table that cannot be
    described is refused without half of it existing. A failure part way
    through the opening closes what was already open, since a process that
    exits without doing so leaves a WAL behind.
    """
    table = [parse_spec(spec) for spec in specs]
    opened: dict[str, Store] = {}
    try:
        opened[keys.ROOT] = Store(root, log=log)
        for prefix, path in table:
            if prefix in opened:
                raise MountError(f"more than one store is mounted at {prefix!r}")
            opened[prefix] = Store(path, log=log)
        return Mounts(opened)
    except Exception:
        for store in opened.values():
            store.close()
        raise


__all__ = [
    "MOUNT_KIND",
    "SPEC_DELIMITER",
    "Mount",
    "MountError",
    "Mounts",
    "Resolved",
    "open_mounts",
    "parse_spec",
]
