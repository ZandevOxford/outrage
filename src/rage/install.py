"""Setting a project up: the MCP entry, the hook, and the skill and agents.

``init`` is the whole of ``rage init`` and the three parts are separable: the
server entry is :mod:`rage.config`'s and is called rather than repeated, the
hook is written into ``.claude/settings.json`` here, and the packaged skill and
agents are copied into ``.claude/``. Most of what follows is about the hook,
because it is the part with something to say.

The settings file belongs to the user, not to rage. It holds their model, their
permissions and their own hooks, so this writes the one entry it owns and
leaves everything else exactly as it found it — the rule :mod:`rage.config`
already follows for ``.mcp.json``, and the reason its ``read_config`` and
``write_config`` are reused here rather than reimplemented.

## Why the marker exists

``mcpServers`` is an object, so :mod:`rage.config` can key on a name and
replace one entry. ``hooks.SessionStart`` is a **list**, and nothing in it says
who wrote what. An installer that cannot recognise its own entry has only bad
options: append every run and accumulate duplicates, or replace the lot and
destroy hooks it did not write.

So the command carries a marker as a trailing shell comment::

    echo '{"hookSpecificOutput": …}'  # rage-managed:session-start:v1

Verified to produce identical output under ``sh``, ``bash`` and ``zsh``, with
the marker absent from stdout in all three.

An unknown JSON key on the entry — ``{"_rageManaged": …}`` — was tested and
works: the client tolerates it and the hook still fires. It was rejected
anyway. It depends on that tolerance continuing, which is undocumented, and if
it ever stops the hook is rejected and delivers nothing *silently*. A shell
comment depends only on POSIX shell semantics and cannot break a hook that runs
at all. Both client behaviours this project has been burnt by were undocumented
ones; see ``project/reference/harness-delivery`` in the store.

**Match on the prefix, never the whole marker.** ``:vN`` is informational. A
matcher that includes the version stops recognising the entry it exists to
replace the moment the version changes, which is how one hook becomes two.

## The bridge this is

The marker is needed because the command is an inlined ``echo`` whose text
changes between releases. If the hook ever becomes ``<abs>/bin/rage hook
session-start``, the command is stable and is its own marker — no comment, no
version, and it works on Windows, where ``#`` does not begin a comment. Expect
to retire this.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import config
from .config import ConfigError, read_config, write_config

#: The hook event rage installs into. One today; the marker names which hook an
#: entry is, so a second one would not be ambiguous.
HOOK_EVENT = "SessionStart"

#: What identifies an entry as ours, and what a matcher compares against. The
#: version that follows it in the file is deliberately *not* part of this.
MARKER = "rage-managed:session-start"

#: The settings fragment that ships with the package. A fragment rather than a
#: file to copy over: only the key below ``hooks`` is ours.
TEMPLATE = Path(__file__).parent / "hooks" / "settings.json"

#: Where a project's skills, agents and settings live, relative to its root.
#: Declared above its three users rather than beside the assets, because the
#: settings path is one of them and used to spell the directory out.
CLAUDE_DIR = ".claude"

#: The settings file the fragment is merged into, inside :data:`CLAUDE_DIR`.
SETTINGS_NAME = "settings.json"

#: The key below which that merge happens. Everything else in the file is
#: somebody else's and is written back as it was found.
HOOKS_FIELD = "hooks"


class InstallError(ConfigError):
    """Settings that cannot safely be updated."""


@dataclass(frozen=True, slots=True)
class HookChange:
    """What installing the hook would do, or did."""

    path: Path
    action: str
    """'created', 'updated' or 'unchanged'."""
    entry: dict[str, Any]
    previous: dict[str, Any] | None
    """The entry being replaced, when there was one."""
    duplicates: int = 0
    """Extra entries of ours removed, from a run that could not identify them."""

    @property
    def writes(self) -> bool:
        return self.action != "unchanged"

    def describe(self) -> str:
        line = f"{self.path}: {self.action}"
        if self.duplicates:
            line += f", removed {self.duplicates} duplicate entr"
            line += "y" if self.duplicates == 1 else "ies"
        return line


def settings_path(project_dir: str | Path) -> Path:
    """Where a project's settings file is, whether or not it exists yet."""
    return Path(project_dir) / CLAUDE_DIR / SETTINGS_NAME


def template_entry() -> dict[str, Any]:
    """The entry to install, read from the packaged template.

    The template holds the marker rather than this module appending it, so the
    command that ships is the command that is installed, character for
    character. A template whose marker were added in code could be edited into
    something the matcher no longer recognises without anything noticing.
    """
    try:
        loaded = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:  # pragma: no cover - a broken install
        raise InstallError("template-missing", path=str(TEMPLATE)) from exc
    except json.JSONDecodeError as exc:  # pragma: no cover - a broken install
        raise InstallError("template-not-json", path=str(TEMPLATE)) from exc

    entries = loaded.get(HOOKS_FIELD, {}).get(HOOK_EVENT)
    if not isinstance(entries, list) or len(entries) != 1:
        raise InstallError("template-hook-count", event=HOOK_EVENT)
    entry = entries[0]
    if not is_ours(entry):
        raise InstallError("template-unmarked", marker=MARKER)
    return entry


def is_ours(entry: Any) -> bool:
    """Whether this ``SessionStart`` entry is one rage wrote.

    Prefix match. See the module docstring on why the version is excluded.
    """
    if not isinstance(entry, dict):
        return False
    hooks = entry.get("hooks")
    if not isinstance(hooks, list):
        return False
    return any(isinstance(h, dict) and MARKER in str(h.get("command", "")) for h in hooks)


def plan(
    path: Path, entry: dict[str, Any] | None = None
) -> tuple[HookChange, dict[str, Any], str | None]:
    """Work out what installing would change, without writing.

    Returns the change, the merged settings and the file's original text, so a
    caller can preview and then write without reading twice — and so a dry run
    goes through this same function rather than a second one that could
    disagree with it.
    """
    entry = template_entry() if entry is None else entry
    settings, original = read_config(path)

    hooks = settings.get(HOOKS_FIELD, {})
    if not isinstance(hooks, dict):
        raise InstallError("config-field-not-an-object", path=str(path), field=HOOKS_FIELD)

    existing = hooks.get(HOOK_EVENT, [])
    if not isinstance(existing, list):
        raise InstallError("config-field-not-a-list", path=str(path), field=HOOK_EVENT)

    ours = [i for i, e in enumerate(existing) if is_ours(e)]
    previous = existing[ours[0]] if ours else None

    if not ours:
        merged_entries = [*existing, entry]
        action = "created"
    else:
        # Keep our entry where the user has it. Moving it to the end would
        # reorder hooks somebody arranged deliberately.
        merged_entries = [e for i, e in enumerate(existing) if i not in set(ours[1:])]
        merged_entries[ours[0]] = entry
        action = "unchanged" if previous == entry and len(ours) == 1 else "updated"

    merged = dict(settings)
    merged[HOOKS_FIELD] = dict(hooks) | {HOOK_EVENT: merged_entries}

    change = HookChange(
        path=path,
        action=action,
        entry=entry,
        previous=previous,
        duplicates=max(len(ours) - 1, 0),
    )
    return change, merged, original


def install(project_dir: str | Path, dry_run: bool = False) -> HookChange:
    """Install the packaged hook into a project, or say what would change.

    The dry run calls the same ``plan`` the real run does, so it cannot preview
    something different from what a write would produce.
    """
    path = settings_path(project_dir)
    change, merged, original = plan(path)
    if not dry_run and change.writes:
        write_config(path, merged, original)
    return change


# -- the packaged skill and agents ---------------------------------------


#: Packaged directories that install into ``.claude/``, copied whole. Markdown
#: a client reads directly: nothing here is executed, so nothing here needs an
#: interpreter or an absolute path, and a copy of it is complete on its own.
ASSET_DIRS = ("skills", "agents")

@dataclass(frozen=True, slots=True)
class FileChange:
    """What installing one packaged file would do, or did."""

    path: Path
    source: Path
    action: str
    """'created', 'updated', 'unchanged' or 'linked'."""

    @property
    def writes(self) -> bool:
        return self.action in ("created", "updated")

    def describe(self) -> str:
        return f"{self.path}: {self.action}"


def asset_sources() -> list[tuple[Path, Path]]:
    """Every packaged file to install, as a source and a path below ``.claude``."""
    found: list[tuple[Path, Path]] = []
    for name in ASSET_DIRS:
        root = Path(__file__).parent / name
        if not root.is_dir():  # pragma: no cover - a broken install
            raise InstallError("assets-missing", asset=name, path=str(root))
        for source in sorted(root.rglob("*")):
            if source.is_file() and not source.name.startswith("."):
                found.append((source, Path(name) / source.relative_to(root)))
    if not found:  # pragma: no cover - a broken install
        raise InstallError(
            "assets-empty", asset=CLAUDE_DIR, path=str(Path(__file__).parent)
        )
    return found


def plan_assets(project_dir: str | Path) -> list[FileChange]:
    """Work out which packaged files a project is missing or has an older copy of."""
    root = Path(project_dir) / CLAUDE_DIR
    changes = []
    for source, relative in asset_sources():
        path = root / relative
        if _through_a_link(root, relative):
            action = "linked"
        elif not path.exists():
            action = "created"
        elif path.read_bytes() == source.read_bytes():
            action = "unchanged"
        else:
            action = "updated"
        changes.append(FileChange(path=path, source=source, action=action))
    return changes


def write_assets(changes: list[FileChange]) -> None:
    """Copy across the files that differ, atomically and one at a time."""
    for change in changes:
        if not change.writes:
            continue
        change.path.parent.mkdir(parents=True, exist_ok=True)
        _replace(change.path, change.source.read_bytes())


def _through_a_link(root: Path, relative: Path) -> bool:
    """Whether anything on the way down to ``relative`` is a symlink.

    A destination reached through a link is reported and left alone. This
    repository points ``.claude/skills/rage`` at its own source tree
    deliberately, so that an edit to the skill is live without reinstalling;
    writing through such a link would edit the package rather than the project.
    Copy is right for an installed project and symlink is right for this one,
    and an installer that cannot tell them apart has to be wrong in one of them.
    """
    walked = root
    for part in relative.parts:
        walked = walked / part
        if walked.is_symlink():
            return True
    return False


def _replace(path: Path, content: bytes) -> None:
    """Write ``content`` to ``path`` through a temporary file, as config.py does.

    Same reason: an interrupted write must not leave a truncated file behind,
    and an existing file's permissions are the user's rather than mkstemp's.
    """
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
        os.chmod(temporary, _mode_for(path))
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _mode_for(path: Path) -> int:
    """Keep an existing file's permissions; a new one is readable like a checkout."""
    try:
        return path.stat().st_mode & 0o7777
    except FileNotFoundError:
        return 0o644


# -- setting a whole project up ------------------------------------------


@dataclass(frozen=True, slots=True)
class Installation:
    """Everything ``rage init`` does to a project, or would do."""

    project_dir: Path
    server: config.Change
    hook: HookChange
    assets: tuple[FileChange, ...]

    @property
    def writes(self) -> bool:
        return self.server.writes or self.hook.writes or any(a.writes for a in self.assets)


def init(
    project_dir: str | Path,
    directory: str | Path | None = None,
    *,
    log: Any = None,
    log_content: str | None = None,
    root_mount: str | None = None,
    mounts: Sequence[str] = (),
    read_only_mounts: Sequence[str] = (),
    dry_run: bool = False,
) -> Installation:
    """Set a project up: the MCP server entry, the hook, and the skill and agents.

    The whole of it is planned before any of it is written, so a refusal — a
    settings file that does not parse, a ``.mcp.json`` that does not — stops
    the run rather than leaving a project half arranged. The dry run stops
    after the same planning the real run does, so it cannot preview something a
    write would disagree with.

    ``rage config`` writes the server entry alone and this calls it rather than
    repeating it, which is also why ``log``, ``log_content``, ``root_mount``
    and the two mount lists are passed through: without them a re-run of
    ``init`` would quietly switch off logging somebody had turned on, or drop
    the mounts they had configured.
    """
    project = Path(project_dir).expanduser().resolve()

    assets = plan_assets(project)

    hook_path = settings_path(project)
    hook, settings, settings_text = plan(hook_path)

    server_path = config.config_path("project", project)
    entry = config.server_entry(
        directory if directory is not None else config.default_store_dir(project),
        log=log,
        log_content=log_content,
        root_mount=root_mount,
        mounts=mounts,
        read_only_mounts=read_only_mounts,
    )
    server, servers, servers_text = config.plan(server_path, "project", entry)

    if not dry_run:
        if server.writes:
            config.write_config(server_path, servers, servers_text)
        if hook.writes:
            config.write_config(hook_path, settings, settings_text)
        write_assets(assets)

    return Installation(project_dir=project, server=server, hook=hook, assets=tuple(assets))


__all__ = [
    "ASSET_DIRS",
    "CLAUDE_DIR",
    "HOOKS_FIELD",
    "HOOK_EVENT",
    "MARKER",
    "SETTINGS_NAME",
    "TEMPLATE",
    "FileChange",
    "HookChange",
    "InstallError",
    "Installation",
    "asset_sources",
    "init",
    "install",
    "is_ours",
    "plan",
    "plan_assets",
    "settings_path",
    "template_entry",
    "write_assets",
]
