"""The documentation store that ships inside the package, and where it is.

A read-only store of documents *about outrage* -- what a key is, what the tools
do, the conventions worth following -- mounted at ``outrage`` so that a session
can read them the same way it reads anything else. No second retrieval path, no
second vocabulary: the manual is documents in the namespace.

**Why this is its own module.** The tree lives in ``site-packages`` once
installed, and every mount a table opens is a file *relative to* ``--dir`` --
:func:`outrage.store.store_file`, which refuses an absolute path on purpose,
since that rule is what makes a mount configuration relocatable. So this mount
cannot be written as a ``KEY=FILE`` spec at all. It is opened here, by absolute
path, and handed to :func:`outrage.mounts.open_mounts` as an already-opened
store -- see its ``attached`` argument, which is the whole of the mount-system
change this needed. ``project/reference/planned/mounts/default-store`` in the
outrage store is the argument for all of it.

**The one behaviour to expect.** The mount is ordinary once it is there: it
shadows, it is listed, it takes precedence exactly as any mount at ``outrage``
would, and a mount table naming ``outrage`` overrides it silently by the
ordinary rule that a later source wins. The only thing special about it is that
the server mounts it without being asked and the command line does not --
``--mount-docs``.

**It is not delivered in the server's instructions.** Only the root store's
readme is, on the delivery-budget argument in
:func:`outrage.server.instructions`; this store announces itself as a mount in
a listing and is read on demand. That is deliberate and belongs to the session
bootstrap rather than here.
"""

from __future__ import annotations

from pathlib import Path

from .errors import OutrageError
from .eventlog import EventLog
from .store_files import FilesystemStore

#: Where the shipped documentation is mounted. A single segment, and the
#: project's own name, because the question it answers is "what does outrage
#: itself say about this" -- the same word somebody would type to ask.
MOUNT_POINT = "outrage"

#: The directory inside the installed package holding the tree. A directory of
#: files rather than a database, so it is diffable in the repository, editable
#: without a tool, and shipped by the same wheel rule that already carries
#: ``skills/`` and ``codex/``.
TREE_NAME = "documents"


class DocumentsError(OutrageError, FileNotFoundError):
    """Raised when the shipped documentation is not in the installation."""


def tree() -> Path:
    """The directory the documents are in, whether or not it is there.

    ``__file__``-relative rather than :mod:`importlib.resources`, and for a
    reason worth stating: the store reads and stats real paths, so a resource
    that had to be materialised out of a zip would be a copy with a different
    lifetime. Every supported installation -- an editable checkout, a wheel
    unpacked by pip -- puts the tree on the filesystem beside this module.
    """
    return Path(__file__).resolve().parent / TREE_NAME


def available() -> bool:
    """Whether this installation actually carries the tree.

    A build that dropped it is the failure this exists to notice: 0.1.0 shipped
    without ``src/outrage/skills/`` and nothing said so. ``test_packaging.py``
    is where that is guarded; this is what a front end asks before mounting
    something it was not explicitly told to mount.
    """
    return tree().is_dir()


def open_documents(*, log: EventLog | None = None) -> FilesystemStore:
    """Open the shipped tree, read-only, refusing if it is not there.

    ``create=False``, so this never writes into an installation: a missing tree
    is reported rather than made, which is the same argument
    :func:`outrage.mounts.open_mounts` makes for a read-only mount that names
    nothing. Read-only is enforced by the *mount*, since
    :class:`~outrage.store_files.FilesystemStore` is a writable backend and the
    file permissions of a ``site-packages`` directory are not something to rely
    on.

    ``hidden`` is left at its default: this is a tree outrage wrote, so a
    dotfile in it is a document rather than somebody's ``.DS_Store``.
    """
    root = tree()
    if not root.is_dir():
        raise DocumentsError("documents-not-installed", path=str(root))
    return FilesystemStore(root, log=log, create=False)


def attached(*, log: EventLog | None = None) -> dict[str, FilesystemStore]:
    """The documentation as the ``attached`` argument ``open_mounts`` takes.

    One call rather than two lines repeated in each front end, and the mount
    point is spelled once.
    """
    return {MOUNT_POINT: open_documents(log=log)}


__all__ = [
    "MOUNT_POINT",
    "TREE_NAME",
    "DocumentsError",
    "attached",
    "available",
    "open_documents",
    "tree",
]
