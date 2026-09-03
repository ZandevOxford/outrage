"""Tests for the command line front end.

Thin by design, so these cover what argparse and the printing add: the
defaults, that --dry-run really does not write, and that a refusal reaches the
user as a message and a non-zero status rather than a traceback.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from outrage import install as install_module
from outrage import mountfile, mounts, shipped
from outrage.cli import main, parse_args


def run(*argv: str) -> tuple[int, str]:
    out = io.StringIO()
    status = main(list(argv), out)
    return status, out.getvalue()


def servers(path: Path) -> dict:
    return json.loads(path.read_text())["mcpServers"]


def test_sessionstart_emits_the_shipped_prompt_as_hook_json():
    status, output = run("sessionstart")

    assert status == 0
    assert json.loads(output) == install_module.sessionstart_payload()


def test_sessionstart_emits_the_flat_copilot_payload_when_selected():
    status, output = run("sessionstart", "--copilot")

    assert status == 0
    assert json.loads(output) == install_module.sessionstart_payload(copilot=True)


def test_python_m_outrage_dispatches_sessionstart_to_the_cli():
    result = subprocess.run(
        [sys.executable, "-m", "outrage", "sessionstart", install_module.SESSIONSTART_MARKER],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == install_module.sessionstart_payload()


def test_config_writes_the_project_file(tmp_path):
    status, output = run("config", "--project-dir", str(tmp_path))

    assert status == 0
    entry = servers(tmp_path / ".mcp.json")["outrage"]
    assert Path(entry["command"]).is_absolute()
    assert entry["args"][-1] == str(tmp_path / ".outrage")
    assert str(tmp_path / ".mcp.json") in output


def test_store_directory_defaults_beside_the_project(tmp_path):
    run("config", "--project-dir", str(tmp_path))

    entry = servers(tmp_path / ".mcp.json")["outrage"]
    assert entry["args"][entry["args"].index("--dir") + 1] == str(tmp_path / ".outrage")


def test_explicit_store_directory_is_used(tmp_path):
    elsewhere = tmp_path / "notes"

    run("config", "--project-dir", str(tmp_path), "--dir", str(elsewhere))

    entry = servers(tmp_path / ".mcp.json")["outrage"]
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

    entry = servers(tmp_path / ".mcp.json")["outrage"]
    assert entry["command"] in output
    assert str(tmp_path / ".outrage") in output


def test_an_update_shows_what_it_replaced(tmp_path):
    path = tmp_path / ".mcp.json"
    path.write_text(
        json.dumps({"mcpServers": {"outrage": {"command": "/old/bin/outrage-server", "args": []}}}),
        encoding="utf-8",
    )

    _, output = run("config", "--project-dir", str(tmp_path))

    assert "was: /old/bin/outrage-server" in output
    assert "now:" in output


def test_explicit_path_overrides_the_scope(tmp_path):
    target = tmp_path / "nested" / "custom.json"

    run("config", "--project-dir", str(tmp_path), "--path", str(target))

    assert "outrage" in servers(target)
    assert not (tmp_path / ".mcp.json").exists()


def test_custom_name_is_registered(tmp_path):
    run("config", "--project-dir", str(tmp_path), "--name", "outrage-notes")

    assert set(servers(tmp_path / ".mcp.json")) == {"outrage-notes"}


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

    assert "outrage" in servers(tmp_path / ".claude.json")


def test_config_leaves_logging_off_by_default(tmp_path):
    run("config", "--project-dir", str(tmp_path))

    # It records document text, so it is never turned on by a command that was
    # not asked to turn it on.
    assert "--log" not in servers(tmp_path / ".mcp.json")["outrage"]["args"]


def test_config_can_turn_logging_on(tmp_path):
    status, output = run("config", "--project-dir", str(tmp_path), "--log")

    assert status == 0
    assert servers(tmp_path / ".mcp.json")["outrage"]["args"][-1] == "--log"
    assert "--log" in output


def test_config_writes_the_mounts_to_the_table_beside_the_stores(tmp_path):
    """And leaves the entry carrying nothing but --dir, which is the payoff."""
    from outrage import mountfile

    status, output = run(
        "config",
        "--project-dir",
        str(tmp_path),
        "--root-mount",
        "main.sqlite",
        "--mount",
        "lib=lib.sqlite",
        "--mount-ro",
        "ref=reference.sqlite",
    )

    assert status == 0
    args = servers(tmp_path / ".mcp.json")["outrage"]["args"]
    assert args == ["--dir", str(tmp_path / ".outrage")]

    table = tmp_path / ".outrage" / mountfile.DEFAULT_NAME
    written = mountfile.read(table)
    assert written.root == mounts.Spec(Path("main.sqlite"))
    assert written.mounts == (("lib", mounts.Spec(Path("lib.sqlite"))),)
    assert written.read_only == (("ref", mounts.Spec(Path("reference.sqlite"))),)
    assert str(table) in output
    # A store is named relative to the directory, so only --dir is a path: it
    # is what lets the project move with one line to fix.
    assert "/" not in table.read_text().split("[mount]")[1]


def test_config_declines_to_rewrite_a_table_and_says_what_to_add(tmp_path):
    from outrage import mountfile

    run("config", "--project-dir", str(tmp_path), "--mount", "lib=lib.sqlite")
    table = tmp_path / ".outrage" / mountfile.DEFAULT_NAME
    before = table.read_text()

    status, output = run("config", "--project-dir", str(tmp_path), "--mount", "other=other.sqlite")

    assert status == 0
    assert table.read_text() == before
    assert "not rewritten" in output
    assert 'other = "other.sqlite"' in output


def test_config_without_mounts_writes_no_table_at_all(tmp_path):
    """`config` registers a server; creating a store directory to drop an empty
    file into it is not something it was asked to do."""
    from outrage import mountfile

    status, output = run("config", "--project-dir", str(tmp_path))

    assert status == 0
    assert not (tmp_path / ".outrage" / mountfile.DEFAULT_NAME).exists()
    assert "mount table" not in output


def test_a_command_reaches_a_second_store_in_the_same_directory(tmp_path):
    from outrage.store_sqlite import SqliteStore

    with SqliteStore(tmp_path / ".outrage", filename="ref.sqlite") as other:
        other.store_document("only/here", "in the second store")

    status, output = run(
        "get", "--dir", str(tmp_path / ".outrage"), "--store", "ref.sqlite", "only/here"
    )
    assert status == 0
    assert "in the second store" in output

    # And the default store in the same directory does not hold it: two stores
    # in one directory, told apart by the file and nothing else.
    assert main(["get", "--dir", str(tmp_path / ".outrage"), "only/here"], io.StringIO()) == 1


def test_scope_defaults_to_project():
    assert parse_args(["config"]).scope == "project"


def test_a_command_is_required():
    with pytest.raises(SystemExit):
        parse_args([])


# -- backup --------------------------------------------------------------


def a_store(directory: Path) -> None:
    from outrage.store_sqlite import SqliteStore

    with SqliteStore(directory) as store:
        store.store_document("context/1/task", "Build the backup command.", title="Task")


def test_backup_writes_a_snapshot_and_says_what_it_checked(tmp_path):
    a_store(tmp_path / ".outrage")

    status, output = run("backup", "--dir", str(tmp_path / ".outrage"))

    assert status == 0
    (written,) = (tmp_path / ".outrage" / "backups").glob("store-*.sqlite")
    assert str(written) in output
    assert "2 documents" in output
    assert "integrity ok" in output


def test_backup_takes_a_destination(tmp_path):
    a_store(tmp_path / ".outrage")

    status, _ = run(
        "backup", "--dir", str(tmp_path / ".outrage"), "--to", str(tmp_path / "s.sqlite")
    )

    assert status == 0
    assert (tmp_path / "s.sqlite").exists()


def test_backup_dry_run_names_the_destination_without_writing(tmp_path):
    a_store(tmp_path / ".outrage")

    status, output = run("backup", "--dir", str(tmp_path / ".outrage"), "--dry-run")

    assert status == 0
    assert "would back up" in output
    assert not (tmp_path / ".outrage" / "backups").exists()


def test_an_empty_pattern_is_a_message_and_a_status(tmp_path, capsys):
    # It was a traceback until 2026-08-29 - `issues/1`. An empty --pattern is
    # something the person typing it can correct, so by `errors.OutrageError`'s
    # rule it is a sentence, and a traceback would be claiming outrage has a bug.
    from outrage.store_sqlite import SqliteStore

    with SqliteStore(tmp_path) as store:
        store.store_document("notes/one", "hello")

    status = main(["get", "--dir", str(tmp_path), "--pattern", "", "notes/one"], io.StringIO())

    assert status == 1
    assert "must not be empty" in capsys.readouterr().err


def test_backing_up_a_store_that_is_not_there_is_refused(tmp_path, capsys):
    status = main(["backup", "--dir", str(tmp_path / "absent")], io.StringIO())

    assert status == 1
    assert "no store at" in capsys.readouterr().err
    # Refused rather than created, or the backup would be of a store the
    # caller never had.
    assert not (tmp_path / "absent").exists()


def test_an_existing_destination_reaches_the_user_as_a_message(tmp_path, capsys):
    a_store(tmp_path / ".outrage")
    target = tmp_path / "taken.sqlite"
    target.write_text("mine")

    status = main(
        ["backup", "--dir", str(tmp_path / ".outrage"), "--to", str(target)], io.StringIO()
    )

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
            "params": {"name": "read_document", "arguments": {"key": "context/5/state"}},
            "result": {"ok": True},
        },
    ]
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return path


def test_log_groups_events_under_the_process_that_wrote_them(tmp_path):
    a_log(tmp_path / ".outrage")

    status, output = run("log", "--dir", str(tmp_path / ".outrage"))

    assert status == 0
    # The header is what says which process the sequence numbers belong to;
    # one file holds more than one and their numbering collides.
    assert "session aaa" in output and "session bbb" in output
    assert "discovery only" in output
    assert "retrieve_document" in output


def test_log_filters_by_operation(tmp_path):
    a_log(tmp_path / ".outrage")

    status, output = run("log", "--dir", str(tmp_path / ".outrage"), "--op", "retrieve_document")

    assert status == 0
    assert "server/discover" not in output


def test_log_summary_reports_truncation_and_whether_it_was_resumed(tmp_path):
    a_log(tmp_path / ".outrage")

    status, output = run("log", "--dir", str(tmp_path / ".outrage"), "--summary")

    assert status == 0
    assert "1 document reads, 1 truncated" in output
    assert "0 of those resumed" in output


def test_log_content_is_shown_only_when_asked_for(tmp_path):
    a_log(tmp_path / ".outrage")

    _, without = run("log", "--dir", str(tmp_path / ".outrage"))
    _, with_content = run("log", "--dir", str(tmp_path / ".outrage"), "--content")

    assert "HEAD-MARK" not in without
    assert "HEAD-MARK" in with_content and "TAIL-MARK" in with_content


def test_log_json_prints_the_records_as_they_were_written(tmp_path):
    a_log(tmp_path / ".outrage")

    _, output = run(
        "log", "--dir", str(tmp_path / ".outrage"), "--op", "retrieve_document", "--json"
    )

    (record,) = [json.loads(line) for line in output.splitlines() if line.strip()]
    # The whole record: the line summary drops an offset of 0 as noise, and
    # --json is what that trade is defensible against.
    assert record["args"]["offset"] == 0
    assert record["result"]["next_offset"] == 60


def test_log_limit_keeps_the_end_and_says_what_it_dropped(tmp_path):
    a_log(tmp_path / ".outrage")

    _, output = run("log", "--dir", str(tmp_path / ".outrage"), "--limit", "1")

    assert "4 earlier matching events not shown" in output
    assert "session bbb" in output and "session aaa" not in output


def test_log_finds_the_file_beside_the_store_by_default(tmp_path, monkeypatch):
    a_log(tmp_path / ".outrage")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OUTRAGE_LOG", raising=False)
    monkeypatch.delenv("OUTRAGE_DIR", raising=False)

    status, output = run("log")

    assert status == 0
    assert "session bbb" in output


def test_a_missing_log_reaches_the_user_as_a_message(tmp_path, capsys):
    status = main(["log", "--dir", str(tmp_path / "absent")], io.StringIO())

    assert status == 1
    assert "no log file at" in capsys.readouterr().err


def test_a_filter_matching_nothing_says_so(tmp_path):
    a_log(tmp_path / ".outrage")

    status, output = run("log", "--dir", str(tmp_path / ".outrage"), "--op", "delete")

    assert status == 0
    assert "no matching events" in output


# -- dump ----------------------------------------------------------------


def a_long_store(directory: Path, size: int = 5000) -> str:
    """A store holding one document longer than the bulk cap, and its content."""
    from outrage.store_sqlite import SqliteStore

    content = "start\n" + "filler line\n" * size + "end of the document\n"
    with SqliteStore(directory) as store:
        store.store_document("notes/long", content, title="A long document")
    return content


def test_dump_prints_a_long_document_whole(tmp_path):
    content = a_long_store(tmp_path / ".outrage")

    status, output = run("dump", "--dir", str(tmp_path / ".outrage"), "notes/long")

    assert status == 0
    # The end matters more than the length: a cut export reads correctly right
    # up to where it stops, which is why nothing downstream notices.
    assert "end of the document" in output
    assert "characters]" not in output
    assert content in output


def test_dump_caps_each_document_when_asked(tmp_path):
    a_long_store(tmp_path / ".outrage")

    status, output = run(
        "dump", "--dir", str(tmp_path / ".outrage"), "notes/long", "--max-chars", "100"
    )

    assert status == 0
    assert "end of the document" not in output
    assert "[100 of " in output


def test_dump_reads_long_metadata_to_the_end_too(tmp_path):
    from outrage.store_sqlite import SqliteStore

    value = "a very long summary. " * 400
    with SqliteStore(tmp_path / ".outrage") as store:
        store.store_document("notes/long", "body", title="Short")
        store.store_document("notes/long/!summary", value)

    status, output = run("dump", "--dir", str(tmp_path / ".outrage"), "--meta", "summary")

    assert status == 0
    assert value in output
    assert "characters]" not in output


def test_dump_exports_a_subtree_at_full_length(tmp_path):
    from outrage.store_sqlite import SqliteStore

    with SqliteStore(tmp_path / ".outrage") as store:
        for name in ("one", "two"):
            store.store_document(f"notes/{name}", "x" * 4000, title=name)

    status, output = run("dump", "--dir", str(tmp_path / ".outrage"), "notes")

    assert status == 0
    assert output.count("x" * 4000) == 2


# -- get and set ---------------------------------------------------------


def test_get_prints_a_long_document_whole(tmp_path):
    content = a_long_store(tmp_path / ".outrage")

    status, output = run("get", "--dir", str(tmp_path / ".outrage"), "notes/long")

    assert status == 0
    assert output == content


def test_get_writes_no_newline_of_its_own(tmp_path, capsys):
    from outrage.store_sqlite import SqliteStore

    with SqliteStore(tmp_path / ".outrage") as store:
        store.store_document("notes/one", "no trailing newline here")

    _, output = run("get", "--dir", str(tmp_path / ".outrage"), "notes/one")

    assert output == "no trailing newline here"


def test_get_and_set_round_trip_at_the_same_length(tmp_path):
    content = a_long_store(tmp_path / ".outrage")
    exported = tmp_path / "exported.md"

    _, output = run("get", "--dir", str(tmp_path / ".outrage"), "notes/long")
    exported.write_text(output)
    run("set", "--dir", str(tmp_path / ".outrage"), "notes/copy", "--file", str(exported))
    _, back = run("get", "--dir", str(tmp_path / ".outrage"), "notes/copy")

    # The whole point of writing no trailing newline: a document that grows a
    # character every time it is exported and re-imported is a corrupted one.
    assert back == content


def test_get_caps_when_asked_and_says_where_to_resume(tmp_path, capsys):
    a_long_store(tmp_path / ".outrage")

    status, output = run(
        "get", "--dir", str(tmp_path / ".outrage"), "notes/long", "--max-chars", "100"
    )

    assert status == 0
    assert len(output) == 100
    # On stderr, so that a redirect to a file gets the content and the person
    # watching still learns the file is a fragment.
    assert "more from --offset 100" in capsys.readouterr().err


def test_get_starts_at_a_pattern_and_still_reads_to_the_end(tmp_path):
    content = a_long_store(tmp_path / ".outrage")

    _, output = run(
        "get", "--dir", str(tmp_path / ".outrage"), "notes/long", "--pattern", "end of the document"
    )

    assert output == content[content.index("end of the document") :]


def test_get_length_caps_the_whole_read_not_just_the_first_slice(tmp_path):
    a_long_store(tmp_path / ".outrage")

    _, output = run("get", "--dir", str(tmp_path / ".outrage"), "notes/long", "--length", "20000")

    # Longer than one slice, so it is delivered by the continuation loop. A
    # --length that stops binding once it exceeds max_chars is a bound that
    # silently is not one.
    assert len(output) == 20000


def test_set_reports_where_it_wrote(tmp_path):
    status, output = run(
        "set", "--dir", str(tmp_path / ".outrage"), "notes/one", "--content", "hello"
    )

    assert status == 0
    assert "notes/one" in output
    assert "5 characters" in output
    assert str(tmp_path / ".outrage" / "store.sqlite") in output


def test_set_allocates_a_number_and_names_the_key_it_wrote(tmp_path):
    run("set", "--dir", str(tmp_path / ".outrage"), "notes/?", "--content", "first")

    _, output = run("set", "--dir", str(tmp_path / ".outrage"), "notes/?", "--content", "second")

    assert output.startswith("notes/2 ")


def test_set_refuses_two_sources(tmp_path, capsys):
    status = main(
        ["set", "--dir", str(tmp_path / ".outrage"), "notes/one", "--content", "x", "--file", "f"],
        io.StringIO(),
    )

    assert status == 1
    assert "not both" in capsys.readouterr().err


def test_reading_a_store_that_is_not_there_is_refused(tmp_path, capsys):
    status = main(["get", "--dir", str(tmp_path / "absent"), "notes/one"], io.StringIO())

    # SqliteStore() would create one, and an empty store answers every question with
    # a confident nothing.
    assert status == 1
    assert "no store at" in capsys.readouterr().err
    assert not (tmp_path / "absent").exists()


# -- ls ------------------------------------------------------------------


def a_tree(directory: Path) -> None:
    """A store with a container, documents beneath it, and metadata."""
    from outrage.store_sqlite import SqliteStore

    with SqliteStore(directory) as store:
        for number in (1, 2, 10):
            store.store_document(f"notes/{number}", f"body {number}", title=f"Note {number}")
        store.store_document("notes/1/detail", "deeper")


def test_ls_lists_one_level_with_kinds(tmp_path):
    a_tree(tmp_path / ".outrage")

    status, output = run("ls", "--dir", str(tmp_path / ".outrage"), "notes")

    assert status == 0
    listed = [line.split()[-1] for line in output.splitlines()]
    assert listed == ["notes/1", "notes/2", "notes/10"]
    assert "document" in output


def test_ls_sorts_numeric_segments_as_numbers(tmp_path):
    a_tree(tmp_path / ".outrage")

    _, output = run("ls", "--dir", str(tmp_path / ".outrage"), "notes")

    assert output.index("notes/2") < output.index("notes/10")


def test_ls_shows_metadata_and_subkeys_under_a_document(tmp_path):
    a_tree(tmp_path / ".outrage")

    _, output = run("ls", "--dir", str(tmp_path / ".outrage"), "notes/1")

    assert "notes/1/!title" in output
    assert "metadata" in output
    assert "notes/1/detail" in output


def test_ls_recursive_reaches_the_bottom(tmp_path):
    a_tree(tmp_path / ".outrage")

    _, output = run("ls", "--dir", str(tmp_path / ".outrage"), "--recursive", "notes")

    assert "notes/1/detail" in output
    assert "notes/10/!title" in output


def test_ls_recursive_from_the_top_reports_the_container(tmp_path):
    a_tree(tmp_path / ".outrage")

    _, output = run("ls", "--dir", str(tmp_path / ".outrage"), "--recursive")

    # Only list_keys reports a key that holds nothing itself; leaving it out is
    # how everything beneath it looks parentless.
    assert "implicit" in output
    assert output.index("  notes\n") < output.index("  notes/1\n")


def test_ls_says_so_when_there_is_nothing(tmp_path):
    a_tree(tmp_path / ".outrage")

    _, output = run("ls", "--dir", str(tmp_path / ".outrage"), "notes/1/detail")

    assert "nothing below notes/1/detail" in output


# -- rm ------------------------------------------------------------------


def test_rm_takes_the_metadata_with_the_document(tmp_path):
    a_tree(tmp_path / ".outrage")

    status, output = run("rm", "--dir", str(tmp_path / ".outrage"), "notes/2")

    assert status == 0
    assert "deleted notes/2" in output
    assert "deleted notes/2/!title" in output


def test_rm_leaves_the_subtree_and_says_it_did(tmp_path):
    a_tree(tmp_path / ".outrage")

    _, output = run("rm", "--dir", str(tmp_path / ".outrage"), "notes/1")

    assert "1 keys below notes/1 remain" in output
    _, listing = run("ls", "--dir", str(tmp_path / ".outrage"), "notes/1")
    assert "notes/1/detail" in listing


def test_rm_dry_run_deletes_nothing(tmp_path):
    a_tree(tmp_path / ".outrage")

    _, output = run("rm", "--dir", str(tmp_path / ".outrage"), "notes/1", "--dry-run")

    assert "would delete notes/1" in output
    assert "would remain" in output
    _, listing = run("ls", "--dir", str(tmp_path / ".outrage"), "notes")
    assert "notes/1" in listing


def test_rm_dry_run_previews_the_subtree_it_would_take(tmp_path):
    a_tree(tmp_path / ".outrage")

    _, output = run(
        "rm", "--dir", str(tmp_path / ".outrage"), "notes/1", "--recursive", "--dry-run"
    )

    assert "and below: notes/1/detail" in output
    _, listing = run("ls", "--dir", str(tmp_path / ".outrage"), "notes/1")
    assert "notes/1/detail" in listing


def test_rm_recursive_takes_the_subtree(tmp_path):
    a_tree(tmp_path / ".outrage")

    _, output = run("rm", "--dir", str(tmp_path / ".outrage"), "notes/1", "--recursive")

    assert "deleted notes/1/detail" in output
    assert "remain" not in output


def test_rm_says_when_there_was_nothing_there(tmp_path):
    a_tree(tmp_path / ".outrage")

    _, output = run("rm", "--dir", str(tmp_path / ".outrage"), "notes/absent")

    assert "nothing stored at notes/absent" in output


# -- check ---------------------------------------------------------------


def test_check_reports_a_sound_store(tmp_path):
    a_tree(tmp_path / ".outrage")

    status, output = run("check", "--dir", str(tmp_path / ".outrage"))

    assert status == 0
    assert "(sqlite)" in output
    assert "integrity ok" in output
    assert "nothing wrong" in output


def test_check_reports_a_parquet_store_without_sqlites_vocabulary(tmp_path):
    """The same subcommand, in the second backend's own terms.

    The line that matters is the third: printed from the report's ``details``
    rather than from fields, so a store with no write-ahead log says nothing
    about one instead of reporting it as zero bytes -- which would read as a
    fact somebody had checked.
    """
    pytest.importorskip("pyarrow", reason="the parquet backend is an optional extra")

    a_tree(tmp_path / ".outrage")
    run(
        "pack",
        str(tmp_path / "ref.parquet"),
        "--dir",
        str(tmp_path / ".outrage"),
        "--from-store",
        "store.sqlite",
    )

    status, output = run("check", "--dir", str(tmp_path), "--store", "ref.parquet")

    assert status == 0
    assert "(parquet)" in output
    assert "order sorted" in output
    assert "integrity" not in output
    assert "log" not in output
    assert "nothing wrong" in output


def test_repair_of_a_store_with_nothing_to_move_says_so(tmp_path):
    """Not a blank, and not a claim to have acted.

    A backend returning no repairs is saying there is nothing its storage
    could need, which the user has to be able to tell from a repair that ran
    and did nothing.
    """
    pytest.importorskip("pyarrow", reason="the parquet backend is an optional extra")

    a_tree(tmp_path / ".outrage")
    run(
        "pack",
        str(tmp_path / "ref.parquet"),
        "--dir",
        str(tmp_path / ".outrage"),
        "--from-store",
        "store.sqlite",
    )

    status, output = run("check", "--repair", "--dir", str(tmp_path), "--store", "ref.parquet")

    assert status == 0
    assert "nothing to repair: a parquet store has no state a repair could move" in output


def test_check_refuses_a_directory_with_no_store(tmp_path, capsys):
    status = main(["check", "--dir", str(tmp_path / "absent")], io.StringIO())

    assert status == 1
    assert "no store at" in capsys.readouterr().err


def test_check_reports_a_row_stored_under_the_wrong_parent(tmp_path):
    import sqlite3

    a_tree(tmp_path / ".outrage")
    connection = sqlite3.connect(tmp_path / ".outrage" / "store.sqlite")
    connection.execute("UPDATE documents SET parent = 'elsewhere' WHERE key = 'notes/2'")
    connection.commit()
    connection.close()

    status, output = run("check", "--dir", str(tmp_path / ".outrage"))

    # Readable by key and invisible to every listing, which is the failure this
    # check exists for: nothing in normal reading would notice.
    assert status == 1
    assert "disagree with the key they are stored under" in output
    assert "notes/2" in output


def test_check_repairs_the_write_ahead_log(tmp_path):
    from outrage.store_sqlite import SqliteStore

    directory = tmp_path / ".outrage"
    with SqliteStore(directory) as store:
        store.store_document("notes/one", "x" * 200000)

    database = directory / "store.sqlite"
    log = directory / "store.sqlite-wal"
    # Reproduce an unfolded log: writes land in the sidecar, and closing the
    # store is what would normally checkpoint them back.
    held_open = SqliteStore(directory)
    held_open.store_document("notes/two", "y" * 400000)
    assert log.stat().st_size > database.stat().st_size

    try:
        status, output = run("check", "--repair", "--dir", str(directory))

        assert status == 0
        assert "checkpoint the write-ahead log" in output
        # The second report is the one that matters: a repair whose own writes
        # leave the log full again would print this warning after fixing it.
        assert output.count("most of the store is in the write-ahead log") == 1
        assert log.stat().st_size < database.stat().st_size
    finally:
        held_open.close()


# -- paging, which the command line does internally ----------------------


def a_wide_store(directory: Path, count: int, content: str = "body") -> None:
    from outrage.store_sqlite import SqliteStore

    with SqliteStore(directory) as store:
        for number in range(1, count + 1):
            store.store_document(f"notes/{number}", content, title=f"Note {number}")


def test_ls_lists_a_level_larger_than_one_page(tmp_path):
    a_wide_store(tmp_path / ".outrage", 250)

    status, output = run("ls", "--dir", str(tmp_path / ".outrage"), "notes")

    # A listing that stops at an internal page size is the silent partial
    # answer, delivered by the layer that was supposed to prevent it.
    assert status == 0
    # A title is a child of its own document, not of the level, so this is 250
    # keys rather than 500.
    assert len(output.splitlines()) == 250
    assert "notes/250" in output


def test_ls_pages_rather_than_asking_for_everything(tmp_path, monkeypatch):
    import outrage.bulk

    a_wide_store(tmp_path / ".outrage", 20)
    monkeypatch.setattr(outrage.bulk, "PAGE", 3)

    _, output = run("ls", "--dir", str(tmp_path / ".outrage"), "notes")

    assert len(output.splitlines()) == 20


def test_ls_recursive_pages_at_every_level(tmp_path, monkeypatch):
    import outrage.bulk
    from outrage.store_sqlite import SqliteStore

    with SqliteStore(tmp_path / ".outrage") as store:
        for number in range(1, 8):
            store.store_document(f"deep/{number}/leaf", "content")
    monkeypatch.setattr(outrage.bulk, "PAGE", 2)

    _, output = run("ls", "--dir", str(tmp_path / ".outrage"), "--recursive", "deep")

    assert [line.split()[-1] for line in output.splitlines()] == [
        key for number in range(1, 8) for key in (f"deep/{number}", f"deep/{number}/leaf")
    ]


def test_ls_limit_shows_less_and_says_so(tmp_path, capsys):
    a_wide_store(tmp_path / ".outrage", 20)

    _, output = run("ls", "--dir", str(tmp_path / ".outrage"), "notes", "--limit", "3")

    assert len(output.splitlines()) == 3
    # On stderr: the listing itself stays clean for whatever it is piped into.
    assert "stopped at --limit 3" in capsys.readouterr().err


def test_dump_exports_more_than_one_page_whole(tmp_path, monkeypatch):
    import outrage.bulk

    a_wide_store(tmp_path / ".outrage", 10, content="x" * 3000)
    monkeypatch.setattr(outrage.bulk, "PAGE", 2)

    _, output = run("dump", "--dir", str(tmp_path / ".outrage"), "notes")

    # Complete by default, across pages and past the per-document cap: an
    # export that quietly holds back is the failure this command exists to
    # avoid, and paging is a new way to commit it.
    assert output.count("x" * 3000) == 10
    assert "characters]" not in output


def test_dump_limit_shows_less_and_says_so(tmp_path, capsys):
    a_wide_store(tmp_path / ".outrage", 10)

    _, output = run("dump", "--dir", str(tmp_path / ".outrage"), "notes", "--limit", "2")

    assert output.count("=== ") == 2
    assert "stopped at --limit 2" in capsys.readouterr().err


def test_dump_asks_for_one_page_before_printing_anything(tmp_path, monkeypatch):
    import argparse

    import outrage.bulk
    import outrage.cli
    from outrage.store_sqlite import SqliteStore

    a_wide_store(tmp_path / ".outrage", 10)
    monkeypatch.setattr(outrage.bulk, "PAGE", 2)

    calls = 0
    original = SqliteStore.get_documents

    def counted(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        return original(self, *args, **kwargs)

    monkeypatch.setattr(SqliteStore, "get_documents", counted)

    with SqliteStore(tmp_path / ".outrage") as opened:
        arguments = argparse.Namespace(key="notes", meta_name=None, depth=None, max_chars=None)
        first = next(outrage.cli._documents(opened, arguments))

    # Lazy, not merely paged: an export that reads the whole subtree before
    # writing its first line is the shape that fails at the size it matters.
    assert first.key == "notes/1"
    assert calls == 1


def test_rm_dry_run_previews_the_whole_subtree_not_one_level(tmp_path):
    from outrage.store_sqlite import SqliteStore

    with SqliteStore(tmp_path / ".outrage") as store:
        store.store_document("tree/one", "content")
        store.store_document("tree/one/two/three", "content")

    _, output = run("rm", "--dir", str(tmp_path / ".outrage"), "tree", "--recursive", "--dry-run")

    # Previewing one level of a deletion that reaches three is not a preview.
    assert "and below: tree/one/two/three" in output


def test_rm_dry_run_preview_can_be_shortened(tmp_path):
    a_wide_store(tmp_path / ".outrage", 10)

    _, output = run(
        "rm",
        "--dir",
        str(tmp_path / ".outrage"),
        "notes",
        "--recursive",
        "--dry-run",
        "--limit",
        "3",
    )

    assert output.count("and below:") == 3
    # The count comes from the store, so a shortened preview still says how
    # much it is shortening.
    assert "and 17 more" in output


def test_rm_dry_run_shortened_count_holds_the_key_s_own_metadata(tmp_path):
    from outrage.store_sqlite import SqliteStore

    with SqliteStore(tmp_path / ".outrage") as store:
        store.store_document("notes", "the index", title="Notes")
        for number in (1, 2, 3):
            store.store_document(f"notes/{number}", "body", title=f"Note {number}")

    _, output = run(
        "rm",
        "--dir",
        str(tmp_path / ".outrage"),
        "notes",
        "--recursive",
        "--dry-run",
        "--limit",
        "2",
    )

    # Seven keys are below `notes`: its own title, three documents and theirs.
    # The preview walks all seven because a recursive delete takes all seven,
    # so a shortened one has five left. Counting instead what a *plain* delete
    # would keep left out `notes/!title` and said four -- and at --limit 6 the
    # same subtraction printed "and -1 more".
    assert output.count("and below:") == 2
    assert "and 5 more" in output

    _, output = run(
        "rm",
        "--dir",
        str(tmp_path / ".outrage"),
        "notes",
        "--recursive",
        "--dry-run",
        "--limit",
        "6",
    )

    assert "and 1 more" in output


def test_a_malformed_key_is_one_line_and_not_a_traceback(tmp_path, capsys):
    # An invalid key is about the request, so it renders as one line rather
    # than reaching the top of main as a bug would. Two examples have been
    # retired from this test by the grammar widening under them: the
    # pre-schema-4 `:` spelling, and `!title`, which is the root's own title
    # now. The malformation has to be a real one.
    a_long_store(tmp_path / ".outrage")

    status, _ = run("get", "--dir", str(tmp_path / ".outrage"), "context/!")

    assert status != 0
    err = capsys.readouterr().err
    assert "metadata name" in err
    assert "Traceback" not in err
    assert err.count("\n") == 1


# -- export and import ---------------------------------------------------


def an_exportable_store(directory: Path) -> Path:
    from outrage.store_sqlite import SqliteStore

    with SqliteStore(directory) as store:
        store.store_document("project", "# Project", title="The project")
        store.store_document("project/reference/env", '{"python": "3.14"}')
    return directory


def test_export_writes_a_file_per_document(tmp_path, capsys):
    an_exportable_store(tmp_path / ".outrage")

    status, output = run("export", "--dir", str(tmp_path / ".outrage"), str(tmp_path / "out"))

    assert status == 0
    assert (tmp_path / "out/project.md").read_text() == "# Project"
    assert (tmp_path / "out/project/!title.md").read_text() == "The project"
    assert (tmp_path / "out/project/reference/env.json").exists()
    assert "wrote" in output
    # The counts go to stderr, so a report piped onward is not corrupted by a
    # note about itself.
    assert "3 written" in capsys.readouterr().err


def test_export_dry_run_writes_nothing(tmp_path):
    an_exportable_store(tmp_path / ".outrage")

    status, output = run(
        "export", "--dir", str(tmp_path / ".outrage"), str(tmp_path / "out"), "--dry-run"
    )

    assert status == 0
    assert "would write" in output
    assert not (tmp_path / "out").exists()


def test_export_refuses_a_store_that_is_not_there(tmp_path, capsys):
    status, _ = run("export", "--dir", str(tmp_path / ".outrage"), str(tmp_path / "out"))

    assert status == 1
    assert "outrage:" in capsys.readouterr().err


def test_import_stores_a_directory_and_says_where(tmp_path, capsys):
    an_exportable_store(tmp_path / ".outrage")
    run("export", "--dir", str(tmp_path / ".outrage"), str(tmp_path / "out"))

    status, output = run("import", "--dir", str(tmp_path / "fresh"), str(tmp_path / "out"))

    assert status == 0
    assert "wrote" in output
    # A first write may create the store, as `outrage set` may: seeding an empty
    # one from a directory is that write in bulk. Saying where it went is then
    # the only thing that makes a mistyped --dir visible.
    assert str(tmp_path / "fresh" / "store.sqlite") in capsys.readouterr().err

    _, listed = run("ls", "--dir", str(tmp_path / "fresh"), "--recursive")
    assert "project/reference/env" in listed


def test_import_leaves_what_is_already_stored(tmp_path):
    an_exportable_store(tmp_path / ".outrage")
    run("export", "--dir", str(tmp_path / ".outrage"), str(tmp_path / "out"))
    (tmp_path / "out/project.md").write_text("# Changed on disk")

    status, output = run("import", "--dir", str(tmp_path / ".outrage"), str(tmp_path / "out"))

    assert status == 0
    assert "skipped" in output
    _, content = run("get", "--dir", str(tmp_path / ".outrage"), "project")
    assert content == "# Project"


def test_import_overwrites_when_asked(tmp_path):
    an_exportable_store(tmp_path / ".outrage")
    run("export", "--dir", str(tmp_path / ".outrage"), str(tmp_path / "out"))
    (tmp_path / "out/project.md").write_text("# Changed on disk")

    run(
        "import",
        "--dir",
        str(tmp_path / ".outrage"),
        str(tmp_path / "out"),
        "--on-conflict",
        "overwrite",
    )

    _, content = run("get", "--dir", str(tmp_path / ".outrage"), "project")
    assert content == "# Changed on disk"


def test_import_stopping_at_a_conflict_is_a_failed_run(tmp_path):
    an_exportable_store(tmp_path / ".outrage")
    run("export", "--dir", str(tmp_path / ".outrage"), str(tmp_path / "out"))

    status, output = run(
        "import",
        "--dir",
        str(tmp_path / ".outrage"),
        str(tmp_path / "out"),
        "--on-conflict",
        "stop",
    )

    # The exit status is the only part of a partial run a script can see.
    assert status == 1
    assert "stopped" in output


def test_import_under_a_key_grafts_the_tree(tmp_path):
    an_exportable_store(tmp_path / ".outrage")
    run("export", "--dir", str(tmp_path / ".outrage"), str(tmp_path / "out"))

    run("import", "--dir", str(tmp_path / ".outrage"), str(tmp_path / "out"), "archive/2026")

    _, content = run("get", "--dir", str(tmp_path / ".outrage"), "archive/2026/project")
    assert content == "# Project"


# -- init ----------------------------------------------------------------


def test_init_arranges_the_whole_project(tmp_path):
    status, output = run("init", "--project-dir", str(tmp_path))

    assert status == 0
    assert servers(tmp_path / ".mcp.json")["outrage"]
    assert (tmp_path / ".claude" / "settings.json").is_file()
    assert (tmp_path / ".claude" / "skills" / "outrage" / "SKILL.md").is_file()
    assert (tmp_path / ".codex" / "skills" / "outrage" / "SKILL.md").is_file()
    assert (tmp_path / ".github" / "agents" / "outrage-search.agent.md").is_file()
    assert "added" in output


def test_init_dry_run_writes_nothing(tmp_path):
    status, output = run("init", "--project-dir", str(tmp_path), "--dry-run")

    assert status == 0
    assert list(tmp_path.iterdir()) == []
    assert "would add" in output


def test_init_names_every_path_it_touches(tmp_path):
    """The command is a guess at several paths, and a wrong one still succeeds."""
    _, output = run("init", "--project-dir", str(tmp_path))

    assert str(tmp_path / ".mcp.json") in output
    assert str(tmp_path / ".claude" / "settings.json") in output
    assert "skills/outrage/SKILL.md" in output
    assert str(tmp_path / ".codex") in output
    assert str(tmp_path / ".github") in output


def test_init_records_the_store_directory_and_the_log(tmp_path):
    run("init", "--project-dir", str(tmp_path), "--dir", str(tmp_path / "store"), "--log")

    args = servers(tmp_path / ".mcp.json")["outrage"]["args"]
    assert str(tmp_path / "store") in args
    assert "--log" in args


def test_init_says_when_there_is_nothing_to_do(tmp_path):
    run("init", "--project-dir", str(tmp_path))

    _, output = run("init", "--project-dir", str(tmp_path))

    assert "already current" in output
    assert "added" not in output


def test_init_refuses_settings_it_cannot_parse(tmp_path):
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text("{not json", encoding="utf-8")

    status, output = run("init", "--project-dir", str(tmp_path))

    assert status == 1
    assert output == "", "the refusal goes to stderr, and nothing was reported as done"


# -- the root ------------------------------------------------------------


def test_the_root_is_written_read_and_printed_as_a_slash(tmp_path):
    d = str(tmp_path / ".outrage")
    status, output = run("set", "--dir", d, "", "--content", "# This store", "--title", "Store")
    assert status == 0
    # "" is invisible in a report, so it prints as `/` -- a legal spelling of
    # the root that normalises straight back to it.
    assert output.startswith("/  ")

    assert run("get", "--dir", d, "")[1] == "# This store"
    assert run("get", "--dir", d, "!title")[1] == "Store"


def test_a_slash_is_a_spelling_of_the_root_on_the_command_line(tmp_path):
    d = str(tmp_path / ".outrage")
    run("set", "--dir", d, "/", "--content", "body")
    assert run("get", "--dir", d, "")[1] == "body"


def test_dump_names_the_root_document(tmp_path):
    d = str(tmp_path / ".outrage")
    run("set", "--dir", d, "", "--content", "root body")
    run("set", "--dir", d, "a", "--content", "a body")

    status, output = run("dump", "--dir", d)
    assert status == 0
    assert "=== /" in output
    assert "=== a" in output


def test_listing_the_top_level_does_not_show_the_root(tmp_path):
    d = str(tmp_path / ".outrage")
    run("set", "--dir", d, "", "--content", "root body")
    run("set", "--dir", d, "a", "--content", "a body")

    output = run("ls", "--dir", d)[1]
    assert " a\n" in output
    assert output.count("\n") == 1  # `a` and nothing else


def test_export_writes_the_root_document_and_names_it_as_a_key(tmp_path):
    d = str(tmp_path / ".outrage")
    run("set", "--dir", d, "", "--content", "root body")

    status, output = run("export", "--dir", d, str(tmp_path / "out"))
    assert status == 0
    # `-` in this column means "no key"; the root is a key, so it is spelled.
    assert "wrote       /  ->" in output
    assert (tmp_path / "out" / ".md").read_text() == "root body"


# -- pack ------------------------------------------------------------------


def test_pack_builds_a_parquet_store_from_a_store(tmp_path, capsys):
    """The compaction: accumulate into SQLite, then pack it into one file."""
    pytest.importorskip("pyarrow", reason="the parquet backend is an optional extra")
    an_exportable_store(tmp_path / ".outrage")

    status, output = run(
        "pack",
        str(tmp_path / "ref.parquet"),
        "--dir",
        str(tmp_path / ".outrage"),
        "--from-store",
        "store.sqlite",
    )

    assert status == 0
    # `read`, not `wrote`: nothing is written until the whole file is, and an
    # interrupted pack has written nothing at all.
    assert "read" in output and "wrote" not in output
    assert "3 packed" in capsys.readouterr().err
    assert (tmp_path / "ref.parquet").exists()

    _, listed = run("ls", "--dir", str(tmp_path), "--store", "ref.parquet", "--recursive")
    assert "project/reference/env" in listed


def test_pack_builds_a_parquet_store_from_a_directory(tmp_path):
    pytest.importorskip("pyarrow", reason="the parquet backend is an optional extra")
    an_exportable_store(tmp_path / ".outrage")
    run("export", "--dir", str(tmp_path / ".outrage"), str(tmp_path / "out"))

    status, _ = run("pack", str(tmp_path / "ref.parquet"), "--from-dir", str(tmp_path / "out"))

    assert status == 0
    _, shown = run("get", "--dir", str(tmp_path), "--store", "ref.parquet", "project")
    assert "# Project" in shown


def test_pack_needs_exactly_one_source(tmp_path):
    """Mutually exclusive and required, so neither is a silent default."""
    with pytest.raises(SystemExit):
        parse_args(["pack", str(tmp_path / "out.parquet")])
    with pytest.raises(SystemExit):
        parse_args(["pack", "out.parquet", "--from-dir", "a", "--from-store", "b"])


def test_pack_dry_run_reports_and_writes_nothing(tmp_path, capsys):
    pytest.importorskip("pyarrow", reason="the parquet backend is an optional extra")
    an_exportable_store(tmp_path / ".outrage")

    status, output = run(
        "pack",
        str(tmp_path / "ref.parquet"),
        "--dir",
        str(tmp_path / ".outrage"),
        "--from-store",
        "store.sqlite",
        "--dry-run",
    )

    assert status == 0
    assert "would pack" in output
    assert "dry run, nothing changed" in capsys.readouterr().err
    assert not (tmp_path / "ref.parquet").exists()


def test_pack_refuses_a_target_that_is_already_there(tmp_path, capsys):
    pytest.importorskip("pyarrow", reason="the parquet backend is an optional extra")
    an_exportable_store(tmp_path / ".outrage")
    args = (
        "pack",
        str(tmp_path / "ref.parquet"),
        "--dir",
        str(tmp_path / ".outrage"),
        "--from-store",
        "store.sqlite",
    )
    assert run(*args)[0] == 0

    status, output = run(*args)
    assert status == 1
    # Refused before a document is read, not after the whole source has been:
    # a refusal that arrives at the end of a long pack is the right answer at
    # the least useful moment.
    assert output == ""
    assert "pass --overwrite" in capsys.readouterr().err

    assert run(*args, "--overwrite")[0] == 0


def test_writing_to_a_parquet_store_is_refused_as_a_message(tmp_path, capsys):
    """A refusal reaches the user as one line and a status, not a traceback.

    And the line does not offer a flag, because unlike a read-only *mount*
    there is none that would make the write succeed.
    """
    pytest.importorskip("pyarrow", reason="the parquet backend is an optional extra")
    an_exportable_store(tmp_path / ".outrage")
    run(
        "pack",
        str(tmp_path / "ref.parquet"),
        "--dir",
        str(tmp_path / ".outrage"),
        "--from-store",
        "store.sqlite",
    )

    status, _ = run("set", "--dir", str(tmp_path), "--store", "ref.parquet", "a", "--content", "x")

    assert status == 1
    reported = capsys.readouterr().err
    assert "written whole rather than updated" in reported
    assert "outrage pack" in reported


# -- ?last ---------------------------------------------------------------


def a_few_threads(directory: Path) -> None:
    from outrage.store_sqlite import SqliteStore

    with SqliteStore(directory) as store:
        for name in ("2", "10", "9"):
            store.store_document(f"context/{name}/state", f"thread {name}", title=name)


def test_last_reads_the_newest_key(tmp_path, capsys):
    a_few_threads(tmp_path / ".outrage")

    status, output = run("get", "--dir", str(tmp_path / ".outrage"), "context/?last/state")

    assert status == 0
    assert output == "thread 10"


def test_last_says_on_stderr_which_key_it_meant(tmp_path, capsys):
    # stdout is the document, so the note cannot go there: `outrage get > f`
    # has to give back exactly what went in.
    a_few_threads(tmp_path / ".outrage")

    run("get", "--dir", str(tmp_path / ".outrage"), "context/?last/state")

    assert "?last is context/10" in capsys.readouterr().err


def test_an_ordinary_key_says_nothing(tmp_path, capsys):
    a_few_threads(tmp_path / ".outrage")

    run("get", "--dir", str(tmp_path / ".outrage"), "context/10/state")

    assert capsys.readouterr().err == ""


def test_last_writes_under_the_newest_key(tmp_path):
    a_few_threads(tmp_path / ".outrage")

    status, output = run(
        "set", "--dir", str(tmp_path / ".outrage"), "context/?last/notes", "--content", "body"
    )

    assert status == 0
    assert "context/10/notes" in output


def test_last_deletes_from_the_newest_key(tmp_path):
    a_few_threads(tmp_path / ".outrage")

    status, output = run(
        "rm", "--dir", str(tmp_path / ".outrage"), "context/?last/state", "--recursive"
    )

    assert status == 0
    assert "context/10/state" in output


def test_last_with_nothing_below_it_is_a_message_and_a_status(tmp_path, capsys):
    a_few_threads(tmp_path / ".outrage")

    status = main(["get", "--dir", str(tmp_path / ".outrage"), "nowhere/?last"], io.StringIO())

    assert status == 1
    assert "nothing below it" in capsys.readouterr().err


# The command line across a mount table. Not a second implementation of the
# server's: the same `open_mounts`, reached through the same options, so the
# thing being checked here is that a person gets the *one* namespace an agent
# gets -- a table typed differently from the server's is a different namespace
# answering the same keys, and nothing would say so.


def a_mounted_project(directory: Path, *, config: str | None = None) -> Path:
    """A root store, a read-write mount, a read-only one, and a table naming them."""
    from outrage.store_sqlite import SqliteStore

    for filename, key, content in (
        ("store.sqlite", "top", "at the root"),
        ("team.sqlite", "plans/q3", "the plan"),
        ("reference.sqlite", "python/asyncio", "the reference"),
    ):
        with SqliteStore(directory, filename=filename) as store:
            store.store_document(key, content)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "mounts.toml").write_text(
        config
        if config is not None
        else '[mount]\nteam = "team.sqlite"\n\n[mount-ro]\nref = "reference.sqlite"\n',
        encoding="utf-8",
    )
    return directory


def test_ls_reads_the_mount_table_from_the_default_file(tmp_path):
    """The payoff: a table in the store directory, and no flag to type."""
    a_mounted_project(tmp_path / ".outrage")

    status, output = run("ls", "--dir", str(tmp_path / ".outrage"), "--recursive")

    assert status == 0
    assert "ref/python/asyncio" in output
    assert "team/plans/q3" in output
    assert "top" in output


def test_get_crosses_a_mount_boundary(tmp_path):
    a_mounted_project(tmp_path / ".outrage")

    status, output = run("get", "--dir", str(tmp_path / ".outrage"), "ref/python/asyncio")

    assert status == 0
    assert output == "the reference"


def test_copy_moves_a_subtree_between_mounted_stores(tmp_path):
    from outrage.store_sqlite import SqliteStore

    directory = tmp_path / ".outrage"
    a_mounted_project(
        directory,
        config=(
            '[mount]\nteam = "team.sqlite"\narchive = "archive.sqlite"\n\n'
            '[mount-ro]\nref = "reference.sqlite"\n'
        ),
    )
    with SqliteStore(directory, filename="archive.sqlite"):
        pass

    status, output = run("copy", "--dir", str(directory), "team/plans", "archive/imported")

    assert status == 0
    assert "wrote       archive/imported/team/plans/q3" in output
    _, copied = run("get", "--dir", str(directory), "archive/imported/team/plans/q3")
    assert copied == "the plan"


def test_copy_exposes_depth_and_the_whole_key_range(tmp_path):
    from outrage.store_sqlite import SqliteStore

    directory = tmp_path / ".outrage"
    a_mounted_project(
        directory,
        config=(
            '[mount]\nteam = "team.sqlite"\narchive = "archive.sqlite"\n\n'
            '[mount-ro]\nref = "reference.sqlite"\n'
        ),
    )
    with SqliteStore(directory, filename="team.sqlite") as team:
        team.store_document("plans/q1", "first", title="Q1")
        team.store_document("plans/q2", "second", title="Q2")
    with SqliteStore(directory, filename="archive.sqlite"):
        pass

    status, _ = run(
        "copy",
        "--dir",
        str(directory),
        "team/plans",
        "archive/window",
        "--depth",
        "1",
        "--after-subtree",
        "team/plans/q1",
        "--final-subtree",
        "team/plans/q2",
    )

    assert status == 0
    _, listed = run("ls", "--dir", str(directory), "archive/window", "--recursive")
    assert "archive/window/team/plans/q2" in listed
    assert "archive/window/team/plans/q2/!title" in listed
    assert "archive/window/team/plans/q1" not in listed
    assert "archive/window/team/plans/q3" not in listed


def test_copy_parser_exposes_every_key_range_cut():
    args = parse_args(
        [
            "copy",
            "source",
            "target",
            "--after",
            "a",
            "--after-inclusive",
            "b",
            "--after-subtree",
            "c",
            "--before",
            "d",
            "--before-inclusive",
            "e",
            "--final-subtree",
            "f",
        ]
    )

    assert (
        args.after,
        args.after_inclusive,
        args.after_subtree,
        args.before,
        args.before_inclusive,
        args.final_subtree,
    ) == ("a", "b", "c", "d", "e", "f")


def test_copy_dry_run_writes_nothing(tmp_path):
    directory = a_mounted_project(tmp_path / ".outrage")

    status, output = run("copy", "--dir", str(directory), "team/plans", "preview", "--dry-run")

    assert status == 0
    assert "would write preview/team/plans/q3" in output
    _, listed = run("ls", "--dir", str(directory), "--recursive")
    assert "preview/team/plans/q3" not in listed


def test_copy_dry_run_reports_the_moment_to_pass_back(tmp_path, capsys):
    """Look, then write only what has not moved: the second call needs the first's time.

    The one part of this a caller cannot get right by hand -- too early refuses
    a run nothing is wrong with, too late arms nothing.
    """
    directory = a_mounted_project(tmp_path / ".outrage")

    status, _ = run("copy", "--dir", str(directory), "team/plans", "preview", "--dry-run")
    reported = capsys.readouterr().err

    assert status == 0
    assert "--unchanged-since " in reported
    watermark = reported.rsplit("--unchanged-since ", 1)[1].split()[0]
    assert (
        main(
            [
                "copy",
                "--dir",
                str(directory),
                "team/plans",
                "preview",
                "--unchanged-since",
                watermark,
            ],
            io.StringIO(),
        )
        == 0
    )


def test_copy_dry_run_under_overwrite_advises_a_repeat_that_lands(tmp_path, capsys):
    """The repeat it recommends has to be a command that runs.

    `--on-conflict overwrite` beside a watermark is refused, so advice naming
    only `--unchanged-since` sends the caller to that refusal. The test types
    back exactly what the message says rather than asserting its words.
    """
    directory = a_mounted_project(tmp_path / ".outrage")
    run("set", "--dir", str(directory), "preview/team/plans/q3", "--content", "mine")

    run(
        "copy",
        "--dir",
        str(directory),
        "team/plans",
        "preview",
        "--on-conflict",
        "overwrite",
        "--dry-run",
    )
    reported = capsys.readouterr().err

    repeat = reported.rsplit("repeat with ", 1)[1].split(" to refuse")[0].split()
    assert "--on-conflict" in repeat
    assert (
        main(["copy", "--dir", str(directory), "team/plans", "preview", *repeat], io.StringIO())
        == 0
    )


def test_copy_refuses_when_the_target_moved_since_the_watermark(tmp_path, capsys):
    directory = a_mounted_project(tmp_path / ".outrage")
    run("set", "--dir", str(directory), "preview/team/plans/q3", "--content", "mine")

    status = main(
        [
            "copy",
            "--dir",
            str(directory),
            "team/plans",
            "preview",
            "--on-conflict",
            "overwrite-unchanged",
            "--unchanged-since",
            "2020-01-01T00:00:00Z",
        ],
        io.StringIO(),
    )

    assert status == 1
    assert "would act on work done since" in capsys.readouterr().err
    _, kept = run("get", "--dir", str(directory), "preview/team/plans/q3")
    assert kept.strip() == "mine"


def test_rm_refuses_when_what_it_would_delete_moved_since(tmp_path, capsys):
    a_tree(tmp_path / ".outrage")

    status = main(
        [
            "rm",
            "--dir",
            str(tmp_path / ".outrage"),
            "notes/1",
            "--recursive",
            "--unchanged-since",
            "2020-01-01T00:00:00Z",
        ],
        io.StringIO(),
    )

    assert status == 1
    assert "refusing to delete" in capsys.readouterr().err
    _, listing = run("ls", "--dir", str(tmp_path / ".outrage"), "notes/1")
    assert "notes/1/detail" in listing


def test_rm_with_a_watermark_nothing_moved_since_deletes(tmp_path):
    a_tree(tmp_path / ".outrage")

    status, output = run(
        "rm",
        "--dir",
        str(tmp_path / ".outrage"),
        "notes/1",
        "--recursive",
        "--unchanged-since",
        "2099-01-01T00:00:00Z",
    )

    assert status == 0
    assert "deleted notes/1/detail" in output


def test_a_watermark_that_is_not_a_timestamp_is_one_line(tmp_path, capsys):
    a_tree(tmp_path / ".outrage")

    status = main(
        ["rm", "--dir", str(tmp_path / ".outrage"), "notes/1", "--unchanged-since", "yesterday"],
        io.StringIO(),
    )

    assert status == 1
    assert "must be an ISO 8601 timestamp" in capsys.readouterr().err


def test_copy_refuses_a_target_inside_its_streaming_source(tmp_path, capsys):
    directory = a_mounted_project(tmp_path / ".outrage")

    status = main(["copy", "--dir", str(directory), "team", "team/archive"], io.StringIO())

    assert status == 1
    assert "target is inside the source subtree" in capsys.readouterr().err


def test_copy_reroot_lands_the_subtree_at_the_target(tmp_path):
    """What a restructure needs: the documents at a new key, not nested deeper.

    Without the flag the same call writes `moved/team/plans/q3`, and no second
    copy strips that prefix back off - ``context/68/findings``.
    """
    directory = a_mounted_project(tmp_path / ".outrage")

    status, output = run("copy", "--dir", str(directory), "team/plans", "moved", "--reroot")

    assert status == 0
    assert "wrote       moved/q3" in output
    _, copied = run("get", "--dir", str(directory), "moved/q3")
    assert "the plan" in copied


def test_copy_reroot_refuses_a_source_inside_its_target(tmp_path, capsys):
    """The overlap a graft is safe with and a re-root is not.

    Grafted, `team/plans` onto `team` writes `team/team/plans/...`, outside
    the walk. Re-rooted it writes `team/...`, back inside it.
    """
    directory = a_mounted_project(tmp_path / ".outrage")

    status = main(
        ["copy", "--dir", str(directory), "team/plans", "team", "--reroot"],
        io.StringIO(),
    )

    assert status == 1
    assert "source is inside the target subtree" in capsys.readouterr().err
    assert main(["copy", "--dir", str(directory), "team/plans", "team"], io.StringIO()) == 0


def test_mount_help_says_surveys_and_recursive_deletes_cross(capsys):
    with pytest.raises(SystemExit):
        parse_args(["get", "--help"])

    help_text = " ".join(capsys.readouterr().out.split())
    assert "surveys and recursive deletes cross mount boundaries" in help_text


def test_set_reports_the_file_the_document_landed_in(tmp_path):
    """Not the root: a key below a mount point is in that mount's store."""
    a_mounted_project(tmp_path / ".outrage")

    status, output = run(
        "set", "--dir", str(tmp_path / ".outrage"), "team/plans/q4", "--content", "next"
    )

    assert status == 0
    assert "team.sqlite" in output


def test_a_write_to_a_read_only_mount_is_refused(tmp_path, capsys):
    """The flag's whole purpose, now reachable from the command line too."""
    a_mounted_project(tmp_path / ".outrage")

    status = main(
        ["set", "--dir", str(tmp_path / ".outrage"), "ref/python/new", "--content", "x"],
        io.StringIO(),
    )

    assert status == 1
    assert "read-only" in capsys.readouterr().err


def test_the_command_line_replaces_one_mount_from_the_file(tmp_path):
    """The use case the file exists for: a committed table, one entry overridden.

    Everything else in it stays as the repository says it is, which is the
    property that makes the override safe to use in anger.
    """
    a_mounted_project(tmp_path / ".outrage")

    status, output = run(
        "ls",
        "--dir",
        str(tmp_path / ".outrage"),
        "--mount",
        "ref=team.sqlite",
        "--recursive",
    )

    assert status == 0
    assert "ref/plans/q3" in output
    assert "team/plans/q3" in output


def test_a_mount_configuration_that_will_not_parse_is_a_message(tmp_path, capsys):
    """Rendered like any other refusal rather than tracebacked out of argparse."""
    a_mounted_project(tmp_path / ".outrage", config="{\n")

    status = main(["ls", "--dir", str(tmp_path / ".outrage")], io.StringIO())

    assert status == 1
    assert "not valid TOML" in capsys.readouterr().err


def test_a_subcommand_that_takes_no_mounts_ignores_the_file(tmp_path):
    """``check`` is about a file -- its integrity -- and says which with --store.

    It would also be handed options it has never heard of, which is why the
    splice asks what the subcommand is before it happens.
    """
    a_mounted_project(tmp_path / ".outrage")

    status, output = run("check", "--dir", str(tmp_path / ".outrage"))

    assert status == 0
    assert "store.sqlite" in output


def test_a_read_only_backend_can_still_be_read_directly(tmp_path, capsys):
    """A table needs a writable root, and reading a packed store must not.

    Two halves of the same answer. A command with nothing mounted opens the
    store itself rather than wrapping it in a table of one, and
    ``--no-mount-config`` is how a project that *has* a table gets back to
    nothing mounted. Without the pair, packing a store and then reading it --
    which is what packing one is for -- would stop working the moment a project
    wrote a mount table down.
    """
    pytest.importorskip("pyarrow", reason="the parquet backend is an optional extra")
    a_mounted_project(tmp_path / ".outrage")
    run(
        "pack",
        str(tmp_path / ".outrage/packed.parquet"),
        "--dir",
        str(tmp_path / ".outrage"),
        "--from-store",
        "store.sqlite",
    )
    capsys.readouterr()

    status, output = run(
        "ls",
        "--dir",
        str(tmp_path / ".outrage"),
        "--store",
        "packed.parquet",
        "--no-mount-config",
        "--recursive",
    )

    assert status == 0
    assert "top" in output


def test_a_mount_from_the_file_can_be_unmounted_for_one_run(tmp_path):
    """Override can replace or add; only this takes an entry away."""
    a_mounted_project(tmp_path / ".outrage")

    status, output = run(
        "ls", "--dir", str(tmp_path / ".outrage"), "--unmount", "ref", "--recursive"
    )

    assert status == 0
    assert "ref/python/asyncio" not in output
    assert "team/plans/q3" in output


def test_unmounting_what_is_not_mounted_is_a_message(tmp_path, capsys):
    a_mounted_project(tmp_path / ".outrage")

    status = main(["ls", "--dir", str(tmp_path / ".outrage"), "--unmount", "rf"], io.StringIO())

    assert status == 1
    assert "removes nothing" in capsys.readouterr().err


# `outrage mounts`: what a command line would open, said before it opens it.


def test_mounts_reports_the_table_and_where_each_entry_came_from(tmp_path):
    a_mounted_project(tmp_path / ".outrage")

    status, output = run("mounts", "--dir", str(tmp_path / ".outrage"))

    assert status == 0
    rows = {line.split()[0]: line for line in output.splitlines()}
    table = str(tmp_path / ".outrage" / "mounts.toml")
    assert rows["/"].split()[1:4] == ["store.sqlite", "root", "ok"]
    # The root is the one entry nobody named, and the column says so rather
    # than crediting a file or a command line that never mentioned it.
    assert rows["/"].endswith("default")
    assert rows["ref"].split()[1] == "reference.sqlite"
    assert "read-only mount" in rows["ref"]
    assert rows["ref"].endswith(table) and rows["team"].endswith(table)


def test_mounts_opens_nothing_and_so_creates_nothing(tmp_path):
    """The gap this closes, and the reason it cannot just be `outrage ls`.

    Opening a read-write mount is what *creates* it, so a mistyped name in a
    committed table becomes an empty store that reads exactly like a store with
    nothing in it yet - and looking is what does it. This looks without opening.
    """
    a_mounted_project(tmp_path / ".outrage")
    before = sorted(p.name for p in (tmp_path / ".outrage").iterdir())

    status, output = run(
        "mounts", "--dir", str(tmp_path / ".outrage"), "--mount", "typo=teem.sqlite"
    )

    assert status == 0
    assert "would create" in output
    assert sorted(p.name for p in (tmp_path / ".outrage").iterdir()) == before


def test_mounts_fails_on_a_table_that_would_not_open(tmp_path):
    """A read-only mount that is not there is the refusal `open_mounts` makes,
    said here rather than at the moment a server failed to start."""
    a_mounted_project(tmp_path / ".outrage")

    status, output = run(
        "mounts", "--dir", str(tmp_path / ".outrage"), "--mount-ro", "gone=gone.sqlite"
    )

    assert status == 1
    assert "missing" in output


def test_mounts_reports_a_duplicate_rather_than_stopping_at_it(tmp_path):
    """Unlike everywhere else, and deliberately: a report that stopped at the
    first thing wrong with a table would stop at the least useful moment."""
    a_mounted_project(tmp_path / ".outrage")

    status, output = run(
        "mounts",
        "--dir",
        str(tmp_path / ".outrage"),
        "--mount",
        "team=a.sqlite",
        "--mount",
        "team=b.sqlite",
    )

    assert status == 1
    assert "duplicate" in output
    assert "a.sqlite" in output and "b.sqlite" in output


def test_mounts_answers_for_the_line_that_was_actually_written(tmp_path):
    """Every option the other commands take, so it reports the real table.

    Including which source won, which is the question the splice created: an
    overridden entry is not shown, because it is not in the table either.
    """
    a_mounted_project(tmp_path / ".outrage")

    status, output = run(
        "mounts",
        "--dir",
        str(tmp_path / ".outrage"),
        "--unmount",
        "ref",
        "--mount",
        "team=store.sqlite",
    )

    assert status == 0
    assert "ref" not in output
    assert "team.sqlite" not in output
    assert "the command line" in output


# The documentation shipped inside the package. The command line does not carry
# it: a bare `outrage` is a clean namespace over the project's own store, and
# `--mount-docs` is how a person asks for the manual.


def test_the_documentation_is_not_mounted_unless_asked(tmp_path):
    a_store(tmp_path / ".outrage")

    status, output = run("ls", "--dir", str(tmp_path / ".outrage"))

    assert status == 0
    assert "outrage" not in output


def test_the_documentation_mounts_when_asked(tmp_path):
    a_store(tmp_path / ".outrage")

    status, output = run("ls", "outrage", "--dir", str(tmp_path / ".outrage"), mountfile.DOCS_FLAG)

    assert status == 0
    assert "outrage/readme" in output


def test_a_write_into_the_documentation_is_refused(tmp_path, capsys):
    a_store(tmp_path / ".outrage")

    status = main(
        [
            "set",
            "outrage/readme",
            "--dir",
            str(tmp_path / ".outrage"),
            mountfile.DOCS_FLAG,
            "--content",
            "no",
        ],
        io.StringIO(),
    )

    assert status == 1
    assert "read-only" in capsys.readouterr().err


def test_mounts_reports_the_documentation_where_it_really_is(tmp_path):
    """Absolute, and not a file inside --dir: it is in the installation.

    That is the whole reason it is a flag rather than a spec -- `store_file`
    refuses an absolute path, correctly, and a mount configuration would not be
    relocatable if it did not.
    """
    status, output = run("mounts", "--dir", str(tmp_path / ".outrage"), mountfile.DOCS_FLAG)

    assert status == 0
    row = next(line for line in output.splitlines() if line.startswith("outrage "))
    assert str(shipped.tree()) in row
    assert "read-only mount" in row and " ok " in row


def test_asking_for_it_twice_over_is_reported_as_a_duplicate(tmp_path):
    """Two claims on one point, typed on one line: the mistake, not an override."""
    status, output = run(
        "mounts",
        "--dir",
        str(tmp_path / ".outrage"),
        mountfile.DOCS_FLAG,
        "--mount",
        "outrage=mine.sqlite",
    )

    assert status == 1
    assert "duplicate" in output
