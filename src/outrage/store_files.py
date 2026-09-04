"""A document store that is a directory of files: one key, one file.

The mapping is :mod:`outrage.bulk`'s, unchanged and reused rather than
restated -- a segment is a path component, an extension names the format, so
``a/b`` stored as markdown is the file ``a/b.md`` and everything below ``a/b``
is in the directory ``a/b/``. That mapping already existed as a pair of one-off
tree walkers; this is the same rule expressed as a :class:`~outrage.store.Store`,
so a directory can answer the reading surface that a database answers and every
bulk operation between the two can become a copy.

**Registered in** :data:`outrage.store._BACKENDS` under ``files``, and
**nameable rather than inferable**. Which backend keeps a store otherwise
follows from its file extension, and a tree has no extension to read -- so this
is the backend a mount has to ask for, as ``--mount export=tree,type=files`` or
the ``type`` of an entry in ``mounts.toml``. That is what the option grammar in
:func:`outrage.mounts.parse_spec` exists for.

Two ways in, because there are two kinds of caller.
:meth:`~outrage.store.FileStore.__init__` is overridden to take the tree
itself: an export target is an absolute path somebody typed, and
:func:`outrage.store.store_file` refuses those, correctly, for the store file it
is about. :meth:`FilesystemStore.in_directory` is the other, and it is the
base's rule unchanged -- a mount is a name relative to ``--dir`` like every
other store, and a tree mounted from a table has to obey exactly the refusals
a database mounted beside it obeys.

## What it costs

Every subtree read is a **walk**, per call, with nothing kept between them.
A sorted depth-first descent produces global key order without materialising
the tree, because :func:`outrage.keys.sort_form` is per segment and delimiter
joined, so a parent's sort form prefixes every descendant's: at each directory,
emit the key's own document, then its metadata, then its subkeys, children in
segment order. Ranges, subtrees and cursors are filters over that stream.

It is O(n) per read of a subtree, which is the wrong shape for a large corpus
and the right one for what this backend is for -- an export target, a working
copy, a tree under review. The fix, if a tree ever holds enough to want one, is
a resident index like :attr:`outrage.store_parquet.ParquetStore._index`, not a
second definition of what the order is. The same paragraph is in
:meth:`outrage.store.Store.last_child` for the same reason: a cost worth paying
should be written down where it is paid.

**A character count is not a byte count**, so a page's ``total_chars`` and an
entry's ``size`` are answered by decoding a file rather than by its size on
disk. A walk that has to report either reads what it walks.

## Where it diverges from the contract, deliberately

Three, each covered by a test that says so:

* **``.`` and ``..`` as whole segments are legal keys and impossible paths.**
  They are refused on write, with :class:`~outrage.bulk.UnmappableError`, and
  cannot occur on read.
* **A key that would land outside the tree is refused**, which is the same
  refusal one directory up: see :func:`outrage.bulk.contained_path`.
* **A file holding bytes that are not UTF-8 text is not a document.** The walk
  passes over it and :meth:`FilesystemStore.check_file` reports it; reading it
  by name says so rather than returning something mangled.

Everything else is the contract as ``tests/test_store.py`` states it, including
the root document, which is the file named by its extension alone at the top of
the tree -- ``.md`` -- and closes the export gap ``planned/root-key`` left.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Self

from . import bulk, keys
from .errors import OutrageError
from .eventlog import EventLog
from .maintenance import Problem, Repaired, Report, _listed
from .store import (
    DEFAULT_BULK_MAX_CHARS,
    DEFAULT_MAX_CHARS,
    EVERYTHING,
    UNBOUNDED,
    AuditRow,
    BoundedSubtree,
    Entry,
    Excerpt,
    FileStore,
    KeyNotFoundError,
    KeyRange,
    MissingMeta,
    Page,
    PatternNotFoundError,
    Store,
    _byte_excerpt,
    _cursor_bound,
    _detect_format,
    _excerpt,
    _find_byte_occurrence,
    _find_occurrence,
    _logged,
    _scope,
    _within,
    check_read_position,
    check_unchanged,
    entry_kind,
    meta_reader,
    resolve_directory,
    store_file,
)

#: What a tree is called when a caller names a store directory and no tree
#: inside it, so that ``.outrage/documents/`` sits beside ``.outrage/store.sqlite``
#: the way two store files would. A name rather than the directory itself: the
#: store directory holds shared infrastructure -- the event log, the backups --
#: and a tree that *was* that directory would read them back as documents.
DEFAULT_TREE_NAME = "documents"

#: The version of this layout. The layout **is** the format, so there is no
#: marker in the tree recording it and :attr:`FilesystemStore.stored_format_version`
#: answers with this rather than reading one. See
#: :meth:`FilesystemStore.stored_format_version`.
FORMAT_VERSION = 1


class NotTextError(OutrageError, ValueError):
    """Raised when a file in the tree does not hold UTF-8 text.

    The store holds text. A file that is not text is reported rather than
    mangled into it -- the same answer :func:`outrage.bulk.import_tree` gives
    for the same file, one layer up.
    """


@dataclass(frozen=True, slots=True)
class _Row:
    """One key in the tree, and the file holding it.

    The columns a database keeps beside a document, derived here from the path
    and its stat: ``format`` from the extension, ``updated_at`` from the
    modification time, ``sort_key`` from the key.

    ``chars`` is None when the walk was not asked to measure. Reading a
    document's length means decoding it, and a count and a delete have no use
    for one, so the reads that report sizes ask for them and the reads that do
    not are not made to pay. :func:`_total_chars` is where an unmeasured row
    reaching a total fails loudly rather than counting as nothing.
    """

    key: str
    doc_key: str
    meta_name: str | None
    meta_path: str | None
    format: str | None
    updated_at: str
    sort_key: str
    chars: int | None
    path: Path


class FilesystemStore(FileStore):
    """A document store kept as a directory of files."""

    default_filename = DEFAULT_TREE_NAME
    backend_name = "files"
    format_version = FORMAT_VERSION
    writable = True

    def __init__(
        self,
        root: str | os.PathLike[str] | None = None,
        *,
        log: EventLog | None = None,
        hidden: bool = True,
        create: bool = True,
        mount_point: str | None = None,
    ) -> None:
        """Open the tree at ``root``, creating it if it is not there.

        ``root`` is the tree itself, absolute or relative, rather than a
        directory and a name within it: an export target is a path a person
        typed and :func:`outrage.store.store_file` refuses those, correctly, for
        the store file it is about. Omitted, it is :data:`DEFAULT_TREE_NAME`
        inside the store directory, which is the one case where the base's rule
        does fit.

        ``create`` is whether opening one makes the directory. True, because a
        store a first write can fill has to exist for the write to land in --
        the same reason every other backend creates its file. False is for a
        caller that must not leave a tree behind when it turns out to write
        nothing: a dry run reporting what an export *would* do has no business
        creating the directory it would have written into. A write still makes
        the directories above it either way.

        ``hidden`` is whether a dotfile is a document. True by default, because
        a store reads back what it wrote and the root document is a dotfile.
        False is the policy for a **foreign** tree -- one this package did not
        write -- where a ``.git`` or a ``.DS_Store`` is not a document and
        importing it as one is a surprise. The root document is not affected by
        it either way: it is named by its extension alone, which is the
        mapping's doing rather than an attempt to hide anything.
        """
        Store.__init__(self, log=log, mount_point=mount_point)
        self.root = (
            resolve_directory() / DEFAULT_TREE_NAME if root is None else Path(root).expanduser()
        )
        # The tree *is* the store file, and the directory around it is the one
        # holding it -- so a backup lands beside the tree rather than inside it,
        # where it would read back as documents.
        self.path = self.root
        self.directory = self.root.parent
        self._hidden = hidden
        # Held only while a `?` is allocated. Allocating reads the level and
        # then writes past its highest number, and two threads reading before
        # either writes pick the same one -- which the SQLite backend keeps off
        # with `BEGIN IMMEDIATE` and this has to keep off itself.
        #
        # **Within one process.** A tree has no lock a second process would
        # see, so two of them allocating at once can still collide; a lock file
        # would be a file in the corpus that is not a document, and the tree is
        # the one backend whose contents somebody else is expected to be
        # editing. Said plainly rather than papered over.
        self._allocating = threading.Lock()
        if create:
            self.root.mkdir(parents=True, exist_ok=True)

    def close(self) -> None:
        """Nothing to release: a file is opened per read and closed by it.

        An honest no-op rather than an omission. A caller is entitled to say it
        has finished with a store without knowing which backend it holds.
        """

    # -- the mapping -----------------------------------------------------

    def _path_for(self, key: str, format: str | None) -> Path:
        """Where ``key`` is written, refused if that is not inside the tree.

        Both refusals are :mod:`outrage.bulk`'s, which is the one place the
        mapping lives: a segment that is not a path component, and a joined
        path that leaves the tree.
        """
        return bulk.contained_path(self.root, bulk.path_for_key(key, format), key)

    def _readable(self, key: str, format: str | None) -> Path | None:
        """Where ``key`` would be read from, or None if that is outside the tree.

        The same containment the write path refuses on, as an **answer rather
        than a refusal**. A read has somewhere to put "there is nothing here"
        and a write does not: a key whose path leads out of the tree through a
        link is a key this store does not hold, and raising instead would mean
        a listing that passed over the link quietly disagreeing with an
        ``exists`` that blew up on it.
        """
        try:
            return bulk.contained_path(self.root, bulk.path_for_key(key, format), key)
        except bulk.UnmappableError:
            return None

    def _files_for(self, key: str) -> list[Path]:
        """Every file the tree holds for ``key``, in name order.

        More than one is a corpus that says two things about one key, which
        writing cannot produce -- a write unlinks the others -- and a hand
        edited tree can. The first is what reads, and :meth:`check_file`
        reports the rest.
        """
        candidates = [self._readable(key, format) for format in bulk.EXTENSION_BY_FORMAT]
        candidates.append(self._readable(key, None))
        held = {
            path if path.suffix in bulk.FORMAT_BY_EXTENSION else path.with_suffix("")
            for path in candidates
            if path is not None
        }
        return sorted(
            (path for path in held if path.is_file() and not path.is_symlink()),
            key=lambda path: path.name,
        )

    def _file_for(self, key: str) -> Path | None:
        """The file ``key`` reads from, or None when nothing holds it."""
        found = self._files_for(key)
        return found[0] if found else None

    def located(self, key: str, format: str | None = None) -> Path | None:
        """The file ``key`` is kept in, which for this backend is the store.

        The base answers None, because a row in a database has no file of its
        own. Here every key has one and the mapping is public, so a transfer
        into a tree reports key to path -- which is what an export has always
        printed and the reason :class:`~outrage.store.Transfer` carries a path
        at all.

        The path a write *would* take, whether or not anything is there yet: a
        report of a copy is about where each document lands. None where that
        path would leave the tree, which is :meth:`_readable`'s answer rather
        than a refusal, since a report is not the place to raise.
        """
        return self._readable(key, format)

    def _dir_for(self, key: str) -> Path:
        """The directory holding the keys immediately below ``key``."""
        parsed = keys.parse(key).key
        if parsed == keys.ROOT:
            return self.root
        return self.root / Path(*parsed.split(keys.DELIMITER))

    # -- writing ---------------------------------------------------------

    @_logged("store_document")
    def store_document(
        self,
        key: str,
        content: str,
        format: str | None = None,
        *,
        title: str | None = None,
        encoding: str | None = None,
        updated_at: str | None = None,
    ) -> str:
        """One file per key, written whole, with the title written beside it.

        No transaction. A filesystem has none to offer, and pretending
        otherwise by writing to a staging directory and renaming would buy
        atomicity for the *pair* while a concurrent reader of the tree can see
        either file at any moment anyway. What is atomic is each file, which is
        :func:`outrage.bulk._write_file`'s ``os.replace``: a write interrupted
        halfway leaves whole files and no half of one.
        """
        # Inside the logged method, deliberately: see `Store._validated`.
        parsed, content, format, title, updated_at = self._validated(
            key, content, format, title=title, encoding=encoding, updated_at=updated_at
        )
        if parsed.has_wildcard:
            with self._allocating:
                allocated = self._next_number(parsed.wildcard_parent)
                parsed = keys.parse(keys.substitute_wildcard(parsed.key, allocated))
                self._write(parsed.key, content, format, updated_at)
        else:
            self._write(parsed.key, content, format, updated_at)
        if title is not None:
            self._write(
                f"{parsed.key}{keys.DELIMITER}{keys.META_PREFIX}title",
                title,
                "markdown",
                updated_at,
            )
        return parsed.key

    def _write(self, key: str, content: str, format: str, updated_at: str | None = None) -> None:
        """Write one key's file, and remove any other file claiming that key.

        **The order is the guarantee.** The new file is written first and the
        old spelling removed after, so a write that fails leaves the document
        that was there; the other way round, a key would spend the gap holding
        nothing. Storing ``a`` as json when ``a.md`` exists has to leave
        exactly one file, or the key reads twice and one of the answers is old.
        """
        path = self._path_for(key, format)
        if path.is_symlink():
            # A link is not a document here -- `_children` passes over one and
            # `_files_for` will not read one -- so `exists` says this key holds
            # nothing, and writing would have `os.replace` destroy a link the
            # store never held. Refused rather than resolved: what is on the
            # other end is somebody else's, and an export into a working
            # directory that quietly replaced a link would be a way to lose
            # work that was never in a store to begin with.
            raise bulk.UnmappableError("key-is-a-symlink", key=key, path=str(path))
        bulk._write_file(path, content)
        if updated_at is not None:
            # The mtime *is* this backend's ``updated_at`` -- there is nowhere
            # else to put one, and a sidecar recording it would be a file in
            # the corpus that is not a document. So a copy that carries a
            # timestamp in sets the file's, and the tree reads back what it was
            # told rather than when the copy happened.
            moment = datetime.fromisoformat(updated_at).timestamp()
            os.utime(path, (moment, moment))
        for other in self._files_for(key):
            if other != path:
                other.unlink()

    def _next_number(self, parent: str) -> str:
        """A numeric segment not in use among the children of ``parent``.

        One past the highest in use, for the reason the other backends give:
        deleting a key in the middle should not hand its number to something
        unrelated. Implicit children count -- a directory with no file of its
        own is as much in use as a document is.
        """
        used = [int(name) for name in self._child_names(parent) if keys.NUMERIC_RE.match(name)]
        return str(max(used) + 1) if used else "1"

    def _child_names(self, parent: str) -> list[str]:
        """The final segments of the keys immediately below ``parent``.

        Metadata is left out by the **segment**, not by ``is_metadata``, which
        says where the whole key first turns to metadata and not whether this
        child does: every key inside ``a/!changelog`` is metadata by that
        reading, and ``22`` there is an ordinary child a number is allocated
        beside.
        """
        return [
            name
            for child in self._level(parent)
            if not (
                name := child.key.rpartition(keys.DELIMITER)[2] if child.key else child.key
            ).startswith(keys.META_PREFIX)
        ]

    @_logged("delete")
    def delete(
        self,
        key: str,
        recursive: bool = False,
        *,
        key_range: KeyRange = UNBOUNDED,
        unchanged_since: str | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        """Unlink the files the selection names, then prune what that emptied.

        ``dry_run`` names them and unlinks nothing, from the same selection.

        The selection is the other backends' exactly: a metadata key is itself
        alone, a document key takes its metadata with it, and descendants come
        too only when ``recursive`` says so. ``key_range`` bounds both halves.

        **A directory left empty is removed**, up to the tree's own root. An
        empty directory is not a key -- nothing is below it, so nothing puts it
        in a listing -- and leaving one behind would make a delete visible in
        the shape of the tree without being visible in the namespace.

        The watermark is checked before the first ``unlink``, which is the only
        place it can be: unlinking is not undoable and there is no transaction
        here to abandon.

        A tree's timestamps are the filesystem's, so a watermark compared
        against one is comparing against an mtime rather than against something
        this store wrote. Touching a file is a change here and would not be in
        a database -- which is the honest reading for a tree a person edits.
        """
        check_unchanged(
            self,
            key,
            unchanged_since,
            action="delete",
            subtree=recursive,
            key_range=key_range,
        )
        parsed = keys.parse(key)
        within = _within(key_range)
        rows = list(self._subtree_rows(parsed.key, measure=False))

        # The key's own row and its whole metadata subtree: one unit, whatever
        # the key is, because metadata has no meaning once what it describes is
        # gone. What ``recursive`` adds is everything else below.
        lo, hi = keys.meta_range(parsed.key)
        below = _below(parsed.key)
        targets = [
            row
            for row in rows
            if row.key == parsed.key or lo <= row.key < hi or (recursive and below(row.key))
        ]

        removed = []
        for row in targets:
            if not within(row.sort_key):
                continue
            if not dry_run:
                row.path.unlink(missing_ok=True)
                self._prune(row.path.parent)
            removed.append(row.key)
        return sorted(removed, key=keys.sort_form)

    def _prune(self, directory: Path) -> None:
        """Remove ``directory`` and its emptied parents, stopping at the tree."""
        root = self.root.resolve()
        current = directory.resolve()
        while current != root and current.is_relative_to(root):
            try:
                current.rmdir()
            except OSError:
                return
            current = current.parent

    # -- reading ---------------------------------------------------------

    def exists(self, key: str) -> bool:
        """Whether a file holds ``key``, asked of the path rather than a walk.

        The one read that does not decode: a file that is there but is not text
        is still a file, and this question is about the key being taken.
        """
        return self._file_for(keys.parse(key).key) is not None

    def level_entry(self, key: str) -> Entry | None:
        """The file if there is one, else whether the directory holds anything.

        The second half is not "does the directory exist": an empty directory
        is not a key, and one is what a hand edited tree or an interrupted run
        leaves behind. It descends until it finds a row and stops there.
        """
        parsed = keys.parse(key)
        if parsed.key == keys.ROOT:
            raise ValueError("the root is not a child of anything, so it has no listing entry")

        path = self._file_for(parsed.key)
        row = None if path is None else self._row(parsed.key, path, measure=True)
        if row is not None:
            return _entry(row)
        if self._holds_anything(parsed.key):
            return _implicit(parsed.key)
        return None

    @_logged("descendant_count")
    def descendant_count(
        self, key: str, *, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False
    ) -> int:
        """What a plain delete of ``key`` would keep, counted over a walk.

        Everything below ``key``, less the metadata unit a non-recursive delete
        takes with it -- which is why a document's own title has never counted
        here. ``whole_subtree`` keeps that unit, which is the walk itself and
        no subtraction at all. See :func:`outrage.keys.meta_range`.

        Unmeasured: a count has no use for a document's length, and measuring
        would make asking how much is below a key cost reading all of it.
        """
        scope = keys.parse(key).key
        below = _below(scope)
        lo, hi = keys.meta_range(scope)
        within = _within(key_range)
        return sum(
            1
            for row in self._subtree_rows(scope, measure=False)
            if below(row.key) and (whole_subtree or not lo <= row.key < hi) and within(row.sort_key)
        )

    @_logged("retrieve_document")
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
        """One path lookup, one file read, and the shared slicing.

        The slicing is :func:`outrage.store._excerpt`, unchanged: how ``length``
        and ``max_chars`` combine is the store's policy rather than this
        backend's, and two backends that sliced differently would return
        different documents for the same call.

        A **byte** offset seeks: a document here is a file, and a file is the
        one thing in this project that already knows how to start reading in
        the middle. :meth:`_byte_read` is that half.
        """
        parsed = keys.parse(key)
        path = self._file_for(parsed.key)
        if path is None:
            beneath = self.descendant_count(parsed.key)
            if beneath:
                raise KeyNotFoundError("key-is-a-container", key=key, beneath=beneath)
            raise KeyNotFoundError("key-not-found", key=key)

        check_read_position(
            key, offset=offset, byte_offset=byte_offset, pattern=pattern, occurrence=occurrence
        )
        row = self._row(parsed.key, path, measure=False)

        if byte_offset is not None:
            # The extension names the format where it names one at all. Where
            # it does not, the content is read for it -- the whole content,
            # since `_detect_format` asks whether the document parses as JSON
            # and a slice of one does not. So an undeclared format costs this
            # read what the character path costs, and a declared one seeks.
            declared = row.format
            if declared is None:
                declared = _detect_format(_text(path, parsed.key))
            return self._byte_read(
                row, path, key, declared, byte_offset, pattern, occurrence, length, max_chars
            )

        content = _text(path, parsed.key)
        start = offset
        if pattern is not None:
            start = _find_occurrence(content, pattern, occurrence, offset)
            if start is None:
                raise PatternNotFoundError(
                    "pattern-not-found",
                    key=key,
                    pattern=pattern,
                    occurrence=occurrence,
                    offset=offset,
                )

        # The extension names the format where it names one at all; where it
        # does not -- `myfile.py` keeps its name and declares nothing -- the
        # content is read for it, which is the same answer a write with no
        # format given would have reached.
        format = row.format if row.format is not None else _detect_format(content)
        return _excerpt(row.key, content, format, row.updated_at, start, length, max_chars)

    def _byte_read(
        self,
        row: _Row,
        path: Path,
        key: str,
        format: str | None,
        byte_offset: int,
        pattern: str | None,
        occurrence: int,
        length: int | None,
        max_chars: int,
    ) -> Excerpt:
        """The byte-addressed half of :meth:`retrieve_document`, which seeks.

        The largest win of the three backends and the least machinery: a
        document here *is* a file, so this opens it, seeks to the byte and
        reads the window. Flat in the size of the document and in the offset,
        where the SQLite path still walks a page chain.

        **A file holding CRLF is the one place this and the character path
        disagree**, and it is `issues/3` rather than this read: the character
        path decodes with universal newlines, so it returns text the file does
        not hold and counts a length the file does not have. What is addressed
        here is the file itself, which is the only thing a byte offset can
        usefully mean to anything outside the store.
        """
        try:
            with path.open("rb") as handle:
                total_bytes = handle.seek(0, os.SEEK_END)

                def read(offset: int, size: int) -> bytes:
                    handle.seek(min(offset, total_bytes))
                    return handle.read(size)

                start = byte_offset
                if pattern is not None:
                    found = _find_byte_occurrence(
                        read, total_bytes, pattern, occurrence, byte_offset
                    )
                    if found is None:
                        raise PatternNotFoundError(
                            "pattern-not-found",
                            key=key,
                            pattern=pattern,
                            occurrence=occurrence,
                            offset=0,
                            byte_offset=byte_offset,
                        )
                    start = found

                return _byte_excerpt(
                    row.key,
                    format,
                    row.updated_at,
                    start,
                    length,
                    max_chars,
                    read=read,
                    total_bytes=total_bytes,
                )
        except UnicodeDecodeError as exc:
            # The same refusal `_text` gives, for the same reason: a file that
            # is not text is not a document, and saying which key was asked for
            # is what turns that into something a caller can act on.
            raise NotTextError("files-not-text", key=row.key, path=str(path)) from exc

    @_logged("list_keys")
    def list_keys(
        self,
        key: str | None = None,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> Page[Entry]:
        """One directory, its files and its subdirectories together.

        Real and implicit keys arrive from the same listing rather than from
        two halves that have to be merged and cut together, which is the defect
        the SQLite shape has to be careful about: a name in this directory is a
        child whether a file holds it or a directory does.

        The totals are over the level rather than over the page, so a cursor
        does not reach them, and they cost a decode per document -- see the
        module docstring on what a character count is.
        """
        entries = self._level(_scope(key))
        bound = _cursor_bound(cursor)
        candidates = [
            entry for entry in entries if bound is None or keys.sort_form(entry.key) > bound
        ]

        items = candidates if limit is None else candidates[:limit]
        more = limit is not None and len(candidates) > limit
        return Page(
            items=items,
            returned=len(items),
            total=len(entries),
            total_chars=sum(entry.size or 0 for entry in entries),
            next_cursor=items[-1].key if more and items else None,
        )

    def _level(self, key: str) -> list[Entry]:
        """One level as listing entries, in key order.

        The level of a key is the *directory named by the whole key*, metadata
        segments included: ``a/!x`` holds ``a/!x/y`` in ``a/!x/``, exactly as
        the mapping says and as the parent column in the other backend does.
        """
        parsed = keys.parse(key)
        entries = []
        for child, path, directory in self._children(parsed.key):
            row = None if path is None else self._row(child, path, measure=True)
            if row is not None:
                entries.append(_entry(row))
            elif directory is not None and self._holds_anything(child):
                entries.append(_implicit(child))
        return entries

    def _children(self, key: str) -> list[tuple[str, Path | None, Path | None]]:
        """:func:`_children` over the directory ``key`` names, with this store's
        answer to whether a dotfile is a document."""
        return _children(self._dir_for(key), key, hidden=self._hidden)

    def _holds_anything(self, key: str) -> bool:
        """Whether anything at all lies below ``key``.

        A directory that holds no row is not a key: it lists as nothing and
        reads as nothing, which is what an interrupted run or a hand edit
        leaves behind. Stops at the first row it finds rather than counting
        them.
        """
        return any(True for _ in self._below_rows(key, measure=False))

    @_logged("get_documents")
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
        """The selection, then the page cut out of it against the two caps.

        The totals come from the selection and the page from the cursor into
        it, which is the split every backend makes: a cursor moves as a caller
        pages and must not reach ``total``.
        """
        selection = self._selection(subtree, key_range, meta_name=meta_name)
        total_chars = _total_chars(selection)

        items: list[Excerpt] = []
        spent = 0
        more = False
        for row in _after(selection, _cursor_bound(cursor)):
            if limit is not None and len(items) >= limit:
                more = True
                break
            expected = min(row.chars or 0, max_chars)
            if items and max_total_chars is not None and spent + expected > max_total_chars:
                # Never on the first document, or a budget smaller than one
                # document returns an empty page with a cursor that does not
                # move, and the caller loops forever making no progress.
                more = True
                break
            content = _text(row.path, row.key)
            format = row.format if row.format is not None else _detect_format(content)
            excerpt = _excerpt(row.key, content, format, row.updated_at, 0, None, max_chars)
            items.append(excerpt)
            spent += excerpt.returned

        return Page(
            items=items,
            returned=len(items),
            total=len(selection),
            total_chars=total_chars,
            next_cursor=items[-1].key if more and items else None,
        )

    @_logged("missing_meta_stats")
    def missing_meta_stats(
        self,
        subtree: BoundedSubtree = EVERYTHING,
        *,
        key_range: KeyRange = UNBOUNDED,
        window: KeyRange = UNBOUNDED,
        meta_name: str | Sequence[str] = "title",
        sample: int = 0,
    ) -> MissingMeta:
        """Documents carrying none of ``meta_name``, over one window.

        The window is measured where the document's metadata *would* have
        sorted, not where the document itself does -- the contract says so, and
        it is what makes a caller's windows tile. Synthesised the same way the
        parquet backend synthesises it, from the same two pieces:
        :func:`outrage.keys.meta_sort_suffix` for an ordinary key, and the
        metadata's own sort form for the root, which contributes no segment for
        a suffix to join onto.
        """
        names = _names(meta_name)
        missing = self._missing(subtree, key_range, names)

        suffix = min(keys.meta_sort_suffix(name) for name in names)
        root = min(keys.sort_form(keys.META_PREFIX + name) for name in names)
        inside = _within(window)
        within = [
            row
            for row in missing
            if inside(root if row.sort_key == keys.ROOT else row.sort_key + suffix)
        ]
        return MissingMeta(
            total=len(within),
            total_chars=_total_chars(within),
            sample=[row.key for row in within[:sample]] if sample > 0 else [],
        )

    @_logged("keys_missing_meta")
    def keys_missing_meta(
        self,
        subtree: BoundedSubtree = EVERYTHING,
        *,
        key_range: KeyRange = UNBOUNDED,
        cursor: str | None = None,
        meta_name: str | Sequence[str] = "title",
        limit: int | None = None,
    ) -> Page[str]:
        """The same selection :meth:`missing_meta_stats` counts, listed.

        Shared rather than reimplemented, for the reason the other backends
        share theirs: the survey, its count and the list of what it could not
        see have to agree about what was in range, and two expressions of one
        predicate are two chances to disagree.
        """
        missing = self._missing(subtree, key_range, _names(meta_name))
        found = list(_after(missing, _cursor_bound(cursor)))
        items = found if limit is None else found[:limit]
        more = limit is not None and len(found) > limit
        return Page(
            items=[row.key for row in items],
            returned=len(items),
            total=len(missing),
            total_chars=_total_chars(missing),
            next_cursor=items[-1].key if more and items else None,
        )

    # -- selecting -------------------------------------------------------

    def _selection(
        self,
        subtree: BoundedSubtree,
        key_range: KeyRange,
        *,
        meta_name: str | Sequence[str] | None,
    ) -> list[_Row]:
        """The rows a subtree read is about, in key order.

        The same three independent conditions the other backends AND together:
        inside ``subtree``, carrying the metadata asked for, and inside
        ``key_range``. A page cursor is not among them, which is what keeps
        ``total`` describing the selection rather than the remainder of it.

        **The subtree is where the walk starts**, rather than a filter over one
        that began at the root. That is the whole of what this backend has
        instead of a bisect: a directory is a subtree, so reading one opens the
        directories under it and no others.
        """
        wanted = None if meta_name is None else _names(meta_name)
        deep_enough = _depth_test(subtree)
        within = _within(key_range)
        seen_from = meta_reader(_scope(subtree.key))

        def carries(row: _Row) -> bool:
            name, path = seen_from(row.key, row.meta_name, row.meta_path)
            if wanted is None:
                return name is None
            return name in wanted and path is None

        return [
            row
            for row in self._subtree_rows(_scope(subtree.key), measure=True)
            if deep_enough(row) and carries(row) and within(row.sort_key)
        ]

    def _missing(
        self, subtree: BoundedSubtree, key_range: KeyRange, names: list[str]
    ) -> list[_Row]:
        """Documents in the selection carrying none of ``names``.

        The metadata a document carries is read from the walk it is already in:
        a document's metadata sorts inside its own subtree, always, so a walk
        that can see the document can see what it carries. Which is why this
        collects from the *unfiltered* rows -- a range that cuts a title out of
        the selection has not taken the title off the document.
        """
        carried: dict[str, set[str]] = {}
        for row in self._subtree_rows(_scope(subtree.key), measure=False):
            # From the last segment, against the key it hangs from. A value of
            # `title` is the key `<document>/!title` and nothing else, at any
            # scope, so this needs no reading of where the whole key first
            # turned to metadata.
            parent, _, name = row.key.rpartition(keys.DELIMITER)
            if name.startswith(keys.META_PREFIX):
                carried.setdefault(parent, set()).add(name[len(keys.META_PREFIX) :])
        return [
            row
            for row in self._selection(subtree, key_range, meta_name=None)
            if not carried.get(row.key, _NOTHING).intersection(names)
        ]

    # -- walking ---------------------------------------------------------

    def _subtree_rows(self, key: str, *, measure: bool) -> Iterator[_Row]:
        """Every row at and below ``key``, in key order.

        The key's own row first, then everything the directory beneath it
        holds, which is exactly the stretch of the order that
        ``sort_form(k) <= sort_key < sort_subtree_end(k)`` names in a backend
        that can bisect.
        """
        parsed = keys.parse(key).key
        path = self._file_for(parsed)
        if path is not None:
            row = self._row(parsed, path, measure=measure)
            if row is not None:
                yield row
        yield from self._below_rows(parsed, measure=measure)

    def _below_rows(self, key: str, *, measure: bool) -> Iterator[_Row]:
        """Every row strictly below ``key``, in key order.

        Depth first, children in segment sort order, the file at a name before
        the directory at it. That is global key order and not merely a tidy
        one: a sort form is per segment and delimiter joined, so a parent's
        prefixes every descendant's, and the metadata marker sorts ahead of the
        document marker, which puts ``a/!title`` in front of ``a/b`` without
        this having to know that it should.
        """
        for child, path, directory in _children(self._dir_for(key), key, hidden=self._hidden):
            if path is not None:
                row = self._row(child, path, measure=measure)
                if row is not None:
                    yield row
            if directory is not None:
                yield from self._below_rows(child, measure=measure)

    def _row(self, key: str, path: Path, *, measure: bool) -> _Row | None:
        """One file as a row, or None when it does not hold a document.

        None for a file that is not UTF-8 text, and only when the walk is
        measuring: an unmeasured walk does not open the file, so it cannot know,
        and a count that skipped rows a read would return would be a different
        answer to the same question. What that costs is that a corpus with a
        binary file in it counts one row more than it can read -- reported by
        :meth:`check_file`, which is where the tree's own faults belong.
        """
        parsed = keys.parse(key)
        stat = path.stat()
        chars = None
        if measure:
            try:
                chars = len(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                return None
        return _Row(
            key=parsed.key,
            doc_key=parsed.doc_key,
            meta_name=parsed.meta_name,
            meta_path=parsed.meta_path,
            format=bulk.FORMAT_BY_EXTENSION.get(path.suffix),
            updated_at=datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(timespec="seconds"),
            sort_key=keys.sort_form(parsed.key),
            chars=chars,
            path=path,
        )

    # -- maintenance -----------------------------------------------------

    @classmethod
    def in_directory(
        cls,
        directory: str | os.PathLike[str] | None = None,
        *,
        filename: str | os.PathLike[str] | None = None,
        log: EventLog | None = None,
        mount_point: str | None = None,
    ) -> Self:
        """The tree ``filename`` names inside a store directory.

        The base's rule, reached the long way round: this constructor takes the
        tree itself, so the directory-plus-relative-name one is applied here
        with :func:`~outrage.store.store_file` and the result handed over as a
        path. A mount is a name inside ``--dir`` whatever backend answers it,
        and every refusal that rule makes -- an absolute path, a ``..`` out of
        the directory -- is made for a tree as it is for a database.

        ``filename`` of None is :data:`DEFAULT_TREE_NAME`, so a tree mounted
        without a name sits beside the store files rather than being one.
        """
        return cls(
            store_file(
                resolve_directory(directory),
                cls.default_filename if filename is None else filename,
            ),
            log=log,
            mount_point=mount_point,
        )

    def opened_at(self, path: Path) -> Self:
        """The tree at ``path``, reading dotfiles the way this store does.

        The base splits a path into a directory and a name within it, which is
        what every other backend's constructor takes; this one's takes the
        directory itself. ``hidden`` travels with it because the root document
        *is* a dotfile: a copy opened without it would not see the key the
        store it was copied from holds at the root, and would compare short
        for a reason that is not a fault.

        **A backup of a tree is a copy of its documents, not of its
        directory.** Whatever the tree holds that is not a document -- a
        symbolic link, a file that is not text, a name no key spells -- is
        passed over, the same way every other read of this store passes it
        over. :meth:`check_file` is what names those, and it is worth running
        before trusting a backup of a tree somebody has been editing by hand.
        """
        return type(self)(path, hidden=self._hidden)

    @property
    def stored_format_version(self) -> int:
        """This build's own, because the layout is the format.

        There is nothing in the tree recording a version and nothing should
        be: a marker file would be litter in an exported tree and a key that is
        not a document, and it could only ever disagree with the layout the
        files are actually in. Answering with :attr:`format_version` says the
        two cannot differ, which is true here and false for a file with a
        header -- cf. "'Nothing to repair' and 'nothing to check' are not the
        same sentence" in ``planned/storage``.
        """
        return self.format_version

    def audit_rows(self) -> Iterator[AuditRow]:
        """Every row the tree holds, in one walk.

        ``parent`` is **derived** rather than read back, because a tree keeps
        no denormalisation of it: a file's parent is the directory it is in, by
        construction. So the parent check in
        :func:`outrage.maintenance.check` cannot fire here, and that is a
        property of the storage rather than a check being skipped.
        """
        for row in self._subtree_rows(keys.ROOT, measure=True):
            yield AuditRow(
                key=row.key,
                doc_key=row.doc_key,
                meta_name=row.meta_name,
                parent=keys.parse(row.key).parent,
                chars=row.chars or 0,
            )

    def check_file(self, report: Report) -> None:
        """What only a tree can say about itself: the files that are not keys.

        A database refuses a bad key at the point of writing, so every row in
        one is a key. A directory takes whatever is put in it, and a tree is
        meant to be edited by hand -- that is most of what it is for -- so the
        faults worth reporting are the ones an editor can create: a name that
        no key spells, two files claiming one key, and a file that is not text.
        """
        files = 0
        size = 0
        unnamed: list[str] = []
        doubled: list[str] = []
        binary: list[str] = []
        seen: set[str] = set()

        for path in sorted(self.root.rglob("*")):
            if path.is_symlink() or not path.is_file() or path.name.startswith(bulk.TEMP_PREFIX):
                continue
            files += 1
            size += path.stat().st_size
            relative = path.relative_to(self.root)
            try:
                key, _ = bulk.key_for_path(relative.as_posix())
                key = keys.parse(key).key
            except (keys.InvalidKeyError, ValueError):
                unnamed.append(str(relative))
                continue
            if key in seen:
                doubled.append(str(relative))
            seen.add(key)
            try:
                path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                binary.append(str(relative))

        report.details["files"] = str(files)
        report.details["bytes"] = str(size)
        for names, summary, detail in (
            (unnamed, "files whose names are not keys", "read as nothing at all"),
            (doubled, "keys held by more than one file", "the first in name order is what reads"),
            (binary, "files that are not UTF-8 text", "passed over by every read"),
        ):
            if names:
                report.problems.append(Problem("warning", summary, f"{_listed(names)}: {detail}"))

    def repair(self) -> list[Repaired]:
        """Nothing, and that is the honest answer rather than a silence.

        A repair moves bytes about inside a file the storage owns. What
        :meth:`check_file` finds here is not that: a file whose name is not a
        key is somebody's file, and a store that quietly renamed or removed it
        would be losing what it was asked to keep. Reporting it and leaving it
        is the only answer that does not.
        """
        return []


#: Stands in for "this document carries no metadata at all", so the lookup in
#: :meth:`FilesystemStore._missing` needs no branch and allocates nothing.
_NOTHING: frozenset[str] = frozenset()


def _children(
    directory: Path, prefix: str, *, hidden: bool
) -> list[tuple[str, Path | None, Path | None]]:
    """The keys immediately below ``prefix``, in key order, with what holds each.

    A name in a directory can be held by a file, by a subdirectory, or by both
    -- ``a.md`` beside ``a/`` is a key that is a document *and* a container,
    which is the whole reason the mapping gives documents an extension. So a
    child is a name and up to two paths rather than one entry per file.

    What is passed over, and each is a decision rather than an omission:
    a **symlink**, in either direction, for the reason an import does not
    follow one; a **half-written file**, which ``os.replace`` means is never
    what a reader wants; a **dotfile**, when the store was opened over a
    foreign tree; and a **name that is not a key**, which reads as nothing at
    all and is reported by :meth:`FilesystemStore.check_file` rather than
    guessed at.
    """
    if not directory.is_dir():
        return []

    files: dict[str, Path] = {}
    directories: dict[str, Path] = {}
    for entry in sorted(directory.iterdir(), key=lambda path: path.name):
        name = entry.name
        if name.startswith(bulk.TEMP_PREFIX) or entry.is_symlink():
            continue
        if not hidden and name.startswith("."):
            continue
        if entry.is_dir():
            directories.setdefault(name, entry)
        elif entry.is_file():
            # The root document is the one file named by an extension alone,
            # and it belongs to the key *holding* this directory rather than to
            # a child of it -- so it is not a child here. Only at the top of
            # the tree, which is the only place a key with no segments is.
            if prefix == keys.ROOT and name in bulk.FORMAT_BY_EXTENSION:
                continue
            stem, extension = os.path.splitext(name)
            files.setdefault(stem if extension in bulk.FORMAT_BY_EXTENSION else name, entry)

    found = []
    for segment in files.keys() | directories.keys():
        key = segment if prefix == keys.ROOT else f"{prefix}{keys.DELIMITER}{segment}"
        try:
            parsed = keys.parse(key).key
        except keys.InvalidKeyError:
            continue
        found.append((parsed, files.get(segment), directories.get(segment)))
    return sorted(found, key=lambda child: keys.sort_form(child[0]))


def _text(path: Path, key: str) -> str:
    """The document in ``path``, or a refusal naming the key it was read for."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise NotTextError("files-not-text", key=key, path=str(path)) from exc


def _names(meta_name: str | Sequence[str]) -> list[str]:
    """One metadata name or several, as a list, refusing none.

    An empty sequence is refused rather than treated as "any": it would select
    every document as missing every name, which is a plausible-looking answer
    to a question the caller did not ask.
    """
    names = [meta_name] if isinstance(meta_name, str) else list(meta_name)
    if not names:
        raise ValueError("meta_name must not be an empty sequence")
    return names


def _total_chars(rows: list[_Row]) -> int:
    """The characters across ``rows``, refusing a row nobody measured.

    Loud rather than lenient. An unmeasured row counts as nothing, and a total
    that is quietly short is the kind of wrong answer a caller acts on: 40 MB
    beneath a key reported as 2 is what makes them read it.
    """
    if any(row.chars is None for row in rows):
        raise ValueError("a total over rows the walk did not measure")
    return sum(row.chars or 0 for row in rows)


def _after(rows: list[_Row], bound: str | None) -> list[_Row]:
    """The rows past a page cursor.

    Separate from the range bounds because a cursor is not one: it moves as a
    caller pages and deliberately does not reach the totals. Keeping the two
    apart is what stops one quietly becoming the other.
    """
    if bound is None:
        return rows
    return [row for row in rows if row.sort_key > bound]


def _depth_test(subtree: BoundedSubtree) -> Callable[[_Row], bool]:
    """``subtree``'s depth budget as a test on a row, and nothing else.

    Depth is counted on ``doc_key`` rather than on the whole key, for the
    reason every backend counts it there: metadata does not add depth, so
    ``a/b`` and ``a/b/!title`` are both at depth 2 and one budget covers a
    document and its metadata together.
    """
    if subtree.depth is None:
        return lambda row: True

    limit = subtree.depth
    base = keys.depth(_scope(subtree.key))

    def deep_enough(row: _Row) -> bool:
        depth = 0 if row.doc_key == keys.ROOT else row.doc_key.count(keys.DELIMITER) + 1
        return depth - base <= limit

    return deep_enough


def _below(scope: str) -> Callable[[str], bool]:
    """A test for the keys strictly beneath ``scope``.

    A half-open string range for an ordinary key, since everything under ``a``
    starts with ``a/`` -- which is what keeps ``a/b`` from picking up
    ``a/beta``. For the root it is a test against the root itself: everything
    else is beneath it, and no string bounds every key from above.
    """
    if scope == keys.ROOT:
        return lambda candidate: candidate != keys.ROOT
    lo, hi = keys.subtree_range(scope)
    return lambda candidate: lo <= candidate < hi


def _implicit(key: str) -> Entry:
    """``key`` as it appears in a listing when only its descendants exist."""
    return Entry(key=key, kind="implicit", size=None, format=None, updated_at=None)


def _entry(row: _Row) -> Entry:
    """A row as it appears in its parent's listing."""
    return Entry(
        key=row.key,
        kind=entry_kind(row.key),
        size=row.chars,
        format=row.format,
        updated_at=row.updated_at,
    )


__all__ = [
    "DEFAULT_TREE_NAME",
    "FORMAT_VERSION",
    "FilesystemStore",
    "NotTextError",
]
