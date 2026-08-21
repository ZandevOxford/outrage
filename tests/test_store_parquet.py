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
from conftest import in_threads, raises_rendered

from rage import bulk, keys
from rage import store as store_module
from rage.store import (
    EVERYTHING,
    UNBOUNDED,
    BackendError,
    BackupError,
    BoundedSubtree,
    KeyNotFoundError,
    KeyRange,
    ReadOnlyStoreError,
)
from rage.store_parquet import ParquetStore
from rage.store_sqlite import SqliteStore

pytest.importorskip("pyarrow", reason="the parquet backend is an optional extra")


#: A corpus chosen for the places the two backends could disagree rather than
#: for size: numeric segments that sort wrong as text, a key whose sibling
#: (``a-x``) sorts between it and its own children under a naive ordering, a
#: document at the root, metadata on the root, JSON beside markdown, and a
#: document with children so that a container read has something to be about.
CORPUS = [
    ("", "root document"),
    ("!title", "The store itself"),
    ("a", "a body"),
    ("a/!title", "A"),
    ("a/!summary", "sum of a"),
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
    ("z", "last"),
]


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
_KEYS = ["", "a", "a/b", "a/10", "context", "context/10", "notes", "z", "a-x", "nope", "a/b/c"]

#: One of each bound :class:`~rage.store.KeyRange` can carry, then the pairs
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
]

_METAS = [None, "title", ["title"], ["title", "summary"], ["summary"]]


def _same(sqlite, parquet, call):
    """Put ``call`` to both stores and require the same answer, exception or not.

    Exceptions are compared as a rendered type and code rather than re-raised,
    because "SQLite raises and parquet returns an empty page" is exactly the
    kind of disagreement this is looking for, and a test that let the first one
    propagate would report it as a failure of the oracle.
    """

    def answer(store):
        try:
            return call(store)
        except Exception as exc:  # noqa: BLE001 - the answer, when it is one
            return type(exc).__name__, getattr(exc, "code", str(exc))

    left, right = answer(sqlite), answer(parquet)
    assert left == right


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
        _same(sqlite, parquet, lambda s, k=key: s.exists(k))
        _same(sqlite, parquet, lambda s, k=key: s.descendant_count(k))
        _same(sqlite, parquet, lambda s, k=key: s.retrieve_document(k))
        if key != keys.ROOT:
            _same(sqlite, parquet, lambda s, k=key: s.level_entry(k))
        for limit in (None, 1, 2, 100):
            _same(sqlite, parquet, lambda s, k=key, n=limit: s.list_keys(k, limit=n))
        # Paged to the end at a page size of two, so a level of three or more
        # crosses a boundary and the totals are asserted on every page.
        _same(sqlite, parquet, lambda s, k=key: _walk_level(s, k))

    for subtree, key_range, meta in itertools.product(_SUBTREES, _RANGES, _METAS):
        _same(
            sqlite,
            parquet,
            lambda s, t=subtree, r=key_range, m=meta: _page(
                s.get_documents(t, key_range=r, meta_name=m)
            ),
        )
        _same(
            sqlite,
            parquet,
            lambda s, t=subtree, r=key_range, m=meta: _walk_documents(s, t, r, m),
        )

    names = ["title", ["title", "x"]]
    for subtree, key_range, meta in itertools.product(_SUBTREES, _RANGES, names):
        _same(
            sqlite,
            parquet,
            lambda s, t=subtree, r=key_range, m=meta: _page(
                s.keys_missing_meta(t, key_range=r, meta_name=m)
            ),
        )
        for window in _RANGES:
            _same(
                sqlite,
                parquet,
                lambda s, t=subtree, r=key_range, m=meta, w=window: s.missing_meta_stats(
                    t, key_range=r, window=w, meta_name=m, sample=3
                ),
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
        _same(
            sqlite,
            parquet,
            lambda s, c=max_chars, t=max_total, n=limit: _walk_documents(
                s, EVERYTHING, UNBOUNDED, None, max_chars=c, max_total_chars=t, limit=n
            ),
        )


def test_the_two_backends_slice_a_document_identically(sqlite, parquet):
    """Offsets, lengths, patterns and occurrences, over the same three documents.

    :func:`rage.store._excerpt` is shared, so this is really asking whether the
    parquet backend hands it the same four fields SQLite does -- and whether a
    pattern that does not occur fails the same way.
    """
    for key in ("a", "a/b/c", "b"):
        for offset, length, pattern, occurrence, max_chars in itertools.product(
            [0, 1, 5], [None, 0, 2], [None, "a", "zz"], [0, 1], [1, 8000]
        ):
            _same(
                sqlite,
                parquet,
                lambda s, k=key, o=offset, ln=length, p=pattern, c=occurrence, m=max_chars: (
                    s.retrieve_document(
                        k, offset=o, length=ln, pattern=p, occurrence=c, max_chars=m
                    )
                ),
            )


def _page(page):
    """A page as the facts worth comparing, rather than as an object."""
    return (
        [
            item if isinstance(item, str) else (item.key, item.content, item.format)
            for item in page.items
        ],
        page.returned,
        page.total,
        page.total_chars,
        page.next_cursor,
    )


def _walk_level(store, key):
    """A whole level, two keys at a time, with each page's totals."""
    seen, totals, cursor = [], [], None
    while True:
        page = store.list_keys(key, limit=2, cursor=cursor)
        seen += [(e.key, e.kind, e.size, e.format) for e in page.items]
        totals.append((page.total, page.total_chars))
        if page.next_cursor is None:
            return seen, totals
        cursor = page.next_cursor


def _walk_documents(store, subtree, key_range, meta, **caps):
    """A whole selection, paged to the end, with each page's totals.

    Bounded at two hundred pages, so a backend whose cursor fails to advance is
    a failure rather than a test run that never finishes -- which is the shape
    the ``max_total_chars`` guard in both backends exists to prevent.
    """
    caps.setdefault("limit", 2)
    seen, totals, cursor = [], [], None
    for _ in range(200):
        page = store.get_documents(
            subtree, key_range=key_range, meta_name=meta, cursor=cursor, **caps
        )
        seen += [(e.key, e.content, e.returned, e.total) for e in page.items]
        totals.append((page.total, page.total_chars))
        if page.next_cursor is None:
            return seen, totals
        cursor = page.next_cursor
    raise AssertionError("the cursor did not reach the end of the selection")


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


def test_a_refused_write_is_recorded_in_the_event_log(tmp_path):
    """What the log is for is what a store was *asked* to do.

    A refused write is one of the more interesting things anyone asks, and a
    backend that skipped the decorator would leave the log silent about it
    while SQLite recorded every write it took.
    """
    import json

    from rage.eventlog import EventLog

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

    with raises_rendered(BackendError, "not a rage store"):
        ParquetStore(tmp_path, filename="other.parquet")


def test_a_file_from_a_later_build_is_refused_rather_than_read(tmp_path, monkeypatch):
    """Nothing is migrated in place here, so the only answer is to repack.

    The version is checked when the store is opened rather than on the first
    read, so a mount table naming an unreadable file fails while somebody is
    still looking at the command that named it.
    """
    from rage import store_parquet

    monkeypatch.setattr(store_parquet, "FORMAT_VERSION", store_parquet.FORMAT_VERSION + 1)
    ParquetStore.build(tmp_path / "future.parquet", [("a", "body", None, None)])
    monkeypatch.undo()

    with raises_rendered(BackendError, "repack it or upgrade rage") as raised:
        ParquetStore(tmp_path, filename="future.parquet")
    assert raised.value.code == "parquet-format-newer"


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
    from rage import store_parquet

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


def test_default_store_opens_a_parquet_file_without_naming_a_backend(tmp_path):
    """Which is what lets a mount spec say `ref=python.parquet` and mean it."""
    ParquetStore.build(tmp_path / "ref.parquet", [("a", "body", None, None)])
    with store_module.open_store(tmp_path, filename="ref.parquet") as store:
        assert isinstance(store, ParquetStore)
        assert store.retrieve_document("a").content == "body"


def test_every_backend_states_whether_it_can_be_written():
    """Read from the source, because the failure it guards is a backend that
    forgets to say -- which inherits ``True`` and reports itself writable."""
    stated = 0
    for path in sorted(pathlib.Path(store_module.__file__).parent.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.ClassDef):
                continue
            if not any(isinstance(b, ast.Name) and b.id == "Store" for b in node.bases):
                continue
            stated += 1
            assert any(
                isinstance(item, ast.Assign)
                and any(getattr(t, "id", None) == "writable" for t in item.targets)
                for item in node.body
            ), f"{path.name}: {node.name} does not say whether it is writable"
    assert stated >= 2, "both backends should have been found"


# -- packing -------------------------------------------------------------


def test_packing_a_store_carries_metadata_and_timestamps_across(sqlite, tmp_path):
    """A compaction rather than a copy that quietly restamps the corpus.

    Metadata especially: a survey by title is worth nothing if the pack it came
    from left every title behind, which is the same argument the export makes.
    """
    target = tmp_path / "packed.parquet"
    transfers = list(bulk.pack(target, bulk.documents_from_store(sqlite)))
    assert {t.action for t in transfers} == {bulk.READ}
    assert len(transfers) == len(CORPUS)

    with ParquetStore(tmp_path, filename="packed.parquet") as store:
        for key, content in CORPUS:
            assert store.retrieve_document(key).content == content
            assert store.retrieve_document(key).updated_at == (
                sqlite.retrieve_document(key).updated_at
            )


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
    assert next(transfers).action == bulk.READ
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
    assert actions == {bulk.READ, bulk.SKIPPED, bulk.FAILED}
    assert [row for _, row in reported if row is not None] == [("good", "fine", "markdown", None)]


def test_check_and_repair_refuse_a_backend_they_cannot_ask(tmp_path, packed):
    """They are SQLite subcommands wearing generic names, and now say so.

    ``planned/backends`` recorded this as an open question rather than a
    defect, on the grounds that nobody could reach it with one backend. A
    second backend is what turns it into one, and the refusal is a message
    because a traceback is for a bug in rage rather than for a request rage
    cannot answer.
    """
    from rage import maintenance

    with raises_rendered(maintenance.CheckError, "only SQLite has") as raised:
        maintenance.check(packed)
    assert raised.value.code == "check-wrong-backend"

    with raises_rendered(maintenance.CheckError, "cannot repair"):
        maintenance.repair(packed)


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
    from rage import store_parquet

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
    from rage.mounts import open_mounts

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
