"""Writing the MCP server configuration for a project or a user.

Separate from :mod:`outrage.cli` for the same reason the store is separate from
the server: the CLI should shape arguments and print, nothing else. Everything
here is callable and testable without going through argparse.

The problem this solves is that an MCP client launches the server as a
subprocess, so it needs an absolute path to an entry point inside whichever
environment outrage was installed in. That path is only reliably known from
inside that environment - which is where this code runs, and is why writing
the configuration is a command rather than something a user does by hand. The
``.mcp.json`` originally written by hand in this repository is the illustration:
it names one machine's conda prefix and is wrong everywhere else.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import OutrageError
from .eventlog import DEFAULT as LOG_BESIDE_STORE
from .store import DEFAULT_DIR_NAME

#: The name this server is registered under. Also the key that a re-run
#: replaces, which is what keeps unrelated servers in the file untouched.
SERVER_NAME = "outrage"

#: Project scoped configuration, committed with the project and read by clients
#: from the project root.
PROJECT_CONFIG_NAME = ".mcp.json"

#: User scoped configuration, in the home directory. Holds a great deal besides
#: MCP servers, which is why nothing here rewrites more of it than one key.
USER_CONFIG_NAME = ".claude.json"

#: The key holding the servers, in both configuration files. The rest of
#: either file belongs to somebody else and is written back untouched.
SERVERS_FIELD = "mcpServers"

#: Where a configuration may be written, and the order of preference: the
#: project it is for, or the user who runs it.
SCOPES = ("project", "user")

#: Console script installed by this package, and the fallback for when it is
#: absent. ``python -m outrage`` is equivalent, and works in an environment the
#: scripts directory of which is not where sys.executable lives.
SCRIPT_NAME = "outrage-server"

#: Console script for the command line, the other half of the pair. A caller
#: told which environment this server runs in wants it to run ``outrage`` there,
#: and there is no module fallback for this one: ``python -m outrage`` is the
#: *server*, so an installation without the script has no second spelling.
CLI_SCRIPT_NAME = "outrage"

_DEFAULT_INDENT = 2


class ConfigError(OutrageError, RuntimeError):
    """Raised when existing configuration cannot be safely updated."""


@dataclass(frozen=True, slots=True)
class Change:
    """What writing the configuration would do, or did."""

    path: Path
    scope: str
    name: str
    action: str
    """'created', 'updated' or 'unchanged'."""
    entry: dict[str, Any]
    previous: dict[str, Any] | None
    """The entry being replaced, when there was one."""

    @property
    def writes(self) -> bool:
        return self.action != "unchanged"


def script_command(
    script: str, executable: str | os.PathLike[str] | None = None
) -> list[str] | None:
    """The absolute command running ``script`` beside the given interpreter, or None.

    A console script names the environment unambiguously, which is the whole
    reason a path is reported rather than a bare name: a caller elsewhere runs
    *this* installation rather than whatever the same word resolves to on their
    PATH.

    None rather than a guess when it is not there. Which fallback is right is a
    property of the script -- the server has one and the command line has none
    -- so the caller who knows that decides, and a report that cannot name a
    command says so.
    """
    python = Path(executable or sys.executable)
    for candidate in (python.parent / script, python.parent / f"{script}.exe"):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return [str(candidate)]
    return None


def launch_command(executable: str | os.PathLike[str] | None = None) -> list[str]:
    """Build the absolute command that starts the server.

    Prefers the console script beside the running interpreter, because it is
    what an install provides and it names the environment unambiguously. Falls
    back to ``<python> -m outrage``, which is equivalent and cannot be missing: it
    needs only the interpreter that is already running and the package that is
    already imported.
    """
    python = Path(executable or sys.executable)
    return script_command(SCRIPT_NAME, python) or [str(python), "-m", "outrage"]


def server_entry(
    directory: str | os.PathLike[str],
    command: list[str] | None = None,
    *,
    log: Any = None,
    log_content: str | None = None,
    no_info: bool = False,
) -> dict[str, Any]:
    """Build the configuration entry for the stores in ``directory``.

    **One absolute path in the whole entry**, and it is the directory. A client
    cannot be relied on to launch the server in the project working directory,
    so a relative ``--dir`` would resolve against somewhere unpredictable and
    quietly produce a second, empty store rather than an error. Everything else
    is named relative to it, which is what lets a project be moved or checked
    out elsewhere with only that one line to fix.

    ``log`` adds ``--log``: a path, or the ``eventlog.DEFAULT`` sentinel for the
    file beside the store. Logging is off unless it is asked for here, and it is
    asked for here rather than by hand because an entry edited by hand is the
    failure this module exists to prevent.

    **The mounts are not here.** A flat run of ``--mount ref=reference.sqlite``
    strings in this array would make a client's JSON the place a mount table is
    maintained, and hand-editing it the supported way to change one. They live
    in ``mounts.toml`` in the store directory instead -
    :mod:`outrage.mountfile` - which is what leaves ``--dir`` as the only thing
    this entry has to carry. **An entry already naming mounts
    keeps them**: :func:`merge_entry` inherits what a new entry does not
    mention, and they still win, since the command line comes after the file.
    Nothing migrates that automatically, deliberately; ``outrage config`` says
    they are there.

    ``no_info`` adds ``--no-info``, withholding the tool that reports the
    server's environment and stores. Written here for the same reason ``--log``
    is: it belongs to the launch, and a client's JSON edited by hand is the
    failure this module exists to prevent. Being valueless makes no difference
    to :func:`merge_entry` -- it inherits by flag, so a re-run that does not
    mention it keeps it.
    """
    argv = list(command) if command is not None else launch_command()
    args = [*argv[1:], "--dir", str(Path(directory).expanduser().resolve())]
    if log is not None:
        args.append("--log")
        # Absolute for the same reason the store directory is.
        if log is not LOG_BESIDE_STORE:
            args.append(str(Path(log).expanduser().resolve()))
        if log_content is not None:
            args += ["--log-content", log_content]
    if no_info:
        args.append("--no-info")
    return {"command": argv[0], "args": args}


def mounts_in(args: Sequence[str]) -> list[str]:
    """The mount options an existing server entry still carries, if any.

    Nothing migrates these: an entry that names mounts goes on working, and
    they win over ``mounts.toml`` because the command line comes after the
    file. But an entry and a file both describing a table, with only one of
    them the place anybody thinks to look, is worth a sentence - so this is
    what ``outrage config`` reports.
    """
    named = ("--mount", "--mount-ro", "--root-mount")
    return [flag for flag, _ in split_args(list(args)) if flag in named]


def split_args(args: Sequence[str]) -> list[tuple[str, list[str]]]:
    """Take an argument list apart into ``(flag, values)`` pairs, in order.

    A flag is any token beginning with ``-``; its values are the tokens up to
    the next flag. That rule is deliberately about *shape* rather than about a
    list of known options: an argument this release has never heard of - added
    by hand, or by a newer one - comes apart the same way and can be put back
    unchanged. A leading token that is not a flag is paired with the empty
    string, so nothing is dropped by a list that does not start with one.
    """
    chunks: list[tuple[str, list[str]]] = []
    for token in args:
        if token.startswith("-"):
            chunks.append((token, []))
        elif chunks:
            chunks[-1][1].append(token)
        else:
            chunks.append(("", [token]))
    return chunks


def merge_entry(previous: dict[str, Any] | None, entry: dict[str, Any]) -> dict[str, Any]:
    """Fold ``entry`` onto the entry already in the file, keeping what it omits.

    An ``outrage init`` that is only asked to set a project up should not be
    able to switch off logging somebody turned on, or drop the mounts they
    configured - and before this it did exactly that, because
    :func:`server_entry` builds an argument list from what the caller passed
    and nothing else. A re-run with no flags therefore wrote an entry with no
    mounts.

    It is also what keeps an entry written before the mount table moved into
    ``mounts.toml`` working: ``server_entry`` no longer builds a ``--mount``,
    so the ones already in the file are inherited by every re-run rather than
    quietly dropped.

    So: **an option the new entry does not mention is inherited from the old
    one.** Options it does mention replace the old ones outright, all of them
    at once, so a re-run naming one ``--mount`` does not accumulate the
    previous three beside it. ``command`` always comes from the new entry -
    the absolute path into this environment is the one thing ``outrage config``
    exists to correct.

    The consequence to know: **an option cannot be removed by leaving it out.**
    Dropping a mount is an edit to the file. That is the right way round for a
    command a user runs to repair a project rather than to redefine it, and
    losing configuration silently is the failure that was actually reported.
    """
    if not previous:
        return entry
    old_args = previous.get("args")
    new_args = entry.get("args")
    if not _is_string_list(old_args) or not _is_string_list(new_args):
        # Nothing safe to take apart. The new entry stands on its own, which is
        # what happened to every entry before this function existed.
        return entry

    new_chunks = split_args(new_args)
    mentioned = {flag for flag, _ in new_chunks}
    inherited = [chunk for chunk in split_args(old_args) if chunk[0] not in mentioned]

    args: list[str] = []
    for flag, values in [*new_chunks, *inherited]:
        if flag:
            args.append(flag)
        args += values

    merged = dict(entry)
    merged["args"] = args
    return merged


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def config_path(scope: str, project_dir: str | os.PathLike[str] | None = None) -> Path:
    """Locate the configuration file for ``scope``."""
    if scope == "project":
        return Path(project_dir or Path.cwd()).expanduser().resolve() / PROJECT_CONFIG_NAME
    if scope == "user":
        return Path.home() / USER_CONFIG_NAME
    raise ValueError(f"unknown scope {scope!r}; expected one of {', '.join(SCOPES)}")


def default_store_dir(project_dir: str | os.PathLike[str] | None = None) -> Path:
    """Where the store goes when the caller does not say."""
    return Path(project_dir or Path.cwd()).expanduser().resolve() / DEFAULT_DIR_NAME


def read_config(path: Path) -> tuple[dict[str, Any], str | None]:
    """Read a configuration file, returning its content and original text.

    A file that exists but does not parse is an error rather than something to
    overwrite. The user scoped file in particular holds a great deal of
    unrelated state, and replacing it wholesale because one read failed would
    do far more damage than declining to write.
    """
    if not path.exists():
        return {}, None
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return {}, text
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError("config-not-json", path=str(path), reason=str(exc)) from exc
    if not isinstance(loaded, dict):
        raise ConfigError("config-not-an-object", path=str(path))
    return loaded, text


def plan(
    path: Path,
    scope: str,
    entry: dict[str, Any],
    name: str = SERVER_NAME,
) -> tuple[Change, dict[str, Any], str | None]:
    """Work out what writing ``entry`` into ``path`` would change.

    Returns the change, the merged configuration, and the file's original text,
    so a caller can report before writing and write without reading twice.
    """
    config, original = read_config(path)
    servers = config.get(SERVERS_FIELD, {})
    if not isinstance(servers, dict):
        raise ConfigError("config-field-not-an-object", path=str(path), field=SERVERS_FIELD)

    previous = servers.get(name)
    if previous is not None and not isinstance(previous, dict):
        raise ConfigError("config-server-not-an-object", path=str(path), server=name)

    # Merged here rather than by each caller, so that `outrage init` and
    # `outrage config` cannot disagree about what a re-run keeps.
    entry = merge_entry(previous, entry)

    if previous is None:
        action = "created"
    elif previous == entry:
        action = "unchanged"
    else:
        action = "updated"

    merged = dict(config)
    merged[SERVERS_FIELD] = dict(servers) | {name: entry}
    change = Change(
        path=path,
        scope=scope,
        name=name,
        action=action,
        entry=entry,
        previous=previous,
    )
    return change, merged, original


def write_config(path: Path, config: dict[str, Any], original: str | None = None) -> None:
    """Write ``config`` to ``path``, replacing it atomically.

    Written to a temporary file in the same directory and moved into place, so
    an interrupted write cannot truncate a file holding configuration this
    command did not create. Indentation and permissions follow the existing
    file where there is one: the point is to change one key, and a wholesale
    reformat or a loosened mode is a change nobody asked for.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(config, indent=_indent_of(original), ensure_ascii=False) + "\n"

    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(temporary, _mode_for(path))
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _indent_of(original: str | None) -> int:
    """Match the existing file's indentation, defaulting to two spaces."""
    if not original:
        return _DEFAULT_INDENT
    for line in original.splitlines()[1:]:
        stripped = line.lstrip(" ")
        if stripped and stripped != line:
            return len(line) - len(stripped)
        if line and not line.startswith(" "):
            # A second line at column zero means the file is not pretty printed.
            return _DEFAULT_INDENT
    return _DEFAULT_INDENT


def _mode_for(path: Path) -> int:
    """Keep an existing file's permissions; mkstemp's 0600 otherwise misleads.

    A new project file is world readable like the rest of a checkout, while a
    new user file is not: it sits in the home directory beside state that has
    no business being readable by anyone else.
    """
    try:
        return path.stat().st_mode & 0o7777
    except FileNotFoundError:
        return 0o644 if path.name == PROJECT_CONFIG_NAME else 0o600


__all__ = [
    "CLI_SCRIPT_NAME",
    "PROJECT_CONFIG_NAME",
    "SCOPES",
    "SCRIPT_NAME",
    "SERVERS_FIELD",
    "SERVER_NAME",
    "USER_CONFIG_NAME",
    "Change",
    "ConfigError",
    "config_path",
    "default_store_dir",
    "launch_command",
    "merge_entry",
    "mounts_in",
    "plan",
    "read_config",
    "script_command",
    "server_entry",
    "split_args",
    "write_config",
]
