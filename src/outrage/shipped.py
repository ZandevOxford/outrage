"""The documentation store that ships inside the package, and where it is.

A read-only store of documents *about outrage* -- what a key is, what the tools
do, the conventions worth following -- mounted at ``outrage`` so that a session
can read them the same way it reads anything else. No second retrieval path, no
second vocabulary: the manual is documents in the namespace.

**Two halves, and only one of them is written by hand.** The documents at the
top of the tree, ``skills/`` among them, are prose, edited in place like any
other file in the repository. ``reference/`` is the API documentation, rendered from the
docstrings in ``src/outrage`` by ``make markdown`` in ``docs/`` and copied in --
one page per module, reached as ``outrage/reference/<module>``. Editing a page
there is editing build output: the change is lost at the next render, and the
source is the docstring.

Nothing in this module knows the difference, and that is on purpose. A
generated page is a file in a directory of files, so it mounts, lists, reads
and is surveyed exactly as the hand-written ones are, and neither
:func:`open_documents` nor the mount has a case for it.

**Why this is its own module.** The tree lives in ``site-packages`` once
installed, and every mount a table opens is a file *relative to* ``--dir`` --
:func:`outrage.store.store_file`, which refuses an absolute path on purpose,
since that rule is what makes a mount configuration relocatable. So this mount
cannot be written as a ``KEY=FILE`` spec at all. It is opened here, by absolute
path, and handed to :func:`outrage.mounts.open_mounts` as an already-opened
store -- see its ``attached`` argument, which is the whole of the mount-system
change this needed.

**The one behaviour to expect.** The mount is ordinary once it is there: it
shadows, it is listed, it takes precedence exactly as any mount at ``outrage``
would, and a mount table naming ``outrage`` overrides it silently by the
ordinary rule that a later source wins. The only thing special about it is that
the server mounts it without being asked and the command line does not --
``--mount-docs``.

**One directory here is delivered, and it is not the readme.** ``skills/``
holds the static text :func:`outrage.server.instructions` sends when a client
connects, as the two documents it is delivered in -- so editing a file there
edits what every session is told, and the budget arithmetic in
:mod:`outrage.server` is what bounds it. The server reads those files directly
rather than through this mount: it needs them at import, and a mount table
naming ``outrage`` would otherwise decide what the server says about itself.

Nothing else here is delivered, the readme included. Only the *root* store's
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
#: files rather than a database, so it is diffable in the repository and
#: shipped by the same wheel rule that already carries ``src/outrage/skills/``
#: -- the packaged agent skill, a different thing from the ``skills/``
#: directory *inside* this tree -- and ``codex/``. Editable without a tool as
#: well -- but of the hand-written half only, and the module docstring says
#: which that is.
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


def open_documents(
    *, log: EventLog | None = None, mount_point: str = MOUNT_POINT
) -> FilesystemStore:
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

    ``mount_point`` defaults to :data:`MOUNT_POINT`, which is where this tree
    goes, and is passed on so that :meth:`~outrage.store.Store._log_key`
    renders an event in the namespace a reader of the log is in. Without it a
    read of ``outrage/readme`` was logged as ``readme``, indistinguishable in
    the log from the root store's own -- a store learns where it was mounted
    for this one purpose and nothing else, and every other mount has always
    said.
    """
    root = tree()
    if not root.is_dir():
        raise DocumentsError("documents-not-installed", path=str(root))
    return FilesystemStore(root, log=log, create=False, mount_point=mount_point)


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
