"""The duckdb backend: that it agrees with SQLite, and what is only its own.

The contract is checked the way the parquet backend's is, and with the same
corpus and the same battery -- imported from ``test_store_parquet.py`` rather
than copied a third time: one corpus, put into both backends, every read put to
each and the answers asserted equal. What differs is how the corpus is laid out
on this side. It is split across several parts, and the parts are shuffled --
rows in no order within a part and none across them -- because arbitrary parts
are what this backend is for, and the case where it answers from one sorted
file proves nothing about the case it exists for.

Then the two things this design turns on, which have no counterpart in any
other backend: a key repeated across parts, paged through at every ``limit``
and required to come out exactly once per row -- the failure the paging rule
exists to prevent, and the only one that would be silent -- and the refusals a
directory has that a file does not.
"""

from __future__ import annotations

import io
import itertools
import random
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from conftest import (
    answers_alike,
    in_threads,
    page_facts,
    raises_rendered,
    walk_documents,
    walk_level,
)
from outrage import keys, maintenance, messages
from outrage import store as store_module
from outrage.cli import main
from outrage.mounts import open_mounts
from outrage.store import (
    EVERYTHING,
    UNBOUNDED,
    BackendError,
    BackupError,
    BoundedSubtree,
    KeyNotFoundError,
    KeyRange,
    ReadOnlyStoreError,
    SearchCriterion,
    Store,
)
from outrage.store_sqlite import SqliteStore

pytest.importorskip("duckdb", reason="the duckdb backend is an optional extra")
pytest.importorskip("pyarrow", reason="building a part needs the parquet extra")

import pyarrow as pa  # noqa: E402 - only once the skip above has had its say
import pyarrow.parquet as pq  # noqa: E402
from test_store_parquet import (  # noqa: E402
    _BYTE_OFFSETS,
    _KEYS,
    _METAS,
    _RANGES,
    _SUBTREES,
    CORPUS,
    _descendants,
)

from outrage.store_duckdb import DuckdbStore  # noqa: E402
from outrage.store_parquet import (  # noqa: E402
    COMPRESSION,
    ROW_GROUP_SIZE,
    VERSION_KEY,
    ParquetStore,
    _schema,
    _utf8_length,
)

# -- writing parts -----------------------------------------------------------
#
# From the measurement that gated this backend, where it built one corpus as a
# single sorted file and as parts in three shapes. A part is written through the
# parquet backend's own schema rather than a second definition of it, so it is
# a file `outrage pack` could have written -- except in the one respect that is
# the point, which is the order its rows are in.


def _rows(documents):
    """The columns a part holds, for ``(key, content, format, updated_at)`` each."""
    out = []
    for key, content, format, updated_at in documents:
        parsed = keys.parse(key)
        out.append(
            {
                "key": parsed.key,
                "doc_key": parsed.doc_key,
                "meta_name": parsed.meta_name,
                "meta_path": parsed.meta_path,
                "parent": parsed.parent,
                "content": content,
                "format": format,
                "updated_at": updated_at,
                "sort_key": keys.sort_form(parsed.key),
                "chars": len(content),
                "bytes": _utf8_length(content),
            }
        )
    return out


def _write_part(rows, path: Path, *, version: bytes | None = None) -> None:
    """One part holding ``rows`` in exactly the order given."""
    schema = _schema(pa)
    if version is not None:
        schema = schema.with_metadata({VERSION_KEY: version})
    table = pa.table({name: [row[name] for row in rows] for name in schema.names}, schema=schema)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path, row_group_size=ROW_GROUP_SIZE, compression=COMPRESSION)


def _shuffled_parts(directory: Path, documents, parts: int = 4, seed: int = 20260911) -> Path:
    """``documents`` dealt at random into ``parts`` files, each in no order at all."""
    rows = _rows(documents)
    random.Random(seed).shuffle(rows)
    for n in range(parts):
        _write_part(rows[n::parts], directory / f"part-{n:04d}.parquet")
    return directory


def _open(directory: Path) -> DuckdbStore:
    return DuckdbStore(directory.parent, filename=directory.name)


def _when(sqlite, key):
    return sqlite.retrieve_document(key).updated_at


@pytest.fixture
def sqlite(tmp_path):
    with SqliteStore(tmp_path / "s") as store:
        for key, content in CORPUS:
            store.store_document(key, content)
        yield store


@pytest.fixture
def duck(tmp_path, sqlite):
    """The same corpus, shuffled across four parts."""
    documents = [
        (key, content, sqlite.retrieve_document(key).format, _when(sqlite, key))
        for key, content in CORPUS
    ]
    with _open(_shuffled_parts(tmp_path / "d" / "ref", documents)) as store:
        yield store


@pytest.fixture
def packed(tmp_path):
    """A small store in two parts written by ``outrage pack``'s own builder."""
    directory = tmp_path / "d" / "ref"
    ParquetStore.build(
        directory / "one.parquet", [("a", "a body", None, None), ("a/!title", "A", None, None)]
    )
    ParquetStore.build(directory / "two.parquet", [("a/b", "below", None, None)])
    with _open(directory) as store:
        yield store


# -- the contract, as a comparison ---------------------------------------


def test_shuffled_parts_answer_every_read_as_sqlite_does(sqlite, duck):
    """The parquet backend's battery, put to a directory of shuffled parts.

    One test for one claim, as there: *these are the same store*. The parts
    hold the corpus in no order, so every read that assumed one -- a listing
    that expected its rows sorted, a page that ended on whatever row came last
    -- disagrees here and nowhere else.
    """
    for key in _KEYS:
        answers_alike(sqlite, duck, lambda s, k=key: s.exists(k))
        answers_alike(sqlite, duck, lambda s, k=key: s.descendant_count(k))
        answers_alike(sqlite, duck, lambda s, k=key: s.latest_change(k))
        answers_alike(sqlite, duck, lambda s, k=key: s.latest_change(k, whole_subtree=True))
        answers_alike(sqlite, duck, lambda s, k=key: s.retrieve_document(k))
        for at in _BYTE_OFFSETS:
            answers_alike(
                sqlite, duck, lambda s, k=key, b=at: s.retrieve_document(k, byte_offset=b)
            )
            answers_alike(
                sqlite,
                duck,
                lambda s, k=key, b=at: s.retrieve_document(k, byte_offset=b, max_chars=4),
            )
        answers_alike(
            sqlite, duck, lambda s, k=key: s.retrieve_document(k, pattern="a", byte_offset=1)
        )
        if key != keys.ROOT:
            answers_alike(sqlite, duck, lambda s, k=key: s.level_entry(k))
        for limit in (None, 0, 1, 2, 100):
            answers_alike(sqlite, duck, lambda s, k=key, n=limit: s.list_keys(k, limit=n))
        answers_alike(sqlite, duck, lambda s, k=key: walk_level(s, k))
        answers_alike(sqlite, duck, lambda s, k=key: _descendants(s, k))
        # A cursor naming each key in turn, whatever level it is on: the
        # listing has to cut a level at a key that is not in it, including one
        # beneath an implicit child, where the child's first row is past the
        # cursor and the child itself is not.
        for cursor in _KEYS:
            answers_alike(
                sqlite, duck, lambda s, k=key, c=cursor: s.list_keys(k, limit=3, cursor=c or None)
            )

    for key, key_range in itertools.product(_KEYS, _RANGES):
        answers_alike(sqlite, duck, lambda s, k=key, r=key_range: s.latest_change(k, key_range=r))
        answers_alike(
            sqlite, duck, lambda s, k=key, r=key_range: s.subtree_totals(k, key_range=r, chars=True)
        )

    for subtree, key_range, meta in itertools.product(_SUBTREES, _RANGES, _METAS):
        answers_alike(
            sqlite,
            duck,
            lambda s, t=subtree, r=key_range, m=meta: page_facts(
                s.get_documents(t, key_range=r, meta_name=m)
            ),
        )
        answers_alike(
            sqlite, duck, lambda s, t=subtree, r=key_range, m=meta: walk_documents(s, t, r, m)
        )

    names = ["title", ["title", "x"]]
    for subtree, key_range, meta in itertools.product(_SUBTREES, _RANGES, names):
        answers_alike(
            sqlite,
            duck,
            lambda s, t=subtree, r=key_range, m=meta: page_facts(
                s.keys_missing_meta(t, key_range=r, meta_name=m)
            ),
        )
        answers_alike(
            sqlite,
            duck,
            lambda s, t=subtree, r=key_range, m=meta: page_facts(
                s.keys_missing_meta(t, key_range=r, meta_name=m, limit=1)
            ),
        )
        for window in _RANGES:
            answers_alike(
                sqlite,
                duck,
                lambda s, t=subtree, r=key_range, m=meta, w=window: s.missing_meta_stats(
                    t, key_range=r, window=w, meta_name=m, sample=3
                ),
            )


def test_the_caps_page_shuffled_parts_to_the_same_end(sqlite, duck):
    """``max_chars``, ``limit`` and ``max_total_chars``, walked to exhaustion."""
    for max_chars, max_total, limit in itertools.product(
        [1, 5, 2000], [None, 1, 10, 100], [None, 1, 3]
    ):
        answers_alike(
            sqlite,
            duck,
            lambda s, c=max_chars, t=max_total, n=limit: walk_documents(
                s, EVERYTHING, UNBOUNDED, None, max_chars=c, max_total_chars=t, limit=n
            ),
        )


def test_shuffled_parts_slice_a_document_as_sqlite_does(sqlite, duck):
    for key in ("a", "a/b/c", "b", "wide"):
        for offset, length, pattern, occurrence, max_chars in itertools.product(
            [0, 1, 5], [None, 0, 2], [None, "a", "zz"], [0, 1], [1, 8000]
        ):
            answers_alike(
                sqlite,
                duck,
                lambda s, k=key, o=offset, ln=length, p=pattern, c=occurrence, m=max_chars: (
                    s.retrieve_document(
                        k, offset=o, length=ln, pattern=p, occurrence=c, max_chars=m
                    )
                ),
            )


def test_the_base_search_is_what_a_duckdb_store_answers(sqlite, duck):
    """``find_documents`` is inherited, and inherited answers must still agree."""
    for criteria, combine in [
        ([SearchCriterion("body", "contains", "document")], "any"),
        ([SearchCriterion("A", "line", "metadata", ("title",))], "any"),
    ]:
        expected = Store.find_documents(
            sqlite, BoundedSubtree("a"), criteria=criteria, combine=combine, scan_limit=3
        )
        found = duck.find_documents(
            BoundedSubtree("a"), criteria=criteria, combine=combine, scan_limit=3
        )
        assert found == expected


def test_one_sorted_file_and_shuffled_parts_are_the_same_store(tmp_path, sqlite, duck):
    """The layout the parquet backend reads, and the one this backend is for.

    A corpus packed into one sorted file and the same corpus shuffled across
    parts, read by the two backends meant for each. Cheaper than the battery
    and asking a different question: not whether this agrees with SQLite, but
    whether the two ways of holding a reference base are interchangeable.
    """
    ParquetStore.build(
        tmp_path / "p" / "ref.parquet",
        ((key, content, None, _when(sqlite, key)) for key, content in CORPUS),
    )
    with ParquetStore(tmp_path / "p", filename="ref.parquet") as parquet:
        for key in _KEYS:
            answers_alike(parquet, duck, lambda s, k=key: walk_level(s, k))
        for subtree in _SUBTREES:
            answers_alike(parquet, duck, lambda s, t=subtree: walk_documents(s, t, UNBOUNDED, None))


# -- a key held in more than one part --------------------------------------

#: One key held by three parts, one by two, and keys around them held once, so
#: a page boundary can land before a run, inside it, and after it.
_REPEATED = {
    "part-0000.parquet": [
        ("a", "first a", "2026-01-01T00:00:00+00:00"),
        ("a/!title", "A", "2026-01-01T00:00:00+00:00"),
        ("b", "only b", "2026-01-01T00:00:00+00:00"),
        ("c", "first c", "2026-01-01T00:00:00+00:00"),
        ("d/x", "under d", "2026-01-01T00:00:00+00:00"),
    ],
    "part-0001.parquet": [
        ("a", "second a", "2026-03-01T00:00:00+00:00"),
        ("c", "second c", "2026-01-01T00:00:00+00:00"),
    ],
    "part-0002.parquet": [
        ("a", "third a", "2026-02-01T00:00:00+00:00"),
        ("e", "only e", "2026-01-01T00:00:00+00:00"),
    ],
}


@pytest.fixture
def repeated(tmp_path):
    directory = tmp_path / "d" / "ref"
    for name, documents in _REPEATED.items():
        _write_part(
            _rows((key, content, "markdown", when) for key, content, when in documents),
            directory / name,
        )
    with _open(directory) as store:
        yield store


def _every_row(*, documents_only: bool = False):
    """Every row the parts hold, in the order a read walks them."""
    rows = [
        (keys.sort_form(key), name, key, content)
        for name, documents in _REPEATED.items()
        for key, content, _ in documents
        if not (documents_only and keys.parse(key).is_metadata)
    ]
    return [(key, content) for _, _, key, content in sorted(rows)]


def _walked(store, **caps):
    seen, pages, cursor = [], 0, None
    while True:
        page = store.get_documents(cursor=cursor, **caps)
        pages += 1
        assert pages < 100, "the cursor stopped moving"
        seen += [(item.key, item.content) for item in page.items]
        if page.next_cursor is None:
            return seen
        cursor = page.next_cursor


def test_a_repeated_key_is_paged_through_exactly_once_per_row_at_every_limit(repeated):
    """The failure the paging rule exists for, and the only silent one.

    A cursor names a key, so a page that ended between two rows of one key
    would resume past both and lose one, or before both and loop. Walked at
    every limit from 1 past the whole store, so a boundary falls at every
    position a run can be cut.
    """
    everything = _every_row(documents_only=True)
    for limit in range(1, len(everything) + 2):
        assert _walked(repeated, limit=limit) == everything, limit


def test_a_repeated_key_survives_a_character_budget_at_every_size(repeated):
    """The budget cuts a page the same way a limit does, so it is held to the same rule."""
    everything = _every_row(documents_only=True)
    for budget in range(1, 60):
        assert _walked(repeated, max_total_chars=budget) == everything, budget
        assert _walked(repeated, max_total_chars=budget, limit=2) == everything, budget


def test_a_run_longer_than_a_page_comes_back_whole(repeated):
    """The one case in which a page holds more than its limit.

    Stopping in front of the run would return nothing and a cursor that does
    not move; the run is bounded by the number of parts, so it is returned.
    """
    page = repeated.get_documents(limit=1)
    assert [item.content for item in page.items] == ["first a", "second a", "third a"]
    assert page.returned == 3
    assert page.next_cursor == "a"


def test_a_page_stops_in_front_of_a_run_rather_than_inside_it(repeated):
    page = repeated.get_documents(key_range=KeyRange(after="a"), limit=2)
    # `b`, then `c` twice: the second `c` would overrun, so the page gives the
    # first back and ends at `b`, one short of its limit.
    assert [item.key for item in page.items] == ["b"]
    assert page.next_cursor == "b"


def test_a_key_is_read_and_listed_as_its_newest_row(repeated):
    """A read and a listing entry agree, and both are the newest row.

    ``level_entry`` is how one key appears in its parent's listing, so the two
    cannot be allowed to differ -- and a mount table merges a level by key,
    so a listing that showed each row would reach an MCP caller as one entry
    beside a ``total`` counting all of them.
    """
    level = repeated.list_keys()
    assert [(entry.key, entry.kind, entry.size) for entry in level.items] == [
        ("a", "document", len("second a")),
        ("b", "document", len("only b")),
        ("c", "document", len("second c")),
        ("d", "implicit", None),
        ("e", "document", len("only e")),
    ]
    assert level.total == 5
    assert level.total_chars == sum(len(c) for c in ("second a", "only b", "second c", "only e"))
    for entry in level.items:
        assert repeated.level_entry(entry.key) == entry

    # Newest by time: part-0001's March beats part-0002's February.
    assert repeated.retrieve_document("a").content == "second a"
    # A tie in time goes to the later part.
    assert repeated.retrieve_document("c").content == "second c"
    assert repeated.exists("a")


def test_every_row_is_still_counted_below_a_listed_key(repeated):
    """The repeats are gone from the entries and not from what lies under them."""
    listed = next(e for e in repeated.list_keys(descendant_counts=True).items if e.key == "a")
    # `a/!title` once; the three rows of `a` itself are the entry, not below it.
    assert listed.descendants == 1
    assert repeated.subtree_totals("").keys == len(_every_row())


def test_a_listing_of_repeated_keys_pages_through_every_entry_once(repeated):
    everything = [(entry.key, entry.size) for entry in repeated.list_keys().items]
    for limit in range(1, len(everything) + 2):
        seen, cursor = [], None
        for _ in range(100):
            page = repeated.list_keys(limit=limit, cursor=cursor)
            seen += [(entry.key, entry.size) for entry in page.items]
            if page.next_cursor is None:
                break
            cursor = page.next_cursor
        assert seen == everything, limit


def test_a_repeated_document_missing_a_title_is_listed_once_per_row(repeated):
    everything = repeated.keys_missing_meta().items
    assert everything == ["b", "c", "c", "d/x", "e"]
    for limit in range(1, len(everything) + 2):
        seen, cursor = [], None
        for _ in range(100):
            page = repeated.keys_missing_meta(limit=limit, cursor=cursor)
            seen += page.items
            if page.next_cursor is None:
                break
            cursor = page.next_cursor
        assert seen == everything, limit


def test_totals_count_rows_and_agree_with_each_other(repeated):
    """Every row counted, and the two counts of "below" still one number."""
    assert repeated.get_documents().total == len(_every_row(documents_only=True))
    assert repeated.descendant_count("", whole_subtree=True) == len(_every_row())
    assert repeated.subtree_totals("").keys == len(_every_row())


def test_check_reports_repeated_keys_as_information_not_as_a_problem(repeated):
    report = maintenance.check(repeated)
    assert report.sound
    assert report.details["parts"] == "3"
    assert report.details["rows"] == str(len(_every_row()))
    # `a` three times and `c` twice: three rows compaction would remove.
    assert report.details["repeated rows"] == "3"


def _mounted(repeated, tmp_path):
    SqliteStore(tmp_path / "d").close()
    return open_mounts(tmp_path / "d", ["ref=ref,type=duckdb"])


def test_through_a_mount_every_row_is_paged_once_at_every_limit(repeated, tmp_path):
    """The mount table pages a subtree by asking each store for its own pages.

    It never cuts a store's page, and it trusts the store's cursor, so the rule
    that a page never ends inside a run survives the crossing with nothing in
    the mount layer knowing about it -- which is what this asserts rather than
    assumes.
    """
    everything = [(f"ref/{key}", content) for key, content in _every_row(documents_only=True)]
    with _mounted(repeated, tmp_path) as table:
        for limit in range(1, len(everything) + 2):
            seen, cursor = [], None
            for _ in range(100):
                page = table.get_documents(BoundedSubtree("ref"), limit=limit, cursor=cursor)
                seen += [(item.key, item.content) for item in page.items]
                if page.next_cursor is None:
                    break
                cursor = page.next_cursor
            assert seen == everything, limit


def test_through_a_mount_a_listing_totals_what_it_pages_through(repeated, tmp_path):
    """What went wrong while a listing showed each row: a total nothing reached."""
    with _mounted(repeated, tmp_path) as table:
        for limit in (1, 2, 3, None):
            seen, cursor, total = [], None, None
            for _ in range(100):
                page = table.list_keys("ref", limit=limit, cursor=cursor)
                total = page.total
                seen += [entry.key for entry in page.items]
                if page.next_cursor is None:
                    break
                cursor = page.next_cursor
            assert len(seen) == total == 5, limit


def test_dump_does_not_print_the_newest_row_under_an_older_one(tmp_path):
    """A capped row is finished by a read by key, and that read is the newest row.

    So an older row longer than the bulk cap would come out as the newer row's
    text under the older row's header, with nothing to say so. It is printed as
    far as the page reached it instead, and the header says why it stops.
    """
    older = "the older row\n" + "filler line\n" * 500
    directory = tmp_path / "d" / "ref"
    _write_part(
        _rows([("a", older, "markdown", "2026-01-01T00:00:00+00:00")]), directory / "0.parquet"
    )
    _write_part(
        _rows([("a", "the newer row\n", "markdown", "2026-03-01T00:00:00+00:00")]),
        directory / "1.parquet",
    )

    out = io.StringIO()
    status = main(["dump", "--dir", str(tmp_path / "d"), "--store", "ref,type=duckdb"], out)
    printed = out.getvalue()

    assert status == 0
    assert printed.count("the newer row") == 1
    assert "the older row" in printed
    assert (
        f"=== a  [{store_module.DEFAULT_BULK_MAX_CHARS} of {len(older)} characters; "
        f"reading the key whole gives a different document"
    ) in printed


# -- what a directory refuses ----------------------------------------------


def test_a_write_is_refused_by_the_backend_in_its_own_words(packed):
    with raises_rendered(ReadOnlyStoreError, "a directory of parquet parts") as raised:
        packed.store_document("a/new", "text")
    assert raised.value.code == "store-read-only"
    rendered = messages.render(raised.value)
    assert "written whole" not in rendered
    with raises_rendered(ReadOnlyStoreError, "duckdb store"):
        packed.delete("a", dry_run=True)


def test_a_refused_write_still_validates_its_arguments_first(packed):
    with pytest.raises(ValueError):
        packed.store_document("a/new", "text", format="nonsense")


def test_a_mount_refuses_a_write_in_the_backend_s_words_not_parquet_s(tmp_path):
    """The mount layer raises this refusal too, and has to say which store it is."""
    base = tmp_path / "base"
    ParquetStore.build(base / "ref" / "one.parquet", [("x", "x", None, None)])
    SqliteStore(base).close()
    with open_mounts(base, ["ref=ref,type=duckdb"]) as table:
        assert table.resolve("ref/x").read_only
        with raises_rendered(ReadOnlyStoreError, "duckdb store") as raised:
            table.resolve("ref/new").writable()
        assert "parquet store" not in messages.render(raised.value)
        assert table.retrieve_document("ref/x").content == "x"


def test_a_missing_directory_is_refused_rather_than_created(tmp_path):
    with raises_rendered(BackendError, "no directory of parquet parts") as raised:
        DuckdbStore(tmp_path, filename="nothing")
    assert raised.value.code == "duckdb-store-missing"
    assert not (tmp_path / "nothing").exists()


def test_a_single_file_is_pointed_at_the_parquet_backend(tmp_path):
    ParquetStore.build(tmp_path / "ref.parquet", [("x", "x", None, None)])
    with raises_rendered(BackendError, "parquet backend") as raised:
        DuckdbStore(tmp_path, filename="ref.parquet")
    assert raised.value.code == "duckdb-not-a-directory"


def test_a_directory_with_no_parts_is_refused(tmp_path):
    (tmp_path / "ref").mkdir()
    (tmp_path / "ref" / "notes.txt").write_text("not a part")
    with raises_rendered(BackendError, "holds no parquet parts") as raised:
        DuckdbStore(tmp_path, filename="ref")
    assert raised.value.code == "duckdb-no-parts"


def test_a_part_that_is_not_parquet_refuses_the_whole_directory(tmp_path):
    ParquetStore.build(tmp_path / "ref" / "one.parquet", [("x", "x", None, None)])
    (tmp_path / "ref" / "two.parquet").write_text("not parquet at all")
    with raises_rendered(BackendError, "cannot be read as parquet") as raised:
        DuckdbStore(tmp_path, filename="ref")
    assert raised.value.code == "duckdb-part-unreadable"


def test_a_part_that_is_not_an_outrage_store_is_named(tmp_path):
    ParquetStore.build(tmp_path / "ref" / "one.parquet", [("x", "x", None, None)])
    pq.write_table(pa.table({"key": ["y"]}), tmp_path / "ref" / "two.parquet")
    with raises_rendered(BackendError, "two.parquet is a parquet file but not") as raised:
        DuckdbStore(tmp_path, filename="ref")
    assert raised.value.code == "duckdb-part-not-a-store"


def test_parts_in_two_formats_are_refused_naming_both(tmp_path):
    rows = _rows([("x", "x", "markdown", "2026-01-01T00:00:00+00:00")])
    _write_part(rows, tmp_path / "ref" / "one.parquet", version=b"1")
    _write_part(rows, tmp_path / "ref" / "two.parquet")
    with raises_rendered(BackendError, "one.parquet is format 1 and two.parquet is format 2"):
        DuckdbStore(tmp_path, filename="ref")


def test_parts_in_an_older_format_are_refused_with_the_way_forward(tmp_path):
    rows = _rows([("x", "x", "markdown", "2026-01-01T00:00:00+00:00")])
    _write_part(rows, tmp_path / "ref" / "one.parquet", version=b"1")
    with raises_rendered(BackendError, "repack the parts") as raised:
        DuckdbStore(tmp_path, filename="ref")
    assert raised.value.code == "duckdb-format-older"


def test_parts_from_a_later_build_are_refused(tmp_path):
    rows = _rows([("x", "x", "markdown", "2026-01-01T00:00:00+00:00")])
    _write_part(rows, tmp_path / "ref" / "one.parquet", version=b"99")
    with raises_rendered(BackendError, "format 99") as raised:
        DuckdbStore(tmp_path, filename="ref")
    assert raised.value.code == "duckdb-format-newer"


def test_extensions_are_refused_in_words_true_of_a_directory_of_parts(packed):
    with raises_rendered(BackendError, "holds its documents as rows"):
        DuckdbStore.in_directory(packed.directory, filename="ref", extensions="keep")


# -- what a directory is ---------------------------------------------------


def test_only_visible_parquet_files_are_parts(tmp_path):
    """A producer writing a part under a hidden name must not have it read half written."""
    directory = tmp_path / "ref"
    ParquetStore.build(directory / "one.parquet", [("x", "x", None, None)])
    (directory / ".two.parquet").write_text("half written")
    (directory / "README").write_text("about these parts")
    with _open(directory) as store:
        assert [entry.key for entry in store.list_keys().items] == ["x"]


def test_the_parts_are_those_there_when_the_store_was_opened(tmp_path):
    directory = tmp_path / "ref"
    ParquetStore.build(directory / "one.parquet", [("x", "x", None, None)])
    with _open(directory) as store:
        ParquetStore.build(directory / "two.parquet", [("y", "y", None, None)])
        assert not store.exists("y")
    with _open(directory) as store:
        assert store.exists("y")


def test_the_backend_is_named_because_a_directory_cannot_name_it(tmp_path):
    ParquetStore.build(tmp_path / "ref" / "one.parquet", [("x", "x", None, None)])
    assert store_module._backend_for("ref", "duckdb") is DuckdbStore
    assert "duckdb" in store_module.backend_names()
    with store_module.open_store(tmp_path, filename="ref", backend="duckdb") as store:
        assert isinstance(store, DuckdbStore)
        assert store.path == tmp_path / "ref"
        assert store.directory == tmp_path


def test_reading_a_directory_needs_no_pyarrow(tmp_path):
    """Said by the module and by the extra, so checked in a process without it."""
    ParquetStore.build(tmp_path / "ref" / "one.parquet", [("x", "hello", None, None)])
    script = (
        "import sys\n"
        "class Block:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name.split('.')[0] in ('pyarrow', 'numpy', 'pandas'):\n"
        "            raise ImportError(name)\n"
        "sys.meta_path.insert(0, Block())\n"
        "from outrage.store_duckdb import DuckdbStore\n"
        f"store = DuckdbStore({str(tmp_path)!r}, filename='ref')\n"
        "print(store.retrieve_document('x').content, store.list_keys().total)\n"
    )
    done = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert done.stdout.startswith("hello 1")


def test_closing_twice_is_allowed_and_reopening_still_reads(packed):
    packed.close()
    packed.close()
    assert packed.retrieve_document("a/b").content == "below"


def test_a_thread_whose_cursor_was_closed_takes_a_new_one(packed):
    """``close`` drops the database; a thread that read before reads after."""
    ready, go = threading.Event(), threading.Event()
    seen = []

    def reader():
        seen.append(packed.retrieve_document("a").content)
        ready.set()
        go.wait()
        seen.append(packed.retrieve_document("a").content)

    worker = threading.Thread(target=reader)
    worker.start()
    ready.wait()
    packed.close()
    go.set()
    worker.join()
    assert seen == ["a body", "a body"]


def test_parallel_readers_all_get_the_document_they_asked_for(tmp_path):
    documents = [(f"doc/{n}", f"content {n}", None, None) for n in range(40)]
    directory = tmp_path / "ref"
    for n in range(4):
        ParquetStore.build(directory / f"part-{n}.parquet", documents[n::4])
    with _open(directory) as store:

        def work(i):
            for n in range(i, 40, 6):
                assert store.retrieve_document(f"doc/{n}").content == f"content {n}"
                assert store.list_keys("doc", limit=5).total == 40

        in_threads(work)


def test_a_container_says_what_is_beneath_it(packed):
    with raises_rendered(KeyNotFoundError) as raised:
        packed.retrieve_document("nothing")
    assert raised.value.code == "key-not-found"


# -- maintenance -------------------------------------------------------------


def test_backing_up_copies_the_parts_the_store_opened(packed, tmp_path):
    ParquetStore.build(packed.path / "late.parquet", [("late", "arrived after open", None, None)])
    done = packed.backup(tmp_path / "copy")
    assert sorted(path.name for path in done.path.iterdir()) == ["one.parquet", "two.parquet"]
    assert done.documents == 3
    assert done.integrity == "ok"
    with _open(done.path) as copy:
        assert copy.retrieve_document("a/b").content == "below"


def test_a_backup_over_something_already_there_is_refused(packed, tmp_path):
    (tmp_path / "copy").mkdir()
    (tmp_path / "copy" / "keep").write_text("mine")
    with pytest.raises(BackupError):
        packed.backup(tmp_path / "copy" / "keep")


def test_check_answers_for_a_duckdb_store_in_its_own_terms(packed):
    report = maintenance.check(packed)
    assert report.backend == "duckdb"
    assert report.sound
    assert report.documents == 2
    assert report.metadata == 1
    assert report.details["parts"] == "2"
    assert report.details["repeated rows"] == "0"
    assert maintenance.repair(packed) == []
