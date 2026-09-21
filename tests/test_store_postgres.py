"""The PostgreSQL backend's own half: the connection, the schema, the version.

What a store *does* is ``test_store.py``, asked of every backend that can be
written, and this backend does not answer it yet -- the operations are steps 5
to 7 of ``plans/postgres/build``. What is here is step 4, and all of it is
about the storage rather than about the namespace: where the tables are put,
how the order is declared, what the three numbers in ``outrage_schema`` mean,
and which of them turn a store into one this build may read and not write.

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
import threading
import time

import pytest

from conftest import in_threads, postgres_dsn, raises_rendered
from outrage import messages, pgservice
from outrage import store as store_module
from outrage.cli import main
from outrage.errors import OutrageError
from outrage.mounts import open_mounts
from outrage.store import BackendError, ReadOnlyStoreError, SchemaVersion, StoreFileError
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

pytestmark = pytest.mark.postgres


def query(store, statement, parameters=()):
    """One statement against the store's own connection, for asking the server."""
    with store._transaction() as cursor:
        cursor.execute(statement, parameters)
        return cursor.fetchall() if cursor.description else []


@pytest.fixture
def registered(monkeypatch):
    """``type=postgres`` made spellable for the length of one test.

    The backend is deliberately out of the registry until its operations are
    built -- ``test_the_backend_is_not_registered_until_its_operations_are_built``
    at the end of this file is the guard -- and this is the one place that
    steps around it. What needs it is the half of the work that is about the
    *schema* and the *mount* rather than about any operation: a tolerant
    startup and ``outrage schema``, neither of which reads or writes a
    document.
    """
    monkeypatch.setitem(store_module._BACKENDS, "postgres", (".store_postgres", "PostgresStore"))


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


def test_a_server_that_is_down_leaves_the_other_mounts_working(tmp_path, registered):
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


# -- the command line ------------------------------------------------------


def test_schema_status_reports_an_empty_schema_without_filling_it(
    tmp_path, postgres_service, registered
):
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


def test_schema_create_then_status_reports_the_store(tmp_path, postgres_service, registered):
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
    tmp_path, postgres_service, registered, capsys
):
    path, _service, _schema = postgres_service
    where = ("--dir", str(tmp_path / "dir"), "--mount", f"shared={path},type=postgres")
    run("schema", "create", "shared", *where)

    status, _output = run("schema", "create", "shared", *where)

    assert status == 1
    assert "already holds an outrage store" in capsys.readouterr().err


def test_schema_status_says_what_this_build_would_do_with_a_store_it_cannot_use(
    tmp_path, postgres_service, registered
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


# -- the module itself -----------------------------------------------------


def test_the_backend_is_not_registered_until_its_operations_are_built():
    """Step 8's job, and the reason a half-built backend is safe to have here.

    Nothing can spell ``type=postgres`` in a mount while the operations raise,
    so the skeleton cannot be reached by a configuration. This is the guard
    that says so, and it is the one test here that should be *deleted* at step
    8 rather than changed.
    """
    from outrage import store as store_module

    assert "postgres" not in store_module._BACKENDS
    assert "postgres" not in store_module.backend_names()


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
