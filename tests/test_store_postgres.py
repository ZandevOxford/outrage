"""The PostgreSQL backend's own half: the connection, the schema, the version.

What a store *does* is ``test_store.py``, asked of every backend that can be
written, this one included. What is here is about the storage rather than
about the namespace: where the tables are put, how the order is declared,
what the three numbers in ``outrage_schema`` mean, and which of them turn a
store into one this build may read and not write -- and, for the operations,
what the contract cannot see: the order under a collation that disagrees
with it, and the server-side slicing of a document longer than one window.

**The whole module carries the ``postgres`` marker**, so ``-m "not
postgres"`` is a full suite run on a machine with no server. Most tests here
take one of the fixtures and skip without ``OUTRAGE_TEST_POSTGRES``; the few
that are pure -- the compatibility rules, the search-path fallback, the
service file -- carry the mark anyway rather than giving the file two rules
about what it needs. The fixtures themselves are in ``conftest.py``, because
``test_store.py`` takes them over when the contract runs against this backend.
"""

from __future__ import annotations

import io
import pathlib
import re
import threading
import time
import types

import pytest
from test_store_sqlite import SPLIT_META_NAMES, assert_the_split_agrees_with_keys_relative

from conftest import answers_alike, in_threads, postgres_dsn, raises_rendered
from outrage import keys, messages, pgservice, store_postgres
from outrage import store as store_module
from outrage.cli import main
from outrage.errors import OutrageError
from outrage.mounts import MountedStore, ReadOnlyMountError, open_mounts
from outrage.store import (
    BackendError,
    InvalidArgumentError,
    ReadOnlyStoreError,
    SchemaVersion,
    StoreFileError,
)
from outrage.store_postgres import (
    MIN_SCHEMA_VERSION,
    SCHEMA_TABLE,
    SCHEMA_VERSION,
    VERSIONS,
    PostgresStore,
    ServiceUnusable,
    _first_schema,
    compatibility,
)
from outrage.store_sqlite import SqliteStore

pytestmark = pytest.mark.postgres


def query(store, statement, parameters=()):
    """One statement against the store's own connection, for asking the server.

    In a plain transaction rather than the store's pipelined one, because
    whether a statement returned rows is only known once a pipeline is
    synchronised, and this asks before fetching.
    """
    conn = store._conn
    with conn.transaction(), conn.cursor() as cursor:
        cursor.execute(statement, parameters)
        return cursor.fetchall() if cursor.description else []


def run(*argv):
    """``outrage`` with its standard output captured, as ``test_cli.py`` runs it."""
    out = io.StringIO()
    status = main(list(argv), out)
    return status, out.getvalue()


# -- opening ---------------------------------------------------------------


def test_a_first_open_creates_the_schema_and_its_tables(postgres_store, postgres_service):
    """The whole of what step 4 is for, in the one case that is not a corner.

    ``options=-csearch_path=<name>`` names a schema that does not exist, the
    open creates it, and the three tables are in it rather than in ``public``.
    """
    _path, _service, schema = postgres_service
    tables = {
        name
        for (name,) in query(
            postgres_store,
            "SELECT tablename FROM pg_tables WHERE schemaname = %s",
            (schema,),
        )
    }
    assert tables == {"documents", "document_archive", SCHEMA_TABLE}
    assert postgres_store.schema == schema


def test_the_store_is_created_at_this_builds_newest_version(postgres_store):
    """Auto-creation is ``create`` at ``F`` and is the same code path.

    The floors come from the version table rather than from the row being
    written by hand, so a version that declared floors and forgot to record
    them would fail here.
    """
    assert postgres_store.stored_format_version == SCHEMA_VERSION
    assert postgres_store.compatibility.stored == VERSIONS[SCHEMA_VERSION]
    assert postgres_store.compatibility.operating == SCHEMA_VERSION
    assert postgres_store.compatibility.writable is True


def test_reopening_finds_the_store_rather_than_making_a_second(tmp_path, postgres_service):
    """A second open is not a second creation, and changes nothing.

    The half that would fail silently: ``CREATE ... IF NOT EXISTS`` succeeds
    on the second run whatever it finds, so the thing worth asserting is that
    the version row is still one row.
    """
    path, service, _schema = postgres_service
    with PostgresStore(tmp_path / "dir", filename=path, service=service) as first:
        version = first.stored_format_version
    with PostgresStore(tmp_path / "dir", filename=path, service=service) as second:
        assert second.stored_format_version == version
        assert query(second, f"SELECT count(*) FROM {SCHEMA_TABLE}") == [(1,)]


def test_the_version_table_can_hold_only_one_row(postgres_store):
    """A second row would make "the store's version" a question with two answers."""
    psycopg = pytest.importorskip("psycopg")
    with pytest.raises(psycopg.errors.UniqueViolation):
        query(
            postgres_store,
            f"INSERT INTO {SCHEMA_TABLE} (version, read_floor, write_floor) VALUES (2, 2, 2)",
        )


def test_the_session_declares_which_build_it_is(postgres_store):
    """The floors are enforced at the server too, and this is what they read.

    A long-running server connected before a migration finds out on its next
    write rather than going on writing a shape the store no longer has.
    """
    assert query(postgres_store, "SELECT current_setting('outrage.client_version')") == [
        (str(SCHEMA_VERSION),)
    ]


def test_asking_about_a_store_that_is_not_there_does_not_create_one(tmp_path, postgres_service):
    """``report=True`` is what a question about a store opens with.

    Opening a store creates it, which is right for a store and wrong for a
    report about one: ``outrage schema status`` against an empty schema should
    say it is empty and leave it that way. What it must not do is leave a
    usable-looking store behind, so every operation on one refuses.
    """
    path, service, schema = postgres_service
    with PostgresStore(tmp_path / "dir", filename=path, service=service, report=True) as asked:
        assert asked.has_store is False
        assert asked.schema_state().stored is None
        assert asked.schema_state().schema == schema
        with raises_rendered(BackendError, "no outrage store in schema"):
            assert asked.stored_format_version
    with PostgresStore(tmp_path / "dir", filename=path, service=service, report=True) as again:
        assert again.has_store is False, "the question created a store after all"


def test_a_report_records_a_version_it_cannot_use_rather_than_refusing(tmp_path, postgres_service):
    """A store this build cannot open is exactly the store worth a report.

    An ordinary open raises, because there is nothing a caller can do with a
    half-opened store; a report says which version it met and which this build
    knows, which is what somebody deciding whether to upgrade needs.
    """
    path, service, _schema = postgres_service
    with PostgresStore(tmp_path / "dir", filename=path, service=service) as opened:
        query(
            opened,
            f"UPDATE {SCHEMA_TABLE} SET version = %s, read_floor = %s, write_floor = %s",
            (SCHEMA_VERSION + 2, SCHEMA_VERSION + 1, SCHEMA_VERSION + 1),
        )
    with PostgresStore(tmp_path / "dir", filename=path, service=service, report=True) as asked:
        state = asked.schema_state()
        assert state.stored.version == SCHEMA_VERSION + 2
        assert state.operating is None
        assert state.writable is False
        assert state.problem.code == "postgres-schema-too-new"
        # The recorded refusal, raised as the error it stands for: one
        # vocabulary, so a report and a use say the same thing about the same
        # store. `Refusal.as_error` is a plain `OutrageError`, which is what a
        # refusal carried across as a value can honestly be.
        with raises_rendered(OutrageError, "may only be read by a build that knows"):
            assert asked.stored_format_version


def test_creating_over_a_store_is_refused(postgres_store):
    """A create that merged into somebody's documents would be the quiet kind."""
    with raises_rendered(BackendError, "already holds an outrage store"):
        postgres_store.create_schema()


def test_creating_at_a_version_this_build_does_not_know_is_refused(postgres_store):
    """``create --version`` is bounded by ``MIN..F``, not by what parses."""
    with raises_rendered(BackendError, "cannot create a PostgreSQL store at schema version"):
        postgres_store.create_schema(SCHEMA_VERSION + 1)


# -- ordering --------------------------------------------------------------

#: Seven keys whose bytewise order and this machine's database collation share
#: no prefix at all -- the measurement in ``reference/postgres-server``, kept
#: here as the case rather than as a remark.
DISAGREEING_KEYS = ["a_b", "a-b", "a!x", "a/b", "a/B", "A/b", "a/x"]


def test_keys_sort_bytewise_rather_than_by_the_databases_own_collation(postgres_store):
    """The silent one: a locale collation pages wrongly and raises nothing.

    Asserted against Python's own sort, which is what every cursor, range and
    page in this package assumes, and against the database's own collation,
    which is what the order would have been without ``COLLATE "C"``. The
    second half is what makes this a test rather than a tautology: if the test
    database were itself C-locale the two orders would agree and the guard
    would pass on a store that had no collation declared at all. It is spelled
    ``COLLATE "default"``, which is Postgres's own name for whatever the
    database was created with, rather than a locale named here -- a locale
    named here would be one more thing about this machine that the suite
    silently required.
    """
    for key in DISAGREEING_KEYS:
        query(
            postgres_store,
            "INSERT INTO documents "
            "(key, doc_key, meta_name, meta_path, parent, content, format, "
            " updated_at, sort_key) "
            "VALUES (%s, %s, NULL, NULL, '', 'x', 'text', '2026-09-21 00:00:00', %s)",
            (key, key, key),
        )
    ordered = [key for (key,) in query(postgres_store, "SELECT key FROM documents ORDER BY key")]
    assert ordered == sorted(DISAGREEING_KEYS)

    collated = [
        key
        for (key,) in query(
            postgres_store,
            'SELECT key FROM documents ORDER BY key COLLATE "default"',
        )
    ]
    assert collated != ordered, (
        "this database's own collation agrees with bytewise order, so this "
        "test cannot tell a declared collation from a missing one"
    )


def test_every_text_column_declares_the_collation(postgres_store, postgres_service):
    """One rule over the table, rather than six judgements about which
    comparisons are safe.

    Read from the catalogue rather than from the DDL string, so that a column
    added later without a collation is found here and not by a page that
    quietly skips a key.
    """
    _path, _service, schema = postgres_service
    for table in ("documents", "document_archive"):
        rows = query(
            postgres_store,
            "SELECT a.attname, c.collname "
            "FROM pg_attribute a "
            "JOIN pg_class t ON t.oid = a.attrelid "
            "JOIN pg_namespace n ON n.oid = t.relnamespace "
            "LEFT JOIN pg_collation c ON c.oid = a.attcollation "
            "WHERE n.nspname = %s AND t.relname = %s AND a.attnum > 0 "
            "  AND NOT a.attisdropped AND a.attcollation <> 0",
            (schema, table),
        )
        assert rows, f"{table} has no text columns at all, which cannot be right"
        assert {collation for _name, collation in rows} == {"C"}, (
            f"{table}: {[name for name, collation in rows if collation != 'C']} "
            f"do not sort bytewise"
        )


def test_the_lengths_are_generated_rather_than_cached(postgres_store):
    """The SQLite length cache and its three triggers, as two stored columns.

    A value computed with the row cannot go stale, which is the whole of why
    the threshold, the backfill and the cache check do not port.
    """
    query(
        postgres_store,
        "INSERT INTO documents "
        "(key, doc_key, meta_name, meta_path, parent, content, format, updated_at, sort_key) "
        "VALUES ('a', 'a', NULL, NULL, '', %s, 'text', '2026-09-21 00:00:00', 'a')",
        ("héllo",),
    )
    assert query(postgres_store, "SELECT chars, bytes FROM documents WHERE key = 'a'") == [(5, 6)]

    query(postgres_store, "UPDATE documents SET content = 'x' WHERE key = 'a'")
    assert query(postgres_store, "SELECT chars, bytes FROM documents WHERE key = 'a'") == [(1, 1)]


def test_the_schema_a_connection_asked_for_is_read_the_way_postgres_reads_it():
    """The fallback for a search path naming nothing that exists yet.

    Pure string work, and worth asking directly: the default path is
    ``"$user", public``, so a reader that took the first entry literally would
    create a schema named after whoever happened to connect. ``SHOW
    search_path`` quotes an entry the server considers to need it, which is
    why the quotes come off.
    """
    assert _first_schema('"$user", public', user="john") == "john"
    assert _first_schema("notes", user="john") == "notes"
    assert _first_schema('"Notes", public', user="john") == "Notes"
    assert _first_schema(", public", user="john") == "public"
    assert _first_schema("", user="john") is None


# -- the service file ------------------------------------------------------


def test_the_service_file_may_be_absolute_or_start_with_a_tilde(tmp_path, monkeypatch):
    """This backend's one relaxation of the relative-only rule.

    The standard service file is in the home directory and is shared with
    ``psql``; a copy of it inside ``--dir`` would be a second place for a
    password to live. Asked of the resolver rather than of an open, so that it
    is a statement about the rule and not about a server.
    """
    absolute = tmp_path / "elsewhere" / "pg_service.conf"
    assert PostgresStore.service_file(tmp_path / "dir", absolute) == absolute

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    assert PostgresStore.service_file(tmp_path / "dir", "~/pg_service.conf") == (
        tmp_path / "home" / "pg_service.conf"
    )


def test_a_relative_service_file_is_still_a_name_inside_the_store_directory(tmp_path):
    """The half of the rule that was never about relocatability.

    ``..`` reaches outside the directory an operator named, and it is refused
    here as it is for every other backend: relaxing "absolute" says where a
    person's own configuration lives, and says nothing about climbing out.
    """
    directory = tmp_path / "dir"
    assert PostgresStore.service_file(directory, "pg_service.conf") == (
        directory / "pg_service.conf"
    )
    with raises_rendered(StoreFileError, "climbs out of the store directory"):
        PostgresStore.service_file(directory, "../pg_service.conf")


def test_a_mount_naming_no_file_means_libpqs_own_lookup(tmp_path):
    """Which is a search, not a path, and is why the backend locates its own store."""
    assert PostgresStore.service_file(tmp_path, None) is None
    assert PostgresStore.locates_own_store is True


def test_every_reason_the_service_cannot_be_read_is_reported_at_once(tmp_path):
    """A file with two things wrong with it is one run, not two.

    The reader collects refusals as values precisely so that this is possible;
    the open has to raise, and the aggregate is what carries them across.
    """
    path = tmp_path / "pg_service.conf"
    path.write_text("[outrage]\nhost=localhost\nhsot=localhost\nsslrootcert=nowhere.pem\n")
    with pytest.raises(ServiceUnusable) as raised:
        PostgresStore(tmp_path / "dir", filename=path)
    codes = [one["code"] for one in raised.value.details["reasons"]]
    assert codes == ["service-parameter-unknown", "service-parameter-missing-file"]

    rendered = messages.render(raised.value)
    assert "hsot" in rendered and "nowhere.pem" in rendered


def test_a_service_that_is_not_in_the_file_is_refused_before_anything_connects(tmp_path):
    path = tmp_path / "pg_service.conf"
    path.write_text("[other]\nhost=localhost\n")
    with raises_rendered(ServiceUnusable, "no PostgreSQL service named 'outrage'"):
        PostgresStore(tmp_path / "dir", filename=path)


def test_a_password_in_the_entry_reaches_no_rendering_of_the_store(tmp_path, postgres_service):
    """The rule the whole service file exists for, asked of this backend.

    ``pgservice`` is held to it for its own values; this is the same question
    one layer up, where a store holds the service and a traceback would print
    whatever it holds.
    """
    path, service, _schema = postgres_service
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("[outrage]\n", "[outrage]\npassword=hunter2\n"), encoding="utf-8")

    with PostgresStore(tmp_path / "dir", filename=path, service=service) as opened:
        assert "hunter2" not in repr(opened.service)
        assert "hunter2" not in str(opened.service.redacted)
        assert opened.service.redacted["password"] == pgservice.REDACTION
        assert opened.service.holds_secret is True


def test_a_server_that_is_not_answering_is_not_a_configuration_error(tmp_path):
    """An offline laptop starts with its other mounts working.

    A port nothing listens on rather than a host that does not resolve, so the
    failure is a refused connection and not a name lookup that some resolvers
    answer with a wildcard.
    """
    path = tmp_path / "pg_service.conf"
    path.write_text("[outrage]\nhost=127.0.0.1\nport=1\ndbname=outrage\nconnect_timeout=2\n")
    with raises_rendered(BackendError, "cannot reach the PostgreSQL server") as raised:
        PostgresStore(tmp_path / "dir", filename=path)
    # The code a tolerant open keys on. `_CONFIGURATION_ERROR_CODES` is the
    # list that stays fatal, and this deliberately is not in it.
    assert raised.value.code == "postgres-unreachable"


# -- the floors ------------------------------------------------------------


def test_a_store_this_build_knows_is_operated_at_its_own_version():
    """Point 1 of ``plans/postgres/migration``: a client writes the store's shape."""
    decided = compatibility(
        SchemaVersion(MIN_SCHEMA_VERSION, MIN_SCHEMA_VERSION, MIN_SCHEMA_VERSION)
    )
    assert decided.operating == MIN_SCHEMA_VERSION
    assert decided.writable is True
    assert decided.read_only_reason is None


def test_a_newer_store_above_the_write_floor_opens_normally():
    """The floors are a promise about shapes, so a newer store can still be written."""
    decided = compatibility(SchemaVersion(SCHEMA_VERSION + 3, SCHEMA_VERSION, SCHEMA_VERSION))
    assert decided.operating == SCHEMA_VERSION
    assert decided.writable is True


def test_a_newer_store_between_the_floors_is_read_only():
    decided = compatibility(SchemaVersion(SCHEMA_VERSION + 3, SCHEMA_VERSION, SCHEMA_VERSION + 1))
    assert decided.operating == SCHEMA_VERSION
    assert decided.writable is False
    assert decided.read_only_reason.code == "postgres-below-write-floor"


def test_a_store_below_this_builds_read_floor_is_refused():
    with raises_rendered(BackendError, "may only be read by a build that knows"):
        compatibility(SchemaVersion(SCHEMA_VERSION + 3, SCHEMA_VERSION + 1, SCHEMA_VERSION + 1))


def test_a_store_older_than_this_build_supports_names_the_migration_command():
    with raises_rendered(BackendError, "outrage schema migrate"):
        compatibility(
            SchemaVersion(MIN_SCHEMA_VERSION - 1, MIN_SCHEMA_VERSION - 1, MIN_SCHEMA_VERSION - 1)
        )


def test_an_open_session_is_turned_away_by_a_raised_write_floor(tmp_path, postgres_service):
    """The floors reach a live store, not only the decision function.

    Raised by hand, which is what ``plans/postgres/migration`` says to do until
    there is a version 2 with a step to run: the refusal paths are worth
    testing before the migration that would produce them exists.
    """
    path, service, _schema = postgres_service
    with PostgresStore(tmp_path / "dir", filename=path, service=service) as opened:
        query(
            opened,
            f"UPDATE {SCHEMA_TABLE} SET version = %s, write_floor = %s",
            (SCHEMA_VERSION + 1, SCHEMA_VERSION + 1),
        )
    with PostgresStore(tmp_path / "dir", filename=path, service=service) as reopened:
        assert reopened.compatibility.writable is False
        with raises_rendered(ReadOnlyStoreError, "only a build that knows version"):
            reopened.store_document("a/b", "x")
        with raises_rendered(ReadOnlyStoreError, "cannot delete"):
            reopened.delete("a/b")


def test_a_store_written_by_something_far_newer_is_refused(tmp_path, postgres_service):
    path, service, _schema = postgres_service
    with PostgresStore(tmp_path / "dir", filename=path, service=service) as opened:
        query(
            opened,
            f"UPDATE {SCHEMA_TABLE} SET version = %s, read_floor = %s, write_floor = %s",
            (SCHEMA_VERSION + 2, SCHEMA_VERSION + 1, SCHEMA_VERSION + 1),
        )
    with raises_rendered(BackendError, "may only be read by a build that knows"):
        PostgresStore(tmp_path / "dir", filename=path, service=service)


# -- connections -----------------------------------------------------------


def test_each_thread_gets_its_own_connection_and_close_takes_them_all(tmp_path, postgres_service):
    """Unlike the SQLite backend, which can only close the calling thread's.

    psycopg lets a connection be closed from another thread, so a store here
    need not leave one to its thread's lifetime -- and a connection left open
    is a backend process at the far end rather than a file handle at this one.
    """
    path, service, _schema = postgres_service
    with PostgresStore(tmp_path / "dir", filename=path, service=service) as opened:
        seen = {}
        lock = threading.Lock()

        def work(index):
            conn = opened._conn
            with lock:
                seen[index] = conn

        in_threads(work, threads=4)
        assert len({id(conn) for conn in seen.values()}) == 4
        held = list(opened._connections)
        assert len(held) == 5  # four workers and the one the open used

    assert all(conn.closed for conn in held)


def test_a_failed_open_closes_the_connection_it_had(tmp_path, postgres_service):
    """A constructor that raises never hands the object back, so nothing else can.

    At this end that is a file handle; at the far end it is a backend process
    the server holds until it notices. The refusal used here is the version
    check, because it is the last thing an open does and so the one with the
    most already open behind it.
    """
    psycopg = pytest.importorskip("psycopg")
    path, service, _schema = postgres_service
    with PostgresStore(tmp_path / "dir", filename=path, service=service) as opened:
        query(
            opened,
            f"UPDATE {SCHEMA_TABLE} SET version = %s, read_floor = %s, write_floor = %s",
            (SCHEMA_VERSION + 2, SCHEMA_VERSION + 1, SCHEMA_VERSION + 1),
        )

    before = _backends(psycopg)
    with pytest.raises(BackendError):
        PostgresStore(tmp_path / "dir", filename=path, service=service)
    assert _settles_at(psycopg, before), (
        f"a failed open left a session behind: {_backends(psycopg)} against {before}"
    )


def _backends(psycopg):
    """How many sessions this application has open on the test server."""
    with psycopg.connect(postgres_dsn(), connect_timeout=5) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE application_name = 'outrage'"
            )
            return cursor.fetchone()[0]


def _settles_at(psycopg, expected, seconds=5.0):
    """Whether the session count comes back to ``expected`` within ``seconds``.

    Polled rather than read once, because closing a connection asks the server
    to end a backend process and ``pg_stat_activity`` catches up a moment
    later. The asymmetry is what makes this an honest test: a count that is
    merely late converges, and a leaked session never does.
    """
    deadline = time.monotonic() + seconds
    while True:
        if _backends(psycopg) == expected:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.05)


def test_closing_twice_is_allowed(postgres_store):
    postgres_store.close()
    postgres_store.close()


# -- a tolerant startup ----------------------------------------------------


def test_a_server_that_is_down_leaves_the_other_mounts_working(tmp_path):
    """The whole point of classing an unreachable server as not-a-mistake.

    An offline laptop starts, its local mounts answer, and the shared one is
    reported missing rather than stopping the server from starting at all. A
    misspelled backend or an option the backend cannot honour stays fatal, and
    that is the line ``_CONFIGURATION_ERROR_CODES`` draws.
    """
    path = tmp_path / "pg_service.conf"
    path.write_text("[outrage]\nhost=127.0.0.1\nport=1\ndbname=outrage\nconnect_timeout=2\n")
    failures = []

    with open_mounts(
        tmp_path / "dir",
        [f"shared={path},type=postgres", "local=local.sqlite"],
        on_open_error=lambda point, spec, ro, exc: failures.append((point, exc.code)),
    ) as table:
        table.store_document("local/note", "the rest of the table still works")
        assert table.retrieve_document("local/note").content.startswith("the rest")
        assert [mount.name for mount in table] == ["/", "local"]

    assert failures == [("shared", "postgres-unreachable")]


def service_file_like(tmp_path, postgres_service, **changed):
    """A second service file, the fixture's with some parameters changed."""
    psycopg = pytest.importorskip("psycopg")
    _path, service, schema = postgres_service
    parameters = psycopg.conninfo.conninfo_to_dict(postgres_dsn())
    parameters["options"] = f"-csearch_path={schema}"
    parameters.update(changed)
    path = tmp_path / "changed_service.conf"
    written = "\n".join(f"{name}={value}" for name, value in sorted(parameters.items()))
    path.write_text(f"[{service}]\n{written}\n", encoding="utf-8")
    return path


def tables_in(schema):
    """The tables a schema holds, asked of the server directly."""
    psycopg = pytest.importorskip("psycopg")
    with psycopg.connect(postgres_dsn(), connect_timeout=5) as conn:
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = %s",
            (schema,),
        ).fetchall()
    return sorted(row[0] for row in rows)


@pytest.mark.parametrize(
    ("said", "code"),
    [
        # As psycopg 3.3 reports them against PostgreSQL 18, one line per
        # address `localhost` resolved to, measured rather than composed.
        (
            'connection failed: connection to server at "127.0.0.1", port 5432 failed: '
            'FATAL:  database "nope" does not exist\nMultiple connection attempts failed.',
            "postgres-database-missing",
        ),
        (
            'connection failed: connection to server at "::1", port 5432 failed: '
            'FATAL:  role "nobody" does not exist',
            "postgres-login-rejected",
        ),
        ('FATAL:  password authentication failed for user "john"', "postgres-login-rejected"),
        (
            'FATAL:  no pg_hba.conf entry for host "10.0.0.2", user "john", database "x"',
            "postgres-login-rejected",
        ),
        ("fe_sendauth: no password supplied", "postgres-login-rejected"),
        (
            'connection failed: connection to server at "127.0.0.1", port 1 failed: '
            "Connection refused",
            None,
        ),
        ("failed to resolve host 'no-such-host.invalid'", None),
        # A server whose lc_messages is German says the same thing in words
        # nothing here matches, and is tolerated rather than guessed at.
        ("FATAL:  Datenbank »nope« existiert nicht", None),
    ],
)
def test_a_failed_connect_is_told_apart_by_what_the_server_said(said, code):
    """No SQLSTATE reaches a connection that never opened, so the text decides."""
    assert store_postgres._connect_refusal(said) == code


def test_a_failed_connect_says_its_reason_once_when_every_attempt_agrees():
    """``localhost`` resolves twice, and psycopg then says everything three times."""
    same = (
        'connection failed: connection to server at "127.0.0.1", port 5432 failed: '
        'FATAL:  database "nope" does not exist\n'
        "Multiple connection attempts failed. All failures were:\n"
        "- host: 'localhost', port: None, hostaddr: '::1': connection failed: connection "
        'to server at "::1", port 5432 failed: FATAL:  database "nope" does not exist\n'
        "- host: 'localhost', port: None, hostaddr: '127.0.0.1': connection failed: "
        'connection to server at "127.0.0.1", port 5432 failed: FATAL:  database "nope" '
        "does not exist\n"
    )
    assert store_postgres._connect_reason(same) == same.split("\n")[0]
    differing = same.replace(
        '"::1", port 5432 failed: FATAL:  database "nope" does not exist',
        '"::1", port 5432 failed: Connection refused',
    )
    assert store_postgres._connect_reason(differing) == differing.strip()
    assert store_postgres._connect_reason("  one line only\n") == "one line only"


def test_the_backend_is_reached_by_either_name(tmp_path, postgres_service):
    """``type=postgres`` and the server's own name, ``postgresql``, are one backend."""
    path, _service, _schema = postgres_service
    with open_mounts(
        tmp_path / "dir",
        [f"shared={path},type=postgres", f"alias={path},type=postgresql"],
    ) as table:
        table.store_document("shared/note", "written through one name")
        assert table.retrieve_document("alias/note").content == "written through one name"
        assert {mount.name: mount.store.backend_name for mount in table}["alias"] == "postgres"


@pytest.mark.parametrize(
    ("changed", "code"),
    [
        ({"dbname": "outrage_no_such_database"}, "postgres-database-missing"),
        ({"user": "outrage_no_such_role"}, "postgres-login-rejected"),
    ],
)
def test_a_server_that_refuses_is_a_configuration_error(tmp_path, postgres_service, changed, code):
    """The server is there, so waiting for it will not help: fatal, not tolerated."""
    path = service_file_like(tmp_path, postgres_service, **changed)
    failures = []
    with pytest.raises(BackendError) as raised:
        open_mounts(
            tmp_path / "dir",
            [f"shared={path},type=postgres", "local=local.sqlite"],
            on_open_error=lambda *failure: failures.append(failure),
        )
    assert raised.value.code == code
    assert failures == []


def test_a_service_file_that_cannot_be_used_is_a_configuration_error(tmp_path):
    """A missing entry is fatal under a tolerant open, as the design says."""
    path = tmp_path / "pg_service.conf"
    path.write_text("[somebody_else]\nhost=localhost\n", encoding="utf-8")
    with pytest.raises(ServiceUnusable):
        open_mounts(
            tmp_path / "dir",
            [f"shared={path},type=postgres"],
            on_open_error=lambda *_failure: pytest.fail("a configuration error was tolerated"),
        )


def test_a_read_only_mount_of_an_empty_schema_is_refused_and_left_empty(tmp_path, postgres_service):
    """The protection ``mount-read-only-missing`` gives every other backend.

    Checked on the server rather than trusted from the refusal: the point is
    that the schema is still empty afterwards, since a read-only mount that
    created its store would mount as one no write could ever contradict.
    """
    path, _service, schema = postgres_service
    with raises_rendered(BackendError, "read-only mount at 'shared' has no store") as raised:
        open_mounts(tmp_path / "dir", read_only_specs=[f"shared={path},type=postgres"])
    assert raised.value.code == "postgres-read-only-missing"
    assert tables_in(schema) == []


def test_a_read_only_mount_of_a_missing_store_is_tolerated_at_startup(tmp_path, postgres_service):
    """Missing is not misconfigured: the same judgement the file backends get."""
    path, _service, _schema = postgres_service
    failures = []
    with open_mounts(
        tmp_path / "dir",
        read_only_specs=[f"shared={path},type=postgres"],
        on_open_error=lambda point, spec, ro, exc: failures.append((point, ro, exc.code)),
    ) as table:
        assert [mount.name for mount in table] == ["/"]
    assert failures == [("shared", True, "postgres-read-only-missing")]


def test_a_read_only_mount_of_a_store_reads_and_refuses_writes(tmp_path, postgres_service):
    path, _service, _schema = postgres_service
    with open_mounts(tmp_path / "dir", [f"shared={path},type=postgres"]) as table:
        table.store_document("shared/note", "there already")
    with open_mounts(tmp_path / "dir", read_only_specs=[f"shared={path},type=postgres"]) as table:
        assert table.retrieve_document("shared/note").content == "there already"
        with pytest.raises(ReadOnlyMountError):
            table.store_document("shared/note", "overwritten")


def test_info_says_where_the_store_is_and_never_the_password(tmp_path, postgres_service):
    """The redacted target, through both front ends' shared description.

    A password planted in the service file: trust authentication ignores it,
    so the store opens, and it must appear in neither the tool's result nor
    the command line's table.
    """
    from outrage import info
    from outrage.cli import _info_rows

    secret = "planted-secret-9f3a"
    path = service_file_like(tmp_path, postgres_service, password=secret)
    _original, service, schema = postgres_service
    with open_mounts(tmp_path / "dir", [f"shared={path},type=postgres"]) as table:
        described = info.describe(table)
    shared = next(mount for mount in described.mounts if mount.mount == "shared")
    assert shared.path == str(path.resolve())
    assert shared.target["service"] == service
    assert shared.target["schema"] == schema
    assert shared.target["password"] == pgservice.REDACTION
    assert shared.target["dbname"] == "outrage_test"
    assert secret not in repr(described)
    row = next(row for row in _info_rows(described) if row[0] == "shared")
    assert f"schema={schema}" in row[3]
    assert secret not in " ".join(row)
    root = next(mount for mount in described.mounts if mount.mount == "/")
    assert root.target is None


def test_the_mount_tool_takes_a_service_file_outside_the_store_directory(
    tmp_path, postgres_service
):
    """An absolute FILE, as the usual ``~/.pg_service.conf`` is.

    The tool resolved every FILE inside the store directory before opening
    anything, which refuses an absolute path as a mistake -- so the backend was
    registered and still out of the tool's reach.
    """
    from outrage.remount import Live

    path, _service, schema = postgres_service
    with open_mounts(tmp_path / "dir") as table, Live(table, directory=tmp_path / "dir") as live:
        with raises_rendered(BackendError, "has no store in schema"):
            live.mount("shared", file=str(path), type="postgres", read_only=True)
        assert tables_in(schema) == []
        changed = live.mount("shared", file=str(path), type="postgres")
        assert "mount-created-store" not in [note.code for note in changed.notes]
        live.table.store_document("shared/note", "through the tool")
        assert live.table.retrieve_document("shared/note").content == "through the tool"


def test_the_mount_tool_reads_no_file_with_a_type_as_libpqs_own_lookup(
    tmp_path, postgres_service, monkeypatch
):
    """No FILE means a built-in only when nothing says a backend finds its own store."""
    from outrage.remount import Live

    path, _service, _schema = postgres_service
    monkeypatch.setenv(pgservice.SERVICE_FILE_VARIABLE, str(path))
    with open_mounts(tmp_path / "dir") as table, Live(table, directory=tmp_path / "dir") as live:
        live.mount("shared", type="postgres")
        shared = {mount.name: mount.store for mount in live.table}["shared"]
        assert shared.path == path


# -- the command line ------------------------------------------------------


def test_info_on_the_command_line_names_the_target(tmp_path, postgres_service):
    path, _service, schema = postgres_service
    with open_mounts(tmp_path / "dir"):
        pass  # `info` reports on a store that is there, so the root is made first
    status, output = run(
        "info", "--dir", str(tmp_path / "dir"), "--mount", f"shared={path},type=postgres"
    )
    assert status == 0
    assert f"schema={schema}" in output
    assert "service=outrage" in output


def test_schema_status_reports_an_empty_schema_without_filling_it(tmp_path, postgres_service):
    """The whole reason ``status`` does not open the store the ordinary way.

    Opening a read-write mount creates its store, so a report that went
    through the mount table would answer its own question -- every schema it
    was pointed at would hold a store by the time it said so.
    """
    path, _service, schema = postgres_service
    status, output = run(
        "schema",
        "status",
        "shared",
        "--dir",
        str(tmp_path / "dir"),
        "--mount",
        f"shared={path},type=postgres",
    )

    assert status == 0
    assert "backend     postgres" in output
    assert f"schema      {schema}" in output
    assert "holds no outrage store yet" in output
    assert f"would create a store at version {SCHEMA_VERSION}" in output


def test_schema_create_then_status_reports_the_store(tmp_path, postgres_service):
    path, _service, _schema = postgres_service
    where = ("--dir", str(tmp_path / "dir"), "--mount", f"shared={path},type=postgres")

    status, output = run("schema", "create", "shared", *where)
    assert status == 0
    assert f"created a store at schema version {SCHEMA_VERSION}" in output
    # Reported from the store the create left behind, not from the empty
    # schema the open found: the object's own state moves with the store.
    assert f"in schema {_schema}" in output

    status, output = run("schema", "status", "shared", *where)
    assert status == 0
    assert f"store       version {SCHEMA_VERSION}" in output
    assert f"on open     read and write, at version {SCHEMA_VERSION}" in output


def test_schema_create_refuses_a_schema_that_already_holds_a_store(
    tmp_path, postgres_service, capsys
):
    path, _service, _schema = postgres_service
    where = ("--dir", str(tmp_path / "dir"), "--mount", f"shared={path},type=postgres")
    run("schema", "create", "shared", *where)

    status, _output = run("schema", "create", "shared", *where)

    assert status == 1
    assert "already holds an outrage store" in capsys.readouterr().err


def test_schema_status_says_what_this_build_would_do_with_a_store_it_cannot_use(
    tmp_path, postgres_service
):
    """A report on a store that cannot be opened is the report worth having."""
    path, service, _schema = postgres_service
    where = ("--dir", str(tmp_path / "dir"), "--mount", f"shared={path},type=postgres")
    with PostgresStore(tmp_path / "dir", filename=path, service=service) as opened:
        query(
            opened,
            f"UPDATE {SCHEMA_TABLE} SET version = %s, read_floor = %s, write_floor = %s",
            (SCHEMA_VERSION + 2, SCHEMA_VERSION + 1, SCHEMA_VERSION + 1),
        )

    status, output = run("schema", "status", "shared", *where)

    assert status == 1
    assert "on open     refused" in output
    assert "may only be read by a build that knows" in output


def test_schema_names_a_mount_this_line_does_not_have(tmp_path, postgres_service, capsys):
    status, _output = run("schema", "status", "elsewhere", "--dir", str(tmp_path / "dir"))
    assert status == 1
    assert "no mount on this command line is at" in capsys.readouterr().err


# -- the operations --------------------------------------------------------
#
# What a store does is `test_store.py`, which runs against this backend. What
# is here is what that file cannot see: the order under a collation that
# disagrees with it, the SQL metadata split in this dialect, and the reads
# whose server-side slicing only shows once a document is longer than the
# window one statement fetches.


@pytest.mark.parametrize("meta_name", SPLIT_META_NAMES)
def test_the_sql_metadata_split_agrees_with_keys_relative(postgres_store, meta_name):
    """The expression SQLite uses, with ``strpos`` for ``instr``, held to the same oracle.

    On the store's own connection, so the scratch table lands in the test's
    schema and goes with it.
    """
    assert_the_split_agrees_with_keys_relative(
        postgres_store._conn, meta_name, find="strpos", mark="%s"
    )


def _paged(read):
    """Every item a paged read returns, two at a time, to the end."""
    seen, cursor = [], None
    for _ in range(100):
        page = read(cursor)
        seen += page.items
        if page.next_cursor is None:
            return seen
        cursor = page.next_cursor
    raise AssertionError("the cursor did not reach the end")


def test_paging_follows_the_stores_order_where_the_collation_would_not(postgres_store):
    """The paging half of the collation guard: every cursor, bounded as Python bounds it.

    Keys chosen to disagree between the database's own collation and
    bytewise order, written through the store and read back two at a time
    through each paged read. A page that bounded on the wrong order would
    skip or repeat a key here and say nothing. The listing walks the level
    at the root, so its children include ``a`` and ``A``, implicit above
    ``a/b`` and ``A/b``.
    """
    for key in DISAGREEING_KEYS:
        postgres_store.store_document(key, "x")
    order = sorted(DISAGREEING_KEYS, key=keys.sort_form)

    documents = _paged(lambda c: postgres_store.get_documents(limit=2, cursor=c))
    assert [item.key for item in documents] == order

    missing = _paged(lambda c: postgres_store.keys_missing_meta(limit=2, cursor=c))
    assert missing == order

    level = sorted({key.split("/")[0] for key in DISAGREEING_KEYS}, key=keys.sort_form)
    listed = _paged(lambda c: postgres_store.list_keys(limit=2, cursor=c))
    assert [entry.key for entry in listed] == level

    collated = [
        key
        for (key,) in query(
            postgres_store, 'SELECT key FROM documents ORDER BY sort_key COLLATE "default"'
        )
    ]
    assert collated != order, (
        "this database's own collation agrees with the store's order, so this "
        "test cannot tell a declared collation from a missing one"
    )


def test_a_level_is_named_by_one_probe_per_child_whatever_lies_beneath(postgres_store):
    """The walk skips a child's subtree rather than reading it.

    Asked of the plan rather than of a clock: ``EXPLAIN ANALYZE`` of the walk
    says how many rows the recursion produced, and it is one per child --
    here three, over a subtree of two hundred rows. A walk that stepped a row
    at a time would produce every one of them.
    """
    for child in ("a", "b", "c"):
        for n in range(1, 67):
            postgres_store.store_document(f"p/{child}/{n}", "x")
    walk, params = postgres_store._walk("p")
    plan = [
        line
        for (line,) in query(
            postgres_store,
            f"EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY OFF) {walk} SELECT child FROM level",
            params,
        )
    ]
    recursive = next(line for line in plan if "Recursive Union" in line)
    produced = re.search(r"actual rows=([0-9.]+)", recursive)
    assert produced is not None and float(produced.group(1)) == 3, plan
    assert [e.key for e in postgres_store.list_keys("p").items] == ["p/a", "p/b", "p/c"]


def test_allocations_under_one_parent_never_share_a_number_whatever_follows_it(
    tmp_path, postgres_service
):
    """The case ``ON CONFLICT`` could not see: two ``?`` writes making different keys.

    ``c/?/doc`` and ``c/?/task`` at once become ``c/5/doc`` and ``c/5/task``
    unless allocation is ordered, and no key collides to say so. Asked of
    separate stores, each with its own connections, which is what two
    devices are.
    """
    path, service, _schema = postgres_service
    stores = [PostgresStore(tmp_path / f"dir{n}", filename=path, service=service) for n in range(4)]
    allocated = []
    lock = threading.Lock()

    def allocate(n):
        suffix = ("doc", "task")[n % 2]
        mine = [stores[n % 4].store_document(f"c/?/{suffix}", "x") for _ in range(15)]
        with lock:
            allocated.extend(key.split("/")[1] for key in mine)

    try:
        in_threads(allocate, threads=8)
    finally:
        for opened in stores:
            opened.close()
    assert sorted(allocated, key=int) == [str(n) for n in range(1, 121)]


def test_the_allocation_space_is_per_parent_and_fits_an_int4():
    from outrage.store_postgres import _allocation_space

    assert _allocation_space("s", "a") == _allocation_space("s", "a")
    assert _allocation_space("s", "a") != _allocation_space("s", "b")
    assert _allocation_space("s", "a") != _allocation_space("t", "a")
    assert all(-(2**31) <= _allocation_space("s", str(n)) < 2**31 for n in range(1000))


def _hold_number(postgres_service, store, parent, number):
    """An outside session holding ``number`` under ``parent``, as another allocator would."""
    from outrage.store_postgres import _TRY_NUMBER, _allocation_space

    conn = _outsider(postgres_service)
    conn.execute("BEGIN")
    held = conn.execute(
        f"SELECT {_TRY_NUMBER.format(number='%s')}",
        (_allocation_space(store.schema, parent), str(number)),
    ).fetchone()[0]
    assert held
    return conn


def test_a_number_another_allocator_holds_is_passed_over_without_waiting(
    postgres_store, postgres_service
):
    """And its title goes with the number taken, not the one passed over."""
    for n in range(1, 5):
        postgres_store.store_document(f"c/{n}/task", "x")
    holder = _hold_number(postgres_service, postgres_store, "c", 5)
    try:
        assert postgres_store.store_document("c/?/task", "mine", title="T") == "c/6/task"
    finally:
        holder.close()
    assert postgres_store.retrieve_document("c/6/task/!title").content == "T"
    assert not postgres_store.exists("c/5")
    assert postgres_store.list_keys("c/5").items == []
    # The holder went away without writing, so 5 is left as a hole.
    assert postgres_store.store_document("c/?/task", "next") == "c/7/task"


def test_an_uncommitted_write_naming_the_number_outright_is_not_written_over(
    postgres_store, postgres_service
):
    """The allocation waits for it, then passes the number over.

    The walk cannot see a write that has not committed, so the candidate is
    that write's number; the insert meets the uncommitted key and waits, and
    once it commits the number is taken. An upsert would have replaced it.
    """
    psycopg = pytest.importorskip("psycopg")
    postgres_store.store_document("c/4/task", "x")
    outcome = {}

    def allocate():
        outcome["key"] = postgres_store.store_document("c/?/task", "allocated")

    with _outsider(postgres_service) as conn:
        with conn.transaction():
            conn.execute(
                "INSERT INTO documents (key, doc_key, parent, content, updated_at, sort_key) "
                "VALUES ('c/5/task', 'c/5/task', 'c/5', 'by hand', 'now', %s)",
                (keys.sort_form("c/5/task"),),
            )
            allocator = threading.Thread(target=allocate)
            allocator.start()
            assert _blocked_on_a_lock(psycopg), "the allocation never met the uncommitted key"
    allocator.join(10)
    assert outcome["key"] == "c/6/task"
    assert postgres_store.retrieve_document("c/5/task").content == "by hand"


@pytest.mark.parametrize(
    ("children", "expected"),
    [
        ([], "1"),
        (["9", "10", "doc"], "11"),
        (["3", "\u0663", "12a", "a12", "\u00b9"], "4"),  # Arabic-Indic three, superscript one
        (["99999999999999999999"], "100000000000000000000"),
    ],
    ids=["empty", "numeric-order", "ascii-digits-only", "past-a-bigint"],
)
def test_the_server_counts_a_segment_as_a_number_exactly_as_keys_does(
    postgres_store, children, expected
):
    """Two statements of one rule: ``keys.NUMERIC_RE`` here, a regex at the server."""
    for child in children:
        postgres_store.store_document(f"p/{child}", "x")
    numbers = [int(c) for c in children if keys.NUMERIC_RE.match(c)]
    assert str(max(numbers, default=0) + 1) == expected
    assert postgres_store.store_document("p/?", "x") == f"p/{expected}"


def test_a_number_at_the_root_is_allocated_too(postgres_store):
    postgres_store.store_document("7", "x")
    postgres_store.store_document("seven", "x")
    assert postgres_store.store_document("?/doc", "x", title="T") == "8/doc"
    assert postgres_store.retrieve_document("8/doc/!title").content == "T"


def test_a_nul_character_is_refused_naming_every_field_that_holds_one(postgres_store):
    """A ``text`` value cannot hold U+0000, so the write says so rather than psycopg."""
    with raises_rendered(
        InvalidArgumentError, r"the content and title fields hold the character U\+0000"
    ):
        postgres_store.store_document("a", "x\0y", title="t\0", contents="fine")
    with raises_rendered(InvalidArgumentError, r"the contents field holds the character U\+0000"):
        postgres_store.store_document("a", "x", contents="\0")
    assert not postgres_store.exists("a")


# A document long enough, and far enough from ASCII, that a byte read runs
# through several windows once the window is shrunk: each line mixes one-,
# two-, three- and four-byte characters.
_LONG = "".join(f"line {n}: é中𝄞 ascii {n * 'x'}\n" for n in range(1, 60))


@pytest.fixture
def both(tmp_path, postgres_store, monkeypatch):
    """The same long document in this backend and in SQLite, with a tiny read window.

    SQLite seeks inside a blob and is the oracle; this backend fetches
    windows from the server. Eleven bytes a window, so every read of any
    length crosses several and every boundary rule is exercised on a window
    edge, including one landing inside a character.
    """
    from outrage import store_postgres

    monkeypatch.setattr(store_postgres, "READAHEAD", 11)
    with SqliteStore(tmp_path / "oracle") as oracle:
        for store in (oracle, postgres_store):
            # One stamp for both, or the comparison is of two clocks a few
            # milliseconds apart rather than of two ways of reading.
            store.store_document("doc", _LONG, "text", updated_at="2026-09-21T10:00:00+00:00")
        yield oracle, postgres_store


@pytest.mark.parametrize(
    "read",
    [
        {"byte_offset": 0, "max_chars": 50},
        {"byte_offset": 9, "max_chars": 7},
        {"byte_offset": 10, "max_chars": 40},
        {"byte_offset": 500, "length": 25},
        {"byte_offset": 5000},
        {"line": 1, "max_chars": 30},
        {"line": 7, "lines": 3},
        {"line": 40, "max_chars": 60},
        {"line": 1000},
        {"byte_offset": 3, "pattern": "中", "occurrence": 4},
        {"line": 3, "pattern": "𝄞", "occurrence": 2},
        {"line": 3, "pattern": "absent"},
    ],
)
def test_a_byte_or_line_read_across_windows_answers_as_a_seek_does(both, read):
    oracle, postgres = both
    answers_alike(oracle, postgres, lambda s: s.retrieve_document("doc", **read))


def test_a_bulk_read_cut_on_the_server_reports_what_a_whole_read_does(tmp_path, postgres_store):
    """A document cut to ``max_chars`` before it crosses the network still reports its whole.

    The excerpt's totals and continuations come from the stored lengths
    rather than from text this end holds, so they are compared, field by
    field, with SQLite's, which slices the whole document.
    """
    corpus = {
        "a": "short",
        "b": "é中𝄞" * 40,
        "c": "x" * 100,
        "d": "𝄞" * 9,
        "e": "",
    }
    with SqliteStore(tmp_path / "oracle") as oracle:
        for store in (oracle, postgres_store):
            for key, content in corpus.items():
                store.store_document(key, content, "text")
        for cap in (1, 8, 9, 10, 100, 1000):
            answers_alike(
                oracle,
                postgres_store,
                lambda s, cap=cap: [
                    (e.key, e.content, e.format)
                    + (e.offset, e.returned, e.total, e.next_offset)
                    + (e.byte_offset, e.total_bytes, e.next_byte_offset)
                    for e in s.get_documents(max_chars=cap).items
                ],
            )


def test_a_document_rewritten_between_windows_is_read_again_whole(both, monkeypatch):
    """A byte read never splices two versions of a document into one excerpt.

    The document is rewritten after the first window has been fetched, so
    the second window belongs to another row version. The read starts again
    on the new version and returns only its text.
    """
    from outrage import store_postgres

    _oracle, postgres = both
    fetch = store_postgres._ServerBytes._fetch
    rewritten = []

    def rewrite_once(self, offset, size):
        if not rewritten:
            rewritten.append(True)
            postgres.store_document("doc", "B" * 200, "text")
        return fetch(self, offset, size)

    monkeypatch.setattr(store_postgres._ServerBytes, "_fetch", rewrite_once)
    read = postgres.retrieve_document("doc", byte_offset=0, max_chars=40)
    assert read.content == "B" * 40
    assert read.total_bytes == 200


def test_a_document_rewritten_on_every_read_is_refused_rather_than_looped(both, monkeypatch):
    from outrage import store_postgres

    _oracle, postgres = both
    fetch = store_postgres._ServerBytes._fetch
    count = iter(range(1000))

    def rewrite_always(self, offset, size):
        postgres.store_document("doc", f"{next(count)}" * 200, "text")
        return fetch(self, offset, size)

    monkeypatch.setattr(store_postgres._ServerBytes, "_fetch", rewrite_always)
    with raises_rendered(BackendError, "rewritten while it was being read, 3 times"):
        postgres.retrieve_document("doc", byte_offset=0, max_chars=40)


def test_a_read_leaves_no_transaction_open(postgres_store):
    """Reads are statements in autocommit, not the start of a transaction held open.

    A connection psycopg left in its default mode would sit idle in a
    transaction after its first read for as long as the store is open,
    holding back the server's vacuum and a lock on every table it read.
    """
    postgres_store.store_document("a", "x")
    postgres_store.retrieve_document("a")
    postgres_store.list_keys()
    psycopg = pytest.importorskip("psycopg")
    assert postgres_store._conn.info.transaction_status == psycopg.pq.TransactionStatus.IDLE


# -- the archive -----------------------------------------------------------


def _archived(store) -> list[tuple]:
    """What the archive holds, as (key, content, updated_at), in the order written.

    The archive has no row number, so the order is the writing transaction's
    id and then the key: every write here is a transaction of its own, and a
    document's metadata is archived by the same one.
    """
    return [
        tuple(row)
        for row in query(
            store,
            "SELECT key, content, updated_at FROM document_archive "
            "ORDER BY xmin::text::bigint, key",
        )
    ]


def _outsider(postgres_service):
    """A connection that is not outrage: no declared build, no versioning setting.

    What ``psql`` is, for the purposes of the triggers.
    """
    psycopg = pytest.importorskip("psycopg")
    _path, _service, schema = postgres_service
    return psycopg.connect(postgres_dsn(), options=f"-csearch_path={schema}", autocommit=True)


def test_a_first_write_archives_nothing(postgres_store):
    postgres_store.store_document("a", "one", updated_at="2026-09-13T10:00:00+00:00")
    assert _archived(postgres_store) == []


def test_an_overwrite_keeps_the_row_it_replaced(postgres_store):
    postgres_store.store_document("a", "one", updated_at="2026-09-13T10:00:00+00:00")
    postgres_store.store_document("a", "two", updated_at="2026-09-13T11:00:00+00:00")

    assert _archived(postgres_store) == [("a", "one", "2026-09-13T10:00:00+00:00")]
    assert postgres_store.retrieve_document("a").content == "two"


def test_a_write_that_changes_nothing_archives_nothing(postgres_store):
    stamp = "2026-09-13T10:00:00+00:00"
    postgres_store.store_document("a", "one", "markdown", updated_at=stamp)
    postgres_store.store_document("a", "one", "markdown", updated_at=stamp)
    assert _archived(postgres_store) == []


@pytest.mark.parametrize(
    "change",
    [
        {"content": "one", "format": "markdown", "updated_at": "2026-09-13T11:00:00+00:00"},
        {"content": "one", "format": "text", "updated_at": "2026-09-13T10:00:00+00:00"},
        {"content": "two", "format": "markdown", "updated_at": "2026-09-13T10:00:00+00:00"},
    ],
    ids=["updated_at", "format", "content"],
)
def test_any_of_the_three_columns_that_can_differ_is_a_change(postgres_store, change):
    postgres_store.store_document("a", "one", "markdown", updated_at="2026-09-13T10:00:00+00:00")
    postgres_store.store_document(
        "a", change["content"], change["format"], updated_at=change["updated_at"]
    )
    assert _archived(postgres_store) == [("a", "one", "2026-09-13T10:00:00+00:00")]


def test_metadata_is_archived_by_the_same_write(postgres_store):
    postgres_store.store_document("a", "body", title="Old", updated_at="2026-09-13T10:00:00+00:00")
    postgres_store.store_document("a", "body", title="New", updated_at="2026-09-13T11:00:00+00:00")

    assert _archived(postgres_store) == [
        ("a", "body", "2026-09-13T10:00:00+00:00"),
        ("a/!title", "Old", "2026-09-13T10:00:00+00:00"),
    ]


def test_two_versions_sharing_a_stamp_are_both_kept(postgres_store):
    stamp = "2026-09-13T10:00:00+00:00"
    for content in ("one", "two", "three"):
        postgres_store.store_document("a", content, updated_at=stamp)

    assert _archived(postgres_store) == [("a", "one", stamp), ("a", "two", stamp)]


def test_a_delete_archives_every_row_it_takes(postgres_store):
    postgres_store.store_document("a", "doc", title="A")
    postgres_store.store_document("a/b", "child")

    taken = postgres_store.delete("a", recursive=True)

    assert sorted(key for key, _, _ in _archived(postgres_store)) == sorted(taken)
    assert not postgres_store.exists("a/b")


def test_a_dry_run_delete_archives_nothing(postgres_store):
    postgres_store.store_document("a", "doc")
    postgres_store.delete("a", dry_run=True)
    assert _archived(postgres_store) == []


def test_with_versioning_off_nothing_is_archived(tmp_path, postgres_service):
    path, service, _schema = postgres_service
    with PostgresStore(tmp_path / "dir", filename=path, service=service, versioning=False) as s:
        s.store_document("a", "one", updated_at="2026-09-13T10:00:00+00:00")
        s.store_document("a", "two", updated_at="2026-09-13T11:00:00+00:00")
        s.delete("a")
        assert _archived(s) == []


def test_a_writer_that_is_not_outrage_is_archived_too(postgres_store, postgres_service):
    """What putting the archive in a trigger buys over a statement of the client's."""
    postgres_store.store_document("a", "one", updated_at="2026-09-13T10:00:00+00:00")
    with _outsider(postgres_service) as conn:
        conn.execute("UPDATE documents SET content = 'by hand' WHERE key = 'a'")
        conn.execute("DELETE FROM documents WHERE key = 'a'")

    assert [content for _, content, _ in _archived(postgres_store)] == ["one", "by hand"]


def test_the_archive_has_the_stored_columns_of_documents_in_their_order(postgres_store):
    """The generated lengths aside, which are the row's rather than its history."""

    def columns(table):
        return [
            (name, generated)
            for name, generated in query(
                postgres_store,
                "SELECT column_name, is_generated FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
                (postgres_store.schema, table),
            )
        ]

    stored = [name for name, generated in columns("documents") if generated == "NEVER"]
    assert [name for name, _ in columns("document_archive")] == stored


def _read_everything(opened) -> list:
    """Every read the archive must stay out of, over the whole store."""
    return [
        [(e.key, e.kind, e.size) for e in opened.list_keys("").items],
        [(e.key, e.content) for e in opened.get_documents(store_module.EVERYTHING).items],
        opened.retrieve_document("a").content,
        opened.subtree_totals("a", chars=True),
        opened.descendant_count("a"),
        opened.latest_change("a"),
        [e.key for e in opened.keys_missing_meta(store_module.EVERYTHING).items],
        opened.missing_meta_stats(store_module.EVERYTHING),
        sorted(opened.audit_rows(), key=repr),
    ]


def test_the_archive_is_invisible_to_every_read(postgres_store):
    """Asked of one store with its archive full and then emptied, which is the difference."""
    stamp = "2026-09-13T10:00:00+00:00"
    for key in ("a", "a/b", "a/c", "a/c/d"):
        postgres_store.store_document(key, f"first {key}", title=key, updated_at=stamp)
    for key in ("a", "a/b", "a/c"):
        postgres_store.store_document(key, f"second {key}", updated_at="2026-09-13T11:00:00+00:00")
    postgres_store.delete("a/c", recursive=True)
    assert _archived(postgres_store), "the comparison means nothing over an empty archive"

    full = _read_everything(postgres_store)
    query(postgres_store, "DELETE FROM document_archive")
    assert _read_everything(postgres_store) == full


# -- concurrent writers ----------------------------------------------------


def test_two_devices_writing_one_key_lose_no_version(tmp_path, postgres_service):
    """The case a client-side copy could not keep: both writers archive what they replaced.

    Every write carries content nobody else writes, so each version that was
    ever live is either the live one now or in the archive exactly once.
    """
    path, service, _schema = postgres_service
    stores = [PostgresStore(tmp_path / f"dir{n}", filename=path, service=service) for n in range(4)]
    stores[0].store_document("k", "first")
    written = ["first"]
    lock = threading.Lock()

    def write(n):
        mine = [f"{n}-{i}" for i in range(15)]
        for content in mine:
            stores[n % 4].store_document("k", content)
        with lock:
            written.extend(mine)

    try:
        in_threads(write, threads=8)
        live = stores[0].retrieve_document("k").content
        kept = [content for key, content, _ in _archived(stores[0]) if key == "k"]
    finally:
        for opened in stores:
            opened.close()
    assert sorted([*kept, live]) == sorted(written)


def _blocked_on_a_lock(psycopg, seconds=5.0):
    """Wait until one of this application's sessions is waiting on a lock."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        with psycopg.connect(postgres_dsn(), connect_timeout=5) as conn:
            waiting = conn.execute(
                "SELECT count(*) FROM pg_stat_activity "
                "WHERE application_name = 'outrage' AND wait_event_type = 'Lock'"
            ).fetchone()[0]
        if waiting:
            return True
        time.sleep(0.02)
    return False


def _collide(postgres_store, postgres_service):
    """Make the store's next write to ``k`` fail to serialise, once.

    An outside transaction updates ``k`` and holds it; the store's write
    queues behind the row lock; the outsider commits. A serializable update of
    a row changed after its snapshot is refused with 40001, which is the
    failure the retry exists for, arranged rather than hoped for.
    """
    psycopg = pytest.importorskip("psycopg")
    postgres_store.store_document("k", "before", updated_at="2026-09-13T10:00:00+00:00")
    outcome = {}

    def write():
        try:
            outcome["key"] = postgres_store.store_document(
                "k", "mine", updated_at="2026-09-13T12:00:00+00:00"
            )
        except BaseException as exc:  # noqa: BLE001 - asserted by the caller
            outcome["error"] = exc

    with _outsider(postgres_service) as conn:
        with conn.transaction():
            conn.execute(
                "UPDATE documents SET content = 'theirs', "
                "updated_at = '2026-09-13T11:00:00+00:00' WHERE key = 'k'"
            )
            writer = threading.Thread(target=write)
            writer.start()
            assert _blocked_on_a_lock(psycopg), "the store's write never queued"
    writer.join(10)
    return outcome


def test_a_write_that_cannot_be_serialised_is_tried_again_and_lands(
    postgres_store, postgres_service, monkeypatch
):
    from outrage import store_postgres

    pauses = []
    monkeypatch.setattr(store_postgres, "time", types.SimpleNamespace(sleep=pauses.append))

    outcome = _collide(postgres_store, postgres_service)

    assert "error" not in outcome, outcome
    assert len(pauses) == 1, "the write landed without the retry it was arranged to need"
    assert postgres_store.retrieve_document("k").content == "mine"
    # And the version the outsider wrote in between is kept, by the retry's trigger.
    assert [content for _, content, _ in _archived(postgres_store)] == ["before", "theirs"]


def test_contention_that_outlasts_the_retries_is_reported_and_writes_nothing(
    postgres_store, postgres_service, monkeypatch
):
    from outrage import store_postgres

    monkeypatch.setattr(store_postgres, "WRITE_ATTEMPTS", 1)

    outcome = _collide(postgres_store, postgres_service)

    assert isinstance(outcome.get("error"), BackendError), outcome
    assert outcome["error"].code == "postgres-write-contended"
    assert "nothing was written" in messages.render(outcome["error"])
    assert postgres_store.retrieve_document("k").content == "theirs"


def test_allocations_move_on_rather_than_retrying(tmp_path, postgres_service, monkeypatch):
    """Why a ``?`` write is ``READ COMMITTED``: the server never has to fail one.

    Under a serializable transaction the check after the lock would read an
    old snapshot, and allocators would be kept apart only by the server
    failing all but one of them each time they met.
    """
    from outrage import store_postgres

    pauses = []
    monkeypatch.setattr(store_postgres, "time", types.SimpleNamespace(sleep=pauses.append))
    path, service, _schema = postgres_service
    stores = [PostgresStore(tmp_path / f"dir{n}", filename=path, service=service) for n in range(4)]
    try:
        in_threads(
            lambda n: [stores[n % 4].store_document("c/?", "x") for _ in range(10)], threads=8
        )
    finally:
        for opened in stores:
            opened.close()
    assert pauses == []


def test_a_deletes_unchanged_since_is_atomic(tmp_path, postgres_service, monkeypatch):
    """A write between the check and the delete sends the delete back to the check.

    Arranged exactly: the check passes, a second device rewrites a document
    the delete is about to take, and only then does the delete run. Its
    snapshot predates that rewrite, so the server refuses it, and the retry's
    check sees the change.
    """
    from outrage import store_postgres

    path, service, _schema = postgres_service
    first = PostgresStore(tmp_path / "one", filename=path, service=service)
    second = PostgresStore(tmp_path / "two", filename=path, service=service)
    try:
        first.store_document("a", "doc", updated_at="2026-01-01T00:00:00+00:00")
        first.store_document("a/b", "child", updated_at="2026-01-01T00:00:00+00:00")
        real = store_postgres.check_unchanged
        calls = []

        def check_then_interfere(*args, **kwargs):
            real(*args, **kwargs)
            calls.append(1)
            if len(calls) == 1:
                second.store_document("a/b", "changed", updated_at="2026-12-01T00:00:00+00:00")

        monkeypatch.setattr(store_postgres, "check_unchanged", check_then_interfere)
        monkeypatch.setattr(store_postgres, "time", types.SimpleNamespace(sleep=lambda _: None))

        with pytest.raises(store_module.ChangedSinceError):
            first.delete("a", recursive=True, unchanged_since="2026-06-01T00:00:00+00:00")
        assert first.retrieve_document("a/b").content == "changed"
        assert len(calls) == 1, "the retried check should have refused, not passed"
    finally:
        first.close()
        second.close()


# -- the server's clock -----------------------------------------------------


@pytest.fixture
def wrong_local_clock(monkeypatch):
    """This machine's clock set far from the server's, so a stamp says whose clock made it."""
    monkeypatch.setattr(store_module, "_now", lambda: "1999-01-01T00:00:00+00:00")


def _server_time(store):
    from outrage.store_postgres import _STAMP

    return query(store, f"SELECT {_STAMP}")[0][0]


def _close(a, b, seconds=5):
    from datetime import datetime

    return abs((datetime.fromisoformat(a) - datetime.fromisoformat(b)).total_seconds()) <= seconds


def test_a_write_naming_no_time_is_stamped_by_the_server(postgres_store, wrong_local_clock):
    postgres_store.store_document("a", "x", title="T")
    postgres_store.store_document("c/?/task", "x", title="T")

    stamps = {
        key: postgres_store.retrieve_document(key).updated_at
        for key in ("a", "a/!title", "c/1/task", "c/1/task/!title")
    }
    assert all(_close(stamp, _server_time(postgres_store)) for stamp in stamps.values()), stamps
    # A document and its metadata carry one stamp, as on every other backend.
    assert stamps["a"] == stamps["a/!title"]
    assert stamps["c/1/task"] == stamps["c/1/task/!title"]


@pytest.mark.parametrize(
    "microseconds", [0, 999, 1000, 1001, 123_456, 999_000, 999_999], ids=lambda n: f"{n}us"
)
def test_the_server_spells_a_stamp_as_this_package_does(postgres_store, microseconds):
    """Two spellings of one rule, held together: ``_stamp`` here, ``_stamp_sql`` there."""
    from datetime import UTC, datetime

    from outrage.store import _stamp
    from outrage.store_postgres import _stamp_sql

    moment = datetime(2026, 9, 21, 10, 0, 0, microseconds, tzinfo=UTC)
    spelled = query(
        postgres_store,
        f"SELECT {_stamp_sql('given.t')} FROM (SELECT %s::timestamptz AS t) AS given",
        (moment,),
    )[0][0]
    assert spelled == _stamp(moment)


def test_a_write_naming_its_time_keeps_it(postgres_store):
    """What a copy does: the source's stamp travels with the document."""
    postgres_store.store_document("a", "x", title="T", updated_at="2020-05-06T07:08:09+00:00")
    assert postgres_store.retrieve_document("a").updated_at == "2020-05-06T07:08:09+00:00"
    assert postgres_store.retrieve_document("a/!title").updated_at == "2020-05-06T07:08:09+00:00"


def test_the_store_tells_the_time_by_the_servers_clock(postgres_store, wrong_local_clock):
    told = postgres_store.now("anything")
    assert _close(told, _server_time(postgres_store))
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d{3})?\+00:00", told)


def test_a_watermark_from_the_server_guards_a_write_this_machine_would_miss(
    postgres_store, monkeypatch
):
    """The hole itself, in the direction that loses work: this machine's clock ahead.

    A watermark from a clock ahead of the stamps is later than a write made
    after the look, and the guarded delete goes ahead over it.
    """
    monkeypatch.setattr(store_module, "_now", lambda: "2099-01-01T00:00:00+00:00")
    looked = postgres_store.now("a")
    time.sleep(1.1)
    postgres_store.store_document("a/b", "written after the look")
    with pytest.raises(store_module.ChangedSinceError):
        postgres_store.delete("a", recursive=True, unchanged_since=looked)


# -- round trips -------------------------------------------------------------


class _RoundTrips:
    """A TCP proxy in front of the test server that counts round trips.

    A round trip starts each time the client sends after the server has
    answered, which is what a remote server charges for; counting bytes or
    statements would miss exactly the difference that matters here, between
    statements queued together and statements each waited for.
    """

    def __init__(self, host, port):
        import socket

        self.count = 0
        self._lock = threading.Lock()
        self._target = (host, port)
        self._server = socket.create_server(("127.0.0.1", 0))
        self.port = self._server.getsockname()[1]
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self):
        import socket

        while True:
            try:
                client, _ = self._server.accept()
            except OSError:
                return
            upstream = socket.create_connection(self._target)
            last = {"side": None}
            for src, dst, side in ((client, upstream, "client"), (upstream, client, "server")):
                threading.Thread(
                    target=self._pump, args=(src, dst, side, last), daemon=True
                ).start()

    def _pump(self, src, dst, side, last):
        while True:
            try:
                data = src.recv(65536)
            except OSError:
                data = b""
            if not data:
                try:
                    dst.close()
                except OSError:
                    pass
                return
            with self._lock:
                if side == "client" and last["side"] != "client":
                    self.count += 1
                last["side"] = side
            try:
                dst.sendall(data)
            except OSError:
                return

    def close(self):
        self._server.close()


@pytest.fixture
def counted_store(tmp_path, postgres_service):
    """An open store whose connection goes through :class:`_RoundTrips`, and the counter."""
    psycopg = pytest.importorskip("psycopg")
    _path, service, schema = postgres_service
    parameters = psycopg.conninfo.conninfo_to_dict(postgres_dsn())
    proxy = _RoundTrips(parameters.get("host", "localhost"), int(parameters.get("port", 5432)))
    parameters.update(host="127.0.0.1", port=str(proxy.port), options=f"-csearch_path={schema}")
    path = tmp_path / "counted.conf"
    written = "\n".join(f"{name}={value}" for name, value in sorted(parameters.items()))
    path.write_text(f"[{service}]\n{written}\n", encoding="utf-8")
    try:
        with PostgresStore(tmp_path / "counted", filename=path, service=service) as opened:
            opened.store_document("c/1/task", "x")
            yield opened, proxy
    finally:
        proxy.close()


@pytest.mark.parametrize(
    ("operation", "trips"),
    [
        (lambda s: s.store_document("a", "x"), 1),
        (lambda s: s.store_document("a", "x", title="T", contents="C"), 1),
        (lambda s: s.store_document("c/?/task", "x", title="T"), 3),
        (lambda s: s.delete("c/1/task"), 2),
    ],
    ids=["write", "write-with-metadata", "allocate", "delete"],
)
def test_a_write_costs_the_round_trips_it_has_to(counted_store, operation, trips):
    """``BEGIN`` and ``COMMIT`` ride with the statements beside them.

    The rest is what each operation cannot avoid: a write reads nothing back,
    an allocation waits for its walk and then its claim, and a delete waits
    for the keys it took. psycopg's own transaction block would add two to
    each, and pass every other test.
    """
    opened, proxy = counted_store
    before = proxy.count
    operation(opened)
    assert proxy.count - before == trips


def test_a_write_that_fails_leaves_no_transaction_open(postgres_store):
    """Rolled back by hand, since ``BEGIN`` is: a failure inside must not strand one."""
    psycopg = pytest.importorskip("psycopg")
    postgres_store.store_document("a", "x", updated_at="2026-12-01T00:00:00+00:00")
    with pytest.raises(store_module.ChangedSinceError):
        postgres_store.delete("a", unchanged_since="2026-06-01T00:00:00+00:00")
    assert postgres_store._conn.info.transaction_status == psycopg.pq.TransactionStatus.IDLE
    query(postgres_store, f"UPDATE {SCHEMA_TABLE} SET write_floor = %s", (SCHEMA_VERSION + 1,))
    with pytest.raises(ReadOnlyStoreError):
        postgres_store.store_document("b", "x")
    assert postgres_store._conn.info.transaction_status == psycopg.pq.TransactionStatus.IDLE


# -- the write floor, at the server ----------------------------------------


def test_a_session_opened_before_the_floor_rose_is_refused_by_the_server(postgres_store):
    """What catches a server started before a migration: its own decision still says yes."""
    postgres_store.store_document("a", "one")
    query(
        postgres_store,
        f"UPDATE {SCHEMA_TABLE} SET version = %s, write_floor = %s",
        (SCHEMA_VERSION + 1, SCHEMA_VERSION + 1),
    )
    assert postgres_store.compatibility.writable, "the refusal must be the server's, not ours"

    with raises_rendered(ReadOnlyStoreError, "only a build that knows version"):
        postgres_store.store_document("a", "two")
    # Learned from the refusal, so the next write is refused here without asking.
    assert postgres_store.compatibility.writable is False
    assert postgres_store.stored == SchemaVersion(SCHEMA_VERSION + 1, 1, SCHEMA_VERSION + 1)
    assert postgres_store.retrieve_document("a").content == "one"


def test_a_delete_is_refused_by_the_server_too(postgres_store):
    postgres_store.store_document("a", "one")
    query(postgres_store, f"UPDATE {SCHEMA_TABLE} SET write_floor = %s", (SCHEMA_VERSION + 1,))

    with raises_rendered(ReadOnlyStoreError, "cannot delete"):
        postgres_store.delete("a")
    assert postgres_store.exists("a")


def test_a_session_that_declares_no_build_is_not_the_floors_business(
    postgres_store, postgres_service
):
    """``psql``, or an operator's repair: the floor is about outrage builds."""
    query(postgres_store, f"UPDATE {SCHEMA_TABLE} SET write_floor = %s", (SCHEMA_VERSION + 1,))
    with _outsider(postgres_service) as conn:
        conn.execute(
            "INSERT INTO documents (key, doc_key, parent, content, updated_at, sort_key) "
            "VALUES ('x', 'x', '', 'by hand', 'now', 'x')"
        )
    assert postgres_store.retrieve_document("x").content == "by hand"


# -- the module itself -----------------------------------------------------


def test_the_backend_imports_no_driver_at_module_scope():
    """``psycopg`` is an extra, so importing the module must not need it.

    The same rule ``pgservice`` is held to and for a stronger reason: this
    module is imported by the registry the moment a mount names the backend,
    and an install without the extra has to answer in a sentence rather than
    raise ``ModuleNotFoundError`` at whoever is watching.
    """
    from outrage import store_postgres

    source = pathlib.Path(store_postgres.__file__).read_text(encoding="utf-8")
    lines = [line for line in source.splitlines() if line.startswith("import psycopg")]
    assert not lines, f"psycopg is imported at module scope: {lines}"


# -- maintenance -------------------------------------------------------------


def _root_of(tmp_path, path):
    """``--dir`` and ``--store`` naming a PostgreSQL store as the root."""
    return ("--dir", str(tmp_path / "dir"), "--store", f"{path},type=postgres")


def test_check_reports_the_version_and_floors_schema_status_does(tmp_path, postgres_store):
    """One decision behind both reports, so a check says what ``status`` says."""
    path = postgres_store.path
    postgres_store.store_document("a", "one", title="A")
    postgres_store.store_document("a", "two")

    status, output = run("check", *_root_of(tmp_path, path))

    assert status == 0
    state = postgres_store.schema_state()
    assert f"format {SCHEMA_VERSION}, 1 documents, 1 metadata" in output
    assert f"schema {state.schema}" in output
    assert f"floors read {state.stored.read_floor} write {state.stored.write_floor}" in output
    assert f"this build {MIN_SCHEMA_VERSION} to {SCHEMA_VERSION}" in output
    assert f"on open read and write at {SCHEMA_VERSION}" in output
    assert "archive 1 rows" in output
    trigger_count = len(store_postgres.TRIGGER_NAMES)
    assert f"triggers {trigger_count} of {trigger_count}" in output
    assert "nothing wrong" in output


def test_check_never_shows_the_password(tmp_path, postgres_service):
    secret = "planted-secret-51c2"
    path = service_file_like(tmp_path, postgres_service, password=secret)
    run("schema", "create", *_root_of(tmp_path, path))

    for command in (("check",), ("check", "--repair"), ("backup", "--dry-run"), ("backup",)):
        status, output = run(*command, *_root_of(tmp_path, path))
        assert status == 0, command
        assert secret not in output, command


@pytest.mark.parametrize("command", [("check",), ("backup",)])
def test_a_maintenance_command_on_an_empty_schema_is_refused_and_leaves_it_empty(
    tmp_path, postgres_service, capsys, command
):
    """Asked about a store, never for one: a check that created it would pass."""
    path, _service, schema = postgres_service

    status, _output = run(*command, *_root_of(tmp_path, path))

    assert status == 1
    assert "there is no outrage store in schema" in capsys.readouterr().err
    assert tables_in(schema) == []


def test_a_store_that_is_its_own_backends_to_find_is_not_looked_for_in_the_directory(
    tmp_path, postgres_store
):
    """The fifth pre-open site: ``check`` resolved the service file against ``--dir``.

    An absolute service file was refused as a store file that is an absolute
    path, before the backend was ever asked.
    """
    assert postgres_store.path.is_absolute()
    status, _output = run("check", *_root_of(tmp_path, postgres_store.path))
    assert status == 0


def _set_numbers(store, version, read_floor, write_floor):
    query(
        store,
        f"UPDATE {SCHEMA_TABLE} SET version = %s, read_floor = %s, write_floor = %s",
        (version, read_floor, write_floor),
    )


def test_a_newer_store_this_build_may_write_is_not_reported_as_too_new(tmp_path, postgres_store):
    """A managed schema's version is judged by its floors, not against this build's.

    The generic check reads a store from a newer build as one it cannot read,
    which is the right answer for a file and the wrong one here.
    """
    _set_numbers(postgres_store, SCHEMA_VERSION + 1, MIN_SCHEMA_VERSION, SCHEMA_VERSION)

    status, output = run("check", *_root_of(tmp_path, postgres_store.path))

    assert status == 0
    assert "newer version of outrage" not in output
    assert "nothing wrong" in output


def test_a_store_this_build_may_only_read_is_a_note_rather_than_a_fault(tmp_path, postgres_store):
    _set_numbers(postgres_store, SCHEMA_VERSION + 1, SCHEMA_VERSION, SCHEMA_VERSION + 1)

    status, output = run("check", *_root_of(tmp_path, postgres_store.path))

    assert status == 0
    assert f"on open read only at {SCHEMA_VERSION}" in output
    assert "note: this build may read the store but not write it" in output


@pytest.mark.parametrize(
    "how", ["DROP TRIGGER {name} ON documents", "ALTER TABLE documents DISABLE TRIGGER {name}"]
)
def test_a_missing_or_disabled_trigger_is_reported_and_left_alone(
    tmp_path, postgres_store, postgres_service, how
):
    """The one storage fault nothing fails on: a write simply stops being archived."""
    name = "outrage_archive_update"
    with _outsider(postgres_service) as outsider:
        outsider.execute(how.format(name=name))

    status, output = run("check", "--repair", *_root_of(tmp_path, postgres_store.path))

    assert status == 1
    assert "warning: triggers the store is kept by are missing or disabled" in output
    assert name in output
    assert "nothing to repair" in output
    trigger_count = len(store_postgres.TRIGGER_NAMES)
    assert f"triggers {trigger_count - 1} of {trigger_count}" in output


def test_every_trigger_the_store_creates_is_one_the_check_looks_for(postgres_store):
    """The names are read out of the statements that create them, so they cannot drift."""
    created = query(
        postgres_store,
        "SELECT t.tgname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = %s AND NOT t.tgisinternal",
        (postgres_store.schema,),
    )
    assert sorted(row[0] for row in created) == sorted(store_postgres.TRIGGER_NAMES)


def test_repair_does_nothing_and_says_so(postgres_store):
    assert postgres_store.repair() == []


def _written(opened):
    """Every row a store holds, as ``(key, content, format, updated_at)``."""
    return sorted(
        (row.key, opened.retrieve_document(row.key).content) for row in opened.audit_rows()
    )


def test_a_backup_is_a_sqlite_store_holding_every_row_and_every_version(tmp_path, postgres_store):
    postgres_store.store_document(
        "a/b", "one", title="Title", updated_at="2026-09-01T10:00:00+00:00"
    )
    postgres_store.store_document("a/b", "two", updated_at="2026-09-02T10:00:00+00:00")
    postgres_store.store_document("c", "three")

    result = postgres_store.backup(tmp_path / "copy.sqlite")

    assert result.path == (tmp_path / "copy.sqlite").resolve()
    assert result.documents == 3
    assert result.integrity == "ok"
    # One file, so it can be carried to a machine that cannot reach the server.
    assert sorted(p.name for p in tmp_path.iterdir() if p.name.startswith("copy")) == [
        "copy.sqlite"
    ]
    with SqliteStore(tmp_path, filename="copy.sqlite") as copy:
        assert _written(copy) == _written(postgres_store)
        for key in ("a/b", "a/b/!title", "c"):
            assert (
                copy.retrieve_document(key).updated_at
                == postgres_store.retrieve_document(key).updated_at
            )
        archived = copy._conn.execute(
            "SELECT key, content, updated_at FROM document_archive"
        ).fetchall()
    assert [tuple(row) for row in archived] == [("a/b", "one", "2026-09-01T10:00:00+00:00")]


def test_a_backups_default_name_is_a_sqlite_file_in_the_store_directory(tmp_path, postgres_store):
    """Not ``.conf``: the store's ``path`` is the service file, and the copy is not one."""
    target = postgres_store.backup_path(None, overwrite=False)
    assert target.parent == (tmp_path / "dir" / "backups").resolve()
    assert target.suffix == ".sqlite"


def test_a_backup_onto_the_service_file_is_refused(postgres_store):
    with pytest.raises(store_module.BackupError) as raised:
        postgres_store.backup(postgres_store.path, overwrite=True)
    assert raised.value.code == "backup-is-the-store"
    assert "[" in postgres_store.path.read_text(encoding="utf-8")


def test_a_backup_is_one_snapshot_whatever_is_written_while_it_reads(
    tmp_path, postgres_store, postgres_service, monkeypatch
):
    """Several devices write this store, so a copy has to be of one moment.

    A write committed between the two tables' reads lands in neither: the
    snapshot was taken before it. And the copy is verified against that
    snapshot rather than the live store, or the write would fail it.
    """
    path, service, _schema = postgres_service
    postgres_store.store_document("a", "one")
    streamed = PostgresStore._streamed

    def interrupted(self, table, name):
        if name == "archive":
            with PostgresStore(tmp_path / "other", filename=path, service=service) as other:
                other.store_document("a", "two")
                other.store_document("b", "new")
        yield from streamed(self, table, name)

    monkeypatch.setattr(PostgresStore, "_streamed", interrupted)
    result = postgres_store.backup(tmp_path / "copy.sqlite")

    assert result.documents == 1
    with SqliteStore(tmp_path, filename="copy.sqlite") as copy:
        assert copy.retrieve_document("a").content == "one"
        assert not copy.exists("b")
        assert copy._conn.execute("SELECT count(*) FROM document_archive").fetchone()[0] == 0


def test_a_backup_that_fails_leaves_no_file_and_no_transaction(
    tmp_path, postgres_store, monkeypatch
):
    postgres_store.store_document("a", "one")

    def broken(self, table, name):
        raise OSError("disk full")
        yield  # pragma: no cover - makes this a generator

    monkeypatch.setattr(PostgresStore, "_streamed", broken)
    with pytest.raises(store_module.BackupError) as raised:
        postgres_store.backup(tmp_path / "copy.sqlite")

    assert raised.value.code == "backup-unwritable"
    assert not (tmp_path / "copy.sqlite").exists()
    idle = pytest.importorskip("psycopg").pq.TransactionStatus.IDLE
    assert postgres_store._conn.info.transaction_status == idle


def test_backup_on_the_command_line_names_the_store_by_where_it_is(tmp_path, postgres_store):
    postgres_store.store_document("a", "one")

    status, output = run("backup", *_root_of(tmp_path, postgres_store.path))

    assert status == 0
    assert "backed up service=outrage" in output
    assert f"schema={postgres_store.schema}" in output
    assert str(postgres_store.path) not in output.splitlines()[0].split(" to ")[0]
    assert "1 rows" in output


def test_a_postgres_mount_is_checked_and_backed_up_by_mount_point(tmp_path, postgres_service):
    """What the mount point is for here: the store has no file to name.

    ``--store`` would have to name the service file, which is a connection's
    configuration rather than the store, and says nothing about which entry
    of it or which schema. John's call, 2026-09-22.
    """
    path, service, schema = postgres_service
    directory = str(tmp_path / "dir")
    mount = ("--dir", directory, "--mount", f"shared={path},type=postgres,service={service}")
    run("schema", "create", "shared", *mount)
    run("set", "shared/note", "--content", "on the server", *mount)

    status, output = run("check", "shared", *mount)
    assert status == 0
    assert f"schema {schema}" in output
    assert "1 documents" in output

    status, output = run("backup", "shared", "--to", str(tmp_path / "copy.sqlite"), *mount)
    assert status == 0
    with SqliteStore(tmp_path, filename="copy.sqlite") as copy:
        # The store's own keys, without the mount point: a mount is where the
        # store hangs in somebody's namespace, not part of what it holds.
        assert copy.retrieve_document("note").content == "on the server"


def test_check_heads_its_report_with_where_the_store_is(tmp_path, postgres_store):
    """Not the service file, which is the connection's configuration, and
    which the report's heading would otherwise present as the store."""
    postgres_store.store_document("a", "one")

    status, output = run("check", *_root_of(tmp_path, postgres_store.path))

    assert status == 0
    heading = output.splitlines()[0]
    assert heading.startswith("service=outrage ")
    assert f"schema={postgres_store.schema} (postgres)" in heading
    assert str(postgres_store.path) not in heading


def test_a_postgres_mount_written_in_the_table_is_named_the_same_way(tmp_path, postgres_service):
    """The spliced line, so a mount nobody typed is as nameable as one typed."""
    path, _service, schema = postgres_service
    directory = tmp_path / "dir"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "mounts.toml").write_text(
        f'[mount]\nshared = "{path},type=postgres"\n', encoding="utf-8"
    )
    run("schema", "create", "shared", "--dir", str(directory))

    status, output = run("check", "shared", "--dir", str(directory))

    assert status == 0
    assert f"schema {schema}" in output


def test_the_root_of_a_line_with_a_postgres_mount_is_still_the_root(tmp_path, postgres_service):
    """A named mount is one store; nothing here acts across the table."""
    path, _service, schema = postgres_service
    mount = ("--dir", str(tmp_path / "dir"), "--mount", f"shared={path},type=postgres")
    run("schema", "create", "shared", *mount)
    run("set", "local/note", "--content", "in the file", *mount)

    status, output = run("check", *mount)

    assert status == 0
    assert "(sqlite)" in output
    assert schema not in output


# -- the mount tool and the command line, reached over a connection ---------


def test_the_mount_tool_names_the_entry_to_connect_with(tmp_path, postgres_service):
    """``service`` on the tool, which until it existed left an MCP caller
    only the ``[outrage]`` entry of any file."""
    import anyio

    from outrage.remount import Live
    from outrage.server import build_server

    path, _service, _schema = postgres_service
    text = path.read_text(encoding="utf-8").replace("[outrage]", "[shared]")
    path.write_text(text, encoding="utf-8")
    directory = tmp_path / "base"
    root = SqliteStore(directory, filename="outrage.sqlite")
    with Live(MountedStore({"": root}), directory=directory) as live:
        server = build_server(live)
        arguments = {"key": "pg", "file": str(path), "type": "postgres", "service": "shared"}
        result = anyio.run(server.call_tool, "mount", arguments)
        assert not result.is_error, result.content
        mounted = {one["mount"]: one for one in result.structured_content["mounts"]}
        assert mounted["pg"]["target"]["service"] == "shared"

        anyio.run(server.call_tool, "store_document", {"key": "pg/a", "content": "hello"})
        read = anyio.run(server.call_tool, "read_document", {"key": "pg/a"})
        assert read.structured_content["content"] == "hello"


def test_a_write_from_the_command_line_says_where_on_the_server_it_went(tmp_path, postgres_service):
    """Not "in" the service file, which holds the connection and not the text."""
    path, _service, schema = postgres_service

    status, output = run(
        "set",
        "--dir",
        str(tmp_path / "dir"),
        "--store",
        f"{path},type=postgres",
        "a",
        "--content",
        "hello",
    )

    assert status == 0
    assert f"schema={schema}" in output
    assert str(path) not in output
