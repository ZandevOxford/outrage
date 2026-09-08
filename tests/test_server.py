"""Tests driving the tools through the MCP server's own dispatch."""

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.server.mcpserver.exceptions import ToolError
from mcp.shared.memory import create_client_server_memory_streams

import outrage
from outrage import bulk, eventlog, mountfile, shipped
from outrage import mounts as mounts_module
from outrage import server as server_module
from outrage import store as store_module
from outrage.eventlog import EventLog
from outrage.server import RequestLog, build_server, instructions, parse_args
from outrage.store_sqlite import SqliteStore

try:
    from mcp.server.mcpserver.exceptions import UnexpectedToolError
except ImportError:  # pragma: no cover - depends which SDK is installed
    # Only mcp 2.1 and later tell a crash from a deliberate failure; 2.0 wrapped
    # both as a plain ToolError and carried the text of either. `pyproject.toml`
    # asks for `mcp>=1.2` because the package itself works against all of them,
    # so the one test of that boundary has to skip rather than fail to import
    # and take the whole module with it.
    UnexpectedToolError = None


@pytest.fixture
def store(tmp_path):
    with SqliteStore(tmp_path) as opened:
        yield opened


@pytest.fixture
def server(tmp_path):
    with SqliteStore(tmp_path) as store:
        store.store_document("context/a1b2/design", "# Store schema\n\n" + "body " * 1000)
        store.store_document("context/a1b2/design/!title", "Store schema")
        store.store_document("context/c3d4/task", "Add a delete tool.")
        store.store_document("context/c3d4/task/!title", "Delete tool")
        yield build_server(store)


def call(server, name: str, **arguments: Any) -> Any:
    """Call a tool and return its structured result, failing on tool errors."""
    result = anyio.run(server.call_tool, name, arguments)
    assert not result.is_error, result.content
    return result.structured_content


def call_expecting_error(server, name: str, **arguments: Any) -> str:
    """Call a tool that should fail, returning the message the caller would see."""
    with pytest.raises(ToolError) as raised:
        anyio.run(server.call_tool, name, arguments)
    return str(raised.value)


def list_tools(server) -> dict[str, Any]:
    return {tool.name: tool for tool in anyio.run(server.list_tools)}


def test_tools_are_registered(server):
    tools = list_tools(server)
    assert set(tools) == {
        "read_document",
        "store_document",
        "ingest_document",
        "make_metadata",
        "list_keys",
        "get_documents",
        "find_documents",
        "keys_missing_meta",
        "delete_keys",
        "copy_tree",
        "document_edit",
        "info",
        "mount",
        "unmount",
    }
    # `document_edit` included, though this server was built without a store
    # directory: it writes below the system temporary directory, which always
    # exists. See `test_the_file_tool_is_offered_without_a_store_directory`.
    assert tools["read_document"].annotations.read_only_hint is True
    assert tools["delete_keys"].annotations.destructive_hint is True
    for tool in tools.values():
        assert tool.description


def test_every_tool_description_is_the_shipped_document(exporting):
    """The registered text has one source, readable through the manual too."""
    tools = list_tools(exporting)

    assert set(tools) == {
        "read_document",
        "store_document",
        "ingest_document",
        "make_metadata",
        "list_keys",
        "get_documents",
        "find_documents",
        "keys_missing_meta",
        "delete_keys",
        "copy_tree",
        "document_edit",
        "info",
        "mount",
        "unmount",
    }
    for name, tool in tools.items():
        assert tool.description == server_module.tool_description(name)


def test_unknown_arguments_are_rejected(server):
    """Guards a reach into the SDK; see server._forbid_unknown_arguments.

    Silently dropping an unknown argument is how a server running stale code
    passes for one running current code, so this failing means the server has
    quietly gone permissive again, not merely that a detail changed.
    """
    message = call_expecting_error(server, "store_document", key="a/b", content="x", nonsense=1)
    assert "nonsense" in message


def test_a_misspelled_argument_is_named_rather_than_ignored(server):
    message = call_expecting_error(server, "store_document", key="a/b", content="x", titel="typo")
    assert "titel" in message
    # The document must not have been written under a half-understood call.
    assert "nothing is stored" in call_expecting_error(server, "read_document", key="a/b")


def test_schemas_tell_clients_that_arguments_are_fixed(server):
    for tool in list_tools(server).values():
        assert tool.input_schema.get("additionalProperties") is False, tool.name


def test_known_arguments_still_pass(server):
    """The strictness must not cost the optional arguments."""
    assert call(
        server,
        "store_document",
        key="a/b",
        content="x",
        title="T",
        contents="# X",
        format="markdown",
    )
    assert call(server, "list_keys")["entries"]


def test_ingest_document_returns_a_typed_preview(server, tmp_path, monkeypatch):
    source = tmp_path / "report.docx"
    source.write_bytes(b"input")
    monkeypatch.setattr(server_module.ingest, "_convert", lambda path: ("# Report\n", "Report"))

    result = call(
        server,
        "ingest_document",
        source=str(source),
        key="reports/q1",
        dry_run=True,
    )

    assert result == {
        "source": str(source.resolve()),
        "key": "reports/q1",
        "title": "Report",
        "characters": 9,
        "format": "markdown",
        "dry_run": True,
    }
    assert "nothing is stored" in call_expecting_error(server, "read_document", key="reports/q1")


def test_ingest_document_is_absent_without_the_documents_extra(store, monkeypatch):
    """A tool whose every call would refuse is not offered at all."""
    monkeypatch.setitem(sys.modules, "markitdown", None)

    tools = list_tools(build_server(store))

    assert "ingest_document" not in tools
    assert "store_document" in tools


def test_the_documentation_generator_gets_every_tool_regardless(store, monkeypatch):
    """`all_tools` documents the server rather than the host it was built on."""
    monkeypatch.setitem(sys.modules, "markitdown", None)

    tools = list_tools(build_server(store, all_tools=True, info_tool=False))

    assert "ingest_document" in tools
    assert tools["ingest_document"].description == server_module.tool_description("ingest_document")
    # The other tool that can be absent, and absent here because this server
    # was told to withhold it: the documentation still describes it.
    assert "info" in tools


def test_info_reports_the_environment_the_stores_and_the_log(tmp_path):
    """What a session cannot see from the outside, over a table of two."""
    with SqliteStore(tmp_path, filename="ref.sqlite") as reference:
        reference.store_document("asyncio", "the reference")
    log = EventLog(tmp_path / "log.jsonl", content="none")
    with mounts_module.open_mounts(tmp_path, read_only_specs=["ref=ref.sqlite"]) as table:
        server = build_server(table, log, tmp_path, mount_config=[str(tmp_path / "mounts.toml")])
        result = call(server, "info")

    assert result["version"] == outrage.__version__
    assert result["python"] == sys.executable
    assert result["prefix"] == sys.prefix
    assert result["directory"] == str(tmp_path.resolve())
    assert result["mount_config"] == [str((tmp_path / "mounts.toml").resolve())]
    assert result["log"] == str((tmp_path / "log.jsonl").resolve())
    assert result["log_content"] == "none"
    assert result["mounts"] == [
        {
            "mount": "/",
            "path": str((tmp_path / "store.sqlite").resolve()),
            "kind": "root",
            "read_only": False,
        },
        {
            "mount": "ref",
            "path": str((tmp_path / "ref.sqlite").resolve()),
            "kind": "read-only mount",
            "read_only": True,
        },
    ]
    log.close()


def test_info_reports_a_mount_nobody_named(tmp_path):
    """The shipped documentation arrives with the server, and is in the answer.

    The reason the report is taken from the live table rather than from the
    argument list: a mount lent to `open_mounts` was never written on any
    command line, and is exactly the one a session is most likely to be
    confused by.
    """
    with mounts_module.open_mounts(tmp_path, attached=shipped.attached()) as table:
        result = call(build_server(table, directory=tmp_path), "info")

    mounted = {mount["mount"]: mount for mount in result["mounts"]}
    assert mounted[shipped.MOUNT_POINT]["path"] == str(shipped.tree().resolve())
    assert mounted[shipped.MOUNT_POINT]["read_only"] is True


def test_info_does_not_guess_at_a_store_directory_it_was_not_given(store):
    """None rather than the default, which would be a confident wrong answer."""
    result = call(build_server(store), "info")

    assert result["directory"] is None
    assert result["log"] is None
    assert result["log_content"] is None
    assert result["mounts"] == [
        {
            "mount": "/",
            "path": str(store.path.resolve()),
            "kind": "root",
            "read_only": False,
        }
    ]


def test_info_is_absent_when_the_server_was_started_without_it(store):
    """`--no-info`: the paths of the machine are not part of what is offered."""
    tools = list_tools(build_server(store, info_tool=False))

    assert "info" not in tools
    assert "read_document" in tools


def test_ingest_document_writes_markdown_and_title(server, tmp_path, monkeypatch):
    source = tmp_path / "report.docx"
    source.write_bytes(b"input")
    monkeypatch.setattr(server_module.ingest, "_convert", lambda path: ("# Report\n", None))

    result = call(server, "ingest_document", source=str(source), key="reports/q1")

    assert result["title"] == "report"
    assert result["title_key"] == "reports/q1/!title"
    assert call(server, "read_document", key="reports/q1")["format"] == "markdown"
    assert call(server, "read_document", key="reports/q1/!title")["content"] == "report"


def test_make_metadata_writes_contents_and_title_by_default(server):
    source = "# Store schema\n\nbody\n\n## Detail\ntext\n"
    call(server, "store_document", key="manual", content=source, format="markdown")

    result = call(server, "make_metadata", key="manual")

    detail = source.index("## Detail")
    expected = f"# Store schema\n0 0\n\n## Detail\n{detail} {detail}\n"
    assert result == {
        "source_key": "manual",
        "source_characters": len(source),
        "source_bytes": len(source.encode()),
        "contents_key": "manual/!contents",
        "headings": 2,
        "contents_characters": len(expected),
        "title_key": "manual/!title",
        "title": "Store schema",
    }
    assert call(server, "read_document", key="manual/!contents")["content"] == expected
    assert call(server, "read_document", key="manual/!title")["content"] == "Store schema"


def test_make_metadata_accepts_a_custom_contents_name(server):
    call(server, "store_document", key="manual", content="# Manual\n", format="markdown")

    result = call(server, "make_metadata", key="manual", metadata_name="outline")

    assert result["contents_key"] == "manual/!outline"


def test_make_metadata_refuses_two_outputs_at_the_title_key(server):
    call(server, "store_document", key="manual", content="# Manual\n", format="markdown")

    message = call_expecting_error(server, "make_metadata", key="manual", metadata_name="title")

    assert "both would be the same '!title'" in message
    assert "metadata_name" in message
    assert call_expecting_error(server, "read_document", key="manual/!title")

    result = call(server, "make_metadata", key="manual", metadata_name="title", title=False)
    assert result["contents_key"] == "manual/!title"


def test_make_metadata_can_keep_link_targets_in_contents(server):
    heading = "# [Manual](https://example.test/manual)\n"
    call(server, "store_document", key="manual", content=heading, format="markdown")

    call(server, "make_metadata", key="manual")
    assert call(server, "read_document", key="manual/!contents")["content"] == "# Manual\n0 0\n"

    call(server, "make_metadata", key="manual", strip_links=False)
    assert call(server, "read_document", key="manual/!contents")["content"] == f"{heading}0 0\n"


def test_make_metadata_indexes_html_and_prefers_its_title_element(server):
    html = (
        "<!doctype html>\n<title>Manual title</title>\n"
        "<h2><a href='/detail'><em>Detail</em></a></h2>\n"
    )
    call(server, "store_document", key="manual", content=html, format="html")

    result = call(server, "make_metadata", key="manual")

    offset = html.index("<h2>")
    assert result["headings"] == 1
    assert result["title"] == "Manual title"
    assert call(server, "read_document", key="manual/!contents")["content"] == (
        f"## Detail\n{offset} {offset}\n"
    )
    assert call(server, "read_document", key="manual/!title")["content"] == "Manual title"


def test_make_metadata_booleans_control_each_write(server):
    call(
        server,
        "store_document",
        key="title-only",
        content="# Title only",
        format="markdown",
        generate_contents=False,
    )
    call(
        server,
        "store_document",
        key="contents-only",
        content="# Contents only",
        format="markdown",
        generate_contents=False,
    )

    title_only = call(server, "make_metadata", key="title-only", contents=False)
    contents_only = call(server, "make_metadata", key="contents-only", title=False)

    assert title_only["title"] == "Title only"
    assert "contents_key" not in title_only
    assert call(server, "read_document", key="title-only/!title")["content"] == "Title only"
    assert call_expecting_error(server, "read_document", key="title-only/!contents")
    assert contents_only["contents_key"] == "contents-only/!contents"
    assert "title" not in contents_only
    assert call_expecting_error(server, "read_document", key="contents-only/!title")


def test_make_metadata_without_a_parsed_title_preserves_an_existing_one(server):
    call(
        server,
        "store_document",
        key="manual",
        content="## No document title\n",
        format="markdown",
        title="Curated title",
    )

    result = call(server, "make_metadata", key="manual", contents=False)

    assert result["title"] is None
    assert "title_key" not in result
    assert call(server, "read_document", key="manual/!title")["content"] == "Curated title"


def test_make_metadata_with_both_outputs_disabled_only_reports_the_source(server):
    source = "# Manual\n"
    call(
        server,
        "store_document",
        key="manual",
        content=source,
        format="markdown",
        generate_contents=False,
    )

    result = call(server, "make_metadata", key="manual", contents=False, title=False)

    assert result == {
        "source_key": "manual",
        "source_characters": len(source),
        "source_bytes": len(source),
    }
    assert call_expecting_error(server, "read_document", key="manual/!contents")
    assert call_expecting_error(server, "read_document", key="manual/!title")


def test_make_metadata_rejects_a_non_indexable_source_with_a_tool_message(server):
    call(server, "store_document", key="plain", content="# Plain", format="text")

    message = call_expecting_error(server, "make_metadata", key="plain")

    assert "not 'markdown'" in message
    assert "or 'html'" in message
    assert "plain" in message


def test_make_metadata_schema_defaults_to_both_outputs(server):
    tools = list_tools(server)

    assert "make_contents" not in tools
    properties = tools["make_metadata"].input_schema["properties"]
    assert properties["contents"]["default"] is True
    assert properties["title"]["default"] is True


def test_ingest_collision_is_a_tool_message_spelling_its_argument(server, tmp_path, monkeypatch):
    source = tmp_path / "report.docx"
    source.write_bytes(b"input")
    monkeypatch.setattr(server_module.ingest, "_convert", lambda path: ("new", None))
    call(server, "store_document", key="reports/q1", content="mine")

    message = call_expecting_error(server, "ingest_document", source=str(source), key="reports/q1")

    assert "overwrite" in message
    assert "--overwrite" not in message
    assert call(server, "read_document", key="reports/q1")["content"] == "mine"


def test_tool_schemas_describe_their_arguments(server):
    tool = list_tools(server)["read_document"]
    properties = tool.input_schema["properties"]
    assert tool.input_schema["required"] == ["key"]
    assert "regex" in properties["pattern"]["description"]


def test_the_conflict_rules_are_all_named_where_one_is_chosen(server):
    """A choice absent from its own argument's description is a choice nobody finds.

    `overwrite-unchanged` was added to `CONFLICTS` and to the tool's text while
    `on_conflict` went on listing the other three, so a session reading the
    argument that takes it saw three of four. The CLI lists them from `choices`
    and cannot drift; this is what keeps the schema honest instead.
    """
    described = list_tools(server)["copy_tree"].input_schema["properties"]["on_conflict"]

    for rule in store_module.CONFLICTS:
        assert rule in described["description"], rule


def test_tool_schemas_describe_their_results(exporting):
    tools = list_tools(exporting)

    for tool in tools.values():
        assert tool.output_schema["type"] == "object", tool.name
        assert tool.output_schema["additionalProperties"] is False, tool.name
        assert tool.output_schema["properties"], tool.name

    # What every read reports, in either unit. The character numbers are not
    # here: a byte-addressed read cannot say what they are and leaves them out,
    # which is the one place this result is allowed to be short of a field.
    read = tools["read_document"].output_schema
    assert read["required"] == [
        "key",
        "content",
        "format",
        "updated_at",
        "returned",
        "byte_offset",
        "total_bytes",
        "truncated",
    ]
    assert set(read["properties"]) == set(read["required"]) | {
        "offset",
        "total",
        "next_offset",
        "next_byte_offset",
    }
    assert read["properties"]["next_offset"]["description"]
    assert read["properties"]["next_byte_offset"]["description"]

    survey = tools["get_documents"].output_schema
    assert survey["properties"]["documents"]["items"] == {"$ref": "#/$defs/_ExcerptResult"}
    assert "without_meta" not in survey["required"]

    search = tools["find_documents"].output_schema
    assert search["properties"]["matches"]["items"] == {"$ref": "#/$defs/_DocumentMatchResult"}
    assert search["properties"]["next_cursor"]["description"]

    file_result = tools["document_edit"].output_schema
    assert set(file_result["required"]) == {"key", "path"}


def test_read_document(server):
    result = call(server, "read_document", key="context/c3d4/task")
    assert result["content"] == "Add a delete tool."
    assert result["truncated"] is False
    assert result["next_offset"] is None


def test_read_document_pages(server):
    first = call(server, "read_document", key="context/a1b2/design", max_chars=20)
    assert first["content"] == "# Store schema\n\nbody"
    assert first["truncated"] is True

    second = call(
        server,
        "read_document",
        key="context/a1b2/design",
        offset=first["next_offset"],
        max_chars=20,
    )
    assert second["offset"] == 20
    assert second["content"] == " body body body body"


def test_read_document_by_pattern(server):
    result = call(server, "read_document", key="context/a1b2/design", pattern="body")
    assert result["offset"] == 16


def test_read_missing_key_is_a_tool_error(server):
    assert "context/zzzz" in call_expecting_error(server, "read_document", key="context/zzzz")


def test_invalid_key_is_a_tool_error(server):
    # `!title` used to be the example here and is the root's title since the
    # root became addressable, so the malformation has to be a real one.
    message = call_expecting_error(server, "read_document", key="context/!")
    assert "metadata name" in message


def test_a_wildcard_is_a_tool_error_when_reading(server):
    message = call_expecting_error(server, "read_document", key="context/?")
    assert "only when storing" in message


def test_argument_validation_rejects_a_negative_offset(server):
    message = call_expecting_error(server, "read_document", key="a", offset=-1)
    assert "offset" in message


def test_read_document_rejects_the_removed_length_argument(server):
    message = call_expecting_error(server, "read_document", key="a", length=1)
    assert "length" in message


def test_store_document_round_trip(server):
    stored = call(server, "store_document", key="project/notes", content="# Notes")
    assert stored == {
        "key": "project/notes",
        "stored": 7,
        "generated": False,
        "contents_key": "project/notes/!contents",
    }
    assert call(server, "read_document", key="project/notes")["content"] == "# Notes"
    assert call(server, "read_document", key="project/notes/!contents")["content"] == (
        "# Notes\n0 0\n"
    )


def test_store_document_reports_an_allocated_key(server):
    stored = call(server, "store_document", key="tmp/?", content="scratch")
    assert stored == {
        "key": "tmp/1",
        "stored": 7,
        "generated": True,
        "contents_key": "tmp/1/!contents",
    }
    assert call(server, "store_document", key="tmp/?", content="more")["key"] == "tmp/2"
    assert call(server, "read_document", key="tmp/1")["content"] == "scratch"


def test_store_document_writes_a_title_in_one_call(server):
    stored = call(server, "store_document", key="project/notes", content="# Notes", title="Notes")
    assert stored["title_key"] == "project/notes/!title"
    assert call(server, "read_document", key="project/notes/!title")["content"] == "Notes"


def test_store_document_titles_the_key_it_allocated(server):
    stored = call(server, "store_document", key="tmp/?", content="scratch", title="Scratch")
    assert (stored["key"], stored["title_key"]) == ("tmp/1", "tmp/1/!title")


def test_store_document_titles_a_metadata_namespace(server):
    call(server, "store_document", key="a/b/!changelog", content="text", title="What changed")
    title = call(server, "read_document", key="a/b/!changelog/!title")
    assert title["content"] == "What changed"


def test_store_document_writes_contents_in_one_call(server):
    stored = call(
        server,
        "store_document",
        key="project/notes",
        content="# Notes",
        contents="# Notes 0 0",
    )
    assert stored["contents_key"] == "project/notes/!contents"
    contents = call(server, "read_document", key="project/notes/!contents")
    assert contents["content"] == "# Notes 0 0"


def test_explicit_store_document_contents_take_precedence_over_generation(server):
    call(
        server,
        "store_document",
        key="project/notes",
        content="# Generated",
        contents="# Supplied",
    )

    contents = call(server, "read_document", key="project/notes/!contents")
    assert contents["content"] == "# Supplied"


def test_store_document_contents_generation_can_be_disabled(server):
    call(
        server,
        "store_document",
        key="project/notes",
        content="# Before",
        contents="# Keep me",
    )

    stored = call(
        server,
        "store_document",
        key="project/notes",
        content="# After",
        generate_contents=False,
    )

    assert "contents_key" not in stored
    contents = call(server, "read_document", key="project/notes/!contents")
    assert contents["content"] == "# Keep me"


def test_storing_metadata_does_not_generate_contents_metadata(server):
    stored = call(server, "store_document", key="project/!summary", content="# Summary")

    assert "contents_key" not in stored
    assert call_expecting_error(server, "read_document", key="project/!summary/!contents")


def test_store_document_contents_follow_the_allocated_key(server):
    stored = call(
        server,
        "store_document",
        key="tmp/?",
        content="scratch",
        contents="# Scratch",
    )
    assert (stored["key"], stored["contents_key"]) == ("tmp/1", "tmp/1/!contents")


def test_store_document_detects_json(server):
    call(server, "store_document", key="project/data", content='{"a": 1}')
    assert call(server, "read_document", key="project/data")["format"] == "json"


def test_store_document_decodes_a_json_string_encoding(server):
    stored = call(
        server,
        "store_document",
        key="a/b/!summary",
        content='"A summary saying \\"hi\\".\\nSecond line."',
        encoding="json-string",
    )
    # `stored` counts what was stored, not the longer encoded form that arrived.
    assert stored["stored"] == len('A summary saying "hi".\nSecond line.')
    assert (
        call(server, "read_document", key="a/b/!summary")["content"]
        == 'A summary saying "hi".\nSecond line.'
    )


def test_store_document_encodes_automatically_generated_contents_for_transport(server):
    stored = call(
        server,
        "store_document",
        key="manual",
        content='"# Heading"',
        format="markdown",
        encoding="json-string",
    )

    assert stored["contents_key"] == "manual/!contents"
    assert call(server, "read_document", key="manual/!contents")["content"] == ("# Heading\n0 0\n")


def test_store_document_rejects_scaffolding_under_a_json_string_encoding(server):
    message = call_expecting_error(
        server,
        "store_document",
        key="a/b/!summary",
        content='"A summary."</content>\n</invoke>\n',
        encoding="json-string",
    )
    assert "not a valid JSON string literal" in message
    # Nothing was written, so the caller can simply send it again.
    assert "nothing is stored" in call_expecting_error(server, "read_document", key="a/b/!summary")


# Six of the seven cases below had no test through the server until 2026-08-29,
# which is why a single failing test stood for a seven-way problem. Each is a
# failure a *caller* can correct, so each has to reach them as a sentence. See
# `issues/1` in the outrage store: mcp 2.1.1 withholds the text of anything that
# is not a `ToolError`, and these were bare `ValueError`s.


def test_store_document_rejects_an_unknown_encoding(server):
    message = call_expecting_error(
        server, "store_document", key="a/b", content="x", encoding="bogus"
    )
    assert "json-string" in message


def test_store_document_rejects_a_json_string_that_is_not_a_string(server):
    message = call_expecting_error(
        server,
        "store_document",
        key="a/b/!summary",
        content='{"summary": "A summary."}',
        encoding="json-string",
    )
    assert "decoded to dict" in message


def test_store_document_rejects_an_unknown_format(server):
    message = call_expecting_error(server, "store_document", key="a/b", content="x", format="bogus")
    assert "markdown" in message


def test_read_document_rejects_an_empty_pattern(server):
    message = call_expecting_error(server, "read_document", key="context/a1b2/design", pattern="")
    assert "must not be empty" in message


@pytest.mark.parametrize("tool", ["get_documents", "keys_missing_meta"])
def test_a_survey_rejects_an_empty_meta_name(server, tool):
    message = call_expecting_error(server, tool, key="context", meta_name=[])
    assert "at least 1 item" in message


@pytest.mark.skipif(
    UnexpectedToolError is None, reason="mcp 2.1 or later draws the distinction this asserts"
)
def test_a_crash_still_reaches_the_caller_with_nothing_in_it(server, monkeypatch):
    """The other half of the rule, and the reason `_reported` stays narrow.

    Every test above wants its message carried through. This one wants the
    opposite, and both come from the same distinction: a caller who can correct
    something is told what, and a bug in outrage is not described to them at all.
    Widening `_reported` to catch `ValueError` would pass all six above and
    break this one, which is exactly the trade it must not make.
    """

    def boom(*args, **kwargs):
        raise ValueError("a detail from inside outrage")

    monkeypatch.setattr(SqliteStore, "retrieve_document", boom)

    with pytest.raises(UnexpectedToolError) as raised:
        anyio.run(server.call_tool, "read_document", {"key": "context/a1b2/design"})
    assert "a detail from inside outrage" not in str(raised.value)
    assert isinstance(raised.value.__cause__, ValueError)


def test_list_keys_at_the_top_level(server):
    entries = call(server, "list_keys")["entries"]
    assert [(e["key"], e["kind"]) for e in entries] == [("context", "implicit")]


def test_list_keys_shows_subkeys_and_metadata(server):
    entries = call(server, "list_keys", key="context/c3d4")["entries"]
    assert [(e["key"], e["kind"]) for e in entries] == [("context/c3d4/task", "document")]

    entries = call(server, "list_keys", key="context/c3d4/task")["entries"]
    assert [(e["key"], e["kind"]) for e in entries] == [("context/c3d4/task/!title", "metadata")]


def test_get_documents_surveys_titles(server):
    result = call(server, "get_documents", key="context", meta_name=["title"])
    assert result["count"] == 2
    assert {d["key"]: d["content"] for d in result["documents"]} == {
        "context/a1b2/design/!title": "Store schema",
        "context/c3d4/task/!title": "Delete tool",
    }


def test_get_documents_survey_names_the_untitled(server):
    call(server, "store_document", key="context/e5f6/note", content="No title here.")
    result = call(server, "get_documents", key="context", meta_name=["title"])
    assert result["count"] == 2
    assert result["without_meta"] == {
        "total": 1,
        "total_chars": len("No title here."),
        "sample": ["context/e5f6/note"],
    }


def test_the_survey_carries_no_cursor_it_cannot_honour(server):
    call(server, "store_document", key="context/e5f6/note", content="No title here.")
    result = call(server, "get_documents", key="context", meta_name=["title"])

    # `after` resumes the documents, so a cursor here named a position in a
    # collection no argument accepts -- and being a key like any other, feeding
    # it back returned a plausible page of the wrong thing.
    assert "next_cursor" not in result["without_meta"]


def test_the_survey_says_none_missing_rather_than_going_quiet(server):
    result = call(server, "get_documents", key="context", meta_name=["title"])

    # Absent and zero are different answers, and a caller reading an absent
    # block as "none" is right only by luck.
    assert result["without_meta"] == {"total": 0, "total_chars": 0, "sample": []}


def test_get_documents_without_meta_says_nothing_about_untitled_documents(server):
    call(server, "store_document", key="context/e5f6/note", content="No title here.")
    assert "without_meta" not in call(server, "get_documents", key="context")


def test_get_documents_truncates(server):
    result = call(server, "get_documents", key="context", max_chars=10)
    assert [d["returned"] for d in result["documents"]] == [10, 10]
    assert result["documents"][0]["truncated"] is True


def test_get_documents_respects_depth(server):
    assert call(server, "get_documents", key="context", depth=1)["count"] == 0
    assert call(server, "get_documents", key="context", depth=2)["count"] == 2


def test_find_documents_searches_bodies_and_metadata(server):
    result = call(
        server,
        "find_documents",
        key="context",
        criteria=[
            {"target": "document", "match": "contains", "pattern": "delete"},
            {
                "target": "metadata",
                "meta_name": ["title"],
                "match": "line",
                "pattern": "Store schema",
            },
        ],
    )

    assert result["key"] == "context"
    assert [match["document"]["key"] for match in result["matches"]] == [
        "context/a1b2/design",
        "context/c3d4/task",
    ]
    assert result["matched"] == 2
    assert result["scanned"] == 2
    assert result["total_candidates"] == 2
    assert result["matches"][0]["witnesses"][0] == {
        "criterion": 1,
        "source_key": "context/a1b2/design/!title",
        "source": "metadata",
        "start": 0,
        "end": 12,
    }


def test_find_documents_can_return_an_empty_nonterminal_page(server):
    for number in range(3):
        call(server, "store_document", key=f"notes/{number}", content="miss")
    call(server, "store_document", key="notes/3", content="match")

    first = call(
        server,
        "find_documents",
        key="notes",
        criteria=[{"target": "document", "match": "contains", "pattern": "match"}],
        scan_limit=2,
    )
    second = call(
        server,
        "find_documents",
        key="notes",
        criteria=[{"target": "document", "match": "contains", "pattern": "match"}],
        scan_limit=2,
        after=first["next_cursor"],
    )

    assert first["matches"] == []
    assert first["next_cursor"] == "notes/1"
    assert [match["document"]["key"] for match in second["matches"]] == ["notes/3"]
    assert second["next_cursor"] is None


def test_find_documents_rejects_unknown_criterion_fields(server):
    message = call_expecting_error(
        server,
        "find_documents",
        criteria=[{"target": "document", "match": "contains", "pattern": "x", "case": "ignore"}],
    )
    assert "case" in message


def test_find_documents_renders_store_validation(server):
    message = call_expecting_error(
        server,
        "find_documents",
        criteria=[
            {
                "target": "document",
                "match": "contains",
                "pattern": "x",
                "meta_name": ["title"],
            }
        ],
    )
    assert "meta_name must be omitted" in message


def test_delete_keys_takes_metadata_with_the_document(server):
    result = call(server, "delete_keys", key="context/c3d4/task")
    assert result["deleted"] == ["context/c3d4/task", "context/c3d4/task/!title"]
    assert result["count"] == 2


def test_delete_keys_is_not_recursive_by_default(server):
    assert call(server, "delete_keys", key="context/a1b2")["count"] == 0
    assert call(server, "delete_keys", key="context/a1b2", recursive=True)["count"] == 2


def test_delete_keys_reports_what_it_kept(server):
    result = call(server, "delete_keys", key="context/a1b2")
    assert result["remaining"] == 2
    assert "recursive=true" in result["note"]


def test_delete_keys_says_nothing_extra_when_it_kept_nothing(server):
    result = call(server, "delete_keys", key="context/c3d4/task")
    assert result["count"] == 2
    assert "remaining" not in result
    result = call(server, "delete_keys", key="context/a1b2", recursive=True)
    assert "remaining" not in result


def keys_below(server, key: str) -> list[str]:
    """The documents under a key. Not the metadata: a subtree read is one or
    the other, which is the same reason a copy reads one key at a time."""
    return [entry["key"] for entry in call(server, "get_documents", key=key)["documents"]]


def titles_below(server, key: str) -> list[str]:
    surveyed = call(server, "get_documents", key=key, meta_name=["title"])
    return [entry["key"] for entry in surveyed["documents"]]


def test_copy_tree_grafts_the_whole_source_key(server):
    """The shipped contract, and what an archive wants: the key is kept."""
    result = call(server, "copy_tree", source="context/a1b2", target="archive")

    assert result["copied"] == {"wrote": 2}
    assert keys_below(server, "archive") == ["archive/context/a1b2/design"]
    # The metadata crossed with it, which is what makes the copy a copy: a
    # store arriving without its titles is one nothing can be surveyed by.
    assert titles_below(server, "archive") == ["archive/context/a1b2/design/!title"]


def test_copy_tree_reroots_onto_the_target(server):
    """What a caller moving a subtree needs: the documents at the new key."""
    call(server, "copy_tree", source="context/a1b2", target="archive", reroot=True)

    assert keys_below(server, "archive") == ["archive/design"]
    assert titles_below(server, "archive") == ["archive/design/!title"]


def test_copy_tree_reports_counts_rather_than_the_keys_it_crossed(server):
    """A copy may cross more keys than a result can hold - ``context/68`` 7.

    So the second run says two documents were skipped and does not say which,
    and the caller is told the size of what happened rather than a list that
    grows with the store.
    """
    call(server, "copy_tree", source="context/a1b2", target="archive")
    result = call(server, "copy_tree", source="context/a1b2", target="archive")

    assert result["copied"] == {"skipped": 2}
    assert result["documents"] == 2
    assert result["next_cursor"] is None
    assert "keys" not in result and "deleted" not in result


def test_copy_tree_resumes_from_the_cursor_it_returns(server):
    """The pair that makes a copy larger than one call expressible.

    The cursor is a *source* key, which is why it cannot be read off the last
    transfer: under a graft the key written is a different key.
    """
    first = call(server, "copy_tree", source="context", target="archive", limit=1)

    assert first["documents"] == 1
    assert first["next_cursor"] == "context/a1b2/design"
    assert "cursor" in first["note"]

    second = call(
        server,
        "copy_tree",
        source="context",
        target="archive",
        limit=10,
        cursor=first["next_cursor"],
    )

    assert second["documents"] == 3
    assert second["next_cursor"] is None
    assert keys_below(server, "archive") == [
        "archive/context/a1b2/design",
        "archive/context/c3d4/task",
    ]
    assert titles_below(server, "archive") == [
        "archive/context/a1b2/design/!title",
        "archive/context/c3d4/task/!title",
    ]


def test_copy_tree_dry_run_writes_nothing(server):
    result = call(server, "copy_tree", source="context/a1b2", target="archive", dry_run=True)

    assert result["copied"] == {"wrote": 2}
    assert result["dry_run"] is True
    assert keys_below(server, "archive") == []


def test_copy_tree_dry_run_reports_the_moment_to_pass_back(server):
    """The pair reads as what it is: look, then write only what has not moved."""
    looked = call(server, "copy_tree", source="context/a1b2", target="archive", dry_run=True)

    assert looked["checked_at"]
    assert "unchanged_since" in looked["note"]
    result = call(
        server,
        "copy_tree",
        source="context/a1b2",
        target="archive",
        unchanged_since=looked["checked_at"],
    )
    assert result["copied"] == {"wrote": 2}


def test_a_paged_copy_names_the_one_argument_a_resume_cannot_keep(server):
    """ "Every other argument unchanged" and a watermark cannot both hold.

    A copy carries the source's timestamps, so the page just written is itself
    a change to the target whenever the source is newer than the moment being
    measured against, and the resume the paging note recommends is refused.
    Found by running it: `context/111/findings` 4.
    """
    looked = call(server, "copy_tree", source="context/a1b2", target="archive", dry_run=True)

    paged = call(
        server,
        "copy_tree",
        source="context/a1b2",
        target="archive",
        limit=1,
        unchanged_since=looked["checked_at"],
    )

    assert paged["next_cursor"] is not None
    assert "Except unchanged_since" in paged["note"]


def test_a_paged_copy_without_a_watermark_keeps_the_short_note(server):
    result = call(server, "copy_tree", source="context/a1b2", target="archive", limit=1)

    assert result["next_cursor"] is not None
    assert "unchanged_since" not in result["note"]


def test_copy_tree_dry_run_advises_the_conflict_rule_a_watermark_works_with(server):
    """Advice that names only the time recommends the pairing the copy refuses.

    `overwrite` beside `unchanged_since` is an `InvalidArgumentError`, so a dry
    run under `overwrite` that says "pass checked_at back as unchanged_since"
    sends the caller to a failure. The test follows the sentence rather than
    matching it: whatever the note tells a caller to do has to be a call that
    lands.
    """
    looked = call(
        server,
        "copy_tree",
        source="context/a1b2",
        target="archive",
        on_conflict="overwrite",
        dry_run=True,
    )

    assert "on_conflict='overwrite-unchanged'" in looked["note"]
    result = call(
        server,
        "copy_tree",
        source="context/a1b2",
        target="archive",
        on_conflict="overwrite-unchanged",
        unchanged_since=looked["checked_at"],
    )
    assert result["copied"] == {"wrote": 2}


def test_copy_tree_dry_run_says_nothing_about_a_conflict_rule_it_does_not_need(server):
    """The default takes a watermark as it stands, so the advice stays the short one."""
    looked = call(server, "copy_tree", source="context/a1b2", target="archive", dry_run=True)

    assert "overwrite-unchanged" not in looked["note"]


def test_copy_tree_with_a_watermark_writes_nothing_when_the_target_moved(server):
    call(server, "copy_tree", source="context/a1b2", target="archive")

    message = call_expecting_error(
        server,
        "copy_tree",
        source="context/a1b2",
        target="archive",
        on_conflict="overwrite-unchanged",
        unchanged_since="2020-01-01T00:00:00Z",
    )

    assert "would act on work done since" in message


def test_copy_tree_names_the_keys_it_left_rather_than_only_counting_them(server, store):
    """A caller who gets three keys learns exactly which three to look at.

    Sampled would be worse than useless here: the whole value of the answer is
    that it is the list, and being shown two of three sends the caller looking
    for a key nothing named.
    """
    store.store_document("archive/context/a1b2/design", "mine", updated_at="2026-01-01T00:00:00Z")

    result = call(
        server,
        "copy_tree",
        source="context/a1b2",
        target="archive",
        on_conflict="overwrite-unchanged",
        unchanged_since="2026-02-01T00:00:00Z",
    )

    # Nothing has moved since the watermark, so the copy lands.
    assert result["copied"] == {"wrote": 2}
    assert "changed" not in result


def test_copy_tree_says_nothing_about_a_watermark_it_was_not_given(server):
    result = call(server, "copy_tree", source="context/a1b2", target="archive")

    assert "changed" not in result and "checked_at" not in result


def test_delete_keys_refuses_when_what_it_would_take_moved_since(server):
    message = call_expecting_error(
        server,
        "delete_keys",
        key="context/a1b2",
        recursive=True,
        unchanged_since="2020-01-01T00:00:00Z",
    )

    assert "refusing to delete" in message
    assert keys_below(server, "context/a1b2") == ["context/a1b2/design"]


def test_delete_keys_with_a_watermark_nothing_moved_since_deletes(server):
    result = call(
        server,
        "delete_keys",
        key="context/a1b2",
        recursive=True,
        unchanged_since="2099-01-01T00:00:00Z",
    )

    # context/a1b2/design and its title; the container itself holds nothing.
    assert result["count"] == 2


def test_delete_keys_dry_run_names_exactly_what_the_delete_takes(server):
    """The preview is the delete's own selection, not a second guess at it.

    Asked of the store rather than worked out above it, so the two cannot
    drift: a preview that disagrees with the run it previews is the one thing a
    preview must not do.
    """
    previewed = call(server, "delete_keys", key="context/a1b2", recursive=True, dry_run=True)

    assert previewed["dry_run"] is True
    assert keys_below(server, "context/a1b2") == ["context/a1b2/design"]

    taken = call(server, "delete_keys", key="context/a1b2", recursive=True)
    assert previewed["deleted"] == taken["deleted"]


def test_delete_keys_dry_run_reports_the_moment_to_pass_back(server):
    """The half of "look, then delete only what has not moved" a session could not get.

    The command line has printed a moment on `rm --dry-run` since the watermark
    was built and the tool reported none, so a session had to take one from a
    `copy_tree` dry run against an unrelated target, or guess at the clock.
    `context/111/findings` 3.
    """
    looked = call(server, "delete_keys", key="context/a1b2", recursive=True, dry_run=True)

    assert looked["checked_at"]
    assert "unchanged_since" in looked["note"]
    result = call(
        server,
        "delete_keys",
        key="context/a1b2",
        recursive=True,
        unchanged_since=looked["checked_at"],
    )
    assert result["count"] == len(looked["deleted"])


def test_delete_keys_dry_run_refuses_rather_than_previewing_a_refusal(server):
    """A preview of a delete that would be refused has to refuse.

    Otherwise it answers the caller's second question -- what would go -- while
    the delete it previews never happens, which reads as a plan that works.
    """
    message = call_expecting_error(
        server,
        "delete_keys",
        key="context/a1b2",
        recursive=True,
        unchanged_since="2020-01-01T00:00:00Z",
        dry_run=True,
    )

    assert "refusing to delete" in message


def test_delete_keys_says_nothing_about_a_dry_run_it_was_not_asked_for(server):
    result = call(server, "delete_keys", key="context/a1b2", recursive=True)

    assert "checked_at" not in result and "dry_run" not in result


def test_copy_tree_refuses_a_target_inside_its_source(server):
    message = call_expecting_error(server, "copy_tree", source="context", target="context/archive")

    assert "target is inside the source subtree" in message


def test_copy_tree_refuses_a_reroot_into_an_ancestor_of_its_source(server):
    """The overlap a graft is safe with and a re-root is not.

    Grafted this pair writes `context/context/a1b2/...`, outside the walk.
    Re-rooted it writes `context/...`, back inside it.
    """
    message = call_expecting_error(
        server, "copy_tree", source="context/a1b2", target="context", reroot=True
    )

    assert "source is inside the target subtree" in message
    assert call(server, "copy_tree", source="context/a1b2", target="context")["documents"] == 2


def test_copy_tree_names_the_read_only_mounts_the_copy_could_not_reach(tmp_path):
    """A count alone reads as a copy that mostly worked - ``context/68`` 7.

    There are never many mount points, so this list is bounded by something
    other than the size of the store, which is why it is a list where the
    failures are a sample.
    """
    with SqliteStore(tmp_path, filename="ref.sqlite") as reference:
        reference.store_document("asyncio", "the reference")
    with SqliteStore(tmp_path) as root:
        root.store_document("notes/ref/python", "mine")
        root.store_document("notes/plain", "mine too")
    with mounts_module.open_mounts(tmp_path, read_only_specs=["archive/ref=ref.sqlite"]) as table:
        server = build_server(table)
        result = call(server, "copy_tree", source="notes", target="archive", reroot=True)

        assert result["copied"] == {"wrote": 1, "failed": 1}
        assert result["mounts_kept"] == ["archive/ref"]
        assert result["failures"] == [
            {"key": "archive/ref/python", "reason": result["failures"][0]["reason"]}
        ]
        assert "read-only" in result["failures"][0]["reason"]
        assert "refuse a write" in result["note"]


def test_a_copy_failure_uses_the_transfer_key_as_its_outer_name():
    """The transfer has crossed the mount boundary when its error has not."""
    error = store_module.InvalidArgumentError(
        "key-is-a-directory", key="inside", path="/tmp/tree/inside"
    )
    transfers = iter([store_module.Transfer(store_module.FAILED, "ref/inside", None, error=error)])

    result = server_module._copied_result(transfers)

    assert result["failures"][0]["key"] == "ref/inside"
    assert "'ref/inside'" in result["failures"][0]["reason"]


def test_copy_tree_says_when_the_failures_it_names_are_a_sample(tmp_path, monkeypatch):
    """A sample presented as a list is a list that lies.

    The cap is what keeps the result the same size as the store grows, so what
    it costs is a caller who cannot see every failure - and the one thing that
    makes that safe is saying so.
    """
    monkeypatch.setattr(server_module, "COPY_FAILURE_SAMPLE", 1)
    with SqliteStore(tmp_path, filename="ref.sqlite") as reference:
        reference.store_document("asyncio", "the reference")
    with SqliteStore(tmp_path) as root:
        root.store_document("notes/ref/python", "mine")
        root.store_document("notes/ref/rust", "mine too")
    with mounts_module.open_mounts(tmp_path, read_only_specs=["archive/ref=ref.sqlite"]) as table:
        server = build_server(table)
        result = call(server, "copy_tree", source="notes", target="archive", reroot=True)

    assert result["copied"] == {"failed": 2}
    assert len(result["failures"]) == 1
    assert "the rest are only counted" in result["note"]


def test_parse_args():
    assert parse_args([]).directory is None
    assert parse_args(["--dir", "/tmp/x"]).directory == "/tmp/x"


def test_parse_args_leaves_logging_off():
    assert parse_args([]).log is None
    assert parse_args(["--log"]).log is eventlog.DEFAULT
    assert parse_args(["--log", "/tmp/l.jsonl"]).log == "/tmp/l.jsonl"
    assert parse_args([]).log_content == "excerpt"


def test_parse_args_offers_the_info_tool_unless_told_not_to():
    assert parse_args([]).no_info is False
    assert parse_args(["--no-info"]).no_info is True


def test_parse_args_reports_the_configuration_files_it_read(tmp_path):
    """The splice flattens the sources away, so the list is kept as it goes.

    What wants it is the `info` tool: a file that was read is where a mount is
    edited, and by the time there is a table nothing can say which files those
    were.
    """
    (tmp_path / "mounts.toml").write_text('[mount]\nteam = "team.sqlite"\n', encoding="utf-8")
    other = tmp_path / "extra.toml"
    other.write_text('[mount]\nref = "ref.sqlite"\n', encoding="utf-8")

    args = parse_args(["--dir", str(tmp_path), "--mount-config", str(other)])

    assert args.config_files == [str(tmp_path / "mounts.toml"), str(other)]
    # `--no-mount-config` is the escape from the default file, and the list
    # says so rather than naming a file whose options were never spliced in.
    assert parse_args(["--dir", str(tmp_path), "--no-mount-config"]).config_files == []


# -- the request log -------------------------------------------------------
#
# `call` above drives `server.call_tool`, which goes straight to the tool
# manager and never runs the middleware chain. So these drive a real client
# session instead: the whole reason for logging at the middleware tier is the
# calls that fail before a tool is entered, and a stub that returns whatever it
# was told to return would not be evidence of anything.


def session_calls(tmp_path, *calls, content="excerpt"):
    """Run a real client session against a logged server, and return the log."""
    log = EventLog(tmp_path / "log.jsonl", content=content)

    async def drive():
        with SqliteStore(tmp_path / "store", log=log) as store:
            store.store_document("a/b", "hello there", title="A doc")
            server = build_server(store, log)
            low = server._lowlevel_server
            async with create_client_server_memory_streams() as (client, serving):
                async with anyio.create_task_group() as tasks:
                    tasks.start_soon(
                        lambda: low.run(
                            serving[0],
                            serving[1],
                            low.create_initialization_options(),
                            raise_exceptions=True,
                        )
                    )
                    async with ClientSession(client[0], client[1]) as session:
                        await session.initialize()
                        for name, arguments in calls:
                            await session.call_tool(name, arguments)
                    tasks.cancel_scope.cancel()

    anyio.run(drive)
    log.close()
    return [json.loads(line) for line in (tmp_path / "log.jsonl").read_text().splitlines()]


def test_the_middleware_is_registered_only_when_there_is_a_log(tmp_path):
    with SqliteStore(tmp_path) as store:
        plain = build_server(store)
        logged = build_server(store, EventLog(tmp_path / "log.jsonl"))

    assert not any(isinstance(m, RequestLog) for m in plain.middleware)
    assert any(isinstance(m, RequestLog) for m in logged.middleware)


def test_the_middleware_is_reached(tmp_path):
    recorded = session_calls(tmp_path, ("read_document", {"key": "a/b"}))

    # `MCPServer.middleware` is documented as provisional. If a future SDK
    # stops calling it, this fails rather than logging silently stopping.
    methods = [e["method"] for e in recorded if e["event"] == "request"]
    assert methods[0] == "initialize"
    assert "tools/call" in methods


def test_the_client_that_connected_is_recorded(tmp_path):
    recorded = session_calls(tmp_path, ("read_document", {"key": "a/b"}))

    (initialize,) = [e for e in recorded if e.get("method") == "initialize"]
    assert initialize["params"]["clientInfo"]["name"]


def test_a_rejected_call_is_recorded_as_an_error(tmp_path):
    recorded = session_calls(tmp_path, ("read_document", {"key": "a/b", "bogus": 1}))

    (called,) = [e for e in recorded if e.get("method") == "tools/call"]
    assert called["result"]["ok"] is False
    assert "bogus" in called["result"]["message"]


def test_a_rejected_call_never_reaches_the_store(tmp_path):
    recorded = session_calls(tmp_path, ("read_document", {"key": "a/b", "bogus": 1}))

    # The absence is the finding: an argument the server does not know is
    # refused before the tool function is entered, which is the failure a log
    # wrapped around those functions could not see at all.
    (called,) = [e for e in recorded if e.get("method") == "tools/call"]
    assert not [e for e in recorded if e["event"] == "store" and e.get("call") == called["call"]]


def test_store_accesses_are_grouped_under_the_call_that_caused_them(tmp_path):
    recorded = session_calls(tmp_path, ("get_documents", {"key": "a", "meta_name": ["title"]}))

    (called,) = [e for e in recorded if e.get("method") == "tools/call"]
    beneath = [
        e["op"] for e in recorded if e["event"] == "store" and e.get("call") == called["call"]
    ]
    # One tool call, more than one access: the survey, and the check for what
    # the survey could not see. That check used to re-read the whole subtree
    # for itself, which is the third access this no longer makes.
    assert beneath == ["get_documents", "missing_meta_stats"]


def test_the_setup_writes_are_not_attributed_to_any_call(tmp_path):
    recorded = session_calls(tmp_path, ("read_document", {"key": "a/b"}))

    (setup,) = [e for e in recorded if e.get("op") == "store_document"]
    assert "call" not in setup


def test_the_content_policy_reaches_the_request_layer(tmp_path):
    recorded = session_calls(
        tmp_path,
        ("store_document", {"key": "c/d", "content": "secret body"}),
        content="none",
    )

    # Scrubbing only the store layer would leave whole documents in the log
    # anyway, making --log-content=none a setting that reads as if it worked.
    (called,) = [e for e in recorded if e.get("method") == "tools/call"]
    written = called["params"]["arguments"]["content"]
    assert written["len"] == len("secret body")
    assert "text" not in written and "head" not in written


# -- pagination ------------------------------------------------------------


def a_wide_store(tmp_path, count: int, content: str = "body"):
    store = SqliteStore(tmp_path)
    for number in range(1, count + 1):
        store.store_document(f"notes/{number}", content, title=f"Note {number}")
    return store


def test_a_listing_says_what_it_is_part_of(tmp_path):
    with a_wide_store(tmp_path, 150) as store:
        result = call(build_server(store), "list_keys", key="notes")

    assert result["returned"] == 100
    assert result["total"] == 150
    assert result["next_cursor"] == "notes/100"


def test_a_listing_resumes_exactly_where_it_stopped(tmp_path):
    with a_wide_store(tmp_path, 150) as store:
        server = build_server(store)
        first = call(server, "list_keys", key="notes")
        second = call(server, "list_keys", key="notes", after=first["next_cursor"])

    assert [e["key"] for e in second["entries"]] == [f"notes/{n}" for n in range(101, 151)]
    assert second["next_cursor"] is None


def test_a_survey_is_capped_in_documents(tmp_path):
    with a_wide_store(tmp_path, 140) as store:
        result = call(build_server(store), "get_documents", key="notes", meta_name=["title"])

    assert result["returned"] == 100
    assert result["total"] == 140
    assert result["next_cursor"] == "notes/100/!title"


def test_a_survey_of_a_small_store_still_arrives_whole(tmp_path):
    with a_wide_store(tmp_path, 60) as store:
        result = call(build_server(store), "get_documents", key="notes", meta_name=["title"])

    # The case these defaults mostly serve. Titles are short, so the character
    # budget is nowhere near spent, and a session that surveys a small store
    # should see it rather than a first page of it.
    assert result["returned"] == 60
    assert result["next_cursor"] is None


def test_a_read_is_capped_in_characters_before_it_reaches_the_limit(tmp_path):
    with a_wide_store(tmp_path, 40, content="x" * 2000) as store:
        result = call(build_server(store), "get_documents", key="notes")

    # Twenty documents of two thousand characters is forty thousand, which
    # honours both stated bounds and is twice what the page allows.
    assert result["returned"] == 10
    assert sum(d["returned"] for d in result["documents"]) <= 20000
    assert result["total"] == 40


def test_the_untitled_are_counted_rather_than_listed(tmp_path):
    store = SqliteStore(tmp_path)
    for number in range(1, 31):
        store.store_document(f"notes/{number}", "body")
    with store:
        result = call(build_server(store), "get_documents", key="notes", meta_name=["title"])

    # The warning is the count. Listing them is the wrong answer at the scale
    # where it matters: there, the list is the corpus.
    assert result["without_meta"]["total"] == 30
    assert len(result["without_meta"]["sample"]) == 10


def test_the_caps_are_written_where_a_caller_can_read_them(server):
    tools = list_tools(server)

    # A default the model cannot see is a default it cannot reason about.
    assert "100" in tools["list_keys"].description
    assert "next_cursor" in tools["list_keys"].description
    assert "100 documents" in tools["get_documents"].description
    assert "20000 characters" in tools["get_documents"].description


def test_the_instructions_say_a_listing_is_a_page(server):
    from outrage.server import static_instructions

    text = static_instructions()

    assert "next_cursor" in text
    assert "`after`" in text
    assert "total" in text


def test_the_untitled_are_enumerated_by_the_tool_that_pages_them(tmp_path):
    store = SqliteStore(tmp_path)
    for number in range(1, 31):
        store.store_document(f"notes/{number}", "body")

    with store:
        server = build_server(store)
        survey = call(server, "get_documents", key="notes", meta_name=["title"])
        rest = call(server, "keys_missing_meta", key="notes")

    # The sample is a warning, not an answer, and the survey no longer pretends
    # to be a first page of one. The same `key` asked of the tool that owns
    # that collection is what enumerates it.
    assert survey["without_meta"]["total"] == rest["total"] == 30
    assert rest["returned"] == 30
    assert rest["keys"][0] == "notes/1"
    assert rest["next_cursor"] is None


def test_missing_metadata_is_asked_for_one_name_at_a_time(tmp_path):
    store = SqliteStore(tmp_path)
    store.store_document("notes/1", "body", title="Titled")

    with store:
        server = build_server(store)
        neither = call(server, "keys_missing_meta", key="notes", meta_name=["title", "summary"])
        summary = call(server, "keys_missing_meta", key="notes", meta_name=["summary"])

    # A document counts as covered when it has any one of the names, so asking
    # for both hides the document that has one and not the other.
    assert neither["keys"] == []
    assert summary["keys"] == ["notes/1"]


def test_missing_metadata_defaults_to_titles(tmp_path):
    store = SqliteStore(tmp_path)
    store.store_document("notes/1", "body")

    with store:
        assert call(build_server(store), "keys_missing_meta")["keys"] == ["notes/1"]


def test_the_untitled_are_counted_over_this_page_not_the_whole_subtree(tmp_path):
    store = SqliteStore(tmp_path)
    for number in range(1, 9):
        store.store_document(f"notes/{number}", "body")
    for number in (2, 5, 7):
        store.store_document(f"notes/{number}/!title", "T")

    with store:
        server = build_server(store)
        first = call(server, "get_documents", key="notes", meta_name=["title"], limit=1)
        second = call(
            server,
            "get_documents",
            key="notes",
            meta_name=["title"],
            limit=1,
            after=first["next_cursor"],
        )

    # The block describes the same stretch of the store as the page it arrives
    # with. Reporting all four untitled documents on every page says nothing
    # about where they are, and says it repeatedly.
    assert first["without_meta"]["sample"] == ["notes/1"]
    assert second["without_meta"]["sample"] == ["notes/3", "notes/4"]


def test_paging_a_survey_tiles_its_windows(tmp_path):
    store = SqliteStore(tmp_path)
    # `a` and `a/x` are both documents: a key holding content and having keys
    # beneath it is ordinary here, and it is what makes the windows subtle.
    for key in ["a", "a/x", "a/y", "b", "b/p", "c"]:
        store.store_document(key, f"content of {key}")
    for key in ["a", "a/y", "c"]:
        store.store_document(f"{key}/!title", "T")

    seen: list[str] = []
    after = None
    with store:
        server = build_server(store)
        while True:
            page = call(server, "get_documents", meta_name=["title"], limit=1, after=after)
            seen += page["without_meta"]["sample"]
            if not page["next_cursor"]:
                break
            after = page["next_cursor"]
        every = call(server, "keys_missing_meta")["keys"]

    # Every untitled document falls in exactly one window: no gap, no overlap.
    # Document keys cannot bound these windows -- `a` sorts before `a/x` while
    # `a/!title` sorts after `a/x/!title` -- and bounding them as though they
    # could double counts `a/x` and loses nothing visibly.
    assert sorted(seen) == sorted(every) == ["a/x", "b", "b/p"]
    assert len(seen) == len(set(seen))


# -- the readme, delivered rather than requested --------------------------


def test_the_readme_is_named_in_the_instructions(store):
    store.store_document("readme", "# This store\n\nRead `contents` next.")

    text = server_module.instructions(store)

    # Named, not carried: the session is told there is one and to read it
    # first, and nothing about how long it is changes what arrives.
    assert "`readme`" in text
    assert "Read it before starting." in text
    assert "Read `contents` next." not in text
    assert server_module.skill("essentials") in text
    assert server_module.skill("tail") in text


def test_the_readme_is_named_before_the_protocol(store):
    store.store_document("readme", "# This store\n\nRead `contents` next.")

    text = server_module.instructions(store)

    # The client cuts this text at a length it does not announce, so order is
    # what decides what survives. The readme line is first because a session
    # that gets only one sentence should get that one.
    essentials = server_module.skill("essentials")

    assert text.index(server_module.READ_README) < text.index(essentials)
    assert text.index(essentials) < text.index(server_module.skill("tail"))


def test_a_readme_costs_the_same_whatever_length_it_is(store):
    """The whole of why inlining went. A store's entry point is the project's
    business, and it used to be bounded by what this server had left over."""
    store.store_document("readme", "short")
    brief = server_module.instructions(store)

    store.store_document("readme", "x" * 20_000)
    enormous = server_module.instructions(store)

    assert brief == enormous


def test_the_delivered_text_fits_the_budget(store):
    # The failure this guards is static prose growing past the cut. It used to
    # push the store's own readme off the end; now it would push the essentials
    # there, which is worse. The tail is allowed to fall past -- that is what
    # makes it the tail.
    store.store_document("readme", "# This store")
    text = server_module.instructions(store)

    protected = text.removesuffix(f"\n{server_module.skill('tail')}")
    assert len(protected) == server_module.PROTECTED_CHARS
    assert server_module.PROTECTED_CHARS <= server_module.DELIVERY_BUDGET


def test_a_store_with_no_readme_is_told_the_convention(store):
    text = server_module.instructions(store)

    # The empty store is where naming the convention is worth most: the session
    # that works out the layout is the one that can write it down.
    assert "no `readme` document" in text


def test_a_container_at_the_readme_key_introduces_nothing(store):
    store.store_document("readme/notes", "beneath, not at")

    assert "no `readme` document" in server_module.instructions(store)


def test_the_server_is_built_with_the_readme_in_place(store):
    # The store is still consulted at build time, even though its content no
    # longer reaches the text: which of the two sentences is sent depends on it.
    assert server_module.NO_README in server_module.build_server(store).instructions

    store.store_document("readme", "the store's own introduction")

    assert server_module.READ_README in server_module.build_server(store).instructions


# -- the root ------------------------------------------------------------


def test_the_root_is_readable_and_writable_through_the_tools(server):
    written = call(server, "store_document", key="", content="# This store", title="This store")
    assert written["key"] == ""
    # Not `/!title`: a caller told the wrong key cannot read it back.
    assert written["title_key"] == "!title"
    assert call(server, "read_document", key="")["content"] == "# This store"
    assert call(server, "read_document", key="!title")["content"] == "This store"


def test_an_omitted_key_resolves_to_the_root(server):
    # A client that sends null for a key it did not fill in means the same as
    # one that left it out, and the result echoes the scope actually used.
    assert call(server, "list_keys")["key"] == ""
    assert call(server, "list_keys", key=None)["key"] == ""
    assert call(server, "get_documents")["key"] == ""
    assert call(server, "keys_missing_meta")["key"] == ""


def test_an_omitted_key_and_the_root_return_the_same_listing(server):
    assert call(server, "list_keys")["entries"] == call(server, "list_keys", key="")["entries"]


def test_the_root_document_does_not_list_below_itself(server):
    call(server, "store_document", key="", content="body")
    listing = call(server, "list_keys", key="")
    assert "" not in [entry["key"] for entry in listing["entries"]]


def test_a_slash_is_a_spelling_of_the_root(server):
    call(server, "store_document", key="/", content="body")
    assert call(server, "read_document", key="")["content"] == "body"


# -- ?last ------------------------------------------------------------------


def test_last_reads_the_newest_key_and_says_which_one(server):
    # `?` reports the number it allocated; this is the same obligation from the
    # other end -- a caller that asked for the newest is told what that was.
    result = call(server, "read_document", key="context/?last/task")
    assert result["key"] == "context/c3d4/task"
    assert result["content"] == "Add a delete tool."


def test_last_is_echoed_resolved_by_every_tool_that_takes_a_key(server):
    for tool in ("list_keys", "get_documents", "keys_missing_meta"):
        assert call(server, tool, key="context/?last")["key"] == "context/c3d4"


def test_last_orders_the_way_a_listing_does(server):
    for name in ("2", "10", "9"):
        call(server, "store_document", key=f"threads/{name}/task", content=name)
    # Numbers sort as numbers, so this is 10 and not the highest spelling.
    assert call(server, "list_keys", key="threads/?last")["key"] == "threads/10"


def test_last_writes_under_the_newest_key(server):
    written = call(server, "store_document", key="context/?last/notes", content="body")
    assert written["key"] == "context/c3d4/notes"
    assert call(server, "read_document", key="context/c3d4/notes")["content"] == "body"


def test_last_and_a_wildcard_in_one_key(server):
    # One segment resolved before the store is reached, the other allocated
    # inside the write. The result names both.
    written = call(server, "store_document", key="context/?last/?", content="body")
    assert written["key"] == "context/c3d4/1"


def test_last_deletes_from_the_newest_key(server):
    result = call(server, "delete_keys", key="context/?last/task", recursive=True)
    assert result["key"] == "context/c3d4/task"
    assert result["deleted"] == ["context/c3d4/task", "context/c3d4/task/!title"]


def test_last_with_nothing_below_it_is_refused_by_name(server):
    message = call_expecting_error(server, "read_document", key="nowhere/?last/task")
    assert "nowhere" in message and "nothing below it" in message


def test_a_key_spelled_last_can_no_longer_be_written(server):
    # The one thing this costs: `?last` used to be an ordinary segment, so a
    # key could be spelled that way. It now names the newest key instead, and
    # there is no escape that gets the old meaning back.
    written = call(server, "store_document", key="context/?last", content="x")
    assert written["key"] == "context/c3d4"
    assert "?last" not in [e["key"] for e in call(server, "list_keys", key="context")["entries"]]


# -- the single-document file round trip ---------------------------------


@pytest.fixture
def exports(tmp_path, monkeypatch):
    """Where this test's exports go.

    The real one is a per-user directory below the system temporary directory,
    which is exactly what these tests must not write into: pointing
    ``gettempdir`` at ``tmp_path`` keeps each test's exports its own, and keeps
    the sweep away from anything a real session left behind.
    """
    (tmp_path / "temp").mkdir()
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path / "temp"))
    return bulk.export_root()


@pytest.fixture
def exporting(tmp_path, exports):
    """A server over a small store, with its exports pointed somewhere safe."""
    with SqliteStore(tmp_path) as store:
        store.store_document("context/a1b2/design", "# Store schema", title="Store schema")
        store.store_document("notes/data", '{"a": 1}', format="json")
        yield build_server(store, directory=tmp_path)


def test_the_file_tool_is_offered_without_a_store_directory(exporting, server):
    """It was registered only when there was somewhere to write; there always is.

    ``build_server`` still takes ``directory`` -- the event log wants it -- but
    the tool no longer depends on it. ``plans/robust-editing``.
    """
    assert "document_edit" in list_tools(exporting)
    assert "document_edit" in list_tools(server)


def test_exporting_writes_the_document_to_a_file_of_its_own(exporting, exports):
    result = call(exporting, "document_edit", key="context/a1b2/design")

    assert Path(result["path"]).parent == exports
    assert Path(result["path"]).read_text() == "# Store schema"
    assert result["exported"] == 14
    assert "call again with its path" in result["note"]


def test_a_file_edited_on_disk_is_stored_back(exporting):
    exported = call(exporting, "document_edit", key="context/a1b2/design")
    Path(exported["path"]).write_text("# Store schema, revised")

    imported = call(exporting, "document_edit", key="context/a1b2/design", path=exported["path"])

    assert (imported["stored"], imported["previous"]) == (23, 14)
    assert imported["contents_key"] == "context/a1b2/design/!contents"
    assert "note" not in imported
    read = call(exporting, "read_document", key="context/a1b2/design")
    assert read["content"] == "# Store schema, revised"
    contents = call(exporting, "read_document", key="context/a1b2/design/!contents")
    assert contents["content"] == "# Store schema, revised\n0 0\n"


def test_document_edit_contents_generation_can_be_disabled(exporting):
    call(
        exporting,
        "store_document",
        key="context/a1b2/design",
        content="# Store schema",
        contents="# Keep me",
    )
    exported = call(exporting, "document_edit", key="context/a1b2/design")
    Path(exported["path"]).write_text("# Store schema, revised")

    imported = call(
        exporting,
        "document_edit",
        key="context/a1b2/design",
        path=exported["path"],
        generate_contents=False,
    )

    assert "contents_key" not in imported
    contents = call(exporting, "read_document", key="context/a1b2/design/!contents")
    assert contents["content"] == "# Keep me"


def test_a_document_that_shrank_is_said_to_have_shrunk(exporting):
    exported = call(exporting, "document_edit", key="context/a1b2/design")
    Path(exported["path"]).write_text("")

    imported = call(exporting, "document_edit", key="context/a1b2/design", path=exported["path"])

    assert (imported["stored"], imported["previous"]) == (0, 14)
    assert "shrank from 14 to 0" in imported["note"]


def test_re_exporting_a_key_leaves_the_first_export_alone(exporting):
    """What the deterministic name cost: the second export destroyed an edit
    the first session had not stored back yet."""
    first = call(exporting, "document_edit", key="context/a1b2/design")
    Path(first["path"]).write_text("# Store schema, half edited")

    again = call(exporting, "document_edit", key="context/a1b2/design")

    assert again["path"] != first["path"]
    assert Path(first["path"]).read_text() == "# Store schema, half edited"


def test_an_import_is_refused_when_somebody_else_wrote_the_document(exporting):
    exported = call(exporting, "document_edit", key="context/a1b2/design")
    Path(exported["path"]).write_text("# Store schema, my edit")
    call(exporting, "store_document", key="context/a1b2/design", content="# Theirs")

    message = call_expecting_error(
        exporting, "document_edit", key="context/a1b2/design", path=exported["path"]
    )

    assert "overwrite" in message
    assert call(exporting, "read_document", key="context/a1b2/design")["content"] == "# Theirs"


def test_overwrite_stores_it_anyway_and_says_what_went(exporting):
    exported = call(exporting, "document_edit", key="context/a1b2/design")
    Path(exported["path"]).write_text("# Store schema, my edit")
    call(exporting, "store_document", key="context/a1b2/design", content="# Theirs")

    imported = call(
        exporting,
        "document_edit",
        key="context/a1b2/design",
        path=exported["path"],
        overwrite=True,
    )

    assert "overwritten anyway" in imported["note"]
    assert call(exporting, "read_document", key="context/a1b2/design")["content"] == (
        "# Store schema, my edit"
    )


def test_a_round_trip_that_changed_nothing_says_so(exporting):
    exported = call(exporting, "document_edit", key="context/a1b2/design")

    imported = call(exporting, "document_edit", key="context/a1b2/design", path=exported["path"])

    assert "identical to what was exported" in imported["note"]


def test_an_export_and_an_import_may_name_different_keys(exporting):
    """Still allowed, and now said out loud: the record names the key it came
    from, so it cannot answer for the target and ``overwrite`` says to write
    regardless."""
    exported = call(exporting, "document_edit", key="context/a1b2/design")
    Path(exported["path"]).write_text("# Store schema, copied")

    imported = call(
        exporting,
        "document_edit",
        key="context/c3d4/design",
        path=exported["path"],
        overwrite=True,
    )

    assert imported["key"] == "context/c3d4/design"
    assert imported["stored"] == 22
    assert imported["unchecked_code"] == "other-key"
    assert "not checked against the document" in imported["note"]


def test_an_unchecked_import_is_refused_and_names_the_way_to_check_it(exporting):
    exported = call(exporting, "document_edit", key="context/a1b2/design")

    message = call_expecting_error(
        exporting, "document_edit", key="context/c3d4/design", path=exported["path"]
    )

    assert "`against`" in message
    assert "overwrite" in message


def test_a_second_file_makes_a_cross_key_import_checked(exporting):
    """`plans/write-preconditions/by-file`: the content comes from one exported
    file and the claim about the target comes from another."""
    call(exporting, "store_document", key="context/c3d4/design", content="# The copy")
    source = call(exporting, "document_edit", key="context/a1b2/design")
    Path(source["path"]).write_text("# Store schema, copied")
    target = call(exporting, "document_edit", key="context/c3d4/design")

    imported = call(
        exporting,
        "document_edit",
        key="context/c3d4/design",
        path=source["path"],
        against=target["path"],
    )

    assert imported["unchecked_code"] is None
    assert imported.get("note") is None
    assert call(exporting, "read_document", key="context/c3d4/design")["content"] == (
        "# Store schema, copied"
    )


def test_a_verbatim_cross_key_copy_is_not_called_a_no_op(exporting):
    """The copy route's ordinary case: the file is meant to be unedited, and
    the document it lands on still changed. Saying "the edit changed nothing"
    beside a `previous` and a `stored` that differ is the sentence contradicting
    the answer it is attached to."""
    call(exporting, "store_document", key="context/c3d4/design", content="# The copy")
    source = call(exporting, "document_edit", key="context/a1b2/design")
    target = call(exporting, "document_edit", key="context/c3d4/design")

    imported = call(
        exporting,
        "document_edit",
        key="context/c3d4/design",
        path=source["path"],
        against=target["path"],
    )

    assert imported["previous"] != imported["stored"]
    assert "the edit changed nothing" not in imported["note"]
    assert "unchanged since it was exported from 'context/a1b2/design'" in imported["note"]


def test_a_checked_cross_key_import_refuses_a_target_somebody_else_wrote(exporting):
    """The write that used to land silently on top of another agent's."""
    call(exporting, "store_document", key="context/c3d4/design", content="# The copy")
    source = call(exporting, "document_edit", key="context/a1b2/design")
    target = call(exporting, "document_edit", key="context/c3d4/design")
    call(exporting, "store_document", key="context/c3d4/design", content="# Theirs")

    message = call_expecting_error(
        exporting,
        "document_edit",
        key="context/c3d4/design",
        path=source["path"],
        against=target["path"],
    )

    assert "overwrite" in message
    assert call(exporting, "read_document", key="context/c3d4/design")["content"] == "# Theirs"


def test_store_document_checks_the_write_against_an_exported_file(exporting):
    """`plans/write-preconditions/by-file` piece 1: an agent that exported a
    document and edited it *in context* rather than on disk gets the same
    staleness refusal the import route gets."""
    exported = call(exporting, "document_edit", key="context/a1b2/design")

    stored = call(
        exporting,
        "store_document",
        key="context/a1b2/design",
        content="# Store schema, edited in context",
        against=exported["path"],
    )

    assert stored["previous"] == 14
    assert stored["unchecked_code"] is None
    assert call(exporting, "read_document", key="context/a1b2/design")["content"] == (
        "# Store schema, edited in context"
    )


def test_store_document_is_refused_when_somebody_else_wrote_the_document(exporting):
    exported = call(exporting, "document_edit", key="context/a1b2/design")
    call(exporting, "store_document", key="context/a1b2/design", content="# Theirs")

    message = call_expecting_error(
        exporting,
        "store_document",
        key="context/a1b2/design",
        content="# Mine",
        against=exported["path"],
    )

    assert "overwrite" in message
    assert call(exporting, "read_document", key="context/a1b2/design")["content"] == "# Theirs"


def test_store_document_overwrites_and_says_what_went(exporting):
    exported = call(exporting, "document_edit", key="context/a1b2/design")
    call(exporting, "store_document", key="context/a1b2/design", content="# Theirs")

    stored = call(
        exporting,
        "store_document",
        key="context/a1b2/design",
        content="# Mine",
        against=exported["path"],
        overwrite=True,
    )

    assert "overwritten anyway" in stored["note"]
    assert call(exporting, "read_document", key="context/a1b2/design")["content"] == "# Mine"


def test_store_document_does_not_read_the_file_it_is_checked_against(exporting):
    """The content comes from the call; the file is a claim, not a source."""
    exported = call(exporting, "document_edit", key="context/a1b2/design")
    Path(exported["path"]).write_text("bytes nobody is storing")

    call(
        exporting,
        "store_document",
        key="context/a1b2/design",
        content="# From the call",
        against=exported["path"],
    )

    assert call(exporting, "read_document", key="context/a1b2/design")["content"] == (
        "# From the call"
    )


def test_a_second_checked_store_is_not_refused_by_the_first(exporting):
    """The renewal reaches this route too, or it is one write per export."""
    exported = call(exporting, "document_edit", key="context/a1b2/design")
    call(
        exporting,
        "store_document",
        key="context/a1b2/design",
        content="# First",
        against=exported["path"],
    )

    stored = call(
        exporting,
        "store_document",
        key="context/a1b2/design",
        content="# Second",
        against=exported["path"],
    )

    assert stored["unchecked_code"] is None
    assert call(exporting, "read_document", key="context/a1b2/design")["content"] == "# Second"


def test_a_checked_store_of_an_encoded_call_renews_what_was_stored(exporting):
    """The record hashes what the store holds, and an encoded call did not send
    it: a record carrying the JSON literal would refuse the next write."""
    exported = call(exporting, "document_edit", key="context/a1b2/design")
    call(
        exporting,
        "store_document",
        key="context/a1b2/design",
        content=json.dumps("# Decoded first"),
        encoding="json-string",
        against=exported["path"],
    )

    stored = call(
        exporting,
        "store_document",
        key="context/a1b2/design",
        content="# Decoded second",
        against=exported["path"],
    )

    assert stored["unchecked_code"] is None


def test_a_check_file_exported_from_another_key_is_refused(exporting):
    exported = call(exporting, "document_edit", key="context/a1b2/design")

    message = call_expecting_error(
        exporting,
        "store_document",
        key="notes/data",
        content="{}",
        against=exported["path"],
    )

    assert "`against`" in message
    assert "notes/data" in message


def test_a_store_that_shrank_under_a_check_is_said_to_have_shrunk(exporting):
    exported = call(exporting, "document_edit", key="context/a1b2/design")

    stored = call(
        exporting,
        "store_document",
        key="context/a1b2/design",
        content="",
        against=exported["path"],
    )

    assert (stored["stored"], stored["previous"]) == (0, 14)
    assert "shrank from 14 to 0" in stored["note"]


def test_an_ordinary_store_document_is_unchanged_by_all_of_this(exporting):
    """No `against` still means no check fields in the answer."""
    stored = call(exporting, "store_document", key="context/a1b2/design", content="# Whatever")

    assert stored == {
        "key": "context/a1b2/design",
        "stored": 10,
        "generated": False,
        "contents_key": "context/a1b2/design/!contents",
    }


def test_a_check_file_on_an_export_is_refused_rather_than_ignored(exporting):
    exported = call(exporting, "document_edit", key="context/a1b2/design")

    message = call_expecting_error(
        exporting, "document_edit", key="context/a1b2/design", against=exported["path"]
    )

    assert "nothing to check" in message


def test_the_file_name_is_what_says_what_format_came_back(exporting):
    exported = call(exporting, "document_edit", key="notes/data")
    assert exported["format"] == "json"
    Path(exported["path"]).write_text('{"a": 2}')

    call(exporting, "document_edit", key="notes/data", path=exported["path"])

    assert call(exporting, "read_document", key="notes/data")["format"] == "json"


def test_a_file_outside_the_export_directory_is_refused(exporting, tmp_path):
    outside = tmp_path / "elsewhere.md"
    outside.write_text("never exported")

    message = call_expecting_error(
        exporting, "document_edit", key="context/a1b2/design", path=str(outside)
    )

    assert "outside the export directory" in message
    assert call(exporting, "read_document", key="context/a1b2/design")["content"] == (
        "# Store schema"
    )


def test_a_file_that_is_not_there_is_refused_by_name(exporting, exports):
    message = call_expecting_error(
        exporting, "document_edit", key="context/a1b2/design", path=str(exports / "gone.md")
    )

    assert "no file at" in message


def test_the_newest_context_can_be_exported_by_asking_for_it(exporting, exports):
    result = call(exporting, "document_edit", key="context/?last/design")

    assert result["key"] == "context/a1b2/design"
    assert Path(result["path"]).parent == exports


def test_a_wildcard_key_is_not_a_round_trip(exporting):
    message = call_expecting_error(exporting, "document_edit", key="context/?/design")

    assert "?" in message


# The documentation shipped inside the package. The server carries it and the
# command line does not, which is the whole of what is different about it:
# everything below asks whether "carried by default" is really an ordinary
# mount. `project/reference/planned/mounts/default-store`.


def test_the_shipped_documentation_is_mounted_unless_told_otherwise(tmp_path):
    assert parse_args(["--dir", str(tmp_path)]).mount_docs is True


def test_unmounting_the_documentation_is_the_off_switch(tmp_path):
    args = parse_args(["--dir", str(tmp_path), mountfile.UNMOUNT_FLAG, mountfile.DOCS_MOUNT])

    assert args.mount_docs is False


def test_a_store_mounted_there_replaces_the_documentation(tmp_path):
    """Silently, and without a duplicate refusal: the override rule, as asked."""
    args = parse_args(["--dir", str(tmp_path), "--mount", f"{mountfile.DOCS_MOUNT}=mine.sqlite"])

    assert args.mount_docs is False
    assert args.mounts == [f"{mountfile.DOCS_MOUNT}=mine.sqlite"]


def test_the_documentation_is_attached_read_only(tmp_path):
    attached = server_module._documents(True)

    assert list(attached) == [shipped.MOUNT_POINT]
    with mounts_module.open_mounts(tmp_path, attached=attached) as table:
        assert [mount.prefix for mount in table.read_only] == [shipped.MOUNT_POINT]


def test_a_build_that_dropped_the_tree_warns_rather_than_refusing(tmp_path, monkeypatch, capsys):
    """The one place the default differs from the flag.

    Nobody asked for this mount, so a missing tree must not stop a session
    starting over documentation that is not what their store is for. The
    command line, where somebody typed --mount-docs, refuses instead.
    """
    monkeypatch.setattr(shipped, "tree", lambda: tmp_path / "gone")

    assert server_module._documents(True) == {}
    assert "not in this installation" in capsys.readouterr().err


def test_nothing_is_attached_when_it_is_not_wanted():
    assert server_module._documents(False) == {}


def test_the_documentation_readme_is_not_delivered(tmp_path):
    """Deliberate, and on the delivery budget: only the root store's is carried.

    `planned/instructions-budget` is the margin, and it is a few dozen
    characters. A second readme is hundreds, so carrying this one would push
    the first past the client's silent cut -- the exact failure the ordering
    exists to prevent.
    """
    with mounts_module.open_mounts(tmp_path, attached=shipped.attached()) as table:
        text = instructions(table)

    assert "outrage manual" not in text
