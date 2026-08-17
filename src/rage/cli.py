"""Command line tool over the store library.

A thin wrapper, like the server: argument shaping and printing only. Anything
with behaviour belongs in :mod:`rage.store` or :mod:`rage.config`, so that it
can be tested without going through argparse and used by whichever of the two
front ends needs it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TextIO

from . import __version__, eventlog, logread, store
from . import config as config_module
from .config import ConfigError
from .logread import LogError
from .store import BackupError


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="rage", description="Command line tool for the Rage document store"
    )
    parser.add_argument("--version", action="version", version=f"rage {__version__}")
    subcommands = parser.add_subparsers(dest="command", required=True)

    config = subcommands.add_parser(
        "config",
        help="write the MCP server configuration for a project or user",
        description=(
            "Register the rage MCP server, filling in the absolute path to this "
            "environment's entry point and to the store directory. Only the "
            "server's own entry is touched; anything else in the file is left "
            "as it was. Safe to re-run, which is how the configuration is "
            "repaired after the environment moves."
        ),
    )
    config.add_argument(
        "--scope",
        choices=config_module.SCOPES,
        default="project",
        help=(
            "Where to write: 'project' for .mcp.json in the project directory "
            "(default), 'user' for ~/.claude.json."
        ),
    )
    config.add_argument(
        "--project-dir",
        metavar="PATH",
        default=None,
        help="Project directory, for --scope project and the default store. Defaults to cwd.",
    )
    config.add_argument(
        "--dir",
        dest="directory",
        metavar="PATH",
        default=None,
        help=(
            "Store directory to record. Defaults to .rage in the project "
            "directory. Written absolute, since the server cannot be relied on "
            "to start in the project directory."
        ),
    )
    config.add_argument(
        "--path",
        dest="config_file",
        metavar="PATH",
        default=None,
        help="Configuration file to write, overriding the one implied by --scope.",
    )
    config.add_argument(
        "--name",
        default=config_module.SERVER_NAME,
        help=f"Name to register the server under (default: {config_module.SERVER_NAME}).",
    )
    config.add_argument(
        "--log",
        nargs="?",
        const=eventlog.DEFAULT,
        default=None,
        metavar="PATH",
        help=(
            "Record the server's requests and store accesses as JSON lines. "
            f"Without a path, writes {eventlog.DEFAULT_LOG_NAME} in the store "
            "directory. Omitted, and so off, unless asked for."
        ),
    )
    config.add_argument(
        "--log-content",
        dest="log_content",
        choices=eventlog.CONTENT_POLICIES,
        default=None,
        help="How much document text the log keeps. Only used alongside --log.",
    )
    config.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing anything.",
    )
    config.set_defaults(handler=config_command)

    backup = subcommands.add_parser(
        "backup",
        help="copy the store to a verified snapshot",
        description=(
            "Copy the database through SQLite itself and check what came out: "
            "an integrity check, the schema version, and a row count against "
            "the source. Copying the files instead is what this exists to "
            "avoid, since a store in WAL mode keeps recent writes in a sidecar "
            "and the copy left behind still opens cleanly."
        ),
    )
    backup.add_argument(
        "--dir",
        dest="directory",
        metavar="PATH",
        default=None,
        help=(
            f"Store directory to back up. Defaults to {store.ENV_DIR}, then "
            f"{store.DEFAULT_DIR_NAME} in the working directory."
        ),
    )
    backup.add_argument(
        "--to",
        dest="destination",
        metavar="PATH",
        default=None,
        help=(
            "Where to write, as a file or a directory. Defaults to a "
            f"timestamped name under {store.BACKUP_DIR_NAME}/ in the store "
            "directory."
        ),
    )
    backup.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the destination if it already exists.",
    )
    backup.add_argument(
        "--dry-run",
        action="store_true",
        help="Report where the backup would go without writing it.",
    )
    backup.set_defaults(handler=backup_command)

    log = subcommands.add_parser(
        "log",
        help="read back the event log",
        description=(
            "Show what the server was asked for and what it touched. Events are "
            "grouped by session, because one file holds more than one process "
            "and the sequence numbers restart with each of them. Only written "
            "when the server was configured with --log."
        ),
    )
    log.add_argument(
        "--dir",
        dest="directory",
        metavar="PATH",
        default=None,
        help=(
            f"Store directory the log sits beside. Defaults to {store.ENV_DIR}, "
            f"then {store.DEFAULT_DIR_NAME} in the working directory."
        ),
    )
    log.add_argument(
        "--path",
        metavar="PATH",
        default=None,
        help=(
            f"Log file to read, overriding {eventlog.ENV_LOG} and the default of "
            f"{eventlog.DEFAULT_LOG_NAME} in the store directory."
        ),
    )
    log.add_argument("--session", default=None, help="Only this session; a prefix is enough.")
    log.add_argument("--call", type=int, default=None, help="Only this call number.")
    log.add_argument("--op", default=None, help="Only this store operation, e.g. get_documents.")
    log.add_argument("--method", default=None, help="Only this MCP method, e.g. tools/call.")
    log.add_argument(
        "--event", default=None, help="Only this kind of event: start, request, notify or store."
    )
    log.add_argument("--key", default=None, help="Only events whose key contains this substring.")
    log.add_argument(
        "--errors", action="store_true", help="Only failures, raised or returned as an error."
    )
    log.add_argument(
        "--content",
        action="store_true",
        help="Show the document text the log kept, marking where it was cut.",
    )
    log.add_argument(
        "--summary",
        action="store_true",
        help=(
            "Report the numbers instead of the events: accesses per call, how "
            "often a read was truncated, and how often one was resumed."
        ),
    )
    log.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Print the matching records as they were written, one per line.",
    )
    log.add_argument(
        "--limit",
        type=int,
        default=50,
        metavar="N",
        help="Show at most the last N matching events. 0 for all. Default 50.",
    )
    log.set_defaults(handler=log_command)

    return parser.parse_args(argv)


def config_command(args: argparse.Namespace, out: TextIO) -> int:
    """Write, or report, the MCP server configuration."""
    project_dir = Path(args.project_dir).expanduser() if args.project_dir else None
    path = (
        Path(args.config_file).expanduser().resolve()
        if args.config_file
        else config_module.config_path(args.scope, project_dir)
    )
    directory = args.directory or config_module.default_store_dir(project_dir)
    entry = config_module.server_entry(directory, log=args.log, log_content=args.log_content)

    change, merged, original = config_module.plan(path, args.scope, entry, name=args.name)
    _report(change, out, dry_run=args.dry_run)

    if change.writes and not args.dry_run:
        config_module.write_config(path, merged, original)
    return 0


def backup_command(args: argparse.Namespace, out: TextIO) -> int:
    """Snapshot the store, or say where the snapshot would go."""
    directory = store.resolve_directory(args.directory)
    if not (directory / store.DB_FILENAME).exists():
        # Opening one would create it, and backing up a store the caller never
        # had is a success that answers the wrong question.
        raise BackupError(f"no store in {directory}")

    with store.open_store(directory) as opened:
        if args.dry_run:
            target = opened.backup_path(args.destination, overwrite=args.overwrite)
            print(f"would back up {opened.path} to {target}", file=out)
            return 0

        result = opened.backup(args.destination, overwrite=args.overwrite)

    print(f"backed up {directory / store.DB_FILENAME} to {result.path}", file=out)
    print(
        f"  {result.documents} documents, {result.bytes} bytes, integrity {result.integrity}",
        file=out,
    )
    return 0


def log_command(args: argparse.Namespace, out: TextIO) -> int:
    """Show the event log, or the numbers over it."""
    log = logread.read_log(_log_path(args))
    selected = logread.Filter(
        session=args.session,
        call=args.call,
        op=args.op,
        method=args.method,
        event=args.event,
        key=args.key,
        errors=args.errors,
    ).select(log.events)

    if args.summary:
        for line in logread.format_summary(logread.summarise(log, selected)):
            print(line, file=out)
        return 0

    shown, dropped = _limited(selected, args.limit)
    if args.as_json:
        for event in shown:
            print(json.dumps(event.record, ensure_ascii=False), file=out)
        return 0

    if dropped:
        print(f"({dropped} earlier matching events not shown; --limit 0 for all)", file=out)
    for session in logread.sessions(shown):
        # The header is not decoration: it is what says which process the
        # sequence numbers below it belong to.
        print(f"\nsession {logread.format_session(session)}", file=out)
        for event in session.events:
            for line in logread.format_event(event, content=args.content):
                print(line, file=out)
    if not shown:
        print(f"no matching events in {log.path}", file=out)
    if log.malformed:
        print(f"\n{len(log.malformed)} unparseable lines skipped", file=out)
    return 0


def _log_path(args: argparse.Namespace) -> Path:
    """Locate the log: --path, then the environment, then beside the store.

    The last step is the reader's own, not ``eventlog.resolve_path``'s: for the
    writer there is no default location because the default is not to log at
    all, but a reader given nothing is being asked about the log this project
    would have written.
    """
    directory = store.resolve_directory(args.directory)
    return eventlog.resolve_path(args.path, directory) or directory / eventlog.DEFAULT_LOG_NAME


def _limited(events: list[logread.Event], limit: int) -> tuple[list[logread.Event], int]:
    """Keep the last ``limit`` events, since a log is usually read from its end."""
    if limit <= 0 or len(events) <= limit:
        return events, 0
    return events[-limit:], len(events) - limit


def _report(change: config_module.Change, out: TextIO, *, dry_run: bool) -> None:
    """Say what is about to change, in enough detail to notice a wrong answer.

    The whole command is a guess at two paths, so printing them is not a
    courtesy: an entry point in the wrong environment or a store directory
    beside the wrong project both produce a server that starts cleanly and
    talks to nothing anyone meant.
    """
    verb = {
        "created": "would add" if dry_run else "added",
        "updated": "would update" if dry_run else "updated",
        "unchanged": "already current",
    }[change.action]

    print(f"{change.scope} configuration: {change.path}", file=out)
    print(f"  {change.name}: {verb}", file=out)
    if change.previous is not None and change.action == "updated":
        _print_command("  was:", change.previous, out)
    _print_command("  now:" if change.action == "updated" else "  ", change.entry, out)


def _print_command(label: str, entry: dict[str, object], out: TextIO) -> None:
    command = " ".join([str(entry.get("command", ""))] + [str(a) for a in entry.get("args", [])])
    print(f"{label} {command}".rstrip(), file=out)


def main(argv: list[str] | None = None, out: TextIO | None = None) -> int:
    args = parse_args(argv)
    try:
        return args.handler(args, out or sys.stdout)
    except (ConfigError, BackupError, LogError) as exc:
        print(f"rage: {exc}", file=sys.stderr)
        return 1


__all__ = ["backup_command", "config_command", "log_command", "main", "parse_args"]
