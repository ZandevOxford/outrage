"""What does a random read into a large document actually cost, per backend?

The measurement behind `plans/byte-offsets`. That plan turns on a claim about
cost -- that a character offset cannot be honoured cheaply by anything, and
that byte addressing is the only thing which makes a seek into a 20 MB document
cheap -- and a claim about cost is worth nothing quoted from a transcript. It
depends on the SQLite build, the page size, the filesystem and the machine, so
this is here to be re-run rather than trusted.

Three questions, and the plan answers differently to each:

* **Today's path.** `retrieve_document` on the real backend, which reads the
  whole document and slices it in Python. Measured through the project's own
  class rather than a hand-written SELECT, so what is timed is what ships.
* **The proposed path.** Incremental blob I/O for SQLite, `seek` for a
  directory of files, and -- for parquet -- nothing, because a row's value is
  decompressed whole out of its row group and there is no sub-value addressing
  to reach for. A backend with no fast path is measured anyway; "no win" is a
  result and the table should have to say it.
* **The totals.** `Excerpt.total` counts *characters*, and in SQLite
  `length(content)` is a full scan of the value while `octet_length` reads a
  stored byte count. Today that costs nothing, because the read has already
  materialised the string. The moment a seek stops materialising it, the
  character total becomes the most expensive thing in the call -- which is the
  whole argument for a stored length column.

Run it with the project's environment on the path::

    python tools/measure_offsets.py
    python tools/measure_offsets.py --sizes 1 5 20 100 --repeats 7

Nothing here touches a store that already exists: every document is synthetic
and every store is built in a temporary directory that is removed on the way
out.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import statistics
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from outrage import store
from outrage.store_parquet import ParquetStore

#: The text documents are built from. Deliberately not ASCII: where every
#: character is one byte the two offsets coincide and a measurement cannot tell
#: a correct implementation from one that confuses them. The ratio here is
#: about 1.06 bytes per character, which is roughly what prose with the odd
#: accent or dash comes to -- an all-CJK document would be nearer 3.
UNIT = "The quick brown fox jumps over the lazy dog. é中\n"

#: The key every synthetic document is written to.
KEY = "big"

#: What a read asks for, matching `store.DEFAULT_MAX_CHARS` so the numbers are
#: about the call a caller actually makes.
TAKE = store.DEFAULT_MAX_CHARS


def document(target_bytes: int) -> str:
    """A document of about ``target_bytes`` bytes, built from :data:`UNIT`."""
    return UNIT * (target_bytes // len(UNIT.encode()))


def timed(work: Callable[[], object], repeats: int) -> float:
    """The median of ``repeats`` runs of ``work``, in milliseconds.

    The median rather than the mean, and one untimed warm-up first. What is
    being compared is the shape of the work -- decode the whole value against
    seek to a page -- and a single scheduling hiccup in a run of seven should
    not be allowed to reorder the table.
    """
    work()
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        work()
        samples.append((time.perf_counter() - start) * 1000)
    return statistics.median(samples)


def positions(text: str) -> list[tuple[str, int, int]]:
    """Where to seek to, as ``(name, character offset, byte offset)``.

    Three points rather than one, because the interesting cost in SQLite is not
    the read: it is walking the overflow page chain to reach the offset, which
    is linear in the offset. A number taken only at the start of a document
    would report a speed-up nothing sustains.
    """
    total = len(text)
    return [
        (name, start, len(text[:start].encode()))
        for name, start in (
            ("start", 0),
            ("middle", (total // 2) - (TAKE // 2)),
            ("end", max(total - TAKE, 0)),
        )
    ]


def measure_sqlite(directory: Path, text: str, repeats: int) -> list[tuple[str, float]]:
    """Today's read, `substr` in SQL, and incremental blob I/O, on one store."""
    rows: list[tuple[str, float]] = []
    with store.open_store(directory, backend="sqlite") as opened:
        opened.store_document(KEY, text, format="markdown")
        for name, start, _ in positions(text):
            rows.append(
                (
                    f"retrieve_document ({name})",
                    timed(
                        lambda start=start: opened.retrieve_document(
                            KEY, offset=start, max_chars=TAKE
                        ),
                        repeats,
                    ),
                )
            )
        path = opened.path

    connection = sqlite3.connect(path)
    try:
        located = connection.execute("SELECT rowid FROM documents WHERE key = ?", (KEY,))
        rowid = located.fetchone()[0]

        for name, start, _ in positions(text):
            rows.append(
                (
                    f"SQL substr ({name})",
                    timed(
                        lambda start=start: connection.execute(
                            "SELECT substr(content, ?, ?) FROM documents WHERE key = ?",
                            (start + 1, TAKE, KEY),
                        ).fetchone(),
                        repeats,
                    ),
                )
            )

        for name, _, byte_start in positions(text):
            rows.append(
                (
                    f"blobopen seek ({name})",
                    timed(
                        lambda byte_start=byte_start: _blob_slice(connection, rowid, byte_start),
                        repeats,
                    ),
                )
            )

        rows.append(
            (
                "length(content)  [characters]",
                timed(
                    lambda: connection.execute(
                        "SELECT length(content) FROM documents WHERE key = ?", (KEY,)
                    ).fetchone(),
                    repeats,
                ),
            )
        )
        rows.append(
            (
                "octet_length(content)  [bytes]",
                timed(
                    lambda: connection.execute(
                        "SELECT octet_length(content) FROM documents WHERE key = ?", (KEY,)
                    ).fetchone(),
                    repeats,
                ),
            )
        )
        rows.append(("byte-domain pattern scan", timed(lambda: _scan(connection, rowid), repeats)))
    finally:
        connection.close()
    return rows


def _blob_slice(connection: sqlite3.Connection, rowid: int, byte_start: int) -> str:
    """One seek and one read, decoded and cut back to a character boundary.

    ``TAKE * 4`` is the over-read: a caller asking for characters cannot know
    how many bytes they occupy, and four is the most UTF-8 spends on one. That
    is 32 KB against 8 000 characters at the worst ratio and the same 32 KB at
    the best, which is the price of keeping the cap in the unit the caller
    budgets in. ``errors='ignore'`` stands in for the boundary trim the real
    implementation owes both ends of the slice.
    """
    with connection.blobopen("documents", "content", rowid, readonly=True) as blob:
        blob.seek(byte_start)
        raw = blob.read(TAKE * 4)
    return raw.decode("utf-8", "ignore")[:TAKE]


def _scan(connection: sqlite3.Connection, rowid: int, chunk: int = 1 << 20) -> int | None:
    """Find a needle that is not there, over chunked blob reads.

    The worst case for a search -- the whole document, and no early exit -- and
    the comparison it is for is against decoding the whole document to run
    ``str.find`` over it. Searching the bytes is sound because UTF-8 is
    self-synchronising: an encoded needle cannot match starting part-way
    through an encoded character, so a byte match is a character match.
    """
    needle = b"a needle no document here contains"
    with connection.blobopen("documents", "content", rowid, readonly=True) as blob:
        size = len(blob)
        position = 0
        carry = b""
        while position < size:
            blob.seek(position)
            data = carry + blob.read(chunk)
            found = data.find(needle)
            if found != -1:
                return position - len(carry) + found
            carry = data[-(len(needle) - 1) :]
            position += chunk
    return None


def measure_files(directory: Path, text: str, repeats: int) -> list[tuple[str, float]]:
    """Today's read against a seek into the file the document already is."""
    rows: list[tuple[str, float]] = []
    with store.open_store(directory, backend="files") as opened:
        opened.store_document(KEY, text, format="markdown")
        for name, start, _ in positions(text):
            rows.append(
                (
                    f"retrieve_document ({name})",
                    timed(
                        lambda start=start: opened.retrieve_document(
                            KEY, offset=start, max_chars=TAKE
                        ),
                        repeats,
                    ),
                )
            )
        path = next(p for p in Path(opened.path).rglob("*") if p.is_file() and KEY in p.name)

    for name, _, byte_start in positions(text):
        rows.append((f"seek + read ({name})", timed(lambda b=byte_start: _seek(path, b), repeats)))
    return rows


def _seek(path: Path, byte_start: int) -> str:
    """The files backend's whole fast path, which is the standard library."""
    with open(path, "rb") as handle:
        handle.seek(byte_start)
        return handle.read(TAKE * 4).decode("utf-8", "ignore")[:TAKE]


def measure_parquet(directory: Path, text: str, repeats: int) -> list[tuple[str, float]]:
    """Today's read, twice, and no proposed path because there is none to propose.

    Both numbers are needed and only together do they say anything true.
    ``ParquetStore._content`` keeps the last row group it decompressed, per
    thread, so a second read of the same document does no I/O and no decoding
    at all -- it slices a Python string that is already in memory, which is why
    the warm figure beats every other backend and means nothing about parquet's
    seeking. The cold figure is what a first read costs, and it is the one a
    fast path would have to improve on. Reaching into the cache to drop it is
    what makes the two separable; nothing but a measurement should do that.
    """
    path = directory / "store.parquet"
    ParquetStore.build(path, [(KEY, text, "markdown", None)])
    rows: list[tuple[str, float]] = []
    with store.open_store(directory, filename=path.name) as opened:

        def read(start: int, cold: bool) -> object:
            if cold:
                opened._local.cache = None
            return opened.retrieve_document(KEY, offset=start, max_chars=TAKE)

        for name, start, _ in positions(text):
            for label, cold in (("warm", False), ("cold", True)):
                rows.append(
                    (
                        f"retrieve_document ({name}, {label})",
                        timed(lambda start=start, cold=cold: read(start, cold), repeats),
                    )
                )
    return rows


BACKENDS = {
    "sqlite": measure_sqlite,
    "files": measure_files,
    "parquet": measure_parquet,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=[1, 5, 20],
        help="document sizes to measure, in megabytes (default: 1 5 20)",
    )
    parser.add_argument(
        "--backends",
        nargs="+",
        choices=sorted(BACKENDS),
        default=sorted(BACKENDS),
        help="which backends to measure (default: all three)",
    )
    parser.add_argument(
        "--repeats", type=int, default=7, help="timed runs per measurement (default: 7)"
    )
    arguments = parser.parse_args(argv)

    print(f"python {sys.version.split()[0]}, sqlite {sqlite3.sqlite_version}")
    for megabytes in arguments.sizes:
        text = document(megabytes * 1024 * 1024)
        print(f"\n== {megabytes} MB: {len(text)} characters, {len(text.encode())} bytes")
        for name in arguments.backends:
            root = Path(tempfile.mkdtemp(prefix="outrage-measure-"))
            try:
                rows = BACKENDS[name](root, text, arguments.repeats)
            finally:
                shutil.rmtree(root, ignore_errors=True)
            print(f"  {name}")
            for label, milliseconds in rows:
                print(f"    {label:34s} {milliseconds:9.3f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
