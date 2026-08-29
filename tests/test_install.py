"""Tests for installing the hook into a project's settings.

Two risks, and almost everything below guards one of them. The first is damage
to a file outrage does not own: the settings hold the user's model, permissions
and their own hooks, and losing any of those to an installer is far worse than
the installer refusing to run. The second is the marker failing to identify our
own entry, which does not look like a failure at all - it looks like a hook
that quietly becomes two, then three.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from conftest import raises_rendered
from outrage.config import ConfigError
from outrage.install import (
    CLAUDE_DIR,
    CLAUDE_HOOK,
    CODEX_DIR,
    COPILOT_HOOK,
    HOOK_TARGETS,
    MARKER,
    FileChange,
    InstallError,
    asset_sources,
    codex_asset_sources,
    init,
    install,
    is_ours,
    plan,
    plan_assets,
    plan_codex_assets,
    settings_path,
    template_entry,
)

# Almost everything here is about the Claude Code hook, which was the only one
# until Copilot CLI arrived. Named locally so those tests read as they did.
HOOK_EVENT = CLAUDE_HOOK.event
TEMPLATE = CLAUDE_HOOK.template


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


def marked_by_a_former_name(text: str, name: str, version: int = 2) -> dict:
    """An entry as a release under a *different* product name would have written it.

    ``rage`` is the one that actually shipped: 0.1.1 wrote it, and the rename is
    what made recognising it a problem. The second name is there to say the
    matcher is not special-casing that one.
    """
    comment = f"{name}-managed:session-start:v{version}"
    return {"hooks": [{"type": "command", "command": f"echo {text!r}  # {comment}"}]}


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
    that exits 0 while emitting something unparseable - which looks exactly
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


@pytest.mark.parametrize("name", ["rage", "former"])
def test_replaces_an_entry_written_under_a_former_product_name(tmp_path, name):
    # The rename to `outrage` moved the marker, so an upgrade stopped
    # recognising what the previous release wrote and appended a second hook.
    path = settings_path(tmp_path)
    previous = marked_by_a_former_name("old text", name)
    write_json(path, {"hooks": {HOOK_EVENT: [FOREIGN, previous]}})

    change = install(tmp_path)

    assert change.action == "updated", "a renamed marker must not append a second hook"
    assert change.previous == previous
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


def test_a_broken_template_is_refused_rather_than_installed(tmp_path):
    """A template without the marker would install an entry no run can find again."""
    broken = tmp_path / "broken.json"
    write_json(broken, {"hooks": {HOOK_EVENT: [FOREIGN]}})

    with raises_rendered(InstallError, "marker"):
        template_entry(replace(CLAUDE_HOOK, template=broken))


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


# -- the packaged skill and agents ---------------------------------------


def actions(changes: list[FileChange]) -> set[str]:
    return {change.action for change in changes}


def installed(project: Path, relative: str) -> Path:
    return project / CLAUDE_DIR / relative


def codex_installed(project: Path, relative: str) -> Path:
    return project / CODEX_DIR / relative


def test_the_package_ships_a_skill_and_three_agents():
    """The copy is only as good as what is packaged, so check it is there."""
    relative = {str(r) for _, r in asset_sources()}

    assert "skills/outrage/SKILL.md" in relative
    assert {r for r in relative if r.startswith("agents/")} >= {
        "agents/outrage-annotate.md",
        "agents/outrage-backfill.md",
        "agents/outrage-search.md",
    }


def test_the_package_ships_a_codex_skill_with_agent_workflows():
    relative = {str(r) for _, r in codex_asset_sources()}

    assert "skills/outrage/SKILL.md" in relative
    assert {
        "skills/outrage/references/annotate.md",
        "skills/outrage/references/backfill.md",
        "skills/outrage/references/search.md",
    } <= relative


def test_an_empty_project_gets_every_packaged_file(tmp_path):
    done = init(tmp_path)
    changes = done.assets

    assert actions(changes) == {"created"}
    for change in changes:
        assert change.path.read_bytes() == change.source.read_bytes()
    assert actions(list(done.codex_assets)) == {"created"}
    for change in done.codex_assets:
        assert change.path.read_bytes() == change.source.read_bytes()


def test_a_second_run_copies_nothing(tmp_path):
    init(tmp_path)
    skill = installed(tmp_path, "skills/outrage/SKILL.md")
    before = skill.stat().st_mtime_ns

    assert actions(init(tmp_path).assets) == {"unchanged"}
    assert skill.stat().st_mtime_ns == before, "an unchanged file is not rewritten"
    assert actions(init(tmp_path).codex_assets) == {"unchanged"}


def test_an_edited_copy_is_replaced_by_the_packaged_one(tmp_path):
    """The copy is output, not a document to keep: an upgrade has to reach it."""
    init(tmp_path)
    skill = installed(tmp_path, "skills/outrage/SKILL.md")
    skill.write_text("something older", encoding="utf-8")

    changes = init(tmp_path).assets

    updated = [c for c in changes if c.path == skill]
    assert [c.action for c in updated] == ["updated"]
    assert skill.read_bytes() == updated[0].source.read_bytes()


def test_a_symlinked_file_is_left_alone(tmp_path):
    """Reported rather than silently skipped, and never written through."""
    elsewhere = tmp_path / "source" / "outrage-search.md"
    elsewhere.parent.mkdir(parents=True)
    elsewhere.write_text("the linked agent", encoding="utf-8")
    link = installed(tmp_path, "agents/outrage-search.md")
    link.parent.mkdir(parents=True)
    link.symlink_to(elsewhere)

    changes = init(tmp_path).assets

    linked = [c for c in changes if c.path == link]
    assert [c.action for c in linked] == ["linked"]
    assert elsewhere.read_text(encoding="utf-8") == "the linked agent"


def test_a_symlinked_directory_is_left_alone(tmp_path):
    """This repository links .claude/skills/outrage at its own source tree."""
    elsewhere = tmp_path / "source" / "outrage"
    elsewhere.mkdir(parents=True)
    (elsewhere / "SKILL.md").write_text("the linked skill", encoding="utf-8")
    link = installed(tmp_path, "skills/outrage")
    link.parent.mkdir(parents=True)
    link.symlink_to(elsewhere, target_is_directory=True)

    changes = init(tmp_path).assets

    assert [c.action for c in changes if "skills" in str(c.path)] == ["linked"]
    assert (elsewhere / "SKILL.md").read_text(encoding="utf-8") == "the linked skill"


def test_a_symlinked_codex_skill_is_left_alone(tmp_path):
    elsewhere = tmp_path / "source" / "outrage"
    elsewhere.mkdir(parents=True)
    (elsewhere / "SKILL.md").write_text("the linked Codex skill", encoding="utf-8")
    link = codex_installed(tmp_path, "skills/outrage")
    link.parent.mkdir(parents=True)
    link.symlink_to(elsewhere, target_is_directory=True)

    changes = plan_codex_assets(tmp_path)

    assert {change.action for change in changes} == {"linked"}
    assert (elsewhere / "SKILL.md").read_text(encoding="utf-8") == "the linked Codex skill"


def test_planning_the_copy_writes_nothing(tmp_path):
    plan_assets(tmp_path)
    plan_codex_assets(tmp_path)

    assert not (tmp_path / CLAUDE_DIR).exists()
    assert not (tmp_path / CODEX_DIR).exists()


# -- setting a whole project up ------------------------------------------


def servers(path: Path) -> dict:
    return read_json(path)["mcpServers"]


def test_init_writes_the_three_things(tmp_path):
    done = init(tmp_path)

    entry = servers(tmp_path / ".mcp.json")["outrage"]
    assert Path(entry["command"]).is_absolute()
    assert entry["args"][-1] == str(tmp_path / ".outrage"), "the store defaults beside the project"
    assert is_ours(entries(settings_path(tmp_path))[-1])
    assert installed(tmp_path, "skills/outrage/SKILL.md").is_file()
    assert codex_installed(tmp_path, "skills/outrage/SKILL.md").is_file()
    assert done.writes


def test_init_records_the_store_directory_it_is_given(tmp_path):
    done = init(tmp_path, tmp_path / "elsewhere")

    assert done.server.entry["args"][-1] == str(tmp_path / "elsewhere")


def test_init_passes_logging_through_to_the_entry(tmp_path):
    """Without this, a re-run of init would switch off logging config turned on."""
    done = init(tmp_path, log=Path(tmp_path / "events.jsonl"), log_content="excerpt")

    assert "--log" in done.server.entry["args"]
    assert "excerpt" in done.server.entry["args"]


def test_init_writes_the_mounts_to_the_table_and_not_to_the_entry(tmp_path):
    """The table is a file in the store directory, and the entry carries --dir.

    Which is the payoff of the file existing: registering a server stops being
    "write the whole table into a client's JSON, correctly, from a command" and
    becomes "point at a directory".
    """
    from outrage import mountfile, mounts

    done = init(
        tmp_path,
        root_mount="main.sqlite",
        mounts=["lib=lib.sqlite"],
        read_only_mounts=["ref=reference.sqlite"],
    )

    assert done.server.entry["args"] == ["--dir", str(tmp_path / ".outrage")]
    written = mountfile.read(tmp_path / ".outrage" / mountfile.DEFAULT_NAME)
    assert written.root == mounts.Spec(Path("main.sqlite"))
    assert written.mounts == (("lib", mounts.Spec(Path("lib.sqlite"))),)
    assert written.read_only == (("ref", mounts.Spec(Path("reference.sqlite"))),)


def test_init_never_rewrites_a_table_that_is_already_there(tmp_path):
    """A file whose reason for existing is comments is written once.

    So a second init naming a different mount reports the lines to add rather
    than writing them under somebody's comments.
    """
    from outrage import mountfile

    init(tmp_path, mounts=["lib=lib.sqlite"])
    table = tmp_path / ".outrage" / mountfile.DEFAULT_NAME
    before = table.read_text()

    done = init(tmp_path, mounts=["other=other.sqlite"])

    assert table.read_text() == before
    assert not done.table.writes
    assert 'other = "other.sqlite"' in done.table.missing


def test_a_second_init_changes_nothing_anywhere(tmp_path):
    init(tmp_path)

    done = init(tmp_path)

    assert not done.writes
    assert done.server.action == "unchanged"
    assert [h.action for h in done.hooks] == ["unchanged"] * len(HOOK_TARGETS)
    assert actions(list(done.assets)) == {"unchanged"}
    assert actions(list(done.codex_assets)) == {"unchanged"}


def test_init_dry_run_writes_nothing_and_agrees_with_the_real_run(tmp_path):
    preview = init(tmp_path, dry_run=True)

    assert not (tmp_path / ".mcp.json").exists()
    assert not (tmp_path / CLAUDE_DIR).exists()
    assert not (tmp_path / CODEX_DIR).exists()

    done = init(tmp_path)
    assert preview.server.action == done.server.action
    assert [h.action for h in preview.hooks] == [h.action for h in done.hooks]
    assert actions(list(preview.assets)) == actions(list(done.assets))


def test_a_refusal_stops_the_whole_run(tmp_path):
    """Planned before written, so a project is never left half arranged."""
    path = settings_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(ConfigError):
        init(tmp_path)

    assert not (tmp_path / ".mcp.json").exists(), "the server entry was not written either"
    assert not installed(tmp_path, "skills/outrage/SKILL.md").exists()
    assert not codex_installed(tmp_path, "skills/outrage/SKILL.md").exists()


# -- the second harness: Copilot CLI -------------------------------------
#
# Copilot CLI reads most of what this project already writes, so the hook was
# the only piece missing. It is a different shape in every way that matters:
# its own file rather than a merge into the user's, `sessionStart` rather than
# `SessionStart`, a `version` stamp the file is ignored without, and the
# command carried twice for the two shells.


def copilot_path(project: Path) -> Path:
    return COPILOT_HOOK.path(project)


def copilot_entries(path: Path) -> list:
    return read_json(path)["hooks"][COPILOT_HOOK.event]


def test_the_copilot_template_ships_and_carries_the_marker():
    assert COPILOT_HOOK.template.is_file(), "the template must travel with the package"
    assert is_ours(template_entry(COPILOT_HOOK))


def test_the_copilot_template_is_a_whole_file_with_its_version_stamp():
    loaded = json.loads(COPILOT_HOOK.template.read_text(encoding="utf-8"))
    # Unlike the Claude fragment this is a complete file, so it carries the
    # version: without it Copilot CLI does not read the hooks at all.
    assert loaded["version"] == 1
    assert len(loaded["hooks"][COPILOT_HOOK.event]) == 1


def test_the_copilot_entry_carries_both_shells():
    entry = template_entry(COPILOT_HOOK)
    assert entry["type"] == "command"
    # Both, because the docs ask for both and a Windows session would otherwise
    # get no context at all. The powershell form is unverified - no PowerShell
    # on the machine this was written on.
    assert entry["bash"].startswith("echo '")
    assert entry["powershell"].startswith("Write-Output '")


def test_the_copilot_marker_is_a_field_and_not_a_shell_comment():
    """The one place outrage puts its marker in JSON rather than in the command.

    A live Copilot session delivered the context from an entry shaped this way.
    None has been seen to deliver it from one carrying a trailing `# marker`,
    so until that is pinned down the shipped shape is the watched one. Keeping
    the command free of the comment is the point, so this asserts it.
    """
    entry = template_entry(COPILOT_HOOK)

    assert re.fullmatch(rf"{re.escape(MARKER)}:v\d+", entry["comment"])
    assert MARKER not in entry["bash"]
    assert MARKER not in entry["powershell"]


@pytest.mark.skipif(os.name != "posix", reason="the marker is a POSIX shell comment")
@pytest.mark.parametrize("shell", ["sh", "bash", "zsh"])
def test_the_copilot_command_emits_the_context_and_hides_the_marker(shell):
    """Same premise as the Claude one, and the same failure if it is wrong.

    Copilot's payload is flatter - `additionalContext` at the top level rather
    than under `hookSpecificOutput` - so this is not the same assertion twice.
    """
    binary = shutil.which(shell)
    if binary is None:
        pytest.skip(f"{shell} is not installed")
    result = subprocess.run(
        [binary, "-c", template_entry(COPILOT_HOOK)["bash"]], capture_output=True, text=True
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "outrage document store" in payload["additionalContext"]
    assert "readme" in payload["additionalContext"]
    assert MARKER not in result.stdout


def test_both_harnesses_deliver_the_same_sentence():
    """One store, one instruction. Two wordings would drift, and silently."""
    claude = json.loads(
        subprocess.run(
            ["sh", "-c", template_entry()["hooks"][0]["command"]],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    copilot = json.loads(
        subprocess.run(
            ["sh", "-c", template_entry(COPILOT_HOOK)["bash"]],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    assert copilot["additionalContext"] == claude["hookSpecificOutput"]["additionalContext"]


def test_init_writes_the_copilot_hook_with_its_version(tmp_path):
    init(tmp_path)
    written = read_json(copilot_path(tmp_path))

    assert written["version"] == 1
    assert written["hooks"][COPILOT_HOOK.event] == [template_entry(COPILOT_HOOK)]


def test_a_second_run_leaves_the_copilot_file_alone(tmp_path):
    install(tmp_path, target=COPILOT_HOOK)
    before = copilot_path(tmp_path).read_text()

    change = install(tmp_path, target=COPILOT_HOOK)

    assert change.action == "unchanged"
    assert copilot_path(tmp_path).read_text() == before


def test_the_copilot_file_is_merged_not_claimed(tmp_path):
    """The file is named for outrage, but that is not a reason to own it.

    Somebody may put their own sessionStart hook beside ours, or another event
    in the same file. Both survive, the same way the Claude settings do.
    """
    path = copilot_path(tmp_path)
    theirs = {"type": "command", "bash": "echo 'mine'"}
    write_json(
        path,
        {
            "version": 1,
            "hooks": {COPILOT_HOOK.event: [theirs], "preToolUse": [{"type": "command"}]},
        },
    )

    install(tmp_path, target=COPILOT_HOOK)
    after = read_json(path)

    assert after["hooks"][COPILOT_HOOK.event] == [theirs, template_entry(COPILOT_HOOK)]
    assert after["hooks"]["preToolUse"] == [{"type": "command"}]
    assert after["version"] == 1


def test_an_existing_copilot_file_keeps_its_own_version(tmp_path):
    """`base` fills a file in, it does not correct one. A version outrage does
    not understand is the user's business, and overwriting it would be the one
    place this installer damaged what it found."""
    path = copilot_path(tmp_path)
    write_json(path, {"version": 2, "hooks": {}})

    install(tmp_path, target=COPILOT_HOOK)

    assert read_json(path)["version"] == 2


def test_is_ours_recognises_a_copilot_entry_and_not_a_neighbour():
    assert is_ours(template_entry(COPILOT_HOOK))
    assert not is_ours({"type": "command", "bash": "echo 'mine'"})


def test_init_reports_one_change_per_harness(tmp_path):
    done = init(tmp_path, dry_run=True)

    assert [h.target for h in done.hooks] == list(HOOK_TARGETS)
    assert [h.path for h in done.hooks] == [t.path(done.project_dir) for t in HOOK_TARGETS]
