"""The sweep that keeps a tree's `!contents` indexes current.

`tools/document_contents.py` walks a directory of documents and writes an index
beside each one, which is what puts them in the documentation build. The shipped
tree exercises the ordinary path on every run of `test_shipped.py`; what it does
not exercise is the two decisions the sweep makes about documents that should
*not* end up with an index, and the destructive one of those is worth seeing
work before it is trusted over a committed tree.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from outrage import contents
from outrage.store_files import FilesystemStore

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import document_contents  # noqa: E402

HEADED = "# One\n\nbody\n\n## Two\n\nmore\n"
PROSE = "No heading anywhere in this document, which is what a tool page is.\n"


@pytest.fixture
def tree(tmp_path):
    """A small tree holding one of each thing the sweep has to decide about."""
    with FilesystemStore(tmp_path / "documents") as store:
        store.store_document("headed", HEADED)
        store.store_document("prose", PROSE)
        store.store_document("headed/!title", "One")
        store.store_document("plain", "# Not markdown\n", format="text")
        yield store


def test_a_document_with_headings_gets_an_index(tree):
    swept = document_contents.sweep(tree)

    assert swept.written == ["headed"]
    assert tree.retrieve_document("headed/!contents").content == contents.render_contents(HEADED)


def test_a_second_run_writes_nothing(tree):
    """The property that makes this safe in a build over a committed tree.

    A sweep that rewrote every index each run would put the whole tree in every
    diff, and the one thing a reader wants from the diff -- which document
    moved -- would be the one thing it does not show.
    """
    document_contents.sweep(tree)
    swept = document_contents.sweep(tree)

    assert swept.written == []
    assert swept.unchanged == ["headed"]


def test_the_sweep_can_keep_link_targets(tree):
    linked = "# [One](https://example.test/one)\n"
    tree.store_document("linked", linked)

    swept = document_contents.sweep(tree, strip_links=False)

    assert "linked" in swept.written
    assert tree.retrieve_document("linked/!contents").content == f"{linked}0 0\n"


def test_an_index_that_no_longer_matches_is_rewritten(tree):
    """Rewritten rather than skipped, which is where this differs from titles.

    `document_titles.py` leaves a title that is already there, because a good
    title is deliberately not the document's heading. An index has no such
    freedom: there is exactly one right answer and anything else addresses the
    wrong offsets.
    """
    tree.store_document("headed/!contents", "# One\n0 0\n")

    swept = document_contents.sweep(tree)

    assert swept.written == ["headed"]
    assert tree.retrieve_document("headed/!contents").content == contents.render_contents(HEADED)


def test_a_document_without_headings_gets_nothing(tree):
    document_contents.sweep(tree)

    assert not tree.exists("prose/!contents")


def test_an_index_left_by_a_document_that_lost_its_headings_is_removed(tree):
    """The stale index this exists to prevent, in the one shape a sweep can fix.

    Every other kind of staleness is repaired by writing the current index over
    it. This one cannot be: the document has no headings left, so the correct
    index is no index, and a sweep that only ever wrote would leave the old one
    pointing into a document that has moved underneath it.
    """
    tree.store_document("prose/!contents", "# Gone\n0 0\n")

    swept = document_contents.sweep(tree)

    assert swept.removed == ["prose/!contents"]
    assert not tree.exists("prose/!contents")


def test_a_dry_run_writes_nothing_and_removes_nothing(tree):
    tree.store_document("prose/!contents", "# Gone\n0 0\n")

    swept = document_contents.sweep(tree, dry_run=True)

    assert swept.written == ["headed"]
    assert swept.removed == ["prose/!contents"]
    assert not tree.exists("headed/!contents")
    assert tree.exists("prose/!contents")


def test_metadata_and_other_formats_are_passed_over(tree):
    """A sweep is not a `make_contents` call repeated.

    `make_contents` refuses a document that is not markdown, which is right for
    somebody who named one and wrong for a walk that meets one: an HTML page in
    the tree is not an error, it is a page with no index. The `!title` beside a
    document is skipped for the same reason a title has no title.
    """
    swept = document_contents.sweep(tree)

    assert "plain" not in swept.written + swept.unchanged + swept.headless
    assert not tree.exists("headed/!title/!contents")
