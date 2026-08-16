"""Command line tool over the store library.

A thin wrapper, like the server: argument shaping and printing only. Anything
with behaviour belongs in :mod:`rage.store` or :mod:`rage.config`, so that it
can be tested without going through argparse and used by whichever of the two
front ends needs it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from . import __version__
from . import config as config_module
from .config import ConfigError


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
        "--dry-run",
        action="store_true",
        help="Report what would change without writing anything.",
    )
    config.set_defaults(handler=config_command)

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
    entry = config_module.server_entry(directory)

    change, merged, original = config_module.plan(path, args.scope, entry, name=args.name)
    _report(change, out, dry_run=args.dry_run)

    if change.writes and not args.dry_run:
        config_module.write_config(path, merged, original)
    return 0


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
    except ConfigError as exc:
        print(f"rage: {exc}", file=sys.stderr)
        return 1


__all__ = ["config_command", "main", "parse_args"]
