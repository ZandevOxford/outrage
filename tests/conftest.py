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
import re
import threading
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
# parquet backend against SQLite, and a three-store mount table against the one
# store holding the same corpus -- so it lives here rather than in either,
# which is the same argument ``in_threads`` above makes.


def answers_alike(one, other, call):
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
