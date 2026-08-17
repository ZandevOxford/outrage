"""Tests for reading a log back.

The writer's tests cover what gets written. These cover what a reader concludes
from it, and most of them exist because a plausible reader concludes something
false: that sequence numbers order a file, that a repeated read is a resumed
one, that a failure the store raised and the refusal the caller received are
two failures.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rage import logread
from rage.logread import Event, Filter, LogError, read_log, sessions, summarise


def write(path: Path, *records: dict) -> Path:
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    return path


def event(session: str = "aaa", seq: int = 1, **fields) -> dict:
    return {"ts": "2026-08-17T19:43:04.079+00:00", "seq": seq, "session": session, **fields}


def store_event(session: str = "aaa", seq: int = 1, op: str = "retrieve_document", **fields):
    return event(session, seq, event="store", op=op, **fields)


def read(session: str, seq: int, key: str, *, offset: int = 0, total: int = 100, returned=None):
    """A retrieve_document event, with the slice it returned."""
    returned = total if returned is None else returned
    next_offset = offset + returned if offset + returned < total else None
    return store_event(
        session,
        seq,
        call=seq,
        args={"key": key, "offset": offset, "max_chars": 8000},
        result={"total": total, "returned": returned, "next_offset": next_offset},
    )


# -- reading ---------------------------------------------------------------


def test_a_missing_log_is_a_message_not_a_traceback(tmp_path):
    with pytest.raises(LogError) as raised:
        read_log(tmp_path / "nowhere.jsonl")

    assert str(tmp_path / "nowhere.jsonl") in str(raised.value)


def test_a_torn_line_is_skipped_rather_than_fatal(tmp_path):
    path = tmp_path / "log.jsonl"
    path.write_text(
        json.dumps(event(event="start")) + "\n" + '{"event": "store", "op": "ret\n',
        encoding="utf-8",
    )

    log = read_log(path)

    # A live log is being appended to, and by more than one process: a partial
    # last line is an expected state, not a corrupt file.
    assert len(log.events) == 1
    assert log.malformed == [2]


def test_a_json_line_that_is_not_an_object_is_malformed(tmp_path):
    path = tmp_path / "log.jsonl"
    path.write_text("[1, 2, 3]\n" + json.dumps(event(event="start")) + "\n", encoding="utf-8")

    log = read_log(path)

    assert len(log.events) == 1
    assert log.malformed == [1]


def test_blank_lines_are_not_malformed(tmp_path):
    path = tmp_path / "log.jsonl"
    path.write_text("\n" + json.dumps(event(event="start")) + "\n\n", encoding="utf-8")

    assert read_log(path).malformed == []


# -- sessions --------------------------------------------------------------


def test_events_are_grouped_by_the_process_that_wrote_them(tmp_path):
    log = read_log(
        write(
            tmp_path / "log.jsonl",
            event("aaa", 1, event="start"),
            event("bbb", 1, event="start"),
            event("aaa", 2, event="store", op="list_keys"),
        )
    )

    assert [session.id for session in log.sessions] == ["aaa", "bbb"]
    assert [event.seq for event in log.sessions[0].events] == [1, 2]


def test_sequence_numbers_are_ordered_within_a_session_not_across_the_file(tmp_path):
    # Two processes appending to one file: seq restarts, so sorting the whole
    # file by it interleaves them into an order neither of them ran in.
    log = read_log(
        write(
            tmp_path / "log.jsonl",
            event("aaa", 1, event="start"),
            event("aaa", 9, event="store", op="delete"),
            event("bbb", 1, event="start"),
            event("aaa", 5, event="store", op="list_keys"),
        )
    )

    first, second = log.sessions
    assert [event.seq for event in first.events] == [1, 5, 9]
    assert [event.seq for event in second.events] == [1]


def test_a_session_reports_the_process_it_was(tmp_path):
    log = read_log(
        write(tmp_path / "log.jsonl", event("aaa", 1, event="start", pid=42, version="0.1.0"))
    )

    session = log.sessions[0]
    assert (session.pid, session.version) == (42, "0.1.0")


def test_the_discovery_process_is_named_so_it_is_not_mistaken_for_the_server(tmp_path):
    log = read_log(
        write(
            tmp_path / "log.jsonl",
            event("aaa", 1, event="start", pid=1),
            event("aaa", 2, event="request", call=1, method="server/discover", result={"ok": True}),
        )
    )

    assert log.sessions[0].is_discovery
    assert "discovery only" in logread.format_session(log.sessions[0])


def test_a_filtered_view_is_not_reported_as_the_discovery_process(tmp_path):
    # A filter that removes the tool calls leaves a session that looks idle.
    # Saying "discovery" there would send a search to the wrong process.
    log = read_log(
        write(
            tmp_path / "log.jsonl",
            event("aaa", 1, event="start", pid=1),
            event("aaa", 2, event="request", call=1, method="tools/call", result={"ok": True}),
        )
    )

    selected = Filter(event="start").select(log.events)

    assert not sessions(selected)[0].is_discovery


# -- filtering -------------------------------------------------------------


@pytest.fixture
def mixed(tmp_path):
    return read_log(
        write(
            tmp_path / "log.jsonl",
            event("aaa", 1, event="start"),
            store_event("aaa", 2, "get_documents", call=1, args={"meta_name": ["title"]}),
            event(
                "aaa",
                3,
                event="request",
                call=1,
                method="tools/call",
                params={"name": "get_documents", "arguments": {"meta_name": ["title"]}},
                result={"ok": True},
            ),
            store_event(
                "bbb",
                1,
                "retrieve_document",
                call=1,
                args={"key": "context/5/state"},
                error={"type": "KeyNotFoundError", "message": "nothing is stored there"},
            ),
        )
    )


def test_filtering_by_operation(mixed):
    assert [e.op for e in Filter(op="get_documents").select(mixed.events)] == ["get_documents"]


def test_filtering_by_method(mixed):
    assert len(Filter(method="tools/call").select(mixed.events)) == 1


def test_filtering_by_session_accepts_a_prefix(mixed):
    assert {e.session for e in Filter(session="bb").select(mixed.events)} == {"bbb"}


def test_filtering_by_key_matches_a_substring(mixed):
    assert [e.key for e in Filter(key="context/5").select(mixed.events)] == ["context/5/state"]


def test_filtering_by_error_finds_both_layers(tmp_path):
    log = read_log(
        write(
            tmp_path / "log.jsonl",
            store_event("aaa", 1, call=1, error={"type": "ValueError", "message": "bad"}),
            event(
                "aaa",
                2,
                event="request",
                call=1,
                method="tools/call",
                result={"ok": False, "message": "Error executing tool"},
            ),
            store_event("aaa", 3, call=2, result={"count": 1}),
        )
    )

    # A tool that returns an error result never raises, so a reader that looked
    # only for `error` would report every rejected call as a success — the bug
    # the writer itself shipped with.
    assert [e.seq for e in Filter(errors=True).select(log.events)] == [1, 2]


def test_filters_combine(mixed):
    assert Filter(op="get_documents", session="bbb").select(mixed.events) == []


# -- the arguments a call carried ------------------------------------------


def test_the_arguments_of_a_store_access_are_reachable(mixed):
    access = Filter(op="get_documents").select(mixed.events)[0]

    assert access.args["meta_name"] == ["title"]


def test_the_arguments_of_a_request_are_reachable_the_same_way(mixed):
    # "Which meta_name did that search screen on" is the question the log
    # settled first, and it must not depend on which layer recorded the call.
    request = Filter(method="tools/call").select(mixed.events)[0]

    assert request.args["meta_name"] == ["title"]
    assert request.tool == "get_documents"


# -- truncation and follow-up ----------------------------------------------


def test_a_read_resumed_at_next_offset_counts_as_followed_up(tmp_path):
    log = read_log(
        write(
            tmp_path / "log.jsonl",
            read("aaa", 1, "notes", total=100, returned=60),
            read("aaa", 2, "notes", offset=60, total=100, returned=40),
        )
    )

    truncated = logread.truncated_reads(log.sessions[0])

    assert len(truncated) == 1
    assert truncated[0].followed_up


def test_reading_the_same_key_again_from_the_top_is_not_a_follow_up(tmp_path):
    log = read_log(
        write(
            tmp_path / "log.jsonl",
            read("aaa", 1, "notes", total=100, returned=60),
            read("aaa", 2, "notes", total=100, returned=60),
        )
    )

    # A caller that starts over has not collected the rest of the document.
    # Matching on the key alone would answer the question backwards.
    assert [read.followed_up for read in logread.truncated_reads(log.sessions[0])] == [False, False]


def test_a_follow_up_by_another_session_does_not_count(tmp_path):
    log = read_log(
        write(
            tmp_path / "log.jsonl",
            read("aaa", 1, "notes", total=100, returned=60),
            read("bbb", 1, "notes", offset=60, total=100, returned=40),
        )
    )

    assert not logread.truncated_reads(log.sessions[0])[0].followed_up


def test_a_whole_read_is_not_truncated(tmp_path):
    log = read_log(write(tmp_path / "log.jsonl", read("aaa", 1, "notes", total=100)))

    assert logread.truncated_reads(log.sessions[0]) == []


# -- the summary -----------------------------------------------------------


def test_accesses_are_counted_per_call_within_a_session(tmp_path):
    log = read_log(
        write(
            tmp_path / "log.jsonl",
            store_event("aaa", 1, call=5, result={"count": 1}),
            store_event("aaa", 2, call=5, result={"count": 1}),
            store_event("bbb", 1, call=5, result={"count": 1}),
        )
    )

    summary = summarise(log)

    # Two sessions' call 5 are two different calls. Adding them together
    # invents a call that touched the store three times, which no call did.
    assert summary.accesses_per_call == {("aaa", 5): 2, ("bbb", 5): 1}
    assert summary.busiest_call == (2, "aaa", 5)


def test_the_two_layers_of_a_single_failure_are_counted_apart(tmp_path):
    log = read_log(
        write(
            tmp_path / "log.jsonl",
            store_event("aaa", 1, call=1, error={"type": "KeyNotFoundError", "message": "no"}),
            event(
                "aaa",
                2,
                event="request",
                call=1,
                method="tools/call",
                result={"ok": False, "message": "Error executing tool"},
            ),
        )
    )

    summary = summarise(log)

    # One failing call, seen twice. Counting both under one label would double
    # every error in the file.
    assert summary.errors == {"KeyNotFoundError": 1}
    assert summary.refused == 1


def test_the_summary_describes_a_filtered_slice(tmp_path):
    log = read_log(
        write(
            tmp_path / "log.jsonl",
            store_event("aaa", 1, call=1, result={"count": 1}),
            store_event("bbb", 1, call=1, result={"count": 1}),
        )
    )

    summary = summarise(log, Filter(session="aaa").select(log.events))

    assert summary.store_accesses == 1
    assert [session.id for session in summary.sessions] == ["aaa"]


def test_the_summary_counts_truncated_reads_and_the_ones_resumed(tmp_path):
    log = read_log(
        write(
            tmp_path / "log.jsonl",
            read("aaa", 1, "notes", total=100, returned=60),
            read("aaa", 2, "notes", offset=60, total=100, returned=40),
            read("aaa", 3, "other", total=100, returned=50),
        )
    )

    summary = summarise(log)

    assert (summary.reads, len(summary.truncated), summary.followed_up) == (3, 2, 1)


def test_documents_truncated_inside_a_survey_are_counted(tmp_path):
    log = read_log(
        write(
            tmp_path / "log.jsonl",
            store_event("aaa", 1, "get_documents", call=1, result={"count": 9, "truncated": 3}),
        )
    )

    assert summarise(log).documents_truncated == 3


# -- rendering -------------------------------------------------------------


def line(event_record: dict, **kwargs) -> str:
    return "\n".join(logread.format_event(Event(line=1, record=event_record), **kwargs))


def test_an_event_line_names_the_call_the_operation_and_the_outcome():
    rendered = line(
        store_event("aaa", 9, call=6, args={"key": "context/5/state"}, result={"count": 4})
    )

    assert "call 6" in rendered
    assert "retrieve_document" in rendered
    assert "key=context/5/state" in rendered


def test_a_truncated_read_says_where_the_rest_begins():
    assert "more at 60" in line(read("aaa", 1, "notes", total=100, returned=60))


def test_an_argument_that_was_never_passed_is_not_a_column():
    # The writer renders a non-string under the content policy as its type
    # alone, so an omitted title arrives as {"type": "NoneType"}.
    rendered = line(
        store_event(
            "aaa",
            1,
            "store_document",
            args={"key": "notes", "title": {"type": "NoneType"}},
            result={"key": "notes"},
        )
    )

    assert "title" not in rendered


def test_a_long_failure_message_is_capped():
    rendered = line(store_event("aaa", 1, error={"type": "ValueError", "message": "x" * 400}))

    assert "…" in rendered
    assert len(rendered) < 300


def test_the_excerpt_is_shown_only_when_asked_for():
    record = store_event(
        "aaa",
        1,
        "store_document",
        args={"key": "notes", "content": {"len": 900, "head": "the start", "tail": "the end"}},
        result={"key": "notes"},
    )

    assert "the start" not in line(record)
    assert "the start" in line(record, content=True)


def test_the_gap_in_an_excerpt_is_marked_rather_than_closed():
    # The failure this was built to catch was scaffolding appended after a
    # summary that read correctly to its last sentence. Joining the two ends
    # would render exactly that as one clean document.
    rendered = line(
        store_event(
            "aaa",
            1,
            "store_document",
            args={"content": {"len": 900, "head": "the start", "tail": "the end"}},
        ),
        content=True,
    )

    assert "884 chars not recorded" in rendered
    assert "the startthe end" not in rendered


def test_the_summary_renders_the_standing_questions(tmp_path):
    log = read_log(
        write(
            tmp_path / "log.jsonl",
            event("aaa", 1, event="start", pid=7, version="0.1.0"),
            read("aaa", 2, "notes", total=100, returned=60),
        )
    )

    rendered = "\n".join(logread.format_summary(summarise(log)))

    assert "1 document reads, 1 truncated" in rendered
    assert "0 of those resumed" in rendered
    assert "abandoned: notes at 60" in rendered
