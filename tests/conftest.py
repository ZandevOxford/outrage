"""Shared test helpers.

Not to be confused with the ``conftest.py`` at the repository root, which is a
different job entirely: that one decides **which copy of outrage** the suite
imports, before anything imports it, and holds no helpers. This one holds only
helpers and touches no paths.

``raises_rendered`` exists because an error no longer carries its own message.
``pytest.raises(cls, match=...)`` matches against ``str(exc)``, which is now a
developer rendering - the class, the code and the details - so a test that
wants to assert what a *person* reads has to render it the way a front end
does. See :mod:`outrage.messages`.

Same call shape as ``pytest.raises`` so a test reads the way it did, and it
still yields the ``ExceptionInfo``, so a test that also wants the code or the
details can have them.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import re
import threading
import uuid
from collections.abc import Iterator
from typing import Any

import pytest

from outrage import messages


@contextlib.contextmanager
def raises_rendered(
    error: type[BaseException], match: str | None = None, *, name: Any = None
) -> Iterator[pytest.ExceptionInfo[Any]]:
    """Assert ``error`` is raised, and that its **rendered** message matches.

    ``name`` is passed through to :func:`outrage.messages.render`, for the tests
    that care which front end is doing the naming.
    """
    with pytest.raises(error) as raised:
        yield raised

    if match is None:
        return
    rendered = messages.render(raised.value, name=name)
    assert re.search(match, rendered), f"{match!r} does not match {rendered!r}"


def in_threads(work, threads=6):
    """Run ``work(i)`` in parallel, re-raising whatever any thread raised.

    Shared because concurrency is asked about from two sides: whether the store
    stays correct under parallel callers (``test_store.py``) and whether a
    SQLite connection stays on the thread that opened it
    (``test_store_sqlite.py``). One helper, so the two cannot drift into
    testing slightly different things.
    """
    failures = []

    def run(i):
        try:
            work(i)
        except BaseException as exc:  # noqa: BLE001 - reported below
            failures.append(exc)

    workers = [threading.Thread(target=run, args=(i,)) for i in range(threads)]
    for t in workers:
        t.start()
    for t in workers:
        t.join()
    if failures:
        raise failures[0]


# -- comparing two stores -------------------------------------------------
#
# One corpus in two stores and every answer asserted equal is how a second
# implementation of ``Store`` is checked against a live oracle rather than
# against expectations written down twice. Two of them use it now -- the
# pyarrow backend against SQLite, and a three-store mount table against the one
# store holding the same corpus -- so it lives here rather than in either,
# which is the same argument ``in_threads`` above makes.


def answers_alike(one, other, call):
    """Put ``call`` to both stores and require the same answer, exception or not.

    Exceptions are compared as a rendered type and code rather than re-raised,
    because "SQLite raises and pyarrow returns an empty page" is exactly the
    kind of disagreement this is looking for, and a test that let the first one
    propagate would report it as a failure of the oracle.
    """

    def answer(store):
        try:
            return call(store)
        except Exception as exc:  # noqa: BLE001 - the answer, when it is one
            return type(exc).__name__, getattr(exc, "code", str(exc))

    left, right = answer(one), answer(other)
    assert left == right


def page_facts(page):
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


def walk_level(store, key):
    """A whole level, two keys at a time, with each page's totals."""
    seen, totals, cursor = [], [], None
    while True:
        page = store.list_keys(key, limit=2, cursor=cursor)
        seen += [(e.key, e.kind, e.size, e.format) for e in page.items]
        totals.append((page.total, page.total_chars))
        if page.next_cursor is None:
            return seen, totals
        cursor = page.next_cursor


def walk_documents(store, subtree, key_range, meta, **caps):
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


def long_options(parser: argparse.ArgumentParser) -> set[str]:
    """Every long option the command line takes, subcommands included.

    Read from the parser the way ``tools/render_cli.py`` reads it, because the
    parser is the only honest answer to "is that a flag": a list here would be
    a second place to remember one. Shared, because two suites ask it of two
    different kinds of sentence -- an error spelled by ``cli._flag`` and a note
    a command line's own table writes out -- and the question is the same.
    """
    found = set()
    for action in parser._actions:
        found.update(option for option in action.option_strings if option.startswith("--"))
        # A subparsers action holds its commands in a mapping; `choices` on an
        # ordinary option is the tuple of values it accepts, and holds no parser.
        choices = getattr(action, "choices", None)
        if isinstance(choices, dict):
            for inner in choices.values():
                if isinstance(inner, argparse.ArgumentParser):
                    found |= long_options(inner)
    return found


# -- a PostgreSQL server, where the machine running the suite has one --------

#: Where the suite looks for a server. A DSN rather than a service file,
#: because it is one line somebody exports and because every other tool takes
#: one; the fixtures below turn it into the service file the backend reads, so
#: that the connection path under test is the one a user takes.
POSTGRES_DSN_VARIABLE = "OUTRAGE_TEST_POSTGRES"


def postgres_dsn() -> str | None:
    """The DSN the suite was given, or None where it was given none.

    Absence is a skip and never a failure: a machine with no PostgreSQL is a
    perfectly ordinary place to run this suite, which is the whole reason the
    ``postgres`` marker exists beside this.
    """
    return os.environ.get(POSTGRES_DSN_VARIABLE) or None


@pytest.fixture
def postgres_schema():
    """A schema name nothing else is using, dropped when the test ends.

    A schema per test rather than a database per test: creating a database is
    seconds and a schema is milliseconds, and a schema is what the backend
    puts a store in anyway -- so the isolation is the same mechanism the
    product uses rather than one invented for the suite.
    """
    dsn = postgres_dsn()
    if dsn is None:
        pytest.skip(f"{POSTGRES_DSN_VARIABLE} is not set")
    psycopg = pytest.importorskip("psycopg")
    name = f"outrage_test_{uuid.uuid4().hex[:12]}"
    yield name
    with psycopg.connect(dsn, connect_timeout=5) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                psycopg.sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                    psycopg.sql.Identifier(name)
                )
            )
        conn.commit()


@pytest.fixture
def postgres_service(tmp_path, postgres_schema):
    """A service file naming the test server, and the schema for this test.

    **The suite is handed a DSN and the backend reads a service file**, so
    this is where the two meet. Writing the file is not a convenience: the
    service file *is* the connection path -- the lookup, the validation, the
    paths resolved against the file -- and a fixture that connected from the
    DSN directly would exercise a route no user takes.

    Returns the file, the service name in it, and the schema the store will
    be in. ``options=-csearch_path=`` is libpq's own spelling for that, and it
    is what ``plans/postgres/connection-file`` tells a person to write.
    """
    psycopg = pytest.importorskip("psycopg")
    parameters = psycopg.conninfo.conninfo_to_dict(postgres_dsn())
    parameters["options"] = f"-csearch_path={postgres_schema}"
    path = tmp_path / "pg_service.conf"
    written = "\n".join(f"{name}={value}" for name, value in sorted(parameters.items()))
    path.write_text(f"[outrage]\n{written}\n", encoding="utf-8")
    return path, "outrage", postgres_schema


@pytest.fixture
def postgres_store(tmp_path, postgres_service):
    """An open store in a schema of this test's own, closed when it ends."""
    from outrage.store_postgres import PostgresStore

    path, service, _schema = postgres_service
    with PostgresStore(tmp_path / "dir", filename=path, service=service) as opened:
        yield opened
