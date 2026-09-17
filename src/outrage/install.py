"""Setting a project up: the MCP entries, hooks, and harness-specific skills.

``init`` is the whole of ``outrage init`` and the three parts are separable: the
server entries - ``.mcp.json``, ``.codex/config.toml`` for Codex and
``.cursor/mcp.json`` for Cursor, neither of which reads the first - are
:mod:`outrage.config`'s and are called rather
than repeated, the
session-start hooks are written here, and packaged assets are copied into the
directories their harness reads. Most of what follows is about the hooks,
because they are the part with something to say.

A config file belongs to the user, not to outrage. It holds their model, their
permissions and their own hooks, so this writes the one entry it owns and
leaves everything else exactly as it found it - the rule :mod:`outrage.config`
already follows for ``.mcp.json``, and the reason its ``read_config`` and
``write_config`` are reused here rather than reimplemented.

## Four harnesses, one hook each

:data:`HOOK_TARGETS` is the list, and everything below takes one of them rather
than assuming Claude Code. Adding the second one is what turned the constants
into a :class:`HookTarget`, on the rule that nothing is generalised before
there is a second real case to generalise *to*, and Copilot CLI was it. Codex,
added third, cost a template and a constant and no change to any function here
- which is the shape working.

Cursor, added fourth, cost one more field. Its file is ``.cursor/hooks.json``,
Copilot's shape down to the ``"version": 1`` stamp and the lower-case
``sessionStart``, and its entry is a single ``command`` string like Codex's.
What it does not share with either is the **payload**, and that is the field:
Cursor reads back ``additional_context`` where Copilot reads
``additionalContext``, the same word in a different case convention. One
character of difference that delivers nothing at all if it is wrong, which is
why :attr:`HookTarget.context_field` spells it out per harness rather than
letting a boolean mean "the flat one".

Cursor's packaged *assets* are still nothing: its project instructions are
``.cursor/rules`` and ``.cursor/commands``, and there is no packaged equivalent
of either here, so :func:`write_assets` has nothing to copy there.

Cursor's ``matcher`` is documented as optional for every event, so unlike the
Codex one it is left out. That is the same rule as Codex's, not a departure
from it: ship what the documentation establishes. For Codex requiredness was
*not* established and the example carried one, so the example won.

They differ in more than spelling:

* **Claude Code** merges into ``.claude/settings.json``, a file the user owns
  outright and which this project does not commit.
* **Copilot CLI** takes a file per purpose under ``.github/hooks/``, so
  ``.github/hooks/outrage.json`` is outrage's own, and repository agents under
  ``.github/agents/``. ``.github`` is usually **committed**, so a re-run's diff
  lands in somebody's version control where the Claude one does not.
* Copilot's packaged template carries both ``bash`` and ``powershell`` forms,
  but the installed entry keeps only the form for the current platform. The
  file also needs ``"version": 1`` at its top. Hence :attr:`HookTarget.base`:
  what to start from when the file does not exist.
* **Codex** reads ``.codex/hooks.json``, its own file like Copilot's, but the
  entry inside is Claude Code's shape down to the ``hookSpecificOutput``
  payload - so the two templates differ only in the ``matcher`` below.
  ``.codex`` is not committed here, so it behaves like the Claude file rather
  than the Copilot one.

All three are written by default. A project that uses one harness carries a
small inert file for the other two, which is cheaper than an installer that has
to be told what the user is running.

## The matcher outrage does not know the vocabulary of

Codex's documented ``SessionStart`` example carries ``"matcher":
"startup|resume"``, and the template ships exactly that. Whether the field is
required, and what else it could match, is **not** established: the
documentation gives no list of sources. Both readings fail the same silent way
this project keeps being caught by - omit a required matcher and the hook never
fires; ship a narrow one and it stops firing on whatever source is not named -
so this ships what was documented and does not improve on it. If a Codex
session is ever seen starting a way this does not match, that is the evidence
to widen it.

## Why the marker exists

``mcpServers`` is an object, so :mod:`outrage.config` can key on a name and
replace one entry. ``hooks.SessionStart`` is a **list**, and nothing in it says
who wrote what. An installer that cannot recognise its own entry has only bad
options: append every run and accumulate duplicates, or replace the lot and
destroy hooks it did not write.

All three harnesses carry the marker as the final argument to the managed
command::

    <python> -m outrage sessionstart outrage-managed:session-start:v3

The CLI accepts that one private argument and does not print it, so the marker
is independent of shell comment syntax and remains absent from stdout.

Copilot's command also carries a hidden ``--copilot`` flag so the CLI emits its
flat ``additionalContext`` payload rather than Claude and Codex's nested one,
and Cursor's carries ``--cursor`` for its ``additional_context``. Both flags
stay accepted for as long as an entry written by an older release might still
be installed: the hook file is only rewritten by ``outrage init``, so upgrading
the package does not upgrade the command line already recorded in it.
Older Copilot entries carried the marker in a ``comment`` field, and older
Claude Code and Codex entries carried it in a trailing shell comment;
:func:`is_ours` looks for the marker anywhere in the entry, so every generation
is recognised and replaced without a migration.

An unknown JSON key on the entry - ``{"_outrageManaged": …}`` - was tested and
works: the client tolerates it and the hook still fires. It was rejected
anyway. It depends on that tolerance continuing, which is undocumented, and if
it ever stops the hook is rejected and delivers nothing *silently*. An ordinary
argument belongs to the command contract and needs no undocumented JSON
tolerance. Both client behaviours this project has been burnt by were
undocumented ones.

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

All four hooks now run ``<python> -m outrage sessionstart``.
The interpreter is the absolute :data:`sys.executable` of the environment that
ran ``outrage init``, for the same reason the MCP entry names that environment:
a hook does not inherit an activated environment. The managed marker is an
ordinary final argument rather than a shell comment, so neither it nor the
command depends on ``#`` meaning the same thing on every platform.

Copilot CLI remains different only at the boundary: its hook contract selects
one of ``bash`` and ``powershell`` according to the platform, and its output is
the documented flat payload. The command reads the same shipped prompt at
invocation time and selects that shape with ``--copilot``. Cursor takes one
command string for every platform, as Codex does, and differs only in the
payload key.

## The packaged files have no identity, so there is a receipt

A hook entry and a server table can be recognised: one carries a marker, the
other a name. A copied markdown file carries nothing at all, so the only
evidence about it is its bytes -- and bytes cannot answer the question that
matters, which is whether a file differing from the packaged copy was *edited*
or is simply an **older release's** copy that nobody has touched. The second is
the common one: it happens to every project on any upgrade that changed a
shipped file.

That was affordable while the answer was "overwrite it anyway". It stops being
affordable once a difference refuses, because then every upgrade refuses.

:class:`InstallRecord` is what separates the two. ``init`` writes one manifest
per harness directory, holding a hash of each file as it wrote it, and a later
run compares three things rather than two: what is on disk, what this release
packages, and what outrage recorded putting there. A file that matches the
record but not the package is an upgrade and is replaced in silence; one that
matches neither was edited, and both ``init`` and ``uninit`` refuse over it.

The rules are :class:`outrage.bulk.ExportRecord`'s, which answers the same
question about an exported document: a file rather than a name or a table in a
process, unknown fields ignored on read so a later writer can record more, and
**a missing record degrades to not making the check** rather than to making it
wrongly. The last is what makes the first run after an upgrade possible at all:
no project in existence has a manifest, so ``init`` adopts -- it does what it
did before, and records what it wrote, so the check begins one run later.

There is deliberately no timestamp and no version string in it. One harness
directory is usually committed, so a field that changes on every run is a diff
in somebody's history for nothing; what is worth recording is what changes only
when the files do.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from . import config, mountfile
from .config import ConfigError, read_config, write_config
from .errors import Refusal

#: What gets written into the entry, minus the ``:vN`` the template adds. One
#: marker for both harnesses: it names the hook, not the client.
MARKER = "outrage-managed:session-start"

#: What a matcher compares against: :data:`MARKER` without the product name, so
#: that an entry written under a former name is still recognised as ours and
#: replaced rather than duplicated. See the module docstring.
MARKER_MATCH = "-managed:session-start"

#: The complete marker written as the final CLI argument. The stable part is
#: still :data:`MARKER_MATCH`; the version remains informational.
SESSIONSTART_MARKER = f"{MARKER}:v3"

#: Where a project's skills, agents and settings live, relative to its root.
#: Declared above its three users rather than beside the assets, because the
#: settings path is one of them and used to spell the directory out.
CLAUDE_DIR = ".claude"

#: Where Codex reads project-scoped skills and hooks, relative to the project
#: root. Both live below it, so the hook target spells out only the filename.
CODEX_DIR = ".codex"

#: Where Copilot CLI reads its repository hook and preferred agent definitions.
GITHUB_DIR = ".github"

#: Where Cursor reads its project hook. The server entry lives here too, as
#: ``mcp.json``; :data:`outrage.config.CURSOR_CONFIG_NAME` is that one.
CURSOR_DIR = ".cursor"

#: The settings file the fragment is merged into, inside :data:`CLAUDE_DIR`.
SETTINGS_NAME = "settings.json"

#: The key below which that merge happens. Everything else in the file is
#: somebody else's and is written back as it was found.
HOOKS_FIELD = "hooks"

#: Where the packaged fragments live.
_TEMPLATES = Path(__file__).parent / "hooks"

_SESSIONSTART_COMMAND = "__OUTRAGE_SESSIONSTART_COMMAND__"
_SESSIONSTART_PROMPT = Path(__file__).parent / "documents" / "hooks" / "sessionstart.md"


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
    """The packaged fragment, **relative to the hooks directory**, holding the
    entry exactly as it is installed. :attr:`fragment` is where it actually is.

    Relative for the same reason :attr:`relative` is: a field that is the whole
    installation's absolute path is different on every machine, and this
    dataclass's ``repr`` is *rendered into the shipped API reference*. An
    absolute path here commits the build machine's checkout to
    ``documents/reference/install.md``, and ``test_the_reference_is_not_stale``
    then fails for anyone whose clone is somewhere else.
    """

    relative: Path
    """Where the file goes, relative to the project root."""

    event: str
    """The key below ``hooks`` this harness fires at session start."""

    base: dict[str, Any] = field(default_factory=dict)
    """What a newly created file starts from, before the entry is merged in.

    Empty for Claude Code. Copilot CLI and Cursor both require
    ``{"version": 1}``, and a file without it is not read - which is the sort of
    thing that fails by the hook simply never firing, so it is carried here
    rather than assumed.
    """

    context_field: str | None = None
    """The key this harness reads the prompt back under, or None for the nested
    Claude Code shape that Codex shares.

    A string rather than a flag because the two flat harnesses do not agree:
    Copilot CLI reads ``additionalContext`` and Cursor ``additional_context``.
    Nothing reports a payload under the wrong key - the session simply starts
    without the context - so the exact spelling is worth stating per harness.
    """

    payload_flag: str | None = None
    """The private ``outrage sessionstart`` flag that selects :attr:`context_field`.

    None where the nested shape is the default and no flag is needed. It is
    part of the installed command, so a flag here can be **added** but not
    renamed or removed: an entry written by an older release keeps running the
    command it recorded until ``outrage init`` rewrites the file.
    """

    @property
    def fragment(self) -> Path:
        """Where :attr:`template` actually is, inside this installation.

        A property rather than a field, so it stays out of the ``repr`` that
        the generated reference renders.
        """
        return _TEMPLATES / self.template

    def path(self, project_dir: str | Path) -> Path:
        """Where this hook's file is in a project, whether or not it exists yet."""
        return Path(project_dir) / self.relative


#: Claude Code: merged into the user's own settings file.
CLAUDE_HOOK = HookTarget(
    name="Claude Code",
    template=Path(SETTINGS_NAME),
    relative=Path(CLAUDE_DIR) / SETTINGS_NAME,
    event="SessionStart",
)

#: Copilot CLI: a file per purpose, so this one is outrage's own. Named for the
#: package rather than the event, so a second outrage hook joins it here rather
#: than claiming a second file.
COPILOT_HOOK = HookTarget(
    name="Copilot CLI",
    template=Path("copilot.json"),
    relative=Path(".github") / "hooks" / "outrage.json",
    event="sessionStart",
    base={"version": 1},
    context_field="additionalContext",
    payload_flag="--copilot",
)

#: Codex: its own file, like Copilot CLI, but the entry is Claude Code's shape
#: - ``SessionStart``, a nested ``hooks`` list, and the same
#: ``hookSpecificOutput`` payload. The one thing neither of the others has is
#: the ``matcher``; see the module docstring on why it is written as documented
#: rather than left out.
CODEX_HOOK = HookTarget(
    name="Codex",
    template=Path("codex.json"),
    relative=Path(CODEX_DIR) / "hooks.json",
    event="SessionStart",
)

#: Cursor: its own file again, Copilot's ``"version": 1`` stamp and lower-case
#: ``sessionStart``, and Codex's single ``command`` string. The one thing it
#: shares with neither is the payload key. ``matcher`` is documented as
#: optional here, so it is left out; see the module docstring on why Codex's is
#: written even so.
CURSOR_HOOK = HookTarget(
    name="Cursor",
    template=Path("cursor.json"),
    relative=Path(CURSOR_DIR) / "hooks.json",
    event="sessionStart",
    base={"version": 1},
    context_field="additional_context",
    payload_flag="--cursor",
)

#: Every hook ``outrage init`` writes, in the order it reports them.
HOOK_TARGETS = (CLAUDE_HOOK, COPILOT_HOOK, CODEX_HOOK, CURSOR_HOOK)

# There is deliberately no module-level HOOK_EVENT or TEMPLATE any more. They
# were the Claude Code target's event and template, and once a second target
# existed an alias that nothing read was a trap: editing it, or patching it in
# a test, would change nothing at all. `CLAUDE_HOOK.event` says which one it
# means, which is the thing that used to be implicit.


@dataclass(frozen=True, slots=True)
class HookChange:
    """What installing or removing the hook would do, or did."""

    path: Path
    action: str
    """``created``, ``updated`` or ``unchanged`` when the entry is being
    written, and ``removed``, ``absent`` or ``refused`` when it is being taken
    away."""

    entry: dict[str, Any]
    previous: dict[str, Any] | None
    """The entry being replaced or removed, when there was one."""
    duplicates: int = 0
    """Extra entries of ours removed, from a run that could not identify them."""

    target: HookTarget = CLAUDE_HOOK
    """Which harness's hook this is, so a report over several can name them."""

    refusals: tuple[Refusal, ...] = ()
    """Why this hook will not be touched, when something stopped it.

    **Never about the entry's content.** An installer replaces its own hook
    entry whole, so nothing a person writes inside one survives the next
    ``init`` anyway and a removal destroys nothing that was not already
    forfeit. What does land here is a settings file that cannot be read.
    """

    @property
    def writes(self) -> bool:
        return self.action in config.WRITING_ACTIONS

    def describe(self) -> str:
        line = f"{self.path}: {self.action}"
        if self.duplicates:
            line += f", removed {self.duplicates} duplicate entr"
            line += "y" if self.duplicates == 1 else "ies"
        return line


def settings_path(project_dir: str | Path) -> Path:
    """Where a project's Claude Code settings file is, existing or not."""
    return CLAUDE_HOOK.path(project_dir)


def sessionstart_command(
    executable: str | os.PathLike[str] | None = None,
    *,
    target: HookTarget = CLAUDE_HOOK,
) -> str:
    """Build the shell command installed for ``target``'s SessionStart payload.

    The absolute interpreter is the one running ``outrage init``. ``shlex``
    quotes it for POSIX shells and ``list2cmdline`` for Windows; neither has to
    quote JSON because :func:`sessionstart_payload` creates that at runtime.
    Windows paths use forward slashes, which Windows accepts and JSON can carry
    without another layer of backslash escaping.
    The marker is a real argument understood by the private CLI wiring, not a
    shell comment, so it survives either command language without reaching
    stdout.

    The only thing ``target`` changes is whether a payload flag is appended,
    which is :attr:`HookTarget.payload_flag`.
    """
    return _sessionstart_command(executable, target=target)


def _sessionstart_command(
    executable: str | os.PathLike[str] | None = None,
    *,
    target: HookTarget = CLAUDE_HOOK,
    shell: str | None = None,
) -> str:
    """The shared hook command, quoted for one harness's actual shell."""
    interpreter = str(Path(executable or sys.executable).resolve())
    if sys.platform == "win32":
        interpreter = interpreter.replace("\\", "/")
    argv = [
        interpreter,
        "-m",
        "outrage",
        "sessionstart",
    ]
    if target.payload_flag:
        argv.append(target.payload_flag)
    argv.append(SESSIONSTART_MARKER)
    if shell == "powershell":
        quoted = ("'" + argument.replace("'", "''") + "'" for argument in argv)
        return "& " + " ".join(quoted)
    if shell == "bash" or sys.platform != "win32":
        return shlex.join(argv)
    return subprocess.list2cmdline(argv)


def sessionstart_payload(*, target: HookTarget = CLAUDE_HOOK) -> dict[str, Any]:
    """Read the shipped prompt and wrap it in ``target``'s hook payload.

    Two shapes, and which one is not a property of this function: a harness
    with a :attr:`HookTarget.context_field` reads the prompt back under that
    key alone, and one without it takes Claude Code's nested envelope, which
    Codex shares down to the event name.
    """
    context = _SESSIONSTART_PROMPT.read_text(encoding="utf-8").removesuffix("\n")
    if target.context_field:
        return {target.context_field: context}
    return {
        "hookSpecificOutput": {
            "hookEventName": target.event,
            "additionalContext": context,
        }
    }


def _render_sessionstart_command(
    value: Any, *, target: HookTarget, shell: str | None = None
) -> Any:
    """Replace the packaged placeholder without knowing a harness's shape."""
    if isinstance(value, str):
        command = _sessionstart_command(
            target=target,
            shell=(
                "powershell"
                if shell is None and target is CLAUDE_HOOK and sys.platform == "win32"
                else shell
            ),
        )
        return value.replace(_SESSIONSTART_COMMAND, command)
    if isinstance(value, list):
        return [_render_sessionstart_command(item, target=target, shell=shell) for item in value]
    if isinstance(value, dict):
        return {
            key: _render_sessionstart_command(
                item,
                target=target,
                shell=key if target is COPILOT_HOOK and key in ("bash", "powershell") else shell,
            )
            for key, item in value.items()
        }
    return value


def template_entry(target: HookTarget = CLAUDE_HOOK) -> dict[str, Any]:
    """The entry to install, read from the packaged template.

    Every harness carries a placeholder rendered with the absolute interpreter
    and managed marker at init time. Copilot and Cursor receive the same
    command with a flag selecting their own flat payload key. The marker is
    present before the entry is accepted, so a broken template cannot silently
    become one a later run fails to recognise.
    """
    try:
        loaded = json.loads(target.fragment.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:  # pragma: no cover - a broken install
        raise InstallError("template-missing", path=str(target.fragment)) from exc
    except json.JSONDecodeError as exc:  # pragma: no cover - a broken install
        raise InstallError("template-not-json", path=str(target.fragment)) from exc

    loaded = _render_sessionstart_command(loaded, target=target)
    entries = loaded.get(HOOKS_FIELD, {}).get(target.event)
    if not isinstance(entries, list) or len(entries) != 1:
        raise InstallError("template-hook-count", event=target.event)
    entry = entries[0]
    if target is COPILOT_HOOK and isinstance(entry, dict):
        entry.pop("bash" if sys.platform == "win32" else "powershell", None)
    if target is CLAUDE_HOOK and sys.platform == "win32":
        handlers = entry.get("hooks") if isinstance(entry, dict) else None
        if isinstance(handlers, list) and len(handlers) == 1 and isinstance(handlers[0], dict):
            # Claude Code otherwise prefers Git Bash when it is installed.
            # A Windows-native absolute interpreter path is not a Bash path;
            # choosing PowerShell makes the command and the shell agree.
            handlers[0]["shell"] = "powershell"
    if not is_ours(entry):
        raise InstallError("template-unmarked", marker=MARKER)
    return entry


def is_ours(entry: Any) -> bool:
    """Whether this session-start entry is one outrage wrote.

    The marker anywhere in the entry, because the harnesses put the command in
    different places - ``hooks[].command`` for Claude Code and Codex, ``bash``
    and ``powershell`` for Copilot CLI - and a matcher that knows those shapes
    has to be taught the next one. Codex arrived and needed nothing here, which
    is the argument. Nothing but our own entry carries a string in this
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


def plan_hook_removal(
    path: Path,
    *,
    target: HookTarget = CLAUDE_HOOK,
) -> tuple[HookChange, dict[str, Any] | None, str | None]:
    """Work out what taking our session-start entry out of ``path`` would change.

    Returns what :func:`plan` returns, with ``None`` in place of the settings
    when there is nothing to write.

    **Every entry the marker matches goes**, not merely the first: a run that
    once failed to recognise its own entry can have left more than one, and
    leaving the extras behind would leave the hook firing.

    Nothing here raises. A settings file that will not parse is recorded as a
    refusal instead, so a caller taking four hooks out at once reports all four
    answers rather than the first failure.

    The event's list is left in place when the last entry leaves it. An empty
    list fires nothing, and the file belongs to whoever else writes in it.
    """
    try:
        settings, original = read_config(path)
    except ConfigError as exc:
        return _hook_refused(path, target, Refusal.of(exc)), None, None

    hooks = settings.get(HOOKS_FIELD, {})
    if not isinstance(hooks, dict):
        refusal = Refusal(
            "config-field-not-an-object",
            overridable=False,
            path=str(path),
            field=HOOKS_FIELD,
        )
        return _hook_refused(path, target, refusal), None, original

    existing = hooks.get(target.event, [])
    if not isinstance(existing, list):
        refusal = Refusal(
            "config-field-not-a-list",
            overridable=False,
            path=str(path),
            field=target.event,
        )
        return _hook_refused(path, target, refusal), None, original

    ours = [index for index, entry in enumerate(existing) if is_ours(entry)]
    if not ours:
        change = HookChange(path=path, action="absent", entry={}, previous=None, target=target)
        return change, None, original

    kept = [entry for index, entry in enumerate(existing) if index not in set(ours)]
    merged = dict(settings)
    merged[HOOKS_FIELD] = dict(hooks) | {target.event: kept}

    change = HookChange(
        path=path,
        action="removed",
        entry={},
        previous=existing[ours[0]],
        duplicates=len(ours) - 1,
        target=target,
    )
    return change, merged, original


def _hook_refused(path: Path, target: HookTarget, *refusals: Refusal) -> HookChange:
    """A hook that will not be touched, carrying why."""
    return HookChange(
        path=path,
        action="refused",
        entry={},
        previous=None,
        target=target,
        refusals=refusals,
    )


# -- the packaged skill and agents ---------------------------------------


#: Packaged directories that install into ``.claude/``, copied whole. Markdown
#: a client reads directly: nothing here is executed, so nothing here needs an
#: interpreter or an absolute path, and a copy of it is complete on its own.
ASSET_DIRS = ("skills", "agents")


#: What ``init`` writes beside the files it copied, in each harness directory,
#: recording what it put there. Named for the suffix the export record already
#: uses, because it is the same mechanism answering the same question.
RECORD_NAME = ".outrage.json"

#: The manifest format. Bumped only by a change an older reader cannot survive;
#: an added field is not one, since unknown fields are ignored on read.
RECORD_VERSION = 1


def _digest(content: bytes) -> str:
    """The hash a receipt records. Named for its algorithm, so a second one can
    be added beside it rather than replacing it."""
    return hashlib.sha256(content).hexdigest()


@dataclass(frozen=True, slots=True)
class InstallRecord:
    """What ``init`` last wrote into one harness directory, as it recorded it.

    The only evidence that separates a packaged file somebody edited from one
    an earlier release wrote. See the module docstring for why bytes alone
    cannot, and :class:`outrage.bulk.ExportRecord` for the shape this follows.
    """

    files: dict[str, str]
    """Each installed file, by its path below the harness directory in POSIX
    spelling, to the hash of what was written there. POSIX because one of these
    directories is committed and read on whatever platform checks it out."""

    version: int = RECORD_VERSION

    @staticmethod
    def path_for(root: str | Path) -> Path:
        """Where the receipt for the directory at ``root`` is kept."""
        return Path(root) / RECORD_NAME

    @classmethod
    def read(cls, root: str | Path) -> InstallRecord | None:
        """The receipt in ``root``, or None if there is not a readable one.

        None for every way it can be absent -- not there, not JSON, not an
        object, holding no usable file table -- because the caller's fallback
        is to make no claim about what it finds, which is exactly right for a
        directory outrage has never recorded writing to.
        """
        try:
            written = cls.path_for(root).read_text(encoding="utf-8")
        except (OSError, ValueError):
            return None
        try:
            held = json.loads(written)
        except json.JSONDecodeError:
            return None
        if not isinstance(held, dict):
            return None
        files = held.get("files")
        if not isinstance(files, dict):
            return None
        # Unknown names dropped rather than refused: a newer writer's extra
        # field must not cost this reader the check it can still make.
        kept = {
            name: value
            for name, value in files.items()
            if isinstance(name, str) and isinstance(value, str)
        }
        version = held.get("version")
        return cls(files=kept, version=version if isinstance(version, int) else RECORD_VERSION)

    @classmethod
    def of(cls, changes: Sequence[FileChange]) -> InstallRecord:
        """The receipt for a directory these changes have just been applied to.

        The packaged bytes, because that is what is on disk once every change
        that writes has been written and every change that did not write was
        already equal to them. A symlinked path is left out: its content is not
        outrage's to claim, and nothing wrote it.
        """
        return cls(
            files={
                change.relative: _digest(change.source.read_bytes())
                for change in changes
                if change.action != "linked"
            }
        )

    def __contains__(self, relative: str) -> bool:
        return relative in self.files

    def matches(self, relative: str, content: bytes) -> bool:
        """Whether ``content`` is what this receipt says was written at ``relative``."""
        recorded = self.files.get(relative)
        return recorded is not None and recorded == _digest(content)

    def write(self, root: str | Path) -> bool:
        """Write this receipt into ``root``, and say whether anything changed.

        False when the directory already holds exactly this, so a re-run leaves
        no diff behind in a harness directory somebody commits.
        """
        if self == InstallRecord.read(root):
            return False
        path = self.path_for(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        _replace(
            path,
            (
                json.dumps(
                    {"version": self.version, "files": self.files},
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8"),
        )
        return True


@dataclass(frozen=True, slots=True)
class FileChange:
    """What installing or removing one packaged file would do, or did."""

    path: Path
    source: Path
    action: str
    """What comparing the file with the packaged copy found, which each command
    reads for itself:

    ``created``
        Not there. ``init`` writes it; a removal has nothing to do.
    ``unchanged``
        Byte for byte the packaged copy.
    ``updated``
        Different, and the receipt says outrage wrote what is there -- so an
        **earlier release's** copy, which nobody has touched.
    ``edited``
        Different, and the receipt says outrage wrote something else. Somebody
        edited it, and both commands refuse rather than destroy it.
    ``unrecorded``
        Different, with no receipt covering it, so which of the two it is
        cannot be told. ``init`` does what it did before receipts existed;
        a removal refuses.
    ``linked``
        Reached through a symlink, and left alone by everything.
    """

    relative: str = ""
    """Where the file is below its harness directory, in POSIX spelling, which
    is how a receipt names it."""

    @property
    def writes(self) -> bool:
        """Whether ``init`` writes this one without being forced."""
        return self.action in ("created", "updated", "unrecorded")

    @property
    def refuses(self) -> bool:
        """Whether this one stops a run that was not forced."""
        return self.action == "edited"

    def describe(self) -> str:
        return f"{self.path}: {self.action}"


def asset_refusals(changes: Sequence[FileChange]) -> list[Refusal]:
    """Every packaged file somebody edited, as refusals, one per file.

    Overridable: the content is real and a caller may knowingly discard it.
    """
    return [Refusal("asset-edited", path=str(change.path)) for change in changes if change.refuses]


def removal_refusals(changes: Sequence[FileChange]) -> list[Refusal]:
    """The same, for a removal, which refuses over one more case.

    A file with no receipt covering it might be an earlier release's copy or
    might be somebody's work, and deleting it is not reversible either way.
    ``init`` overwrites such a file because that is what it has always done and
    a refusal there would block the very upgrade that starts recording them;
    deleting one on the same evidence would be a different bet entirely.
    """
    return [
        *asset_refusals(changes),
        *(
            Refusal("asset-unrecorded", path=str(change.path))
            for change in changes
            if change.action == "unrecorded"
        ),
    ]


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
        raise InstallError("assets-empty", asset=CLAUDE_DIR, path=str(Path(__file__).parent))
    return found


def plan_assets(project_dir: str | Path) -> list[FileChange]:
    """Work out which packaged files a project is missing or has an older copy of."""
    return _plan_files(Path(project_dir) / CLAUDE_DIR, asset_sources())


def _plan_files(root: Path, sources: list[tuple[Path, Path]]) -> list[FileChange]:
    """Compare packaged files with one harness directory without writing.

    Three-way where it used to be two: what is on disk, what this release
    packages, and what the receipt in ``root`` says outrage wrote. Only the
    third can tell an edit from an upgrade, and where there is no receipt this
    says so -- ``unrecorded`` -- rather than guessing either way.

    One comparison for both commands, deliberately. A removal that worked out
    for itself what "differs" meant could disagree with the installer about the
    same file, and the two disagreeing is the failure neither would notice.
    """
    record = InstallRecord.read(root)
    changes = []
    for source, relative in sources:
        path = root / relative
        spelt = relative.as_posix()
        if _through_a_link(root, relative):
            action = "linked"
        elif not path.exists():
            action = "created"
        else:
            held = path.read_bytes()
            if held == source.read_bytes():
                action = "unchanged"
            elif record is None or spelt not in record:
                action = "unrecorded"
            elif record.matches(spelt, held):
                action = "updated"
            else:
                action = "edited"
        changes.append(FileChange(path=path, source=source, action=action, relative=spelt))
    return changes


def write_assets(changes: list[FileChange], *, force: bool = False) -> None:
    """Copy across the files that differ, atomically and one at a time.

    ``force`` also replaces a file somebody edited, which is otherwise the one
    thing this declines to do.
    """
    for change in changes:
        if not (change.writes or (force and change.refuses)):
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


def copilot_asset_sources() -> list[tuple[Path, Path]]:
    """Every packaged Copilot agent, as a source and path below ``.github``."""
    root = Path(__file__).parent / "copilot" / "agents"
    if not root.is_dir():  # pragma: no cover - a broken install
        raise InstallError("assets-missing", asset="copilot/agents", path=str(root))
    found = [
        (source, Path("agents") / source.relative_to(root))
        for source in sorted(root.rglob("*"))
        if source.is_file() and not source.name.startswith(".")
    ]
    if not found:  # pragma: no cover - a broken install
        raise InstallError("assets-empty", asset=GITHUB_DIR, path=str(root))
    return found


def plan_copilot_assets(project_dir: str | Path) -> list[FileChange]:
    """Work out which Copilot agents a project is missing or has an older copy of."""
    return _plan_files(Path(project_dir) / GITHUB_DIR, copilot_asset_sources())


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
    codex_server: config.Change
    """The same server in ``.codex/config.toml``, which is where Codex reads it."""

    cursor_server: config.Change
    """The same server again in ``.cursor/mcp.json``, for Cursor. Its hook is in
    :attr:`hooks` with the rest; what it has none of is packaged assets."""

    hooks: tuple[HookChange, ...]
    """One per :data:`HOOK_TARGETS`, in that order."""

    assets: tuple[FileChange, ...]
    """Claude Code skills and agents."""

    codex_assets: tuple[FileChange, ...]
    """Codex skills."""

    copilot_assets: tuple[FileChange, ...]
    """Copilot CLI agents."""

    table: mountfile.Starter
    """The project's mount table: written when there is none, never rewritten."""

    refusals: tuple[Refusal, ...] = ()
    """Every reason this installation will not proceed, not merely the first.

    Empty on an ordinary run. What lands here is a packaged file somebody
    edited, which is the one thing ``init`` declines to overwrite -- and every
    one of them, so a person is told the whole of what is in the way and
    decides once.
    """

    @property
    def writes(self) -> bool:
        return (
            self.server.writes
            or self.codex_server.writes
            or self.cursor_server.writes
            or self.table.writes
            or any(h.writes for h in self.hooks)
            or any(a.writes for a in self.assets)
            or any(a.writes for a in self.codex_assets)
            or any(a.writes for a in self.copilot_assets)
        )


def init(
    project_dir: str | Path,
    directory: str | Path | None = None,
    *,
    log: Any = None,
    log_content: str | None = None,
    no_info: bool = False,
    no_remount: bool = False,
    no_versioning: bool = False,
    root_mount: str | None = None,
    mounts: Sequence[str] = (),
    read_only_mounts: Sequence[str] = (),
    dry_run: bool = False,
    force: bool = False,
) -> Installation:
    """Set a project up: the MCP server entries, hooks, and packaged skills.

    The server entry is written three times, to ``.mcp.json``, to Codex's
    ``.codex/config.toml`` and to Cursor's ``.cursor/mcp.json``, from the same
    options; the Codex one carries a marker, :func:`outrage.config.plan_codex`
    says why, and the Cursor one carries a ``type``,
    :func:`outrage.config.cursor_entry` says why. The hooks are one per
    :data:`HOOK_TARGETS`, which is all four harnesses.

    The whole of it is planned before any of it is written, so a refusal - a
    settings file that does not parse, a ``.mcp.json`` that does not - stops
    the run rather than leaving a project half arranged. The dry run stops
    after the same planning the real run does, so it cannot preview something a
    write would disagree with.

    ``outrage config`` writes the server entry alone and this calls it rather than
    repeating it, which is also why ``log``, ``log_content``, ``no_info``,
    ``no_remount`` and ``no_versioning`` are passed through. ``root_mount`` and
    the two mount lists no longer reach the entry at all: a mount table lives in
    ``mounts.toml``, and they seed it - see :func:`outrage.mountfile.plan_starter`, and note that a
    table already there is reported and left alone rather than rewritten.

    Passing them through was never enough on its own, and a real project lost
    three mounts and its ``--log`` to a re-run of ``outrage init`` that was only
    meant to install a hook: the flags default to nothing, so the entry was
    rebuilt with nothing. :func:`outrage.config.merge_entry` is the actual fix
    and it sits in ``plan``, where both this and ``outrage config`` reach it.

    **A packaged file somebody edited stops the run**, and ``force`` is what
    replaces it anyway. Every such file is reported, not the first, which is
    why they are collected as :class:`outrage.errors.Refusal` values rather
    than raised: the whole of what is in the way should reach a person in one
    go. Refusing is only affordable because a receipt can tell an edit from an
    older release's copy -- :class:`InstallRecord`, and the module docstring on
    what happens where there is no receipt yet.
    """
    project = Path(project_dir).expanduser().resolve()

    assets = plan_assets(project)
    codex_assets = plan_codex_assets(project)
    copilot_assets = plan_copilot_assets(project)

    hooks = []
    for target in HOOK_TARGETS:
        path = target.path(project)
        hooks.append((path, *plan(path, target=target)))

    store_dir = directory if directory is not None else config.default_store_dir(project)
    server_path = config.config_path("project", project)
    entry = config.server_entry(
        store_dir,
        log=log,
        log_content=log_content,
        no_info=no_info,
        no_remount=no_remount,
        no_versioning=no_versioning,
    )
    server, servers, servers_text = config.plan(server_path, "project", entry)
    codex_path = config.codex_config_path(project)
    codex_entry = config.server_entry(
        store_dir,
        log=log,
        log_content=log_content,
        no_info=no_info,
        no_remount=no_remount,
        no_versioning=no_versioning,
        marked=True,
    )
    codex_server, codex_document, codex_text = config.plan_codex(codex_path, codex_entry)
    # Cursor's file is `.mcp.json`'s shape, so this is `plan` again with
    # another path rather than a planner of its own.
    cursor_path = config.cursor_config_path(project)
    cursor_server, cursor_servers, cursor_text = config.plan(
        cursor_path, config.CURSOR_SCOPE, config.cursor_entry(entry)
    )
    table = mountfile.plan_starter(
        store_dir,
        root_mount=root_mount,
        mounts=mounts,
        read_only_mounts=read_only_mounts,
    )

    refusals = (
        ()
        if force
        else tuple(
            [
                *asset_refusals(assets),
                *asset_refusals(codex_assets),
                *asset_refusals(copilot_assets),
            ]
        )
    )

    if not dry_run and not refusals:
        if server.writes:
            config.write_config(server_path, servers, servers_text)
        if codex_server.writes:
            config.write_toml(codex_path, codex_document, codex_text)
        if cursor_server.writes:
            config.write_config(cursor_path, cursor_servers, cursor_text)
        if table.writes:
            mountfile.write_starter(table)
        for path, hook, settings, settings_text in hooks:
            if hook.writes:
                config.write_config(path, settings, settings_text)
        for root, changes in (
            (project / CLAUDE_DIR, assets),
            (project / CODEX_DIR, codex_assets),
            (project / GITHUB_DIR, copilot_assets),
        ):
            write_assets(changes, force=force)
            # After the copies, so the receipt describes what is actually
            # there rather than what was about to be.
            InstallRecord.of(changes).write(root)

    return Installation(
        project_dir=project,
        server=server,
        codex_server=codex_server,
        cursor_server=cursor_server,
        table=table,
        hooks=tuple(hook for _, hook, _, _ in hooks),
        assets=tuple(assets),
        codex_assets=tuple(codex_assets),
        copilot_assets=tuple(copilot_assets),
        refusals=refusals,
    )


# -- taking a project apart again ----------------------------------------


def removal_action(change: FileChange, *, forced: bool = False) -> str:
    """What removing one packaged file does, read off the shared comparison.

    The comparison is :func:`_plan_files`' and says what the file *is*; this
    says what a removal makes of that, which is not the same reading the
    installer takes. An earlier release's copy is still outrage's to delete;
    a file nobody can account for is not.
    """
    if change.action == "linked":
        return "linked"
    if change.action == "created":
        return "absent"
    if change.action in ("unchanged", "updated"):
        return "removed"
    return "removed" if forced else "refused"


@dataclass(frozen=True, slots=True)
class Edit:
    """One file a removal will write or delete, decided and ready to apply.

    The plan carries these so that applying it needs nothing but the plan --
    see :func:`apply_uninit` on why that matters.
    """

    path: Path
    document: Any | None = None
    """The whole file as it will be left, or None where it is being deleted."""
    original: str | None = None
    """The file's text as it was read, so its layout can be preserved."""
    toml: bool = False
    delete: bool = False


@dataclass(frozen=True, slots=True)
class Uninstallation:
    """Everything ``outrage uninit`` would take out of a project, and why not.

    Produced whole before anything is written, and applied from itself, so
    nothing can be done that the report did not describe.
    """

    project_dir: Path
    forced: bool
    server: config.Change
    codex_server: config.Change
    cursor_server: config.Change
    hooks: tuple[HookChange, ...]
    assets: tuple[FileChange, ...]
    codex_assets: tuple[FileChange, ...]
    copilot_assets: tuple[FileChange, ...]
    receipts: tuple[Path, ...]
    """The install receipts to delete. Outrage's own bookkeeping rather than
    configuration, and one left behind would claim files that are gone."""

    file_refusals: tuple[Refusal, ...] = ()
    edits: tuple[Edit, ...] = ()

    @property
    def refusals(self) -> tuple[Refusal, ...]:
        """Every reason found, over the whole project, in the order reported."""
        return (
            *self.server.refusals,
            *self.codex_server.refusals,
            *self.cursor_server.refusals,
            *(refusal for hook in self.hooks for refusal in hook.refusals),
            *self.file_refusals,
        )

    @property
    def blocking(self) -> tuple[Refusal, ...]:
        """The refusals that still stand, which under force is those no flag reaches."""
        return tuple(
            refusal for refusal in self.refusals if not (self.forced and refusal.overridable)
        )

    @property
    def writes(self) -> bool:
        return bool(self.edits)


def _forced(change: Any) -> Any:
    """A refused change reinstated, where every reason for it was overridable.

    Done to the *plan* rather than at the moment of writing, so that applying
    it stays a matter of doing what the report said and needs to know nothing
    about flags.
    """
    if change.action != "refused" or not change.refusals:
        return change
    if not all(refusal.overridable for refusal in change.refusals):
        return change
    return replace(change, action="removed")


def plan_uninit(project_dir: str | Path, *, force: bool = False) -> Uninstallation:
    """Work out everything removing outrage from a project would do.

    **Never writes and never raises.** A file that cannot be read becomes a
    refusal like any other, because the point of planning the whole project
    first is to report every reason at once: a caller who fixes one thing,
    runs again and meets the next has been sent round a loop this could have
    spared them.

    ``force`` is applied here, to the plan, rather than at the moment of
    writing. A refusal every reason for which is overridable becomes an
    ordinary removal and the reasons stay on it, so the report can say what was
    overridden; one that no flag reaches stays refused whatever was asked for.
    """
    project = Path(project_dir).expanduser().resolve()
    edits: list[Edit] = []

    def _edit(change: Any, path: Path, document: Any, original: str | None, toml: bool) -> Any:
        change = _forced(change) if force else change
        if change.writes and document is not None:
            edits.append(Edit(path=path, document=document, original=original, toml=toml))
        return change

    server_path = config.config_path("project", project)
    server, servers, servers_text = config.plan_removal(server_path, "project")
    server = _edit(server, server_path, servers, servers_text, False)

    codex_path = config.codex_config_path(project)
    codex_server, codex_document, codex_text = config.plan_codex_removal(codex_path)
    codex_server = _edit(codex_server, codex_path, codex_document, codex_text, True)

    cursor_path = config.cursor_config_path(project)
    cursor_server, cursor_servers, cursor_text = config.plan_removal(
        cursor_path, config.CURSOR_SCOPE
    )
    cursor_server = _edit(cursor_server, cursor_path, cursor_servers, cursor_text, False)

    hooks = []
    for target in HOOK_TARGETS:
        path = target.path(project)
        hook, settings, settings_text = plan_hook_removal(path, target=target)
        hooks.append(_edit(hook, path, settings, settings_text, False))

    assets = plan_assets(project)
    codex_assets = plan_codex_assets(project)
    copilot_assets = plan_copilot_assets(project)

    receipts: list[Path] = []
    for root, changes in (
        (project / CLAUDE_DIR, assets),
        (project / CODEX_DIR, codex_assets),
        (project / GITHUB_DIR, copilot_assets),
    ):
        for change in changes:
            if removal_action(change, forced=force) == "removed":
                edits.append(Edit(path=change.path, delete=True))
        receipt = InstallRecord.path_for(root)
        if receipt.exists():
            receipts.append(receipt)
            edits.append(Edit(path=receipt, delete=True))

    return Uninstallation(
        project_dir=project,
        forced=force,
        server=server,
        codex_server=codex_server,
        cursor_server=cursor_server,
        hooks=tuple(hooks),
        assets=tuple(assets),
        codex_assets=tuple(codex_assets),
        copilot_assets=tuple(copilot_assets),
        receipts=tuple(receipts),
        file_refusals=tuple(
            [
                *removal_refusals(assets),
                *removal_refusals(codex_assets),
                *removal_refusals(copilot_assets),
            ]
        ),
        edits=tuple(edits),
    )


def apply_uninit(plan: Uninstallation) -> None:
    """Carry out a plan :func:`plan_uninit` produced.

    **Takes the plan, not the project.** Nothing here looks at the project
    again, so there is no second derivation that could reach a different answer
    from the one already reported -- which is what makes the two passes a
    property of the code rather than a convention that holds until somebody
    adds a third caller.

    Applying a plan that still has :attr:`Uninstallation.blocking` refusals is
    the caller's mistake to avoid; this does what it was given.
    """
    for edit in plan.edits:
        if edit.delete:
            edit.path.unlink(missing_ok=True)
        elif edit.toml:
            config.write_toml(edit.path, edit.document, edit.original)
        else:
            config.write_config(edit.path, edit.document, edit.original)


def uninit(
    project_dir: str | Path,
    *,
    dry_run: bool = False,
    force: bool = False,
) -> Uninstallation:
    """Remove outrage's integration from a project, or say what removing it would do.

    Takes out the server entries, the session-start hooks, the packaged skills
    and agents, and the receipts recording them. **Leaves every file and
    directory standing**: an empty servers object and an empty hook list
    trigger nothing, and pruning a container risks removing a key the harness
    needs. The store directory is not touched at all -- this removes an
    integration, not anybody's documents.

    **Nothing at all is written when anything still refuses**, force or no
    force, which is the same all-or-nothing the installer has and for the same
    reason: a project left half arranged is a worse state than one left alone,
    and here it would be one where some of outrage still starts. A refusal no
    flag reaches -- a file that cannot be read -- therefore stops the whole
    removal, and the remedy is to repair or delete that file and run again.
    See :func:`plan_uninit`.
    """
    plan = plan_uninit(project_dir, force=force)
    if not dry_run and not plan.blocking:
        apply_uninit(plan)
    return plan


__all__ = [
    "ASSET_DIRS",
    "CLAUDE_DIR",
    "CODEX_DIR",
    "CURSOR_DIR",
    "GITHUB_DIR",
    "CLAUDE_HOOK",
    "CODEX_HOOK",
    "COPILOT_HOOK",
    "CURSOR_HOOK",
    "HOOKS_FIELD",
    "HOOK_TARGETS",
    "MARKER",
    "MARKER_MATCH",
    "SESSIONSTART_MARKER",
    "SETTINGS_NAME",
    "Edit",
    "FileChange",
    "HookChange",
    "HookTarget",
    "InstallError",
    "InstallRecord",
    "Installation",
    "RECORD_NAME",
    "RECORD_VERSION",
    "Uninstallation",
    "apply_uninit",
    "asset_refusals",
    "asset_sources",
    "codex_asset_sources",
    "copilot_asset_sources",
    "init",
    "install",
    "is_ours",
    "plan",
    "plan_assets",
    "plan_hook_removal",
    "plan_codex_assets",
    "plan_copilot_assets",
    "plan_uninit",
    "removal_action",
    "removal_refusals",
    "settings_path",
    "uninit",
    "sessionstart_command",
    "sessionstart_payload",
    "template_entry",
    "write_assets",
]
