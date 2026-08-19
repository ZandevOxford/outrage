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
        store.store_document("notes/long/!summary", value)

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


# -- get and set ---------------------------------------------------------


def test_get_prints_a_long_document_whole(tmp_path):
    content = a_long_store(tmp_path / ".rage")

    status, output = run("get", "--dir", str(tmp_path / ".rage"), "notes/long")

    assert status == 0
    assert output == content


def test_get_writes_no_newline_of_its_own(tmp_path, capsys):
    from rage.store import Store

    with Store(tmp_path / ".rage") as store:
        store.store_document("notes/one", "no trailing newline here")

    _, output = run("get", "--dir", str(tmp_path / ".rage"), "notes/one")

    assert output == "no trailing newline here"


def test_get_and_set_round_trip_at_the_same_length(tmp_path):
    content = a_long_store(tmp_path / ".rage")
    exported = tmp_path / "exported.md"

    _, output = run("get", "--dir", str(tmp_path / ".rage"), "notes/long")
    exported.write_text(output)
    run("set", "--dir", str(tmp_path / ".rage"), "notes/copy", "--file", str(exported))
    _, back = run("get", "--dir", str(tmp_path / ".rage"), "notes/copy")

    # The whole point of writing no trailing newline: a document that grows a
    # character every time it is exported and re-imported is a corrupted one.
    assert back == content


def test_get_caps_when_asked_and_says_where_to_resume(tmp_path, capsys):
    a_long_store(tmp_path / ".rage")

    status, output = run(
        "get", "--dir", str(tmp_path / ".rage"), "notes/long", "--max-chars", "100"
    )

    assert status == 0
    assert len(output) == 100
    # On stderr, so that a redirect to a file gets the content and the person
    # watching still learns the file is a fragment.
    assert "more from --offset 100" in capsys.readouterr().err


def test_get_starts_at_a_pattern_and_still_reads_to_the_end(tmp_path):
    content = a_long_store(tmp_path / ".rage")

    _, output = run(
        "get", "--dir", str(tmp_path / ".rage"), "notes/long", "--pattern", "end of the document"
    )

    assert output == content[content.index("end of the document") :]


def test_get_length_caps_the_whole_read_not_just_the_first_slice(tmp_path):
    a_long_store(tmp_path / ".rage")

    _, output = run("get", "--dir", str(tmp_path / ".rage"), "notes/long", "--length", "20000")

    # Longer than one slice, so it is delivered by the continuation loop. A
    # --length that stops binding once it exceeds max_chars is a bound that
    # silently is not one.
    assert len(output) == 20000


def test_set_reports_where_it_wrote(tmp_path):
    status, output = run("set", "--dir", str(tmp_path / ".rage"), "notes/one", "--content", "hello")

    assert status == 0
    assert "notes/one" in output
    assert "5 characters" in output
    assert str(tmp_path / ".rage" / "store.sqlite") in output


def test_set_allocates_a_number_and_names_the_key_it_wrote(tmp_path):
    run("set", "--dir", str(tmp_path / ".rage"), "notes/?", "--content", "first")

    _, output = run("set", "--dir", str(tmp_path / ".rage"), "notes/?", "--content", "second")

    assert output.startswith("notes/2 ")


def test_set_refuses_two_sources(tmp_path, capsys):
    status = main(
        ["set", "--dir", str(tmp_path / ".rage"), "notes/one", "--content", "x", "--file", "f"],
        io.StringIO(),
    )

    assert status == 1
    assert "not both" in capsys.readouterr().err


def test_reading_a_store_that_is_not_there_is_refused(tmp_path, capsys):
    status = main(["get", "--dir", str(tmp_path / "absent"), "notes/one"], io.StringIO())

    # Store() would create one, and an empty store answers every question with
    # a confident nothing.
    assert status == 1
    assert "no store in" in capsys.readouterr().err
    assert not (tmp_path / "absent").exists()


# -- ls ------------------------------------------------------------------


def a_tree(directory: Path) -> None:
    """A store with a container, documents beneath it, and metadata."""
    from rage.store import Store

    with Store(directory) as store:
        for number in (1, 2, 10):
            store.store_document(f"notes/{number}", f"body {number}", title=f"Note {number}")
        store.store_document("notes/1/detail", "deeper")


def test_ls_lists_one_level_with_kinds(tmp_path):
    a_tree(tmp_path / ".rage")

    status, output = run("ls", "--dir", str(tmp_path / ".rage"), "notes")

    assert status == 0
    listed = [line.split()[-1] for line in output.splitlines()]
    assert listed == ["notes/1", "notes/2", "notes/10"]
    assert "document" in output


def test_ls_sorts_numeric_segments_as_numbers(tmp_path):
    a_tree(tmp_path / ".rage")

    _, output = run("ls", "--dir", str(tmp_path / ".rage"), "notes")

    assert output.index("notes/2") < output.index("notes/10")


def test_ls_shows_metadata_and_subkeys_under_a_document(tmp_path):
    a_tree(tmp_path / ".rage")

    _, output = run("ls", "--dir", str(tmp_path / ".rage"), "notes/1")

    assert "notes/1/!title" in output
    assert "metadata" in output
    assert "notes/1/detail" in output


def test_ls_recursive_reaches_the_bottom(tmp_path):
    a_tree(tmp_path / ".rage")

    _, output = run("ls", "--dir", str(tmp_path / ".rage"), "--recursive", "notes")

    assert "notes/1/detail" in output
    assert "notes/10/!title" in output


def test_ls_recursive_from_the_top_reports_the_container(tmp_path):
    a_tree(tmp_path / ".rage")

    _, output = run("ls", "--dir", str(tmp_path / ".rage"), "--recursive")

    # Only list_keys reports a key that holds nothing itself; leaving it out is
    # how everything beneath it looks parentless.
    assert "implicit" in output
    assert output.index("  notes\n") < output.index("  notes/1\n")


def test_ls_says_so_when_there_is_nothing(tmp_path):
    a_tree(tmp_path / ".rage")

    _, output = run("ls", "--dir", str(tmp_path / ".rage"), "notes/1/detail")

    assert "nothing below notes/1/detail" in output


# -- rm ------------------------------------------------------------------


def test_rm_takes_the_metadata_with_the_document(tmp_path):
    a_tree(tmp_path / ".rage")

    status, output = run("rm", "--dir", str(tmp_path / ".rage"), "notes/2")

    assert status == 0
    assert "deleted notes/2" in output
    assert "deleted notes/2/!title" in output


def test_rm_leaves_the_subtree_and_says_it_did(tmp_path):
    a_tree(tmp_path / ".rage")

    _, output = run("rm", "--dir", str(tmp_path / ".rage"), "notes/1")

    assert "1 keys below notes/1 remain" in output
    _, listing = run("ls", "--dir", str(tmp_path / ".rage"), "notes/1")
    assert "notes/1/detail" in listing


def test_rm_dry_run_deletes_nothing(tmp_path):
    a_tree(tmp_path / ".rage")

    _, output = run("rm", "--dir", str(tmp_path / ".rage"), "notes/1", "--dry-run")

    assert "would delete notes/1" in output
    assert "would remain" in output
    _, listing = run("ls", "--dir", str(tmp_path / ".rage"), "notes")
    assert "notes/1" in listing


def test_rm_dry_run_previews_the_subtree_it_would_take(tmp_path):
    a_tree(tmp_path / ".rage")

    _, output = run("rm", "--dir", str(tmp_path / ".rage"), "notes/1", "--recursive", "--dry-run")

    assert "and below: notes/1/detail" in output
    _, listing = run("ls", "--dir", str(tmp_path / ".rage"), "notes/1")
    assert "notes/1/detail" in listing


def test_rm_recursive_takes_the_subtree(tmp_path):
    a_tree(tmp_path / ".rage")

    _, output = run("rm", "--dir", str(tmp_path / ".rage"), "notes/1", "--recursive")

    assert "deleted notes/1/detail" in output
    assert "remain" not in output


def test_rm_says_when_there_was_nothing_there(tmp_path):
    a_tree(tmp_path / ".rage")

    _, output = run("rm", "--dir", str(tmp_path / ".rage"), "notes/absent")

    assert "nothing stored at notes/absent" in output


# -- check ---------------------------------------------------------------


def test_check_reports_a_sound_store(tmp_path):
    a_tree(tmp_path / ".rage")

    status, output = run("check", "--dir", str(tmp_path / ".rage"))

    assert status == 0
    assert "integrity ok" in output
    assert "nothing wrong" in output


def test_check_refuses_a_directory_with_no_store(tmp_path, capsys):
    status = main(["check", "--dir", str(tmp_path / "absent")], io.StringIO())

    assert status == 1
    assert "no store in" in capsys.readouterr().err


def test_check_reports_a_row_stored_under_the_wrong_parent(tmp_path):
    import sqlite3

    a_tree(tmp_path / ".rage")
    connection = sqlite3.connect(tmp_path / ".rage" / "store.sqlite")
    connection.execute("UPDATE documents SET parent = 'elsewhere' WHERE key = 'notes/2'")
    connection.commit()
    connection.close()

    status, output = run("check", "--dir", str(tmp_path / ".rage"))

    # Readable by key and invisible to every listing, which is the failure this
    # check exists for: nothing in normal reading would notice.
    assert status == 1
    assert "disagree with the key they are stored under" in output
    assert "notes/2" in output


def test_check_repairs_the_write_ahead_log(tmp_path):
    from rage.store import Store

    directory = tmp_path / ".rage"
    with Store(directory) as store:
        store.store_document("notes/one", "x" * 200000)

    database = directory / "store.sqlite"
    log = directory / "store.sqlite-wal"
    # Reproduce an unfolded log: writes land in the sidecar, and closing the
    # store is what would normally checkpoint them back.
    held_open = Store(directory)
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
    from rage.store import Store

    with Store(directory) as store:
        for number in range(1, count + 1):
            store.store_document(f"notes/{number}", content, title=f"Note {number}")


def test_ls_lists_a_level_larger_than_one_page(tmp_path):
    a_wide_store(tmp_path / ".rage", 250)

    status, output = run("ls", "--dir", str(tmp_path / ".rage"), "notes")

    # A listing that stops at an internal page size is the silent partial
    # answer, delivered by the layer that was supposed to prevent it.
    assert status == 0
    # A title is a child of its own document, not of the level, so this is 250
    # keys rather than 500.
    assert len(output.splitlines()) == 250
    assert "notes/250" in output


def test_ls_pages_rather_than_asking_for_everything(tmp_path, monkeypatch):
    import rage.bulk

    a_wide_store(tmp_path / ".rage", 20)
    monkeypatch.setattr(rage.bulk, "PAGE", 3)

    _, output = run("ls", "--dir", str(tmp_path / ".rage"), "notes")

    assert len(output.splitlines()) == 20


def test_ls_recursive_pages_at_every_level(tmp_path, monkeypatch):
    import rage.bulk
    from rage.store import Store

    with Store(tmp_path / ".rage") as store:
        for number in range(1, 8):
            store.store_document(f"deep/{number}/leaf", "content")
    monkeypatch.setattr(rage.bulk, "PAGE", 2)

    _, output = run("ls", "--dir", str(tmp_path / ".rage"), "--recursive", "deep")

    assert [line.split()[-1] for line in output.splitlines()] == [
        key for number in range(1, 8) for key in (f"deep/{number}", f"deep/{number}/leaf")
    ]


def test_ls_limit_shows_less_and_says_so(tmp_path, capsys):
    a_wide_store(tmp_path / ".rage", 20)

    _, output = run("ls", "--dir", str(tmp_path / ".rage"), "notes", "--limit", "3")

    assert len(output.splitlines()) == 3
    # On stderr: the listing itself stays clean for whatever it is piped into.
    assert "stopped at --limit 3" in capsys.readouterr().err


def test_dump_exports_more_than_one_page_whole(tmp_path, monkeypatch):
    import rage.bulk

    a_wide_store(tmp_path / ".rage", 10, content="x" * 3000)
    monkeypatch.setattr(rage.bulk, "PAGE", 2)

    _, output = run("dump", "--dir", str(tmp_path / ".rage"), "notes")

    # Complete by default, across pages and past the per-document cap: an
    # export that quietly holds back is the failure this command exists to
    # avoid, and paging is a new way to commit it.
    assert output.count("x" * 3000) == 10
    assert "characters]" not in output


def test_dump_limit_shows_less_and_says_so(tmp_path, capsys):
    a_wide_store(tmp_path / ".rage", 10)

    _, output = run("dump", "--dir", str(tmp_path / ".rage"), "notes", "--limit", "2")

    assert output.count("=== ") == 2
    assert "stopped at --limit 2" in capsys.readouterr().err


def test_dump_asks_for_one_page_before_printing_anything(tmp_path, monkeypatch):
    import argparse

    import rage.bulk
    import rage.cli
    from rage.store import Store

    a_wide_store(tmp_path / ".rage", 10)
    monkeypatch.setattr(rage.bulk, "PAGE", 2)

    calls = 0
    original = Store.get_documents

    def counted(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Store, "get_documents", counted)

    with Store(tmp_path / ".rage") as opened:
        arguments = argparse.Namespace(key="notes", meta_name=None, depth=None, max_chars=None)
        first = next(rage.cli._documents(opened, arguments))

    # Lazy, not merely paged: an export that reads the whole subtree before
    # writing its first line is the shape that fails at the size it matters.
    assert first.key == "notes/1"
    assert calls == 1


def test_rm_dry_run_previews_the_whole_subtree_not_one_level(tmp_path):
    from rage.store import Store

    with Store(tmp_path / ".rage") as store:
        store.store_document("tree/one", "content")
        store.store_document("tree/one/two/three", "content")

    _, output = run("rm", "--dir", str(tmp_path / ".rage"), "tree", "--recursive", "--dry-run")

    # Previewing one level of a deletion that reaches three is not a preview.
    assert "and below: tree/one/two/three" in output


def test_rm_dry_run_preview_can_be_shortened(tmp_path):
    a_wide_store(tmp_path / ".rage", 10)

    _, output = run(
        "rm", "--dir", str(tmp_path / ".rage"), "notes", "--recursive", "--dry-run", "--limit", "3"
    )

    assert output.count("and below:") == 3
    # The count comes from the store, so a shortened preview still says how
    # much it is shortening.
    assert "and 17 more" in output


def test_a_malformed_key_is_one_line_and_not_a_traceback(tmp_path, capsys):
    # An invalid key is about the request, so it renders as one line rather
    # than reaching the top of main as a bug would. The example used to be the
    # pre-schema-4 `:` spelling; `:` is an ordinary segment character since
    # schema 5, so the malformation has to be a real one.
    a_long_store(tmp_path / ".rage")

    status, _ = run("get", "--dir", str(tmp_path / ".rage"), "!title")

    assert status != 0
    err = capsys.readouterr().err
    assert "metadata segment" in err
    assert "Traceback" not in err
    assert err.count("\n") == 1


# -- export and import ---------------------------------------------------


def an_exportable_store(directory: Path) -> Path:
    from rage.store import Store

    with Store(directory) as store:
        store.store_document("project", "# Project", title="The project")
        store.store_document("project/reference/env", '{"python": "3.14"}')
    return directory


def test_export_writes_a_file_per_document(tmp_path, capsys):
    an_exportable_store(tmp_path / ".rage")

    status, output = run("export", "--dir", str(tmp_path / ".rage"), str(tmp_path / "out"))

    assert status == 0
    assert (tmp_path / "out/project.md").read_text() == "# Project"
    assert (tmp_path / "out/project/!title.md").read_text() == "The project"
    assert (tmp_path / "out/project/reference/env.json").exists()
    assert "wrote" in output
    # The counts go to stderr, so a report piped onward is not corrupted by a
    # note about itself.
    assert "3 written" in capsys.readouterr().err


def test_export_dry_run_writes_nothing(tmp_path):
    an_exportable_store(tmp_path / ".rage")

    status, output = run(
        "export", "--dir", str(tmp_path / ".rage"), str(tmp_path / "out"), "--dry-run"
    )

    assert status == 0
    assert "would write" in output
    assert not (tmp_path / "out").exists()


def test_export_refuses_a_store_that_is_not_there(tmp_path, capsys):
    status, _ = run("export", "--dir", str(tmp_path / ".rage"), str(tmp_path / "out"))

    assert status == 1
    assert "rage:" in capsys.readouterr().err


def test_import_stores_a_directory_and_says_where(tmp_path, capsys):
    an_exportable_store(tmp_path / ".rage")
    run("export", "--dir", str(tmp_path / ".rage"), str(tmp_path / "out"))

    status, output = run("import", "--dir", str(tmp_path / "fresh"), str(tmp_path / "out"))

    assert status == 0
    assert "wrote" in output
    # A first write may create the store, as `rage set` may: seeding an empty
    # one from a directory is that write in bulk. Saying where it went is then
    # the only thing that makes a mistyped --dir visible.
    assert str(tmp_path / "fresh" / "store.sqlite") in capsys.readouterr().err

    _, listed = run("ls", "--dir", str(tmp_path / "fresh"), "--recursive")
    assert "project/reference/env" in listed


def test_import_leaves_what_is_already_stored(tmp_path):
    an_exportable_store(tmp_path / ".rage")
    run("export", "--dir", str(tmp_path / ".rage"), str(tmp_path / "out"))
    (tmp_path / "out/project.md").write_text("# Changed on disk")

    status, output = run("import", "--dir", str(tmp_path / ".rage"), str(tmp_path / "out"))

    assert status == 0
    assert "skipped" in output
    _, content = run("get", "--dir", str(tmp_path / ".rage"), "project")
    assert content == "# Project"


def test_import_overwrites_when_asked(tmp_path):
    an_exportable_store(tmp_path / ".rage")
    run("export", "--dir", str(tmp_path / ".rage"), str(tmp_path / "out"))
    (tmp_path / "out/project.md").write_text("# Changed on disk")

    run(
        "import",
        "--dir",
        str(tmp_path / ".rage"),
        str(tmp_path / "out"),
        "--on-conflict",
        "overwrite",
    )

    _, content = run("get", "--dir", str(tmp_path / ".rage"), "project")
    assert content == "# Changed on disk"


def test_import_stopping_at_a_conflict_is_a_failed_run(tmp_path):
    an_exportable_store(tmp_path / ".rage")
    run("export", "--dir", str(tmp_path / ".rage"), str(tmp_path / "out"))

    status, output = run(
        "import", "--dir", str(tmp_path / ".rage"), str(tmp_path / "out"), "--on-conflict", "stop"
    )

    # The exit status is the only part of a partial run a script can see.
    assert status == 1
    assert "stopped" in output


def test_import_under_a_key_grafts_the_tree(tmp_path):
    an_exportable_store(tmp_path / ".rage")
    run("export", "--dir", str(tmp_path / ".rage"), str(tmp_path / "out"))

    run("import", "--dir", str(tmp_path / ".rage"), str(tmp_path / "out"), "archive/2026")

    _, content = run("get", "--dir", str(tmp_path / ".rage"), "archive/2026/project")
    assert content == "# Project"


# -- init ----------------------------------------------------------------


def test_init_arranges_the_whole_project(tmp_path):
    status, output = run("init", "--project-dir", str(tmp_path))

    assert status == 0
    assert servers(tmp_path / ".mcp.json")["rage"]
    assert (tmp_path / ".claude" / "settings.json").is_file()
    assert (tmp_path / ".claude" / "skills" / "rage" / "SKILL.md").is_file()
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
    assert "skills/rage/SKILL.md" in output


def test_init_records_the_store_directory_and_the_log(tmp_path):
    run("init", "--project-dir", str(tmp_path), "--dir", str(tmp_path / "store"), "--log")

    args = servers(tmp_path / ".mcp.json")["rage"]["args"]
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
