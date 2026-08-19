"""Tests for installing the hook into a project's settings.

Two risks, and almost everything below guards one of them. The first is damage
to a file rage does not own: the settings hold the user's model, permissions
and their own hooks, and losing any of those to an installer is far worse than
the installer refusing to run. The second is the marker failing to identify our
own entry, which does not look like a failure at all — it looks like a hook
that quietly becomes two, then three.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from rage.config import ConfigError
from rage.install import (
    HOOK_EVENT,
    MARKER,
    TEMPLATE,
    InstallError,
    install,
    is_ours,
    plan,
    settings_path,
    template_entry,
)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def entries(path: Path) -> list:
    return read_json(path)["hooks"][HOOK_EVENT]


def marked(text: str, version: int = 1) -> dict:
    """An entry carrying our marker, as an older release would have written it."""
    return {"hooks": [{"type": "command", "command": f"echo {text!r}  # {MARKER}:v{version}"}]}


FOREIGN = {"hooks": [{"type": "command", "command": "echo 'the user own hook'"}]}


# -- the packaged template -----------------------------------------------


def test_template_ships_and_carries_the_marker():
    assert TEMPLATE.is_file(), "the template must travel with the package"
    entry = template_entry()
    assert is_ours(entry)


def test_template_is_a_fragment_holding_one_entry():
    loaded = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    assert list(loaded) == ["hooks"], "the template must claim only the key it owns"
    assert len(loaded["hooks"][HOOK_EVENT]) == 1


@pytest.mark.skipif(os.name != "posix", reason="the marker is a POSIX shell comment")
@pytest.mark.parametrize("shell", ["sh", "bash", "zsh"])
def test_the_installed_command_emits_valid_json_and_hides_the_marker(shell):
    """The whole premise: a comment that the shell drops and a client never sees.

    Run for real rather than reasoned about, because the failure mode is a hook
    that exits 0 while emitting something unparseable — which looks exactly
    like a hook that was never configured.
    """
    binary = shutil.which(shell)
    if binary is None:
        pytest.skip(f"{shell} is not installed")
    command = template_entry()["hooks"][0]["command"]
    result = subprocess.run([binary, "-c", command], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["hookSpecificOutput"]["hookEventName"] == HOOK_EVENT
    assert MARKER not in result.stdout


# -- recognising our own entry -------------------------------------------


@pytest.mark.parametrize("version", [1, 2, 17])
def test_is_ours_matches_across_versions(version):
    """The version is informational; a matcher including it grows duplicates."""
    assert is_ours(marked("x", version=version))


@pytest.mark.parametrize(
    "entry",
    [
        FOREIGN,
        {},
        {"hooks": "not a list"},
        {"hooks": [{"type": "command"}]},
        "not an object",
        None,
    ],
)
def test_is_ours_rejects_everything_else(entry):
    assert not is_ours(entry)


# -- installing ----------------------------------------------------------


def test_creates_the_file_in_an_empty_project(tmp_path):
    change = install(tmp_path)
    assert change.action == "created"
    assert entries(settings_path(tmp_path)) == [template_entry()]


def test_a_second_run_changes_nothing(tmp_path):
    install(tmp_path)
    before = settings_path(tmp_path).read_text()
    change = install(tmp_path)
    assert change.action == "unchanged"
    assert settings_path(tmp_path).read_text() == before


def test_replaces_our_older_entry_in_place(tmp_path):
    path = settings_path(tmp_path)
    write_json(path, {"hooks": {HOOK_EVENT: [FOREIGN, marked("old text")]}})

    change = install(tmp_path)

    assert change.action == "updated"
    assert change.previous == marked("old text")
    # Position matters: somebody may have ordered these deliberately.
    assert entries(path) == [FOREIGN, template_entry()]


def test_removes_duplicates_left_by_a_run_that_could_not_identify_them(tmp_path):
    path = settings_path(tmp_path)
    write_json(path, {"hooks": {HOOK_EVENT: [marked("a"), FOREIGN, marked("b"), marked("c")]}})

    change = install(tmp_path)

    assert change.duplicates == 2
    assert entries(path) == [template_entry(), FOREIGN]
    assert "removed 2 duplicate entries" in change.describe()


def test_leaves_the_rest_of_the_settings_alone(tmp_path):
    path = settings_path(tmp_path)
    original = {
        "model": "opus",
        "permissions": {"allow": ["Bash(git *)"]},
        "hooks": {
            HOOK_EVENT: [FOREIGN],
            "PostToolUse": [{"hooks": [{"type": "command", "command": "echo untouched"}]}],
        },
    }
    write_json(path, original)

    install(tmp_path)
    after = read_json(path)

    assert after["model"] == original["model"]
    assert after["permissions"] == original["permissions"]
    assert after["hooks"]["PostToolUse"] == original["hooks"]["PostToolUse"]
    assert after["hooks"][HOOK_EVENT] == [FOREIGN, template_entry()]


# -- refusing rather than damaging ---------------------------------------


def test_refuses_a_settings_file_that_does_not_parse(tmp_path):
    path = settings_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(ConfigError):
        install(tmp_path)
    assert path.read_text(encoding="utf-8") == "{not json", "the file must be left alone"


@pytest.mark.parametrize(
    "settings",
    [
        {"hooks": "not an object"},
        {"hooks": {HOOK_EVENT: "not a list"}},
    ],
)
def test_refuses_settings_shaped_wrongly(tmp_path, settings):
    path = settings_path(tmp_path)
    write_json(path, settings)
    before = path.read_text(encoding="utf-8")

    with pytest.raises(InstallError):
        install(tmp_path)
    assert path.read_text(encoding="utf-8") == before


def test_a_broken_template_is_refused_rather_than_installed(tmp_path, monkeypatch):
    """A template without the marker would install an entry no run can find again."""
    broken = tmp_path / "broken.json"
    write_json(broken, {"hooks": {HOOK_EVENT: [FOREIGN]}})
    monkeypatch.setattr("rage.install.TEMPLATE", broken)

    with pytest.raises(InstallError, match="marker"):
        template_entry()


# -- previewing ----------------------------------------------------------


def test_dry_run_writes_nothing_and_reports_the_same_action(tmp_path):
    change = install(tmp_path, dry_run=True)
    assert change.action == "created"
    assert not settings_path(tmp_path).exists()
    assert install(tmp_path).action == "created", "the real run agrees with the preview"


def test_plan_does_not_touch_the_file(tmp_path):
    path = settings_path(tmp_path)
    write_json(path, {"hooks": {HOOK_EVENT: [FOREIGN]}})
    before = path.read_text(encoding="utf-8")

    plan(path)

    assert path.read_text(encoding="utf-8") == before


# -- keeping the file as it was found ------------------------------------


def test_existing_indentation_is_kept(tmp_path):
    path = settings_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"model": "opus"}, indent=4) + "\n", encoding="utf-8")

    install(tmp_path)

    assert '\n    "model"' in path.read_text(encoding="utf-8")


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions")
def test_existing_permissions_are_kept(tmp_path):
    path = settings_path(tmp_path)
    write_json(path, {"model": "opus"})
    os.chmod(path, 0o640)

    install(tmp_path)

    assert path.stat().st_mode & 0o777 == 0o640
