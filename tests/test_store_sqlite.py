"""The SQLite backend: the file, its schema, and how the schema moves forward.

What :mod:`outrage.store_sqlite` is answerable for on its own, as opposed to what
any store has to do. ``test_store.py`` holds the second, and exercises it
through this backend because it is the only one there is; here are the tests
that would have nothing to say about a store kept some other way.

Three groups: that opening a store makes the file, that a store written by an
older build is migrated to the current schema rather than misread, and that a
connection belongs to the thread that opened it.

The migrations are the reason this file is worth having separately. Each one
builds a database the way the *old* build wrote it -- not out of the current
schema, which would be testing the migration against a store that never
existed -- and then opens it through :class:`~outrage.store_sqlite.SqliteStore`
and asks what came out.
"""

import sqlite3
import threading
from pathlib import Path

import pytest

from conftest import in_threads
from outrage import keys, maintenance
from outrage import store as store_module
from outrage import store_sqlite as sqlite_module
from outrage.store import BoundedSubtree
from outrage.store_sqlite import SqliteStore


@pytest.fixture
def store(tmp_path):
    with SqliteStore(tmp_path / "store") as s:
        yield s


# -- the file ------------------------------------------------------------


def test_creates_directory_and_database(tmp_path):
    directory = tmp_path / "nested" / ".outrage"
    with SqliteStore(directory) as s:
        assert s.path == directory / "store.sqlite"
    assert (directory / "store.sqlite").exists()


def test_rejects_a_newer_schema(tmp_path):
    with SqliteStore(tmp_path) as s:
        s._conn.execute("PRAGMA user_version=999")
        s._conn.commit()
    with pytest.raises(RuntimeError, match="newer version"):
        SqliteStore(tmp_path)


# -- migrations ----------------------------------------------------------


#: The table as it stood before ``sort_key`` was added. Spelled out rather than
#: taken from ``store._SCHEMA``, which is the *current* schema: building an old
#: store out of the new definition tests the migration against a database that
#: never existed.
_SCHEMA_BEFORE_SORT_KEY = """
CREATE TABLE documents (
  key        TEXT PRIMARY KEY,
  doc_key    TEXT NOT NULL,
  meta_name  TEXT,
  parent     TEXT NOT NULL,
  content    TEXT NOT NULL,
  format     TEXT,
  updated_at TEXT NOT NULL
);
"""


def an_old_store(directory: Path, version: int, rows: list[tuple]) -> None:
    """A store at ``version``, written the way that version wrote them."""
    directory.mkdir(exist_ok=True)
    conn = sqlite3.connect(directory / "store.sqlite")
    conn.executescript(_SCHEMA_BEFORE_SORT_KEY)
    conn.executemany(
        "INSERT INTO documents (key, doc_key, meta_name, parent, content, format, updated_at)"
        " VALUES (?, ?, ?, ?, ?, 'markdown', 'then')",
        rows,
    )
    conn.execute(f"PRAGMA user_version={version}")
    conn.commit()
    conn.close()


def test_migrates_period_delimited_keys_to_slashes(tmp_path):
    """A schema 1 store was written before the delimiter changed."""
    directory = tmp_path / ".outrage"
    directory.mkdir()
    conn = sqlite3.connect(directory / "store.sqlite")
    conn.executescript(_SCHEMA_BEFORE_SORT_KEY)
    conn.executemany(
        "INSERT INTO documents (key, doc_key, meta_name, parent, content, format, updated_at)"
        " VALUES (?, ?, ?, ?, ?, 'markdown', 'then')",
        [
            ("context.a1b2.design", "context.a1b2.design", None, "context.a1b2", "Body."),
            (
                "context.a1b2.design:title",
                "context.a1b2.design",
                "title",
                "context.a1b2.design",
                "Store schema",
            ),
        ],
    )
    conn.execute("PRAGMA user_version=1")
    conn.commit()
    conn.close()

    with SqliteStore(directory) as s:
        assert s._conn.execute("PRAGMA user_version").fetchone()[0] == sqlite_module.SCHEMA_VERSION
        assert s.retrieve_document("context/a1b2/design").content == "Body."
        assert [e.key for e in s.list_keys("context/a1b2").items] == ["context/a1b2/design"]
        survey = s.get_documents(BoundedSubtree("context"), meta_name="title")
        assert [e.key for e in survey.items] == ["context/a1b2/design/!title"]


def test_migrates_a_store_that_predates_the_sort_key(tmp_path):
    directory = tmp_path / ".outrage"
    an_old_store(
        directory,
        version=2,
        rows=[
            ("notes/10", "notes/10", None, "notes", "tenth"),
            ("notes/2", "notes/2", None, "notes", "second"),
            ("notes/03", "notes/03", None, "notes", "third, written padded"),
        ],
    )

    with SqliteStore(directory) as s:
        assert s._conn.execute("PRAGMA user_version").fetchone()[0] == sqlite_module.SCHEMA_VERSION
        # notes/03 was rewritten, not just indexed: the key it names has changed.
        found = s.get_documents(BoundedSubtree("notes")).items
        assert [e.key for e in found] == ["notes/2", "notes/3", "notes/10"]
        assert s.retrieve_document("notes/3").content == "third, written padded"


def test_a_store_holding_both_spellings_is_refused_rather_than_merged(tmp_path):
    directory = tmp_path / ".outrage"
    an_old_store(
        directory,
        version=2,
        rows=[
            ("notes/1", "notes/1", None, "notes", "one spelling"),
            ("notes/01", "notes/01", None, "notes", "the other"),
        ],
    )

    # Nothing can tell which of the two was meant, so neither is thrown away.
    with pytest.raises(RuntimeError, match="one key once leading zeros"):
        SqliteStore(directory)


def test_a_migrated_store_has_exactly_the_schema_a_fresh_one_has(tmp_path):
    """Otherwise an older build writes rows a newer one cannot order.

    `ALTER TABLE ADD COLUMN` needs a default for a NOT NULL column, and that
    default outlives the migration: a server still running the previous build
    would insert an empty sort key without complaint, and those rows sort ahead
    of everything. Observed, not hypothetical.
    """
    migrated = tmp_path / "migrated"
    an_old_store(migrated, version=2, rows=[("notes/1", "notes/1", None, "notes", "body")])
    with SqliteStore(migrated):
        pass

    with SqliteStore(tmp_path / "fresh") as s:
        s.store_document("notes/1", "body")

    def shape(directory):
        conn = sqlite3.connect(directory / "store.sqlite")
        # name, type, notnull and default per column, plus the indexes. Not the
        # DDL text: ALTER TABLE RENAME quotes the table name, which differs
        # without meaning anything, while the column default -- the thing that
        # was actually wrong -- does not show up in a casual reading of it.
        columns = [tuple(row[1:5]) for row in conn.execute("PRAGMA table_info(documents)")]
        indexes = sorted(row[1] for row in conn.execute("PRAGMA index_list(documents)"))
        return columns, indexes

    assert shape(migrated) == shape(tmp_path / "fresh")

    columns, _ = shape(migrated)
    sort_key = [column for column in columns if column[0] == "sort_key"]
    assert sort_key == [("sort_key", "TEXT", 1, None)], "sort_key must be NOT NULL with no default"


def test_the_migration_fills_in_a_sort_key_for_every_row(tmp_path):
    directory = tmp_path / ".outrage"
    an_old_store(
        directory,
        version=2,
        rows=[
            ("notes/1", "notes/1", None, "notes", "body"),
            ("notes/1/!title", "notes/1", "title", "notes/1", "A title"),
        ],
    )

    with SqliteStore(directory) as s:
        empty = s._conn.execute("SELECT count(*) FROM documents WHERE sort_key = ''").fetchone()[0]
        assert empty == 0


def test_schema_3_metadata_keys_migrate_to_a_segment(tmp_path):
    # A schema 3 store, written before metadata became a segment.
    path = tmp_path / "store.sqlite"
    con = sqlite3.connect(path)
    con.executescript(sqlite_module._TABLE.format(name="documents") + sqlite_module._INDEXES)
    con.executemany(
        "INSERT INTO documents (key, doc_key, meta_name, parent, content, format, "
        "updated_at, sort_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("a", "a", None, "", "body", "markdown", "2026-01-01T00:00:00+00:00", "a"),
            ("a/b", "a/b", None, "a", "body", "markdown", "2026-01-01T00:00:00+00:00", "a/b"),
            ("a:title", "a", "title", "a", "A", "markdown", "2026-01-01T00:00:00+00:00", "a:title"),
            (
                "a/b:title",
                "a/b",
                "title",
                "a/b",
                "B",
                "markdown",
                "2026-01-01T00:00:00+00:00",
                "a/b:title",
            ),
        ],
    )
    con.execute("PRAGMA user_version=3")
    con.commit()
    con.close()

    opened = SqliteStore(tmp_path)

    # The key moved; what was derived from it did not, because none of those
    # columns ever held the suffix.
    rows = {r["key"]: r for r in opened.connection.execute("SELECT * FROM documents")}
    assert set(rows) == {"a", "a/b", "a/!title", "a/b/!title"}
    assert rows["a/!title"]["doc_key"] == "a"
    assert rows["a/!title"]["meta_name"] == "title"
    assert rows["a/!title"]["parent"] == "a"
    assert rows["a/b/!title"]["content"] == "B"

    # And the sort keys now put a document's metadata ahead of its subtree.
    assert rows["a/!title"]["sort_key"] < rows["a/b"]["sort_key"]
    assert rows["a/!title"]["sort_key"] < rows["a/b/!title"]["sort_key"]

    assert opened.retrieve_document("a/!title").content == "A"
    version = opened.connection.execute("PRAGMA user_version").fetchone()[0]
    assert version == sqlite_module.SCHEMA_VERSION


#: The table as it stood at schema 5, before a metadata name became one
#: segment. Spelled out for the reason ``_SCHEMA_BEFORE_SORT_KEY`` is: building
#: an old store out of the current definition tests the migration against a
#: database that never existed.
_SCHEMA_5 = """
CREATE TABLE documents (
  key        TEXT PRIMARY KEY,
  doc_key    TEXT NOT NULL,
  meta_name  TEXT,
  parent     TEXT NOT NULL,
  content    TEXT NOT NULL,
  format     TEXT,
  updated_at TEXT NOT NULL,
  sort_key   TEXT NOT NULL
);
"""


def test_schema_5_metadata_names_are_re_split_at_the_first_segment(tmp_path):
    # Schema 5 read everything below the first `!` as the name, so `a/!x/y` was
    # metadata called `x/y`. Schema 6 makes the name one segment and puts the
    # rest in `meta_path`. No key moves; the two derived columns are rebuilt.
    def schema_5_meta_name(key):
        head, sep, tail = key.partition("/!")
        return tail if sep else None

    written = ["a", "a/!title", "a/!changelog", "a/!changelog/22", "a/!changelog/22/!title"]
    con = sqlite3.connect(tmp_path / "store.sqlite")
    con.executescript(_SCHEMA_5)
    con.executemany(
        "INSERT INTO documents (key, doc_key, meta_name, parent, content, format, "
        "updated_at, sort_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                keys.parse(k).key,
                keys.parse(k).doc_key,
                schema_5_meta_name(k),
                keys.parse(k).parent,
                "body",
                "markdown",
                "2026-01-01T00:00:00+00:00",
                keys.sort_form(k),
            )
            for k in written
        ],
    )
    con.execute("PRAGMA user_version=5")
    con.commit()
    con.close()

    opened = SqliteStore(tmp_path)

    assert (
        opened.connection.execute("PRAGMA user_version").fetchone()[0]
        == sqlite_module.SCHEMA_VERSION
    )
    split = {
        row[0]: (row[1], row[2])
        for row in opened.connection.execute("SELECT key, meta_name, meta_path FROM documents")
    }
    assert split == {
        "a": (None, None),
        "a/!title": ("title", None),
        "a/!changelog": ("changelog", None),
        "a/!changelog/22": ("changelog", "22"),
        "a/!changelog/22/!title": ("changelog", "22/!title"),
    }
    # And the store now answers about the namespace, which is what the columns
    # are for: the note is a document inside the changelog, not a name on `a`.
    assert [e.key for e in opened.list_keys("a/!changelog").items] == ["a/!changelog/22"]
    survey = opened.get_documents(BoundedSubtree("a/!changelog"), meta_name="title")
    assert [e.key for e in survey.items] == ["a/!changelog/22/!title"]


def test_a_store_migrated_to_schema_6_has_the_schema_a_fresh_one_has(tmp_path):
    # The reason `_migrate_meta_namespace` rebuilds rather than ALTERs: a file
    # carrying a column a fresh store does not is one an older build writes a
    # wrong `meta_name` into without complaint.
    con = sqlite3.connect(tmp_path / "store.sqlite")
    con.executescript(_SCHEMA_5)
    con.execute("PRAGMA user_version=5")
    con.commit()
    con.close()
    with SqliteStore(tmp_path):
        pass

    with SqliteStore(tmp_path / "fresh") as s:
        s.store_document("a", "body")

    def shape(directory):
        conn = sqlite3.connect(directory / "store.sqlite")
        columns = [tuple(row[1:5]) for row in conn.execute("PRAGMA table_info(documents)")]
        indexes = sorted(row[1] for row in conn.execute("PRAGMA index_list(documents)"))
        return columns, indexes

    assert shape(tmp_path) == shape(tmp_path / "fresh")


def test_schema_4_sort_keys_are_rebuilt_for_the_marked_sort_form(tmp_path):
    # Schema 4 joined the sort form with `/` and leaned on `!` sorting below
    # every character a segment could begin with. Schema 5 marks every segment
    # and joins below every legal segment character instead. Only `sort_key`
    # changes: the keys themselves are already right.
    def schema_4_sort_form(key):
        def pad(segment):
            if segment.startswith("!"):
                return "!" + pad(segment[1:])
            return segment.zfill(16) if segment.isdigit() else segment

        return "/".join(pad(part) for part in key.split("/"))

    written = ["a", "a-x", "a/b", "a/2", "a/10", "a/!title", "a-x/!title"]
    con = sqlite3.connect(tmp_path / "store.sqlite")
    con.executescript(sqlite_module._TABLE.format(name="documents") + sqlite_module._INDEXES)
    con.executemany(
        "INSERT INTO documents (key, doc_key, meta_name, parent, content, format, "
        "updated_at, sort_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                keys.parse(k).key,
                keys.parse(k).doc_key,
                keys.parse(k).meta_name,
                keys.parse(k).parent,
                "body",
                "markdown",
                "2026-01-01T00:00:00+00:00",
                schema_4_sort_form(k),
            )
            for k in written
        ],
    )
    con.execute("PRAGMA user_version=4")
    con.commit()
    con.close()

    opened = SqliteStore(tmp_path)

    assert (
        opened.connection.execute("PRAGMA user_version").fetchone()[0]
        == sqlite_module.SCHEMA_VERSION
    )
    rows = dict(opened.connection.execute("SELECT key, sort_key FROM documents"))
    assert set(rows) == set(written)
    for key, sort_key in rows.items():
        assert sort_key == keys.sort_form(key), key

    # The inversion schema 4 recorded as unfixed, gone: `a` sorts before `a-x`
    # as documents, and now so does their metadata.
    assert rows["a"] < rows["a-x"]
    assert rows["a/!title"] < rows["a-x/!title"]
    opened.connection.close()


# -- connections ---------------------------------------------------------


def test_a_connection_does_not_escape_its_thread(store):
    """Each thread gets its own, so the objects differ and nothing is shared."""
    seen = {}
    lock = threading.Lock()

    def note(i):
        store.list_keys()  # opens this thread's connection
        with lock:
            seen[i] = id(store._conn)

    in_threads(note, threads=4)

    assert len(set(seen.values())) == 4


# -- the backend behind the interface -------------------------------------


def test_the_sqlite_store_implements_the_whole_interface():
    """Nothing abstract is left, which is what lets it be instantiated at all."""
    assert issubclass(SqliteStore, store_module.Store)
    assert SqliteStore.__abstractmethods__ == frozenset()


def test_default_store_is_the_one_place_a_backend_is_chosen(tmp_path):
    """The seam a second backend arrives at.

    Every caller in the package -- the server, the command line, the mount
    table -- goes through here rather than naming a class, so this is the
    assertion that would have to be updated to change what a store is.
    """
    s = store_module.default_store(tmp_path)
    try:
        assert isinstance(s, SqliteStore)
    finally:
        s.close()

    with store_module.open_store(tmp_path) as opened:
        assert isinstance(opened, SqliteStore)


def test_the_connection_is_the_backend_s_own(store):
    """``connection`` is on the backend, not on the interface.

    ``check_file`` uses it to ask SQLite about the file itself. That question
    has no meaning for a store kept some other way, which is why the answering
    is on the backend and only the *asking* is on
    :class:`outrage.store.Store` -- and why the attribute itself must not appear
    there.
    """
    assert isinstance(store.connection, sqlite3.Connection)
    assert not hasattr(store_module.Store, "connection")


# -- the length cache ----------------------------------------------------
#
# A cache and not a column, so what these have to establish is not that a
# number is right -- counting is always available and always correct -- but
# that a *stale* number can never be read. That is the one failure mode a
# separate table has and a column does not, and the triggers are the answer.


#: Comfortably past `LENGTH_THRESHOLD`, so the cache takes an interest in it.
LONG = "x" * (sqlite_module.LENGTH_THRESHOLD + 100)

#: Comfortably below it, so the cache does not.
SHORT = "y" * 10


def _cached(store):
    """What the cache holds, as a plain dict, read behind the store's back."""
    return dict(store._conn.execute(f"SELECT key, chars FROM {sqlite_module.LENGTH_CACHE_TABLE}"))


def test_only_documents_worth_caching_are_cached(store):
    store.store_document("long", LONG)
    store.store_document("short", SHORT)

    # The threshold's whole purpose: an entry for the document whose length
    # costs something to find, and none for the one whose does not.
    assert _cached(store) == {"long": len(LONG)}


def test_the_cache_does_not_move_the_schema_version(store):
    """The reason it is a cache rather than a column, asserted.

    A schema bump makes an older build refuse the store outright. Nothing here
    needs that: a build that has never heard of this table reads the store
    correctly and merely counts, and one that writes to it still fires the
    triggers, because they live in the file rather than in any build.
    """
    store.store_document("long", LONG)
    assert store.format_version == sqlite_module.SCHEMA_VERSION == 6


def test_a_shortened_document_loses_its_cached_length(store):
    store.store_document("k", LONG)
    assert _cached(store) == {"k": len(LONG)}

    store.store_document("k", SHORT)

    # Not merely updated to the new length: it drops below the threshold, so
    # the right answer is no entry at all. An entry that stayed would be a
    # cached length for a document that no longer has it.
    assert _cached(store) == {}
    assert store.list_keys().items[0].size == len(SHORT)


def test_a_deleted_document_takes_its_cached_length_with_it(store):
    store.store_document("k", LONG)
    store.delete("k")

    # Or the next document to be given this key would inherit a length that
    # was never its own.
    assert _cached(store) == {}


def test_a_writer_that_knows_nothing_of_the_cache_invalidates_it(store):
    """The property a column could not have, and the reason for the triggers.

    A build of outrage older than this table -- or any other writer at all --
    updates ``documents`` and knows nothing to update beside it. The triggers
    are in the file, so they fire anyway, and the stale entry is gone rather
    than being read as the truth.
    """
    store.store_document("k", LONG)
    replacement = "z" * (sqlite_module.LENGTH_THRESHOLD * 2)

    store._conn.execute("UPDATE documents SET content = ? WHERE key = ?", (replacement, "k"))
    store._conn.commit()

    assert _cached(store) == {}
    assert store.list_keys().items[0].size == len(replacement)
    assert store.list_keys().total_chars == len(replacement)


def test_a_migration_that_rewrites_keys_does_not_strand_an_entry(store):
    """The update trigger names both keys, and this is why.

    A key is never rewritten by a write, but migrations have rewritten every
    key in the store twice. A cache entry left under the old name would then
    describe a document that is no longer there.
    """
    store.store_document("before", LONG)
    store._conn.execute(
        "UPDATE documents SET key = ?, sort_key = ? WHERE key = ?",
        ("after", keys.sort_form("after"), "before"),
    )
    store._conn.commit()

    assert _cached(store) == {}


def test_totals_are_the_same_whether_or_not_the_cache_has_the_answer(store):
    """The cache is an optimisation, so emptying it must change no answer."""
    for name, content in (("a/one", LONG), ("a/two", SHORT), ("a/three", LONG * 2)):
        store.store_document(name, content)

    def totals():
        return (
            store.list_keys("a").total_chars,
            store.get_documents(BoundedSubtree("a")).total_chars,
        )

    with_cache = totals()
    _empty_the_cache(store)
    without_cache = totals()

    assert with_cache == without_cache == (len(LONG) + len(SHORT) + len(LONG) * 2,) * 2


def test_an_existing_store_is_backfilled_when_the_cache_first_appears(tmp_path):
    """A document written before the table existed still gets an entry.

    Without this the cache would only ever cover documents written after the
    build that introduced it, and a long document already in the store would
    pay for a count on every read of it, forever, with nothing to change that
    but rewriting it.
    """
    with SqliteStore(tmp_path / "store") as s:
        s.store_document("old", LONG)
        s._conn.executescript(
            f"DROP TRIGGER {sqlite_module.LENGTH_CACHE_TABLE}_insert;"
            f"DROP TRIGGER {sqlite_module.LENGTH_CACHE_TABLE}_update;"
            f"DROP TRIGGER {sqlite_module.LENGTH_CACHE_TABLE}_delete;"
            f"DROP TABLE {sqlite_module.LENGTH_CACHE_TABLE};"
        )

    with SqliteStore(tmp_path / "store") as reopened:
        assert _cached(reopened) == {"old": len(LONG)}


def test_the_backfill_runs_once_and_not_on_every_open(tmp_path):
    """Or every open of a large store would scan all of it to say nothing.

    Asserted by leaving the table deliberately incomplete: a second open that
    backfilled again would fill the gap in, and the point is that it does not
    look.
    """
    with SqliteStore(tmp_path / "store") as s:
        s.store_document("k", LONG)
        s._conn.execute(f"DELETE FROM {sqlite_module.LENGTH_CACHE_TABLE}")
        s._conn.commit()

    with SqliteStore(tmp_path / "store") as reopened:
        assert _cached(reopened) == {}
        # And the answer is still right, which is what makes that safe.
        assert reopened.list_keys().items[0].size == len(LONG)


def test_a_byte_read_reports_the_character_total_from_the_cache(store):
    """The one thing the stored length is on the critical path for.

    Before it, a byte-addressed read reported ``total`` as None and the front
    ends printed the byte total instead, because counting characters means
    reading the whole document -- which is the cost the byte offset exists to
    avoid.
    """
    store.store_document("long", LONG)
    store.store_document("short", SHORT)

    assert store.retrieve_document("long", byte_offset=0).total == len(LONG)
    # And a document with no entry is counted, which is affordable precisely
    # because not having an entry is what being short means.
    assert store.retrieve_document("short", byte_offset=0).total == len(SHORT)


def test_a_byte_read_of_a_long_document_is_right_without_an_entry(store):
    """Correct first, fast second: an empty cache costs time and not accuracy."""
    store.store_document("long", LONG)
    _empty_the_cache(store)

    assert store.retrieve_document("long", byte_offset=0).total == len(LONG)


# -- a read that fills the cache -----------------------------------------
#
# John's call, 2026-09-05: a cache should be invisible to the user, so a write
# on a read path is not the surprise it would be if it changed a document. A
# document is only ever found uncached because a writer older than the cache
# emptied the entry, and the read has already paid for the length by then.


def _empty_the_cache(store):
    store._conn.execute(f"DELETE FROM {sqlite_module.LENGTH_CACHE_TABLE}")
    store._conn.commit()


def test_a_byte_read_writes_down_the_length_it_had_to_count(store):
    store.store_document("long", LONG)
    _empty_the_cache(store)

    store.retrieve_document("long", byte_offset=0)

    # Or every byte read of this document would keep paying for the count that
    # the offset was chosen to avoid, with nothing to change that but a write.
    assert _cached(store) == {"long": len(LONG)}


def test_a_character_read_writes_it_down_too(store):
    """The same fact, arrived at more cheaply rather than differently.

    A character read holds the whole document, so the length is in hand and
    writing it down costs a row rather than a count. Drawing the line at the
    byte path would have left the commonest read of all not filling a cache it
    could fill for nothing.
    """
    store.store_document("long", LONG)
    _empty_the_cache(store)

    store.retrieve_document("long")

    assert _cached(store) == {"long": len(LONG)}


def test_a_read_of_a_short_document_writes_nothing(store):
    store.store_document("short", SHORT)

    store.retrieve_document("short")
    store.retrieve_document("short", byte_offset=0)

    assert _cached(store) == {}


def test_a_read_does_not_rewrite_an_entry_that_is_already_there(store):
    """A hit is a hit: the read trusts the cache and does not check it.

    Asserted through a deliberately wrong entry, which survives. Verifying it
    on every read would mean counting on every read, which is the whole cost
    being avoided -- checking that entries agree with their documents is
    ``check``'s job and it is the expensive path on purpose.
    """
    store.store_document("long", LONG)
    store._conn.execute(f"UPDATE {sqlite_module.LENGTH_CACHE_TABLE} SET chars = 7")
    store._conn.commit()

    store.retrieve_document("long")
    store.retrieve_document("long", byte_offset=0)

    assert _cached(store) == {"long": 7}


def test_a_bulk_read_does_not_fill_the_cache(store):
    """The line between a note taken in passing and a scan nobody asked for.

    Reading one document establishes one length. A subtree read establishes a
    sum, and filling the cache from it would be the backfill again, run on
    somebody's read of a corpus rather than once when the table was made.
    """
    store.store_document("a/long", LONG)
    _empty_the_cache(store)

    assert store.get_documents(BoundedSubtree("a")).total_chars == len(LONG)
    assert _cached(store) == {}


def test_a_read_still_answers_when_the_cache_cannot_be_written(store):
    """Invisible in both directions.

    A store another writer holds locked would otherwise turn a read that had
    already succeeded into an error, over a note nobody asked to be taken.
    ``query_only`` stands in for the lock: it refuses writes and answers reads,
    which is the shape of every way this can fail.

    Note what is *not* being claimed. The cache table itself is load-bearing
    once it exists -- every read names it -- so a store somebody has dropped it
    from is a broken store, exactly as it would be for any other table. What is
    tolerated is a write that cannot land, not a table that is not there.
    """
    store.store_document("long", LONG)
    _empty_the_cache(store)
    store._conn.execute("PRAGMA query_only=ON")
    try:
        assert store.retrieve_document("long").content == LONG
        assert store.retrieve_document("long", byte_offset=0).total == len(LONG)
    finally:
        store._conn.execute("PRAGMA query_only=OFF")

    assert _cached(store) == {}


def test_listing_a_level_does_not_select_the_documents_it_lists(store):
    """A listing reports a size, and used to read every document to get one.

    ``SELECT *`` pulled each listed document's whole text into Python so that
    ``len()`` could be taken of it. The size now comes from the cache, or from
    ``length()`` evaluated inside SQLite, and neither moves the text.
    """
    store.store_document("a/one", LONG)
    statements = []
    store._conn.set_trace_callback(statements.append)
    try:
        listing = store.list_keys("a")
    finally:
        store._conn.set_trace_callback(None)

    assert [entry.size for entry in listing.items] == [len(LONG)]
    assert not [sql for sql in statements if "SELECT *" in sql]


def test_check_reports_a_cached_length_that_no_longer_describes_its_document(store):
    """It should not be reachable, which is exactly what a check is for."""
    store.store_document("k", LONG)
    store._conn.execute(f"UPDATE {sqlite_module.LENGTH_CACHE_TABLE} SET chars = 1")
    store._conn.commit()

    report = maintenance.check(store)
    assert [p.summary for p in report.problems if "cached document lengths" in p.summary]

    done = maintenance.repair(store)
    dropped = [step for step in done if "cached lengths" in step.action]

    # Counted in what it actually moved. Every repair before this one moved
    # bytes about inside the file, so the report said "bytes" and meant it;
    # this one drops rows, and "1 -> 0 bytes" is a sentence that reads
    # correctly and is false. Found by running a repair and reading it.
    assert [(step.before, step.after, step.unit) for step in dropped] == [(1, 0, "entries")]
    assert _cached(store) == {}
    assert not [
        p for p in maintenance.check(store).problems if "cached document lengths" in p.summary
    ]
