"""The mount table a running server serves, and how it is changed.

:mod:`outrage.mounts` deliberately has none of what is here: a table is
immutable, knows no directory, opens no file and holds no lock. This is where
a table becomes something a *process* has -- one reference, swapped under a
lock, with the stores that fall out of it closed when nothing serves them any
more.

**The safety argument, in one paragraph.** A change never edits a table. It
builds a new one with :meth:`~outrage.mounts.MountedStore.remounted` and swaps
the reference, and every server call reads that reference once, at entry, and
uses the table it got for its whole duration. So a traversal spanning several
stores -- a sequence of per-store segments, with a cursor recomputed at each
boundary -- can never see two tables, which is the failure that kept mounts to
start-time configuration until now. What it cannot promise is a *page taken
before a change and continued after it*: a cursor is a key in the outer
namespace, and which store answers for it is exactly what changed. That is the
same class of thing as a document written between two pages, and it is written
down rather than guarded.

**Sharing rather than reopening.** A surviving mount keeps the very same
:class:`~outrage.store.Store` object, because
:attr:`~outrage.store.Store.mount_point` is the only thing a store knows about
its own mounting and a surviving mount keeps its prefix. So an in-flight call
holding the old table goes on reading a store that is also in the new one, and
nothing is opened twice for a mount that did not move. A mount at a *new*
prefix always opens a new store.

**Closing is safe for the same reason it looks unsafe.**
:meth:`~outrage.store_sqlite.SqliteStore.close` closes only the calling
thread's connection, by design, so a store dropped by a change cannot be closed
out from under a call running on another thread; the rest of its connections go
when the store is collected or the thread ends.

Notes are derived here rather than in :mod:`outrage.server`, per the note
layer: this is the layer that knows what the change did, and it carries facts
rather than sentences. What the tools say about them is
:data:`outrage.messages.MCP`.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from . import keys, shipped
from . import store as store_module
from .eventlog import EventLog
from .mounts import MountedStore, MountError
from .notes import Note
from .store import Store, store_file

#: The stores outrage ships, by the mount point each answers for, as the
#: openers that produce them. This is what lets a mount be spelled without a
#: file: the shipped tree lives in ``site-packages``, is not relative to
#: ``--dir`` and so has no ``KEY=FILE`` spelling at all, which is the whole
#: reason unmounting the manual would otherwise be a one-way door.
#:
#: A mapping rather than a special case for ``outrage``, because the shape is
#: the point: a second shipped store would be an entry here and nothing else.
SHIPPED: Mapping[str, Callable[..., Store]] = MappingProxyType(
    {shipped.MOUNT_POINT: shipped.open_documents}
)


@dataclass(frozen=True, slots=True)
class Changed:
    """A change, as the table it produced and what is worth remarking on.

    The table is returned rather than left to be read back off
    :attr:`Live.table`, because between the two another thread may have changed
    it again -- and an answer describing a table that is no longer there is the
    one thing a report of a change must not be.
    """

    table: MountedStore
    notes: tuple[Note, ...] = ()


class Live:
    """The table this process is serving, and the only thing that may replace it.

    Read :attr:`table` once per call and use what you got. The read is a plain
    attribute load, which is atomic, so readers take no lock at all; only a
    change does, and it holds the lock across opening, cloning and swapping so
    that two changes cannot each clone the table the other is about to replace.

    ``directory`` is where a mounted file is looked for, under the same rule
    every mount follows -- relative to the store directory, which is what makes
    a mount configuration relocatable. ``log`` is given to any store opened
    here, so a dynamically mounted store records what it is asked exactly as
    one named on the command line does.

    Used as a context manager by :func:`outrage.server.main`, in place of the
    ``with open_mounts(...) as table:`` it would otherwise use: that would close
    the table it opened, which after a change is no longer the one being
    served, and would close stores the live table still shares.
    """

    def __init__(
        self,
        table: MountedStore,
        *,
        directory: str | os.PathLike[str] | None = None,
        log: EventLog | None = None,
    ) -> None:
        self._table = table
        # Resolved once, here, for the reason `open_mounts` resolves it once:
        # a mount's file and any check made about that file have to agree
        # about where it is, and asking twice is how they come to disagree.
        self._directory = store_module.resolve_directory(directory)
        self._log = log
        self._lock = threading.Lock()

    @property
    def table(self) -> MountedStore:
        """The table as it is now. Read it once, at the start of a call."""
        return self._table

    @property
    def directory(self) -> os.PathLike[str]:
        """The store directory a mounted file is named relative to."""
        return self._directory

    def mount(
        self,
        key: str,
        *,
        file: str | os.PathLike[str] | None = None,
        type: str | None = None,
        extensions: str | None = None,
        read_only: bool = False,
    ) -> Changed:
        """Open a store and mount it at ``key``, replacing whatever is there.

        ``file`` is relative to the store directory, as every mount's file is.
        Omitting it mounts the store **outrage ships** for that key -- today the
        documentation at ``outrage`` and nothing else -- which is the only way
        back for a caller that unmounted the manual, since a tree in
        ``site-packages`` has no spelling as a mount file. A shipped store is
        always mounted read-only: the next upgrade replaces it, so anything
        written there would be lost, and the table the call returns says so.

        ``extensions`` is the mount option of the same name, and only a tree
        has an answer to it -- :data:`~outrage.mounts.EXTENSIONS_OPTION`. It is
        what mounts a documentation bundle whose documents link to each other
        by file name, since ``keep`` makes the key and the file name one
        string. A backend that keeps its store in a file refuses it, as does a
        shipped store, whose tree this package wrote and already reads its own
        way.

        A read-only mount must already exist, the same refusal
        :func:`~outrage.mounts.open_mounts` makes and for the same reason: a
        mistyped name would be *created*, mount as an empty store, and read as
        though the reference base were simply empty, while the flag that was
        supposed to protect it made that impossible to notice by writing.
        """
        prefix = keys.parse(key).key
        with self._lock:
            mount_path = None if file is None else store_file(self._directory, file)
            created = mount_path is not None and not mount_path.exists()
            store = self._opened(prefix, file, type, extensions, read_only)
            # Everything up to the swap is inside this, `open_mounts`'s own
            # shape: a failure anywhere closes what was opened and leaves the
            # live table exactly as it was. Deriving the notes is in here for
            # the same reason -- it reads the new table's stores, so it is a
            # thing that can fail, and failing after the store was opened and
            # before it was served would leak it.
            try:
                after = self._table.remounted(
                    mount={prefix: store},
                    read_only=[prefix] if read_only or file is None else [],
                )
                replaced = prefix in {mount.prefix for mount in self._table}
                notes = notes_for_mount(
                    after,
                    prefix,
                    replaced=replaced,
                    shipped=file is None,
                    created=str(mount_path) if created else None,
                )
            except Exception:
                store.close()
                raise
            return self._swap(after, notes)

    def unmount(self, key: str) -> Changed:
        """Drop the mount at ``key``, and close its store once nothing serves it.

        What the store beneath was holding there comes back into view, which is
        the one consequence a caller is unlikely to have in mind: a mount
        *shadows*, so keys the outer store holds at the mount point have been
        unreachable for as long as it was mounted.
        """
        prefix = keys.parse(key).key
        with self._lock:
            after = self._table.remounted(unmount=[prefix])
            return self._swap(after, notes_for_unmount(after, prefix))

    def close(self) -> None:
        """Close every store the live table holds."""
        self._table.close()

    def __enter__(self) -> Live:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _opened(
        self,
        prefix: str,
        file: str | os.PathLike[str] | None,
        type: str | None,
        extensions: str | None,
        read_only: bool,
    ) -> Store:
        """The store to mount at ``prefix``: a file under the directory, or a shipped one."""
        if file is None:
            opener = SHIPPED.get(prefix)
            if opener is None:
                raise MountError("mount-nothing-shipped", mount=prefix, shipped=sorted(SHIPPED))
            if type is not None:
                raise MountError("mount-shipped-takes-no-type", mount=prefix)
            if extensions is not None:
                raise MountError("mount-shipped-takes-no-extensions", mount=prefix)
            return opener(log=self._log)
        if read_only:
            database = store_file(self._directory, file)
            if not database.exists():
                raise MountError("mount-read-only-missing", mount=prefix, path=str(database))
        return store_module.default_store(
            self._directory,
            filename=file,
            backend=type,
            extensions=extensions,
            log=self._log,
            mount_point=prefix,
        )

    def _swap(self, after: MountedStore, notes: list[Note]) -> Changed:
        """Serve ``after``, and close what no longer has a table to be in.

        By identity, because that is what ownership means here: a store the new
        table shares with the old is still being served, and a store that is in
        neither is this process's to close. Called with the lock held.
        """
        before = self._table
        self._table = after
        serving = {id(mount.store) for mount in after}
        for mount in before:
            if id(mount.store) not in serving:
                mount.store.close()
        return Changed(table=after, notes=tuple(notes))


def notes_for_mount(
    after: MountedStore,
    prefix: str,
    *,
    replaced: bool,
    shipped: bool = False,
    created: str | None = None,
) -> list[Note]:
    """What a mount is worth remarking on, as codes and facts.

    Two of them are about what the caller can no longer see. A mount
    **shadows**: the store that would otherwise own those keys is never
    consulted for them, so a document sitting at the mount point becomes
    unreachable rather than merged -- which the server has warned about on
    stderr at startup since mounts existed, where a tool caller could not read
    it. And a mount at a point something already held has *replaced* it, which
    is the rule a tool call makes unambiguous in a way two configuration
    sources do not.

    ``created`` is the path of a writable store that did not exist before this
    call opened it. Dynamic mounts are an MCP-only operation, so this is the
    one audience that needs the typo warning; startup and command-line mounts
    keep their existing quiet behaviour.

    ``shipped`` is whether this mounted the store outrage ships rather than a
    file, and it changes the last note rather than adding one. A file mount is
    made permanent by writing it into the mount configuration file; the shipped
    tree cannot be written there at all -- having no ``KEY=FILE`` spelling is
    the reason it can be mounted by name -- and needs no entry, because it is
    mounted by default. Telling that caller to write it down named a file they
    could not name.
    """
    notes: list[Note] = []
    if created is not None:
        notes.append(Note("mount-created-store", mount=prefix, path=created))
    if replaced:
        notes.append(Note("mount-replaced-another", mount=prefix))
    if any(mount.prefix == prefix for mount in after.shadowing()):
        notes.append(Note("mount-shadows-keys", mount=prefix))
    # Two appends rather than one with the code chosen inline: `test_notes.py`
    # requires every emit site to name a literal, so that the set of codes a
    # table has to word can be read off the source rather than guessed at.
    if shipped:
        notes.append(Note("remount-shipped-is-default", mount=prefix))
    else:
        notes.append(Note("remount-not-permanent", mount=prefix))
    return notes


def notes_for_unmount(after: MountedStore, prefix: str) -> list[Note]:
    """What an unmount is worth remarking on.

    Asked of the table *after* the change, which is what makes it true: whether
    anything is there now is a question about the store that answers for the
    key now, and the old table's mount is exactly what stopped that store being
    consulted.

    The permanence note is **not** the one a mount gets. Both say the table
    lasts only as long as the server, which is the fact; what follows from it
    is the opposite instruction, and for a while this shared the mount's, so an
    unmount ended by telling the caller to write the mount they had just
    removed into the configuration file.
    """
    notes: list[Note] = []
    if after.exists(prefix) or after.descendant_count(prefix) > 0:
        notes.append(Note("unmount-revealed-keys", mount=prefix))
    notes.append(Note("unmount-not-permanent", mount=prefix))
    return notes


__all__ = [
    "SHIPPED",
    "Changed",
    "Live",
    "notes_for_mount",
    "notes_for_unmount",
]
