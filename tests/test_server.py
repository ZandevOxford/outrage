"""Tests driving the tools through the MCP server's own dispatch."""

import json
from pathlib import Path
from typing import Any

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.server.mcpserver.exceptions import ToolError
from mcp.shared.memory import create_client_server_memory_streams

from outrage import eventlog, mountfile, shipped
from outrage import mounts as mounts_module
from outrage import server as server_module
from outrage.eventlog import EventLog
from outrage.server import RequestLog, build_server, instructions, parse_args
from outrage.store_sqlite import SqliteStore


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
        "retrieve_document",
        "store_document",
        "list_keys",
        "get_documents",
        "keys_missing_meta",
        "delete_keys",
    }
    # `document_file` is deliberately not in that set: it writes files under the
    # store directory, and this server was built without being told where that
    # is. See `test_the_file_tool_is_offered_only_when_there_is_somewhere_to_write`.
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
    # `!title` used to be the example here and is the root's title since the
    # root became addressable, so the malformation has to be a real one.
    message = call_expecting_error(server, "retrieve_document", key="context/!")
    assert "metadata name" in message


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
    assert stored["title_key"] == "project/notes/!title"
    assert call(server, "retrieve_document", key="project/notes/!title")["content"] == "Notes"


def test_store_document_titles_the_key_it_allocated(server):
    stored = call(server, "store_document", key="tmp/?", content="scratch", title="Scratch")
    assert (stored["key"], stored["title_key"]) == ("tmp/1", "tmp/1/!title")


def test_store_document_titles_a_metadata_namespace(server):
    call(server, "store_document", key="a/b/!changelog", content="text", title="What changed")
    title = call(server, "retrieve_document", key="a/b/!changelog/!title")
    assert title["content"] == "What changed"


def test_store_document_detects_json(server):
    call(server, "store_document", key="project/data", content='{"a": 1}')
    assert call(server, "retrieve_document", key="project/data")["format"] == "json"


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
        call(server, "retrieve_document", key="a/b/!summary")["content"]
        == 'A summary saying "hi".\nSecond line.'
    )


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
    assert "nothing is stored" in call_expecting_error(
        server, "retrieve_document", key="a/b/!summary"
    )


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
    assert beneath == ["get_documents", "missing_meta_stats"]


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
    from outrage.server import INSTRUCTIONS

    assert "next_cursor" in INSTRUCTIONS
    assert "`after`" in INSTRUCTIONS
    assert "total" in INSTRUCTIONS


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


def test_a_readme_is_carried_in_the_instructions(store):
    store.store_document("readme", "# This store\n\nRead `project` next.")

    text = server_module.instructions(store)

    # Delivered, not requested: a line telling a session to go and read a key
    # is a line that can be read past, and the whole point is that this one
    # arrives before the session has to know to ask.
    assert "Read `project` next." in text
    assert server_module.ESSENTIALS in text
    assert server_module.TAIL in text


def test_the_readme_is_delivered_before_the_protocol(store):
    store.store_document("readme", "# This store\n\nRead `project` next.")

    text = server_module.instructions(store)

    # The client cuts this text at a length it does not announce, so order is
    # what decides what survives. The readme was last for long enough that it
    # never reached a session at all; see `planned/instructions-budget`.
    assert text.index("Read `project` next.") < text.index(server_module.ESSENTIALS)
    assert text.index(server_module.ESSENTIALS) < text.index(server_module.TAIL)


def test_the_essentials_leave_room_for_a_readme(store):
    # The whole failure was static prose growing past the cut and pushing the
    # store's own routing off the end. This fails the moment that starts again,
    # rather than three weeks later when somebody re-measures a transcript.
    assert server_module.README_MAX_CHARS >= server_module.README_FLOOR_CHARS

    store.store_document("readme", "x" * server_module.README_MAX_CHARS)
    text = server_module.instructions(store)

    # Everything ahead of the tail is what the budget has to cover. The tail is
    # allowed to fall past the cut -- that is what makes it the tail.
    delivered = text.removesuffix(f"\n{server_module.TAIL}")
    assert len(delivered) <= server_module.DELIVERY_BUDGET
    assert "x" * server_module.README_MAX_CHARS in delivered


def test_a_store_with_no_readme_is_told_the_convention(store):
    text = server_module.instructions(store)

    # The empty store is where naming the convention is worth most: the session
    # that works out the layout is the one that can write it down.
    assert "no `readme` document" in text


def test_a_container_at_the_readme_key_introduces_nothing(store):
    store.store_document("readme/notes", "beneath, not at")

    assert "no `readme` document" in server_module.instructions(store)


def test_an_oversized_readme_is_named_rather_than_shortened(store):
    store.store_document("readme", "x" * 2500)

    text = server_module.instructions(store)

    # A silently shortened entry point would be this project's own recurring
    # failure at the one document meant to prevent it. Told the size, a reader
    # can decide to go and read the rest.
    assert "x" * 2500 not in text
    assert "2500 characters" in text
    assert "Read it before starting" in text


def test_the_server_is_built_with_the_readme_in_place(store):
    store.store_document("readme", "the store's own introduction")

    built = server_module.build_server(store)

    assert "the store's own introduction" in built.instructions


# -- the root ------------------------------------------------------------


def test_the_root_is_readable_and_writable_through_the_tools(server):
    written = call(server, "store_document", key="", content="# This store", title="This store")
    assert written["key"] == ""
    # Not `/!title`: a caller told the wrong key cannot read it back.
    assert written["title_key"] == "!title"
    assert call(server, "retrieve_document", key="")["content"] == "# This store"
    assert call(server, "retrieve_document", key="!title")["content"] == "This store"


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
    assert call(server, "retrieve_document", key="")["content"] == "body"


# -- ?last ------------------------------------------------------------------


def test_last_reads_the_newest_key_and_says_which_one(server):
    # `?` reports the number it allocated; this is the same obligation from the
    # other end -- a caller that asked for the newest is told what that was.
    result = call(server, "retrieve_document", key="context/?last/task")
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
    assert call(server, "retrieve_document", key="context/c3d4/notes")["content"] == "body"


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
    message = call_expecting_error(server, "retrieve_document", key="nowhere/?last/task")
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
def exporting(tmp_path):
    """A server told where the store directory is, so `document_file` exists."""
    with SqliteStore(tmp_path) as store:
        store.store_document("context/a1b2/design", "# Store schema", title="Store schema")
        store.store_document("notes/data", '{"a": 1}', format="json")
        yield build_server(store, directory=tmp_path)


@pytest.fixture
def exports(tmp_path):
    return tmp_path / "export"


def test_the_file_tool_is_offered_only_when_there_is_somewhere_to_write(exporting, server):
    assert "document_file" in list_tools(exporting)
    assert "document_file" not in list_tools(server)


def test_exporting_writes_the_document_under_the_store_directory(exporting, exports):
    result = call(exporting, "document_file", key="context/a1b2/design")

    assert result["path"] == str(exports / "context" / "a1b2" / "design.md")
    assert Path(result["path"]).read_text() == "# Store schema"
    assert result["exported"] == 14
    assert result["replaced"] is False
    assert "call again with its path" in result["note"]


def test_a_file_edited_on_disk_is_stored_back(exporting):
    exported = call(exporting, "document_file", key="context/a1b2/design")
    Path(exported["path"]).write_text("# Store schema, revised")

    imported = call(exporting, "document_file", key="context/a1b2/design", path=exported["path"])

    assert (imported["stored"], imported["previous"]) == (23, 14)
    assert "note" not in imported
    read = call(exporting, "retrieve_document", key="context/a1b2/design")
    assert read["content"] == "# Store schema, revised"


def test_a_document_that_shrank_is_said_to_have_shrunk(exporting):
    exported = call(exporting, "document_file", key="context/a1b2/design")
    Path(exported["path"]).write_text("")

    imported = call(exporting, "document_file", key="context/a1b2/design", path=exported["path"])

    assert (imported["stored"], imported["previous"]) == (0, 14)
    assert "shrank from 14 to 0" in imported["note"]


def test_re_exporting_a_key_says_it_overwrote_the_file(exporting):
    call(exporting, "document_file", key="context/a1b2/design")

    again = call(exporting, "document_file", key="context/a1b2/design")

    assert again["replaced"] is True
    assert "overwritten" in again["note"]


def test_an_export_and_an_import_may_name_different_keys(exporting):
    exported = call(exporting, "document_file", key="context/a1b2/design")

    imported = call(exporting, "document_file", key="context/c3d4/design", path=exported["path"])

    assert imported == {
        "key": "context/c3d4/design",
        "path": exported["path"],
        "stored": 14,
        "previous": None,
    }


def test_the_file_name_is_what_says_what_format_came_back(exporting):
    exported = call(exporting, "document_file", key="notes/data")
    assert exported["format"] == "json"
    Path(exported["path"]).write_text('{"a": 2}')

    call(exporting, "document_file", key="notes/data", path=exported["path"])

    assert call(exporting, "retrieve_document", key="notes/data")["format"] == "json"


def test_a_file_outside_the_export_directory_is_refused(exporting, tmp_path):
    outside = tmp_path / "elsewhere.md"
    outside.write_text("never exported")

    message = call_expecting_error(
        exporting, "document_file", key="context/a1b2/design", path=str(outside)
    )

    assert "outside the export directory" in message
    assert call(exporting, "retrieve_document", key="context/a1b2/design")["content"] == (
        "# Store schema"
    )


def test_a_file_that_is_not_there_is_refused_by_name(exporting, exports):
    message = call_expecting_error(
        exporting, "document_file", key="context/a1b2/design", path=str(exports / "gone.md")
    )

    assert "no file at" in message


def test_the_newest_context_can_be_exported_by_asking_for_it(exporting, exports):
    result = call(exporting, "document_file", key="context/?last/design")

    assert result["key"] == "context/a1b2/design"
    assert result["path"] == str(exports / "context" / "a1b2" / "design.md")


def test_a_wildcard_key_is_not_a_round_trip(exporting):
    message = call_expecting_error(exporting, "document_file", key="context/?/design")

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
