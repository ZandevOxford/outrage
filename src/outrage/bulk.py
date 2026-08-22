"""Whole subtrees, in and out: the streaming walkers, and the file mapping.

The store's own reads are pages, and every one of them is bounded on purpose.
This module holds the callers that legitimately want all of it - a listing of a
level, an export of a subtree, an import of a directory - and gets there the
only way that stays bounded: page internally, yield as each page arrives, and
never hold the collection.

Behaviour rather than argument shaping, so that it can be tested without going
through argparse. ``cli`` prints what these yield and decides nothing.

The file mapping is one rule: **a key segment is a path component, and a
document gets an extension naming its format**. `a/b` stored as markdown is
`a/b.md`, and anything below `a/b` is in the directory `a/b/`, which is why the
extension exists at all - a key is both a document and a container, and a path
cannot be both a file and a directory. Metadata is a segment like any other, so
`a/b/!title` is the file `a/b/!title.md`. Nothing is escaped and nothing is
transformed, which is the arrangement the key grammar was widened for: the
characters a filename can hold are the characters a segment can hold.

A tree is written from the root of the key namespace, not from the key that was
exported, so `outrage export out context/10` writes `out/context/10/...` and
re-imports to where it came from. Grafting it somewhere else is what the
import's key prefix is for.

What this is not is a backup. `updated_at` does not survive the round trip and
neither does anything else the database holds about a document; ``Store.backup``
is the copy that keeps all of it.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from . import keys, messages, store
from .errors import RageError

#: How much of a collection one internal query asks for. The command line reads
#: to the end regardless, so this only decides how many round trips that takes
#: and how much is held at once: large enough to be one query for an ordinary
#: level, small enough that a huge one is never held whole.
PAGE = 200

#: The extension a document is written with, by stored format. Named for the
#: direction it maps in, because the inverse is right below it and a reader
#: reaching for one of the two should not have to check which is which. One
#: entry per member of :data:`outrage.store.FORMATS`, so nothing can be stored
#: that an export cannot name.
EXTENSION_BY_FORMAT = {
    "markdown": ".md",
    "json": ".json",
    "text": ".txt",
    "html": ".html",
}

#: The format a file name declares. Deliberately the inverse of
#: :data:`EXTENSION_BY_FORMAT` and nothing more: the extensions an export
#: writes are the extensions an import strips, so a file named `myfile.py`
#: keeps its name and becomes the key `myfile.py` rather than losing a suffix
#: nothing here put there. That is why there is no `.htm` and no `.text`, close
#: as they are -- an export never writes one, so an import reads it as part of
#: the name. Not to be confused with :data:`outrage.store.FORMATS`, which is what
#: a document may be *stored* as; this is what a file name says it is.
FORMAT_BY_EXTENSION = {
    extension: format for format, extension in EXTENSION_BY_FORMAT.items()
}

#: Segments that are legal keys and impossible file names. `.` and `..` became
#: legal segments when the grammar widened to mirror a filesystem; a path
#: component of `..` does not mirror anything, it climbs out of the directory
#: the caller named.
TRAVERSAL = (".", "..")

#: Leave what is already there and carry on. The default, because a transfer
#: that overwrites by accident cannot be undone from here.
SKIP = "skip"

#: Replace what is already there.
OVERWRITE = "overwrite"

#: Stop the whole transfer at the first collision, having written what came
#: before it. What a caller wants when a collision means the wrong target.
STOP = "stop"

#: What to do about something already there, at the far end.
CONFLICTS = (SKIP, OVERWRITE, STOP)

#: The outcome recorded on a :class:`Transfer`: it crossed.
WROTE = "wrote"

#: Something was already there and ``SKIP`` was asked for.
SKIPPED = "skipped"

#: This one could not cross, and the rest were still tried. ``reason`` says why.
FAILED = "failed"

#: Read and held for a file that is not written yet. A pack cannot report a
#: document as written while it goes -- nothing is written until the whole
#: parquet file is -- and calling it ``wrote`` in the meantime would be a
#: report an interrupted run made untrue. See :func:`pack_tree`.
READ = "read"

#: The collision that ended the run, under ``STOP``. Reported rather than
#: swallowed, so a caller can see where the transfer stopped and why; nothing
#: after it is yielded at all.
STOPPED = "stopped"


class UnmappableError(RageError, ValueError):
    """Raised when a key has no file it can be written to, or a file no key."""


@dataclass(frozen=True, slots=True)
class Transfer:
    """One document crossing the boundary, or not, and why not.

    Yielded per document rather than collected, so that a front end can print
    an export as it happens and an interrupted one has reported exactly what it
    did. ``action`` is what happened to the store or the file tree, and it says
    nothing about a dry run: a caller that wrote nothing knows it, and it is the
    only one that can render the difference honestly.
    """

    action: str
    key: str | None
    path: Path | None
    reason: str | None = None
    characters: int = 0


#: One document as :meth:`outrage.store_parquet.ParquetStore.build` takes it:
#: key, content, the format or None to detect it, and the timestamp or None
#: for now. A tuple rather than a class because it is what a build consumes
#: and nothing holds one for longer than that.
Document = tuple[str, str, str | None, str | None]

#: What a pack's source yields: the report of one document, and the document
#: itself -- or None where there is nothing to pack, which is a symlink or a
#: file that would not read. Paired so a caller can print the walk as it
#: happens while the rows accumulate for a file that is written at the end.
Packable = tuple[Transfer, Document | None]


# -- walking the store ---------------------------------------------------


def levels(opened: store.Store, key: str | None) -> Iterator[store.Entry]:
    """One level, a page at a time, to the end.

    The store pages and the command line does not: a person listing a key wants
    the level, and a listing that stops at an internal page size is the silent
    partial answer this project keeps finding. Streaming is what makes it both
    complete and bounded in memory - and it fails better, since a long listing
    interrupted has already shown its first thousand lines rather than nothing.
    """
    cursor = None
    while True:
        page = opened.list_keys(key, limit=PAGE, cursor=cursor)
        yield from page.items
        if page.next_cursor is None:
            return
        cursor = page.next_cursor


def walk(opened: store.Store, key: str | None) -> Iterator[store.Entry]:
    """Every key below ``key``, depth first.

    Built from repeated ``list_keys`` rather than from ``get_documents``,
    because only ``list_keys`` reports the containers - a key holding nothing
    itself but with documents beneath it does not appear in a subtree read at
    all, and leaving it out of a listing is how its children look parentless.
    It is also the only walk that reports metadata beside the documents, which
    is what an export needs: a survey by title is worth nothing if the export it
    came from left every title behind.
    """
    for entry in levels(opened, key):
        yield entry
        if entry.kind != "metadata":
            yield from walk(opened, entry.key)


# -- the mapping ---------------------------------------------------------


def path_for_key(key: str, format: str | None = None) -> PurePosixPath:
    """The relative path ``key`` is written to, extension included.

    >>> path_for_key("a/b", "markdown"), path_for_key("a/b", "json")
    (PurePosixPath('a/b.md'), PurePosixPath('a/b.json'))
    >>> path_for_key("a/b", "text"), path_for_key("a/b", "html")
    (PurePosixPath('a/b.txt'), PurePosixPath('a/b.html'))
    >>> path_for_key("a/b/!title")
    PurePosixPath('a/b/!title.md')
    """
    parsed = keys.parse(key).key
    if parsed == keys.ROOT:
        # A path is made of segments and the root has none, so its file would
        # be named by the empty stem: `.md`, which is hidden, which an import
        # skips by default. That does not relocate the root document, it drops
        # it. Refused until the naming is settled -- see `planned/root-key` in
        # the rage store, which has the two ways out. The root's *metadata*
        # maps normally, as `!title.md`, so only the document itself is stuck.
        raise UnmappableError("root-has-no-filename")
    segments = parsed.split(keys.DELIMITER)
    for segment in segments:
        if segment in TRAVERSAL:
            raise UnmappableError("key-segment-is-traversal", key=key, segment=segment)
    extension = EXTENSION_BY_FORMAT.get(format or "markdown", EXTENSION_BY_FORMAT["markdown"])
    return PurePosixPath(*segments[:-1], segments[-1] + extension)


def key_for_path(
    relative: PurePosixPath | str, prefix: str | None = None
) -> tuple[str, str | None]:
    """The key a file at ``relative`` imports to, and the format it declares.

    The inverse of ``path_for_key`` for anything an export wrote, and the
    obvious reading of anything else: a name carrying neither extension keeps
    it whole and has its format detected from the content instead.

    >>> key_for_path("a/b.md")
    ('a/b', 'markdown')
    >>> key_for_path("b.json", "a")
    ('a/b', 'json')
    >>> key_for_path("notes.txt"), key_for_path("page.html")
    (('notes', 'text'), ('page', 'html'))
    >>> key_for_path("src/myfile.py")
    ('src/myfile.py', None)
    """
    relative = PurePosixPath(relative)
    stem, extension = os.path.splitext(relative.name)
    format = FORMAT_BY_EXTENSION.get(extension)
    name = stem if format is not None else relative.name

    parts = [*relative.parts[:-1], name]
    # An empty prefix is the root, which prefixes nothing. Tested rather than
    # left to normalisation, which would tidy `/a` back to `a` and reach the
    # same answer by accident.
    if prefix:
        parts = [prefix, *parts]
    candidate = keys.DELIMITER.join(parts)
    # Parsed without the wildcard, which is the guard as much as the check: a
    # file named `?.md` would otherwise reach `store_document`, where a whole
    # segment of `?` means "allocate me a number" and the import would invent
    # keys rather than mirror the directory.
    return keys.parse(candidate).key, format


# -- out of the store ----------------------------------------------------


def export_tree(
    opened: store.Store,
    key: str | None,
    target: str | os.PathLike[str],
    *,
    on_conflict: str = SKIP,
    dry_run: bool = False,
) -> Iterator[Transfer]:
    """Write every document at and below ``key`` into ``target``, one per file.

    Yields a ``Transfer`` per document as it goes. Nothing already in ``target``
    is replaced unless ``on_conflict`` says so, because the directory belongs to
    the caller rather than to the store: an export into a working directory is
    otherwise a way to lose work that was never in the store to begin with.
    """
    _check_conflict(on_conflict)
    target = Path(target).expanduser()
    written: set[Path] = set()

    for stored, format in _exported(opened, key):
        try:
            path = target / path_for_key(stored, format)
        except UnmappableError as exc:
            # `reason` is report text, like "already there" beside it, so it is
            # rendered here. The default namer is the right one: bulk transfer
            # is a command line operation over one store directory, and there
            # is no mount table for a key to be named against.
            yield Transfer(FAILED, stored, None, messages.render(exc))
            continue

        if path in written or path.exists() or path.is_symlink():
            reason = "already there" if path not in written else "two keys, one path"
            if on_conflict == STOP:
                yield Transfer(STOPPED, stored, path, reason)
                return
            if on_conflict == SKIP:
                yield Transfer(SKIPPED, stored, path, reason)
                continue

        try:
            excerpt = store.read_all(opened, stored)
        except RageError as exc:
            # A key can go between the listing and the read; the walk is not a
            # snapshot and nothing here pretends it is.
            yield Transfer(FAILED, stored, path, messages.render(exc))
            continue

        if not dry_run:
            try:
                _write_file(path, excerpt.content)
            except OSError as exc:
                yield Transfer(FAILED, stored, path, str(exc))
                continue
        written.add(path)
        yield Transfer(WROTE, stored, path, characters=len(excerpt.content))


def _exported(opened: store.Store, key: str | None) -> Iterator[tuple[str, str | None]]:
    """Every key an export covers: the one asked for, then everything below it.

    ``walk`` lists what is *below* a key, which is what a listing wants and not
    what an export does - a key is a document and a container at once, and
    exporting `project` without the document stored at `project` is the silent
    partial answer wearing an export's clothes. Read at one character, so that
    asking whether it is there costs no more than asking.

    Containers are dropped here rather than in the walk: one holds nothing to
    write, its directory arrives with the first document beneath it, and an
    empty directory says something about the store that is not true.
    """
    # The root is included like any other key: `None` names it rather than
    # meaning "no key at all", so a store that titles itself is exported with
    # its title. Whether the root *document* can be written to a file is a
    # separate question, and `path_for_key` is where it is answered.
    try:
        root = opened.retrieve_document(keys.ROOT if key is None else key, max_chars=1)
    except store.KeyNotFoundError:
        pass
    else:
        yield root.key, root.format
    for entry in walk(opened, key):
        if entry.kind != "implicit":
            yield entry.key, entry.format


def _write_file(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` through a temporary file in the same directory.

    So that an export interrupted halfway leaves whole files and no half of
    one - the same reason the configuration writer does it, for the same kind
    of file: one somebody else owns.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=".outrage-", suffix=".tmp", delete=False
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(content)
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


# -- into the store ------------------------------------------------------


class SourceMissingError(RageError, FileNotFoundError):
    """Raised when the directory to import from is not there."""


def import_tree(
    opened: store.Store,
    source: str | os.PathLike[str],
    key: str | None = None,
    *,
    on_conflict: str = SKIP,
    dry_run: bool = False,
    hidden: bool = False,
) -> Iterator[Transfer]:
    """Store every file below ``source``, keyed by its path under ``key``.

    Yields a ``Transfer`` per file as it goes. ``on_conflict`` decides what
    happens to a key that already holds something, one key at a time: ``stop``
    is the strictest available and stops at the first, having kept what it
    already wrote. There is deliberately no mode that refuses the whole import
    unless every key is free - a directory could be walked twice to promise
    that, but a source that is a stream cannot be, and a guarantee that
    quietly weakens when the source changes is worse than one never offered.
    ``--dry-run`` is what answers the question that mode was reaching for.
    """
    _check_conflict(on_conflict)
    source = Path(source).expanduser()
    if not source.is_dir():
        raise SourceMissingError("import-source-missing", source=str(source))
    seen: set[str] = set()

    for path, kind in _entries(source, hidden=hidden):
        relative = PurePosixPath(path.relative_to(source).as_posix())
        if kind == "symlink":
            # Not followed, in either sense: a link out of the tree imports
            # something the caller did not name, and a link back into it
            # imports the same documents twice under two keys.
            yield Transfer(SKIPPED, None, path, "symlink")
            continue
        try:
            stored, format = key_for_path(relative, key)
        except keys.InvalidKeyError as exc:
            yield Transfer(FAILED, None, path, messages.render(exc))
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            # The store holds text. A file that is not text is reported rather
            # than mangled into it, and the run carries on around it.
            yield Transfer(FAILED, stored, path, str(exc))
            continue

        if stored in seen or opened.exists(stored):
            reason = "two files, one key" if stored in seen else "already stored"
            if on_conflict == STOP:
                yield Transfer(STOPPED, stored, path, reason)
                return
            if on_conflict == SKIP:
                yield Transfer(SKIPPED, stored, path, reason)
                continue

        if not dry_run:
            opened.store_document(stored, content, format)
        seen.add(stored)
        yield Transfer(WROTE, stored, path, characters=len(content))


def _entries(root: Path, *, hidden: bool) -> Iterator[tuple[Path, str]]:
    """Every file below ``root``, in name order, with symlinks named not followed.

    Sorted so that two runs over the same tree report in the same order and a
    diff of two reports is about the trees rather than about the readdir order
    the filesystem happened to hand back. Directories are descended where their
    name falls.
    """
    for entry in sorted(root.iterdir(), key=lambda path: path.name):
        if not hidden and entry.name.startswith("."):
            continue
        if entry.is_symlink():
            yield entry, "symlink"
        elif entry.is_dir():
            yield from _entries(entry, hidden=hidden)
        elif entry.is_file():
            yield entry, "file"


# -- into a file that is written whole -----------------------------------


def documents_from_tree(
    source: str | os.PathLike[str],
    key: str | None = None,
    *,
    hidden: bool = False,
) -> Iterator[Packable]:
    """Every file below ``source`` as a document, beside the report of it.

    The same walk, mapping and refusals :func:`import_tree` makes -- one path
    to a key, symlinks named and not followed, a file that is not text reported
    rather than mangled -- so a tree packs to exactly the keys importing it
    would have produced. Shared by walking the same helpers rather than by
    calling ``import_tree``, which needs a store to write to and this does not.

    Yields the ``Transfer`` first so a caller can report as it reads, and the
    row second, or None when there is nothing to pack. ``updated_at`` is None:
    a file's modification time is not the store's timestamp for the document,
    and inventing one at build time is the honest answer -- see
    :meth:`outrage.store_parquet.ParquetStore.build`.
    """
    source = Path(source).expanduser()
    if not source.is_dir():
        raise SourceMissingError("import-source-missing", source=str(source))

    for path, kind in _entries(source, hidden=hidden):
        relative = PurePosixPath(path.relative_to(source).as_posix())
        if kind == "symlink":
            yield Transfer(SKIPPED, None, path, "symlink"), None
            continue
        try:
            stored, format = key_for_path(relative, key)
        except keys.InvalidKeyError as exc:
            yield Transfer(FAILED, None, path, messages.render(exc)), None
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            yield Transfer(FAILED, stored, path, str(exc)), None
            continue
        yield (
            Transfer(READ, stored, path, characters=len(content)),
            (stored, content, format, None),
        )


def documents_from_store(
    opened: store.Store, key: str | None = None
) -> Iterator[Packable]:
    """Every document at and below ``key`` in ``opened``, beside the report.

    The other half of a pack, and the one a reference base is usually made
    with: accumulate into a writable store, then compact. Built on the same
    walk an export uses, so metadata comes across as the rows it is -- a
    ``!title`` is a key like any other here, and a packed store surveys exactly
    as the one it came from did. An export that left every title behind would
    make the survey worthless, and so would a pack.

    Timestamps come across too, which is what makes this a compaction rather
    than a copy that quietly restamps the corpus.
    """
    for stored, _ in _exported(opened, key):
        whole = store.read_all(opened, stored)
        yield (
            Transfer(READ, stored, None, characters=whole.total),
            (stored, whole.content, whole.format, whole.updated_at),
        )


def pack(
    target: str | os.PathLike[str],
    documents: Iterator[Packable],
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> Iterator[Transfer]:
    """Report each document as it is read, then write them all as one file.

    **The write is at the end, and that is the shape of the format rather than
    a choice.** A parquet store is sorted by key on the way in and its
    statistics describe the whole of it, so there is no point at which half a
    file is a usable store. So this reports ``read`` per document, not
    ``wrote``: an interrupted pack has written nothing, and a report claiming
    otherwise would be the kind of half-truth ``import_tree`` streams
    specifically to avoid.

    Nothing is skipped for collisions the way an import is. There is nothing to
    collide with -- the target is a new file, refused outright if it is already
    there unless ``overwrite`` -- and two source documents claiming one key is
    resolved by the last one, which is what overwriting means everywhere else.
    """
    from .store_parquet import ParquetStore

    # Before a single document is read. A pack reads its whole source before
    # writing anything, so checking at the write would refuse only after the
    # reading was done - right answer, least useful moment.
    ParquetStore.check_target(target, overwrite=overwrite)

    rows: list[Document] = []
    for transfer, row in documents:
        if row is not None:
            rows.append(row)
        yield transfer

    if not dry_run:
        ParquetStore.build(target, rows, overwrite=overwrite)


def _check_conflict(on_conflict: str) -> None:
    if on_conflict not in CONFLICTS:
        raise ValueError(f"on_conflict must be one of {CONFLICTS}, got {on_conflict!r}")


__all__ = [
    "CONFLICTS",
    "Document",
    "EXTENSION_BY_FORMAT",
    "FAILED",
    "FORMAT_BY_EXTENSION",
    "OVERWRITE",
    "PAGE",
    "Packable",
    "READ",
    "SKIP",
    "SKIPPED",
    "STOP",
    "STOPPED",
    "TRAVERSAL",
    "WROTE",
    "SourceMissingError",
    "Transfer",
    "UnmappableError",
    "documents_from_store",
    "documents_from_tree",
    "export_tree",
    "import_tree",
    "pack",
    "key_for_path",
    "levels",
    "path_for_key",
    "walk",
]
