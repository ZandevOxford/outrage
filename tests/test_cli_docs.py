"""The generated command-line documentation and its renderer."""

from __future__ import annotations

import sys
from pathlib import Path

from outrage import shipped
from outrage.cli import argument_parser

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import render_cli  # noqa: E402


def test_argument_parser_exposes_a_fresh_complete_parser():
    first = argument_parser()
    second = argument_parser()

    assert first is not second
    assert first.parse_args(["get", "a"]).command == "get"


def test_the_cli_document_is_not_stale():
    assert (shipped.tree() / "cli.md").read_text() == render_cli.render(argument_parser())


def test_usage_has_a_heading_instead_of_argparses_label():
    rendered = render_cli.render(argument_parser())

    assert "## Usage\n\n```text\noutrage " in rendered
    assert "### Usage\n\n```text\noutrage init " in rendered
    assert "usage: " not in rendered
