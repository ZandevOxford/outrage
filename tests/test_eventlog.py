"""Tests for the event log itself, independently of what it records.

Two properties matter more than the rest. The log must never be able to break
the call it is recording, since a store that fails because its log failed is a
worse trade than an unlogged store. And what it writes must be readable after
the fact by something other than this process - one JSON object per line, from
however many writers.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from outrage import eventlog
from outrage.eventlog import EventLog


@pytest.fixture
def log(tmp_path):
    log = EventLog(tmp_path / "log.jsonl")
    yield log
    log.close()


def lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


# -- writing ---------------------------------------------------------------


def test_each_event_is_one_json_object_on_its_own_line(log, tmp_path):
    log.emit("store", op="retrieve_document")
    log.emit("store", op="list_keys")

    assert [event["op"] for event in lines(tmp_path / "log.jsonl")] == [
        "retrieve_document",
        "list_keys",
    ]


def test_sequence_numbers_order_events_within_a_second(log, tmp_path):
    for _ in range(5):
        log.emit("store", op="list_keys")

    # The clock is not fine enough to separate these, so ordering rests on seq.
    assert [event["seq"] for event in lines(tmp_path / "log.jsonl")] == [1, 2, 3, 4, 5]


def test_every_event_carries_the_session(log, tmp_path):
    log.emit("store", op="list_keys")

    assert lines(tmp_path / "log.jsonl")[0]["session"] == log.session


def test_a_log_with_no_path_writes_nothing(tmp_path):
    log = EventLog(None)
    log.emit("store", op="list_keys")

    assert not log.enabled
    assert list(tmp_path.iterdir()) == []


def test_the_file_is_not_readable_by_everyone(log, tmp_path):
    log.emit("store", op="list_keys")

    # It holds document text, so it should not be more readable than the
    # documents themselves.
    assert stat.S_IMODE((tmp_path / "log.jsonl").stat().st_mode) == 0o600


def test_an_event_appends_rather_than_replacing(tmp_path):
    first = EventLog(tmp_path / "log.jsonl")
    first.emit("start")
    first.close()
    second = EventLog(tmp_path / "log.jsonl")
    second.emit("start")
    second.close()

    assert len(lines(tmp_path / "log.jsonl")) == 2


def test_two_processes_appending_do_not_damage_each_other_s_lines(tmp_path):
    path = tmp_path / "log.jsonl"
    script = (
        "from outrage.eventlog import EventLog;"
        f"log = EventLog({str(path)!r});"
        "[log.emit('store', op='list_keys', filler='x' * 200) for _ in range(100)];"
        "log.close()"
    )
    running = [subprocess.Popen([sys.executable, "-c", script]) for _ in range(2)]
    for process in running:
        assert process.wait() == 0

    # Interleaved writes would show up as a line that does not parse, not as a
    # missing one, so the count and the parse together are the assertion.
    assert len(lines(path)) == 200


# -- failure ---------------------------------------------------------------


def test_a_write_failure_disables_the_log_without_raising(log, tmp_path, monkeypatch, capsys):
    def explode(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(os, "write", explode)
    log.emit("store", op="list_keys")

    assert not log.enabled
    assert "disk full" in capsys.readouterr().err


def test_a_disabled_log_reports_once_and_then_stays_quiet(log, monkeypatch, capsys):
    def explode(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(os, "write", explode)
    log.emit("store", op="list_keys")
    capsys.readouterr()
    log.emit("store", op="list_keys")

    # A message per call would be a failure repeated onto a stream the client
    # shows the user, for a log that already stopped after the first one.
    assert capsys.readouterr().err == ""


def test_an_unopenable_path_is_reported_rather_than_raised(tmp_path, capsys):
    blocking = tmp_path / "notadir"
    blocking.write_text("", encoding="utf-8")

    log = EventLog(blocking / "log.jsonl")

    assert not log.enabled
    assert "event log disabled" in capsys.readouterr().err


def test_an_unserialisable_value_is_rendered_rather_than_losing_the_log(log, tmp_path):
    log.emit("store", op="list_keys", path=Path("/tmp/x"))

    # Better a value rendered as its repr than an exception that costs every
    # event after it.
    assert lines(tmp_path / "log.jsonl")[0]["path"] == "/tmp/x"


# -- content ---------------------------------------------------------------


def test_a_long_value_keeps_both_ends_and_the_hash_of_the_whole(log):
    text = "head" + "-" * 500 + "tail"
    field = log.content_field(text)

    # The tail matters: the failure that prompted this log appended scaffolding
    # after content that read correctly to its last sentence.
    assert field["head"].startswith("head")
    assert field["tail"].endswith("tail")
    assert field["len"] == len(text)
    assert "text" not in field


def test_a_short_value_is_kept_whole(log):
    assert log.content_field("hello")["text"] == "hello"


def test_content_none_keeps_the_length_and_the_hash_but_no_text(tmp_path):
    log = EventLog(tmp_path / "log.jsonl", content="none")
    field = log.content_field("x" * 500)

    assert field["len"] == 500
    assert field["sha256"]
    assert "text" not in field and "head" not in field
    log.close()


def test_content_full_keeps_everything(tmp_path):
    log = EventLog(tmp_path / "log.jsonl", content="full")

    assert log.content_field("x" * 500)["text"] == "x" * 500
    log.close()


def test_the_hash_is_of_the_whole_value_not_the_excerpt(log):
    long = log.content_field("x" * 500)
    same = EventLog(None, content="full").content_field("x" * 500)

    assert long["sha256"] == same["sha256"]


def test_only_the_content_bearing_arguments_are_policed(log):
    scrubbed = log.arguments({"key": "a/b", "content": "hello", "recursive": True})

    assert scrubbed["key"] == "a/b"
    assert scrubbed["recursive"] is True
    assert scrubbed["content"]["text"] == "hello"


def test_a_boolean_title_control_is_not_mistaken_for_title_content(log):
    scrubbed = log.arguments({"key": "a/b", "title": False})

    assert scrubbed["title"] is False


def test_an_unknown_content_policy_is_refused():
    with pytest.raises(ValueError, match="content must be one of"):
        EventLog(None, content="some")


# -- correlation -----------------------------------------------------------


def test_events_carry_the_call_they_were_made_under(log, tmp_path):
    token = eventlog.current_call.set(7)
    log.emit("store", op="list_keys")
    eventlog.current_call.reset(token)
    log.emit("store", op="list_keys")

    recorded = lines(tmp_path / "log.jsonl")
    assert recorded[0]["call"] == 7
    assert "call" not in recorded[1]


# -- resolution ------------------------------------------------------------


def test_a_bare_flag_puts_the_log_beside_the_store(tmp_path):
    assert eventlog.resolve_path(eventlog.DEFAULT, tmp_path) == tmp_path / "log.jsonl"


def test_an_explicit_path_wins(tmp_path, monkeypatch):
    monkeypatch.setenv(eventlog.ENV_LOG, "/from/env")

    assert eventlog.resolve_path("/explicit", tmp_path) == Path("/explicit")


def test_the_environment_is_consulted_next(tmp_path, monkeypatch):
    monkeypatch.setenv(eventlog.ENV_LOG, "/from/env")

    assert eventlog.resolve_path(None, tmp_path) == Path("/from/env")


def test_nothing_at_all_means_no_log(tmp_path, monkeypatch):
    monkeypatch.delenv(eventlog.ENV_LOG, raising=False)

    # There is no default location, because the default is not to log.
    assert eventlog.resolve_path(None, tmp_path) is None
