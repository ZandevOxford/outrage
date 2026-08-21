"""The SQLite backend: the file, its schema, and how the schema moves forward.

What :mod:`rage.store_sqlite` is answerable for on its own, as opposed to what
any store has to do. ``test_store.py`` holds the second, and exercises it
through this backend because it is the only one there is; here are the tests
that would have nothing to say about a store kept some other way.

Three groups: that opening a store makes the file, that a store written by an
older build is migrated to the current schema rather than misread, and that a
connection belongs to the thread that opened it.

The migrations are the reason this file is worth having separately. Each one
builds a database the way the *old* build wrote it -- not out of the current
schema, which would be testing the migration against a store that never
existed -- and then opens it through :class:`~rage.store_sqlite.SqliteStore`
and asks what came out.
"""

import sqlite3
import threading
from pathlib import Path

import pytest
from conftest import in_threads

from rage import keys
from rage import store as store_module
from rage import store_sqlite as sqlite_module
from rage.store import BoundedSubtree
from rage.store_sqlite import SqliteStore


@pytest.fixture
def store(tmp_path):
    with SqliteStore(tmp_path / "store") as s:
        yield s


# -- the file ------------------------------------------------------------


def test_creates_directory_and_database(tmp_path):
    directory = tmp_path / "nested" / ".rage"
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
    directory = tmp_path / ".rage"
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
    directory = tmp_path / ".rage"
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
    directory = tmp_path / ".rage"
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
    directory = tmp_path / ".rage"
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
            ("a/b:title", "a/b", "title", "a/b", "B", "markdown",
             "2026-01-01T00:00:00+00:00", "a/b:title"),
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

    assert opened.connection.execute("PRAGMA user_version").fetchone()[0] == 5
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

    :mod:`rage.maintenance` reaches through it to ask SQLite about the file
    itself. That question has no meaning for a store kept some other way, so
    the attribute must not appear on :class:`rage.store.Store`.
    """
    assert isinstance(store.connection, sqlite3.Connection)
    assert not hasattr(store_module.Store, "connection")
