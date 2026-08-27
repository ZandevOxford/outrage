"""Setting a project up: the MCP entry, hooks, and harness-specific skills.

``init`` is the whole of ``outrage init`` and the three parts are separable: the
server entry is :mod:`outrage.config`'s and is called rather than repeated, the
session-start hooks are written here, and packaged assets are copied into the
directories their harness reads. Most of what follows is about the hooks,
because they are the part with something to say.

A config file belongs to the user, not to outrage. It holds their model, their
permissions and their own hooks, so this writes the one entry it owns and
leaves everything else exactly as it found it - the rule :mod:`outrage.config`
already follows for ``.mcp.json``, and the reason its ``read_config`` and
``write_config`` are reused here rather than reimplemented.

## Two harnesses, one hook each

:data:`HOOK_TARGETS` is the list, and everything below takes one of them rather
than assuming Claude Code. Adding the second one is what turned the constants
into a :class:`HookTarget`; ``project/reference/harness-portability`` said not
to generalise before there was something real to generalise *to*, and Copilot
CLI is it.

They differ in more than spelling:

* **Claude Code** merges into ``.claude/settings.json``, a file the user owns
  outright and which this project does not commit.
* **Copilot CLI** takes a file per purpose under ``.github/hooks/``, so
  ``.github/hooks/outrage.json`` is outrage's own - but ``.github`` is usually
  **committed**, so a re-run's diff lands in somebody's version control where
  the Claude one does not.
* Copilot's entry carries the command twice, as ``bash`` and ``powershell``,
  and the file needs ``"version": 1`` at its top. Hence
  :attr:`HookTarget.base`: what to start from when the file does not exist.

Both are written by default. A project that uses one harness carries a small
inert file for the other, which is cheaper than an installer that has to be
told what the user is running.

## Why the marker exists

``mcpServers`` is an object, so :mod:`outrage.config` can key on a name and
replace one entry. ``hooks.SessionStart`` is a **list**, and nothing in it says
who wrote what. An installer that cannot recognise its own entry has only bad
options: append every run and accumulate duplicates, or replace the lot and
destroy hooks it did not write.

So the command carries a marker as a trailing shell comment::

    echo '{"hookSpecificOutput": …}'  # outrage-managed:session-start:v1

Verified to produce identical output under ``sh``, ``bash`` and ``zsh``, with
the marker absent from stdout in all three.

**Copilot CLI carries the same marker in a ``comment`` field instead**, which
reverses the argument below for that harness alone. The reason is evidence: a
live session was seen to deliver the context from an entry shaped that way,
and no session has yet been seen to deliver it from one carrying a trailing
shell comment. Which of the two that difference belongs to is *not* settled -
the failing runs were all non-interactive, and no sessionStart hook fired in
any of them - so this ships the shape that was watched working and leaves the
question in the store rather than guessing at it. :func:`is_ours` looks for the
marker anywhere in the entry, so both forms are recognised and a later
correction moves it without a migration.

An unknown JSON key on the entry - ``{"_outrageManaged": …}`` - was tested and
works: the client tolerates it and the hook still fires. It was rejected
anyway. It depends on that tolerance continuing, which is undocumented, and if
it ever stops the hook is rejected and delivers nothing *silently*. A shell
comment depends only on POSIX shell semantics and cannot break a hook that runs
at all. Both client behaviours this project has been burnt by were undocumented
ones; see ``project/reference/harness-delivery`` in the store.

**Match on the stable part, never the whole marker.** ``:vN`` is
informational, and so is the product name in front of it. A matcher that
includes either stops recognising the entry it exists to replace the moment
that part changes, which is how one hook becomes two.

That is not hypothetical: the rename to ``outrage`` moved the name, an upgrade
stopped recognising what the previous release had written, and ``init``
appended a second session-start hook instead of replacing the first. So
:data:`MARKER` is what gets *written* and :data:`MARKER_MATCH` is what gets
*compared*, and the second is the part a rename does not touch. The cost is a
slightly wider namespace claim - any entry carrying ``-managed:session-start``
is treated as ours - which is the same bet the previous matcher already made
one word further along.

## The bridge this is

The marker is needed because the command is an inlined ``echo`` whose text
changes between releases. If the hook ever becomes ``<abs>/bin/outrage hook
session-start``, the command is stable and is its own marker - no comment, no
version, and it works on Windows, where ``#`` does not begin a comment. Expect
to retire this.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config, mountfile
from .config import ConfigError, read_config, write_config

#: What gets written into the entry, minus the ``:vN`` the template adds. One
#: marker for both harnesses: it names the hook, not the client.
MARKER = "outrage-managed:session-start"

#: What a matcher compares against: :data:`MARKER` without the product name, so
#: that an entry written under a former name is still recognised as ours and
#: replaced rather than duplicated. See the module docstring.
MARKER_MATCH = "-managed:session-start"

#: Where a project's skills, agents and settings live, relative to its root.
#: Declared above its three users rather than beside the assets, because the
#: settings path is one of them and used to spell the directory out.
CLAUDE_DIR = ".claude"

#: Where Codex reads project-scoped skills, relative to the project root.
CODEX_DIR = ".codex"

#: The settings file the fragment is merged into, inside :data:`CLAUDE_DIR`.
SETTINGS_NAME = "settings.json"

#: The key below which that merge happens. Everything else in the file is
#: somebody else's and is written back as it was found.
HOOKS_FIELD = "hooks"

#: Where the packaged fragments live.
_TEMPLATES = Path(__file__).parent / "hooks"


class InstallError(ConfigError):
    """Settings that cannot safely be updated."""


@dataclass(frozen=True, slots=True)
class HookTarget:
    """One harness's session-start hook: where it goes and what shape it is.

    Everything harness-specific about the hook is one of these fields, so
    supporting a third client is a fourth instance rather than a branch in the
    code below. What is *not* here is deliberate: the merge rule, the marker
    and the refusal to touch what it did not write are the same everywhere.
    """

    name: str
    """What ``outrage init`` calls this in its output."""

    template: Path
    """The packaged fragment, holding the entry exactly as it is installed."""

    relative: Path
    """Where the file goes, relative to the project root."""

    event: str
    """The key below ``hooks`` this harness fires at session start."""

    base: dict[str, Any] = field(default_factory=dict)
    """What a newly created file starts from, before the entry is merged in.

    Empty for Claude Code. Copilot CLI requires ``{"version": 1}``, and a file
    without it is not read - which is the sort of thing that fails by the hook
    simply never firing, so it is carried here rather than assumed.
    """

    def path(self, project_dir: str | Path) -> Path:
        """Where this hook's file is in a project, whether or not it exists yet."""
        return Path(project_dir) / self.relative


#: Claude Code: merged into the user's own settings file.
CLAUDE_HOOK = HookTarget(
    name="Claude Code",
    template=_TEMPLATES / SETTINGS_NAME,
    relative=Path(CLAUDE_DIR) / SETTINGS_NAME,
    event="SessionStart",
)

#: Copilot CLI: a file per purpose, so this one is outrage's own. Named for the
#: package rather than the event, so a second outrage hook joins it here rather
#: than claiming a second file.
COPILOT_HOOK = HookTarget(
    name="Copilot CLI",
    template=_TEMPLATES / "copilot.json",
    relative=Path(".github") / "hooks" / "outrage.json",
    event="sessionStart",
    base={"version": 1},
)

#: Every hook ``outrage init`` writes, in the order it reports them.
HOOK_TARGETS = (CLAUDE_HOOK, COPILOT_HOOK)

# There is deliberately no module-level HOOK_EVENT or TEMPLATE any more. They
# were the Claude Code target's event and template, and once a second target
# existed an alias that nothing read was a trap: editing it, or patching it in
# a test, would change nothing at all. `CLAUDE_HOOK.event` says which one it
# means, which is the thing that used to be implicit.


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

    target: HookTarget = CLAUDE_HOOK
    """Which harness's hook this is, so a report over several can name them."""

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
    """Where a project's Claude Code settings file is, existing or not."""
    return CLAUDE_HOOK.path(project_dir)


def template_entry(target: HookTarget = CLAUDE_HOOK) -> dict[str, Any]:
    """The entry to install, read from the packaged template.

    The template holds the marker rather than this module appending it, so the
    command that ships is the command that is installed, character for
    character. A template whose marker were added in code could be edited into
    something the matcher no longer recognises without anything noticing.
    """
    try:
        loaded = json.loads(target.template.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:  # pragma: no cover - a broken install
        raise InstallError("template-missing", path=str(target.template)) from exc
    except json.JSONDecodeError as exc:  # pragma: no cover - a broken install
        raise InstallError("template-not-json", path=str(target.template)) from exc

    entries = loaded.get(HOOKS_FIELD, {}).get(target.event)
    if not isinstance(entries, list) or len(entries) != 1:
        raise InstallError("template-hook-count", event=target.event)
    entry = entries[0]
    if not is_ours(entry):
        raise InstallError("template-unmarked", marker=MARKER)
    return entry


def is_ours(entry: Any) -> bool:
    """Whether this session-start entry is one outrage wrote.

    The marker anywhere in the entry, because the two harnesses put the command
    in different places - ``hooks[].command`` for Claude Code, ``bash`` and
    ``powershell`` for Copilot CLI - and a matcher that knows both shapes has
    to be taught a third. Nothing but our own entry carries a string in this
    namespace.

    Compares :data:`MARKER_MATCH`, not :data:`MARKER`. See the module docstring
    on why neither the version nor the product name is part of it.
    """
    if not isinstance(entry, dict):
        return False
    return MARKER_MATCH in json.dumps(entry)


def plan(
    path: Path,
    entry: dict[str, Any] | None = None,
    *,
    target: HookTarget = CLAUDE_HOOK,
) -> tuple[HookChange, dict[str, Any], str | None]:
    """Work out what installing would change, without writing.

    Returns the change, the merged settings and the file's original text, so a
    caller can preview and then write without reading twice - and so a dry run
    goes through this same function rather than a second one that could
    disagree with it.
    """
    entry = template_entry(target) if entry is None else entry
    settings, original = read_config(path)

    if not settings:
        # A file that is not there yet starts from whatever the harness
        # requires, which for Copilot CLI is the version stamp. Merged under
        # the read so that an existing file's own top-level keys win: this is
        # the one place outrage would otherwise overwrite something it did not
        # write.
        settings = dict(target.base)

    hooks = settings.get(HOOKS_FIELD, {})
    if not isinstance(hooks, dict):
        raise InstallError("config-field-not-an-object", path=str(path), field=HOOKS_FIELD)

    existing = hooks.get(target.event, [])
    if not isinstance(existing, list):
        raise InstallError("config-field-not-a-list", path=str(path), field=target.event)

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
    merged[HOOKS_FIELD] = dict(hooks) | {target.event: merged_entries}

    change = HookChange(
        path=path,
        action=action,
        entry=entry,
        previous=previous,
        duplicates=max(len(ours) - 1, 0),
        target=target,
    )
    return change, merged, original


def install(
    project_dir: str | Path,
    dry_run: bool = False,
    *,
    target: HookTarget = CLAUDE_HOOK,
) -> HookChange:
    """Install one packaged hook into a project, or say what would change.

    The dry run calls the same ``plan`` the real run does, so it cannot preview
    something different from what a write would produce.
    """
    path = target.path(project_dir)
    change, merged, original = plan(path, target=target)
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
    return _plan_files(Path(project_dir) / CLAUDE_DIR, asset_sources())


def _plan_files(root: Path, sources: list[tuple[Path, Path]]) -> list[FileChange]:
    """Compare packaged files with one harness directory without writing."""
    changes = []
    for source, relative in sources:
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


def codex_asset_sources() -> list[tuple[Path, Path]]:
    """Every packaged Codex skill, as a source and path below ``.codex``."""
    root = Path(__file__).parent / "codex" / "skills"
    if not root.is_dir():  # pragma: no cover - a broken install
        raise InstallError("assets-missing", asset="codex/skills", path=str(root))
    found = [
        (source, Path("skills") / source.relative_to(root))
        for source in sorted(root.rglob("*"))
        if source.is_file() and not source.name.startswith(".")
    ]
    if not found:  # pragma: no cover - a broken install
        raise InstallError("assets-empty", asset=CODEX_DIR, path=str(root))
    return found


def plan_codex_assets(project_dir: str | Path) -> list[FileChange]:
    """Work out which Codex skills a project is missing or has an older copy of."""
    return _plan_files(Path(project_dir) / CODEX_DIR, codex_asset_sources())


def _through_a_link(root: Path, relative: Path) -> bool:
    """Whether anything on the way down to ``relative`` is a symlink.

    A destination reached through a link is reported and left alone. This
    repository points ``.claude/skills/outrage`` at its own source tree
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
    """Everything ``outrage init`` does to a project, or would do."""

    project_dir: Path
    server: config.Change
    hooks: tuple[HookChange, ...]
    """One per :data:`HOOK_TARGETS`, in that order."""

    assets: tuple[FileChange, ...]
    """Claude Code skills and agents."""

    codex_assets: tuple[FileChange, ...]
    """Codex skills."""

    table: mountfile.Starter
    """The project's mount table: written when there is none, never rewritten."""

    @property
    def writes(self) -> bool:
        return (
            self.server.writes
            or self.table.writes
            or any(h.writes for h in self.hooks)
            or any(a.writes for a in self.assets)
            or any(a.writes for a in self.codex_assets)
        )


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
    """Set a project up: the MCP server entry, hooks, and packaged skills.

    The whole of it is planned before any of it is written, so a refusal - a
    settings file that does not parse, a ``.mcp.json`` that does not - stops
    the run rather than leaving a project half arranged. The dry run stops
    after the same planning the real run does, so it cannot preview something a
    write would disagree with.

    ``outrage config`` writes the server entry alone and this calls it rather than
    repeating it, which is also why ``log`` and ``log_content`` are passed
    through. ``root_mount`` and the two mount lists no longer reach the entry
    at all: a mount table lives in ``mounts.toml`` in the store directory, and
    they seed it - see :func:`outrage.mountfile.plan_starter`, and note that a
    table already there is reported and left alone rather than rewritten.

    Passing them through was never enough on its own, and a real project lost
    three mounts and its ``--log`` to a re-run of ``outrage init`` that was only
    meant to install a hook: the flags default to nothing, so the entry was
    rebuilt with nothing. :func:`outrage.config.merge_entry` is the actual fix
    and it sits in ``plan``, where both this and ``outrage config`` reach it.
    """
    project = Path(project_dir).expanduser().resolve()

    assets = plan_assets(project)
    codex_assets = plan_codex_assets(project)

    hooks = []
    for target in HOOK_TARGETS:
        path = target.path(project)
        hooks.append((path, *plan(path, target=target)))

    store_dir = directory if directory is not None else config.default_store_dir(project)
    server_path = config.config_path("project", project)
    entry = config.server_entry(store_dir, log=log, log_content=log_content)
    server, servers, servers_text = config.plan(server_path, "project", entry)
    table = mountfile.plan_starter(
        store_dir,
        root_mount=root_mount,
        mounts=mounts,
        read_only_mounts=read_only_mounts,
    )

    if not dry_run:
        if server.writes:
            config.write_config(server_path, servers, servers_text)
        if table.writes:
            mountfile.write_starter(table)
        for path, hook, settings, settings_text in hooks:
            if hook.writes:
                config.write_config(path, settings, settings_text)
        write_assets(assets)
        write_assets(codex_assets)

    return Installation(
        project_dir=project,
        server=server,
        table=table,
        hooks=tuple(hook for _, hook, _, _ in hooks),
        assets=tuple(assets),
        codex_assets=tuple(codex_assets),
    )


__all__ = [
    "ASSET_DIRS",
    "CLAUDE_DIR",
    "CODEX_DIR",
    "CLAUDE_HOOK",
    "COPILOT_HOOK",
    "HOOKS_FIELD",
    "HOOK_TARGETS",
    "MARKER",
    "MARKER_MATCH",
    "SETTINGS_NAME",
    "FileChange",
    "HookChange",
    "HookTarget",
    "InstallError",
    "Installation",
    "asset_sources",
    "codex_asset_sources",
    "init",
    "install",
    "is_ours",
    "plan",
    "plan_assets",
    "plan_codex_assets",
    "settings_path",
    "template_entry",
    "write_assets",
]
