"""The parquet backend: one columnar file, written once and read many times.

The second implementation of :class:`rage.store.Store`, and the one the
reference-base case is for -- use 2 of ``project/reference/scale``: tens of
thousands of small documents, built in one pass rather than accumulated, and
reached by survey and search. It answers the same twelve operations
:class:`~rage.store_sqlite.SqliteStore` does, in the same vocabulary, and
shares none of the storage.

**It does not write.** A parquet file is not updated in place, so
:meth:`~ParquetStore.store_document` and :meth:`~ParquetStore.delete` refuse
rather than pretend. Documents get in through :meth:`ParquetStore.build`,
which writes the whole file in one pass, and through ``rage pack``, which is
the command line over it. That refusal is the backend's own and not a mount's:
see :class:`rage.store.ReadOnlyStoreError` for the difference, which is that
no flag exists to take this one off.

The file is one row per key, carrying the columns
:class:`~rage.store_sqlite.SqliteStore` keeps plus ``chars``, sorted by
``sort_key``. Two of those are the whole design:

* **Sorted by ``sort_key``** means every stretch of the key order this store's
  vocabulary can name -- a :class:`~rage.store.KeyRange`, a page cursor, a
  subtree -- is a *contiguous run of rows*. So a bound is found by bisecting
  rather than by testing every row, and the content of a page comes out of the
  one or two row groups it falls in. ``planned/parquet`` predicted this would
  be the columnar payoff, and it is.
* **``chars`` is precomputed.** SQLite answers ``total_chars`` with
  ``sum(length(content))``, which is per-row work over the column holding all
  the bytes. Written down at build time it is a small integer column, so
  **every total, and every listing, is answered without the content column
  being opened at all** -- ``total_chars`` over forty thousand documents costs
  a scan of a small integer column rather than of the corpus, and
  :meth:`~ParquetStore.list_keys` reports each entry's ``size`` from it.

  What that does *not* mean is that a survey reads no content. A survey
  returns the title text, and a title is a document like any other, so its
  rows are read -- but only the rows on the page, and never the documents
  being surveyed. The distinction is worth keeping straight, and
  ``test_chars_is_stored_so_a_total_never_opens_the_content_column`` pins
  which half is which.

What that buys is bounded by one thing worth knowing before reading further.
A :class:`~rage.store.Page` reports ``total`` and ``total_chars`` over the
whole *selection*, and a total over an arbitrary predicate cannot come from
row-group statistics -- it needs every row the predicate selects. So the
contract obliges this backend to hold the small columns whole, in memory, and
only ``content`` is read lazily. That is why :meth:`ParquetStore._index` is
built once per file and ``content`` never joins it.

pyarrow is an optional dependency: ``pip install rage[parquet]``. It is
imported inside this module and this module is imported only by
:func:`rage.store._backend_for`, so an install without it is unaffected until
something names a ``.parquet`` file.
"""

from __future__ import annotations

import os
import shutil
import threading
from bisect import bisect_left, bisect_right
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import keys
from .eventlog import EventLog
from .maintenance import Problem, Repaired, Report, _listed
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
    KeyNotFoundError,
    KeyRange,
    MissingMeta,
    Page,
    PatternNotFoundError,
    ReadOnlyStoreError,
    Store,
    _cursor_bound,
    _excerpt,
    _find_occurrence,
    _logged,
    _now,
    _position,
    _scope,
)

#: What a parquet store's file is called when a caller names none. Beside
#: :data:`rage.store_sqlite.DEFAULT_STORE_FILE`, each in its own module, and
#: it is the extension of this one that :func:`rage.store._backend_for` reads
#: to know which backend a file wants.
DEFAULT_STORE_FILE = "store.parquet"

#: The layout this build writes, recorded in the file's own key-value metadata
#: so a file from a later build is refused rather than read with the wrong
#: shape assumed. The same rule as :data:`rage.store_sqlite.SCHEMA_VERSION`
#: without the migrations: nothing here is ever updated in place, so an old
#: file is repacked rather than upgraded.
FORMAT_VERSION = 1

#: Where that version is written.
VERSION_KEY = b"rage.format-version"

#: The columns held whole once a file is opened: everything except ``content``.
#: Naming them is what keeps the promise in the module docstring checkable --
#: the expensive column is absent from this list, and every read that does not
#: return document text stops here.
INDEX_COLUMNS = (
    "key",
    "doc_key",
    "meta_name",
    "parent",
    "format",
    "updated_at",
    "sort_key",
    "chars",
)

#: Rows per row group. The unit parquet reads content in, so it is the unit a
#: page's text is paid for in: too large and a five-document read decompresses
#: thousands, too small and the per-group statistics and headers outweigh the
#: data they describe. Sized for the reference case, where a document is a few
#: hundred characters and a page is tens of them.
ROW_GROUP_SIZE = 2048

#: How the content column is compressed. Reference text compresses very well
#: and zstd decompresses fast enough that a row group is cheap to open; it
#: ships in the pyarrow wheel, so this costs no further dependency.
COMPRESSION = "zstd"


def _arrow() -> tuple[Any, Any]:
    """pyarrow, or a sentence saying it is not installed.

    Imported through a function so the failure is *this* package's to explain.
    A ``ModuleNotFoundError`` surfacing out of a mount table would name pyarrow
    at somebody who asked for a store, and say nothing about the extra that
    provides it.
    """
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - exercised by uninstalling
        raise BackendError("parquet-needs-pyarrow", reason=str(exc)) from exc
    return pa, pq


@dataclass(frozen=True, slots=True)
class _Row:
    """One key's columns, less its content.

    Slotted because there is one of these per key and the reference case has
    tens of thousands: the point of leaving ``content`` out is that what stays
    resident is small, and a dict per row would give most of that back.

    ``position`` is the row's index in the file, which is how the content it
    does not carry is found again.
    """

    key: str
    doc_key: str
    meta_name: str | None
    parent: str
    format: str | None
    updated_at: str
    sort_key: str
    chars: int
    position: int


@dataclass(frozen=True, slots=True)
class _Index:
    """Everything about a file that is not document text.

    Built once, on the first read, and thrown away when the store is closed.
    Four structures, and each exists because one operation cannot be answered
    from the others in less than a scan:

    ``rows`` is every row in ``sort_key`` order, which is the order the file is
    written in, so a bound on the order is a slice of this list.

    ``by_key`` answers "is this key stored, and where", which is
    :meth:`ParquetStore.exists` and the first half of every read.

    ``children`` maps a key to the keys immediately below it, **implicit ones
    included**. A key that holds nothing and has something beneath it appears
    in its parent's listing, and there is no row anywhere that says so; the
    SQLite backend recovers it with a ``DISTINCT`` over truncated parents, and
    here it is cheaper to record it while the rows are being read once anyway.

    ``meta_names`` maps a document key to the metadata names attached to it,
    which is what turns SQLite's ``NOT EXISTS`` self-join into a set test.
    """

    rows: list[_Row]
    by_key: dict[str, _Row]
    children: dict[str, set[str]]
    meta_names: dict[str, set[str]]

    #: ``rows`` projected onto ``sort_key``, so :func:`bisect` can seek without
    #: a key function per comparison. Held rather than recomputed because every
    #: bounded read bisects it at least twice.
    order: list[str]

    #: The first row position of each row group, cumulative, so a row's
    #: position tells you which group to open for its content. Here rather than
    #: lazily on the store because it is one more fact read off the file, and
    #: a second piece of lazily built shared state is a second thing to get
    #: right under threads for no gain.
    group_starts: list[int]


class ParquetStore(Store):
    """A document store held in a single parquet file, read only."""

    default_filename = DEFAULT_STORE_FILE
    backend_name = "parquet"
    format_version = FORMAT_VERSION
    writable = False

    def __init__(
        self,
        directory: str | os.PathLike[str] | None = None,
        *,
        filename: str | os.PathLike[str] | None = None,
        log: EventLog | None = None,
    ) -> None:
        # Where the file is, and the directory around it, are the base's
        # business, exactly as they are for SQLite.
        super().__init__(directory, filename=filename, log=log)
        if not self.path.exists():
            # Refused rather than created. Every other backend can be opened
            # empty because a first write would fill it; this one has no first
            # write, so an empty parquet store is a thing that can only ever
            # read back empty. A mistyped name would otherwise mount as a
            # reference base that is simply missing -- the same argument
            # ``open_mounts`` makes for a read-only mount, one step further
            # along, and here it holds however the store was opened.
            raise BackendError("parquet-store-missing", path=str(self.path))
        # One open file per thread, and one decoded row group per thread, for
        # the reason `SqliteStore` keeps one connection per thread: the server
        # runs its sync tool handlers in a worker pool, and a reader whose
        # state is shared between them returns another thread's answer. That
        # was a live defect once already -- `planned/concurrency` -- and it was
        # silent about a third of the time, which is what makes it worth
        # paying for here before anyone hits it.
        self._local = threading.local()
        # The index *is* shared, because it is immutable once built and there
        # is no reason to hold one copy per thread of something that can be
        # tens of megabytes. The lock is only around building it.
        self._built: _Index | None = None
        self._lock = threading.Lock()
        self._check_version()

    # -- the file --------------------------------------------------------

    def _check_version(self) -> None:
        """Refuse a file this build does not know how to read.

        On the way in rather than on the first read, so a mount table that
        names an unreadable file fails while somebody is still looking at the
        command that named it.
        """
        metadata = self._parquet.schema_arrow.metadata or {}
        written = metadata.get(VERSION_KEY)
        if written is None:
            raise BackendError("parquet-not-a-store", path=str(self.path))
        if int(written) > FORMAT_VERSION:
            raise BackendError(
                "parquet-format-newer",
                path=str(self.path),
                found=int(written),
                expected=FORMAT_VERSION,
            )

    @property
    def _parquet(self) -> Any:
        """The open file, opened on first use.

        One per thread, for the reason ``SqliteStore`` opens one connection per
        thread. A ``ParquetFile`` holds a file object with a seek position and
        a reader with buffered state, so two threads reading row groups through
        one handle is the same shape of mistake -- and the file is read-only
        and immutable, so a handle per thread costs a footer read and buys the
        whole problem away.

        **Never hand one of these to another thread**, which is the constraint
        ``planned/concurrency`` records for SQLite and which holds here for the
        same reason.
        """
        opened: Any | None = getattr(self._local, "file", None)
        if opened is None:
            _, pq = _arrow()
            opened = self._local.file = pq.ParquetFile(self.path)
        return opened

    @property
    def _index(self) -> _Index:
        """The small columns, read whole on first use.

        Lazy because mounting a reference base should cost nothing until it is
        read: a server holding one beside a session store must not pay for the
        reference base to answer a question about the session. Opening the
        store reads the file's footer, to check the version while somebody is
        still looking at the command that named it; the columns wait until
        something asks.

        Read whole because the contract asks for totals. ``Page.total`` and
        ``Page.total_chars`` describe the selection rather than the page, and
        no row-group statistic answers "how many rows match this predicate" --
        only "could any row in this group match". Recorded in
        ``context/35/findings``: that field is what decides how much of a
        columnar file a read has to open.
        """
        built = self._built
        if built is None:
            with self._lock:
                # Re-checked inside the lock: two threads can both find it
                # missing, and the second would otherwise build a second copy
                # and hand back a different object from the one the first
                # published.
                if self._built is None:
                    self._built = self._read_index()
                built = self._built
        return built

    def _read_index(self) -> _Index:
        """Every column but ``content``, as rows and the three lookups over them.

        A single pass. The columns arrive as Arrow arrays and are converted
        once with ``to_pylist``; going through Arrow scalars per cell costs
        more than the conversion does, and everything below wants Python
        strings anyway.
        """
        table = self._parquet.read(columns=list(INDEX_COLUMNS))
        columns = {name: table.column(name).to_pylist() for name in INDEX_COLUMNS}

        rows: list[_Row] = []
        by_key: dict[str, _Row] = {}
        children: dict[str, set[str]] = {}
        meta_names: dict[str, set[str]] = {}

        for position in range(table.num_rows):
            row = _Row(
                key=columns["key"][position],
                doc_key=columns["doc_key"][position],
                meta_name=columns["meta_name"][position],
                parent=columns["parent"][position],
                format=columns["format"][position],
                updated_at=columns["updated_at"][position],
                sort_key=columns["sort_key"][position],
                chars=columns["chars"][position],
                position=position,
            )
            rows.append(row)
            by_key[row.key] = row
            if row.meta_name is not None:
                meta_names.setdefault(row.doc_key, set()).add(row.meta_name)
            _record_ancestry(children, row.key)

        metadata = self._parquet.metadata
        starts = [0]
        for group in range(metadata.num_row_groups):
            starts.append(starts[-1] + metadata.row_group(group).num_rows)

        return _Index(
            rows=rows,
            by_key=by_key,
            children=children,
            meta_names=meta_names,
            order=[row.sort_key for row in rows],
            # The running total has one entry per group plus a tail past the
            # last, and the tail is dropped: a bisect over the starts alone
            # lands on the group a position is in, and an empty file keeps one
            # entry so the arithmetic needs no special case.
            group_starts=starts[:-1] or [0],
        )

    def _content(self, row: _Row) -> str:
        """The text of one row, read from the row group it falls in.

        The one place ``content`` is touched. A page of a survey never gets
        here at all, and a page of documents gets here for the rows it is
        actually returning -- which, because the file is in ``sort_key`` order
        and a page is a contiguous run of it, fall in one or two groups.

        The last group read is kept -- per thread, like the handle -- which is
        what makes a page of twenty documents one decompression rather than
        twenty. One group rather than a cache of several: a read that walks the
        file in order never looks back, and holding more would grow with the
        corpus for no reader that exists.
        """
        group, offset = self._locate(row.position)
        # Read into a local before it is used, not tested on the attribute and
        # then read from it again. Even per-thread that is the habit worth
        # keeping: the two reads are what let a swapped cache return content
        # from a different row group, and it would return it silently.
        cached: tuple[int, list[str]] | None = getattr(self._local, "cache", None)
        if cached is None or cached[0] != group:
            table = self._parquet.read_row_group(group, columns=["content"])
            cached = (group, table.column("content").to_pylist())
            self._local.cache = cached
        return cached[1][offset]

    def _locate(self, position: int) -> tuple[int, int]:
        """Which row group a row is in, and where within it."""
        starts = self._index.group_starts
        group = bisect_right(starts, position) - 1
        return group, position - starts[group]

    def close(self) -> None:
        """Drop the file handle and the index built over it.

        Safe more than once, which the contract requires and a store held by a
        mount table relies on: the table closes everything it opened when a
        single failure part way through means unwinding.

        Only this thread's handle, for the reason :meth:`_parquet` gives. The
        rest are released when their thread ends or the process exits.
        """
        opened: Any | None = getattr(self._local, "file", None)
        if opened is not None:
            opened.close()
            self._local.file = None
        self._local.cache = None
        # The index is the memory this store holds, and a caller saying it has
        # finished means to have it back. Another thread still reading rebuilds
        # it from its own handle, which costs work and breaks nothing --
        # unlike a file handle, which is why that one is only ever this
        # thread's to close.
        with self._lock:
            self._built = None

    # -- writing, which this backend does not do -------------------------

    @_logged("store_document")
    def store_document(
        self,
        key: str,
        content: str,
        format: str | None = None,
        *,
        title: str | None = None,
        encoding: str | None = None,
    ) -> str:
        """Refused: a parquet file is not updated in place.

        Validated first, then refused, and the order is deliberate. A caller
        who passed a malformed key and a caller who passed a good one are
        asking different questions, and answering both with "this store does
        not write" hides a bug behind a limitation -- the argument would be
        just as wrong against the store they meant to write to. So this calls
        :meth:`Store._validated` exactly as a writing backend does, and every
        refusal in it happens here too.

        Logged like any other write, and for the same reason: what the event
        log is for is what a store was *asked* to do, and a refused write is
        one of the more interesting things anyone asks. ``_logged`` records the
        refusal beside the arguments and re-raises.

        :meth:`build` is the way in, and ``rage pack`` is the command line
        over it.
        """
        self._validated(key, content, format, title=title, encoding=encoding)
        raise ReadOnlyStoreError("store-read-only", key=key, path=str(self.path), action="write")

    @_logged("delete")
    def delete(
        self, key: str, recursive: bool = False, *, key_range: KeyRange = UNBOUNDED
    ) -> list[str]:
        """Refused, for the reason :meth:`store_document` is."""
        raise ReadOnlyStoreError(
            "store-read-only", key=key, path=str(self.path), action="delete"
        )

    # -- reading ---------------------------------------------------------

    def exists(self, key: str) -> bool:
        """One dict lookup, over the index rather than the file."""
        return keys.parse(key).key in self._index.by_key

    def level_entry(self, key: str) -> Entry | None:
        """The stored row if there is one, else whether anything lies below.

        The second half is a lookup rather than a scan because ``children``
        already records implicit keys -- see :class:`_Index`.
        """
        parsed = keys.parse(key)
        if parsed.key == keys.ROOT:
            raise ValueError("the root is not a child of anything, so it has no listing entry")

        row = self._index.by_key.get(parsed.key)
        if row is not None:
            return _entry(row)
        if self._index.children.get(parsed.key):
            return Entry(key=parsed.key, kind="implicit", size=None, format=None, updated_at=None)
        return None

    @_logged("descendant_count")
    def descendant_count(self, key: str, *, key_range: KeyRange = UNBOUNDED) -> int:
        """How many rows lie strictly below ``key``, within ``key_range``.

        Counted over the index. A ``doc_key`` test is not a bound on the order,
        so this cannot bisect the way a range can; the range half does, and
        narrows what the ``doc_key`` half then has to look at.
        """
        index = self._index
        lower, upper = _span(index.order, key_range)
        # Narrowed by the subtree's own bounds first. It does not *answer* the
        # question -- `k/!title` sorts inside them and is not below `k` -- but
        # it is what keeps a count of one subtree from walking the corpus.
        inner, outer = _span(index.order, _subtree_range(key))
        below = _below(keys.parse(key).doc_key)
        return sum(
            1
            for row in index.rows[max(lower, inner) : min(upper, outer)]
            if below(row.doc_key)
        )

    @_logged("retrieve_document")
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
        """One index lookup, one row group, and the shared slicing.

        The slicing is :func:`rage.store._excerpt`, unchanged and unwrapped:
        how ``length`` and ``max_chars`` combine is the store's policy and not
        this backend's, and two backends that sliced differently would return
        different documents for the same call.
        """
        parsed = keys.parse(key)
        row = self._index.by_key.get(parsed.key)
        if row is None:
            beneath = 0 if parsed.is_metadata else self.descendant_count(key)
            if beneath:
                raise KeyNotFoundError("key-is-a-container", key=key, beneath=beneath)
            raise KeyNotFoundError("key-not-found", key=key)

        content = self._content(row)
        if offset < 0:
            raise ValueError("offset must not be negative")

        start = offset
        if pattern is not None:
            if not pattern:
                raise ValueError("pattern must not be empty")
            if occurrence < 0:
                raise ValueError("occurrence must not be negative")
            start = _find_occurrence(content, pattern, occurrence, offset)
            if start is None:
                raise PatternNotFoundError(
                    "pattern-not-found",
                    key=key,
                    pattern=pattern,
                    occurrence=occurrence,
                    offset=offset,
                )

        return _excerpt(row.key, content, row.format, row.updated_at, start, length, max_chars)

    @_logged("list_keys")
    def list_keys(
        self,
        key: str | None = None,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> Page[Entry]:
        """One level, real and implicit keys together.

        ``children`` holds both, so unlike SQLite there are no two halves to
        merge and no risk of cutting them separately -- which is the defect
        that shape has to be careful about. The level's totals are over the
        whole level and so unaffected by the cursor, and the characters come
        from ``chars`` without any content being read.
        """
        parent = keys.parse(_scope(key)).doc_key
        names = self._index.children.get(parent, set())
        bound = _cursor_bound(cursor)

        # Sorted on the form, and the form is kept rather than recomputed for
        # the cursor test below: `sort_form` parses and pads a key, and a level
        # of ten thousand would otherwise do it twice each.
        ordered = sorted(
            ((keys.sort_form(name), self._as_child(name)) for name in names),
            key=lambda pair: pair[0],
        )
        entries = [entry for _, entry in ordered]
        candidates = [entry for form, entry in ordered if bound is None or form > bound]

        items = candidates if limit is None else candidates[:limit]
        more = limit is not None and len(candidates) > limit
        # Over the level rather than the page: what a caller cannot work out
        # from a page is how much of the whole they are holding.
        total_chars = sum(entry.size or 0 for entry in entries)
        return Page(
            items=items,
            returned=len(items),
            total=len(entries),
            total_chars=total_chars,
            next_cursor=items[-1].key if more and items else None,
        )

    def _as_child(self, key: str) -> Entry:
        """A child of some level as it appears there, stored or implicit.

        Named apart from :meth:`level_entry`, which answers a different
        question: that one is asked about a key that may not be there at all
        and returns None when it is not, while this is asked about a name
        already known to be in the level and so always has an answer.
        """
        row = self._index.by_key.get(key)
        if row is not None:
            return _entry(row)
        return Entry(key=key, kind="implicit", size=None, format=None, updated_at=None)

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
        it, which is the same split SQLite makes with a separate ``count(*)``:
        a cursor moves as a caller pages and must not reach ``total``.

        **``total_chars`` is answered from ``chars`` and touches no content.**
        The page's documents are then read one row group at a time, so a survey
        -- which returns metadata, and whose documents are short -- opens the
        content column for a page's worth of rows and no more.
        """
        selection = self._selection(subtree, key_range, meta_name=meta_name)
        total = len(selection)
        total_chars = sum(row.chars for row in selection)

        items: list[Excerpt] = []
        spent = 0
        more = False
        for row in _after(selection, _cursor_bound(cursor)):
            if limit is not None and len(items) >= limit:
                more = True
                break
            expected = min(row.chars, max_chars)
            if items and max_total_chars is not None and spent + expected > max_total_chars:
                # Never on the first document, or a budget smaller than one
                # document returns an empty page with a cursor that does not
                # move, and the caller loops forever making no progress.
                more = True
                break
            excerpt = _excerpt(
                row.key, self._content(row), row.format, row.updated_at, 0, None, max_chars
            )
            items.append(excerpt)
            spent += excerpt.returned

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
        """Documents carrying none of ``meta_name``, over one window.

        The window is measured at the position a document's metadata *would*
        have taken, not at the document's own -- the contract says so, and
        ``test_survey_windows_tile_over_adversarial_keys`` is the guard. That
        synthesised position is ``sort_key`` plus a fixed suffix, which is
        monotone in ``sort_key``, so the rows satisfying a bound on it are
        still a contiguous run and this still bisects. SQLite cannot: the
        concatenation is not sargable there, so it scans the selection and pays
        about 6% for it. Here the ordering does the work.
        """
        names = _names(meta_name)
        missing = self._missing(subtree, key_range, names)

        # Where the row would have sorted had the document carried the name.
        # Asked for several, a document would first have appeared at the
        # earliest of them.
        suffix = min(keys.meta_sort_suffix(name) for name in names)
        # The root is the one document whose metadata is not its sort form plus
        # a suffix: it contributes no segment, so `!title` is a *first* segment
        # rather than one joined onto a previous.
        root = min(keys.sort_form(keys.META_PREFIX + name) for name in names)

        def position(row: _Row) -> str:
            return root if row.sort_key == keys.ROOT else row.sort_key + suffix

        lower, upper = _span([position(row) for row in missing], window)
        within = missing[lower:upper]
        return MissingMeta(
            total=len(within),
            total_chars=sum(row.chars for row in within),
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

        Shared rather than reimplemented, for the reason the SQLite backend
        shares its ``NOT EXISTS``: the survey, its count and the list of what
        it could not see have to agree about what was in range, and two
        expressions of the same predicate are two chances to disagree.
        """
        missing = self._missing(subtree, key_range, _names(meta_name))
        total_chars = sum(row.chars for row in missing)

        found = list(_after(missing, _cursor_bound(cursor)))
        items = found if limit is None else found[:limit]
        more = limit is not None and len(found) > limit
        return Page(
            items=[row.key for row in items],
            returned=len(items),
            total=len(missing),
            total_chars=total_chars,
            next_cursor=items[-1].key if more and items else None,
        )

    # -- selecting -------------------------------------------------------

    def _in_range(self, key_range: KeyRange) -> list[_Row]:
        """The rows inside ``key_range``, as a slice of the file's own order.

        The bisect, and the reason the file is sorted. Every bound a
        :class:`~rage.store.KeyRange` can carry is a comparison against a row's
        position in the order the rows are already in, so the answer is a
        contiguous run found by two searches rather than a predicate evaluated
        against every row.
        """
        lower, upper = _span(self._index.order, key_range)
        return self._index.rows[lower:upper]

    def _selection(
        self,
        subtree: BoundedSubtree,
        key_range: KeyRange,
        *,
        meta_name: str | Sequence[str] | None,
    ) -> list[_Row]:
        """The rows a subtree read is about, in key order.

        The same three independent conditions the SQLite backend ANDs
        together, and all three are required to hold: a row is in the selection
        when it is inside ``subtree``, carries the metadata asked for, **and**
        falls inside ``key_range``. A page cursor is not among them, which is
        what keeps ``total`` describing the selection rather than the remainder
        of it.

        **Both the range and the subtree are bisected**, and their spans are
        intersected before either is sliced -- see :func:`_subtree_range` for
        why a subtree is a stretch of the order too. What is left to test per
        row is the depth budget, which is not a bound on the order at all, and
        the metadata name.
        """
        wanted = None if meta_name is None else _names(meta_name)
        index = self._index
        lower, upper = _span(index.order, key_range)
        inner, outer = _span(index.order, _subtree_range(subtree.key))
        rows = index.rows[max(lower, inner) : min(upper, outer)]

        deep_enough = _depth_test(subtree)
        return [
            row
            for row in rows
            if deep_enough(row)
            and (row.meta_name in wanted if wanted is not None else row.meta_name is None)
        ]

    def _missing(
        self, subtree: BoundedSubtree, key_range: KeyRange, names: list[str]
    ) -> list[_Row]:
        """Documents in the selection carrying none of ``names``.

        SQLite's ``NOT EXISTS`` against a self-join, as a set test: the index
        already records which metadata names each document key carries, so this
        costs a dict lookup per document rather than a correlated subquery.
        That is the one place the columnar layout is unambiguously the better
        shape -- ``planned/parquet`` said this would stop being an anti-join,
        and it has.
        """
        carried = self._index.meta_names
        return [
            row
            for row in self._selection(subtree, key_range, meta_name=None)
            if not carried.get(row.doc_key, _NOTHING).intersection(names)
        ]

    # -- maintenance -----------------------------------------------------

    @_logged("backup")
    def backup(
        self,
        destination: str | os.PathLike[str] | None = None,
        *,
        overwrite: bool = False,
    ) -> Backup:
        """A file copy, and a re-read to show it is one.

        **The file really is the store here**, which is the difference from
        SQLite worth stating out loud. There is no WAL and no journal, so
        nothing has been written anywhere else and a copy cannot be silently
        short -- the trap ``project/reference/snapshots`` exists for is that
        backend's rather than the store's, and this is the evidence.

        The copy is still verified rather than assumed. What can go wrong is
        the copy itself: a truncated write, a full disk. So the copy is
        reopened, its version read and its rows counted against the source, on
        the principle the SQLite backend states -- a copy that opens cleanly is
        not evidence of a complete one.
        """
        target = self.backup_path(destination, overwrite=overwrite)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copyfile(self.path, target)
        except OSError as exc:
            target.unlink(missing_ok=True)
            raise BackupError("backup-unwritable", target=str(target), reason=str(exc)) from exc

        expected = self._parquet.metadata.num_rows
        _, pq = _arrow()
        try:
            copy = pq.ParquetFile(target)
        except Exception as exc:
            raise BackupError(
                "backup-corrupt", target=str(target), integrity=str(exc)
            ) from exc
        try:
            documents = copy.metadata.num_rows
            written = (copy.schema_arrow.metadata or {}).get(VERSION_KEY)
        finally:
            copy.close()

        if written is None or int(written) != FORMAT_VERSION:
            raise BackupError(
                "backup-schema-mismatch",
                target=str(target),
                found=0 if written is None else int(written),
                expected=FORMAT_VERSION,
            )
        if documents != expected:
            raise BackupError(
                "backup-short", target=str(target), found=documents, expected=expected
            )
        return Backup(
            path=target,
            bytes=target.stat().st_size,
            documents=documents,
            # Parquet's own footer checksum is what opening the file above
            # verified; there is no second integrity pass to run, and saying
            # 'ok' here means exactly that the file reads as a parquet store.
            integrity="ok",
        )

    @property
    def stored_format_version(self) -> int:
        """From the file's own key-value metadata, where ``build`` wrote it.

        ``_check_version`` has already refused anything newer than this build
        by the time a check can run, so the error branch of
        ``maintenance._check_format_version`` is unreachable here -- see the
        note there. A file older than this build still opens, and still says
        so.
        """
        return int((self._parquet.schema_arrow.metadata or {})[VERSION_KEY])

    def audit_rows(self) -> Iterator[AuditRow]:
        """Every row, from the index, without opening the content column.

        The index is exactly the columns a check wants and it is resident
        already -- ``chars`` most of all, which is the column this backend has
        and SQLite does not, precisely so that counting characters never costs
        a read of the text.
        """
        for row in self._index.rows:
            yield AuditRow(
                key=row.key,
                doc_key=row.doc_key,
                meta_name=row.meta_name,
                parent=row.parent,
                chars=row.chars,
            )

    def check_file(self, report: Report) -> None:
        """Whether the file is still in the order every read of it assumes.

        This is parquet's ``integrity_check``, and it exists for the same
        reason: a file that fails it reads *wrongly* rather than failing to
        read. Every lookup here bisects ``sort_key`` -- that is what makes a
        bounded range 0.04 ms rather than 14 -- and bisection over rows that
        are not sorted returns a confidently wrong answer with nothing
        anywhere to contradict it.

        Cheap enough to do unconditionally: one pass over a column that is
        resident already, against a file that promised to be sorted when it
        was written.
        """
        index = self._index
        report.details["rows"] = str(len(index.rows))
        report.details["row groups"] = str(self._parquet.metadata.num_row_groups)

        # ``order`` is the sort_key column in the order the file holds it,
        # never re-sorted on the way in -- which is what makes comparing it
        # with itself a check rather than a tautology.
        out_of_order = [
            index.rows[position].key
            for position in range(1, len(index.order))
            if index.order[position] < index.order[position - 1]
        ]
        report.details["order"] = "sorted" if not out_of_order else "not sorted"
        if out_of_order:
            report.problems.append(
                Problem(
                    "error",
                    "the file is not in sort order",
                    f"{_listed(out_of_order)}; every read bisects this column, so a file "
                    f"out of order answers wrongly rather than failing. Rebuild it with "
                    f"rage pack.",
                )
            )

    def repair(self) -> list[Repaired]:
        """Nothing, and that is the honest answer rather than a silence.

        A repair moves bytes about inside a mutable file: a checkpoint folds a
        sidecar back, a vacuum compacts free pages. A parquet store is one
        immutable file with no sidecar and no free pages, so there is no state
        it can reach that moving bytes would fix -- which is *provable* here,
        and so different in kind from "nothing to check", a sentence that would
        read as a clean bill of health for a store nothing looked at.

        A file that fails :meth:`check_file` is not repaired but rebuilt, by
        ``rage pack``, from a source that is still right.
        """
        return []

    # -- building --------------------------------------------------------

    @classmethod
    def check_target(
        cls, path: str | os.PathLike[str], *, overwrite: bool = False
    ) -> Path:
        """Where a build would write, refusing a file already there.

        Public and separate from :meth:`build` so a caller can hit the refusal
        **before** reading its source. A pack reads the whole corpus before it
        writes anything, so leaving this to the write means a refusal that
        arrives after forty thousand documents have been read — which is the
        right answer delivered at the least useful moment. ``build`` calls it
        too, so the guarantee does not depend on the caller remembering.
        """
        target = Path(path).expanduser()
        if target.exists() and not overwrite:
            raise BackendError("parquet-target-exists", path=str(target))
        return target

    @classmethod
    def build(
        cls,
        path: str | os.PathLike[str],
        documents: Iterable[tuple[str, str, str | None, str | None]],
        *,
        overwrite: bool = False,
    ) -> int:
        """Write a whole parquet store in one pass, and return the row count.

        ``documents`` yields ``(key, content, format, updated_at)``. A format
        of None is detected from the content and an ``updated_at`` of None is
        now, so a caller with a directory of files supplies neither and a
        caller copying an existing store supplies both -- which is what lets
        ``rage pack`` keep timestamps when packing a store and invent them when
        packing a tree.

        Every key goes through :meth:`Store._validated`, the same check a
        writing backend applies, because this is where a document enters the
        namespace and a build that admitted a key ``store_document`` would
        refuse would make this file a second namespace. A ``?`` is refused
        rather than allocated: allocation reads the store to find a free number
        and there is no store to read yet, and a number allocated against a
        half-written file would not be the one a reader later sees.

        **The rows are held before they are written.** They must be sorted by
        ``sort_key`` for anything above to bisect, and a sort needs all of
        them. For the corpus this is for -- tens of thousands of small
        documents -- that is a few hundred megabytes at worst and one pass; a
        corpus past that wants an external sort, and this should say so rather
        than quietly swapping.
        """
        pa, pq = _arrow()
        target = cls.check_target(path, overwrite=overwrite)

        rows: dict[str, tuple[keys.Key, str, str, str]] = {}
        for key, content, format, updated_at in documents:
            parsed, decoded, resolved, _ = cls._validated(
                key, content, format, title=None, encoding=None
            )
            if parsed.has_wildcard:
                raise BackendError("parquet-build-wildcard", key=key)
            # Last one wins, which is what overwriting means everywhere else in
            # the store. Silently keeping the first would make the result
            # depend on an iteration order the caller did not choose.
            rows[parsed.key] = (parsed, decoded, resolved, updated_at or _now())

        ordered = sorted(rows.values(), key=lambda row: keys.sort_form(row[0].key))
        table = pa.table(
            {
                "key": [parsed.key for parsed, _, _, _ in ordered],
                "doc_key": [parsed.doc_key for parsed, _, _, _ in ordered],
                "meta_name": [parsed.meta_name for parsed, _, _, _ in ordered],
                "parent": [parsed.parent for parsed, _, _, _ in ordered],
                "content": [content for _, content, _, _ in ordered],
                "format": [format for _, _, format, _ in ordered],
                "updated_at": [stamp for _, _, _, stamp in ordered],
                "sort_key": [keys.sort_form(parsed.key) for parsed, _, _, _ in ordered],
                "chars": [len(content) for _, content, _, _ in ordered],
            },
            schema=_schema(pa),
        )

        target.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(
            table,
            target,
            row_group_size=ROW_GROUP_SIZE,
            compression=COMPRESSION,
            # Recorded in the footer, so a reader other than this one -- a
            # notebook, a query engine -- is told the file is ordered rather
            # than having to discover it or assume it is not.
            sorting_columns=[pq.SortingColumn(_schema(pa).get_field_index("sort_key"))],
        )
        return table.num_rows


def _schema(pa: Any) -> Any:
    """The columns a parquet store holds, and the version stamp on them.

    Every column is a string but ``chars``, including ``format`` and
    ``meta_name``, which are nullable because a document has no metadata name
    and an unrecognised file has no format. The stamp is file-level key-value
    metadata rather than a column: it is one fact about the file, and a column
    would repeat it per row and let two rows disagree.
    """
    return pa.schema(
        [
            ("key", pa.string()),
            ("doc_key", pa.string()),
            ("meta_name", pa.string()),
            ("parent", pa.string()),
            ("content", pa.string()),
            ("format", pa.string()),
            ("updated_at", pa.string()),
            ("sort_key", pa.string()),
            ("chars", pa.int64()),
        ],
        metadata={VERSION_KEY: str(FORMAT_VERSION).encode()},
    )


#: Stands in for "this document carries no metadata at all", so the lookup in
#: :meth:`ParquetStore._missing` needs no branch and allocates nothing.
_NOTHING: frozenset[str] = frozenset()


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


def _span(marks: list[str], key_range: KeyRange) -> tuple[int, int]:
    """Where ``key_range`` starts and stops within ``marks``, by bisecting it.

    ``marks`` is each row's position in whatever ordering the bounds are
    measured against, and the rows behind it must be sorted by it. Every caller
    is: the file is written in ``sort_key`` order, and the synthesised metadata
    position a survey window is measured at is monotone in ``sort_key``, so it
    preserves that order.

    Indices rather than a slice, so **two ranges can be intersected without
    slicing between them** -- which is what :meth:`ParquetStore._selection`
    needs, because a subtree is a stretch of the order too and narrowing by one
    before bisecting the other would put the second bisect on a list whose
    marks no longer line up.

    Six one-sided bounds collapse to two, because they all cut the same
    ordering: the lower ones to the latest cut from below, the upper ones to
    the earliest from above. What differs between them is only which key the
    cut is taken at and whether it is inclusive -- the distinction
    :class:`~rage.store.KeyRange` documents -- and that survives here as the
    choice between ``bisect_left`` and ``bisect_right``. The table below is the
    same six rows as ``store_sqlite._range_clauses``, and the two are meant to
    be read against each other.
    """
    lower, upper = 0, len(marks)
    for key, is_lower, seek, at in (
        # `>= p`: the first row not below p.
        (key_range.after_inclusive, True, bisect_left, _position),
        # `> p`: the first row past the last one equal to p.
        (key_range.after, True, bisect_right, _position),
        # `>= end-of-subtree`: the first row past the subtree entirely.
        (key_range.after_subtree, True, bisect_left, keys.sort_subtree_end),
        # `< p`: stops in front of p.
        (key_range.before, False, bisect_left, _position),
        # `<= p`: stops after the last row equal to p.
        (key_range.before_inclusive, False, bisect_right, _position),
        # `< end-of-subtree`: stops at the end of the subtree, inclusive of it.
        (key_range.final_subtree, False, bisect_left, keys.sort_subtree_end),
    ):
        if key is None:
            continue
        cut = seek(marks, at(key))
        if is_lower:
            lower = max(lower, cut)
        else:
            upper = min(upper, cut)
    return (lower, upper) if lower < upper else (0, 0)


def _subtree_range(key: str | None) -> KeyRange:
    """A :class:`~rage.store.KeyRange` selecting exactly the subtree at ``key``.

    **A subtree is a stretch of the order as well as a part of the hierarchy**,
    and the two coincide exactly: ``sort_form(k) <= sort_key <
    sort_subtree_end(k)`` is ``k``, its metadata and its descendants and
    nothing else. Every key inside those bounds continues ``sort_form(k)`` with
    the sort delimiter, so its ``doc_key`` is ``k`` or below it; and every key
    with such a ``doc_key`` sorts inside them.

    That equivalence is why the subtree is bisected here rather than tested per
    row against ``doc_key``, which is what the SQLite backend must do because
    its ``doc_key`` column carries no ordering index. Measured at 40k rows a
    survey of one subtree went from being *slower* than SQLite to being a
    seek -- the one place the columnar layout was losing, and it was losing for
    a reason that had nothing to do with columns.

    Careful: this is **not** what ``descendant_count`` asks. It counts keys
    strictly *below* ``k``, and ``k/!title`` sorts inside these bounds while
    sharing ``k``'s ``doc_key``. The bounds narrow that question; they do not
    answer it.

    The root has no such bounds, and needs none: everything is inside it.
    """
    if key is None or keys.parse(key).doc_key == keys.ROOT:
        return UNBOUNDED
    return KeyRange(after_inclusive=key, final_subtree=key)


def _after(rows: list[_Row], bound: str | None) -> list[_Row]:
    """The rows past a page cursor, which is a bisect like any other bound.

    Separate from :func:`_bounded` because a cursor is *not* a bound on the
    selection: it moves as a caller pages and deliberately does not reach the
    totals. Same mechanism, different argument, and keeping the two apart is
    what stops one quietly becoming the other.
    """
    if bound is None:
        return rows
    return rows[bisect_right([row.sort_key for row in rows], bound) :]


def _depth_test(subtree: BoundedSubtree) -> Callable[[_Row], bool]:
    """``subtree``'s depth budget as a test on a row, and nothing else.

    The *key* half of a subtree is bisected rather than tested --
    :func:`_subtree_range` -- so all that is left per row is how far down it
    sits. Depth is counted on ``doc_key`` rather than on the whole key, for the
    reason the SQLite backend gives: metadata does not add depth, so ``a/b``
    and ``a/b/!title`` are both at depth 2 and one budget covers a document and
    its metadata together.

    A budget of None is every depth, and says so by returning a test that is
    always true rather than by making every caller branch.
    """
    if subtree.depth is None:
        return lambda row: True

    limit = subtree.depth
    base = keys.depth(_scope(subtree.key))

    def deep_enough(row: _Row) -> bool:
        # The root has no segments and so breaks the delimiters-plus-one
        # formula: it would come out at depth 1, and `depth=0` from the root
        # would then exclude the very document it names.
        depth = 0 if row.doc_key == keys.ROOT else row.doc_key.count(keys.DELIMITER) + 1
        return depth - base <= limit

    return deep_enough


def _below(doc_key: str) -> Callable[[str], bool]:
    """A test for the keys strictly beneath ``doc_key``.

    A half-open string range for an ordinary key, since everything under ``a``
    starts with ``a/`` -- which is what keeps ``a/b`` from picking up
    ``a/beta``. For the root it is a test against the root itself: everything
    else is beneath it, and no string bounds every key from above, so
    ``keys.subtree_range`` refuses to invent one.
    """
    if doc_key == keys.ROOT:
        return lambda candidate: candidate != keys.ROOT
    lo, hi = keys.subtree_range(doc_key)
    return lambda candidate: lo <= candidate < hi


def _record_ancestry(children: dict[str, set[str]], key: str) -> None:
    """Record ``key`` and every key it brings into being under its parent.

    Walks up until it reaches a key already recorded, so a corpus sharing deep
    prefixes -- which a reference base is entirely made of -- costs one step
    per key after the first that reaches a given directory.

    The root is where it stops rather than something it records. The root is
    its own parent, so recording it would list it as a child of itself and
    count it into its own level's totals, which is the exception
    ``_children_clause`` exists to make in the other backend.
    """
    current = key
    while current != keys.ROOT:
        parent = current.rpartition(keys.DELIMITER)[0]
        siblings = children.setdefault(parent, set())
        if current in siblings:
            return
        siblings.add(current)
        current = parent


def _entry(row: _Row) -> Entry:
    """A stored row as a listing entry.

    ``size`` comes from ``chars`` rather than from the text, which is the
    difference that lets a listing of ten thousand keys never open the content
    column.
    """
    return Entry(
        key=row.key,
        kind="metadata" if row.meta_name is not None else "document",
        size=row.chars,
        format=row.format,
        updated_at=row.updated_at,
    )


__all__ = [
    "COMPRESSION",
    "DEFAULT_STORE_FILE",
    "FORMAT_VERSION",
    "INDEX_COLUMNS",
    "ROW_GROUP_SIZE",
    "VERSION_KEY",
    "ParquetStore",
]
