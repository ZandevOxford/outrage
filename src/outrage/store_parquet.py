"""The parquet backend: one columnar file, written once and read many times.

The second implementation of :class:`outrage.store.Store`, and the one the
reference-base case is for: tens of thousands of small documents, built in one
pass rather than accumulated, and reached by survey and search. It answers the
same twelve operations :class:`~outrage.store_sqlite.SqliteStore` does, in the
same vocabulary, and shares none of the storage.

**It does not write.** A parquet file is not updated in place, so
:meth:`~ParquetStore.store_document` and :meth:`~ParquetStore.delete` refuse
rather than pretend. Documents get in through :meth:`ParquetStore.build`,
which writes the whole file in one pass, and through ``outrage pack``, which is
the command line over it. That refusal is the backend's own and not a mount's:
see :class:`outrage.store.ReadOnlyStoreError` for the difference, which is that
no flag exists to take this one off.

The file is one row per key, carrying the columns
:class:`~outrage.store_sqlite.SqliteStore` keeps plus ``chars``, sorted by
``sort_key``. Two of those are the whole design:

* **Sorted by ``sort_key``** means every stretch of the key order this store's
  vocabulary can name -- a :class:`~outrage.store.KeyRange`, a page cursor, a
  subtree -- is a *contiguous run of rows*. So a bound is found by bisecting
  rather than by testing every row, and the content of a page comes out of the
  one or two row groups it falls in. This is the columnar payoff.
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
A :class:`~outrage.store.Page` reports ``total`` and ``total_chars`` over the
whole *selection*, and a total over an arbitrary predicate cannot come from
row-group statistics -- it needs every row the predicate selects. So the
contract obliges this backend to hold the small columns whole, in memory, and
only ``content`` is read lazily. That is why :meth:`ParquetStore._index` is
built once per file and ``content`` never joins it.

**How they are held is what decides how large a store can be.** They are the
file's own Arrow columns, searched by bisecting ``sort_key`` and converted a
row at a time for the rows an answer actually names. They were once a Python
object per key with three dictionaries over them, which measured at 865 bytes
a row -- fifteen times the file it came from, and 12.1 GB before a single read
of a seven-million-document reference base. Holding the columns instead is 120
bytes a row on the same corpus, and the eager dictionaries turn out to be
derivable from the order the file is already in: see :class:`_Index`.

pyarrow is an optional dependency: ``pip install outrage[parquet]``. It is
imported inside this module and this module is imported only by
:func:`outrage.store._backend_for`, so an install without it is unaffected until
something names a ``.parquet`` file.
"""

from __future__ import annotations

import os
import shutil
import sys
import threading
from array import array
from bisect import bisect_left, bisect_right
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import keys
from .eventlog import EventLog
from .maintenance import ROWS_OUT_OF_ORDER, Problem, Repaired, Report, _listed
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
    _byte_excerpt,
    _cursor_bound,
    _excerpt,
    _find_byte_occurrence,
    _find_occurrence,
    _logged,
    _now,
    _position,
    _scope,
    _sliced,
    _SubtreeTotals,
    _with_descendants,
    check_read_position,
    entry_kind,
    meta_reader,
)

#: What a parquet store's file is called when a caller names none. Beside
#: :data:`outrage.store_sqlite.DEFAULT_STORE_FILE`, each in its own module, and
#: it is the extension of this one that :func:`outrage.store._backend_for` reads
#: to know which backend a file wants.
DEFAULT_STORE_FILE = "store.parquet"

#: The layout this build writes, recorded in the file's own key-value metadata
#: so a file from a later build is refused rather than read with the wrong
#: shape assumed. The same rule as :data:`outrage.store_sqlite.SCHEMA_VERSION`
#: without the migrations: nothing here is ever updated in place, so an old
#: file is repacked rather than upgraded.
#:
#: **Version 1 is still read**, and nothing is rewritten to do it. It has no
#: ``meta_path`` column and a ``meta_name`` written under the rule that a name
#: swallowed everything below the first ``!``; both come off ``key``, which the
#: file carries, so :meth:`ParquetStore._build` derives them on the way in.
FORMAT_VERSION = 2

#: Where that version is written.
VERSION_KEY = b"outrage.format-version"

#: The columns held whole once a file is opened: everything except ``content``.
#: Naming them is what keeps the promise in the module docstring checkable --
#: the expensive column is absent from this list, and every read that does not
#: return document text stops here.
INDEX_COLUMNS = (
    "key",
    "doc_key",
    "meta_name",
    "meta_path",
    "parent",
    "format",
    "updated_at",
    "sort_key",
    "chars",
    "bytes",
)

#: Of those, the ones actually read into memory. ``doc_key`` and ``parent``
#: come off ``key``, which the index is holding anyway, and between them they
#: were a quarter of what an open store cost. ``doc_key`` is derived where a
#: depth budget asks for it -- :meth:`ParquetStore._walked`, the only question
#: anything asks of it -- and ``parent`` turns out not to be read by any read
#: at all: it was a denormalisation for listing a level, and a level is now
#: found by walking the order instead.
#:
#: Both are written to the file all the same. The file is read by other things,
#: a column a reader can recompute is still a column a query engine should not
#: have to, and :meth:`ParquetStore.audit_rows` checks the written ones against
#: the keys they claim to describe.
HELD_COLUMNS = tuple(name for name in INDEX_COLUMNS if name not in ("doc_key", "parent", "bytes"))

#: Whether a pack writes ``bytes``. On by default and omitted by ``outrage pack
#: --no-byte-lengths``, and the only column here that is optional: ``chars`` is
#: what answers a total without opening ``content``, so a file without it would
#: read every document to list a level.
#:
#: **Written before anything reads it, which needs its reason.** Which of the
#: two lengths is expensive is a property of the storage: SQLite gets bytes
#: from a blob handle and a directory of files from ``st_size``, while here
#: only the content column holds them. And a parquet file is never updated, so
#: a file packed without this can only gain it by being packed again -- unlike
#: the other two backends, where the same fact can be written down at any later
#: date for nothing. So it is written at the one moment it is cheap, for the
#: same reason ``doc_key`` and ``parent`` are written and not held: a column a
#: reader can recompute is still a column a query engine should not have to.
BYTE_LENGTHS = True

#: Columns worth dictionary encoding **if it helps**, tested rather than
#: assumed. In a store packed in one pass every row tends to carry the same
#: ``updated_at`` and one of three formats, and encoding those is 4 bytes a row
#: against 29; in a store imported from a corpus with a real timestamp per
#: document it is 4 bytes a row *on top* of the 29, so it is measured and kept
#: only when it wins. ``key`` and ``sort_key`` are never candidates -- they are
#: distinct by construction, and encoding them costs more than it saves every
#: time.
ENCODABLE = ("format", "updated_at")

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


def _compute() -> tuple[Any, Any]:
    """pyarrow and its compute kernels, through the same explanation.

    Separate from :func:`_arrow` because only the three reads that evaluate a
    predicate over a whole column want it, and because a caller wanting both
    should say so once rather than import in the middle of a method.
    """
    pa, _ = _arrow()
    import pyarrow.compute as pc

    return pa, pc


#: How many rows a chunked walk converts at a time. Big enough that the
#: per-call overhead of ``to_pylist`` is amortised away, small enough that the
#: Python strings it makes are freed long before the walk ends -- which is the
#: whole point of walking in chunks rather than converting a column.
CHUNK = 8192

#: How far a child walk probes forward before it gives up and bisects. Most
#: keys have a handful of rows beneath them -- a document, its title, perhaps a
#: note -- so the next sibling is usually two or three rows along and a linear
#: step finds it for the cost of one comparison. A bisect costs about twenty.
#: Past this many steps the subtree is big enough that the bisect is cheaper,
#: and the walk stops guessing. See :meth:`_Index.children`.
PROBE = 8


@dataclass(frozen=True, slots=True)
class _Row:
    """One key's columns, less its content.

    **Made on demand and thrown away**, which is the change from the layout
    that held one of these per key: at forty thousand rows that cost 37 MB and
    was invisible, and at the fourteen million a whole-encyclopaedia reference
    base needs it was 12.9 GB before a single read -- measured, not estimated.
    So the columns stay in Arrow and a row is materialised for the handful of
    rows an answer actually names.

    Slotted still, because the transient ones are made in the inner loop of
    every read.

    **It carries what a returned row is asked for, and nothing else.** It used
    to mirror the columns; a row read from a resident list may as well carry
    every field, because they were already objects. Made on demand they are not
    free: ``doc_key`` is a parse and ``sort_key``, ``meta_name``, ``meta_path``
    and ``parent`` are a decode each, per document returned, for fields no
    caller of :meth:`_Index.row` reads. The selections that *do* ask about
    those read the column instead -- :meth:`_Index.matching` for the metadata
    split, :meth:`ParquetStore._walked` for the one question ``doc_key``
    answers -- and neither makes a row to do it.

    ``position`` is the row's index in the file, which is how the content it
    does not carry is found again.
    """

    key: str
    format: str | None
    updated_at: str
    chars: int
    position: int


class _Text(Sequence[str]):
    """One string column, indexable a row at a time without decoding the rest.

    :func:`bisect_left` and :func:`bisect_right` need indexing and a length and
    nothing else, so this is the whole adapter -- a bisect over fourteen
    million rows reads about twenty-four rows of the column and leaves the rest
    alone. Converting the column to a Python list to bisect it would give back
    exactly the memory this exists to save.

    **It reads the Arrow buffers itself where it can.** ``array[i].as_py()``
    builds a pyarrow scalar on the way to the string and measures at 400 ns;
    slicing the offsets and the data directly is 210, and every bisect, every
    child walk and every metadata lookahead pays that cost per row visited.
    The fast path needs a single unsliced ``string`` array with no nulls, which
    is what ``combine_chunks`` gives for the columns this is used on; anything
    else -- a nullable column, a build of pyarrow that hands back something
    else -- falls back to ``as_py`` and is merely correct.
    """

    __slots__ = ("_array", "_offsets", "_data")

    def __init__(self, array: Any) -> None:
        self._array = array
        self._offsets: Any = None
        self._data: Any = None
        try:
            pa, _ = _arrow()
            if array.type == pa.string() and array.offset == 0 and array.null_count == 0:
                _, offsets, data = array.buffers()
                if offsets is not None and data is not None:
                    self._offsets = memoryview(offsets).cast("i")
                    self._data = memoryview(data)
        except (AttributeError, TypeError, ValueError):  # pragma: no cover - fallback
            self._offsets = None

    def __len__(self) -> int:
        return len(self._array)

    def __getitem__(self, position: Any) -> Any:
        offsets = self._offsets
        if offsets is None:  # pragma: no cover - only a column the fast path refuses
            return self._array[position].as_py()
        return str(self._data[offsets[position] : offsets[position + 1]], "utf-8")


class _Numbers(Sequence[int]):
    """The ``chars`` column, read a row at a time straight off its buffer.

    :class:`_Text` for integers, and for the same reason: a listing sums
    ``chars`` over every key in a level and building a pyarrow scalar for each
    is most of the cost of the listing. ``int64`` is fixed width, so there are
    no offsets -- one cast and an index.
    """

    __slots__ = ("_array", "_data")

    def __init__(self, array: Any) -> None:
        self._array = array
        self._data: Any = None
        try:
            pa, _ = _arrow()
            if array.type == pa.int64() and array.offset == 0 and array.null_count == 0:
                _, data = array.buffers()
                if data is not None:
                    self._data = memoryview(data).cast("q")
        except (AttributeError, TypeError, ValueError):  # pragma: no cover - fallback
            self._data = None

    def __len__(self) -> int:
        return len(self._array)

    def __getitem__(self, position: Any) -> Any:
        if self._data is None:  # pragma: no cover - only a column the fast path refuses
            return self._array[position].as_py()
        return self._data[position]


def _positions(indices: Any) -> Any:
    """Arrow row indices as a typed array of Python-indexable ints.

    Eight bytes an entry and no object per row, which is what lets a selection
    be the whole corpus. Copied off the Arrow buffer where the byte order
    allows -- Arrow is little-endian everywhere and :mod:`array` is native --
    and element by element where it does not, which is the same answer more
    slowly rather than a different one.
    """
    out = array("q")
    data = indices.buffers()[1]
    # The width is checked rather than assumed. Both kernels that feed this
    # return 64-bit indices today, and a build that returned 32-bit ones would
    # otherwise be read as half as many rows at twice the value -- silently,
    # and as a wrong answer rather than a crash. The fallback is the same
    # answer more slowly.
    wide = indices.type.bit_width == out.itemsize * 8
    if wide and sys.byteorder == "little" and indices.offset == 0 and data is not None:
        out.frombytes(memoryview(data)[: len(indices) * out.itemsize])
    else:  # pragma: no cover - a narrower index or a big-endian machine
        out.extend(indices.to_pylist())
    return out


class _Index:
    """Every column but ``content``, held as Arrow and searched by bisecting.

    Built once, on the first read, and dropped when the store is closed.

    **The file is sorted by ``sort_key``, and that is now the only index there
    is.** The layout this replaced also held a ``_Row`` per key, a ``by_key``
    dict, a ``children`` map and a ``meta_names`` map, each because one
    operation could not be answered from the others in less than a scan. All
    four are derivable from the order, and the derivations are cheap:

    * **"is this key stored, and where"** is :meth:`find`: one bisect for
      ``sort_form(key)``, then one comparison to see whether the row landed on
      is the key or merely where it would go.
    * **the keys immediately below one key, implicit ones included**, is
      :meth:`children`. A key's descendants are a contiguous run -- see
      :func:`_subtree_range` -- so the walk takes the first row in it, reads
      the child off that row's key, and skips that child's own run to reach the
      next. A key that holds nothing and has something beneath it is found the
      same way as one that holds something, which is what the ``children`` map
      was recording eagerly.
    * **the metadata names a key carries** is :meth:`carries`. Metadata sorts
      immediately after the key it hangs from and before any subkey, because
      ``!`` sorts below an ordinary segment mark -- so the names are the rows
      *directly following* the key's own row, and finding them costs no search
      at all.

    What is left resident is the Arrow columns, which is the file's own small
    columns and nothing per row on top of them.
    """

    __slots__ = ("columns", "order", "names", "sizes", "group_starts", "num_rows")

    def __init__(self, columns: dict[str, Any], group_starts: list[int]) -> None:
        #: One combined Arrow array per name in :data:`INDEX_COLUMNS`. Combined
        #: rather than chunked so that indexing one is a buffer offset rather
        #: than a search for the chunk holding it.
        self.columns = columns
        #: ``sort_key`` as a bisectable sequence. Held rather than made per
        #: call because every bounded read bisects it at least twice.
        self.order = _Text(columns["sort_key"])
        #: ``key`` the same way. The child walk and the metadata lookahead read
        #: it a row at a time and never want the whole column.
        self.names = _Text(columns["key"])
        #: ``chars`` the same way, for the listing that sums a level.
        self.sizes = _Numbers(columns["chars"])
        #: The first row position of each row group, cumulative, so a row's
        #: position tells you which group to open for its content.
        self.group_starts = group_starts
        self.num_rows = len(columns["key"])

    def __len__(self) -> int:
        return self.num_rows

    # -- one row at a time ------------------------------------------------

    def at(self, name: str, position: int) -> Any:
        """One cell, decoded."""
        return self.columns[name][position].as_py()

    def row(self, position: int) -> _Row:
        """One row, materialised for a caller that is returning it.

        Four columns and a position, which is what an :class:`Entry` and an
        :class:`~outrage.store.Excerpt` are made of. See :class:`_Row` for why
        it is not all of them.
        """
        columns = self.columns
        return _Row(
            key=self.names[position],
            format=columns["format"][position].as_py(),
            updated_at=columns["updated_at"][position].as_py(),
            chars=self.sizes[position],
            position=position,
        )

    def find(self, key: str) -> int | None:
        """Where ``key`` is stored, or None if it is not stored at all.

        The bisect lands where the key *would* go whether or not it is there,
        so the comparison after it is not a formality -- it is the whole
        difference between "stored" and "would sort here".
        """
        position = bisect_left(self.order, keys.sort_form(key), 0, self.num_rows)
        if position < self.num_rows and self.names[position] == key:
            return position
        return None

    # -- runs of rows -----------------------------------------------------

    def column_in(self, name: str, start: int, stop: int) -> Iterator[Any]:
        """One column over ``[start, stop)``, converted a chunk at a time.

        The walk every count and every predicate runs on. Chunked so that a
        count over a million rows holds a few thousand Python strings at a
        time rather than a million: the conversion is the cost that has to be
        paid to test a row, and holding the result afterwards is the cost that
        does not.
        """
        column = self.columns[name]
        for base in range(start, stop, CHUNK):
            end = min(base + CHUNK, stop)
            yield from column[base:end].to_pylist()

    def columns_in(self, names: Sequence[str], start: int, stop: int) -> Iterator[tuple]:
        """Several columns over ``[start, stop)``, chunk-aligned and zipped.

        Separate from :meth:`column_in` because a predicate usually wants two
        or three columns of the same row, and zipping whole-column iterators
        would hold a chunk of each anyway -- this at least keeps them aligned
        and converts each exactly once.
        """
        held = [self.columns[name] for name in names]
        for base in range(start, stop, CHUNK):
            end = min(base + CHUNK, stop)
            yield from zip(*(column[base:end].to_pylist() for column in held), strict=True)

    def span(self, key: str | None) -> tuple[int, int]:
        """The run of rows ``key``'s whole subtree occupies, itself included."""
        return _span(self.order, _subtree_range(key))

    def children(self, parent: str) -> Iterator[tuple[str, int | None]]:
        """Each key immediately below ``parent``, and where its own row is.

        In key order, which is the order the file is already in, and lazily:
        a level of seven million is counted by a caller that holds one child at
        a time.

        The position is None for an **implicit** child -- a key that holds
        nothing and has something beneath it. Those appear in a listing and
        there is no row anywhere that says so; here the walk arrives at a row
        whose key is *below* the child rather than equal to it, which is the
        same fact read off the order instead of recorded in a map.
        """
        start, stop = self.span(parent)
        names = self.names
        cut = 0 if parent == keys.ROOT else len(parent) + 1
        position = start
        # `parent`'s own row sorts first inside its subtree, and it is not a
        # child of itself.
        if position < stop and names[position] == parent:
            position += 1

        while position < stop:
            key = names[position]
            edge = key.find(keys.DELIMITER, cut)
            child = key if edge < 0 else key[:edge]
            yield child, (position if key == child else None)

            # Past this child's own subtree to the next sibling. Everything
            # under a key begins with that key and a delimiter, so a plain
            # prefix test says whether a row is still inside it -- no parse, no
            # sort form, and a child with nothing beneath it is found in one
            # comparison, which is the overwhelmingly common case. Only a child
            # deep enough to outrun :data:`PROBE` is worth a bisect, and that
            # one pays the single ``sort_subtree_end`` it needs.
            inside = child + keys.DELIMITER
            probe = position + 1
            ceiling = min(stop, probe + PROBE)
            while probe < ceiling and names[probe].startswith(inside):
                probe += 1
            if probe == ceiling and probe < stop and names[probe].startswith(inside):
                probe = bisect_left(self.order, keys.sort_subtree_end(child), probe, stop)
            position = probe

    def matching(self, start: int, stop: int, wanted: list[str] | None) -> tuple[Any, int]:
        """The document or named-metadata rows in ``[start, stop)``, vectorised.

        The predicate a survey runs on every row it considers, expressed as
        Arrow compute over a slice of two columns rather than as a Python test
        per row. That matters only at scale, and at scale it is the whole
        difference: a survey of a seven-million-document reference base reports
        a ``total`` over all of it, so the predicate really is evaluated seven
        million times, and a Python loop doing it is seconds where this is
        milliseconds.

        **Only for a scope that is not itself metadata.** From inside a
        metadata namespace the stored ``meta_name`` is a segment above the
        question being asked and matches nothing --
        :func:`outrage.store.meta_reader` is where that rule lives -- so the
        caller keeps the general walk for that case.
        """
        pa, pc = _compute()
        names = self.columns["meta_name"][start:stop]
        if wanted is None:
            # A document is a row whose key never turned to metadata.
            mask = pc.is_null(names)
        else:
            mask = pc.and_(
                pc.is_in(names, value_set=pa.array(wanted, pa.string())),
                # The *value* of a name, not something below it: `a/!title` and
                # not `a/!title/of`.
                pc.is_null(self.columns["meta_path"][start:stop]),
            )
        chosen = pc.indices_nonzero(mask)
        total = pc.sum(pc.filter(self.columns["chars"][start:stop], mask)).as_py() or 0

        if start:
            # `indices_nonzero` counts from the slice, and everything above
            # counts from the file. Shifted in Arrow rather than in a Python
            # loop, which would undo the point of the kernel above on exactly
            # the reads that bound themselves.
            chosen = pc.add(chosen, start)
        return _positions(chosen), total

    def has_children(self, key: str) -> bool:
        """Whether anything at all is stored below ``key``.

        Two bisects and a comparison. The subtree run holds ``key``'s own row
        first when it has one, so what is left after stepping over it is
        exactly what "has something beneath it" means.
        """
        start, stop = self.span(key)
        if start < stop and self.names[start] == key:
            start += 1
        return start < stop

    def carries(self, position: int, key: str, names: Sequence[str]) -> bool:
        """Whether the row at ``position`` carries any metadata in ``names``.

        No search: a key's metadata is the rows straight after its own. That
        holds because ``sort_form`` marks a metadata segment below an ordinary
        one, so ``a/!title`` sorts after ``a`` and before ``a/b``, and nothing
        else can come between.

        Only *direct* metadata counts, which is what the map this replaced
        recorded: ``a/!title`` is a name on ``a`` and ``a/!title/!of`` is a
        name on ``a/!title``. So a row deeper than one segment is skipped
        rather than ending the walk -- it is still inside the metadata unit,
        and a later row may still be a direct name.
        """
        # `keys.meta_range` says the same thing, and parses to say it. This
        # is asked once per document in a survey of the whole store, and the
        # key came out of the file already normalised, so the bounds are built
        # rather than derived: everything in `key`'s metadata unit begins with
        # the key, a delimiter and `!`, and nothing else does.
        prefix = keys.META_PREFIX if key == keys.ROOT else key + keys.DELIMITER + keys.META_PREFIX
        cut = len(prefix)
        column = self.names
        probe = position + 1
        while probe < self.num_rows:
            candidate = column[probe]
            if not candidate.startswith(prefix):
                return False
            name = candidate[cut:]
            if keys.DELIMITER not in name and name in names:
                return True
            probe += 1
        return False


class _Selection:
    """The rows one read is about, as positions into the file.

    **Positions rather than rows**, and that is the whole of it: a selection
    can be the entire corpus -- ``get_documents()`` at the root reports a
    ``total`` over every document there is -- and materialising a row object
    per key to count them is what made a large reference base unopenable in
    the first place. Eight bytes each in a typed array, and the two or three
    dozen rows a page actually returns are made from the columns at the end.

    ``total_chars`` is accumulated as the selection is built rather than
    computed from it. The characters are in the chunk being walked anyway, and
    adding them up there costs nothing; going back for them afterwards would
    mean touching every selected row a second time.
    """

    __slots__ = ("index", "positions", "total_chars")

    def __init__(self, index: _Index, positions: Any, total_chars: int) -> None:
        self.index = index
        self.positions = positions
        self.total_chars = total_chars

    def __len__(self) -> int:
        return len(self.positions)

    def column(self, name: str) -> list[Any]:
        """One column at the selected rows, gathered in one vectorised take.

        For the callers that need a value from every selected row rather than
        from a page of them -- the survey window, which measures each document
        at the position its metadata would have taken. Arrow gathers the whole
        column at once; a Python loop over the positions would decode them one
        at a time and is the thing worth avoiding at seven figures.
        """
        if not self.positions:
            return []
        pa, pc = _compute()
        gathered = pa.array(self.positions, type=pa.int64())
        return pc.take(self.index.columns[name], gathered).to_pylist()

    def narrowed(self, lower: int, upper: int) -> _Selection:
        """The selection cut down to ``[lower, upper)`` of its own positions."""
        kept = self.positions[lower:upper]
        sizes = self.index.sizes
        return _Selection(self.index, kept, sum(sizes[position] for position in kept))

    def after(self, bound: str | None) -> Any:
        """The positions past a page cursor, which is a bisect like any other.

        A cursor is *not* a bound on the selection: it moves as a caller pages
        and deliberately does not reach the totals. Same mechanism, different
        argument, and keeping the two apart is what stops one quietly becoming
        the other.
        """
        if bound is None:
            return self.positions
        order = self.index.order
        return self.positions[bisect_right(self.positions, bound, key=lambda p: order[p]) :]


class ParquetStore(FileStore):
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
        mount_point: str | None = None,
    ) -> None:
        # Where the file is, and the directory around it, are the base's
        # business, exactly as they are for SQLite.
        super().__init__(
            directory,
            filename=filename,
            log=log,
            mount_point=mount_point,
        )
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
        # was a live defect once already, and it was
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
        # Kept, because an older file is read rather than refused and the
        # reader has to know which layout it is looking at. Only a file
        # *newer* than this build is refused -- the comparison is `>`, not
        # `!=`, and the strict one belongs to backup verification.
        self._written_version = int(written)
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
        the SQLite backend is under and which holds here for the same reason.
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

        Held as Arrow rather than as Python objects because the contract asks
        for totals. ``Page.total`` and ``Page.total_chars`` describe the
        selection rather than the page, and no row-group statistic answers "how
        many rows match this predicate" -- only "could any row in this group
        match". That field is what decides how much of a columnar file a read
        has to open. So the small columns
        are resident and only ``content`` is read lazily -- but resident as the
        file's own columns, which is a buffer per column, and not as a row
        object per key, which was fifteen times the size of the file it came
        from.
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
        """Every column but ``content``, combined and kept as Arrow.

        A single pass, and nothing per row. ``combine_chunks`` is the one piece
        of work done on the way in: a parquet read gives one chunk per row
        group, and indexing a chunked array means finding the chunk first --
        which a bisect would pay for on every one of its twenty-odd probes.
        Combined once, an index is a buffer offset.
        """
        # A version 1 file has no `meta_path` column, and the `meta_name` it
        # does have was written under the rule that a name swallowed everything
        # below the first `!`. Both come off `key`, which every version
        # carries, so the older file is read whole and re-split here rather
        # than repacked. Nothing is written back: this backend has no
        # migrations, and the derivation costs one parse per row on the one
        # pass that reads the columns anyway.
        pa, _ = _arrow()
        derive = self._written_version < 2
        held = [name for name in HELD_COLUMNS if not (derive and name == "meta_path")]
        table = self._parquet.read(columns=held)
        columns = {name: table.column(name).combine_chunks() for name in held}
        if derive:
            split = [keys.parse(key) for key in columns["key"].to_pylist()]
            columns["meta_name"] = pa.array([parsed.meta_name for parsed in split], pa.string())
            columns["meta_path"] = pa.array([parsed.meta_path for parsed in split], pa.string())

        for name in ENCODABLE:
            encoded = columns[name].dictionary_encode()
            if encoded.nbytes < columns[name].nbytes:
                columns[name] = encoded

        metadata = self._parquet.metadata
        starts = [0]
        for group in range(metadata.num_row_groups):
            starts.append(starts[-1] + metadata.row_group(group).num_rows)

        return _Index(
            columns=columns,
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
        contents: str | None = None,
        encoding: str | None = None,
        updated_at: str | None = None,
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

        :meth:`build` is the way in, and ``outrage pack`` is the command line
        over it.
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
        raise ReadOnlyStoreError("store-read-only", key=key, path=str(self.path), action="write")

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
        """Refused, for the reason :meth:`store_document` is.

        Before the watermark is looked at rather than after: a store that
        cannot delete anything refuses whether or not the subtree moved, and
        checking first would answer a caller's second question while leaving
        their first one to a different sentence.

        ``dry_run`` is refused with the rest of it. A preview whose answer is
        "these keys would go" from a store where they never could is the one
        thing a preview must not say.
        """
        raise ReadOnlyStoreError("store-read-only", key=key, path=str(self.path), action="delete")

    # -- reading ---------------------------------------------------------

    def exists(self, key: str) -> bool:
        """One bisect, over the index rather than the file."""
        return self._index.find(keys.parse(key).key) is not None

    def level_entry(self, key: str) -> Entry | None:
        """The stored row if there is one, else whether anything lies below.

        The second half is two bisects rather than a scan, and it finds an
        implicit key the same way the listing does -- see
        :meth:`_Index.has_children`.
        """
        parsed = keys.parse(key)
        if parsed.key == keys.ROOT:
            raise ValueError("the root is not a child of anything, so it has no listing entry")

        index = self._index
        position = index.find(parsed.key)
        if position is not None:
            return _entry(index.row(position))
        if index.has_children(parsed.key):
            return Entry(key=parsed.key, kind="implicit", size=None, format=None, updated_at=None)
        return None

    @_logged("descendant_count")
    def descendant_count(
        self, key: str, *, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False
    ) -> int:
        """How many rows lie strictly below ``key``, within ``key_range``.

        Counted over the index. The subtree is a stretch of the order and the
        range is bisected; what is left per row is whether the key is one a
        plain delete of ``key`` would *keep*, which the bounds narrow but do
        not answer -- and under ``whole_subtree`` there is nothing left to ask,
        since the bisected stretch is the answer.
        """
        index = self._index
        parsed = keys.parse(key)
        lower, upper = _span(index.order, key_range)
        # Narrowed by the subtree's own bounds first. It does not answer the
        # question -- `key` itself and its whole metadata unit sort inside them
        # and are not counted -- but it keeps a count of one subtree from
        # walking the corpus.
        inner, outer = index.span(key)
        below = _below(parsed.key)
        lo, hi = keys.meta_range(parsed.key)
        # Only `key` is needed to answer this, so only `key` is converted, and
        # a chunk of it at a time.
        return sum(
            1
            for candidate in index.column_in("key", max(lower, inner), min(upper, outer))
            if below(candidate) and (whole_subtree or not lo <= candidate < hi)
        )

    def _subtree_totals(
        self, key: str, *, key_range: KeyRange = UNBOUNDED, chars: bool = False
    ) -> _SubtreeTotals:
        """The subtree's run of rows, counted by arithmetic and walked once.

        A subtree is one contiguous stretch of a file already written in key
        order, so :meth:`_Index.span` gives it in two bisections and the number
        of keys in it is a subtraction -- no rows converted at all. Only the
        document count needs the walk, and only ``meta_name`` is converted for
        it: that column is written for every row below a metadata segment and
        not the segment alone, which is exactly the definition
        :class:`~outrage.store._SubtreeTotals` states.

        ``key``'s own row sorts first inside its own subtree and is dropped
        here, which is what makes this *strictly* below and keeps an entry's
        own ``size`` from being counted again in its ``descendant_chars``. It
        is dropped after the range is applied and not before: a range that
        starts past it has already excluded it, and stepping over a row the
        bounds never included would take a real one with it.

        The characters are a slice of ``chars`` off its buffer, so they cost
        far less here than in a store that has to measure content -- but they
        stay behind the flag, because a surface that is opt in on one backend
        and always on in another is two contracts wearing one name.
        """
        parsed = keys.parse(key)
        index = self._index
        inner, outer = index.span(parsed.key)
        lower, upper = _span(index.order, key_range)
        start, stop = max(inner, lower), max(min(outer, upper), max(inner, lower))
        if start < stop and index.names[start] == parsed.key:
            start += 1
        documents = sum(1 for name in index.column_in("meta_name", start, stop) if name is None)
        sizes = index.sizes
        return _SubtreeTotals(
            keys=stop - start,
            documents=documents,
            chars=sum(sizes[position] for position in range(start, stop)) if chars else None,
        )

    @_logged("latest_change")
    def latest_change(
        self, key: str, *, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False
    ) -> str | None:
        """The newest ``updated_at`` over the rows :meth:`descendant_count` counts.

        The same bisected stretch and the same per-row question, taking a
        maximum instead of a total. Two columns are converted rather than one,
        in step and a chunk at a time: the timestamp is only wanted for a row
        the key test keeps, and pairing them is what says which row it belongs
        to.
        """
        index = self._index
        parsed = keys.parse(key)
        lower, upper = _span(index.order, key_range)
        inner, outer = index.span(key)
        start, stop = max(lower, inner), min(upper, outer)
        below = _below(parsed.key)
        lo, hi = keys.meta_range(parsed.key)
        newest: str | None = None
        for candidate, moment in zip(
            index.column_in("key", start, stop),
            index.column_in("updated_at", start, stop),
            strict=True,
        ):
            if not below(candidate) or (not whole_subtree and lo <= candidate < hi):
                continue
            if moment is not None and (newest is None or moment > newest):
                newest = moment
        return newest

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
        """One index lookup, one row group, and the shared slicing.

        The slicing is :func:`outrage.store._excerpt`, unchanged and unwrapped:
        how ``length`` and ``max_chars`` combine is the store's policy and not
        this backend's, and two backends that sliced differently would return
        different documents for the same call.

        **A byte offset is honoured and not accelerated**, which the plan says
        rather than implying parity: a row's value is decompressed whole out of
        its row group and there is no sub-value addressing to reach for. So the
        content is encoded and sliced, which costs what it costs and answers
        the same bytes as a backend that seeks.
        """
        parsed = keys.parse(key)
        index = self._index
        position = index.find(parsed.key)
        if position is None:
            beneath = self.descendant_count(key)
            if beneath:
                raise KeyNotFoundError("key-is-a-container", key=key, beneath=beneath)
            raise KeyNotFoundError("key-not-found", key=key)

        check_read_position(
            key, offset=offset, byte_offset=byte_offset, pattern=pattern, occurrence=occurrence
        )
        row = index.row(position)
        content = self._content(row)

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
            return _excerpt(row.key, content, row.format, row.updated_at, start, length, max_chars)

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
            row.key,
            row.format,
            row.updated_at,
            start,
            length,
            max_chars,
            read=read,
            total_bytes=len(data),
            # Free here, and so reported. This backend has no seek, so a byte
            # read holds the whole document either way and the character total
            # costs nothing on top of it. A backend that does seek reports one
            # only where it was written down.
            total=len(content),
        )

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
        """One level, real and implicit keys together, walked in order.

        :meth:`_Index.children` yields both kinds in key order -- which is the
        order the file is already in, so nothing is sorted here. That is the
        difference this shape makes: the layout it replaced held a set of every
        child of every key, and then called ``sort_form`` on every name in the
        level on every call. At two hundred thousand keys a listing of the root
        took most of a second, all of it re-deriving an order the file was
        already written in.

        **One pass, and it holds a page.** The totals are over the whole level
        and so unaffected by the cursor, which means the level has to be walked
        whatever happens; what does not have to happen is an ``Entry`` per key
        surviving that walk. Only the page's worth is kept, plus one more --
        which is how ``more`` is known without counting the rest twice.

        The characters come from ``chars`` without any content being read.

        The descendant flags are filled over the page afterwards, one
        :meth:`_subtree_totals` per child, and are the one part of this that is
        linear in the subtree rather than in the level.
        """
        # The whole key, not its document part: a metadata namespace is a
        # level like any other and ``list_keys("a/!x")`` lists what is in it.
        parent = keys.parse(_scope(key)).key
        index = self._index
        bound = _cursor_bound(cursor)

        total = 0
        total_chars = 0
        items: list[Entry] = []
        more = False
        sizes = index.sizes
        for child, position in index.children(parent):
            total += 1
            # The level's characters need one number per child, not a row. A
            # row is ten columns decoded, and building one per key is what a
            # listing of a large level cannot afford -- so only the page's
            # worth are made, below.
            if position is not None:
                total_chars += sizes[position]
            if bound is not None and keys.sort_form(child) <= bound:
                continue
            if limit is None or len(items) < limit:
                items.append(
                    _entry(index.row(position)) if position is not None else _implicit(child)
                )
            else:
                # One past the page is all it takes to know there is a next
                # one. Counting the rest would walk the level twice.
                more = True

        items = _with_descendants(self, items, counts=descendant_counts, chars=descendant_chars)
        return Page(
            items=items,
            returned=len(items),
            total=total,
            total_chars=total_chars,
            next_cursor=items[-1].key if more and items else None,
        )

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
        index = self._index
        selection = self._selection(subtree, key_range, meta_name=meta_name)

        items: list[Excerpt] = []
        spent = 0
        more = False
        for position in selection.after(_cursor_bound(cursor)):
            if limit is not None and len(items) >= limit:
                more = True
                break
            # The budget is decided from `chars` alone, so a document the
            # budget refuses is never materialised and never read.
            expected = min(index.at("chars", position), max_chars)
            if items and max_total_chars is not None and spent + expected > max_total_chars:
                # Never on the first document, or a budget smaller than one
                # document returns an empty page with a cursor that does not
                # move, and the caller loops forever making no progress.
                more = True
                break
            row = index.row(position)
            excerpt = _excerpt(
                row.key, self._content(row), row.format, row.updated_at, 0, None, max_chars
            )
            items.append(excerpt)
            spent += excerpt.returned

        return Page(
            items=items,
            returned=len(items),
            total=len(selection),
            total_chars=selection.total_chars,
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

        # Gathered in one take rather than a decode per row: this is the one
        # read that needs a value from every selected row instead of from a
        # page of them.
        marks = [
            root if sort_key == keys.ROOT else sort_key + suffix
            for sort_key in missing.column("sort_key")
        ]
        lower, upper = _span(marks, window)
        within = missing.narrowed(lower, upper)
        return MissingMeta(
            total=len(within),
            total_chars=within.total_chars,
            sample=[self._index.at("key", position) for position in within.positions[:sample]]
            if sample > 0
            else [],
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
        index = self._index
        missing = self._missing(subtree, key_range, _names(meta_name))

        found = missing.after(_cursor_bound(cursor))
        items = found if limit is None else found[:limit]
        more = limit is not None and len(found) > limit
        listed = [index.at("key", position) for position in items]
        return Page(
            items=listed,
            returned=len(listed),
            total=len(missing),
            total_chars=missing.total_chars,
            next_cursor=listed[-1] if more and listed else None,
        )

    # -- selecting -------------------------------------------------------

    def _selection(
        self,
        subtree: BoundedSubtree,
        key_range: KeyRange,
        *,
        meta_name: str | Sequence[str] | None,
        keep: Callable[[int, str], bool] | None = None,
    ) -> _Selection:
        """The rows a subtree read is about, as positions in key order.

        The same three independent conditions the SQLite backend ANDs
        together, and all three are required to hold: a row is in the selection
        when it is inside ``subtree``, carries the metadata asked for, **and**
        falls inside ``key_range``. A page cursor is not among them, which is
        what keeps ``total`` describing the selection rather than the remainder
        of it.

        **Both the range and the subtree are bisected**, and their spans are
        intersected before either is walked -- see :func:`_subtree_range` for
        why a subtree is a stretch of the order too. What is left to test per
        row is the depth budget, which is not a bound on the order at all, and
        the metadata name -- the latter read as it is seen from the key the
        read was scoped at, which :func:`outrage.store.meta_reader` decides.

        The walk converts the four columns those tests need a chunk at a time
        and keeps a position and a character count. Nothing per row survives
        it, which is what lets the selection be the whole corpus.

        ``keep`` is a further test, given the row's position and key, for the
        one caller that has one: :meth:`_missing` asks whether the document
        already carries a name, and asking it here rather than over the result
        means the walk happens once.
        """
        wanted = None if meta_name is None else _names(meta_name)
        index = self._index
        lower, upper = _span(index.order, key_range)
        inner, outer = index.span(subtree.key)
        start, stop = max(lower, inner), min(upper, outer)

        scope = keys.parse(_scope(subtree.key))
        if subtree.depth is None and not scope.is_metadata:
            positions, total_chars = index.matching(start, stop, wanted)
        else:
            positions, total_chars = self._walked(subtree, start, stop, wanted)

        if keep is not None:
            positions, total_chars = self._kept(positions, keep)
        return _Selection(index, positions, total_chars)

    def _walked(
        self, subtree: BoundedSubtree, start: int, stop: int, wanted: list[str] | None
    ) -> tuple[Any, int]:
        """:meth:`_selection`'s predicate as a Python walk, for when it must be.

        Two things force it. A **depth budget** is not a bound on the order and
        not a column either -- it is counted off ``doc_key`` per row. And a
        scope that is **itself metadata** reads its split per row rather than
        from the stored columns, which is
        :func:`outrage.store.meta_reader`'s rule.

        Neither is what a large reference base is surveyed with, so this is the
        general answer and :meth:`_Index.matching` is the fast one. Both must
        select the same rows, and ``test_the_two_backends_answer_every_read_identically``
        is what says so: it runs every read at every bound against SQLite, and
        a depth budget on the same subtree takes this path where the plain
        survey took the other.
        """
        index = self._index
        deep_enough = _depth_test(subtree)
        seen_from = meta_reader(_scope(subtree.key))

        positions = array("q")
        total_chars = 0
        walk = index.columns_in(("key", "meta_name", "meta_path", "chars"), start, stop)
        for offset, (key, name, path, chars) in enumerate(walk):
            seen_name, seen_path = seen_from(key, name, path)
            if wanted is None:
                if seen_name is not None:
                    continue
            elif seen_name not in wanted or seen_path is not None:
                continue
            # The parse is paid here and nowhere else: this is the only walk
            # that asks a question of `doc_key`, and it is the walk a depth
            # budget forces. A survey without one never reaches this method.
            if not deep_enough(keys.parse(key).doc_key):
                continue
            positions.append(start + offset)
            total_chars += chars
        return positions, total_chars

    def _kept(self, positions: Any, keep: Callable[[int, str], bool]) -> tuple[Any, int]:
        """``positions`` narrowed by a test that needs the row's key.

        The keys are gathered in one Arrow take rather than decoded one at a
        time: this runs over a selection that may be every document in the
        store, and the take is the difference between one vectorised gather and
        seven million scalar builds.
        """
        index = self._index
        if not positions:
            return positions, 0

        pa, pc = _compute()
        gathered = pa.array(positions, type=pa.int64())
        names = pc.take(index.columns["key"], gathered).to_pylist()

        sizes = index.sizes
        kept = array("q")
        total_chars = 0
        for position, key in zip(positions, names, strict=True):
            if keep(position, key):
                kept.append(position)
                total_chars += sizes[position]
        return kept, total_chars

    def _missing(
        self, subtree: BoundedSubtree, key_range: KeyRange, names: list[str]
    ) -> _Selection:
        """Documents in the selection carrying none of ``names``.

        SQLite's ``NOT EXISTS`` against a self-join, as a look at the next row:
        a key's metadata sorts immediately after it, so whether a document
        carries a name is answered by the rows already adjacent to it rather
        than by a correlated subquery -- see :meth:`_Index.carries`. That is
        the one place the columnar layout is unambiguously the better shape:
        the anti-join stops being one.

        **The lookahead deliberately reaches outside the selection.** Whether a
        document has a title is a fact about the store, not about the range the
        caller asked over, so a ``key_range`` that happens to cut between a
        document and its title must not make the document look untitled.
        """
        index = self._index
        return self._selection(
            subtree,
            key_range,
            meta_name=None,
            keep=lambda position, key: not index.carries(position, key, names),
        )

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
        short. The trap where a WAL lets a plain file copy succeed and be stale
        is SQLite's rather than the store's, and this is the evidence.

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
            raise BackupError("backup-corrupt", target=str(target), integrity=str(exc)) from exc
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
        """Every row **as the file stores it**, streamed a row group at a time.

        From the file rather than from the index, and the difference is the
        point. The index no longer holds ``doc_key`` or ``parent`` -- which is
        what makes an open store a quarter of what it used to cost -- and what
        it does not hold it cannot check. Worse, both come off ``key``, and a
        value derived from a key can never disagree with it. A check reading
        the index would therefore pass unconditionally on exactly the defect
        ``_report_parents`` exists to find -- a stored ``parent`` that does not
        match its key, written by something that was not this build -- and
        would report a clean file while saying nothing.

        So this reads the stored columns. It is the one caller that wants what
        is *written down* rather than what is true, and it is a check, which
        is allowed to be the expensive path. ``iter_batches`` streams, so a
        corpus that does not fit in memory is still checked without it.

        ``chars`` is the column this backend has and SQLite does not, precisely
        so that counting characters never costs a read of the text -- and this
        never opens ``content`` either.
        """
        held = ("key", "doc_key", "meta_name", "parent", "chars")
        for batch in self._parquet.iter_batches(batch_size=CHUNK, columns=list(held)):
            columns = [batch.column(name).to_pylist() for name in held]
            for key, doc_key, meta_name, parent, chars in zip(*columns, strict=True):
                yield AuditRow(
                    key=key,
                    doc_key=doc_key,
                    meta_name=meta_name,
                    parent=parent,
                    chars=chars,
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
        report.details["rows"] = str(len(index))
        report.details["row groups"] = str(self._parquet.metadata.num_row_groups)

        # The ``sort_key`` column in the order the file holds it, never
        # re-sorted on the way in -- which is what makes comparing it with
        # itself a check rather than a tautology. Walked a chunk at a time and
        # kept only as the previous value, so checking a corpus that does not
        # fit in memory as rows does not need it to.
        out_of_order: list[str] = []
        previous: str | None = None
        walk = index.columns_in(("key", "sort_key"), 0, len(index))
        for key, sort_key in walk:
            if previous is not None and sort_key < previous:
                out_of_order.append(key)
            previous = sort_key
        report.details["order"] = "sorted" if not out_of_order else "not sorted"
        if out_of_order:
            report.problems.append(
                Problem(
                    ROWS_OUT_OF_ORDER,
                    "error",
                    "the file is not in sort order",
                    f"{_listed(out_of_order)}; every read bisects this column, so a file "
                    f"out of order answers wrongly rather than failing. Rebuild it with "
                    f"outrage pack.",
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
        ``outrage pack``, from a source that is still right.
        """
        return []

    # -- building --------------------------------------------------------

    @classmethod
    def check_target(cls, path: str | os.PathLike[str], *, overwrite: bool = False) -> Path:
        """Where a build would write, refusing a file already there.

        Public and separate from :meth:`build` so a caller can hit the refusal
        **before** reading its source. A pack reads the whole corpus before it
        writes anything, so leaving this to the write means a refusal that
        arrives after forty thousand documents have been read - which is the
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
        byte_lengths: bool = BYTE_LENGTHS,
    ) -> int:
        """Write a whole parquet store in one pass, and return the row count.

        ``documents`` yields ``(key, content, format, updated_at)``. A format
        of None is detected from the content and an ``updated_at`` of None is
        now, so a caller with a directory of files supplies neither and a
        caller copying an existing store supplies both -- which is what lets
        ``outrage pack`` keep timestamps when packing a store and invent them when
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
            parsed, decoded, resolved, _, _, stamped = cls._validated(
                key,
                content,
                format,
                title=None,
                contents=None,
                encoding=None,
                updated_at=updated_at,
            )
            if parsed.has_wildcard:
                raise BackendError("parquet-build-wildcard", key=key)
            # Last one wins, which is what overwriting means everywhere else in
            # the store. Silently keeping the first would make the result
            # depend on an iteration order the caller did not choose.
            rows[parsed.key] = (parsed, decoded, resolved, stamped or _now())

        ordered = sorted(rows.values(), key=lambda row: keys.sort_form(row[0].key))
        table = pa.table(
            {
                "key": [parsed.key for parsed, _, _, _ in ordered],
                "doc_key": [parsed.doc_key for parsed, _, _, _ in ordered],
                "meta_name": [parsed.meta_name for parsed, _, _, _ in ordered],
                "meta_path": [parsed.meta_path for parsed, _, _, _ in ordered],
                "parent": [parsed.parent for parsed, _, _, _ in ordered],
                "content": [content for _, content, _, _ in ordered],
                "format": [format for _, _, format, _ in ordered],
                "updated_at": [stamp for _, _, _, stamp in ordered],
                "sort_key": [keys.sort_form(parsed.key) for parsed, _, _, _ in ordered],
                "chars": [len(content) for _, content, _, _ in ordered],
                **(
                    {"bytes": [_utf8_length(content) for _, content, _, _ in ordered]}
                    if byte_lengths
                    else {}
                ),
            },
            schema=_schema(pa, byte_lengths=byte_lengths),
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
            sorting_columns=[
                pq.SortingColumn(_schema(pa, byte_lengths=byte_lengths).get_field_index("sort_key"))
            ],
        )
        return table.num_rows


def _utf8_length(content: str) -> int:
    """How many bytes ``content`` is in UTF-8, encoding only when it must.

    ``str.isascii`` is a flag CPython already keeps on the string, and an ASCII
    document is exactly as many bytes as it is characters -- which most
    Markdown is. So the column costs a pass over a flag for most of a corpus
    and an encode for the rest, rather than an encode for all of it.
    """
    return len(content) if content.isascii() else len(content.encode())


def _schema(pa: Any, *, byte_lengths: bool = BYTE_LENGTHS) -> Any:
    """The columns a parquet store holds, and the version stamp on them.

    Every column is a string but ``chars``, including ``format``, ``meta_name``
    and ``meta_path``, which are nullable because a document has no metadata
    name, a metadata value has nothing below it, and an unrecognised file has
    no format. The stamp is file-level key-value
    metadata rather than a column: it is one fact about the file, and a column
    would repeat it per row and let two rows disagree.
    """
    fields = [
        ("key", pa.string()),
        ("doc_key", pa.string()),
        ("meta_name", pa.string()),
        ("meta_path", pa.string()),
        ("parent", pa.string()),
        ("content", pa.string()),
        ("format", pa.string()),
        ("updated_at", pa.string()),
        ("sort_key", pa.string()),
        ("chars", pa.int64()),
    ]
    if byte_lengths:
        fields.append(("bytes", pa.int64()))
    # The stamp does not move for `bytes`. A reader keys on the column being
    # there rather than on the version, which it has to anyway -- the pack
    # option means two files can carry the same version and differ in columns --
    # and which is what keeps every file already written readable. Moving the
    # stamp instead is what once made every file written before the change
    # report itself as not being a store at all -- a misleading answer for a
    # file that was one, and one no migration could take back, because nothing
    # here is ever updated in place.
    return pa.schema(fields, metadata={VERSION_KEY: str(FORMAT_VERSION).encode()})


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
    :class:`~outrage.store.KeyRange` documents -- and that survives here as the
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
    """A :class:`~outrage.store.KeyRange` selecting exactly the subtree at ``key``.

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

    Careful: this is **not** what ``descendant_count`` asks. It counts what a
    plain delete of ``k`` would keep, and ``k`` itself and its whole metadata
    unit sort inside these bounds without being any of it. The bounds narrow
    that question; they do not answer it.

    The root has no such bounds, and needs none: everything is inside it.
    """
    if key is None or keys.parse(key).key == keys.ROOT:
        return UNBOUNDED
    return KeyRange(after_inclusive=key, final_subtree=key)


def _depth_test(subtree: BoundedSubtree) -> Callable[[str], bool]:
    """``subtree``'s depth budget as a test on a row's ``doc_key``, and nothing else.

    The *key* half of a subtree is bisected rather than tested --
    :func:`_subtree_range` -- so all that is left per row is how far down it
    sits. Depth is counted on ``doc_key`` rather than on the whole key, for the
    reason the SQLite backend gives: metadata does not add depth, so ``a/b``
    and ``a/b/!title`` are both at depth 2 and one budget covers a document and
    its metadata together.

    Takes the ``doc_key`` rather than a row because that is all it reads, and
    the walk that calls it has the column in hand and no row made yet.

    A budget of None is every depth, and says so by returning a test that is
    always true rather than by making every caller branch.
    """
    if subtree.depth is None:
        return lambda doc_key: True

    limit = subtree.depth
    base = keys.depth(_scope(subtree.key))

    def deep_enough(doc_key: str) -> bool:
        # The root has no segments and so breaks the delimiters-plus-one
        # formula: it would come out at depth 1, and `depth=0` from the root
        # would then exclude the very document it names.
        depth = 0 if doc_key == keys.ROOT else doc_key.count(keys.DELIMITER) + 1
        return depth - base <= limit

    return deep_enough


def _below(scope: str) -> Callable[[str], bool]:
    """A test for the keys strictly beneath ``scope``.

    A half-open string range for an ordinary key, since everything under ``a``
    starts with ``a/`` -- which is what keeps ``a/b`` from picking up
    ``a/beta``. For the root it is a test against the root itself: everything
    else is beneath it, and no string bounds every key from above, so
    ``keys.subtree_range`` refuses to invent one.
    """
    if scope == keys.ROOT:
        return lambda candidate: candidate != keys.ROOT
    lo, hi = keys.subtree_range(scope)
    return lambda candidate: lo <= candidate < hi


def _entry(row: _Row) -> Entry:
    """A stored row as a listing entry.

    ``size`` comes from ``chars`` rather than from the text, which is the
    difference that lets a listing of ten thousand keys never open the content
    column.
    """
    return Entry(
        key=row.key,
        kind=entry_kind(row.key),
        size=row.chars,
        format=row.format,
        updated_at=row.updated_at,
    )


def _implicit(key: str) -> Entry:
    """A key that holds nothing and has something beneath it, as a listing entry.

    It has no row, so it has no size, format or timestamp -- and saying so with
    None three times is the honest answer rather than borrowing a descendant's.
    """
    return Entry(key=key, kind="implicit", size=None, format=None, updated_at=None)


__all__ = [
    "CHUNK",
    "COMPRESSION",
    "DEFAULT_STORE_FILE",
    "ENCODABLE",
    "FORMAT_VERSION",
    "BYTE_LENGTHS",
    "HELD_COLUMNS",
    "INDEX_COLUMNS",
    "PROBE",
    "ROW_GROUP_SIZE",
    "VERSION_KEY",
    "ParquetStore",
]
