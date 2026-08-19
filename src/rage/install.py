"""Installing rage's hooks into a project's ``.claude/settings.json``.

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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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

SETTINGS_NAME = "settings.json"

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

    def describe(self) -> str:
        line = f"{self.path}: {self.action}"
        if self.duplicates:
            line += f", removed {self.duplicates} duplicate entr"
            line += "y" if self.duplicates == 1 else "ies"
        return line


def settings_path(project_dir: str | Path) -> Path:
    return Path(project_dir) / ".claude" / SETTINGS_NAME


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
        raise InstallError(f"packaged template missing at {TEMPLATE}") from exc
    except json.JSONDecodeError as exc:  # pragma: no cover - a broken install
        raise InstallError(f"packaged template at {TEMPLATE} is not valid JSON") from exc

    entries = loaded.get(HOOKS_FIELD, {}).get(HOOK_EVENT)
    if not isinstance(entries, list) or len(entries) != 1:
        raise InstallError(f"packaged template must hold exactly one {HOOK_EVENT} entry")
    entry = entries[0]
    if not is_ours(entry):
        raise InstallError(f"packaged template's command does not carry the {MARKER!r} marker")
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
        raise InstallError(f"{path} has a {HOOKS_FIELD!r} that is not an object; leaving it alone")

    existing = hooks.get(HOOK_EVENT, [])
    if not isinstance(existing, list):
        raise InstallError(f"{path} has a {HOOK_EVENT!r} that is not a list; leaving it alone")

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
    if not dry_run and change.action != "unchanged":
        write_config(path, merged, original)
    return change


__all__ = [
    "HOOK_EVENT",
    "HOOKS_FIELD",
    "MARKER",
    "TEMPLATE",
    "HookChange",
    "InstallError",
    "install",
    "is_ours",
    "plan",
    "settings_path",
    "template_entry",
]
