"""The parquet backend: that it agrees with SQLite, and what is only its own.

``test_store.py`` says a second backend should pass it unchanged but for the
fixtures at the top. **A read-only backend cannot**, and pretending otherwise
would mean either a fixture that quietly rebuilds the file behind every write
-- making a store that refuses writes look like one that takes them -- or
skipping half the file and calling the rest a contract.

So the contract is checked the other way round, in
:func:`test_the_two_backends_answer_every_read_identically`: one corpus, built
into both backends, the same battery of calls put to each, and the answers
asserted equal. That is stronger than re-running the read half of
``test_store.py`` would be, because it compares against a live oracle rather
than against expectations written down twice, and it is honest about the
asymmetry. It also guards exactly what the ``Store``/backend split exists to
prevent: two stores that disagree about what a key is are two namespaces.

The rest of this file is what has no SQLite counterpart -- the refusals, the
file's own format, building it, and the two claims the module docstring makes
about what a read touches.
"""

from __future__ import annotations

import ast
import itertools
import pathlib
import threading

import pytest

from conftest import (
    answers_alike,
    in_threads,
    page_facts,
    raises_rendered,
    walk_documents,
    walk_level,
)
from outrage import bulk, keys, messages
from outrage import store as store_module
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
from outrage.store_files import FilesystemStore
from outrage.store_parquet import (
    FORMAT_VERSION,
    HELD_COLUMNS,
    INDEX_COLUMNS,
    ParquetStore,
)
from outrage.store_sqlite import SqliteStore

pytest.importorskip("pyarrow", reason="the parquet backend is an optional extra")


#: A corpus chosen for the places the two backends could disagree rather than
#: for size: numeric segments that sort wrong as text, a key whose sibling
#: (``a-x``) sorts between it and its own children under a naive ordering, a
#: document at the root, metadata on the root, JSON beside markdown, a
#: document with children so that a container read has something to be about,
#: and a metadata namespace holding documents of its own -- the one shape whose
#: split is not the one the stored columns record.
CORPUS = [
    ("", "root document"),
    ("!title", "The store itself"),
    ("a", "a body"),
    ("a/!title", "A"),
    ("a/!summary", "sum of a"),
    ("a/!changelog", "what changed"),
    ("a/!changelog/!title", "Changelog"),
    ("a/!changelog/22", "note twenty-two"),
    ("a/!changelog/22/!title", "Note 22"),
    ("a/2", "a two"),
    ("a/10", "a ten"),
    ("a/10/!title", "A ten"),
    ("a/b", "a b body"),
    ("a/b/c", "deep"),
    ("a/b/c/!title", "Deep"),
    ("a-x", "adversarial sibling"),
    ("a-x/!title", "A-x"),
    ("b", '{"json": true}'),
    ("b/!title", "B"),
    ("context/1/design", "design one"),
    ("context/2/design", "design two"),
    ("context/10/design", "design ten"),
    ("context/10/design/!title", "Ten"),
    ("notes/src/file.py", "note"),
    # Characters of one, two, three and four bytes, so a byte offset into it
    # is a different number from the character offset and the comparison below
    # can tell a backend that confused them.
    ("wide", "# Caf\u00e9\n\nna\u00efve \u2014 \U0001f600 tail\n"),
    ("z", "last"),
]

#: Byte positions the battery reads ``wide`` from: its start, one inside each
#: width of character, its last byte, and past its end.
_BYTE_OFFSETS = [0, 1, 5, 6, 13, 14, 15, 20, 21, 22, 31, 32, 99]


@pytest.fixture
def sqlite(tmp_path):
    """The corpus in the backend that can be written."""
    with SqliteStore(tmp_path / "s") as store:
        for key, content in CORPUS:
            store.store_document(key, content)
        yield store


@pytest.fixture
def parquet(tmp_path, sqlite):
    """The same corpus packed, timestamps included.

    Built from ``sqlite`` rather than from ``CORPUS`` so ``updated_at`` matches
    and the comparison below is about the store rather than about the clock.
    """
    ParquetStore.build(
        tmp_path / "p" / "ref.parquet",
        ((key, content, None, sqlite.retrieve_document(key).updated_at) for key, content in CORPUS),
    )
    with ParquetStore(tmp_path / "p", filename="ref.parquet") as store:
        yield store


@pytest.fixture
def packed(tmp_path):
    """A small parquet store, for the tests that do not need a comparison."""
    ParquetStore.build(
        tmp_path / "p" / "ref.parquet",
        [("a", "a body", None, None), ("a/!title", "A", None, None), ("a/b", "below", None, None)],
    )
    with ParquetStore(tmp_path / "p", filename="ref.parquet") as store:
        yield store


# -- the contract, as a comparison ---------------------------------------

#: Keys the battery asks about: the root, a document with children, one
#: without, containers that hold nothing themselves, a key that is not there,
#: and the numeric and adversarial ones.
_KEYS = [
    "",
    "a",
    "a/b",
    "a/10",
    "context",
    "context/10",
    "notes",
    "z",
    "a-x",
    "nope",
    "a/b/c",
    "a/!changelog",
    "a/!changelog/22",
    # The one document whose characters are not its bytes.
    "wide",
]

#: One of each bound :class:`~outrage.store.KeyRange` can carry, then the pairs
#: that matter: a stretch either side of an excluded subtree, and a bound
#: naming a key that does not exist.
_RANGES = [
    UNBOUNDED,
    KeyRange(after="a"),
    KeyRange(after_inclusive="a"),
    KeyRange(after_subtree="a"),
    KeyRange(before="b"),
    KeyRange(before_inclusive="b"),
    KeyRange(final_subtree="a"),
    KeyRange(after="a", before="z"),
    KeyRange(after_subtree="a", before="z"),
    KeyRange(after_inclusive="context/2", final_subtree="context/10"),
    KeyRange(after="nope"),
]

_SUBTREES = [
    EVERYTHING,
    BoundedSubtree(key="a"),
    BoundedSubtree(key="a", depth=0),
    BoundedSubtree(key="a", depth=1),
    BoundedSubtree(key="context", depth=2),
    BoundedSubtree(key=None, depth=1),
    BoundedSubtree(key="nope"),
    BoundedSubtree(key="", depth=0),
    BoundedSubtree(key="a/!changelog"),
    BoundedSubtree(key="a/!changelog", depth=0),
]

_METAS = [None, "title", ["title"], ["title", "summary"], ["summary"]]


def test_the_two_backends_answer_every_read_identically(sqlite, parquet):
    """The contract, checked against a live oracle rather than expectations.

    Around four thousand comparisons across every read on the interface, every
    bound, and the caps and cursors that page them. Written as one test rather
    than parametrised into thousands because what is being asserted is a single
    claim -- *these are the same store* -- and a run reporting four thousand
    passes would say that claim four thousand times and locate a failure no
    better than the assertion message does.
    """
    for key in _KEYS:
        answers_alike(sqlite, parquet, lambda s, k=key: s.exists(k))
        answers_alike(sqlite, parquet, lambda s, k=key: s.descendant_count(k))
        answers_alike(sqlite, parquet, lambda s, k=key: s.latest_change(k))
        answers_alike(sqlite, parquet, lambda s, k=key: s.latest_change(k, whole_subtree=True))
        answers_alike(sqlite, parquet, lambda s, k=key: s.retrieve_document(k))
        # The portability contract: a byte offset is the unit that survives
        # leaving a store, so the two backends have to return the same content
        # for one even though only one of them can seek to it. This is the
        # test that fails when a fast path drifts from the conversion it
        # replaced -- including where it snaps, and where it stops.
        for at in _BYTE_OFFSETS:
            answers_alike(
                sqlite, parquet, lambda s, k=key, b=at: s.retrieve_document(k, byte_offset=b)
            )
            answers_alike(
                sqlite,
                parquet,
                lambda s, k=key, b=at: s.retrieve_document(k, byte_offset=b, max_chars=4),
            )
        answers_alike(
            sqlite, parquet, lambda s, k=key: s.retrieve_document(k, pattern="a", byte_offset=1)
        )
        if key != keys.ROOT:
            answers_alike(sqlite, parquet, lambda s, k=key: s.level_entry(k))
        for limit in (None, 1, 2, 100):
            answers_alike(sqlite, parquet, lambda s, k=key, n=limit: s.list_keys(k, limit=n))
        # Paged to the end at a page size of two, so a level of three or more
        # crosses a boundary and the totals are asserted on every page.
        answers_alike(sqlite, parquet, lambda s, k=key: walk_level(s, k))

    for key, key_range in itertools.product(_KEYS, _RANGES):
        answers_alike(
            sqlite, parquet, lambda s, k=key, r=key_range: s.latest_change(k, key_range=r)
        )

    for subtree, key_range, meta in itertools.product(_SUBTREES, _RANGES, _METAS):
        answers_alike(
            sqlite,
            parquet,
            lambda s, t=subtree, r=key_range, m=meta: page_facts(
                s.get_documents(t, key_range=r, meta_name=m)
            ),
        )
        answers_alike(
            sqlite,
            parquet,
            lambda s, t=subtree, r=key_range, m=meta: walk_documents(s, t, r, m),
        )

    names = ["title", ["title", "x"]]
    for subtree, key_range, meta in itertools.product(_SUBTREES, _RANGES, names):
        answers_alike(
            sqlite,
            parquet,
            lambda s, t=subtree, r=key_range, m=meta: page_facts(
                s.keys_missing_meta(t, key_range=r, meta_name=m)
            ),
        )
        for window in _RANGES:
            answers_alike(
                sqlite,
                parquet,
                lambda s, t=subtree, r=key_range, m=meta, w=window: s.missing_meta_stats(
                    t, key_range=r, window=w, meta_name=m, sample=3
                ),
            )


def test_the_base_search_is_the_oracle_for_every_backend(sqlite, parquet):
    """An optimized override must remain identical to the inherited baseline."""
    searches = [
        ([SearchCriterion("body", "contains", "document")], "any"),
        ([SearchCriterion("A", "line", "metadata", ("title",))], "any"),
        (
            [
                SearchCriterion(r"\bdesign\b", "regex", "document"),
                SearchCriterion("Ten", "contains", "metadata", ("title",)),
            ],
            "all",
        ),
    ]
    for criteria, combine in searches:
        expected = Store.find_documents(
            sqlite,
            BoundedSubtree("a"),
            criteria=criteria,
            combine=combine,
            scan_limit=3,
        )
        assert (
            sqlite.find_documents(
                BoundedSubtree("a"), criteria=criteria, combine=combine, scan_limit=3
            )
            == expected
        )
        assert (
            parquet.find_documents(
                BoundedSubtree("a"), criteria=criteria, combine=combine, scan_limit=3
            )
            == expected
        )


def test_the_two_backends_agree_under_every_combination_of_caps(sqlite, parquet):
    """The three bounds on a read multiply, and they page to the same end.

    ``max_chars`` caps a document, ``limit`` and the cursor page the
    collection, and ``max_total_chars`` caps the page as a whole. Walked to
    exhaustion rather than checked one page at a time, because what has to
    match is the *sequence* -- a backend can agree about every page and still
    stop in a different place.
    """
    for max_chars, max_total, limit in itertools.product(
        [1, 5, 2000], [None, 1, 10, 100], [None, 1, 3]
    ):
        answers_alike(
            sqlite,
            parquet,
            lambda s, c=max_chars, t=max_total, n=limit: walk_documents(
                s, EVERYTHING, UNBOUNDED, None, max_chars=c, max_total_chars=t, limit=n
            ),
        )


def test_the_two_backends_slice_a_document_identically(sqlite, parquet):
    """Offsets, lengths, patterns and occurrences, over the same three documents.

    :func:`outrage.store._excerpt` is shared, so this is really asking whether the
    parquet backend hands it the same four fields SQLite does -- and whether a
    pattern that does not occur fails the same way.
    """
    for key in ("a", "a/b/c", "b"):
        for offset, length, pattern, occurrence, max_chars in itertools.product(
            [0, 1, 5], [None, 0, 2], [None, "a", "zz"], [0, 1], [1, 8000]
        ):
            answers_alike(
                sqlite,
                parquet,
                lambda s, k=key, o=offset, ln=length, p=pattern, c=occurrence, m=max_chars: (
                    s.retrieve_document(
                        k, offset=o, length=ln, pattern=p, occurrence=c, max_chars=m
                    )
                ),
            )


# -- what only this backend does -----------------------------------------


def test_a_write_is_refused_by_the_backend_rather_than_by_a_flag(packed):
    """And the message does not offer a flag, because none would work."""
    with raises_rendered(ReadOnlyStoreError, "written whole rather than updated") as raised:
        packed.store_document("a", "new")
    assert raised.value.code == "store-read-only"

    with raises_rendered(ReadOnlyStoreError, "cannot delete"):
        packed.delete("a")


def test_a_refused_write_still_validates_its_arguments_first(packed):
    """A bad key and a good one are different questions, and get different answers.

    Answering both with "this store does not write" would hide a bug behind a
    limitation: the same argument would be just as wrong against the store the
    caller meant to write to.
    """
    with pytest.raises(keys.InvalidKeyError):
        packed.store_document("a/b\x00c", "content")
    with pytest.raises(ValueError, match="format must be one of"):
        packed.store_document("a", "content", "parquet")
    with pytest.raises(TypeError, match="contents must be a string"):
        packed.store_document("a", "content", contents=object())


def test_a_refused_write_is_recorded_in_the_event_log(tmp_path):
    """What the log is for is what a store was *asked* to do.

    A refused write is one of the more interesting things anyone asks, and a
    backend that skipped the decorator would leave the log silent about it
    while SQLite recorded every write it took.
    """
    import json

    from outrage.eventlog import EventLog

    ParquetStore.build(tmp_path / "ref.parquet", [("a", "body", None, None)])
    log = EventLog(tmp_path / "log.jsonl")
    with ParquetStore(tmp_path, filename="ref.parquet", log=log) as store:
        with pytest.raises(ReadOnlyStoreError):
            store.store_document("a", "new")
    log.close()

    events = [json.loads(line) for line in (tmp_path / "log.jsonl").read_text().splitlines()]
    written = [e for e in events if e.get("op") == "store_document"]
    assert len(written) == 1
    assert written[0]["error"]["type"] == "ReadOnlyStoreError"
    assert written[0]["args"]["key"] == "a"


def test_a_missing_parquet_store_is_refused_rather_than_created(tmp_path):
    """Every other backend opens empty because a first write would fill it.

    This one has no first write, so an empty store could only ever read back
    empty -- and a mistyped name would mount as a reference base that is simply
    missing, which no read could ever contradict.
    """
    with raises_rendered(BackendError, "no parquet store at") as raised:
        ParquetStore(tmp_path, filename="absent.parquet")
    assert raised.value.code == "parquet-store-missing"


def test_a_parquet_file_that_is_not_a_store_is_refused(tmp_path):
    """Its columns would be somebody else's, and would mean something else."""
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    pq.write_table(pa.table({"key": ["a"], "content": ["b"]}), tmp_path / "other.parquet")

    with raises_rendered(BackendError, "not an outrage store"):
        ParquetStore(tmp_path, filename="other.parquet")


def test_a_file_from_a_later_build_is_refused_rather_than_read(tmp_path, monkeypatch):
    """Nothing is migrated in place here, so the only answer is to repack.

    The version is checked when the store is opened rather than on the first
    read, so a mount table naming an unreadable file fails while somebody is
    still looking at the command that named it.
    """
    from outrage import store_parquet

    monkeypatch.setattr(store_parquet, "FORMAT_VERSION", store_parquet.FORMAT_VERSION + 1)
    ParquetStore.build(tmp_path / "future.parquet", [("a", "body", None, None)])
    monkeypatch.undo()

    with raises_rendered(BackendError, "repack it or upgrade outrage") as raised:
        ParquetStore(tmp_path, filename="future.parquet")
    assert raised.value.code == "parquet-format-newer"


def test_a_version_1_file_is_read_by_deriving_the_split_from_its_keys(tmp_path):
    """The older layout, read whole and re-split -- not repacked.

    Version 1 has no ``meta_path`` column and a ``meta_name`` written under the
    rule that a name swallowed everything below the first ``!``. Both come off
    ``key``, which every version carries, so the file opens and answers about
    the namespace exactly as a repacked one would. Nothing is written back:
    this backend has no migrations, and that stance is intact.
    """
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    from outrage import store_parquet

    written = ["a", "a/!title", "a/!changelog", "a/!changelog/22", "a/!changelog/22/!title"]

    def version_1_meta_name(key):
        _, sep, tail = key.partition("/!")
        return tail if sep else None

    schema = pa.schema(
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
        metadata={store_parquet.VERSION_KEY: b"1"},
    )
    ordered = sorted(written, key=keys.sort_form)
    pq.write_table(
        pa.table(
            {
                "key": ordered,
                "doc_key": [keys.parse(k).doc_key for k in ordered],
                "meta_name": [version_1_meta_name(k) for k in ordered],
                "parent": [keys.parse(k).parent for k in ordered],
                "content": ["body" for _ in ordered],
                "format": ["markdown" for _ in ordered],
                "updated_at": ["2026-01-01T00:00:00+00:00" for _ in ordered],
                "sort_key": [keys.sort_form(k) for k in ordered],
                "chars": [4 for _ in ordered],
            },
            schema=schema,
        ),
        tmp_path / "old.parquet",
    )

    with ParquetStore(tmp_path, filename="old.parquet") as store:
        assert [e.key for e in store.list_keys("a/!changelog").items] == ["a/!changelog/22"]
        survey = store.get_documents(BoundedSubtree("a/!changelog"), meta_name="title")
        assert [e.key for e in survey.items] == ["a/!changelog/22/!title"]
        # And from outside, the note is not one of `a`'s titles.
        assert [e.key for e in store.get_documents(meta_name="title").items] == ["a/!title"]


def test_building_refuses_a_wildcard_because_there_is_nothing_to_allocate_from(tmp_path):
    """A ``?`` is a number read out of the store, and there is no store yet."""
    with raises_rendered(BackendError, "nothing to read"):
        ParquetStore.build(tmp_path / "out.parquet", [("tmp/?", "body", None, None)])


def test_building_refuses_an_existing_file_unless_told_to_replace_it(tmp_path):
    target = tmp_path / "out.parquet"
    ParquetStore.build(target, [("a", "one", None, None)])
    with raises_rendered(BackendError, "already exists"):
        ParquetStore.build(target, [("a", "two", None, None)])

    ParquetStore.build(target, [("a", "two", None, None)], overwrite=True)
    with ParquetStore(tmp_path, filename="out.parquet") as store:
        assert store.retrieve_document("a").content == "two"


def test_building_takes_the_last_of_two_documents_claiming_one_key(tmp_path):
    """Which is what overwriting means everywhere else in the store.

    Silently keeping the first would make the result depend on an iteration
    order the caller did not choose.
    """
    ParquetStore.build(
        tmp_path / "out.parquet", [("a", "first", None, None), ("a", "second", None, None)]
    )
    with ParquetStore(tmp_path, filename="out.parquet") as store:
        assert store.retrieve_document("a").content == "second"


def test_building_validates_every_key_the_way_a_writing_backend_does(tmp_path):
    """A build that admitted a key ``store_document`` refuses is a second namespace."""
    with pytest.raises(keys.InvalidKeyError):
        ParquetStore.build(tmp_path / "out.parquet", [("a/b\x00c", "body", None, None)])
    assert not (tmp_path / "out.parquet").exists()


def test_the_file_is_written_in_key_order_and_says_so(tmp_path):
    """The sort is what every bound above bisects, and the footer records it.

    Asserted on the file rather than through the store, because a reader other
    than this one -- a notebook, a query engine -- is entitled to be told the
    file is ordered rather than having to discover it.
    """
    pq = pytest.importorskip("pyarrow.parquet")
    ParquetStore.build(
        tmp_path / "out.parquet",
        [(key, content, None, None) for key, content in CORPUS],
    )
    opened = pq.ParquetFile(tmp_path / "out.parquet")
    written = opened.read(columns=["key", "sort_key"])
    forms = written.column("sort_key").to_pylist()
    assert forms == sorted(forms)
    assert [keys.sort_form(k) for k in written.column("key").to_pylist()] == forms
    assert opened.metadata.row_group(0).sorting_columns


def test_chars_is_stored_so_a_total_never_opens_the_content_column(packed, monkeypatch):
    """The claim the module docstring makes, asserted rather than asserted at.

    Enforced by making a read of the content column fail, so any path that
    reaches it turns this into an error rather than a slower pass.

    Note what is *not* claimed. A survey returns the title text, and a title is
    a document like any other, so ``get_documents(meta_name=...)`` reads
    content for the rows it returns -- it just never reads the documents being
    surveyed, and never reads anything to state the totals. Getting that
    distinction wrong is easy and is why it is written down twice.
    """

    def refuse(*args, **kwargs):
        raise AssertionError("the content column was opened")

    monkeypatch.setattr(packed, "_content", refuse)

    listing = packed.list_keys("a")
    assert [entry.size for entry in listing.items] == [len("A"), len("below")]
    assert listing.total_chars == len("A") + len("below")

    assert packed.keys_missing_meta().total_chars == len("below")
    assert packed.missing_meta_stats().total_chars == len("below")
    # One, not two: `a/!title` shares `a`'s doc_key, so it sits *at* the key
    # rather than below it -- the same answer SQLite gives, and the corner
    # `level_entry` exists for.
    assert packed.descendant_count("a") == 1
    assert packed.exists("a") and not packed.exists("nope")
    # A survey's totals, without taking the page that would read the titles.
    assert packed.get_documents(meta_name=["title"], limit=0).total_chars == len("A")


def test_a_page_of_documents_reads_each_row_group_once(tmp_path, monkeypatch):
    """Content is read by row group, and a page is contiguous, so it costs one.

    Twenty documents in one group is one decompression rather than twenty,
    which is the whole reason the last group read is kept.
    """
    from outrage import store_parquet

    monkeypatch.setattr(store_parquet, "ROW_GROUP_SIZE", 8)
    ParquetStore.build(
        tmp_path / "many.parquet",
        [(f"k/{n:03d}", f"document {n}", None, None) for n in range(24)],
    )
    with ParquetStore(tmp_path, filename="many.parquet") as store:
        reads = []
        original = store._parquet.read_row_group
        monkeypatch.setattr(
            store._parquet,
            "read_row_group",
            lambda group, **kw: (reads.append(group), original(group, **kw))[1],
        )
        page = store.get_documents(limit=8)
        assert page.returned == 8
        # Eight documents, one group of eight, one read.
        assert reads == [0]
        store.get_documents(limit=8, cursor=page.next_cursor)
        assert reads == [0, 1]


def test_backing_up_copies_the_file_because_the_file_is_the_store(packed, tmp_path):
    """No WAL, so nothing has been written anywhere else.

    Which is the point worth recording: the trap
    ``project/reference/snapshots`` exists for is SQLite's rather than the
    store's. The copy is still verified, because what can go wrong here is the
    copy itself.
    """
    result = packed.backup(tmp_path / "copy.parquet")
    assert result.documents == 3
    assert result.integrity == "ok"
    assert result.bytes == packed.path.stat().st_size

    with ParquetStore(tmp_path, filename="copy.parquet") as copy:
        assert copy.retrieve_document("a").content == "a body"


def test_a_backup_over_the_store_itself_is_refused(packed):
    """``backup_path``'s refusal, which is the base's and not this backend's."""
    with raises_rendered(BackupError, "the store itself"):
        packed.backup(packed.path, overwrite=True)


def test_a_container_says_what_is_beneath_it_rather_than_that_it_is_missing(parquet):
    """The same answer SQLite gives, and the one that turns a dead end into a call."""
    with pytest.raises(KeyNotFoundError) as raised:
        parquet.retrieve_document("context")
    assert raised.value.code == "key-is-a-container"
    assert raised.value.details["beneath"] == 4

    with pytest.raises(KeyNotFoundError) as raised:
        parquet.retrieve_document("nope")
    assert raised.value.code == "key-not-found"


def test_closing_twice_is_allowed_and_reopening_still_reads(tmp_path, packed):
    """A mount table closes what it opened when a failure means unwinding."""
    packed.close()
    packed.close()
    with ParquetStore(tmp_path / "p", filename="ref.parquet") as store:
        assert store.retrieve_document("a").content == "a body"


# -- choosing a backend --------------------------------------------------


def test_the_extension_chooses_the_backend(tmp_path):
    """The whole of the selection rule, and the reason no new grammar was added."""
    assert store_module._backend_for("ref.parquet") is ParquetStore
    assert store_module._backend_for("ref.sqlite") is SqliteStore
    assert store_module._backend_for(None) is SqliteStore
    # An unrecognised name is the default backend, not an error: a store file
    # has always been free to be called anything, and refusing every unclaimed
    # name would break configurations that named one before a backend claimed
    # an extension.
    assert store_module._backend_for("ref.db") is SqliteStore


def test_a_backend_may_be_named_instead_of_inferred(tmp_path):
    """The seam a directory of files needs, since a directory has no extension.

    Named rather than guessed at, so the two mistakes are answered differently:
    an unrecognised *extension* falls back to the default, and an unrecognised
    *name* is refused. One is a file called something a backend never claimed;
    the other is somebody saying a word this build does not know, and a store
    quietly opened as some other kind reads as a store that is simply empty.
    """
    assert store_module._backend_for("documents", "files") is FilesystemStore
    # The name wins over the extension, which is the point of asking.
    assert store_module._backend_for("ref.sqlite", "parquet") is ParquetStore
    assert store_module.backend_names() == ("files", "parquet", "sqlite")

    with raises_rendered(BackendError, "there is no 'tree' backend"):
        store_module._backend_for("documents", "tree")


def test_default_store_opens_a_parquet_file_without_naming_a_backend(tmp_path):
    """Which is what lets a mount spec say `ref=python.parquet` and mean it."""
    ParquetStore.build(tmp_path / "ref.parquet", [("a", "body", None, None)])
    with store_module.open_store(tmp_path, filename="ref.parquet") as store:
        assert isinstance(store, ParquetStore)
        assert store.retrieve_document("a").content == "body"


def test_every_backend_states_whether_it_can_be_written():
    """Read from the source, because the failure it guards is a backend that
    forgets to say -- which inherits ``True`` and reports itself writable.

    A store that *answers* a write is one that defines ``store_document``,
    which is what picks the concrete ones out here. ``FileStore`` is a base
    and not a backend: it has no storage to have a policy about, and making it
    state one would be a third place for the three that do to disagree with.
    """
    stated = 0
    for path in sorted(pathlib.Path(store_module.__file__).parent.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.ClassDef):
                continue
            if not any(
                isinstance(b, ast.Name) and b.id in ("Store", "FileStore") for b in node.bases
            ):
                continue
            if not any(
                isinstance(item, ast.FunctionDef) and item.name == "store_document"
                for item in node.body
            ):
                continue
            stated += 1
            assert any(
                isinstance(item, ast.Assign)
                and any(getattr(t, "id", None) == "writable" for t in item.targets)
                for item in node.body
            ), f"{path.name}: {node.name} does not say whether it is writable"
    assert stated >= 3, "every backend and the mount table should have been found"


# -- packing -------------------------------------------------------------


def test_packing_a_store_carries_metadata_and_timestamps_across(sqlite, tmp_path):
    """A compaction rather than a copy that quietly restamps the corpus.

    Metadata especially: a survey by title is worth nothing if the pack it came
    from left every title behind, which is the same argument the export makes.
    """
    target = tmp_path / "packed.parquet"
    transfers = list(bulk.pack(target, bulk.documents_from_store(sqlite)))
    assert {t.action for t in transfers} == {store_module.READ}
    assert len(transfers) == len(CORPUS)

    with ParquetStore(tmp_path, filename="packed.parquet") as store:
        for key, content in CORPUS:
            assert store.retrieve_document(key).content == content
            assert store.retrieve_document(key).updated_at == (
                sqlite.retrieve_document(key).updated_at
            )


def test_a_parquet_store_is_a_source_a_copy_reads_whole(sqlite, parquet, tmp_path):
    """A reference base copied back out, key for key and stamp for stamp.

    The direction that needs nothing new: a copy asks its source only for the
    reads every store answers, so a file written whole is a source like any
    other even though nothing can be written to it.
    """
    with SqliteStore(tmp_path / "back") as target:
        transfers = list(target.copy_from(parquet))
        assert {t.action for t in transfers} == {store_module.WROTE}
        for key, content in CORPUS:
            assert target.retrieve_document(key).content == content
            assert target.retrieve_document(key).updated_at == (
                sqlite.retrieve_document(key).updated_at
            )


def test_copying_into_a_parquet_store_is_refused_document_by_document(parquet, tmp_path):
    """Read only is read only, and the copy says which end refused.

    Not a hole in ``copy_from``: a parquet file is written whole and the way
    in is a build, which is what ``pack`` is. What matters here is that the
    refusal arrives per document, carrying the backend's own refusal, rather
    than as an exception ending a transfer half way through.

    The refusal travels as the error and not as a sentence, so this asserts the
    code: which end refused is a fact, and the prose beside it belongs to
    whichever front end is reading. Rendered here too, once, because "the
    backend's own" is a claim about the sentence and not only about the code.
    """
    with SqliteStore(tmp_path / "source") as source:
        source.store_document("zzz/nothing-here", "body")
        transfers = list(parquet.copy_from(source))
    assert [t.action for t in transfers] == [store_module.FAILED]
    assert transfers[0].reason is None
    assert transfers[0].error is not None
    assert transfers[0].error.code == "store-read-only"
    assert "written whole rather than updated in place" in messages.render(transfers[0].error)


def test_a_built_timestamp_is_normalised_like_a_written_one(tmp_path):
    """A build is a write, so the stamp it records has the one spelling too.

    The rows are bisected in key order and read back as strings; a file whose
    timestamps were whatever its caller happened to spell would compare
    against a store's own by luck.
    """
    target = tmp_path / "built.parquet"
    ParquetStore.build(
        target,
        [
            ("a", "one", None, "2020-01-02T05:04:05+02:00"),
            ("b", "two", None, "2020-01-02T03:04:05"),
        ],
    )
    with ParquetStore(tmp_path, filename="built.parquet") as store:
        assert store.retrieve_document("a").updated_at == "2020-01-02T03:04:05+00:00"
        assert store.retrieve_document("b").updated_at == "2020-01-02T03:04:05+00:00"


def test_a_built_timestamp_that_is_not_one_is_refused(tmp_path):
    with pytest.raises(ValueError, match="ISO 8601"):
        ParquetStore.build(tmp_path / "built.parquet", [("a", "one", None, "yesterday")])


def test_packing_a_store_and_packing_its_export_reach_the_same_store(sqlite, tmp_path):
    """The two sources are the same mapping, which is what makes them one verb."""
    # A subtree rather than the whole store, because the root *document* has
    # no file it can be written to -- `path_for_key` says so -- and an export
    # that cannot carry it is not a disagreement between the two sources.
    list(bulk.export_tree(sqlite, "a", tmp_path / "tree"))
    from_store = tmp_path / "a.parquet"
    from_tree = tmp_path / "b.parquet"
    list(bulk.pack(from_store, bulk.documents_from_store(sqlite, "a")))
    list(bulk.pack(from_tree, bulk.documents_from_tree(tmp_path / "tree", hidden=True)))

    with ParquetStore(tmp_path, filename="a.parquet") as one:
        with ParquetStore(tmp_path, filename="b.parquet") as two:
            assert [e.key for e in one.get_documents().items] == [
                e.key for e in two.get_documents().items
            ]
            assert one.get_documents().total_chars == two.get_documents().total_chars


def test_a_pack_that_is_interrupted_leaves_no_store_behind(sqlite, tmp_path):
    """Which is why the report says `read` and not `wrote`.

    A parquet store is sorted on the way in and its statistics describe the
    whole of it, so there is no point at which half a file is a usable store.
    An import can honestly report a document as stored the moment it is; this
    cannot, and saying so is the difference.
    """
    target = tmp_path / "partial.parquet"
    transfers = bulk.pack(target, bulk.documents_from_store(sqlite))
    assert next(transfers).action == store_module.READ
    transfers.close()
    assert not target.exists()


def test_a_dry_run_reports_everything_and_writes_nothing(sqlite, tmp_path):
    target = tmp_path / "none.parquet"
    transfers = list(bulk.pack(target, bulk.documents_from_store(sqlite), dry_run=True))
    assert len(transfers) == len(CORPUS)
    assert not target.exists()


def test_packing_a_tree_maps_paths_exactly_as_an_import_would(tmp_path):
    """Shared helpers rather than a second mapping, so the two cannot drift."""
    source = tmp_path / "tree"
    (source / "a").mkdir(parents=True)
    (source / "a" / "one.md").write_text("# One")
    (source / "a" / "!title.md").write_text("A")
    (source / "two.json").write_text('{"k": 1}')

    list(bulk.pack(tmp_path / "out.parquet", bulk.documents_from_tree(source)))
    with ParquetStore(tmp_path, filename="out.parquet") as store:
        assert [e.key for e in store.get_documents().items] == ["a/one", "two"]
        assert store.retrieve_document("a/!title").content == "A"
        assert store.retrieve_document("two").format == "json"


def test_packing_a_tree_reports_what_it_could_not_map(tmp_path):
    """A symlink is named and not followed, and a binary file is not mangled."""
    source = tmp_path / "tree"
    source.mkdir()
    (source / "good.md").write_text("fine")
    (source / "binary.md").write_bytes(b"\xff\xfe\x00")
    (source / "link.md").symlink_to(source / "good.md")

    reported = list(bulk.documents_from_tree(source))
    actions = {transfer.action for transfer, _ in reported}
    assert actions == {store_module.READ, store_module.SKIPPED, store_module.FAILED}
    assert [row for _, row in reported if row is not None] == [("good", "fine", "markdown", None)]


def test_check_answers_for_a_parquet_store_in_its_own_terms(packed):
    """The five row questions any backend answers, and the one that is its own.

    This used to be a refusal: ``check`` reached for ``store.connection`` and
    was made to say so in a sentence. The refusal was the minimum, and the
    real answer is that most of what a check asks is not SQLite's -- so a
    parquet store gets a real report rather than an apology.
    """
    from outrage import maintenance

    report = maintenance.check(packed)

    assert report.backend == "parquet"
    assert (report.documents, report.metadata) == (2, 1)
    assert report.characters == len("a body") + len("A") + len("below")
    # Its own storage, in vocabulary SQLite has no answer for -- and with no
    # integrity or write-ahead log reported as a zero.
    assert report.details["order"] == "sorted"
    assert report.details["rows"] == "3"
    assert "integrity" not in report.details
    assert "log" not in report.details
    assert report.sound and not report.problems


def test_repair_of_a_parquet_store_does_nothing_and_says_it_did_nothing(packed):
    """An empty list, not a refusal and not a claim to have acted.

    Different from ``check`` finding nothing: this says there is no state the
    storage could reach that moving bytes would fix, which is provable for one
    immutable file with no sidecar and no free pages.
    """
    from outrage import maintenance

    assert maintenance.repair(packed) == []


def test_the_row_checks_are_not_sqlites_and_fire_for_parquet_too(tmp_path):
    """The evidence that five of the seven checks belong above the backend.

    ``parent`` is a denormalisation -- it exists so listing a level is a lookup
    rather than a scan -- and **both** backends keep one, for the same reason.
    So both can be handed a file where it disagrees with the key it was derived
    from, which makes a document unlistable while it is still readable by key.
    That was checked in SQL until this split, which read as SQLite's question
    and never was.
    """
    import pyarrow.parquet as pq

    from outrage import maintenance

    path = tmp_path / "p" / "ref.parquet"
    ParquetStore.build(path, [("a", "one", None, None), ("a/b", "two", None, None)])

    table = pq.read_table(path)
    parents = table.column("parent").to_pylist()
    parents[table.column("key").to_pylist().index("a/b")] = "elsewhere"
    column = table.schema.get_field_index("parent")
    pq.write_table(table.set_column(column, "parent", [parents]), path)

    with ParquetStore(path.parent, filename=path.name) as store:
        report = maintenance.check(store)

    assert not report.sound
    problem = next(p for p in report.problems if p.code == maintenance.ROWS_UNDER_WRONG_KEY)
    assert problem.severity == "warning"
    assert "a/b claims parent 'elsewhere', implies 'a'" in problem.detail


def test_check_finds_a_parquet_file_that_is_not_in_sort_order(tmp_path):
    """Parquet's ``integrity_check``: a file that reads wrongly rather than failing.

    Every lookup bisects ``sort_key``. Rows out of order do not raise -- they
    return a confident wrong answer, with nothing anywhere to contradict it --
    so this is the one thing about the file worth checking, and it is an error
    rather than a warning.
    """
    import pyarrow.parquet as pq

    from outrage import maintenance

    path = tmp_path / "p" / "ref.parquet"
    ParquetStore.build(path, [("a", "one", None, None), ("b", "two", None, None)])

    # Rewrite the same rows in the wrong order, keeping the schema and its
    # metadata, which is what a file assembled by something other than `build`
    # could plausibly look like.
    table = pq.read_table(path)
    pq.write_table(table.take([1, 0]), path)

    with ParquetStore(path.parent, filename=path.name) as store:
        report = maintenance.check(store)

    assert report.details["order"] == "not sorted"
    assert not report.sound
    problem = next(p for p in report.problems if p.code == maintenance.ROWS_OUT_OF_ORDER)
    assert problem.severity == "error"
    assert "outrage pack" in problem.detail
    # Reported, and left alone: rebuilding is not moving bytes about.
    assert not report.repairable


def test_a_file_handle_and_its_row_group_cache_do_not_escape_their_thread(tmp_path):
    """Each thread gets its own of both, mirroring the SQLite connection.

    Asserted on the objects rather than by racing readers, and deliberately.
    Two threads sharing the cache genuinely can return a different document's
    text -- the check on the group and the read of the content are two
    operations -- but the window is a bytecode or two wide, so a test that
    hammers it passes with the bug in place. That was tried, and it did.
    Pinning the design that removes the window is the test that fails when
    somebody undoes it.

    The handle matters more than the cache. A ``ParquetFile`` holds a file
    object with a seek position and a reader with buffered state, so two
    threads reading row groups through one is the same mistake
    ``planned/concurrency`` records, and this one is in C.
    """
    ParquetStore.build(
        tmp_path / "many.parquet",
        [(f"k/{n:03d}", f"document {n}", None, None) for n in range(60)],
    )
    # The objects, not their ids. A thread's locals are freed when it ends, so
    # `id()` of a dead thread's cache is reused by a live one's and the test
    # reports sharing that is not there -- which it did, first time.
    handles: dict[int, object] = {}
    caches: dict[int, object] = {}
    lock = threading.Lock()

    with ParquetStore(tmp_path, filename="many.parquet") as store:

        def note(worker):
            # Reads a document, which opens this thread's handle and fills its
            # cache, and checks it got the right one while it is here.
            assert store.retrieve_document("k/030").content == "document 30"
            with lock:
                handles[worker] = store._parquet
                caches[worker] = store._local.cache

        in_threads(note, threads=4)

    assert len({id(handle) for handle in handles.values()}) == 4
    assert len({id(cache) for cache in caches.values()}) == 4


def test_parallel_readers_all_get_the_document_they_asked_for(tmp_path, monkeypatch):
    """A smoke test over the design above, at a row-group size that crosses.

    It does not reliably catch a shared cache -- see the test above for why --
    but it does catch a handle that cannot serve two threads at once, which is
    the failure that raises rather than lies.
    """
    from outrage import store_parquet

    monkeypatch.setattr(store_parquet, "ROW_GROUP_SIZE", 4)
    ParquetStore.build(
        tmp_path / "many.parquet",
        [(f"k/{n:03d}", f"document {n}", None, None) for n in range(60)],
    )

    with ParquetStore(tmp_path, filename="many.parquet") as store:

        def read(worker):
            for n in range(60):
                found = store.retrieve_document(f"k/{n:03d}").content
                assert found == f"document {n}", f"worker {worker} read {found!r}"

        in_threads(read)


def test_read_only_is_the_backend_and_the_mount_together(tmp_path):
    """Both, and they compose: neither one replaces the other.

    A SQLite store is read-write or read-only according to how it was mounted.
    A parquet store is read-only either way -- the flag can say so and adds
    nothing, and leaving the flag off takes nothing away.
    """
    from outrage.mounts import open_mounts

    ParquetStore.build(tmp_path / "base" / "ref.parquet", [("a", "body", None, None)])
    SqliteStore(tmp_path / "base", filename="rw.sqlite").close()
    SqliteStore(tmp_path / "base", filename="ro.sqlite").close()

    with open_mounts(
        tmp_path / "base",
        ["rw=rw.sqlite", "pq=ref.parquet"],
        ["ro=ro.sqlite"],
    ) as table:
        assert not table.resolve("rw/x").read_only
        assert table.resolve("ro/x").read_only
        assert table.resolve("pq/x").read_only

    # And naming the parquet mount read-only as well is neither an error nor a
    # change: the flag is redundant against storage that already refuses.
    with open_mounts(tmp_path / "base", ["rw=rw.sqlite"], ["pq=ref.parquet"]) as table:
        assert table.resolve("pq/x").read_only
        assert not table.resolve("rw/x").read_only


# -- the index, once it stopped being a row per key -----------------------
#
# `plans/wikipedia-import/reader` is why these exist. The index used to hold a
# `_Row` per key and three dictionaries over them; it now holds the file's own
# Arrow columns and derives all four from the order the file is written in. The
# comparison against SQLite above is the specification and passes either way,
# which is the point -- these are the invariants the *derivations* rest on, and
# each one is a way the change could have been silently wrong.


def test_an_implicit_key_is_listed_although_no_row_says_so(tmp_path):
    """A key that holds nothing and has something beneath it still lists.

    The `children` map recorded this eagerly, walking each key's ancestors on
    the way in. The walk derives it instead: it lands on a row *below* the
    child rather than on the child, which is the same fact read off the order.
    Two levels of it, so a chain of implicit keys is covered rather than one.
    """
    ParquetStore.build(
        tmp_path / "p" / "ref.parquet",
        [("a/b/c/d", "deep", None, None), ("a/b/c/e", "also deep", None, None)],
    )
    with ParquetStore(tmp_path / "p", filename="ref.parquet") as store:
        assert [entry.key for entry in store.list_keys().items] == ["a"]
        assert store.level_entry("a").kind == "implicit"
        assert store.level_entry("a/b").kind == "implicit"
        assert [entry.key for entry in store.list_keys("a/b/c").items] == ["a/b/c/d", "a/b/c/e"]
        # Nothing is stored at it, so it has no size, format or timestamp --
        # rather than borrowing a descendant's.
        assert store.level_entry("a").size is None
        assert store.level_entry("a").updated_at is None


def test_a_level_is_listed_in_order_without_the_level_being_sorted(tmp_path):
    """The file's order is the level's order, including where they differ.

    Nothing sorts a level any more, which is only sound because ``sort_form``
    order is what the file is already in -- so the keys that sort *differently*
    as plain text are what says it works. A numeric segment pads, so ``2``
    comes before ``10``; and a child's own row may be absent while its subtree
    still fixes where it sorts.
    """
    ParquetStore.build(
        tmp_path / "p" / "ref.parquet",
        [(key, "body", None, None) for key in ("x/2", "x/10", "x/9/under", "x/1")],
    )
    with ParquetStore(tmp_path / "p", filename="ref.parquet") as store:
        assert [entry.key for entry in store.list_keys("x").items] == [
            "x/1",
            "x/2",
            "x/9",
            "x/10",
        ]
        assert store.level_entry("x/9").kind == "implicit"


def test_a_child_with_a_long_subtree_is_skipped_by_bisecting_past_it(tmp_path):
    """The walk steps over a small subtree and bisects over a large one.

    Both paths have to reach the same next sibling, and `PROBE` is where they
    part. So: one child with nothing beneath it, one with fewer descendants
    than the probe allows, and one with many more.
    """
    from outrage.store_parquet import PROBE

    rows = [("t/alone", "body", None, None)]
    rows += [(f"t/small/{n}", "body", None, None) for n in range(PROBE - 2)]
    rows += [(f"t/large/{n}", "body", None, None) for n in range(PROBE * 5)]
    rows += [("t/last", "body", None, None)]
    ParquetStore.build(tmp_path / "p" / "ref.parquet", rows)

    with ParquetStore(tmp_path / "p", filename="ref.parquet") as store:
        page = store.list_keys("t")
        assert [entry.key for entry in page.items] == [
            "t/alone",
            "t/large",
            "t/last",
            "t/small",
        ]
        assert page.total == 4


def test_metadata_is_found_by_looking_at_the_next_row_not_by_searching(tmp_path):
    """A survey's "does this carry a title" is the rows adjacent to the key.

    That is only true because ``sort_form`` marks a metadata segment below an
    ordinary one, so a key's metadata sorts after it and before any subkey.
    The corpus below is arranged so that a walk which stopped at the first
    non-matching name, or which counted metadata one level too deep, would get
    a different answer.
    """
    ParquetStore.build(
        tmp_path / "p" / "ref.parquet",
        [
            ("a", "body", None, None),
            ("a/!author", "someone", None, None),
            ("a/!title", "A", None, None),
            ("a/b", "below", None, None),
            ("b", "body", None, None),
            # Metadata of a's metadata, not of a: `a/!title` carries `of`, and
            # `a` does not.
            ("c", "body", None, None),
            ("c/!title", "C", None, None),
            ("c/!title/!of", "the title", None, None),
        ],
    )
    with ParquetStore(tmp_path / "p", filename="ref.parquet") as store:
        assert store.keys_missing_meta(meta_name="title").items == ["a/b", "b"]
        # `author` sorts before `title`, so a walk that gave up on the first
        # name it did not want would miss the title behind it -- `c` is here
        # because it has a title and no author, and `a` is absent because it
        # has both.
        assert store.keys_missing_meta(meta_name="author").items == ["a/b", "b", "c"]
        # `of` is a name on `a/!title`, and on nothing else -- so every
        # document lacks it, `a` included.
        assert store.keys_missing_meta(meta_name="of").items == ["a", "a/b", "b", "c"]


def test_carrying_a_name_is_a_fact_about_the_store_not_about_the_range(tmp_path):
    """A bound that cuts between a document and its title leaves it titled.

    The lookahead deliberately reaches outside the selection. Whether a
    document has a title is a fact about the store; a caller asking about a
    stretch of the key order is not asking to have that fact re-decided. The
    range below ends at ``a``, so ``a/!title`` is outside it.
    """
    ParquetStore.build(
        tmp_path / "p" / "ref.parquet",
        [("a", "body", None, None), ("a/!title", "A", None, None), ("z", "body", None, None)],
    )
    with ParquetStore(tmp_path / "p", filename="ref.parquet") as store:
        within = KeyRange(before_inclusive="a")
        assert store.keys_missing_meta(key_range=within).items == []
        assert store.missing_meta_stats(key_range=within).total == 0


def test_the_two_selection_paths_agree_where_a_depth_budget_forces_the_slow_one(sqlite, parquet):
    """A depth budget takes the Python walk; without one the predicate vectorises.

    Two implementations of one predicate is two chances to disagree, so the
    pair is compared directly rather than only through the battery above --
    against SQLite, which has neither.
    """
    for key in ("", "one", "one/two"):
        for depth in (None, 0, 1, 2, 5):
            subtree = BoundedSubtree(key=key or None, depth=depth)
            answers_alike(sqlite, parquet, lambda s, t=subtree: page_facts(s.get_documents(t)))
            answers_alike(sqlite, parquet, lambda s, t=subtree: page_facts(s.keys_missing_meta(t)))


def test_a_repeated_column_is_dictionary_encoded_and_a_distinct_one_is_not(tmp_path):
    """Encoding is measured against the column, not assumed to help.

    A store packed in one pass carries one timestamp for every row and encoding
    it is four bytes a row against twenty-nine. A store imported from a corpus
    with a real timestamp per document carries distinct ones, and encoding
    those is four bytes a row *on top*. Both files below are read by the same
    code; what differs is only what it chose.
    """
    import pyarrow as pa

    from outrage.store_parquet import ENCODABLE

    same = [(f"k{n}", "body", "markdown", "2026-09-01T00:00:00+00:00") for n in range(200)]
    apart = [
        (f"k{n}", "body", "markdown", f"2026-09-01T00:{n // 60:02}:{n % 60:02}+00:00")
        for n in range(200)
    ]

    def encoded(rows, name):
        target = tmp_path / name / "ref.parquet"
        ParquetStore.build(target, rows)
        with ParquetStore(target.parent, filename="ref.parquet") as store:
            column = store._index.columns["updated_at"]
            # The values are what matters either way; the encoding is a
            # representation and every read goes through the same accessors.
            assert store.retrieve_document("k7").updated_at == rows[7][3]
            return pa.types.is_dictionary(column.type)

    assert "updated_at" in ENCODABLE
    assert encoded(same, "one")
    assert not encoded(apart, "many")


def test_the_derived_columns_agree_with_the_ones_the_file_still_stores(packed):
    """``doc_key`` and ``parent`` are recomputed, and must match what is written.

    They are no longer read into the index -- between them they were a quarter
    of what an open store cost -- but they are still written, and ``check``
    still reads them from the file. If the derivation and the column ever
    disagreed, a sound file would start reporting itself broken.
    """
    import pyarrow.parquet as pq

    table = pq.read_table(packed.path)
    stored = zip(
        table.column("key").to_pylist(),
        table.column("doc_key").to_pylist(),
        table.column("parent").to_pylist(),
        strict=True,
    )
    for key, doc_key, parent in stored:
        # Against ``keys.parse``, which is what ``maintenance._report_parents``
        # compares the stored column with -- so this is the same derivation the
        # check will make, not a second opinion written beside it.
        assert keys.parse(key).doc_key == doc_key
        assert keys.parse(key).parent == parent

    # And the audit reads the stored ones, so the two are compared for real by
    # `maintenance.check` on every file it is given.
    from outrage import maintenance

    assert maintenance.check(packed).sound


# -- the byte-length column ----------------------------------------------
#
# Written by default, left out on request, and read by *nothing here yet*.
# Which of the two lengths is expensive is a property of the storage: SQLite
# gets bytes from a blob handle and a directory of files from `st_size`, and
# only this backend has to open the content column to find out. And a parquet
# file is never updated in place, so a store packed without the column can
# gain it only by being packed again -- which is why it is written now, at the
# one moment it costs a flag test per document, rather than when something
# first wants it.


#: A document whose bytes and characters differ, so a column holding one
#: cannot pass for a column holding the other.
WIDE_DOC = "héllo wörld \U0001f600"


def _column(path, name):
    pq = pytest.importorskip("pyarrow.parquet")
    opened = pq.ParquetFile(path)
    if name not in opened.schema_arrow.names:
        return None
    return opened.read(columns=[name]).column(name).to_pylist()


def test_a_pack_writes_each_document_s_length_in_bytes(tmp_path):
    target = tmp_path / "out.parquet"
    ParquetStore.build(target, [("a", "ascii", None, None), ("b", WIDE_DOC, None, None)])

    assert _column(target, "bytes") == [len(b"ascii"), len(WIDE_DOC.encode())]
    # Beside `chars` and not instead of it: the two differ exactly where the
    # document is not ASCII, which is the whole reason both are kept.
    assert _column(target, "chars") == [len("ascii"), len(WIDE_DOC)]
    assert _column(target, "bytes") != _column(target, "chars")


def test_a_pack_can_be_asked_not_to_write_it(tmp_path):
    target = tmp_path / "out.parquet"
    ParquetStore.build(target, [("a", WIDE_DOC, None, None)], byte_lengths=False)

    assert _column(target, "bytes") is None
    # `chars` is not optional and cannot be: a total and a listing are answered
    # from it without the content column being opened at all, so a file without
    # it would read every document to list a level.
    assert _column(target, "chars") == [len(WIDE_DOC)]


def test_a_file_without_the_column_reads_exactly_like_one_with_it(tmp_path):
    """The stamp does not move for this column, so both are ordinary stores.

    A reader keys on the column being there rather than on the format version,
    which it has to anyway -- the pack option means two files carry the same
    version and differ in columns -- and which is what keeps every file written
    before this readable rather than refused.
    """
    documents = [(key, content, None, "2026-01-01T00:00:00+00:00") for key, content in CORPUS]
    ParquetStore.build(tmp_path / "with.parquet", documents)
    ParquetStore.build(tmp_path / "without.parquet", documents, byte_lengths=False)

    with (
        ParquetStore(tmp_path, filename="with.parquet") as rich,
        ParquetStore(tmp_path, filename="without.parquet") as plain,
    ):
        assert rich.stored_format_version == plain.stored_format_version == FORMAT_VERSION
        for call in (
            lambda s: s.list_keys("a"),
            lambda s: s.get_documents(BoundedSubtree("a")),
            lambda s: s.retrieve_document("a"),
            lambda s: s.retrieve_document("a", byte_offset=1),
        ):
            assert call(rich) == call(plain)


def test_the_byte_column_is_written_but_not_held_in_memory(tmp_path):
    """Written for a reader of the file, not for a read of the store.

    The same answer ``doc_key`` and ``parent`` get: a column a reader can
    recompute is still a column a query engine should not have to, and holding
    one nothing here reads would be bytes per row of an open store for nothing.
    """
    assert "bytes" in INDEX_COLUMNS
    assert "bytes" not in HELD_COLUMNS
