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
import tomllib
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


def test_windows_paths_written_to_json_use_forward_slashes(monkeypatch):
    monkeypatch.setattr(config_module.sys, "platform", "win32")

    assert config_module._path_text(r"C:\Users\John\env\outrage-server.exe") == (
        "C:/Users/John/env/outrage-server.exe"
    )
    entry = server_entry(
        r"C:\Users\John\project",
        command=[r"C:\Users\John\env\outrage-server.exe"],
        log=r"C:\Users\John\logs\outrage.log",
    )
    assert entry["command"] == "C:/Users/John/env/outrage-server.exe"
    assert "C:/Users/John/project" in entry["args"][-3]
    assert "C:/Users/John/logs/outrage.log" in entry["args"][-1]
    assert "\\" not in json.dumps(entry)


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


def test_an_entry_offers_the_info_tool_unless_told_not_to(tmp_path):
    assert "--no-info" not in server_entry(tmp_path, command=["outrage-server"])["args"]
    entry = server_entry(tmp_path, command=["outrage-server"], no_info=True)
    assert entry["args"][-1] == "--no-info"


def test_a_valueless_flag_survives_a_re_run_that_does_not_mention_it(tmp_path):
    """`--no-info` takes no value, and inheritance is by flag rather than by pair.

    The failure this guards is the one `merge_entry` exists for: a re-run of
    `outrage config` meant to repair a path must not quietly hand back a tool
    somebody chose to withhold.
    """
    previous = server_entry(tmp_path, command=["outrage-server"], no_info=True)

    merged = config_module.merge_entry(previous, server_entry(tmp_path, command=["outrage-server"]))

    assert "--no-info" in merged["args"]


def test_an_entry_records_no_versioning_and_a_re_run_keeps_it(tmp_path):
    """What `outrage init` has to preserve, or the edit is lost on the next run."""
    assert "--no-versioning" not in server_entry(tmp_path, command=["outrage-server"])["args"]
    previous = server_entry(tmp_path, command=["outrage-server"], no_versioning=True)
    assert previous["args"][-1] == "--no-versioning"

    merged = config_module.merge_entry(previous, server_entry(tmp_path, command=["outrage-server"]))

    assert "--no-versioning" in merged["args"]


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


def test_a_written_entry_says_everything_the_mount_it_stands_for_said(tmp_path):
    """A starter table wrote ``path`` and ``type`` and dropped the rest.

    Found while the ``service`` option was being added, 2026-09-20: the entry
    writer named two fields rather than rendering the options a spec carries,
    so ``outrage init --mount docs=bundle,type=files,extensions=keep`` wrote a
    table mounting the bundle under the *other* mapping -- a store that reads
    as simply the wrong keys, with nothing raised and nothing to see. The
    round trip through the file is the assertion, since that is the trip the
    mount actually makes.
    """
    table = mountfile.plan_starter(
        tmp_path / "base",
        mounts=["docs=bundle,type=files,extensions=keep,lock=interprocess"],
        read_only_mounts=["ref=reference.sqlite,versioning=off"],
    )
    mountfile.write_starter(table)

    written = mountfile.read(table.path)
    assert written.mounts == (
        ("docs", mounts.Spec(Path("bundle"), "files", "keep", None, "interprocess")),
    )
    assert written.read_only == (("ref", mounts.Spec(Path("reference.sqlite"), None, None, "off")),)


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


def test_a_field_this_code_never_writes_survives():
    """The rule above, one level out, over the entry's own fields.

    An entry is an object with more in it than the two fields written here -
    a client's schema has others and a user may have added one, `env` and `cwd`
    being the ones that come up. Rebuilding the object from `command` and
    `args` took the rest with it and left an argument list that was entirely
    correct, which is why nothing looked wrong.
    """
    previous = entry_with("--dir", "/p/.outrage") | {"env": {"OUTRAGE_DEBUG": "1"}, "cwd": "/p"}
    new = entry_with("--dir", "/p/.outrage")

    merged = config_module.merge_entry(previous, new)

    assert merged["env"] == {"OUTRAGE_DEBUG": "1"}
    assert merged["cwd"] == "/p"


def test_a_field_the_new_entry_carries_replaces_the_old_one():
    previous = entry_with("--dir", "/p/.outrage") | {"type": "sse", "env": {"A": "1"}}
    new = entry_with("--dir", "/p/.outrage") | {"type": "stdio"}

    merged = config_module.merge_entry(previous, new)

    assert merged["type"] == "stdio"
    assert merged["env"] == {"A": "1"}


def test_the_new_entrys_fields_come_before_the_inherited_ones():
    """Cursor's entry leads with `type`, so an entry a re-run writes should
    still read as the shape that client documents rather than as whatever
    order the file it replaced happened to hold."""
    previous = {"env": {"A": "1"}, "command": "/old/bin/outrage-server", "args": ["--dir", "/p"]}
    new = config_module.cursor_entry(entry_with("--dir", "/p"))

    merged = config_module.merge_entry(previous, new)

    assert list(merged) == ["type", "command", "args", "env"]


def test_a_malformed_argument_list_does_not_cost_the_fields_beside_it():
    """The two halves are independent: an argument list too damaged to take
    apart says nothing about whether the `env` next to it is worth keeping."""
    previous = {"command": "/old/bin/outrage-server", "args": "not a list", "env": {"A": "1"}}
    new = entry_with("--dir", "/p/.outrage")

    merged = config_module.merge_entry(previous, new)

    assert merged["args"] == ["--dir", "/p/.outrage"]
    assert merged["env"] == {"A": "1"}


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


def test_a_hand_added_env_is_not_even_a_change(tmp_path):
    """End to end, and the report matters as much as the file.

    A project whose entry carries an `env` somebody wrote should come out of a
    re-run untouched and be *reported* as untouched, rather than rewritten as
    an update that happens to be missing something.
    """
    path = tmp_path / ".mcp.json"
    entry = config_module.server_entry(tmp_path / ".outrage", ["/env/bin/outrage-server"]) | {
        "env": {"OUTRAGE_DEBUG": "1"}
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


# -- Codex ----------------------------------------------------------------
#
# Codex reads servers from TOML, in a file it also writes itself: a tool's
# approval lands in a table below the server's. So the risks are the JSON ones
# plus the marker - an entry a re-run cannot find is an entry that is never
# repaired.

CODEX_BY_HAND = """\
model = "gpt"

[mcp_servers.outrage]
command = "/old/env/bin/outrage-server"
args = [
    "--dir",
    "/project/.outrage",
    "--mount",
    "lib=lib.sqlite",
    "--log",
]

[mcp_servers.outrage.tools.store_document]
approval_mode = "approve"

[tui]
theme = "dark"
"""


def codex_entry(tmp_path: Path, **options) -> dict:
    return server_entry(tmp_path / ".outrage", ["/env/bin/outrage-server"], marked=True, **options)


def apply_codex(path: Path, entry: dict) -> Change:
    change, document, original = config_module.plan_codex(path, entry)
    if change.writes:
        config_module.write_toml(path, document, original)
    return change


def test_the_marker_is_the_first_argument_so_no_option_can_take_it(tmp_path):
    # `--log` takes an optional path, and would read a marker after it as one.
    entry = codex_entry(tmp_path, log=eventlog.DEFAULT)
    assert entry["args"][0] == config_module.SERVER_MARKER
    assert entry["args"][-1] == "--log"


def test_the_json_entry_carries_no_marker(tmp_path):
    entry = server_entry(tmp_path / ".outrage", ["/env/bin/outrage-server"])
    assert not any(config_module.is_server_marker(arg) for arg in entry["args"])


def test_a_codex_file_is_created_with_one_marked_table(tmp_path):
    path = config_module.codex_config_path(tmp_path)

    change = apply_codex(path, codex_entry(tmp_path))

    assert change.action == "created"
    assert path.read_text().startswith("[mcp_servers.outrage]\n")
    assert path.read_text().endswith('",\n]\n'), "no blank line added at the end"
    written = tomllib.loads(path.read_text())["mcp_servers"]["outrage"]
    assert written == codex_entry(tmp_path)


def test_a_second_codex_run_changes_nothing(tmp_path):
    path = config_module.codex_config_path(tmp_path)
    apply_codex(path, codex_entry(tmp_path))
    before = path.read_text()

    change = apply_codex(path, codex_entry(tmp_path))

    assert change.action == "unchanged"
    assert path.read_text() == before


def test_an_unmarked_table_of_that_name_is_adopted_and_everything_else_kept(tmp_path):
    """The hand-written entry this feature was found beside, near enough."""
    path = tmp_path / "config.toml"
    path.write_text(CODEX_BY_HAND, encoding="utf-8")

    change = apply_codex(path, codex_entry(tmp_path))

    assert change.action == "updated"
    assert change.previous["command"] == "/old/env/bin/outrage-server"
    text = path.read_text()
    loaded = tomllib.loads(text)
    table = loaded["mcp_servers"]["outrage"]
    assert table["command"] == "/env/bin/outrage-server"
    assert table["args"] == [
        config_module.SERVER_MARKER,
        "--dir",
        str(tmp_path / ".outrage"),
        "--mount",
        "lib=lib.sqlite",
        "--log",
    ], "the directory is replaced, the mount and the log inherited"
    assert table["tools"] == {"store_document": {"approval_mode": "approve"}}
    assert loaded["model"] == "gpt"
    assert loaded["tui"] == {"theme": "dark"}
    # Only the two changed lines differ, so nothing was reformatted.
    changed = set(CODEX_BY_HAND.splitlines()) ^ set(text.splitlines())
    assert changed == {
        'command = "/old/env/bin/outrage-server"',
        'command = "/env/bin/outrage-server"',
        '    "/project/.outrage",',
        f'    "{tmp_path / ".outrage"}",',
        f'    "{config_module.SERVER_MARKER}",',
    }


def test_a_marked_table_is_found_under_another_name(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        '[mcp_servers.store]\ncommand = "/old"\n'
        'args = ["outrage-managed:mcp-server:v1", "--dir", "/d"]\n\n'
        '[mcp_servers.outrage]\ncommand = "somebody-else"\n',
        encoding="utf-8",
    )

    change = apply_codex(path, codex_entry(tmp_path))

    assert change.name == "store"
    loaded = tomllib.loads(path.read_text())["mcp_servers"]
    assert loaded["store"]["command"] == "/env/bin/outrage-server"
    assert loaded["outrage"] == {"command": "somebody-else"}


@pytest.mark.parametrize(
    "old_marker", ["outrage-managed:mcp-server:v0", "rage-managed:mcp-server:v1"]
)
def test_a_marker_of_another_version_or_name_is_replaced_not_kept(tmp_path, old_marker):
    """An old marker inherited behind `--log` would become the log's path."""
    path = tmp_path / "config.toml"
    path.write_text(
        f'[mcp_servers.outrage]\ncommand = "/old"\nargs = ["--log", "{old_marker}"]\n',
        encoding="utf-8",
    )

    apply_codex(path, codex_entry(tmp_path))

    args = tomllib.loads(path.read_text())["mcp_servers"]["outrage"]["args"]
    assert [a for a in args if config_module.is_server_marker(a)] == [config_module.SERVER_MARKER]
    assert args[0] == config_module.SERVER_MARKER


def test_a_new_table_among_others_keeps_the_blank_line_before_the_next(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[mcp_servers.other]\ncommand = "o"\n\n[tui]\na = 1\n', encoding="utf-8")

    apply_codex(path, codex_entry(tmp_path))

    text = path.read_text()
    assert "]\n\n[tui]" in text
    assert tomllib.loads(text)["mcp_servers"]["other"] == {"command": "o"}


def test_an_unparseable_codex_file_is_left_alone(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[broken\n", encoding="utf-8")

    with raises_rendered(ConfigError, "not valid TOML"):
        config_module.plan_codex(path, codex_entry(tmp_path))

    assert path.read_text() == "[broken\n"


@pytest.mark.parametrize(
    ("text", "said"),
    [
        ('mcp_servers = "outrage"\n', "'mcp_servers' that is not a table"),
        ('[mcp_servers]\noutrage = "outrage-server"\n', "'outrage' server that is not a table"),
    ],
)
def test_a_codex_file_shaped_wrongly_is_left_alone(tmp_path, text, said):
    path = tmp_path / "config.toml"
    path.write_text(text, encoding="utf-8")

    with raises_rendered(ConfigError, said):
        config_module.plan_codex(path, codex_entry(tmp_path))


def test_a_codex_file_keeps_its_permissions(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(CODEX_BY_HAND, encoding="utf-8")
    path.chmod(0o640)

    apply_codex(path, codex_entry(tmp_path))

    assert stat.S_IMODE(path.stat().st_mode) == 0o640
