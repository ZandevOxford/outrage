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
neither does anything else the database holds about a document; ``FileStore.backup``
is the copy that keeps all of it.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator, Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from . import keys, messages, store
from .errors import OutrageError
from .store import (
    CONFLICTS,
    FAILED,
    READ,
    SKIP,
    SKIPPED,
    STOP,
    STOPPED,
    WROTE,
    Transfer,
)

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

#: What a half-written file is called while it is being written. Named rather
#: than spelled inline because a store that *reads* a tree has to skip one:
#: :func:`_write_file` finishes with ``os.replace``, so the temporary is only
#: ever seen by a reader looking at the same directory at the same moment, and
#: a reader that took it for a document would report a key nothing wrote.
TEMP_PREFIX = ".outrage-"

#: Segments that are legal keys and impossible file names. `.` and `..` became
#: legal segments when the grammar widened to mirror a filesystem; a path
#: component of `..` does not mirror anything, it climbs out of the directory
#: the caller named.
TRAVERSAL = (".", "..")

class UnmappableError(OutrageError, ValueError):
    """Raised when a key has no file it can be written to, or a file no key."""


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

    **It descends into a metadata entry too**, because a ``!`` segment opens a
    namespace and there may be documents inside it. It used to stop at one, on
    the reading that metadata was a leaf; an export then dropped ``a/!x/y``
    without saying so. The shape on disk is the ordinary
    document-with-children one -- ``!x.md`` beside the directory ``!x/`` --
    which is what ``FilesystemStore`` already writes.
    """
    for entry in levels(opened, key):
        yield entry
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
    extension = EXTENSION_BY_FORMAT.get(format or "markdown", EXTENSION_BY_FORMAT["markdown"])
    if parsed == keys.ROOT:
        # The mapping's own answer, taken rather than refused: a path is made
        # of segments and the root has none, so its file is named by the empty
        # stem -- `.md` at the top of the tree. No key has an empty last
        # segment, so it collides with nothing. It is hidden, which is a
        # question for what *reads* a tree and not for the mapping: an import's
        # dotfile skip is a policy for foreign trees, and it makes an exception
        # for this one file. See `planned/root-key`.
        return PurePosixPath(extension)
    segments = parsed.split(keys.DELIMITER)
    for segment in segments:
        if segment in TRAVERSAL:
            raise UnmappableError("key-segment-is-traversal", key=key, segment=segment)
    return PurePosixPath(*segments[:-1], segments[-1] + extension)


def contained_path(root: str | os.PathLike[str], relative: PurePosixPath, key: str) -> Path:
    """``root / relative``, refused unless it stays inside ``root``.

    **The guard on the join, rather than on the segments.** A segment of `..`
    is refused by :func:`path_for_key` and gives a good sentence when it is,
    but it was never the whole of the question: the traversal that is
    reachable today is in the *target tree* rather than in the namespace, a
    symlinked directory anywhere along the path being enough to write through
    it. Resolving the joined path and requiring containment catches that, and
    the two Windows cases beside it -- a segment holding a backslash, which
    re-parses into components off a Windows path, and one holding a colon,
    which becomes a drive and drops the target from the path entirely --
    without enumerating what a component may look like on any platform.

    :func:`os.path.realpath` rather than :meth:`Path.resolve`, for the strict
    reading of a path that does not exist yet: the file being written is
    usually the part that is missing, and it is the *directories* above it that
    a link can redirect.

    See ``project/reference/planned/export-traversal``, which is the whole
    analysis and says which of these are reachable where.
    """
    inside = Path(os.path.realpath(root))
    candidate = Path(root) / relative
    if not Path(os.path.realpath(candidate)).is_relative_to(inside):
        raise UnmappableError("key-escapes-tree", key=key, path=str(candidate))
    return candidate


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
    if len(relative.parts) == 1 and relative.name in FORMAT_BY_EXTENSION:
        # The root document, which is the one file named by an extension alone
        # -- `path_for_key` writes it there. Only at the top of the tree: a
        # `.md` further down would be the document of a key with an empty last
        # segment, and there is no such key, so it falls through and is read as
        # a name like any other leading-dot name.
        return (prefix or keys.ROOT), FORMAT_BY_EXTENSION[relative.name]
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


# -- store to store ------------------------------------------------------


class OverlappingCopyError(OutrageError, ValueError):
    """Raised when a copy would write into the subtree it is still reading."""


def overlapping(source: str, target: str, *, reroot: bool = False) -> None:
    """Refuse a source and target pair a copy cannot safely stream between.

    :func:`copied` walks the source live rather than snapshotting it, so a
    document landing inside the selection can be found by the walk that is
    still running and copied a second time. Which landings those are depends
    on the spelling, and the two are not symmetrical:

    * **grafted**, every key lands beneath ``target`` *and* its own source key,
      so the landing zone is inside the selection exactly when ``target`` is at
      or below ``source``. The other direction is safe and shipped:
      ``copy a/b a`` writes ``a/a/b/...``, which the walk of ``a/b`` never
      reaches. ``context/68/decisions`` 1 is the decision not to widen the rule
      to cover it.
    * **re-rooted**, the source key is stripped, so every key lands beneath
      ``target`` alone and the two subtrees have to be disjoint. ``a/b``
      re-rooted onto ``a`` sends ``a/b/b/x`` to ``a/b/x`` -- back inside the
      walk it came from, and later in the order than the key being read.

    Called by a front end before the copy starts, so that the refusal is a
    refusal rather than an exception raised out of a generator half way
    through. Both front ends call this one, because the command line and the
    server disagreeing about which copies are allowed is exactly the split
    ``mounts.toml`` was made to avoid.
    """
    if keys.strip_prefix(source, target) is not None:
        raise OverlappingCopyError("copy-target-inside-source", source=source, target=target)
    if reroot and keys.strip_prefix(target, source) is not None:
        raise OverlappingCopyError("copy-source-inside-target", source=source, target=target)


def copied(
    source: store.Store,
    target: store.Store,
    subtree: store.BoundedSubtree = store.EVERYTHING,
    *,
    key_range: store.KeyRange = store.UNBOUNDED,
    prefix: str | None = None,
    reroot: bool = False,
    on_conflict: str = SKIP,
    dry_run: bool = False,
    cursor: str | None = None,
    limit: int | None = None,
) -> Generator[Transfer, None, str | None]:
    """Every document ``subtree`` names, from one store into another.

    What :meth:`outrage.store.Store.copy_from` does unless a backend has a
    better way, and it is called through that rather than directly: a caller
    naming both ends in one breath cannot be overridden by the end that knows
    how it is written. Here because the walk is here -- a store's own reads
    are pages and this is the caller that legitimately wants all of them.

    Read with :func:`outrage.store.read_all` rather than through
    ``get_documents``, for the reason ``context/11/decisions`` settled: a
    subtree read selects documents *or* named metadata, so there is no "all of
    it, metadata included" read, and a copy missing every ``!title`` leaves a
    store nothing can be surveyed by. One read per document is what
    completeness costs.

    A collision is decided on the key at the far end, by asking the target,
    which is the only thing that knows -- and the answer a *tree* gives is
    about the key rather than about one spelling of its file, so a document
    already there as ``a.md`` collides with one arriving as json.

    ``reroot`` decides which of the two spellings ``prefix`` means, and the
    difference is what a caller moving a subtree needs: grafted, every key
    keeps its own name beneath the prefix, so ``a/b`` copied to ``tmp`` lands
    at ``tmp/a/b``; re-rooted, the subtree's own key is stripped first and it
    lands *at* ``tmp``. Both are wanted -- an archive keeps the whole key on
    purpose -- but only the second can say "these documents now live at
    another key", and without it no copy can express a move at all. See
    :func:`overlapping`, which is why the safe pairs differ between them.

    ``limit`` and ``cursor`` are how a copy too large for one call is taken in
    pieces, and they are the pair a *front end* needs rather than a person at a
    terminal: the command line reads to the end and prints as it goes. At most
    ``limit`` documents cross, and the generator **returns** the source key of
    the last one -- the resume cursor, None when the selection ran out and
    there is nothing left to resume from. Returned rather than yielded because
    it is a fact about the run and not a transfer, and because it is a *source*
    key: a ``Transfer`` carries the key written, which under a prefix or a
    reroot is not the key to come back with.

    The stop is decided before the write, not after it, so a run stopped by
    ``limit`` has copied exactly that many documents and the next call starts
    where this one stopped rather than a document past it. ``cursor`` is what
    it costs: the walk is filtered rather than sought, as every bound here is,
    so resuming re-lists the keys already crossed. It does not re-read them,
    which is where the expense in a copy is.
    """
    _check_conflict(on_conflict)

    # What re-rooting strips: the key the copy is *about*, so that what crosses
    # lands at ``prefix`` rather than beneath its whole source key. The root
    # strips nothing, which is why grafting needs no second branch here.
    inner = keys.parse(subtree.key).key if reroot and subtree.key is not None else keys.ROOT

    crossed: str | None = None
    counted = 0
    for key, format in _selected(source, subtree, key_range, cursor):
        if limit is not None and counted >= limit:
            # Stopped in front of a key rather than after it, so the count is
            # the limit exactly and `crossed` names a document that really did.
            return crossed
        counted += 1
        crossed = key
        landed = _grafted(key, prefix, inner=inner)
        path = target.located(landed, format) or source.located(key, format)

        if target.exists(landed):
            if on_conflict == STOP:
                yield Transfer(STOPPED, landed, path, "already stored")
                # Nothing after the collision crosses, so there is nothing to
                # resume: a caller that wants the rest asks for it differently.
                return None
            if on_conflict == SKIP:
                yield Transfer(SKIPPED, landed, path, "already stored")
                continue

        try:
            excerpt = store.read_all(source, key)
        except (OutrageError, OSError) as exc:
            # A key can go between the listing and the read; the walk is not a
            # snapshot and nothing here pretends it is.
            yield Transfer(FAILED, landed, path, _reason(exc))
            continue

        if not dry_run:
            try:
                target.store_document(
                    landed, excerpt.content, excerpt.format, updated_at=excerpt.updated_at
                )
            except (OutrageError, OSError) as exc:
                # A key the far end cannot hold -- a segment no path can spell,
                # a link where a file has to go, a store that refuses writes --
                # fails on its own and the rest are still tried, which is what
                # every transfer here does. ``OSError`` beside the store's own
                # refusals because one end may be a directory of files, and
                # "a plain file is in the way of this key's directory" is the
                # far end answering rather than this one breaking.
                yield Transfer(FAILED, landed, path, _reason(exc))
                continue
        yield Transfer(
            READ if target.writes_deferred else WROTE,
            landed,
            path,
            characters=len(excerpt.content),
        )
    return None


def _reason(exc: OutrageError | OSError) -> str:
    """What to print beside a failed transfer, from either kind of refusal.

    A store's own refusal has a written sentence and a code;
    :func:`outrage.messages.render` is what turns one into report text. An
    ``OSError`` has only what the operating system said, which is the honest
    thing to pass on rather than dress up.
    """
    return messages.render(exc) if isinstance(exc, OutrageError) else str(exc)


def _grafted(key: str, prefix: str | None, *, inner: str = keys.ROOT) -> str:
    """``key`` as it is spelled beneath ``prefix``, or unchanged without one.

    An empty prefix is the root, which prefixes nothing, and is tested rather
    than left to normalisation: joining it would spell a leading delimiter and
    reach the same answer by tidying up after itself.

    ``inner`` is the key the copy was scoped at, and it is stripped before the
    graft: that is the re-rooting spelling, where ``a/b`` copied to ``tmp``
    lands at ``tmp`` and ``a/b/one`` at ``tmp/one``. The root is the default
    and strips nothing, so grafting the whole source key -- an archive, a
    backup, the contract :meth:`outrage.store.Store.copy_from` has always had --
    is this same call with nothing named.
    """
    relative = keys.strip_prefix(inner, key)
    # None where the key is not below the scope at all, which a selection
    # cannot produce; unchanged rather than guessed if one ever does.
    if relative is not None:
        key = relative
    if not prefix or prefix == keys.ROOT:
        return key
    return keys.with_prefix(keys.parse(prefix).key, key)


def _selected(
    opened: store.Store,
    subtree: store.BoundedSubtree,
    key_range: store.KeyRange,
    cursor: str | None = None,
) -> Iterator[tuple[str, str | None]]:
    """The keys a transfer covers: the one asked for, then everything below it.

    ``walk`` lists what is *below* a key, which is what a listing wants and not
    what a copy does - a key is a document and a container at once, and copying
    `project` without the document stored at `project` is the silent partial
    answer wearing a transfer's clothes. Read at one character, so that asking
    whether it is there costs no more than asking.

    **A key holding nothing itself is dropped by its size rather than by its
    kind**, which is the one thing this does not share with :func:`_exported`.
    An implicit container holds nothing, and so does a *mount point* whose
    store has no root document - and a mount point is not implicit, it is a
    key of its own kind. Going by kind alone would report every empty mount as
    a document that failed to read, which is a copy inventing a fault out of a
    table's shape.

    The two bounds are filtered over the walk rather than pushed into it,
    because the walk is ``list_keys`` all the way down and a level listing
    takes neither - which is exactly why it reports the containers and the
    metadata that a subtree read does not. ``cursor`` is filtered the same way
    and for the same reason, which is what makes resuming cost a re-listing of
    what was already crossed rather than nothing.
    """
    inside = store._within(key_range)
    # A cursor is a bound like any other, and deliberately not one of the six:
    # the cuts are the selection and this is where the reader had got to, which
    # is the distinction ``KeyRange``'s own docstring draws. ``after`` is what
    # it means -- past that key, its children included -- and an absent cursor
    # is an unbounded range, so there is no branch to take here.
    resumed = store._within(store.KeyRange(after=cursor))
    scope = keys.ROOT if subtree.key is None else keys.parse(subtree.key).key
    try:
        # The key asked for is included like any other: `None` names the root
        # rather than meaning "no key at all", so a store that titles itself is
        # copied with its title.
        root = opened.retrieve_document(scope, max_chars=1)
    except store.KeyNotFoundError:
        pass
    else:
        position = keys.sort_form(root.key)
        if inside(position) and resumed(position):
            yield root.key, root.format

    for entry in walk(opened, subtree.key):
        if entry.size is None:
            continue
        if subtree.depth is not None and keys.depth(entry.key) - keys.depth(scope) > subtree.depth:
            continue
        position = keys.sort_form(entry.key)
        if inside(position) and resumed(position):
            yield entry.key, entry.format


def export_tree(
    opened: store.Store,
    key: str | None,
    target: str | os.PathLike[str],
    *,
    on_conflict: str = SKIP,
    dry_run: bool = False,
) -> Iterator[Transfer]:
    """Write every document at and below ``key`` into ``target``, one per file.

    A copy into a directory of files, which is what an export always was: the
    mapping it is written by is :class:`~outrage.store_files.FilesystemStore`'s
    now, so this is where the target directory becomes a store and nothing
    more. Yields a ``Transfer`` per document as it goes.

    Nothing already in ``target`` is replaced unless ``on_conflict`` says so,
    because the directory belongs to the caller rather than to the store: an
    export into a working directory is otherwise a way to lose work that was
    never in the store to begin with. What is already there is decided **by
    key** rather than by one spelling of its file, so a document held as
    ``a.md`` collides with one arriving as json.

    ``FilesystemStore`` is imported here rather than at the top of the module
    because it is written in terms of this one -- the mapping lives here and
    the store is expressed in it, not the other way round.
    """
    from .store_files import FilesystemStore

    # A dry run must leave no directory behind: it reports what an export
    # *would* do, and creating the target is doing some of it.
    with FilesystemStore(Path(target).expanduser(), create=not dry_run) as tree:
        yield from tree.copy_from(
            opened,
            store.BoundedSubtree(key),
            on_conflict=on_conflict,
            dry_run=dry_run,
        )


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
        "w", encoding="utf-8", dir=path.parent, prefix=TEMP_PREFIX, suffix=".tmp", delete=False
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


class SourceMissingError(OutrageError, FileNotFoundError):
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

    The inverse of :func:`export_tree` and the same operation: a copy *out of*
    a directory of files into a store. Yields a ``Transfer`` per file as it
    goes.

    ``hidden`` is whether a dotfile is a document. False by default, which is
    the policy for a **foreign** tree -- one this package did not write, where
    a ``.git`` or a ``.DS_Store`` is not a document and importing it as one is
    a surprise. The root document is exempt either way, since it is named by
    its extension alone.

    What the tree does not hold as a document does not cross and is not
    reported: a symlink, a half-written file, a name that is not a key, and the
    second file claiming a key two of them claim. ``outrage check`` over the
    tree is what names those, because deciding what a directory holds is the
    store's question rather than the transfer's.

    ``on_conflict`` decides what happens to a key that already holds something,
    one key at a time: ``stop`` is the strictest available and stops at the
    first, having kept what it already wrote. There is deliberately no mode
    that refuses the whole import unless every key is free - a directory could
    be walked twice to promise that, but a source that is a stream cannot be,
    and a guarantee that quietly weakens when the source changes is worse than
    one never offered. ``--dry-run`` is what answers the question that mode was
    reaching for.
    """
    from .store_files import FilesystemStore

    source = Path(source).expanduser()
    if not source.is_dir():
        # Before a store is opened over it, because opening one *makes* the
        # directory: an import from a mistyped path would otherwise succeed at
        # importing nothing and leave the mistake behind as a new empty tree.
        raise SourceMissingError("import-source-missing", source=str(source))

    with FilesystemStore(source, hidden=hidden, create=False) as tree:
        yield from opened.copy_from(
            tree, prefix=key, on_conflict=on_conflict, dry_run=dry_run
        )


def _entries(root: Path, *, hidden: bool, top: bool = True) -> Iterator[tuple[Path, str]]:
    """Every file below ``root``, in name order, with symlinks named not followed.

    Sorted so that two runs over the same tree report in the same order and a
    diff of two reports is about the trees rather than about the readdir order
    the filesystem happened to hand back. Directories are descended where their
    name falls.

    **The dotfile skip makes one exception**, and it is the root document. The
    mapping names it by its extension alone -- `.md` at the top of the tree --
    so skipping it would drop a document this package's own export wrote, which
    is not a policy about foreign trees but a hole in the round trip. Only at
    the top, where that file is, and only for a name that is exactly an
    extension, which is why ``top`` is tracked rather than inferred from the
    name.
    """
    for entry in sorted(root.iterdir(), key=lambda path: path.name):
        skipped = entry.name.startswith(".") and not (top and entry.name in FORMAT_BY_EXTENSION)
        if not hidden and skipped:
            continue
        if entry.is_symlink():
            yield entry, "symlink"
        elif entry.is_dir():
            yield from _entries(entry, hidden=hidden, top=False)
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


# -- one document, to a file and back ------------------------------------
#
# The single-document half of the same mapping the tree walkers use, for the
# document that is edited by shell tools rather than moved in bulk: a read that
# writes a file and a write that reads one, sharing every rule above about what
# a key is called on disk. See ``context/66/decisions``.


#: The mapping failures a single-document export answers with a random name
#: instead of a refusal, and exactly those: a key that cannot be a path is
#: still a key somebody wants to edit, and there is nowhere else for it to go.
#: Anything else :func:`path_for_key` or :func:`contained_path` raises is a
#: refusal, and stays one.
UNNAMEABLE = ("key-segment-is-traversal", "key-escapes-tree")

#: What a key with no path of its own is named instead. Not
#: :data:`TEMP_PREFIX`, which marks a file that is half written and that a
#: reader must skip: this one is the export, and it is finished.
FALLBACK_PREFIX = "document-"


class FileMissingError(OutrageError, FileNotFoundError):
    """Raised when the file to import one document from is not there."""


@dataclass(frozen=True, slots=True)
class Exported:
    """What exporting one document did: where it went, and what stood there."""

    path: Path
    """The file written."""
    excerpt: store.Excerpt
    """The document written to it, whole."""
    replaced: bool
    """Whether a file was already at that path. A fact, not a refusal:
    overwriting on re-export is the point of a deterministic name, and the case
    it costs is an edit that had not been imported back yet. See
    ``context/66/decisions``, call 1."""


@dataclass(frozen=True, slots=True)
class Imported:
    """What importing one file did: where it went, and what it displaced."""

    key: str
    """The key written, as it was asked for."""
    stored: int
    """Characters written."""
    previous: int | None
    """Characters the key held before, or None if it held nothing. The
    distinction is kept because an empty document and no document are different
    things to have overwritten."""


def file_for_key(
    root: str | os.PathLike[str], key: str, format: str | None = None
) -> tuple[Path, bool]:
    """The file under ``root`` that ``key`` is exported to, and whether it is the
    key's own.

    The key's own mapped path, so exporting a key twice reuses one file:
    nothing accumulates, and a stale copy of an earlier export cannot be picked
    up by mistake. The cost is taken deliberately - a second export overwrites
    an edit that had not been imported back yet.

    **A key with no path gets a random name here instead**, for the two cases
    in :data:`UNNAMEABLE`. It still carries the format's extension, because
    with the key and the path free to disagree the path is the only thing left
    that says what the content is.

    The root key is not one of those cases: it maps to the extension alone at
    the top of ``root``, which is hidden and valid.

    The flag says which of the two happened, because the answers differ in what
    a caller may say about the file: a mapped path may already hold an earlier
    export, and a fallback never does.
    """
    try:
        return contained_path(root, path_for_key(key, format), key), True
    except UnmappableError as exc:
        if exc.code not in UNNAMEABLE:
            raise
    directory = Path(root)
    directory.mkdir(parents=True, exist_ok=True)
    # `mkstemp` rather than a name of our own, for the guarantee that the name
    # is free: two unnameable keys must not land on one file, which is the one
    # thing a random name is here to avoid.
    handle, named = tempfile.mkstemp(
        dir=directory,
        prefix=FALLBACK_PREFIX,
        suffix=EXTENSION_BY_FORMAT.get(format or "markdown", EXTENSION_BY_FORMAT["markdown"]),
    )
    os.close(handle)
    return Path(named), False


def contained_file(root: str | os.PathLike[str], path: str | os.PathLike[str], key: str) -> Path:
    """``path`` as a file inside ``root``, refused unless it stays inside it.

    The absolute-path end of :func:`contained_path`, which takes a path
    *relative* to the root because that is what a key maps to. An import
    arrives with the absolute path an export handed back, so it is relativised
    and then checked by the one rule - rather than by a second containment
    strategy that could disagree with the first.
    """
    given = Path(path).expanduser()
    if given.is_absolute():
        try:
            # Lexical, and deliberately: whether the result is really inside is
            # `contained_path`'s question, answered against the filesystem, and
            # a `..` this produces is exactly what it is there to refuse.
            relative = PurePosixPath(os.path.relpath(given, Path(root)))
        except ValueError as exc:
            # A different drive on Windows, where there is no relative path at
            # all. Not inside the root, which is the answer either way.
            raise UnmappableError("import-file-escapes-tree", key=key, path=str(given)) from exc
    else:
        relative = PurePosixPath(given)
    try:
        return contained_path(root, relative, key)
    except UnmappableError as exc:
        if exc.code != "key-escapes-tree":
            raise
        # The same containment rule and the other direction. `key-escapes-tree`
        # says a key would be *written* somewhere it should not be, which is
        # the wrong half of the story for a caller who asked to read a file.
        raise UnmappableError("import-file-escapes-tree", key=key, path=str(given)) from exc


def export_document(
    opened: store.Store, key: str, root: str | os.PathLike[str]
) -> Exported:
    """Write the document at ``key`` to its file under ``root``, whole.

    The whole document rather than a slice, which is the only readable size: a
    slice edited and imported back is a silent truncation of everything the
    read stopped short of.
    """
    excerpt = store.read_all(opened, key)
    path, mapped = file_for_key(root, key, excerpt.format)
    # Asked before the write, which is the only moment it can be asked:
    # `_write_file` replaces, and afterwards the file is there either way. Only
    # of a mapped path -- a fallback name is allocated by creating the file, so
    # the file being there says nothing about what was.
    replaced = mapped and path.exists()
    _write_file(path, excerpt.content)
    return Exported(path=path, excerpt=excerpt, replaced=replaced)


def import_document(
    opened: store.Store, key: str, path: str | os.PathLike[str], root: str | os.PathLike[str]
) -> Imported:
    """Store the content of ``path`` at ``key``, and say what it displaced.

    ``path`` must be inside ``root``, which is the whole of the check: a tool
    that stored any file the caller named would read anything the server can
    read. See ``project/reference/planned/export-traversal``.

    **A relative ``path`` is relative to ``root``**, not to the working
    directory: it is relativised before it is checked, so the containment rule
    is asked once. ``tmp/1.md`` is a good way to name an export; the same file
    named ``.outrage/export/tmp/1.md`` from the repository root is not.

    **The key and the path do not have to agree.** The content is stored where
    the caller says, whatever file it came from, which is what makes an export,
    an edit and an import to a second key a way of copying content around the
    store.

    An empty file is stored rather than refused - emptying a document is a
    thing a person may legitimately mean. What guards the accident is the
    report: both sizes come back, so an edit script that truncated is visible
    to whoever asked. See ``context/66/decisions``, call 3.
    """
    from .store_files import NotTextError

    file = contained_file(root, path, key)
    try:
        content = file.read_text(encoding="utf-8")
    except (FileNotFoundError, IsADirectoryError) as exc:
        # `given` and `root` beside the joined path, because the two disagree
        # in the case most likely to be got wrong: a relative path is taken
        # from `root`, and the message has to say so to be read correctly.
        raise FileMissingError(
            "import-file-missing",
            key=key,
            path=str(file),
            given=str(path),
            root=str(Path(root)),
        ) from exc
    except UnicodeDecodeError as exc:
        raise NotTextError("files-not-text", key=key, path=str(file)) from exc
    try:
        previous: int | None = opened.retrieve_document(key, max_chars=1).total
    except store.KeyNotFoundError:
        previous = None
    written = opened.store_document(key, content, _format_of(file.name))
    return Imported(key=written, stored=len(content), previous=previous)


def _format_of(name: str) -> str | None:
    """The format a file name declares, for a caller that already has the key.

    The format half of :func:`key_for_path`, split out because an import of one
    document is *told* its key: putting the name through the whole mapping
    would let a file name that is not a key refuse a write to a key that is.
    """
    if name in FORMAT_BY_EXTENSION:
        # The root document, the one file named by its extension alone.
        return FORMAT_BY_EXTENSION[name]
    return FORMAT_BY_EXTENSION.get(os.path.splitext(name)[1])



def _check_conflict(on_conflict: str) -> None:
    if on_conflict not in CONFLICTS:
        raise ValueError(f"on_conflict must be one of {CONFLICTS}, got {on_conflict!r}")


__all__ = [
    "Document",
    "EXTENSION_BY_FORMAT",
    "Exported",
    "FALLBACK_PREFIX",
    "FORMAT_BY_EXTENSION",
    "Imported",
    "PAGE",
    "Packable",
    "TEMP_PREFIX",
    "TRAVERSAL",
    "UNNAMEABLE",
    "FileMissingError",
    "OverlappingCopyError",
    "SourceMissingError",
    "UnmappableError",
    "contained_file",
    "contained_path",
    "copied",
    "documents_from_store",
    "documents_from_tree",
    "export_document",
    "export_tree",
    "file_for_key",
    "import_document",
    "import_tree",
    "pack",
    "key_for_path",
    "levels",
    "overlapping",
    "path_for_key",
    "walk",
]
