"""Tests driving the tools through the MCP server's own dispatch."""

import json
from typing import Any

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.server.mcpserver.exceptions import ToolError
from mcp.shared.memory import create_client_server_memory_streams

from rage import eventlog
from rage.eventlog import EventLog
from rage.server import RequestLog, build_server, parse_args
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
        "keys_missing_meta",
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
    assert result["without_meta"] == {
        "total": 1,
        "sample": ["context/e5f6/note"],
        "next_cursor": None,
    }


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


def test_parse_args_leaves_logging_off():
    assert parse_args([]).log is None
    assert parse_args(["--log"]).log is eventlog.DEFAULT
    assert parse_args(["--log", "/tmp/l.jsonl"]).log == "/tmp/l.jsonl"
    assert parse_args([]).log_content == "excerpt"


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
        with Store(tmp_path / "store", log=log) as store:
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
    with Store(tmp_path) as store:
        plain = build_server(store)
        logged = build_server(store, EventLog(tmp_path / "log.jsonl"))

    assert not any(isinstance(m, RequestLog) for m in plain.middleware)
    assert any(isinstance(m, RequestLog) for m in logged.middleware)


def test_the_middleware_is_reached(tmp_path):
    recorded = session_calls(tmp_path, ("retrieve_document", {"key": "a/b"}))

    # `MCPServer.middleware` is documented as provisional. If a future SDK
    # stops calling it, this fails rather than logging silently stopping.
    methods = [e["method"] for e in recorded if e["event"] == "request"]
    assert methods[0] == "initialize"
    assert "tools/call" in methods


def test_the_client_that_connected_is_recorded(tmp_path):
    recorded = session_calls(tmp_path, ("retrieve_document", {"key": "a/b"}))

    (initialize,) = [e for e in recorded if e.get("method") == "initialize"]
    assert initialize["params"]["clientInfo"]["name"]


def test_a_rejected_call_is_recorded_as_an_error(tmp_path):
    recorded = session_calls(tmp_path, ("retrieve_document", {"key": "a/b", "bogus": 1}))

    (called,) = [e for e in recorded if e.get("method") == "tools/call"]
    assert called["result"]["ok"] is False
    assert "bogus" in called["result"]["message"]


def test_a_rejected_call_never_reaches_the_store(tmp_path):
    recorded = session_calls(tmp_path, ("retrieve_document", {"key": "a/b", "bogus": 1}))

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
    assert beneath == ["get_documents", "keys_missing_meta"]


def test_the_setup_writes_are_not_attributed_to_any_call(tmp_path):
    recorded = session_calls(tmp_path, ("retrieve_document", {"key": "a/b"}))

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
    store = Store(tmp_path)
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
    assert result["next_cursor"] == "notes/100:title"


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
    store = Store(tmp_path)
    for number in range(1, 31):
        store.store_document(f"notes/{number}", "body")
    with store:
        result = call(build_server(store), "get_documents", key="notes", meta_name=["title"])

    # The warning is the count. Listing them is the wrong answer at the scale
    # where it matters: there, the list is the corpus.
    assert result["without_meta"]["total"] == 30
    assert len(result["without_meta"]["sample"]) == 10
    assert result["without_meta"]["next_cursor"] == "notes/10"


def test_the_caps_are_written_where_a_caller_can_read_them(server):
    tools = list_tools(server)

    # A default the model cannot see is a default it cannot reason about.
    assert "100" in tools["list_keys"].description
    assert "next_cursor" in tools["list_keys"].description
    assert "100 documents" in tools["get_documents"].description
    assert "20000 characters" in tools["get_documents"].description


def test_the_instructions_say_a_listing_is_a_page(server):
    from rage.server import INSTRUCTIONS

    assert "next_cursor" in INSTRUCTIONS
    assert "`after`" in INSTRUCTIONS
    assert "total" in INSTRUCTIONS


def test_the_untitled_can_be_paged_where_the_survey_only_sampled(tmp_path):
    store = Store(tmp_path)
    for number in range(1, 31):
        store.store_document(f"notes/{number}", "body")

    with store:
        server = build_server(store)
        survey = call(server, "get_documents", key="notes", meta_name=["title"])
        rest = call(
            server,
            "keys_missing_meta",
            key="notes",
            after=survey["without_meta"]["next_cursor"],
        )

    # The sample is a warning, not an answer. A cursor that no tool accepts
    # would make it a dead end instead of a first page.
    assert rest["returned"] == 20
    assert rest["total"] == 30
    assert rest["keys"][0] == "notes/11"
    assert rest["next_cursor"] is None


def test_missing_metadata_is_asked_for_one_name_at_a_time(tmp_path):
    store = Store(tmp_path)
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
    store = Store(tmp_path)
    store.store_document("notes/1", "body")

    with store:
        assert call(build_server(store), "keys_missing_meta")["keys"] == ["notes/1"]
