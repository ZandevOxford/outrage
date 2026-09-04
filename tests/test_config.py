"""Tests for writing the MCP server configuration.

The risk this command carries is not that it fails but that it succeeds
wrongly: a config naming the wrong environment, a relative store path that
resolves somewhere else at launch, or an unrelated key lost from a file that
holds far more than this server's entry. Most of what follows guards those.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pytest

from conftest import raises_rendered
from outrage import config as config_module
from outrage import eventlog, mountfile, mounts, store
from outrage.config import (
    Change,
    ConfigError,
    config_path,
    launch_command,
    plan,
    read_config,
    server_entry,
    write_config,
)


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def apply(path: Path, entry: dict, name: str = "outrage") -> Change:
    """Plan and write in one step, as the command does."""
    change, merged, original = plan(path, "project", entry, name=name)
    if change.writes:
        write_config(path, merged, original)
    return change


# -- the launch command --------------------------------------------------


def test_prefers_the_console_script_beside_the_interpreter(tmp_path):
    python = tmp_path / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.touch()
    script = tmp_path / "bin" / "outrage-server"
    script.touch()
    script.chmod(script.stat().st_mode | stat.S_IXUSR)

    assert launch_command(python) == [str(script)]


def test_falls_back_to_the_module_when_no_script_is_installed(tmp_path):
    python = tmp_path / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.touch()

    # Equivalent, and cannot be missing: it needs only the interpreter that is
    # running and the package that is already imported.
    assert launch_command(python) == [str(python), "-m", "outrage"]


def test_the_real_interpreter_yields_an_absolute_command():
    command = launch_command()
    assert Path(command[0]).is_absolute()
    assert Path(command[0]).exists()
    assert command[0] != "outrage-server", "a bare name would resolve against the client's PATH"


# -- the entry -----------------------------------------------------------


def test_store_directory_is_recorded_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entry = server_entry(".outrage", command=["/env/bin/outrage-server"])

    recorded = Path(entry["args"][entry["args"].index("--dir") + 1])
    assert recorded.is_absolute()
    # A relative --dir would resolve against wherever the client happened to
    # launch the server, creating a second empty store instead of failing.
    assert recorded == (tmp_path / ".outrage").resolve()


def test_entry_keeps_extra_command_arguments(tmp_path):
    entry = server_entry(tmp_path, command=[sys.executable, "-m", "outrage"])
    assert entry["command"] == sys.executable
    assert entry["args"] == ["-m", "outrage", "--dir", str(tmp_path.resolve())]


def test_an_entry_asks_for_no_logging_unless_told_to(tmp_path):
    assert "--log" not in server_entry(tmp_path, command=["outrage-server"])["args"]


def test_a_bare_log_flag_leaves_the_path_to_the_server(tmp_path):
    entry = server_entry(tmp_path, command=["outrage-server"], log=eventlog.DEFAULT)
    assert entry["args"][-1] == "--log"


def test_a_log_path_is_recorded_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entry = server_entry(tmp_path, command=["outrage-server"], log="log.jsonl")

    # Same reason the store directory is: a relative path resolves against
    # wherever the client happened to launch the server.
    assert entry["args"][-1] == str((tmp_path / "log.jsonl").resolve())


def test_the_content_policy_travels_with_the_flag(tmp_path):
    entry = server_entry(
        tmp_path, command=["outrage-server"], log=eventlog.DEFAULT, log_content="none"
    )
    assert entry["args"][-2:] == ["--log-content", "none"]


# -- scopes --------------------------------------------------------------


def test_project_scope_is_mcp_json_in_the_project(tmp_path):
    assert config_path("project", tmp_path) == tmp_path.resolve() / ".mcp.json"


def test_user_scope_is_in_the_home_directory():
    assert config_path("user") == Path.home() / ".claude.json"


def test_unknown_scope_is_rejected():
    with pytest.raises(ValueError, match="unknown scope"):
        config_path("global")


# -- writing -------------------------------------------------------------


def test_creates_a_configuration_file(tmp_path):
    path = tmp_path / ".mcp.json"
    change = apply(path, {"command": "/env/bin/outrage-server", "args": ["--dir", "/store"]})

    assert change.action == "created"
    written = json.loads(path.read_text())["mcpServers"]["outrage"]
    assert written["command"] == "/env/bin/outrage-server"


def test_rerunning_with_the_same_entry_changes_nothing(tmp_path):
    path = tmp_path / ".mcp.json"
    entry = {"command": "/env/bin/outrage-server", "args": ["--dir", "/store"]}
    apply(path, entry)
    before = path.read_text()

    change = apply(path, entry)

    assert change.action == "unchanged"
    assert not change.writes
    assert path.read_text() == before


def test_rerunning_after_the_environment_moves_repairs_the_entry(tmp_path):
    path = tmp_path / ".mcp.json"
    apply(path, {"command": "/old/bin/outrage-server", "args": ["--dir", "/store"]})

    change = apply(path, {"command": "/new/bin/outrage-server", "args": ["--dir", "/store"]})

    assert change.action == "updated"
    assert change.previous == {"command": "/old/bin/outrage-server", "args": ["--dir", "/store"]}
    written = json.loads(path.read_text())["mcpServers"]["outrage"]
    assert written["command"] == "/new/bin/outrage-server"


def test_other_servers_and_other_keys_survive(tmp_path):
    path = tmp_path / ".mcp.json"
    write_json(
        path,
        {
            "numStartups": 7,
            "mcpServers": {"other": {"command": "/somewhere/else", "args": ["--flag"]}},
        },
    )

    apply(path, {"command": "/env/bin/outrage-server", "args": ["--dir", "/store"]})

    written = json.loads(path.read_text())
    assert written["numStartups"] == 7
    assert written["mcpServers"]["other"] == {"command": "/somewhere/else", "args": ["--flag"]}
    assert set(written["mcpServers"]) == {"other", "outrage"}


def test_a_custom_name_leaves_the_default_entry_alone(tmp_path):
    path = tmp_path / ".mcp.json"
    apply(path, {"command": "/env/bin/outrage-server", "args": []})
    apply(path, {"command": "/other/bin/outrage-server", "args": []}, name="outrage-notes")

    servers = json.loads(path.read_text())["mcpServers"]
    assert servers["outrage"]["command"] == "/env/bin/outrage-server"
    assert servers["outrage-notes"]["command"] == "/other/bin/outrage-server"


def test_empty_file_is_treated_as_empty_configuration(tmp_path):
    path = tmp_path / ".mcp.json"
    path.write_text("", encoding="utf-8")

    change = apply(path, {"command": "/env/bin/outrage-server", "args": []})

    assert change.action == "created"
    assert "outrage" in json.loads(path.read_text())["mcpServers"]


# -- refusing to write ---------------------------------------------------


def test_unparseable_file_is_left_alone(tmp_path):
    # The user scoped file holds a great deal besides MCP servers. Overwriting
    # it because one read failed would cost far more than declining to write.
    path = tmp_path / ".claude.json"
    path.write_text('{"broken": ', encoding="utf-8")

    with raises_rendered(ConfigError, "not valid JSON"):
        plan(path, "user", {"command": "x", "args": []})

    assert path.read_text() == '{"broken": '


def test_non_object_file_is_left_alone(tmp_path):
    path = tmp_path / ".mcp.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")

    with raises_rendered(ConfigError, "does not hold a JSON object"):
        plan(path, "project", {"command": "x", "args": []})


def test_non_object_servers_field_is_left_alone(tmp_path):
    path = tmp_path / ".mcp.json"
    write_json(path, {"mcpServers": ["outrage"]})

    with raises_rendered(ConfigError, "not an object"):
        plan(path, "project", {"command": "x", "args": []})


def test_non_object_existing_entry_is_left_alone(tmp_path):
    path = tmp_path / ".mcp.json"
    write_json(path, {"mcpServers": {"outrage": "outrage-server"}})

    with raises_rendered(ConfigError, "not an object"):
        plan(path, "project", {"command": "x", "args": []})


# -- how the file is written ---------------------------------------------


def test_existing_permissions_are_kept(tmp_path):
    path = tmp_path / ".claude.json"
    write_json(path, {"numStartups": 7})
    path.chmod(0o600)

    apply(path, {"command": "/env/bin/outrage-server", "args": []})

    # mkstemp's default would be right here by luck; the risk is the reverse,
    # a 0600 file rewritten world readable.
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_a_new_user_file_is_private(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    path = config_path("user")

    write_config(path, {"mcpServers": {}})

    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_a_new_project_file_is_readable(tmp_path):
    path = tmp_path / ".mcp.json"

    write_config(path, {"mcpServers": {}})

    # It belongs to the checkout, and is meant to be committed and shared.
    assert stat.S_IMODE(path.stat().st_mode) == 0o644


def test_indentation_of_an_existing_file_is_matched(tmp_path):
    path = tmp_path / ".claude.json"
    path.write_text(json.dumps({"numStartups": 7}, indent=4) + "\n", encoding="utf-8")

    apply(path, {"command": "/env/bin/outrage-server", "args": []})

    # Changing one key should not rewrite every line of a file this command
    # does not own.
    assert '\n    "numStartups"' in path.read_text()


def test_no_temporary_file_is_left_behind(tmp_path):
    path = tmp_path / ".mcp.json"
    apply(path, {"command": "/env/bin/outrage-server", "args": []})

    assert [p.name for p in tmp_path.iterdir()] == [".mcp.json"]


def test_a_failed_write_leaves_the_original_intact(tmp_path, monkeypatch):
    path = tmp_path / ".mcp.json"
    write_json(path, {"mcpServers": {"other": {"command": "/somewhere/else"}}})
    before = path.read_text()

    def explode(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", explode)

    with pytest.raises(OSError, match="disk full"):
        write_config(path, {"mcpServers": {}}, before)

    assert path.read_text() == before
    assert [p.name for p in tmp_path.iterdir()] == [".mcp.json"]


def test_read_config_reports_a_missing_file_as_empty(tmp_path):
    config, original = read_config(tmp_path / "absent.json")
    assert config == {}
    assert original is None


def test_server_name_is_the_key_that_gets_replaced():
    # The whole "leave unrelated servers alone" property rests on this.
    assert config_module.SERVER_NAME == "outrage"
    assert config_module.SERVERS_FIELD == "mcpServers"


def test_the_entry_no_longer_carries_the_mounts(tmp_path):
    """The payoff, and the thing this changed.

    A mount table used to be a flat run of ``--mount`` strings in this array,
    which made a client's JSON the place a table was maintained. It is
    ``mounts.toml`` in the store directory now, and what is left here is the
    one thing a file cannot hold - the directory it is in.
    """
    args = config_module.server_entry(tmp_path / "base", command=["outrage-server"])["args"]

    assert args == ["--dir", str(tmp_path / "base")]


def test_a_mount_is_written_to_the_table_beside_the_stores(tmp_path):
    """A mount names a file inside --dir, and only --dir is a path.

    The opposite of what this used to assert about a mount being absolute: it
    is a store *in* the directory, and resolving it would put back the absolute
    path that stops being true the moment the project moves.
    """
    table = mountfile.plan_starter(
        tmp_path / "base",
        mounts=["ref=reference.sqlite", "lib/deep=stores/deep.sqlite"],
    )
    mountfile.write_starter(table)

    written = mountfile.read(tmp_path / "base" / mountfile.DEFAULT_NAME)
    assert written.mounts == (
        ("ref", mounts.Spec(Path("reference.sqlite"))),
        ("lib/deep", mounts.Spec(Path("stores/deep.sqlite"))),
    )
    assert "# Mounted read-write." in table.text


def test_the_root_mount_is_written_only_when_it_is_not_the_default(tmp_path):
    # An entry that never asked for one is not written to say what it already
    # meant -- which is what keeps a re-run reporting "already current".
    assert not mountfile.plan_starter(tmp_path / "a").writes
    assert not mountfile.plan_starter(tmp_path / "b", root_mount=store.default_store_file()).writes

    named = mountfile.plan_starter(tmp_path / "c", root_mount="main.sqlite")
    assert named.writes
    mountfile.write_starter(named)
    assert mountfile.read(named.path).root == mounts.Spec(Path("main.sqlite"))


def test_a_misspelled_mount_point_is_refused_while_writing_the_table(tmp_path):
    """Refused here, where somebody is looking, rather than by a server nobody sees."""
    from outrage.mounts import MountError

    with pytest.raises(MountError):
        mountfile.plan_starter(tmp_path, mounts=["no-delimiter"])
    with raises_rendered(MountError, "no mount point"):
        mountfile.plan_starter(tmp_path, mounts=["=/srv/x"])
    with pytest.raises(MountError):
        mountfile.plan_starter(tmp_path, read_only_mounts=["no-delimiter"])


def test_a_read_only_mount_is_written_to_its_own_table(tmp_path):
    table = mountfile.plan_starter(
        tmp_path / "base",
        mounts=["lib=lib.sqlite"],
        read_only_mounts=["ref=reference.sqlite", "shared/base=shared.sqlite"],
    )
    mountfile.write_starter(table)

    written = mountfile.read(table.path)
    assert written.mounts == (("lib", mounts.Spec(Path("lib.sqlite"))),)
    assert written.read_only == (
        ("ref", mounts.Spec(Path("reference.sqlite"))),
        ("shared/base", mounts.Spec(Path("shared.sqlite"))),
    )


def test_a_table_already_there_is_reported_and_not_rewritten(tmp_path):
    """The whole reason it is TOML is comments, and a rewrite loses them.

    So a run naming a mount the file does not hold says which lines to add.
    One that names what the file already says has nothing to report at all.
    """
    mountfile.write_starter(mountfile.plan_starter(tmp_path, mounts=["ref=reference.sqlite"]))
    before = (tmp_path / mountfile.DEFAULT_NAME).read_text()

    same = mountfile.plan_starter(tmp_path, mounts=["ref=reference.sqlite"])
    more = mountfile.plan_starter(tmp_path, mounts=["team=team.sqlite"])

    assert not same.writes and same.missing == ""
    assert not more.writes
    assert more.missing == '[mount]\nteam = "team.sqlite"'
    assert (tmp_path / mountfile.DEFAULT_NAME).read_text() == before


def test_an_entry_that_still_names_mounts_is_reported_rather_than_migrated(tmp_path):
    """Nothing migrates an installed configuration, deliberately.

    Such an entry goes on working - `merge_entry` inherits what a new entry
    does not mention, and the command line comes after the file, so it still
    wins. But a table in two places with only one of them the place anybody
    looks is worth a sentence.
    """
    assert config_module.mounts_in(["--dir", "/p/.outrage", "--log"]) == []
    assert config_module.mounts_in(
        ["--dir", "/p", "--mount", "a=a.sqlite", "--mount-ro", "r=r.sqlite"]
    ) == ["--mount", "--mount-ro"]


# -- keeping what a re-run was not told about ----------------------------
#
# Reported from a real project: `outrage init`, run to install a hook, rewrote
# the server entry from the flags it was given - none - and dropped three
# mounts and `--log` that had been configured months earlier. Nothing failed.
# The server simply came back next session serving one store instead of four.


def entry_with(*args: str) -> dict:
    return {"command": "/env/bin/outrage-server", "args": list(args)}


def test_a_re_run_with_no_flags_keeps_the_mounts_and_the_log():
    previous = entry_with(
        "--dir",
        "/p/.outrage",
        "--mount",
        "test=test.sqlite",
        "--mount-ro",
        "ref=ref.sqlite",
        "--log",
    )
    plain = entry_with("--dir", "/p/.outrage")

    assert config_module.merge_entry(previous, plain) == previous


def test_naming_an_option_replaces_that_option_and_only_it():
    """All of a flag's occurrences go together: a re-run naming one mount means
    one mount, not one added to the three that were there."""
    previous = entry_with(
        "--dir",
        "/p/.outrage",
        "--mount",
        "a=a.sqlite",
        "--mount",
        "b=b.sqlite",
        "--log",
    )
    new = entry_with("--dir", "/p/.outrage", "--mount", "c=c.sqlite")

    merged = config_module.merge_entry(previous, new)

    assert merged["args"] == ["--dir", "/p/.outrage", "--mount", "c=c.sqlite", "--log"]


def test_the_directory_and_the_command_are_always_the_new_ones():
    """The absolute path into this environment is what `outrage config` is for;
    inheriting a stale one would defeat the command."""
    previous = entry_with("--dir", "/old/.outrage", "--log")
    new = {"command": "/new/bin/outrage-server", "args": ["--dir", "/new/.outrage"]}

    merged = config_module.merge_entry(previous, new)

    assert merged["command"] == "/new/bin/outrage-server"
    assert merged["args"] == ["--dir", "/new/.outrage", "--log"]


def test_an_option_this_release_has_never_heard_of_survives():
    """The rule is about shape, not a list of known flags, so that a hand-added
    argument or one from a newer release is not quietly deleted."""
    previous = entry_with("--dir", "/p/.outrage", "--future-flag", "value", "-v")
    new = entry_with("--dir", "/p/.outrage")

    merged = config_module.merge_entry(previous, new)

    assert merged["args"] == ["--dir", "/p/.outrage", "--future-flag", "value", "-v"]


def test_nothing_to_merge_from_leaves_the_new_entry_alone():
    new = entry_with("--dir", "/p/.outrage")

    assert config_module.merge_entry(None, new) == new
    assert config_module.merge_entry({}, new) == new
    assert config_module.merge_entry({"args": "not a list"}, new) == new
    assert config_module.merge_entry({"args": [1, 2]}, new) == new


def test_init_twice_leaves_a_configured_project_untouched(tmp_path):
    """The whole bug, end to end: set a project up with mounts, then re-run the
    plain command somebody would use to repair a hook.

    The entry is written by hand here because nothing writes one like it any
    more - a mount table is a file now. Which is exactly why this still
    matters: an entry an older release wrote is what an installed project has,
    nothing migrates it, and a re-run must not be what takes its mounts away.
    """
    path = tmp_path / ".mcp.json"
    entry = {
        "command": "/env/bin/outrage-server",
        "args": [
            "--dir",
            str(tmp_path / ".outrage"),
            "--mount",
            "test=test.sqlite",
            "--mount-ro",
            "ref=ref.sqlite",
            "--log",
        ],
    }
    _, merged, _ = config_module.plan(path, "project", entry)
    config_module.write_config(path, merged)
    before = path.read_text()

    plain = config_module.server_entry(tmp_path / ".outrage", ["/env/bin/outrage-server"])
    change, merged, original = config_module.plan(path, "project", plain)

    assert change.action == "unchanged"
    assert not change.writes
    config_module.write_config(path, merged, original)
    assert path.read_text() == before


def test_split_args_keeps_a_leading_bare_token():
    # `python -m outrage` puts `-m outrage` at the front of the args, so the
    # first token is not always a flag.
    split = config_module.split_args(["-m", "outrage", "--log"])
    assert split == [("-m", ["outrage"]), ("--log", [])]
    assert config_module.split_args(["bare", "--log"]) == [("", ["bare"]), ("--log", [])]
