"""Tests for the command line front end.

Thin by design, so these cover what argparse and the printing add: the
defaults, that --dry-run really does not write, and that a refusal reaches the
user as a message and a non-zero status rather than a traceback.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from rage.cli import main, parse_args


def run(*argv: str) -> tuple[int, str]:
    out = io.StringIO()
    status = main(list(argv), out)
    return status, out.getvalue()


def servers(path: Path) -> dict:
    return json.loads(path.read_text())["mcpServers"]


def test_config_writes_the_project_file(tmp_path):
    status, output = run("config", "--project-dir", str(tmp_path))

    assert status == 0
    entry = servers(tmp_path / ".mcp.json")["rage"]
    assert Path(entry["command"]).is_absolute()
    assert entry["args"][-1] == str(tmp_path / ".rage")
    assert str(tmp_path / ".mcp.json") in output


def test_store_directory_defaults_beside_the_project(tmp_path):
    run("config", "--project-dir", str(tmp_path))

    entry = servers(tmp_path / ".mcp.json")["rage"]
    assert entry["args"][entry["args"].index("--dir") + 1] == str(tmp_path / ".rage")


def test_explicit_store_directory_is_used(tmp_path):
    elsewhere = tmp_path / "notes"

    run("config", "--project-dir", str(tmp_path), "--dir", str(elsewhere))

    entry = servers(tmp_path / ".mcp.json")["rage"]
    assert entry["args"][-1] == str(elsewhere)


def test_dry_run_reports_without_writing(tmp_path):
    status, output = run("config", "--project-dir", str(tmp_path), "--dry-run")

    assert status == 0
    assert "would add" in output
    assert not (tmp_path / ".mcp.json").exists()


def test_dry_run_of_a_rerun_says_nothing_would_change(tmp_path):
    run("config", "--project-dir", str(tmp_path))

    _, output = run("config", "--project-dir", str(tmp_path), "--dry-run")

    assert "already current" in output


def test_report_names_both_paths_it_guessed(tmp_path):
    # The two guesses are the whole command, and both fail silently at launch
    # if wrong, so both have to be visible before anyone runs the server.
    _, output = run("config", "--project-dir", str(tmp_path))

    entry = servers(tmp_path / ".mcp.json")["rage"]
    assert entry["command"] in output
    assert str(tmp_path / ".rage") in output


def test_an_update_shows_what_it_replaced(tmp_path):
    path = tmp_path / ".mcp.json"
    path.write_text(
        json.dumps({"mcpServers": {"rage": {"command": "/old/bin/rage-server", "args": []}}}),
        encoding="utf-8",
    )

    _, output = run("config", "--project-dir", str(tmp_path))

    assert "was: /old/bin/rage-server" in output
    assert "now:" in output


def test_explicit_path_overrides_the_scope(tmp_path):
    target = tmp_path / "nested" / "custom.json"

    run("config", "--project-dir", str(tmp_path), "--path", str(target))

    assert "rage" in servers(target)
    assert not (tmp_path / ".mcp.json").exists()


def test_custom_name_is_registered(tmp_path):
    run("config", "--project-dir", str(tmp_path), "--name", "rage-notes")

    assert set(servers(tmp_path / ".mcp.json")) == {"rage-notes"}


def test_a_refusal_is_a_message_and_a_status(tmp_path, capsys):
    path = tmp_path / ".mcp.json"
    path.write_text("{not json", encoding="utf-8")

    status = main(["config", "--project-dir", str(tmp_path)], io.StringIO())

    assert status == 1
    assert "not valid JSON" in capsys.readouterr().err
    assert path.read_text() == "{not json"


def test_user_scope_targets_the_home_file(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    run("config", "--scope", "user", "--project-dir", str(tmp_path))

    assert "rage" in servers(tmp_path / ".claude.json")


def test_config_leaves_logging_off_by_default(tmp_path):
    run("config", "--project-dir", str(tmp_path))

    # It records document text, so it is never turned on by a command that was
    # not asked to turn it on.
    assert "--log" not in servers(tmp_path / ".mcp.json")["rage"]["args"]


def test_config_can_turn_logging_on(tmp_path):
    status, output = run("config", "--project-dir", str(tmp_path), "--log")

    assert status == 0
    assert servers(tmp_path / ".mcp.json")["rage"]["args"][-1] == "--log"
    assert "--log" in output


def test_scope_defaults_to_project():
    assert parse_args(["config"]).scope == "project"


def test_a_command_is_required():
    with pytest.raises(SystemExit):
        parse_args([])


# -- backup --------------------------------------------------------------


def a_store(directory: Path) -> None:
    from rage.store import Store

    with Store(directory) as store:
        store.store_document("context/1/task", "Build the backup command.", title="Task")


def test_backup_writes_a_snapshot_and_says_what_it_checked(tmp_path):
    a_store(tmp_path / ".rage")

    status, output = run("backup", "--dir", str(tmp_path / ".rage"))

    assert status == 0
    (written,) = (tmp_path / ".rage" / "backups").glob("store-*.sqlite")
    assert str(written) in output
    assert "2 documents" in output
    assert "integrity ok" in output


def test_backup_takes_a_destination(tmp_path):
    a_store(tmp_path / ".rage")

    status, _ = run("backup", "--dir", str(tmp_path / ".rage"), "--to", str(tmp_path / "s.sqlite"))

    assert status == 0
    assert (tmp_path / "s.sqlite").exists()


def test_backup_dry_run_names_the_destination_without_writing(tmp_path):
    a_store(tmp_path / ".rage")

    status, output = run("backup", "--dir", str(tmp_path / ".rage"), "--dry-run")

    assert status == 0
    assert "would back up" in output
    assert not (tmp_path / ".rage" / "backups").exists()


def test_backing_up_a_store_that_is_not_there_is_refused(tmp_path, capsys):
    status = main(["backup", "--dir", str(tmp_path / "absent")], io.StringIO())

    assert status == 1
    assert "no store in" in capsys.readouterr().err
    # Refused rather than created, or the backup would be of a store the
    # caller never had.
    assert not (tmp_path / "absent").exists()


def test_an_existing_destination_reaches_the_user_as_a_message(tmp_path, capsys):
    a_store(tmp_path / ".rage")
    target = tmp_path / "taken.sqlite"
    target.write_text("mine")

    status = main(["backup", "--dir", str(tmp_path / ".rage"), "--to", str(target)], io.StringIO())

    assert status == 1
    assert "already exists" in capsys.readouterr().err
    assert target.read_text() == "mine"


# -- log -------------------------------------------------------------------


def a_log(directory: Path) -> Path:
    """A log holding a discovery process and a serving one, as a real file does."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "log.jsonl"
    records = [
        {
            "ts": "2026-08-17T19:43:04.079+00:00",
            "seq": 1,
            "session": "aaa",
            "event": "start",
            "pid": 1,
            "version": "0.1.0",
        },
        {
            "ts": "2026-08-17T19:43:04.107+00:00",
            "seq": 2,
            "session": "aaa",
            "event": "request",
            "call": 1,
            "method": "server/discover",
            "result": {"ok": True},
        },
        {
            "ts": "2026-08-17T19:43:05.000+00:00",
            "seq": 1,
            "session": "bbb",
            "event": "start",
            "pid": 2,
            "version": "0.1.0",
        },
        {
            "ts": "2026-08-17T19:43:06.000+00:00",
            "seq": 2,
            "session": "bbb",
            "event": "store",
            "call": 1,
            "op": "retrieve_document",
            "args": {"key": "context/5/state", "offset": 0},
            "result": {
                "total": 100,
                "returned": 60,
                "next_offset": 60,
                "content": {"len": 100, "head": "HEAD-MARK", "tail": "TAIL-MARK"},
            },
        },
        {
            "ts": "2026-08-17T19:43:06.100+00:00",
            "seq": 3,
            "session": "bbb",
            "event": "request",
            "call": 1,
            "method": "tools/call",
            "params": {"name": "retrieve_document", "arguments": {"key": "context/5/state"}},
            "result": {"ok": True},
        },
    ]
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return path


def test_log_groups_events_under_the_process_that_wrote_them(tmp_path):
    a_log(tmp_path / ".rage")

    status, output = run("log", "--dir", str(tmp_path / ".rage"))

    assert status == 0
    # The header is what says which process the sequence numbers belong to;
    # one file holds more than one and their numbering collides.
    assert "session aaa" in output and "session bbb" in output
    assert "discovery only" in output
    assert "retrieve_document" in output


def test_log_filters_by_operation(tmp_path):
    a_log(tmp_path / ".rage")

    status, output = run("log", "--dir", str(tmp_path / ".rage"), "--op", "retrieve_document")

    assert status == 0
    assert "server/discover" not in output


def test_log_summary_reports_truncation_and_whether_it_was_resumed(tmp_path):
    a_log(tmp_path / ".rage")

    status, output = run("log", "--dir", str(tmp_path / ".rage"), "--summary")

    assert status == 0
    assert "1 document reads, 1 truncated" in output
    assert "0 of those resumed" in output


def test_log_content_is_shown_only_when_asked_for(tmp_path):
    a_log(tmp_path / ".rage")

    _, without = run("log", "--dir", str(tmp_path / ".rage"))
    _, with_content = run("log", "--dir", str(tmp_path / ".rage"), "--content")

    assert "HEAD-MARK" not in without
    assert "HEAD-MARK" in with_content and "TAIL-MARK" in with_content


def test_log_json_prints_the_records_as_they_were_written(tmp_path):
    a_log(tmp_path / ".rage")

    _, output = run("log", "--dir", str(tmp_path / ".rage"), "--op", "retrieve_document", "--json")

    (record,) = [json.loads(line) for line in output.splitlines() if line.strip()]
    # The whole record: the line summary drops an offset of 0 as noise, and
    # --json is what that trade is defensible against.
    assert record["args"]["offset"] == 0
    assert record["result"]["next_offset"] == 60


def test_log_limit_keeps_the_end_and_says_what_it_dropped(tmp_path):
    a_log(tmp_path / ".rage")

    _, output = run("log", "--dir", str(tmp_path / ".rage"), "--limit", "1")

    assert "4 earlier matching events not shown" in output
    assert "session bbb" in output and "session aaa" not in output


def test_log_finds_the_file_beside_the_store_by_default(tmp_path, monkeypatch):
    a_log(tmp_path / ".rage")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RAGE_LOG", raising=False)
    monkeypatch.delenv("RAGE_DIR", raising=False)

    status, output = run("log")

    assert status == 0
    assert "session bbb" in output


def test_a_missing_log_reaches_the_user_as_a_message(tmp_path, capsys):
    status = main(["log", "--dir", str(tmp_path / "absent")], io.StringIO())

    assert status == 1
    assert "no log file at" in capsys.readouterr().err


def test_a_filter_matching_nothing_says_so(tmp_path):
    a_log(tmp_path / ".rage")

    status, output = run("log", "--dir", str(tmp_path / ".rage"), "--op", "delete")

    assert status == 0
    assert "no matching events" in output


# -- dump ----------------------------------------------------------------


def a_long_store(directory: Path, size: int = 5000) -> str:
    """A store holding one document longer than the bulk cap, and its content."""
    from rage.store import Store

    content = "start\n" + "filler line\n" * size + "end of the document\n"
    with Store(directory) as store:
        store.store_document("notes/long", content, title="A long document")
    return content


def test_dump_prints_a_long_document_whole(tmp_path):
    content = a_long_store(tmp_path / ".rage")

    status, output = run("dump", "--dir", str(tmp_path / ".rage"), "notes/long")

    assert status == 0
    # The end matters more than the length: a cut export reads correctly right
    # up to where it stops, which is why nothing downstream notices.
    assert "end of the document" in output
    assert "characters]" not in output
    assert content in output


def test_dump_caps_each_document_when_asked(tmp_path):
    a_long_store(tmp_path / ".rage")

    status, output = run(
        "dump", "--dir", str(tmp_path / ".rage"), "notes/long", "--max-chars", "100"
    )

    assert status == 0
    assert "end of the document" not in output
    assert "[100 of " in output


def test_dump_reads_long_metadata_to_the_end_too(tmp_path):
    from rage.store import Store

    value = "a very long summary. " * 400
    with Store(tmp_path / ".rage") as store:
        store.store_document("notes/long", "body", title="Short")
        store.store_document("notes/long:summary", value)

    status, output = run("dump", "--dir", str(tmp_path / ".rage"), "--meta", "summary")

    assert status == 0
    assert value in output
    assert "characters]" not in output


def test_dump_exports_a_subtree_at_full_length(tmp_path):
    from rage.store import Store

    with Store(tmp_path / ".rage") as store:
        for name in ("one", "two"):
            store.store_document(f"notes/{name}", "x" * 4000, title=name)

    status, output = run("dump", "--dir", str(tmp_path / ".rage"), "notes")

    assert status == 0
    assert output.count("x" * 4000) == 2
