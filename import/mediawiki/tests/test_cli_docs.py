"""The generated command-line document beside the README.

It is rendered by the repository's own `tools/render_cli.py`, the renderer that
writes outrage's `cli.md`, so the two stay in one shape. That reaches outside
this distribution, which is acceptable for a test and nothing else: the
document is only ever built from the checkout.
"""

from __future__ import annotations

import sys
from pathlib import Path

from outrage_mediawiki.cli import parser

DISTRIBUTION = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DISTRIBUTION.parents[1] / "tools"))

import render_cli  # noqa: E402

TITLE = "The mediawiki-import command line"


def test_the_cli_document_is_not_stale():
    """`make -C docs documents` rewrites it; run that after changing the parser."""
    written = (DISTRIBUTION / "cli.md").read_text(encoding="utf-8")
    assert written == render_cli.render(parser(), TITLE)


def test_every_option_is_explained_and_no_default_is_left_unexpanded():
    rendered = render_cli.render(parser(), TITLE)

    options = [line for line in rendered.splitlines() if line.startswith("- `--")]
    assert options, "no options were rendered"
    assert all(not line.endswith("` - ") for line in options), "an option has no help"
    assert "%(" not in rendered
