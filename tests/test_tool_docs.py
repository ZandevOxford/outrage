"""The generated MCP tool documentation and its renderer."""

from __future__ import annotations

import sys
from pathlib import Path

from outrage import shipped

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import render_tools  # noqa: E402


def test_the_tool_document_is_not_stale():
    assert (shipped.tree() / "tools.md").read_text() == render_tools.render(
        render_tools.registered_tools()
    )


def test_every_registered_tool_documents_its_schema():
    tools = render_tools.registered_tools()
    rendered = render_tools.render(tools)

    assert "## `read_document`" in rendered
    assert "## `document_edit`" in rendered
    assert "## `ingest_document`" in rendered
    assert "## `make_metadata`" in rendered
    assert "- `key` (string; required) — Key to read" in rendered
    assert "- `offset` (integer; default 0; minimum 0)" in rendered
    assert "- `meta_name` (array[string] or null; default null; minimum items 1)" in rendered
    assert rendered.count("### Returns") == len(tools)
    assert "`object` with fields:" not in rendered
    assert "- `content` (string; required) — The returned document content" in rendered
    assert "- `without_meta` (MissingMeta or null; optional)" in rendered
    assert "#### `Excerpt` fields" in rendered
