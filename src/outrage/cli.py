"""Command line tool over the store library.

A thin wrapper, like the server: argument shaping and printing only. Anything
with behaviour belongs in :mod:`outrage.store` or :mod:`outrage.config`, so that it
can be tested without going through argparse and used by whichever of the two
front ends needs it.

What this module *offers* is three names: :func:`main`, :func:`parse_args`,
and :class:`ConflictingSourceError` as something to catch. The subcommand handlers
are argparse wiring reached through ``handler``, one per subcommand and never
from outside, so they are private -- which also keeps this page from being a
list of twelve near-identical ``(args, out) -> int`` entries in place of an
orientation. The interface people actually use here is the command line, and
``outrage --help`` is what states it.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import TextIO

from . import __version__, bulk, eventlog, install, keys, logread, maintenance, messages, store
from . import config as config_module
from .errors import OutrageError


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """The whole command line, and the handler each subcommand dispatches to.

    Every subcommand sets ``handler``, so :func:`main` dispatches without a
    branch per command and this function is the only place the shape of the
    command line is written down. Separate from :func:`main` so that a test can
    ask what an argument list parses to without running anything.
    """
    parser = argparse.ArgumentParser(
        prog="outrage", description="Command line tool for the Outrage document store"
    )
    parser.add_argument("--version", action="version", version=f"outrage {__version__}")
    subcommands = parser.add_subparsers(dest="command", required=True)

    init = subcommands.add_parser(
        "init",
        help="set a project up: MCP server, session hooks, skill and agents",
        description=(
            "Arrange everything a project needs to use outrage: the MCP server "
            "entry in .mcp.json, a session-start hook for each harness - "
            ".claude/settings.json for Claude Code and .github/hooks/outrage.json "
            "for Copilot CLI - and the packaged skill and agents in .claude/. "
            "Only the entries outrage owns are written; anything else in those "
            "files is left as it was, and a file already holding the current "
            "content is not rewritten. An option already on an existing server "
            "entry - a mount, --log - is kept even when this run does not "
            "mention it. Safe to re-run, which is how a project is repaired "
            "after outrage is upgraded or the environment moves."
        ),
    )
    init.add_argument(
        "--project-dir",
        metavar="PATH",
        default=None,
        help="Project directory to set up, and the default store location. Defaults to cwd.",
    )
    init.add_argument(
        "--dir",
        dest="directory",
        metavar="PATH",
        default=None,
        help=(
            "Store directory to record. Defaults to .outrage in the project "
            "directory. Written absolute, since the server cannot be relied on "
            "to start in the project directory."
        ),
    )
    # The same options config takes, because init calls config to write the
    # entry: without them a re-run of init would quietly drop the mounts
    # somebody had configured, exactly as it once would have dropped logging.
    _mount_options(init, "Set a")
    _log_options(init)
    init.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing anything.",
    )
    init.set_defaults(handler=_init_command)

    config = subcommands.add_parser(
        "config",
        help="write the MCP server configuration for a project or user",
        description=(
            "Register the outrage MCP server, filling in the absolute path to this "
            "environment's entry point and to the store directory. Only the "
            "server's own entry is touched; anything else in the file is left "
            "as it was. Options already on that entry are kept unless this run "
            "names the same one, so a re-run cannot silently drop mounts or "
            "logging - which also means removing one is an edit to the file. "
            "Safe to re-run, which is how the configuration is "
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
            "Store directory to record. Defaults to .outrage in the project "
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
    _mount_options(config, "Record a")
    _log_options(config)
    config.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing anything.",
    )
    config.set_defaults(handler=_config_command)

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
    # The shared spelling, so that backing up the store a command just wrote to
    # is the same two arguments that named it. A directory holds several
    # stores, and a backup of the wrong one is the kind of success nobody reads
    # twice.
    _store_option(backup)
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
    backup.set_defaults(handler=_backup_command)

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
    log.set_defaults(handler=_log_command)

    get = subcommands.add_parser(
        "get",
        help="print the document stored at a key",
        description=(
            "Read a key and print its content. Metadata is a key like any "
            "other, so `outrage get notes/x/!title` prints the title. The whole "
            "document is printed by default: the tool's own read truncates at "
            "a cap and hands back a continuation offset, which is right for an "
            "agent's context window and wrong for a person redirecting a "
            "document to a file. Ask for a slice and you get exactly the slice."
        ),
    )
    _store_option(get)
    get.add_argument(
        "key",
        help=(
            "Key to read, e.g. context/1/task, context/1/task/!title, or "
            "context/?last/task for the newest."
        ),
    )
    get.add_argument("--offset", type=int, default=0, help="Character offset to start at.")
    get.add_argument("--length", type=int, default=None, help="Characters to return.")
    get.add_argument("--pattern", default=None, help="Literal substring to start the read from.")
    get.add_argument(
        "--occurrence",
        type=int,
        default=0,
        help="Which appearance of --pattern to use, 0 being the first.",
    )
    get.add_argument(
        "--max-chars",
        dest="max_chars",
        type=int,
        default=None,
        help=(
            "Cap the read at this many characters, which turns off reading to "
            f"the end. Matches the tool's own cap at {store.DEFAULT_MAX_CHARS}."
        ),
    )
    get.set_defaults(handler=_get_command)

    set_ = subcommands.add_parser(
        "set",
        help="store a document, from a file or from standard input",
        description=(
            "Write content to a key, overwriting whatever is there. Content "
            "comes from standard input unless --file or --content is given, so "
            "a document can be piped in. A `?` segment in the key is replaced "
            "by a number the store allocates, and the key actually written is "
            "printed - which is the only way to learn the allocated number."
        ),
    )
    _store_option(set_)
    set_.add_argument(
        "key",
        help=(
            "Key to write, e.g. notes/thing, notes/? to allocate a number, or "
            "context/?last/task for the newest."
        ),
    )
    set_.add_argument("--content", default=None, help="Content, instead of reading it in.")
    set_.add_argument("--file", default=None, metavar="PATH", help="Read the content from a file.")
    set_.add_argument(
        "--title",
        default=None,
        help=(
            "Title to store alongside, as the key's !title metadata. What "
            "later surveys find the document by. Not allowed on a metadata key."
        ),
    )
    set_.add_argument(
        "--format",
        dest="format",
        choices=store.FORMATS,
        default=None,
        help="Detected from the content when omitted.",
    )
    set_.set_defaults(handler=_set_command)

    ls = subcommands.add_parser(
        "ls",
        help="list the keys immediately below a key",
        description=(
            "List one level. Includes documents, metadata, and keys that exist "
            "only because something beneath them does - a container holds "
            "nothing itself and cannot be read, which is why listing and "
            "reading disagree about whether it is there."
        ),
    )
    _store_option(ls)
    ls.add_argument(
        "key",
        nargs="?",
        default=None,
        help="Key to list below, ?last for the newest. Omit for the top.",
    )
    ls.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Descend the whole subtree rather than one level.",
    )
    _limit_option(ls, "keys")
    ls.set_defaults(handler=_ls_command)

    dump = subcommands.add_parser(
        "dump",
        help="print every document at and below a key",
        description=(
            "Read a subtree. With --meta the result holds that metadata "
            "instead of the documents, which is how the titles of everything "
            "under a key are surveyed in one pass. Every document is printed "
            "whole by default, as `outrage get` does and for the same reason: "
            "`outrage dump > file` is an export, and an export that quietly holds "
            "back part of a document is one nothing downstream can tell from a "
            "complete one. Pass --max-chars to cap each document for a skim; a "
            "capped one is then marked with what it held."
        ),
    )
    _store_option(dump)
    dump.add_argument("key", nargs="?", default=None, help="Key whose subtree to read.")
    dump.add_argument(
        "--meta",
        dest="meta_name",
        action="append",
        default=None,
        metavar="NAME",
        help="Return this metadata instead of documents. Repeatable.",
    )
    dump.add_argument("--depth", type=int, default=None, help="Levels below key to descend.")
    dump.add_argument(
        "--max-chars",
        dest="max_chars",
        type=int,
        default=None,
        help=(
            "Cap each document at this many characters, which turns off "
            "printing them whole. Matches the tool's own bulk cap at "
            f"{store.DEFAULT_BULK_MAX_CHARS}."
        ),
    )
    _limit_option(dump, "documents")
    dump.set_defaults(handler=_dump_command)

    export = subcommands.add_parser(
        "export",
        help="write a subtree out as a directory of files",
        description=(
            "Export documents to files, one file per document: a key segment "
            "is a directory, and the last one is a file with an extension "
            "naming its format. The extension is what lets a key be both a "
            "document and a container, since a path cannot be both a file and "
            "a directory. Metadata is a segment like any other, so a title is "
            "exported as the file !title.md beside its document's directory. "
            "Paths are written from the top of the key namespace rather than "
            "from the key asked for, so an export of a subtree imports back to "
            "where it came from. This is not a backup: it carries the "
            "documents and nothing the database holds about them, and `outrage "
            "backup` is the copy that keeps the rest."
        ),
    )
    _store_option(export)
    export.add_argument(
        "target", metavar="DIRECTORY", help="Directory to write into. Created if missing."
    )
    export.add_argument("key", nargs="?", default=None, help="Key whose subtree to export.")
    _conflict_option(export, "A file already there is")
    export.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be written without writing it.",
    )
    export.set_defaults(handler=_export_command)

    import_ = subcommands.add_parser(
        "import",
        help="store a directory of files as documents",
        description=(
            "Import files as documents, inverting `outrage export`: a path "
            "becomes a key, and a .md or .json extension is stripped and read "
            "as the format. Any other name is kept whole, so a file at "
            "src/myfile.py is stored at the key src/myfile.py. Nothing already "
            "stored is replaced unless --on-conflict says so. There is no mode "
            "that refuses the whole import unless every key is free: a "
            "directory could be walked twice to promise that and a stream "
            "could not, and --dry-run answers the same question without "
            "promising anything it might later have to take back."
        ),
    )
    _store_option(import_)
    import_.add_argument(
        "source", metavar="DIRECTORY", help="Directory to read documents from."
    )
    import_.add_argument(
        "key",
        nargs="?",
        default=None,
        help="Key prefix to store beneath. The top level by default.",
    )
    _conflict_option(import_, "A key already holding a document is")
    import_.add_argument(
        "--hidden",
        action="store_true",
        help="Include files and directories whose name begins with a dot.",
    )
    import_.add_argument(
        "--dry-run", action="store_true", help="Report what would be stored without storing it."
    )
    import_.set_defaults(handler=_import_command)

    pack = subcommands.add_parser(
        "pack",
        help="build a read-only parquet store from a tree or another store",
        description=(
            "Write a parquet store: one file, sorted by key, holding a whole "
            "corpus. Parquet is read-only here -- it is not updated in place, "
            "so there is no import that adds to one -- and this is the way "
            "documents get in. The source is either a directory of files, "
            "mapped to keys exactly as `outrage import` maps them, or an existing "
            "store, whose documents, metadata and timestamps all come across; "
            "the second is how a reference base is usually made, by "
            "accumulating into a SQLite store and compacting it afterwards. "
            "Nothing is written until the whole file is, so an interrupted "
            "pack leaves no store behind and the report says `read` rather "
            "than `wrote`. Mount the result with the server's --mount-ro, or "
            "read it directly with --store."
        ),
    )
    pack.add_argument(
        "target", metavar="FILE", help="Parquet file to write. Created, with its parents."
    )
    source = pack.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--from-dir", metavar="DIRECTORY", default=None, help="Directory of files to pack."
    )
    source.add_argument(
        "--from-store",
        metavar="FILE",
        default=None,
        help=(
            "A store in --dir to pack, as a file relative to it. Any backend, "
            "so a parquet store can be repacked to a later format this way."
        ),
    )
    pack.add_argument(
        "--dir",
        dest="directory",
        metavar="PATH",
        default=None,
        help=(
            f"Store directory --from-store is read from. Defaults to "
            f"{store.ENV_DIR}, then {store.DEFAULT_DIR_NAME} in the working "
            f"directory."
        ),
    )
    pack.add_argument(
        "key",
        nargs="?",
        default=None,
        help=(
            "Key prefix. Documents are stored beneath it when packing a "
            "directory, and the subtree packed when packing a store."
        ),
    )
    pack.add_argument(
        "--hidden",
        action="store_true",
        help="Include files and directories whose name begins with a dot.",
    )
    pack.add_argument(
        "--overwrite", action="store_true", help="Replace the target if it is already there."
    )
    pack.add_argument(
        "--dry-run", action="store_true", help="Report what would be packed without writing it."
    )
    pack.set_defaults(handler=_pack_command)

    rm = subcommands.add_parser(
        "rm",
        help="delete a key",
        description=(
            "Delete a key and the metadata attached to it. Descendants survive "
            "unless --recursive is given, so a mistyped key cannot silently "
            "discard a subtree; what was left behind is reported either way."
        ),
    )
    _store_option(rm)
    rm.add_argument("key", help="Key to delete, ?last for the newest.")
    rm.add_argument(
        "--recursive", "-r", action="store_true", help="Also delete everything beneath the key."
    )
    rm.add_argument(
        "--dry-run", action="store_true", help="Report what would go without deleting it."
    )
    _limit_option(rm, "keys previewed by --dry-run")
    rm.set_defaults(handler=_rm_command)

    check = subcommands.add_parser(
        "check",
        help="check the store, and optionally repair it",
        description=(
            "Ask whether the store is sound: the row invariants and the format "
            "version, which every backend answers, and then whatever the "
            "backend under it can say about its own storage. For SQLite that "
            "is its own integrity check and how much of the store is sitting "
            "in the write-ahead log rather than in the database -- invisible "
            "in normal use, and what makes a copy of the database file alone "
            "lose recent writes. For parquet it is whether the file is still "
            "in the sort order every read of it bisects."
        ),
    )
    _store_option(check)
    check.add_argument(
        "--repair",
        action="store_true",
        help=(
            "Fix what the check found and the backend can act on: for SQLite, "
            "fold the write-ahead log back into the database and compact it. "
            "No repair changes a document, and a backend with nothing a repair "
            "could move says so rather than claiming to have acted."
        ),
    )
    check.set_defaults(handler=_check_command)

    return parser.parse_args(argv)


def _limit_option(parser: argparse.ArgumentParser, what: str) -> None:
    """Add ``--limit``, which shows less rather than fetching less.

    The command line pages the store internally and always reads to the end,
    so this is a display bound and nothing else: the user asks to see less and
    is told when they got it. Nobody ever gets less by accident, which is the
    opposite default to the tools and for the opposite reason - a redirect into
    a file is an export.
    """
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help=f"Show at most N {what}, and say so on stderr. Everything by default.",
    )


def _conflict_option(parser: argparse.ArgumentParser, what: str) -> None:
    """What to do about something already at the far end, spelled once.

    Per item rather than for the run as a whole, which is the only promise a
    stream can keep: 'stop' stops at the first conflict and says what it had
    already done, rather than claiming an all-or-nothing it would have to
    abandon the moment the source stopped being a directory it can pre-walk.
    """
    parser.add_argument(
        "--on-conflict",
        dest="on_conflict",
        choices=bulk.CONFLICTS,
        default=bulk.SKIP,
        help=(
            f"{what} left alone (skip, the default), replaced (overwrite), or "
            f"stops the run where it stands (stop)."
        ),
    )


def _log_options(parser: argparse.ArgumentParser) -> None:
    """Whether the server logs, spelled the same way wherever an entry is written."""
    parser.add_argument(
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
    parser.add_argument(
        "--log-content",
        dest="log_content",
        choices=eventlog.CONTENT_POLICIES,
        default=None,
        help="How much document text the log keeps. Only used alongside --log.",
    )


def _mount_options(parser: argparse.ArgumentParser, verb: str) -> None:
    """The stores a server entry records, spelled the same way on init and config.

    Every one of them is a file inside the store directory, so this is the one
    place that has to say so.
    """
    parser.add_argument(
        "--root-mount",
        dest="root_mount",
        metavar="FILE",
        default=None,
        help=(
            f"{verb} --root-mount for the server: the store answering for every "
            f"key no mount claims, as a file inside --dir (default: "
            f"{store.default_store_file()}). Written only when it is not the default."
        ),
    )
    parser.add_argument(
        "--mount",
        dest="mounts",
        action="append",
        default=[],
        metavar="KEY=FILE",
        help=(
            f"{verb} --mount for the server: another store under KEY, as in "
            "ref=reference.sqlite. FILE is relative to --dir, like "
            "--root-mount. Repeatable, and refused here if the mount point is "
            "not a valid key."
        ),
    )
    parser.add_argument(
        "--mount-ro",
        dest="read_only_mounts",
        action="append",
        default=[],
        metavar="KEY=FILE",
        help=(
            f"{verb} --mount-ro for the server: as --mount, but the server "
            "refuses every write routed there. Repeatable."
        ),
    )


def _store_option(parser: argparse.ArgumentParser) -> None:
    """Which store to act on, spelled the same way on every subcommand.

    Two arguments, because a store is a *file inside* a directory: the
    directory is shared -- the log and the backups sit in it - and the file
    says which of the stores in it this command means. The server spells the
    same pair ``--dir`` and ``--root-mount``.
    """
    parser.add_argument(
        "--dir",
        dest="directory",
        metavar="PATH",
        default=None,
        help=(
            f"Store directory. Defaults to {store.ENV_DIR}, then "
            f"{store.DEFAULT_DIR_NAME} in the working directory."
        ),
    )
    parser.add_argument(
        "--store",
        dest="filename",
        metavar="FILE",
        default=store.default_store_file(),
        help=(
            f"Which store in that directory, as a file relative to it "
            f"(default: {store.default_store_file()}). The server's --mount and "
            f"--root-mount name stores the same way."
        ),
    )


def _init_command(args: argparse.Namespace, out: TextIO) -> int:
    """Set a project up, or say what setting it up would change."""
    project = Path(args.project_dir).expanduser() if args.project_dir else Path.cwd()
    done = install.init(
        project,
        args.directory,
        log=args.log,
        log_content=args.log_content,
        root_mount=args.root_mount,
        mounts=args.mounts,
        read_only_mounts=args.read_only_mounts,
        dry_run=args.dry_run,
    )

    _report(done.server, out, dry_run=args.dry_run)
    for hook in done.hooks:
        _report_hook(hook, out, dry_run=args.dry_run)
    _report_assets(
        done.assets,
        out,
        dry_run=args.dry_run,
        root=done.project_dir / install.CLAUDE_DIR,
        label="skill and agents",
    )
    _report_assets(
        done.codex_assets,
        out,
        dry_run=args.dry_run,
        root=done.project_dir / install.CODEX_DIR,
        label="Codex skill",
    )

    if args.dry_run and done.writes:
        # Where the report is long enough to scroll, one line on stderr is what
        # says the run did nothing after the reader has stopped reading.
        print("outrage: dry run, nothing changed", file=sys.stderr)
    return 0


def _config_command(args: argparse.Namespace, out: TextIO) -> int:
    """Write, or report, the MCP server configuration."""
    project_dir = Path(args.project_dir).expanduser() if args.project_dir else None
    path = (
        Path(args.config_file).expanduser().resolve()
        if args.config_file
        else config_module.config_path(args.scope, project_dir)
    )
    directory = args.directory or config_module.default_store_dir(project_dir)
    entry = config_module.server_entry(
        directory,
        log=args.log,
        log_content=args.log_content,
        root_mount=args.root_mount,
        mounts=args.mounts,
        read_only_mounts=args.read_only_mounts,
    )

    change, merged, original = config_module.plan(path, args.scope, entry, name=args.name)
    _report(change, out, dry_run=args.dry_run)

    if change.writes and not args.dry_run:
        config_module.write_config(path, merged, original)
    return 0


def _backup_command(args: argparse.Namespace, out: TextIO) -> int:
    """Snapshot the store, or say where the snapshot would go."""
    directory = store.resolve_directory(args.directory)
    database = store.store_file(directory, args.filename)
    if not database.exists():
        # Opening one would create it, and backing up a store the caller never
        # had is a success that answers the wrong question.
        raise store.BackupError("check-no-store", path=str(database))

    with store.open_store(directory, filename=args.filename) as opened:
        if args.dry_run:
            target = opened.backup_path(args.destination, overwrite=args.overwrite)
            print(f"would back up {opened.path} to {target}", file=out)
            return 0

        result = opened.backup(args.destination, overwrite=args.overwrite)

    print(f"backed up {database} to {result.path}", file=out)
    print(
        f"  {result.documents} documents, {result.bytes} bytes, integrity {result.integrity}",
        file=out,
    )
    return 0


def _log_command(args: argparse.Namespace, out: TextIO) -> int:
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


def _resolved(opened: store.Store, args: argparse.Namespace) -> None:
    """Replace a ``?last`` in ``args.key`` with the key it names, and say so.

    Rebinds the argument rather than returning a value: a command uses its key
    to read with and again in what it prints when there was nothing there, and
    a resolution that reached only half of those would report the question
    instead of the answer.

    The note goes to stderr, and only when a ``?last`` was actually asked for,
    so a report piped onward is unchanged and an ordinary key costs no line.
    Said at all for the reason a ``?`` reports the number it allocated: reading
    the wrong document is the one outcome the caller cannot see happening.
    """
    if args.key is None or keys.LAST not in args.key.split(keys.DELIMITER):
        return
    args.key = keys.resolve_last(args.key, opened.last_child)
    print(f"outrage: {keys.LAST} is {keys.displayed(args.key)}", file=sys.stderr)


def _get_command(args: argparse.Namespace, out: TextIO) -> int:
    """Print a document, whole unless a slice was asked for."""
    with _open_existing(args) as opened:
        _resolved(opened, args)
        slicing = {
            "offset": args.offset,
            "length": args.length,
            "pattern": args.pattern,
            "occurrence": args.occurrence,
        }
        if args.max_chars is None:
            excerpt = store.read_all(opened, args.key, **slicing)
        else:
            excerpt = opened.retrieve_document(args.key, max_chars=args.max_chars, **slicing)

    # No trailing newline of our own: the content is the output, and a document
    # round-tripped through `outrage get > f` and `outrage set < f` has to come back
    # the same length it went in.
    out.write(excerpt.content)
    if excerpt.truncated:
        print(
            f"\noutrage: {excerpt.returned} of {excerpt.total} characters; "
            f"more from --offset {excerpt.next_offset}",
            file=sys.stderr,
        )
    return 0


def _set_command(args: argparse.Namespace, out: TextIO) -> int:
    """Write a document from an argument, a file, or standard input."""
    content = _content(args)
    directory = store.resolve_directory(args.directory)
    with store.open_store(directory, filename=args.filename) as opened:
        _resolved(opened, args)
        written = opened.store_document(args.key, content, args.format, title=args.title)

    # The resolved directory, not the one asked for: a mistyped --dir creates a
    # store rather than failing, so the only defence is saying where it went.
    print(
        f"{keys.displayed(written)}  {len(content)} characters in "
        f"{store.store_file(directory, args.filename)}",
        file=out,
    )
    return 0


def _content(args: argparse.Namespace) -> str:
    """Content from --content, --file, or standard input, in that order."""
    if args.content is not None and args.file is not None:
        raise ConflictingSourceError("content-two-sources")
    if args.content is not None:
        return args.content
    if args.file is not None:
        path = Path(args.file).expanduser()
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConflictingSourceError(
                "content-unreadable", path=str(path), reason=str(exc)
            ) from exc
    if sys.stdin.isatty():
        # Otherwise the command hangs on an empty terminal looking like it
        # worked, and the store ends up with an empty document at a good key.
        raise ConflictingSourceError("content-missing")
    return sys.stdin.read()


class ConflictingSourceError(OutrageError):
    """Raised when the content to store cannot be determined from the arguments."""


def _ls_command(args: argparse.Namespace, out: TextIO) -> int:
    """List one level, or the whole subtree, printing as it goes."""
    shown = 0
    with _open_existing(args) as opened:
        _resolved(opened, args)
        entries = bulk.walk(opened, args.key) if args.recursive else bulk.levels(opened, args.key)
        for entry in entries:
            if args.limit is not None and shown >= args.limit:
                # On stderr, so a listing piped into something else is not
                # corrupted by a note about itself.
                print(f"outrage: stopped at --limit {args.limit}", file=sys.stderr)
                break
            size = "-" if entry.size is None else str(entry.size)
            print(
                f"{entry.kind:<9} {size:>8}  {entry.updated_at or '-':<20}  {entry.key}", file=out
            )
            shown += 1

    if not shown:
        print(f"nothing below {args.key or 'the top level'}", file=out)
    return 0


def _dump_command(args: argparse.Namespace, out: TextIO) -> int:
    """Print a subtree, one document at a time, as each one arrives."""
    shown = 0
    with _open_existing(args) as opened:
        _resolved(opened, args)
        for excerpt in _documents(opened, args):
            if args.limit is not None and shown >= args.limit:
                print(f"outrage: stopped at --limit {args.limit}", file=sys.stderr)
                break
            header = f"=== {keys.displayed(excerpt.key)}"
            if excerpt.truncated:
                # Named on the line above the content, so that a reader sees it
                # before reading rather than after acting on half a document.
                header += f"  [{excerpt.returned} of {excerpt.total} characters]"
            print(header, file=out)
            print(excerpt.content, file=out)
            shown += 1

    if not shown:
        print(f"nothing at or below {args.key or 'the top level'}", file=out)
    return 0


def _documents(opened: store.Store, args: argparse.Namespace) -> Iterator[store.Excerpt]:
    """The subtree, a page at a time, each document whole unless capped.

    Yielded as they arrive rather than collected first. An export that holds
    every document in memory before writing any stops working at exactly the
    size an export matters at, and it fails worse when it does: an interrupted
    stream has already written what it reached.
    """
    cursor = None
    while True:
        page = opened.get_documents(
            store.BoundedSubtree(args.key, args.depth),
            meta_name=args.meta_name,
            max_chars=args.max_chars or store.DEFAULT_BULK_MAX_CHARS,
            limit=bulk.PAGE,
            cursor=cursor,
        )
        for found in page.items:
            # Only the ones that came back short are read again, so the common
            # document costs one query. Deliberately not pushed down into
            # get_documents: reading a whole subtree to the end is the call the
            # scale requirement exists to keep out of the library, and the
            # command line is the one caller that legitimately wants it.
            if args.max_chars is None and found.truncated:
                yield store.read_all(opened, found.key)
            else:
                yield found
        if page.next_cursor is None:
            return
        cursor = page.next_cursor


def _export_command(args: argparse.Namespace, out: TextIO) -> int:
    """Write a subtree out as files, reporting each document as it lands."""
    with _open_existing(args) as opened:
        _resolved(opened, args)
        transfers = bulk.export_tree(
            opened,
            args.key,
            args.target,
            on_conflict=args.on_conflict,
            dry_run=args.dry_run,
        )
        return _report_transfers(transfers, args, out, source_first=False)


def _import_command(args: argparse.Namespace, out: TextIO) -> int:
    """Store a directory of files, reporting each file as it goes in."""
    # Creating rather than refusing, for the reason `set` does: a first write
    # has to be able to make the store it writes to, and seeding an empty one
    # from a directory is that write in bulk. The resolved path is printed for
    # the same reason too - it is the only thing that makes a mistyped --dir
    # visible rather than silently successful.
    directory = store.resolve_directory(args.directory)
    with store.open_store(directory, filename=args.filename) as opened:
        _resolved(opened, args)
        transfers = bulk.import_tree(
            opened,
            args.source,
            args.key,
            on_conflict=args.on_conflict,
            dry_run=args.dry_run,
            hidden=args.hidden,
        )
        status = _report_transfers(transfers, args, out, source_first=True)
    print(f"outrage: into {store.store_file(directory, args.filename)}", file=sys.stderr)
    return status


def _report_transfers(
    transfers: Iterator[bulk.Transfer],
    args: argparse.Namespace,
    out: TextIO,
    *,
    source_first: bool,
) -> int:
    """Print one line per document as it crosses, then a count, and say how it went.

    A line at a time rather than a summary at the end, because the operation
    streams: what has been reported is what has actually happened, so an
    interrupted run leaves a true record rather than none. The counts go to
    stderr, so a report piped onward is not corrupted by a note about itself.
    """
    counted: dict[str, int] = {}
    for transfer in transfers:
        counted[transfer.action] = counted.get(transfer.action, 0) + 1
        # `-` means there is no key or no path -- a file that mapped to no key,
        # a key that mapped to no file. The root is a key, so it is spelled
        # rather than blanked: `key or "-"` would report it as absent.
        left = "-" if transfer.key is None else keys.displayed(transfer.key)
        right = transfer.path or "-"
        if source_first:
            left, right = right, left
        line = f"{_verb(transfer.action, args.dry_run):<11} {left}  ->  {right}"
        if transfer.reason is not None:
            line += f"  ({transfer.reason})"
        print(line, file=out)

    if not counted:
        print("nothing to transfer", file=out)
    else:
        counts = ", ".join(f"{count} {_NOUNS[action]}" for action, count in counted.items())
        prefix = "dry run, nothing changed: " if args.dry_run else ""
        print(f"outrage: {prefix}{counts}", file=sys.stderr)
    # A run that stopped or failed is not a run that worked, and the exit
    # status is the only part of that a script can see.
    return 1 if counted.get(bulk.FAILED) or counted.get(bulk.STOPPED) else 0


#: What to call each action when counting them up, as against when reporting
#: one as it happens: "5 written" rather than "5 wrote".
_NOUNS = {
    bulk.READ: "packed",
    bulk.WROTE: "written",
    bulk.SKIPPED: "skipped",
    bulk.FAILED: "failed",
    bulk.STOPPED: "stopped",
}


def _verb(action: str, dry_run: bool) -> str:
    """What to call an action that a dry run did not take."""
    if not dry_run:
        return action
    return {
        bulk.WROTE: "would write",
        bulk.READ: "would pack",
        bulk.SKIPPED: "would skip",
        bulk.STOPPED: "would stop",
    }.get(
        action, action
    )


def _pack_command(args: argparse.Namespace, out: TextIO) -> int:
    """Build a parquet store from a directory or from another store.

    The two sources differ in one thing worth naming: packing a store keeps
    each document's ``updated_at`` and packing a tree cannot, because a file's
    modification time is not the store's timestamp for a document. So a pack of
    a store is a compaction and a pack of a tree is an import that happens to
    land in parquet.
    """
    target = Path(args.target).expanduser()
    if args.from_store is not None:
        with _open_existing(argparse.Namespace(
            directory=args.directory, filename=args.from_store
        )) as opened:
            _resolved(opened, args)
            status = _report_transfers(
                bulk.pack(
                    target,
                    bulk.documents_from_store(opened, args.key),
                    overwrite=args.overwrite,
                    dry_run=args.dry_run,
                ),
                args,
                out,
                source_first=False,
            )
    else:
        status = _report_transfers(
            bulk.pack(
                target,
                bulk.documents_from_tree(args.from_dir, args.key, hidden=args.hidden),
                overwrite=args.overwrite,
                dry_run=args.dry_run,
            ),
            args,
            out,
            source_first=True,
        )
    if not args.dry_run and status == 0:
        # The one line that says the file exists, since every line above it
        # said only that a document was read. To stderr with the counts, so a
        # report piped onward is still just the documents.
        print(f"outrage: packed into {target}", file=sys.stderr)
    return status


def _rm_command(args: argparse.Namespace, out: TextIO) -> int:
    """Delete a key, saying what went and what stayed."""
    with _open_existing(args) as opened:
        _resolved(opened, args)
        beneath = opened.descendant_count(args.key)
        if args.dry_run:
            # Asking the store rather than predicting: a dry run that computes
            # its own answer is one that can disagree with what it previews.
            print(f"would delete {keys.displayed(args.key)}", file=out)
            if args.recursive:
                # The whole subtree, not one level of it: a preview that shows
                # the first level of a deletion reaching five is not a preview
                # of what --recursive takes.
                #
                # And counted the same way it is walked. `beneath` reports what
                # a plain delete would *keep*, so it leaves out the key's own
                # metadata unit -- which this walk reports, because a recursive
                # delete takes it. Subtracting one from the other said "and 1
                # more" where three were left, and went negative once the limit
                # reached past the ordinary children.
                taken = opened.descendant_count(args.key, whole_subtree=True)
                previewed = 0
                for entry in bulk.walk(opened, args.key):
                    if args.limit is not None and previewed >= args.limit:
                        print(f"  and {taken - previewed} more", file=out)
                        break
                    print(f"  and below: {entry.key}", file=out)
                    previewed += 1
            _report_remainder(args, beneath, out, dry_run=True)
            return 0

        removed = opened.delete(args.key, recursive=args.recursive)

    for key in removed:
        print(f"deleted {keys.displayed(key)}", file=out)
    if not removed:
        print(f"nothing stored at {keys.displayed(args.key)}", file=out)
    # `beneath` unadjusted, and the same number the dry run above passes. It
    # counts what a plain delete would *keep*, which is already what is left
    # once one has happened; a recursive delete has no remainder to report at
    # all, and `_report_remainder` decides that for itself. The `len(removed)`
    # correction that stood here applied only when `recursive` -- which is
    # exactly when nothing is printed -- so it never reached an output.
    _report_remainder(args, beneath, out)
    return 0


def _report_remainder(
    args: argparse.Namespace, beneath: int, out: TextIO, *, dry_run: bool = False
) -> None:
    """Say what a non-recursive delete leaves behind.

    Without this, deleting a key that holds nothing itself but has a subtree
    under it looks identical to deleting nothing at all - which is exactly the
    case where a caller most needs to know the subtree is still there.
    """
    if args.recursive or beneath <= 0:
        return
    verb = "would remain" if dry_run else "remain"
    print(
        f"  {beneath} keys below {keys.displayed(args.key)} {verb}; --recursive to take them too",
        file=out,
    )


def _check_command(args: argparse.Namespace, out: TextIO) -> int:
    """Report on the store, and optionally repair what can be repaired.

    The one pair of subcommands about the *store* rather than about documents,
    and it works for any backend. :mod:`outrage.maintenance` asks the questions
    every backend can answer -- the row invariants, the format version -- and
    the backend answers for its own storage through ``check_file``.
    ``_open_existing`` hands back whichever backend the store file names, so
    pointing this at a parquet store gives a parquet report rather than a
    refusal or a SQLite report full of zeroes.
    """
    with _open_existing(args) as opened:
        report = maintenance.check(opened)
        _print_report(report, out)

        if not args.repair:
            if report.repairable:
                print("\n--repair can fix:", file=out)
                for problem in report.repairable:
                    print(f"  {problem.summary}", file=out)
            return 0 if report.sound else 1

        print("\nrepairing", file=out)
        done = maintenance.repair(opened)
        for action in done:
            print(f"  {action.action}: {action.before} -> {action.after} bytes", file=out)
        if not done:
            # An empty list is a backend saying there is nothing its storage
            # could need, which is not the same as finding nothing wrong. Said
            # rather than left as a blank, so the difference reaches the user.
            print(f"  nothing to repair: a {report.backend} store has no state a "
                  f"repair could move", file=out)

    # Re-opened deliberately: the point of the second check is what the file
    # looks like now, and reusing the first report would be reporting the claim
    # rather than the result.
    with _open_existing(args) as reopened:
        after = maintenance.check(reopened)
    print("", file=out)
    _print_report(after, out)
    return 0 if after.sound else 1


def _print_report(report: maintenance.Report, out: TextIO) -> None:
    """Two lines and then the problems: what any store says, then what this one does.

    The second line is the backend's own, printed from ``details`` rather than
    from fields, which is what lets a parquet store report its row groups and
    its sort order where SQLite reports its integrity and its log - instead of
    both being made to answer the other's questions with a zero.
    """
    print(f"{report.path} ({report.backend})", file=out)
    print(
        f"  format {report.format_version}, "
        f"{report.documents} documents, {report.metadata} metadata, "
        f"{report.characters} characters",
        file=out,
    )
    if report.details:
        print("  " + ", ".join(f"{label} {value}" for label, value in report.details.items()),
              file=out)
    for problem in report.problems:
        print(f"  {problem.severity}: {problem.summary}", file=out)
        if problem.detail:
            print(f"    {problem.detail}", file=out)
    if report.sound and not report.problems:
        print("  nothing wrong", file=out)


def _open_existing(args: argparse.Namespace):
    """Open a store that is already there, refusing to create one.

    ``Store.__init__`` creates what is missing, so a command acting on an
    existing store has to check first - otherwise a mistyped --dir reports a
    perfectly healthy empty store, which is a wrong answer delivered as a clean
    bill of health.
    """
    directory = maintenance.require_store(store.resolve_directory(args.directory), args.filename)
    return store.open_store(directory, filename=args.filename)


#: What each action reads as, before it has happened and after. One vocabulary
#: for the server entry, the hook and the copied files, so a report over all
#: three does not describe the same outcome three ways.
_ACTIONS = {
    "created": ("would add", "added"),
    "updated": ("would update", "updated"),
    "unchanged": ("already current", "already current"),
    "linked": ("left linked", "left linked"),
}


def _said(action: str, dry_run: bool) -> str:
    return _ACTIONS[action][0 if dry_run else 1]


def _report(change: config_module.Change, out: TextIO, *, dry_run: bool) -> None:
    """Say what is about to change, in enough detail to notice a wrong answer.

    The whole command is a guess at two paths, so printing them is not a
    courtesy: an entry point in the wrong environment or a store directory
    beside the wrong project both produce a server that starts cleanly and
    talks to nothing anyone meant.
    """
    verb = _said(change.action, dry_run)

    print(f"{change.scope} configuration: {change.path}", file=out)
    print(f"  {change.name}: {verb}", file=out)
    if change.previous is not None and change.action == "updated":
        _print_command("  was:", change.previous, out)
    _print_command("  now:" if change.action == "updated" else "  ", change.entry, out)


def _report_hook(change: install.HookChange, out: TextIO, *, dry_run: bool) -> None:
    """Say what the hook entry did, and name any duplicates cleared out.

    The duplicates line matters more than it looks: an entry outrage could not
    recognise is a hook that fired twice, and the only moment anybody finds out
    is the run that finally removes it.
    """
    print(f"session hook ({change.target.name}): {change.path}", file=out)
    print(f"  {change.target.event}: {_said(change.action, dry_run)}", file=out)
    if change.duplicates:
        removed = "would remove" if dry_run else "removed"
        entries = "entry" if change.duplicates == 1 else "entries"
        print(f"  {removed} {change.duplicates} duplicate {entries}", file=out)


def _report_assets(
    changes: tuple[install.FileChange, ...],
    out: TextIO,
    *,
    dry_run: bool,
    root: Path,
    label: str,
) -> None:
    """Say what happened to each packaged file, by its path within the project."""
    print(f"{label}: {root}", file=out)
    for change in changes:
        try:
            where = change.path.relative_to(root)
        except ValueError:  # pragma: no cover - only if an asset root changes
            where = change.path
        line = f"  {_said(change.action, dry_run):<15} {where}"
        if change.action == "linked":
            # Not a failure, and not silence either: a linked file is one this
            # run deliberately did not update, so the reader can see it is old.
            line += "  (a symlink, left as it is)"
        print(line, file=out)


def _print_command(label: str, entry: dict[str, object], out: TextIO) -> None:
    command = " ".join([str(entry.get("command", ""))] + [str(a) for a in entry.get("args", [])])
    print(f"{label} {command}".rstrip(), file=out)


def main(argv: list[str] | None = None, out: TextIO | None = None) -> int:
    """Run one command and return its exit status.

    The console script ``outrage``, and the whole of what this front end does:
    parse, dispatch, and turn a :class:`~outrage.errors.OutrageError` into a sentence
    on stderr. ``out`` is where a command's own output goes, and defaults to
    stdout; a test passes its own and reads what a person would have seen.

    Returns rather than exits, so that a caller in the same process -- which is
    every test of this module -- gets the status without the interpreter
    stopping.
    """
    args = parse_args(argv)
    try:
        return args.handler(args, out or sys.stdout)
    except OutrageError as exc:
        # One base rather than a tuple that grows with each command. A failure
        # that is not a OutrageError is a bug in outrage, and a traceback is the right
        # output for a bug.
        #
        # Rendered here, because this is a front end and the error is not. The
        # command line opens one store directory and knows nothing about a
        # mount table, so a key names itself: the default namer is the correct
        # one here and the mount-aware one would be wrong. See `messages`.
        print(f"outrage: {messages.render(exc)}", file=sys.stderr)
        return 1


__all__ = [
    "ConflictingSourceError",
    "main",
    "parse_args",
]
