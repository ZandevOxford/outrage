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
        store.store_document("context.a1b2.design", "# Store schema\n\n" + "body " * 1000)
        store.store_document("context.a1b2.design:title", "Store schema")
        store.store_document("context.c3d4.task", "Add a delete tool.")
        store.store_document("context.c3d4.task:title", "Delete tool")
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


def test_tool_schemas_describe_their_arguments(server):
    tool = list_tools(server)["retrieve_document"]
    properties = tool.input_schema["properties"]
    assert tool.input_schema["required"] == ["key"]
    assert "regex" in properties["pattern"]["description"]


def test_retrieve_document(server):
    result = call(server, "retrieve_document", key="context.c3d4.task")
    assert result["content"] == "Add a delete tool."
    assert result["truncated"] is False
    assert result["next_offset"] is None


def test_retrieve_document_pages(server):
    first = call(server, "retrieve_document", key="context.a1b2.design", max_chars=20)
    assert first["content"] == "# Store schema\n\nbody"
    assert first["truncated"] is True

    second = call(
        server,
        "retrieve_document",
        key="context.a1b2.design",
        offset=first["next_offset"],
        max_chars=20,
    )
    assert second["offset"] == 20
    assert second["content"] == " body body body body"


def test_retrieve_document_by_pattern(server):
    result = call(server, "retrieve_document", key="context.a1b2.design", pattern="body")
    assert result["offset"] == 16


def test_retrieve_missing_key_is_a_tool_error(server):
    assert "context.zzzz" in call_expecting_error(server, "retrieve_document", key="context.zzzz")


def test_invalid_key_is_a_tool_error(server):
    assert "segment" in call_expecting_error(server, "retrieve_document", key="a..b")


def test_argument_validation_rejects_a_negative_offset(server):
    message = call_expecting_error(server, "retrieve_document", key="a", offset=-1)
    assert "offset" in message


def test_store_document_round_trip(server):
    stored = call(server, "store_document", key="project.notes", content="# Notes")
    assert stored == {"key": "project.notes", "stored": 7}
    assert call(server, "retrieve_document", key="project.notes")["content"] == "# Notes"


def test_store_document_detects_json(server):
    call(server, "store_document", key="project.data", content='{"a": 1}')
    assert call(server, "retrieve_document", key="project.data")["format"] == "json"


def test_list_keys_at_the_top_level(server):
    entries = call(server, "list_keys")["entries"]
    assert [(e["key"], e["kind"]) for e in entries] == [("context", "implicit")]


def test_list_keys_shows_subkeys_and_metadata(server):
    entries = call(server, "list_keys", key="context.c3d4")["entries"]
    assert [(e["key"], e["kind"]) for e in entries] == [("context.c3d4.task", "document")]

    entries = call(server, "list_keys", key="context.c3d4.task")["entries"]
    assert [(e["key"], e["kind"]) for e in entries] == [("context.c3d4.task:title", "metadata")]


def test_get_documents_surveys_titles(server):
    result = call(server, "get_documents", key="context", meta_name=["title"])
    assert result["count"] == 2
    assert {d["key"]: d["content"] for d in result["documents"]} == {
        "context.a1b2.design:title": "Store schema",
        "context.c3d4.task:title": "Delete tool",
    }


def test_get_documents_truncates(server):
    result = call(server, "get_documents", key="context", max_chars=10)
    assert [d["returned"] for d in result["documents"]] == [10, 10]
    assert result["documents"][0]["truncated"] is True


def test_get_documents_respects_depth(server):
    assert call(server, "get_documents", key="context", depth=1)["count"] == 0
    assert call(server, "get_documents", key="context", depth=2)["count"] == 2


def test_delete_keys_takes_metadata_with_the_document(server):
    result = call(server, "delete_keys", key="context.c3d4.task")
    assert result["deleted"] == ["context.c3d4.task", "context.c3d4.task:title"]
    assert result["count"] == 2


def test_delete_keys_is_not_recursive_by_default(server):
    assert call(server, "delete_keys", key="context.a1b2")["count"] == 0
    assert call(server, "delete_keys", key="context.a1b2", recursive=True)["count"] == 2


def test_parse_args():
    assert parse_args([]).directory is None
    assert parse_args(["--dir", "/tmp/x"]).directory == "/tmp/x"
