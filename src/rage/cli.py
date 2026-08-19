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
from collections.abc import Iterator
from pathlib import Path
from typing import TextIO

from . import __version__, eventlog, logread, maintenance, store
from . import config as config_module
from .errors import RageError


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

    get = subcommands.add_parser(
        "get",
        help="print the document stored at a key",
        description=(
            "Read a key and print its content. Metadata is a key like any "
            "other, so `rage get notes/x/!title` prints the title. The whole "
            "document is printed by default: the tool's own read truncates at "
            "a cap and hands back a continuation offset, which is right for an "
            "agent's context window and wrong for a person redirecting a "
            "document to a file. Ask for a slice and you get exactly the slice."
        ),
    )
    _store_option(get)
    get.add_argument(
        "key", help="Key to read, e.g. context/1/task or context/1/task/!title."
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
    get.set_defaults(handler=get_command)

    set_ = subcommands.add_parser(
        "set",
        help="store a document, from a file or from standard input",
        description=(
            "Write content to a key, overwriting whatever is there. Content "
            "comes from standard input unless --file or --content is given, so "
            "a document can be piped in. A `?` segment in the key is replaced "
            "by a number the store allocates, and the key actually written is "
            "printed — which is the only way to learn the allocated number."
        ),
    )
    _store_option(set_)
    set_.add_argument("key", help="Key to write, e.g. notes/thing or notes/? to allocate.")
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
    set_.set_defaults(handler=set_command)

    ls = subcommands.add_parser(
        "ls",
        help="list the keys immediately below a key",
        description=(
            "List one level. Includes documents, metadata, and keys that exist "
            "only because something beneath them does — a container holds "
            "nothing itself and cannot be read, which is why listing and "
            "reading disagree about whether it is there."
        ),
    )
    _store_option(ls)
    ls.add_argument("key", nargs="?", default=None, help="Key to list below. Omit for the top.")
    ls.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Descend the whole subtree rather than one level.",
    )
    _limit_option(ls, "keys")
    ls.set_defaults(handler=ls_command)

    dump = subcommands.add_parser(
        "dump",
        help="print every document at and below a key",
        description=(
            "Read a subtree. With --meta the result holds that metadata "
            "instead of the documents, which is how the titles of everything "
            "under a key are surveyed in one pass. Every document is printed "
            "whole by default, as `rage get` does and for the same reason: "
            "`rage dump > file` is an export, and an export that quietly holds "
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
    dump.set_defaults(handler=dump_command)

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
    rm.add_argument("key", help="Key to delete.")
    rm.add_argument(
        "--recursive", "-r", action="store_true", help="Also delete everything beneath the key."
    )
    rm.add_argument(
        "--dry-run", action="store_true", help="Report what would go without deleting it."
    )
    _limit_option(rm, "keys previewed by --dry-run")
    rm.set_defaults(handler=rm_command)

    check = subcommands.add_parser(
        "check",
        help="check the store file, and optionally repair it",
        description=(
            "Ask whether the file is sound: SQLite's own integrity check, the "
            "schema version, the row invariants, and how much of the store is "
            "sitting in the write-ahead log rather than in the database. That "
            "last one is invisible in normal use and is what makes a copy of "
            "the database file alone lose recent writes."
        ),
    )
    _store_option(check)
    check.add_argument(
        "--repair",
        action="store_true",
        help=(
            "Fold the write-ahead log back into the database and compact it. "
            "Neither step changes a document."
        ),
    )
    check.set_defaults(handler=check_command)

    return parser.parse_args(argv)


def _limit_option(parser: argparse.ArgumentParser, what: str) -> None:
    """Add ``--limit``, which shows less rather than fetching less.

    The command line pages the store internally and always reads to the end,
    so this is a display bound and nothing else: the user asks to see less and
    is told when they got it. Nobody ever gets less by accident, which is the
    opposite default to the tools and for the opposite reason — a redirect into
    a file is an export.
    """
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help=f"Show at most N {what}, and say so on stderr. Everything by default.",
    )


def _store_option(parser: argparse.ArgumentParser) -> None:
    """The store directory, spelled the same way on every subcommand."""
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
        raise store.BackupError(f"no store in {directory}")

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


def get_command(args: argparse.Namespace, out: TextIO) -> int:
    """Print a document, whole unless a slice was asked for."""
    with _open_existing(args) as opened:
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
    # round-tripped through `rage get > f` and `rage set < f` has to come back
    # the same length it went in.
    out.write(excerpt.content)
    if excerpt.truncated:
        print(
            f"\nrage: {excerpt.returned} of {excerpt.total} characters; "
            f"more from --offset {excerpt.next_offset}",
            file=sys.stderr,
        )
    return 0


def set_command(args: argparse.Namespace, out: TextIO) -> int:
    """Write a document from an argument, a file, or standard input."""
    content = _content(args)
    directory = store.resolve_directory(args.directory)
    with store.open_store(directory) as opened:
        written = opened.store_document(args.key, content, args.format, title=args.title)

    # The resolved directory, not the one asked for: a mistyped --dir creates a
    # store rather than failing, so the only defence is saying where it went.
    print(f"{written}  {len(content)} characters in {directory / store.DB_FILENAME}", file=out)
    return 0


def _content(args: argparse.Namespace) -> str:
    """Content from --content, --file, or standard input, in that order."""
    if args.content is not None and args.file is not None:
        raise ConflictingSource("give --content or --file, not both")
    if args.content is not None:
        return args.content
    if args.file is not None:
        path = Path(args.file).expanduser()
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConflictingSource(f"cannot read {path}: {exc}") from exc
    if sys.stdin.isatty():
        # Otherwise the command hangs on an empty terminal looking like it
        # worked, and the store ends up with an empty document at a good key.
        raise ConflictingSource("nothing to store: pass --content, --file, or pipe it in")
    return sys.stdin.read()


class ConflictingSource(RageError):
    """Raised when the content to store cannot be determined from the arguments."""


#: How much of a collection one internal query asks for. The command line reads
#: to the end regardless, so this only decides how many round trips that takes
#: and how much is held at once: large enough to be one query for an ordinary
#: level, small enough that a huge one is never held whole.
PAGE = 200


def ls_command(args: argparse.Namespace, out: TextIO) -> int:
    """List one level, or the whole subtree, printing as it goes."""
    shown = 0
    with _open_existing(args) as opened:
        entries = _walk(opened, args.key) if args.recursive else _level(opened, args.key)
        for entry in entries:
            if args.limit is not None and shown >= args.limit:
                # On stderr, so a listing piped into something else is not
                # corrupted by a note about itself.
                print(f"rage: stopped at --limit {args.limit}", file=sys.stderr)
                break
            size = "-" if entry.size is None else str(entry.size)
            print(
                f"{entry.kind:<9} {size:>8}  {entry.updated_at or '-':<20}  {entry.key}", file=out
            )
            shown += 1

    if not shown:
        print(f"nothing below {args.key or 'the top level'}", file=out)
    return 0


def _level(opened: store.Store, key: str | None) -> Iterator[store.Entry]:
    """One level, a page at a time, to the end.

    The store pages and the command line does not: a person listing a key wants
    the level, and a listing that stops at an internal page size is the silent
    partial answer this project keeps finding. Streaming is what makes it both
    complete and bounded in memory — and it fails better, since a long listing
    interrupted has already shown its first thousand lines rather than nothing.
    """
    cursor = None
    while True:
        page = opened.list_keys(key, limit=PAGE, after=cursor)
        yield from page.items
        if page.next_cursor is None:
            return
        cursor = page.next_cursor


def _walk(opened: store.Store, key: str | None) -> Iterator[store.Entry]:
    """Every key below ``key``, depth first.

    Built from repeated ``list_keys`` rather than from ``get_documents``,
    because only ``list_keys`` reports the containers — a key holding nothing
    itself but with documents beneath it does not appear in a subtree read at
    all, and leaving it out of a listing is how its children look parentless.
    """
    for entry in _level(opened, key):
        yield entry
        if entry.kind != "metadata":
            yield from _walk(opened, entry.key)


def dump_command(args: argparse.Namespace, out: TextIO) -> int:
    """Print a subtree, one document at a time, as each one arrives."""
    shown = 0
    with _open_existing(args) as opened:
        for excerpt in _documents(opened, args):
            if args.limit is not None and shown >= args.limit:
                print(f"rage: stopped at --limit {args.limit}", file=sys.stderr)
                break
            header = f"=== {excerpt.key}"
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
            args.key,
            meta_name=args.meta_name,
            depth=args.depth,
            max_chars=args.max_chars or store.DEFAULT_BULK_MAX_CHARS,
            limit=PAGE,
            after=cursor,
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


def rm_command(args: argparse.Namespace, out: TextIO) -> int:
    """Delete a key, saying what went and what stayed."""
    with _open_existing(args) as opened:
        beneath = opened.descendant_count(args.key)
        if args.dry_run:
            # Asking the store rather than predicting: a dry run that computes
            # its own answer is one that can disagree with what it previews.
            print(f"would delete {args.key}", file=out)
            if args.recursive:
                # The whole subtree, not one level of it: a preview that shows
                # the first level of a deletion reaching five is not a preview
                # of what --recursive takes.
                previewed = 0
                for entry in _walk(opened, args.key):
                    if args.limit is not None and previewed >= args.limit:
                        print(f"  and {beneath - previewed} more", file=out)
                        break
                    print(f"  and below: {entry.key}", file=out)
                    previewed += 1
            _report_remainder(args, beneath, out, dry_run=True)
            return 0

        removed = opened.delete(args.key, recursive=args.recursive)

    for key in removed:
        print(f"deleted {key}", file=out)
    if not removed:
        print(f"nothing stored at {args.key}", file=out)
    _report_remainder(args, beneath - (len(removed) - 1 if args.recursive else 0), out)
    return 0


def _report_remainder(
    args: argparse.Namespace, beneath: int, out: TextIO, *, dry_run: bool = False
) -> None:
    """Say what a non-recursive delete leaves behind.

    Without this, deleting a key that holds nothing itself but has a subtree
    under it looks identical to deleting nothing at all — which is exactly the
    case where a caller most needs to know the subtree is still there.
    """
    if args.recursive or beneath <= 0:
        return
    verb = "would remain" if dry_run else "remain"
    print(f"  {beneath} keys below {args.key} {verb}; --recursive to take them too", file=out)


def check_command(args: argparse.Namespace, out: TextIO) -> int:
    """Report on the store file, and optionally fold its sidecar back in."""
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
        for done in maintenance.repair(opened):
            print(f"  {done.action}: {done.before} -> {done.after} bytes", file=out)

    # Re-opened deliberately: the point of the second check is what the file
    # looks like now, and reusing the first report would be reporting the claim
    # rather than the result.
    with _open_existing(args) as reopened:
        after = maintenance.check(reopened)
    print("", file=out)
    _print_report(after, out)
    return 0 if after.sound else 1


def _print_report(report: maintenance.Report, out: TextIO) -> None:
    print(f"{report.path}", file=out)
    print(
        f"  schema {report.schema}, integrity {report.integrity}, "
        f"{report.documents} documents, {report.metadata} metadata, "
        f"{report.characters} characters",
        file=out,
    )
    print(f"  {report.main_bytes} bytes in the database, {report.wal_bytes} in its log", file=out)
    for problem in report.problems:
        print(f"  {problem.severity}: {problem.summary}", file=out)
        if problem.detail:
            print(f"    {problem.detail}", file=out)
    if report.sound and not report.problems:
        print("  nothing wrong", file=out)


def _open_existing(args: argparse.Namespace):
    """Open a store that is already there, refusing to create one.

    ``Store.__init__`` creates what is missing, so a command acting on an
    existing store has to check first — otherwise a mistyped --dir reports a
    perfectly healthy empty store, which is a wrong answer delivered as a clean
    bill of health.
    """
    directory = maintenance.require_store(store.resolve_directory(args.directory))
    return store.open_store(directory)


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
    except RageError as exc:
        # One base rather than a tuple that grows with each command. A failure
        # that is not a RageError is a bug in rage, and a traceback is the right
        # output for a bug.
        print(f"rage: {exc}", file=sys.stderr)
        return 1


__all__ = [
    "backup_command",
    "check_command",
    "config_command",
    "dump_command",
    "get_command",
    "log_command",
    "ls_command",
    "main",
    "parse_args",
    "rm_command",
    "set_command",
]
