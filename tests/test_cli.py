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
