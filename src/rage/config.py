"""Writing the MCP server configuration for a project or a user.

Separate from :mod:`rage.cli` for the same reason the store is separate from
the server: the CLI should shape arguments and print, nothing else. Everything
here is callable and testable without going through argparse.

The problem this solves is that an MCP client launches the server as a
subprocess, so it needs an absolute path to an entry point inside whichever
environment rage was installed in. That path is only reliably known from
inside that environment — which is where this code runs, and is why writing
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

from .errors import RageError
from .eventlog import DEFAULT as LOG_BESIDE_STORE
from .mounts import SPEC_DELIMITER, parse_spec
from .store import DB_FILENAME, DEFAULT_DIR_NAME

#: The name this server is registered under. Also the key that a re-run
#: replaces, which is what keeps unrelated servers in the file untouched.
SERVER_NAME = "rage"

#: Project scoped configuration, committed with the project and read by clients
#: from the project root.
PROJECT_CONFIG_NAME = ".mcp.json"

#: User scoped configuration, in the home directory. Holds a great deal besides
#: MCP servers, which is why nothing here rewrites more of it than one key.
USER_CONFIG_NAME = ".claude.json"

SERVERS_FIELD = "mcpServers"

SCOPES = ("project", "user")

#: Console script installed by this package, and the fallback for when it is
#: absent. ``python -m rage`` is equivalent, and works in an environment the
#: scripts directory of which is not where sys.executable lives.
SCRIPT_NAME = "rage-server"

_DEFAULT_INDENT = 2


class ConfigError(RageError, RuntimeError):
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


def launch_command(executable: str | os.PathLike[str] | None = None) -> list[str]:
    """Build the absolute command that starts the server.

    Prefers the console script beside the running interpreter, because it is
    what an install provides and it names the environment unambiguously. Falls
    back to ``<python> -m rage``, which is equivalent and cannot be missing: it
    needs only the interpreter that is already running and the package that is
    already imported.
    """
    python = Path(executable or sys.executable)
    for candidate in (python.parent / SCRIPT_NAME, python.parent / f"{SCRIPT_NAME}.exe"):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return [str(candidate)]
    return [str(python), "-m", "rage"]


def server_entry(
    directory: str | os.PathLike[str],
    command: list[str] | None = None,
    *,
    log: Any = None,
    log_content: str | None = None,
    root_mount: str | None = None,
    mounts: Sequence[str] = (),
    read_only_mounts: Sequence[str] = (),
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

    ``root_mount`` names the store answering for every key no mount claims, as
    a file inside the directory. Recorded only when it is not the default, so
    that an entry which never asked for one is not rewritten to say what it
    already meant.

    ``mounts`` are ``KEY=FILE`` specs, each recorded as a ``--mount``, and
    ``read_only_mounts`` the same specs recorded as ``--mount-ro``. They go
    through the same parse the server will do, so a misspelled mount point is
    refused while somebody is looking at the command that wrote it rather than
    at a client that silently failed to start a server. The file is written as
    given: it names a store inside ``--dir``, and resolving it here would put
    back the absolute path this shape exists to remove. A file that is not
    relative is refused by ``store_file`` when the server opens it.
    """
    argv = list(command) if command is not None else launch_command()
    args = [*argv[1:], "--dir", str(Path(directory).expanduser().resolve())]
    if root_mount is not None and root_mount != DB_FILENAME:
        args += ["--root-mount", root_mount]
    for flag, specs in (("--mount", mounts), ("--mount-ro", read_only_mounts)):
        for spec in specs:
            prefix, path = parse_spec(spec)
            args += [flag, f"{prefix}{SPEC_DELIMITER}{path}"]
    if log is not None:
        args.append("--log")
        # Absolute for the same reason the store directory is.
        if log is not LOG_BESIDE_STORE:
            args.append(str(Path(log).expanduser().resolve()))
        if log_content is not None:
            args += ["--log-content", log_content]
    return {"command": argv[0], "args": args}


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
        raise ConfigError(f"{path} is not valid JSON ({exc}); leaving it alone") from exc
    if not isinstance(loaded, dict):
        raise ConfigError(f"{path} does not hold a JSON object; leaving it alone")
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
        raise ConfigError(f"{path} has a {SERVERS_FIELD!r} that is not an object; leaving it alone")

    previous = servers.get(name)
    if previous is not None and not isinstance(previous, dict):
        raise ConfigError(f"{path} has a {name!r} server that is not an object; leaving it alone")

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
    "PROJECT_CONFIG_NAME",
    "SCOPES",
    "SERVERS_FIELD",
    "SERVER_NAME",
    "USER_CONFIG_NAME",
    "Change",
    "ConfigError",
    "config_path",
    "default_store_dir",
    "launch_command",
    "plan",
    "read_config",
    "server_entry",
    "write_config",
]
