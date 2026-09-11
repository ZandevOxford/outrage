"""The duckdb backend: a directory of parquet parts, read as one store.

The fourth implementation of :class:`outrage.store.Store`, and the one for a
reference base **too large for one file, or that arrives in pieces**. Each part
is a file ``outrage pack`` could have written -- the same columns and the same
format stamp as :mod:`outrage.store_parquet` -- and the store is every part
together. Nothing about the file format is redefined here.

**The parts may be in any order.** Not sorted, not disjoint. A store is in sort
order, but the source it was made from need not be: a producer holding its
corpus in page-id order, or crawl order, or one file per batch, cannot be asked
to sort across files before it can be read. That is what rules out answering
this with the parquet backend's own reads, which bisect a single sorted file
and hold its small columns resident to do it -- over parts in arbitrary order
that index would have to be merged at open and held over the whole corpus. Here
nothing is held between queries but duckdb's own buffers, and **what this
costs does not grow with the corpus**, which is the reason to have it. Reads are
slower than the parquet backend's -- several milliseconds where a bisect is
microseconds -- and every one of them is still far below the round trip of the
tool call carrying it.

**A directory names it**, and has no extension to name its backend, so it is
always asked for: ``ref=refbase,type=duckdb``. The parts are the ``.parquet``
files directly inside it, less dotfiles, which is what a producer writing a
part under a temporary name and renaming it into place needs. **The list is
taken when the store is opened**, and the store is those parts until it is
opened again: a part appearing later is picked up by the next open, and a part
half written while a store is being read is never read at all.

**A key held in more than one part is held more than once**, and nothing
resolves it. The store is the concatenation of its parts: reading the rows --
:meth:`DuckdbStore.get_documents`, :meth:`DuckdbStore.keys_missing_meta` --
returns a repeated key once per row, their totals count rows, and every row is
reachable. Reading the *key* -- :meth:`DuckdbStore.retrieve_document`,
:meth:`DuckdbStore.exists`, :meth:`DuckdbStore.level_entry` -- answers with the
newest of them, and so does a listing, since a listing entry is by contract
what :meth:`~DuckdbStore.level_entry` says about that key. What removes the
repeats is compaction, which is packing the directory into one file, and not
anything here.

What repeated rows do need is a rule about pages, because **a cursor names a
key and never a position**: two rows sharing a key cannot be told apart by one,
so a page ending between them would resume past both or before both. So **a
page never ends inside a run of one key**. It stops before the run and returns
fewer than ``limit``, which a limit allows; and where one run is longer than a
whole page it returns the whole run, which is the only case in which
``returned`` exceeds ``limit``. That run is as long as the number of parts
repeating the key, and it overruns ``max_total_chars`` the way a first document
larger than the budget already does, for the same reason -- anything smaller
is a page that cannot move. A mount table pages across stores by asking each
for its own pages and never cutting one, so the rule holds through a mount with
nothing there knowing about it.

**It does not write**, like the parquet backend and for a related reason: the
directory changes by gaining a part, which is a file somebody else writes, and
nothing here updates a part in place. So :meth:`~DuckdbStore.store_document`
and :meth:`~DuckdbStore.delete` refuse, and the refusal is the storage's rather
than a mount's.

**Every part must be in the same format version, and it must be this build's.**
A version 1 part carries no ``meta_path`` column and splits ``meta_name``
under an older rule; reading one would mean re-deriving that split in SQL,
which is a second definition of the key grammar. So an older part is refused
with the advice to repack it, and a directory mixing versions -- a repack left
half done -- is refused naming both.

duckdb is an optional dependency: ``pip install outrage[duckdb]``. It is
imported inside this module, and this module only when something names the
backend, so an install without it is unaffected until then. pyarrow is not
needed to read a directory; only building a part is its business.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import threading
import uuid
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import Any

from . import keys
from .eventlog import EventLog
from .maintenance import Repaired, Report
from .store import (
    DEFAULT_BULK_MAX_CHARS,
    DEFAULT_MAX_CHARS,
    EVERYTHING,
    UNBOUNDED,
    AuditRow,
    BackendError,
    Backup,
    BackupError,
    BoundedSubtree,
    Entry,
    Excerpt,
    FileStore,
    KeyNotFoundError,
    KeyRange,
    MissingMeta,
    Page,
    PatternNotFoundError,
    ReadOnlyStoreError,
    SubtreeTotals,
    _byte_excerpt,
    _clear,
    _cursor_bound,
    _excerpt,
    _find_byte_occurrence,
    _find_occurrence,
    _logged,
    _scope,
    _sliced,
    _stored_bytes,
    _with_descendants,
    check_read_position,
    entry_kind,
)
from .store_parquet import FORMAT_VERSION, VERSION_KEY
from .store_sqlite import _below, _meta_clauses, _range_clauses, _subtree_clauses

#: What a duckdb store's directory is called when a caller names none. It has
#: no extension because a directory has none to give, which is why this backend
#: is always named rather than inferred.
DEFAULT_STORE_DIR = "parts"

#: What a part's file name ends with. The only files in the directory that are
#: read; anything else there is left alone.
PART_SUFFIX = ".parquet"

#: The ceiling on what duckdb may hold in memory. Set because its own default
#: is most of the machine's RAM, which is the wrong answer for a server sharing
#: a machine with the editor it serves. Measured to make almost no difference to
#: what it actually holds -- a reference base of 2.7 million rows sat near 140 MB
#: whatever this said -- and every read here is bounded by a key rather than an
#: offset, so none of them sorts a whole selection to reach a page.
MEMORY_LIMIT = "1GB"

#: How many rows a page's read asks for when the caller named no limit, and
#: what a run of reads grows from. Doubled on each further read up to
#: :data:`BATCH_CEILING`, so a short page costs one small query and a long walk
#: does not cost one query per handful of rows.
BATCH = 64

#: The largest read :data:`BATCH` grows to.
BATCH_CEILING = 4096

#: Rows audited at a time. The same figure the parquet backend walks in, for
#: the same reason: large enough to amortise a fetch, small enough that the
#: rows are freed long before the walk ends.
AUDIT_CHUNK = 8192

#: The columns a part holds that any read here asks for. Named in the view
#: rather than taken with ``*``, so a part written with ``bytes`` and one
#: written without it are the same store, and so the two columns duckdb adds --
#: which part a row came from, and where in it -- have names of this module's
#: choosing.
_COLUMNS = (
    "key",
    "doc_key",
    "meta_name",
    "meta_path",
    "parent",
    "content",
    "format",
    "updated_at",
    "sort_key",
    "chars",
)

#: The order every read here walks: the store's own, then the part, then the
#: row within it. The last two are what make it a *total* order when a key is
#: repeated, which the paging rule depends on -- a run of one key comes out in
#: the same sequence every time, and a read resuming inside one resumes at the
#: row after the last it returned.
_ORDER = "sort_key, part, part_row"

#: Which of a repeated key's rows a read by key returns: the most recently
#: written, then the later part. A pack stamps a whole part with one time, so
#: the tie is the common case rather than a corner.
_NEWEST = "updated_at DESC, part DESC, part_row DESC"


def _duckdb() -> Any:
    """duckdb, or a sentence saying it is not installed.

    Imported through a function so the failure is this package's to explain,
    for the reason :func:`outrage.store_parquet._arrow` gives.
    """
    try:
        import duckdb
    except ImportError as exc:  # pragma: no cover - exercised by uninstalling
        raise BackendError("duckdb-needs-duckdb", reason=str(exc)) from exc
    return duckdb


def _quoted(path: Path) -> str:
    """``path`` as a SQL string literal.

    The part list is written into the view's definition, because a view cannot
    take parameters. Doubling a quote is the whole of SQL string escaping.
    """
    return "'" + str(path).replace("'", "''") + "'"


class DuckdbStore(FileStore):
    """A document store held as a directory of parquet parts, read only."""

    default_filename = DEFAULT_STORE_DIR
    backend_name = "duckdb"
    format_version = FORMAT_VERSION
    writable = False

    def __init__(
        self,
        directory: str | os.PathLike[str] | None = None,
        *,
        filename: str | os.PathLike[str] | None = None,
        log: EventLog | None = None,
        mount_point: str | None = None,
    ) -> None:
        # The directory of parts is `path`, named inside the store directory
        # like any other store, and the store directory is where the event log
        # and a backup go -- beside the parts rather than among them.
        super().__init__(directory, filename=filename, log=log, mount_point=mount_point)
        if not self.path.exists():
            # Refused rather than created, for the reason a missing parquet
            # file is: nothing here writes, so an empty store could only ever
            # read back empty, and a mistyped name would mount as a reference
            # base that is simply missing.
            raise BackendError("duckdb-store-missing", path=str(self.path))
        if not self.path.is_dir():
            raise BackendError("duckdb-not-a-directory", path=str(self.path))
        self._parts = _parts_in(self.path)
        if not self._parts:
            raise BackendError("duckdb-no-parts", path=str(self.path))

        # One database per store and a cursor per thread, which is duckdb's
        # model for concurrency and the same rule the other two backends are
        # under: the server answers tools from a worker pool, and state shared
        # between threads is how one caller gets another's answer. The
        # database is made on first use and dropped by `close`, and the
        # generation is how a thread holding a cursor into a dropped one
        # knows to take a new one rather than use a closed connection.
        self._local = threading.local()
        self._lock = threading.Lock()
        self._database: Any | None = None
        self._spill: Path | None = None
        self._generation = 0
        # On the way in rather than on the first read, so a mount naming an
        # unreadable directory fails while somebody is still looking at it.
        self._written_version = self._check_versions()

    # -- the directory ---------------------------------------------------

    def _connect(self) -> Any:
        """A database over this store's parts, with the view every read uses.

        In memory: nothing here is persisted, and the parts are the store. The
        settings are explicit because duckdb's defaults are chosen for a
        process that has the machine to itself -- memory as a share of all of
        it, and spill files in the working directory, which for a server is
        wherever it was started. Spill goes to a directory of this store's own
        under the system's temporary directory, made only if duckdb spills and
        removed on :meth:`close`.

        The parquet metadata cache keeps each part's footer between queries,
        which is most of what the first read of a many-part directory costs.
        """
        duckdb = _duckdb()
        self._spill = Path(tempfile.gettempdir()) / f"outrage-duckdb-{uuid.uuid4().hex}"
        database = duckdb.connect(
            config={"memory_limit": MEMORY_LIMIT, "temp_directory": str(self._spill)}
        )
        try:
            database.execute("SET parquet_metadata_cache = true")
            listed = ", ".join(_quoted(part) for part in self._parts)
            database.execute(
                f"CREATE VIEW parts AS SELECT {', '.join(_COLUMNS)}, "
                "filename AS part, file_row_number AS part_row "
                f"FROM read_parquet([{listed}], filename = true, "
                "file_row_number = true, union_by_name = true)"
            )
        except Exception:
            database.close()
            raise
        return database

    @property
    def _cursor(self) -> Any:
        """This thread's connection to the store's database.

        **Never hand one to another thread.** A duckdb cursor is a connection
        of its own, and one shared between threads is the same mistake a
        SQLite connection shared between them is.
        """
        local = self._local
        cursor = getattr(local, "cursor", None)
        if cursor is not None and getattr(local, "generation", None) == self._generation:
            return cursor
        with self._lock:
            if self._database is None:
                self._database = self._connect()
            cursor = self._database.cursor()
            local.cursor, local.generation = cursor, self._generation
        return cursor

    def _all(self, sql: str, params: Sequence[object] = ()) -> list[tuple]:
        return self._cursor.execute(sql, list(params)).fetchall()

    def _one(self, sql: str, params: Sequence[object] = ()) -> tuple | None:
        return self._cursor.execute(sql, list(params)).fetchone()

    def _check_versions(self) -> int:
        """Refuse a directory whose parts this build cannot read as one store.

        Four refusals, in the order a person fixing the directory would want
        them: a part that will not open, a part that is not an outrage store at
        all, parts that disagree about their format, and a format other than
        this build's. Read from each part's footer through duckdb itself, so
        pyarrow is not needed to open a store it would not be used to read.
        """
        duckdb = _duckdb()
        listed = ", ".join(_quoted(part) for part in self._parts)
        probe = duckdb.connect()
        try:
            written = probe.execute(
                f"SELECT file_name, value FROM parquet_kv_metadata([{listed}]) WHERE key = ?",
                [VERSION_KEY],
            ).fetchall()
        except duckdb.Error as exc:
            raise BackendError(
                "duckdb-part-unreadable", path=str(self.path), reason=str(exc)
            ) from exc
        finally:
            probe.close()

        stamps: dict[str, int] = {}
        for name, value in written:
            try:
                stamps[str(name)] = int(bytes(value))
            except ValueError:
                # A stamp that is not a number is not one this package wrote.
                continue
        for part in self._parts:
            if str(part) not in stamps:
                raise BackendError("duckdb-part-not-a-store", path=str(part))

        first = self._parts[0]
        found = stamps[str(first)]
        for part in self._parts[1:]:
            if stamps[str(part)] != found:
                raise BackendError(
                    "duckdb-mixed-versions",
                    path=str(self.path),
                    first=first.name,
                    first_version=found,
                    other=part.name,
                    other_version=stamps[str(part)],
                )
        if found > FORMAT_VERSION:
            raise BackendError(
                "duckdb-format-newer", path=str(self.path), found=found, expected=FORMAT_VERSION
            )
        if found < FORMAT_VERSION:
            raise BackendError(
                "duckdb-format-older", path=str(self.path), found=found, expected=FORMAT_VERSION
            )
        return found

    def close(self) -> None:
        """Drop the database, and every thread's cursor into it with it.

        Safe more than once. Unlike the parquet backend, which closes only this
        thread's file, this closes the one database every cursor is a
        connection to -- duckdb has no other way to give the memory back -- so
        a thread still mid-read when the store is closed has that read fail.
        That is the same promise a mount table already keeps by closing a store
        only once nothing is serving it. The next read from any thread opens a
        new database and carries on.
        """
        with self._lock:
            database, self._database = self._database, None
            spill, self._spill = self._spill, None
            self._generation += 1
        cursor = getattr(self._local, "cursor", None)
        self._local.cursor = None
        if cursor is not None:
            cursor.close()
        if database is not None:
            database.close()
        if spill is not None:
            shutil.rmtree(spill, ignore_errors=True)

    # -- writing, which this backend does not do -------------------------

    @_logged("store_document")
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
        """Refused: a part is added by writing a file, not through a store.

        Validated first, then refused, for the reason
        :meth:`outrage.store_parquet.ParquetStore.store_document` gives: a
        malformed argument is a bug, and "this store does not write" would hide
        it behind a limitation.
        """
        self._validated(
            key,
            content,
            format,
            title=title,
            contents=contents,
            encoding=encoding,
            updated_at=updated_at,
        )
        raise ReadOnlyStoreError(
            "store-read-only",
            key=key,
            path=str(self.path),
            action="write",
            backend=self.backend_name,
        )

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
        """Refused, dry run included, for the reason :meth:`store_document` is."""
        raise ReadOnlyStoreError(
            "store-read-only",
            key=key,
            path=str(self.path),
            action="delete",
            backend=self.backend_name,
        )

    # -- reading by key --------------------------------------------------

    def exists(self, key: str) -> bool:
        """Whether any part holds a row at ``key``."""
        position = keys.sort_form(keys.parse(key).key)
        return self._one("SELECT 1 FROM parts WHERE sort_key = ? LIMIT 1", [position]) is not None

    def level_entry(self, key: str) -> Entry | None:
        """The newest row at ``key`` if there is one, else whether anything lies below.

        The newest rather than one per row, although a listing shows each: this
        answers how one key appears, and a caller reconciling it against
        another store's level wants one answer for one key.
        """
        parsed = keys.parse(key)
        if parsed.key == keys.ROOT:
            raise ValueError("the root is not a child of anything, so it has no listing entry")

        row = self._one(
            f"SELECT key, format, updated_at, chars FROM parts WHERE sort_key = ? "
            f"ORDER BY {_NEWEST} LIMIT 1",
            [keys.sort_form(parsed.key)],
        )
        if row is not None:
            return _entry(row)
        below, bounds = _below("key", parsed.key)
        if self._one(f"SELECT 1 FROM parts WHERE {below} LIMIT 1", bounds) is None:
            return None
        return _implicit(parsed.key)

    @_logged("descendant_count")
    def descendant_count(
        self, key: str, *, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False
    ) -> int:
        """A count of the rows below ``key``, less the metadata unit a delete takes.

        The SQLite backend's query over the parts, and deliberately the same
        predicates: :func:`outrage.store_sqlite._below` and
        :func:`outrage.keys.meta_range` say which keys, and a count here that
        drew the line elsewhere would be a second meaning of "below". A key
        repeated across parts counts once per row.
        """
        where, params = _below_unit(key, key_range, whole_subtree)
        row = self._one(f"SELECT count(*) FROM parts WHERE {where}", params)
        return int(row[0]) if row else 0

    @_logged("subtree_totals")
    def subtree_totals(
        self, key: str, *, key_range: KeyRange = UNBOUNDED, chars: bool = False
    ) -> SubtreeTotals:
        """One aggregate over the subtree: rows, documents, and optionally characters.

        Documents are the rows with no ``meta_name``, which the column records
        for every row below a metadata segment -- the definition
        :class:`~outrage.store.SubtreeTotals` states. The characters come from
        ``chars``, so a total never reads a document; they stay behind the flag
        all the same, because a surface that is opt in on one backend and
        always on in another is two contracts wearing one name.
        """
        below, bounds = _below("key", keys.parse(key).key)
        clauses, params = _range_clauses(key_range)
        within = "".join(f" AND {clause}" for clause in clauses)
        row = self._one(
            "SELECT count(*), count(*) FILTER (WHERE meta_name IS NULL), "
            f"coalesce(sum(chars), 0) FROM parts WHERE {below}{within}",
            [*bounds, *params],
        )
        assert row is not None  # noqa: S101 - an aggregate always returns a row
        return SubtreeTotals(
            keys=int(row[0]), documents=int(row[1]), chars=int(row[2]) if chars else None
        )

    @_logged("latest_change")
    def latest_change(
        self, key: str, *, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False
    ) -> str | None:
        """The newest ``updated_at`` over the rows :meth:`descendant_count` counts."""
        where, params = _below_unit(key, key_range, whole_subtree)
        row = self._one(f"SELECT max(updated_at) FROM parts WHERE {where}", params)
        return row[0] if row else None

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
        """The newest row at ``key``, sliced by the shared slicing.

        **A byte offset is honoured and not accelerated**, as in the parquet
        backend: a value comes out of its part whole, so the content is
        encoded and sliced, and answers the same bytes a backend that seeks
        does.
        """
        parsed = keys.parse(key)
        row = self._one(
            f"SELECT key, content, format, updated_at FROM parts WHERE sort_key = ? "
            f"ORDER BY {_NEWEST} LIMIT 1",
            [keys.sort_form(parsed.key)],
        )
        if row is None:
            beneath = self.descendant_count(key)
            if beneath:
                raise KeyNotFoundError("key-is-a-container", key=key, beneath=beneath)
            raise KeyNotFoundError("key-not-found", key=key)

        check_read_position(
            key, offset=offset, byte_offset=byte_offset, pattern=pattern, occurrence=occurrence
        )
        stored, content, format, updated_at = row

        if byte_offset is None:
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
            return _excerpt(stored, content, format, updated_at, start, length, max_chars)

        data = content.encode()
        read = _sliced(data)
        start = byte_offset
        if pattern is not None:
            found = _find_byte_occurrence(read, len(data), pattern, occurrence, byte_offset)
            if found is None:
                raise PatternNotFoundError(
                    "pattern-not-found",
                    key=key,
                    pattern=pattern,
                    occurrence=occurrence,
                    offset=offset,
                    byte_offset=byte_offset,
                )
            start = found
        return _byte_excerpt(
            stored,
            format,
            updated_at,
            start,
            length,
            max_chars,
            read=read,
            total_bytes=len(data),
            total=len(content),
        )

    # -- reading a level -------------------------------------------------

    @_logged("list_keys")
    def list_keys(
        self,
        key: str | None = None,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        descendant_counts: bool = False,
        descendant_chars: bool = False,
    ) -> Page[Entry]:
        """One level, grouped from the rows below it.

        Each row below ``key`` names the child it is under by its next segment,
        and grouping on that names the level: a child whose own key is among
        its rows is stored, and one whose rows all lie beneath it is implicit.
        **This reads the subtree rather than the level**, which is the one
        read here whose cost is not bounded by what it returns. The parquet
        backend bisects past each child's run; SQL has no bisect-and-skip, so
        a level costs its subtree. Listing the root groups the whole store.

        **A key is listed once, whatever number of parts hold it**, as the
        newest of its rows -- the entry :meth:`level_entry` gives for it, which
        is the contract: that method answers how one key appears in this
        listing. So ``total`` counts keys and ``total_chars`` their newest rows.
        The repeats stay visible where rows are read, in :meth:`get_documents`
        and :meth:`keys_missing_meta`, and are counted by
        :meth:`subtree_totals`, so a listing's ``descendants`` counts every row
        below an entry.

        Two queries: the totals over the whole level, then the page, ordered
        and cut at the cursor. Each child's newest row comes out of the same
        grouping, so a page reads nothing further.
        """
        parent = keys.parse(_scope(key)).key
        level, params = _level(parent)

        totals = self._one(f"SELECT count(*), coalesce(sum(own.chars), 0) FROM ({level})", params)
        assert totals is not None  # noqa: S101 - an aggregate always returns a row

        past, bounds = _past_cursor(parent, cursor)
        children = self._all(
            f"SELECT child, own FROM ({level}) WHERE true{past} ORDER BY first"
            + ("" if limit is None else " LIMIT ?"),
            [*params, *bounds, *([] if limit is None else [limit + 1])],
        )
        # One past the page is all it takes to know there is a next one.
        more = limit is not None and len(children) > limit
        page = children[:limit] if limit is not None else children
        items = [
            _implicit(child)
            if own is None
            else _entry((child, own["format"], own["updated_at"], own["chars"]))
            for child, own in page
        ]
        items = _with_descendants(self, items, counts=descendant_counts, chars=descendant_chars)
        return Page(
            items=items,
            returned=len(items),
            total=int(totals[0]),
            total_chars=int(totals[1]),
            next_cursor=items[-1].key if more and items else None,
        )

    # -- reading a selection ---------------------------------------------

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
        """The selection's totals from one aggregate, and a page read in order.

        The selection is the SQLite backend's predicate, which is why a total
        here and a total there can be compared at all. The page is read a
        batch at a time past the cursor rather than in one query, so that the
        two caps -- ``limit`` and ``max_total_chars`` -- decide how much is
        read, and :func:`_page` decides where it ends.
        """
        where, params = self._selection(subtree, key_range, meta_name=meta_name)
        total, total_chars = self._totals(where, params)

        spent = 0

        def room(taken: list[tuple], row: tuple) -> bool:
            nonlocal spent
            if limit is not None and len(taken) >= limit:
                return False
            expected = min(row[4], max_chars)
            # Never on the first row, or a budget smaller than one document
            # returns an empty page with a cursor that does not move.
            if taken and max_total_chars is not None and spent + expected > max_total_chars:
                return False
            spent += expected
            return True

        rows = self._rows(
            "key, content, format, updated_at, chars",
            where,
            params,
            after=_cursor_bound(cursor),
            batch=BATCH if limit is None else limit + 1,
        )
        taken, more = _page(rows, lambda row: row[0], room)
        items = [
            _excerpt(key, content, format, updated_at, 0, None, max_chars)
            for key, content, format, updated_at, *_ in taken
        ]
        return Page(
            items=items,
            returned=len(items),
            total=total,
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
        """Documents carrying none of ``meta_name``, over one survey window.

        The window is measured at the position the document's metadata *would*
        have taken, synthesised in SQL exactly as the SQLite backend does it --
        see :meth:`outrage.store_sqlite.SqliteStore.missing_meta_stats` for why
        it is that position and not the document's own.
        """
        names = _names(meta_name)
        where, params = self._missing(subtree, key_range, names)

        suffix = min(keys.meta_sort_suffix(name) for name in names)
        root = min(keys.sort_form(keys.META_PREFIX + name) for name in names)
        position = "(CASE WHEN sort_key = '' THEN ? ELSE sort_key || ? END)"
        clauses, bounds = _range_clauses(window, position, [root, suffix])
        where += "".join(f" AND {clause}" for clause in clauses)
        params += bounds

        total, total_chars = self._totals(where, params)
        found: list[str] = []
        if sample > 0 and total:
            found = [
                row[0]
                for row in self._all(
                    f"SELECT key FROM parts WHERE {where} ORDER BY {_ORDER} LIMIT ?",
                    [*params, sample],
                )
            ]
        return MissingMeta(total=total, total_chars=total_chars, sample=found)

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
        """The selection :meth:`missing_meta_stats` counts, listed a page at a time.

        A document repeated across parts is listed once per row, like any
        other listing here, and paged by the same rule.
        """
        where, params = self._missing(subtree, key_range, _names(meta_name))
        total, total_chars = self._totals(where, params)
        rows = self._rows(
            "key",
            where,
            params,
            after=_cursor_bound(cursor),
            batch=BATCH if limit is None else limit + 1,
        )
        taken, more = _page(rows, lambda row: row[0], _limited(limit))
        listed = [row[0] for row in taken]
        return Page(
            items=listed,
            returned=len(listed),
            total=total,
            total_chars=total_chars,
            next_cursor=listed[-1] if more and listed else None,
        )

    # -- selecting -------------------------------------------------------

    def _selection(
        self,
        subtree: BoundedSubtree,
        key_range: KeyRange,
        *,
        meta_name: str | Sequence[str] | None,
    ) -> tuple[str, list[object]]:
        """The WHERE clause a subtree read is about, as the SQLite backend writes it.

        The same three independent conditions -- inside ``subtree``, carrying
        the metadata asked for, inside ``key_range`` -- from the same
        functions, because what they compile to is dialect-neutral SQL and two
        spellings of one selection are two chances to disagree. The one part
        that is not shared is a read scoped *inside* a metadata namespace: see
        :meth:`_scoped_inside`.
        """
        where, params = _subtree_clauses(subtree)
        scope = keys.parse(_scope(subtree.key))
        if scope.is_metadata:
            clauses, bounds = self._scoped_inside(scope, meta_name)
        else:
            clauses, bounds = _meta_clauses(scope, meta_name)
        where += clauses
        params += bounds
        clauses, bounds = _range_clauses(key_range)
        where += clauses
        params += bounds
        return " AND ".join(where) if where else "true", params

    def _scoped_inside(
        self, scope: keys.Key, meta_name: str | Sequence[str] | None
    ) -> tuple[list[str], list[object]]:
        """The metadata test for a read scoped inside a metadata namespace, as keys.

        From inside ``a/!changelog`` the stored ``meta_name`` is a segment above
        the question, so the split has to be read relative to the scope --
        :func:`outrage.keys.relative`, which is the only definition of it. The
        SQLite backend calls that per row from SQL. duckdb can too, but a
        Python function in duckdb needs numpy, which is a large thing to ask an
        install to carry for one rare read; so the namespace's keys are read
        out, tested here, and the ones that pass handed back as a list.

        That costs a read of the namespace, which is what the per-row call
        costs anyway, and a namespace is what is being read.
        """
        wanted = None if meta_name is None else _names(meta_name)
        below, bounds = _below("key", scope.key)
        candidates = self._all(
            f"SELECT DISTINCT key FROM parts WHERE key = ? OR {below}", [scope.key, *bounds]
        )
        chosen = []
        for (candidate,) in candidates:
            seen = keys.relative(candidate, scope.key)
            if wanted is None:
                if seen.meta_name is None:
                    chosen.append(candidate)
            elif seen.meta_name in wanted and seen.meta_path is None:
                chosen.append(candidate)
        return ["key IN (SELECT unnest(?::VARCHAR[]))"], [chosen]

    def _missing(
        self, subtree: BoundedSubtree, key_range: KeyRange, names: list[str]
    ) -> tuple[str, list[object]]:
        """The documents in the selection carrying none of ``names``.

        SQLite correlates each document with the exact key a value would sit
        at. The same fact from the other side: a row whose last segment is
        ``!name`` is a value carried by its ``parent``, so the documents that
        carry one are a set of parents, and the ones that do not are an
        anti-join against it -- one hash join here where a correlated lookup
        per document would be a nested loop.

        Whether a document carries a name is a fact about the store rather
        than about the range, so the carried set is taken over every part and
        every key, not the selection.
        """
        where, params = self._selection(subtree, key_range, meta_name=None)
        marks = ", ".join("?" for _ in names)
        where += (
            " AND key NOT IN (SELECT parent FROM parts WHERE parent IS NOT NULL "
            f"AND split_part(key, '{keys.DELIMITER}', -1) IN ({marks}))"
        )
        return where, [*params, *(keys.META_PREFIX + name for name in names)]

    def _totals(self, where: str, params: Sequence[object]) -> tuple[int, int]:
        row = self._one(
            f"SELECT count(*), coalesce(sum(chars), 0) FROM parts WHERE {where}", params
        )
        assert row is not None  # noqa: S101 - an aggregate always returns a row
        return int(row[0]), int(row[1])

    def _rows(
        self,
        columns: str,
        where: str,
        params: Sequence[object],
        *,
        after: str | None,
        batch: int,
    ) -> Iterator[tuple]:
        """The selection's rows in the store's order, read a batch at a time.

        Past ``after``, a cursor's sort position, and then past the last row of
        the previous batch -- a position in :data:`_ORDER`, which is total, so a
        batch ending inside a run of one key resumes at the next row of that
        run. Nothing here is a cursor a caller sees: those stay keys.

        Each batch is its own query, fetched whole, so nothing is held open
        between them and a caller that stops reading has left no result set
        behind on the thread's cursor. The ``sort_key >=`` beside the row
        comparison is the half duckdb can use to skip row groups.
        """
        position: tuple | None = None
        while True:
            clause, bound = where, list(params)
            if position is not None:
                clause += " AND sort_key >= ? AND (sort_key, part, part_row) > (?, ?, ?)"
                bound += [position[0], *position]
            elif after is not None:
                clause += " AND sort_key > ?"
                bound.append(after)
            fetched = self._all(
                f"SELECT {columns}, sort_key, part, part_row FROM parts WHERE {clause} "
                f"ORDER BY {_ORDER} LIMIT ?",
                [*bound, batch],
            )
            yield from fetched
            if len(fetched) < batch:
                return
            position = fetched[-1][-3:]
            batch = min(batch * 2, BATCH_CEILING)

    # -- maintenance -----------------------------------------------------

    @_logged("backup")
    def backup(
        self,
        destination: str | os.PathLike[str] | None = None,
        *,
        overwrite: bool = False,
    ) -> Backup:
        """A copy of every part into a directory of its own, and a re-read of it.

        The parts are the store, so copying them is the whole copy, and the
        parts copied are the ones this store opened -- not whatever the
        directory holds by now. The copy is then opened as a store of its own,
        which checks every part's format, and its rows counted against these.
        """
        target = self.backup_path(destination, overwrite=overwrite)
        _clear(target)
        try:
            target.mkdir(parents=True)
            for part in self._parts:
                shutil.copyfile(part, target / part.name)
        except OSError as exc:
            shutil.rmtree(target, ignore_errors=True)
            raise BackupError("backup-unwritable", target=str(target), reason=str(exc)) from exc

        expected = self._totals("true", [])[0]
        try:
            with self.opened_at(target) as copy:
                documents = copy._totals("true", [])[0]
                written = copy.stored_format_version
        except BackendError as exc:
            # Rendered here, as `store._said` renders a refusal nested inside a
            # backup's: by now it is a detail of another error rather than one
            # a front end is handed, and `str` of it is the developer's form.
            # Imported where it is used because `messages` is written in terms
            # of the store.
            from . import messages

            raise BackupError(
                "backup-corrupt", target=str(target), integrity=messages.render(exc)
            ) from exc
        if written != self._written_version:
            raise BackupError(
                "backup-schema-mismatch",
                target=str(target),
                found=written,
                expected=self._written_version,
            )
        if documents != expected:
            raise BackupError(
                "backup-short", target=str(target), found=documents, expected=expected
            )
        return Backup(path=target, bytes=_stored_bytes(target), documents=documents, integrity="ok")

    @property
    def stored_format_version(self) -> int:
        """The version every part carries, which opening has checked they agree on."""
        return self._written_version

    def audit_rows(self) -> Iterator[AuditRow]:
        """Every row every part holds, as written, a chunk at a time.

        On a cursor of its own rather than the thread's: a caller walking this
        may ask the store something else between two rows, and a query on the
        same cursor would end the one this is still reading.
        """
        cursor = self._cursor.cursor()
        try:
            cursor.execute("SELECT key, doc_key, meta_name, parent, chars FROM parts")
            while batch := cursor.fetchmany(AUDIT_CHUNK):
                for key, doc_key, meta_name, parent, chars in batch:
                    yield AuditRow(
                        key=key, doc_key=doc_key, meta_name=meta_name, parent=parent, chars=chars
                    )
        finally:
            cursor.close()

    def check_file(self, report: Report) -> None:
        """How many parts, how many rows, and how many of them repeat a key.

        Order is not checked, because nothing here depends on it: the parquet
        backend checks its file is sorted since every read of it bisects, and
        every read here is a query. A repeated key is not a problem either --
        it is legal, and a listing shows it -- so it is reported as the number
        of rows compacting the directory into one file would remove.
        """
        row = self._one("SELECT count(*), count(DISTINCT key) FROM parts")
        assert row is not None  # noqa: S101 - an aggregate always returns a row
        rows, distinct = int(row[0]), int(row[1])
        report.details["parts"] = str(len(self._parts))
        report.details["rows"] = str(rows)
        # The count alone: a report prints each detail as its label and then
        # its value, so a sentence here reads as a sentence with a label in
        # front of it.
        report.details["repeated rows"] = str(rows - distinct)

    def repair(self) -> list[Repaired]:
        """Nothing, and provably so.

        A part is never updated in place, so there is no state a repair could
        move bytes about to fix. A part that is wrong is rebuilt from a source
        that is still right, and a directory with repeated keys is compacted by
        packing it into one file.
        """
        return []


# -- the pieces of a read ----------------------------------------------------


def _parts_in(directory: Path) -> list[Path]:
    """The parts a directory holds, in the order their names sort.

    Dotfiles are passed over: a producer writing a part under a hidden name
    and renaming it into place must not have the half-written file read, and
    some filesystems leave hidden companion files beside every real one. The
    order is the one a repeated key's rows come out in, so a later part is the
    one whose name sorts later.
    """
    return sorted(
        path
        for path in directory.iterdir()
        if path.suffix == PART_SUFFIX and not path.name.startswith(".") and path.is_file()
    )


def _names(meta_name: str | Sequence[str]) -> list[str]:
    """One metadata name or several, as a list, refusing none."""
    names = [meta_name] if isinstance(meta_name, str) else list(meta_name)
    if not names:
        raise ValueError("meta_name must not be an empty sequence")
    return names


def _below_unit(key: str, key_range: KeyRange, whole_subtree: bool) -> tuple[str, list[object]]:
    """The rows strictly below ``key``, less its metadata unit unless ``whole_subtree``.

    What :meth:`~DuckdbStore.descendant_count` and
    :meth:`~DuckdbStore.latest_change` both select, in one place so the two
    answer about the same rows.
    """
    parsed = keys.parse(key)
    below, bounds = _below("key", parsed.key)
    params: list[object] = list(bounds)
    where = below
    if not whole_subtree:
        lo, hi = keys.meta_range(parsed.key)
        where += " AND NOT (key >= ? AND key < ?)"
        params += [lo, hi]
    clauses, extra = _range_clauses(key_range)
    where += "".join(f" AND {clause}" for clause in clauses)
    return where, params + extra


def _level(parent: str) -> tuple[str, list[object]]:
    """A query naming each child of ``parent``, with its own newest row if it has one.

    One row per child: its key, where its subtree starts in the order, and
    ``own`` -- the child's own row, the newest where several parts hold it, or
    NULL for an implicit child with nothing of its own.

    The child is the row's key cut at its next segment, which is the same cut
    :meth:`outrage.store_parquet._Index.children` makes. ``first`` orders the
    children correctly because each child's rows are one contiguous stretch of
    the order, so the stretches sort as their first rows do.

    The newest row is the greatest of a struct whose leading fields are
    :data:`_NEWEST`'s ordering, so the row's other fields come along with it
    and a NULL among them cannot make the aggregate reach for an older row.
    """
    below, bounds = _below("key", parent)
    if parent == keys.ROOT:
        child, cut = f"split_part(key, '{keys.DELIMITER}', 1)", []
    else:
        child = f"? || split_part(key, '{keys.DELIMITER}', ?)"
        cut = [parent + keys.DELIMITER, parent.count(keys.DELIMITER) + 2]
    return (
        "SELECT child, min(sort_key) AS first, "
        "max({'updated_at': updated_at, 'part': part, 'part_row': part_row, "
        "'format': format, 'chars': chars}) FILTER (WHERE key = child) AS own "
        f"FROM (SELECT {child} AS child, key, sort_key, updated_at, part, part_row, "
        f"format, chars FROM parts WHERE {below}) "
        "GROUP BY child"
    ), [*cut, *bounds]


def _past_cursor(parent: str, cursor: str | None) -> tuple[str, list[object]]:
    """The children of ``parent`` that sort after ``cursor``, as a test on :func:`_level`.

    A child is past the cursor when its own position is, and ``first`` is its
    own position whenever the child is stored. An implicit child's first row
    is somewhere below it, so a cursor naming that child -- or naming a key
    beneath it -- sorts before the first row and would bring the child back.
    Which child that could be is one question about the cursor's own key,
    answered here rather than per row: the child of ``parent`` the cursor is at
    or under, which is excluded by name.
    """
    if cursor is None:
        return "", []
    bound = _cursor_bound(cursor)
    at = keys.parse(cursor).key
    within = at if parent == keys.ROOT else keys.strip_prefix(parent, at)
    if not within:
        return " AND first > ?", [bound]
    enclosing = within.split(keys.DELIMITER, 1)[0]
    if parent != keys.ROOT:
        enclosing = parent + keys.DELIMITER + enclosing
    return " AND first > ? AND child <> ?", [bound, enclosing]


def _limited(limit: int | None) -> Callable[[list[Any], Any], bool]:
    """A page's room when all that bounds it is a count."""
    return lambda taken, row: limit is None or len(taken) < limit


def _page[R](
    rows: Iterator[R],
    key_of: Callable[[R], str],
    room: Callable[[list[R], R], bool],
) -> tuple[list[R], bool]:
    """Cut a page from ``rows``, never between two rows of one key.

    ``room`` says whether a row may join the page, given what it already holds
    -- the limit, the character budget, whatever the read is capped by.
    Returns the page and whether anything follows it.

    A cursor names a key, so a page ending between two rows of the same key
    would resume after both and lose one, or before both and repeat. So where
    the first row left out shares a key with the last one taken, the page gives
    back that key's rows and ends in front of them, returning fewer than it had
    room for. **Unless that leaves nothing**: a page that is one key's rows
    from the start cannot end in front of them without making no progress, so
    it takes all of them instead, however many that is -- the one case in which
    a page holds more than ``room`` allows.

    Without repeated keys this is exactly the loop every other backend runs.
    """
    taken: list[R] = []
    for row in rows:
        if room(taken, row):
            taken.append(row)
            continue
        if not taken or key_of(row) != key_of(taken[-1]):
            return taken, True
        run = key_of(row)
        start = len(taken)
        while start and key_of(taken[start - 1]) == run:
            start -= 1
        if start:
            return taken[:start], True
        taken.append(row)
        for row in rows:
            if key_of(row) != run:
                return taken, True
            taken.append(row)
        return taken, False
    return taken, False


def _entry(row: tuple) -> Entry:
    """A stored row -- key, format, updated_at, chars -- as a listing entry."""
    key, format, updated_at, chars = row[:4]
    return Entry(key=key, kind=entry_kind(key), size=chars, format=format, updated_at=updated_at)


def _implicit(key: str) -> Entry:
    """A key that holds nothing and has something beneath it, as a listing entry."""
    return Entry(key=key, kind="implicit", size=None, format=None, updated_at=None)


__all__ = [
    "AUDIT_CHUNK",
    "BATCH",
    "BATCH_CEILING",
    "DEFAULT_STORE_DIR",
    "MEMORY_LIMIT",
    "PART_SUFFIX",
    "DuckdbStore",
]
