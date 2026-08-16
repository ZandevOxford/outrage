"""Tests driving the tools through the MCP server's own dispatch."""

from typing import Any

import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from rage.server import build_server, parse_args
from rage.store import Store


@pytest.fixture
def server(tmp_path):
    with Store(tmp_path) as store:
        store.store_document("context/a1b2/design", "# Store schema\n\n" + "body " * 1000)
        store.store_document("context/a1b2/design:title", "Store schema")
        store.store_document("context/c3d4/task", "Add a delete tool.")
        store.store_document("context/c3d4/task:title", "Delete tool")
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
        "retrieve_document",
        "store_document",
        "list_keys",
        "get_documents",
        "delete_keys",
    }
    assert tools["retrieve_document"].annotations.read_only_hint is True
    assert tools["delete_keys"].annotations.destructive_hint is True
    for tool in tools.values():
        assert tool.description


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
    assert "nothing is stored" in call_expecting_error(server, "retrieve_document", key="a/b")


def test_schemas_tell_clients_that_arguments_are_fixed(server):
    for tool in list_tools(server).values():
        assert tool.input_schema.get("additionalProperties") is False, tool.name


def test_known_arguments_still_pass(server):
    """The strictness must not cost the optional arguments."""
    assert call(server, "store_document", key="a/b", content="x", title="T", format="markdown")
    assert call(server, "list_keys")["entries"]


def test_tool_schemas_describe_their_arguments(server):
    tool = list_tools(server)["retrieve_document"]
    properties = tool.input_schema["properties"]
    assert tool.input_schema["required"] == ["key"]
    assert "regex" in properties["pattern"]["description"]


def test_retrieve_document(server):
    result = call(server, "retrieve_document", key="context/c3d4/task")
    assert result["content"] == "Add a delete tool."
    assert result["truncated"] is False
    assert result["next_offset"] is None


def test_retrieve_document_pages(server):
    first = call(server, "retrieve_document", key="context/a1b2/design", max_chars=20)
    assert first["content"] == "# Store schema\n\nbody"
    assert first["truncated"] is True

    second = call(
        server,
        "retrieve_document",
        key="context/a1b2/design",
        offset=first["next_offset"],
        max_chars=20,
    )
    assert second["offset"] == 20
    assert second["content"] == " body body body body"


def test_retrieve_document_by_pattern(server):
    result = call(server, "retrieve_document", key="context/a1b2/design", pattern="body")
    assert result["offset"] == 16


def test_retrieve_missing_key_is_a_tool_error(server):
    assert "context/zzzz" in call_expecting_error(server, "retrieve_document", key="context/zzzz")


def test_invalid_key_is_a_tool_error(server):
    assert "segment" in call_expecting_error(server, "retrieve_document", key="a//b")


def test_a_wildcard_is_a_tool_error_when_reading(server):
    message = call_expecting_error(server, "retrieve_document", key="context/?")
    assert "only when storing" in message


def test_argument_validation_rejects_a_negative_offset(server):
    message = call_expecting_error(server, "retrieve_document", key="a", offset=-1)
    assert "offset" in message


def test_store_document_round_trip(server):
    stored = call(server, "store_document", key="project/notes", content="# Notes")
    assert stored == {"key": "project/notes", "stored": 7, "generated": False}
    assert call(server, "retrieve_document", key="project/notes")["content"] == "# Notes"


def test_store_document_reports_an_allocated_key(server):
    stored = call(server, "store_document", key="tmp/?", content="scratch")
    assert stored == {"key": "tmp/1", "stored": 7, "generated": True}
    assert call(server, "store_document", key="tmp/?", content="more")["key"] == "tmp/2"
    assert call(server, "retrieve_document", key="tmp/1")["content"] == "scratch"


def test_store_document_writes_a_title_in_one_call(server):
    stored = call(server, "store_document", key="project/notes", content="# Notes", title="Notes")
    assert stored["title_key"] == "project/notes:title"
    assert call(server, "retrieve_document", key="project/notes:title")["content"] == "Notes"


def test_store_document_titles_the_key_it_allocated(server):
    stored = call(server, "store_document", key="tmp/?", content="scratch", title="Scratch")
    assert (stored["key"], stored["title_key"]) == ("tmp/1", "tmp/1:title")


def test_store_document_rejects_a_title_on_a_metadata_key(server):
    message = call_expecting_error(
        server, "store_document", key="a/b:summary", content="text", title="Nope"
    )
    assert "cannot attach a title" in message


def test_store_document_detects_json(server):
    call(server, "store_document", key="project/data", content='{"a": 1}')
    assert call(server, "retrieve_document", key="project/data")["format"] == "json"


def test_store_document_decodes_a_json_string_encoding(server):
    stored = call(
        server,
        "store_document",
        key="a/b:summary",
        content='"A summary saying \\"hi\\".\\nSecond line."',
        encoding="json-string",
    )
    # `stored` counts what was stored, not the longer encoded form that arrived.
    assert stored["stored"] == len('A summary saying "hi".\nSecond line.')
    assert (
        call(server, "retrieve_document", key="a/b:summary")["content"]
        == 'A summary saying "hi".\nSecond line.'
    )


def test_store_document_rejects_scaffolding_under_a_json_string_encoding(server):
    message = call_expecting_error(
        server,
        "store_document",
        key="a/b:summary",
        content='"A summary."</content>\n</invoke>\n',
        encoding="json-string",
    )
    assert "not a valid JSON string literal" in message
    # Nothing was written, so the caller can simply send it again.
    assert "nothing is stored" in call_expecting_error(
        server, "retrieve_document", key="a/b:summary"
    )


def test_list_keys_at_the_top_level(server):
    entries = call(server, "list_keys")["entries"]
    assert [(e["key"], e["kind"]) for e in entries] == [("context", "implicit")]


def test_list_keys_shows_subkeys_and_metadata(server):
    entries = call(server, "list_keys", key="context/c3d4")["entries"]
    assert [(e["key"], e["kind"]) for e in entries] == [("context/c3d4/task", "document")]

    entries = call(server, "list_keys", key="context/c3d4/task")["entries"]
    assert [(e["key"], e["kind"]) for e in entries] == [("context/c3d4/task:title", "metadata")]


def test_get_documents_surveys_titles(server):
    result = call(server, "get_documents", key="context", meta_name=["title"])
    assert result["count"] == 2
    assert {d["key"]: d["content"] for d in result["documents"]} == {
        "context/a1b2/design:title": "Store schema",
        "context/c3d4/task:title": "Delete tool",
    }


def test_get_documents_survey_names_the_untitled(server):
    call(server, "store_document", key="context/e5f6/note", content="No title here.")
    result = call(server, "get_documents", key="context", meta_name=["title"])
    assert result["count"] == 2
    assert result["without_meta"] == ["context/e5f6/note"]


def test_get_documents_survey_is_quiet_when_everything_is_titled(server):
    assert "without_meta" not in call(server, "get_documents", key="context", meta_name=["title"])


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


def test_delete_keys_takes_metadata_with_the_document(server):
    result = call(server, "delete_keys", key="context/c3d4/task")
    assert result["deleted"] == ["context/c3d4/task", "context/c3d4/task:title"]
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


def test_parse_args():
    assert parse_args([]).directory is None
    assert parse_args(["--dir", "/tmp/x"]).directory == "/tmp/x"
