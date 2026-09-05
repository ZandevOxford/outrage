"""Command line tool over the store library.

A thin wrapper, like the server: argument shaping and printing only. Anything
with behaviour belongs in :mod:`outrage.store` or :mod:`outrage.config`, so that it
can be tested without going through argparse and used by whichever of the two
front ends needs it.

What this module *offers* is :func:`argument_parser`, :func:`parse_args`,
:func:`main`, and :class:`ConflictingSourceError` as something to catch. The
subcommand handlers are argparse wiring reached through ``handler``, one per
subcommand and never from outside, so they are private -- which also keeps this
page from being a list of twelve near-identical ``(args, out) -> int`` entries
in place of an orientation. The interface people actually use here is the
command line, and ``outrage --help`` is what states it.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any, TextIO

from . import (
    __version__,
    bulk,
    contents,
    eventlog,
    ingest,
    install,
    keys,
    logread,
    maintenance,
    messages,
    mountfile,
    mounts,
    shipped,
    store,
)
from . import config as config_module
from .errors import OutrageError
from .mounts import MOUNT_KIND, READ_ONLY_MOUNT_KIND

#: The subcommands that act across a whole mount table rather than on one
#: store file. Everything that reads or writes documents is here; ``check`` and
#: ``backup`` are not, and by nature: both are about a *file* -- its integrity,
#: its bytes -- and both already say which one they mean with ``--store``.
#: ``pack`` is not either, for the same reason its target is one file.
#:
#: ``mounts`` is here for the options and the splice rather than for opening
#: anything: it reports the table a command line would open, which is a
#: question only worth asking of the same list every other one of these gets.
#:
#: Read by :func:`parse_args` to decide whether a mount configuration file is
#: spliced in, and by the loop that adds the options, so the two cannot drift.
MOUNTED = (
    "get",
    "set",
    "ingest",
    "make_contents",
    "ls",
    "dump",
    "copy",
    "rm",
    "export",
    "import",
    "mounts",
)

#: The rules a command with no watermark can offer. ``overwrite-unchanged``
#: is measured against ``--unchanged-since``, which only ``copy`` takes: an
#: export or an import offering it would be offering a choice whose only
#: outcome is a refusal from a layer that cannot say which flag is missing.
_UNWATERMARKED_CONFLICTS = tuple(c for c in store.CONFLICTS if c != store.OVERWRITE_UNCHANGED)

_RANGE_ARGUMENTS = (
    "after",
    "after_inclusive",
    "after_subtree",
    "before",
    "before_inclusive",
    "final_subtree",
)


def argument_parser() -> argparse.ArgumentParser:
    """Build the whole command-line interface.

    Every subcommand sets ``handler``, so :func:`main` dispatches without a
    branch per command and this function is the one place the shape of the
    command line is written down. It returns a new parser on every call, making
    the interface available to documentation and other introspection without
    parsing ``sys.argv`` or reading a mount configuration.
    """
    parser = argparse.ArgumentParser(
        prog="outrage", description="Command line tool for the Outrage document store"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"outrage {__version__}",
        help="show the installed version and exit",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    init = subcommands.add_parser(
        "init",
        help="set a project up: MCP server, session hooks, skill and agents",
        description=(
            "Arrange everything a project needs to use outrage: the MCP server "
            "entry in .mcp.json, a session-start hook for each harness - "
            ".claude/settings.json for Claude Code, .github/hooks/outrage.json "
            "for Copilot CLI, .codex/hooks.json for Codex - and the packaged "
            "skill and agents in .claude/, Copilot agents in .github/agents/, "
            "and the Codex skills in .codex/. "
            "Only the entries outrage owns are written; anything else in those "
            "files is left as it was, and a file already holding the current "
            "content is not rewritten. Mounts go in mounts.toml in the store "
            "directory, which is written once and maintained by hand "
            "thereafter; an option already on an existing server entry - "
            "--log, or a mount an older release wrote there - is kept even "
            "when this run does not mention it. Safe to re-run, which is how a "
            "project is repaired after outrage is upgraded or the environment "
            "moves."
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

    sessionstart = subcommands.add_parser(
        "sessionstart",
        help="emit the managed SessionStart context as hook JSON",
        description="Emit the managed SessionStart context as hook JSON.",
    )
    sessionstart.add_argument(
        "--copilot",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    sessionstart.add_argument(
        "managed_marker",
        nargs="?",
        choices=(install.SESSIONSTART_MARKER,),
        help=argparse.SUPPRESS,
    )
    sessionstart.set_defaults(handler=_sessionstart_command)

    config = subcommands.add_parser(
        "config",
        help="write the MCP server configuration for a project or user",
        description=(
            "Register the outrage MCP server, filling in the absolute path to this "
            "environment's entry point and to the store directory. Only the "
            "server's own entry is touched; anything else in the file is left "
            "as it was. Options already on that entry are kept unless this run "
            "names the same one, so a re-run cannot silently drop logging - "
            "which also means removing one is an edit to the file. Mounts are "
            "not written here at all: they go in mounts.toml in the store "
            "directory, which both the server and the command line read, and "
            "which is written once and maintained by hand thereafter. Safe to "
            "re-run, which is how the configuration is repaired after the "
            "environment moves."
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
    _table_options(get)
    get.add_argument(
        "key",
        help=(
            "Key to read, e.g. context/1/task, context/1/task/!title, or "
            "context/?last/task for the newest."
        ),
    )
    get.add_argument("--offset", type=int, default=0, help="Character offset to start at.")
    get.add_argument(
        "--byte-offset",
        dest="byte_offset",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Byte offset to start at, instead of --offset. Counts UTF-8 bytes, "
            "which is the unit a file on disk is addressed in, so an offset "
            "from a contents index still names the same place after the "
            "document has been written out. A byte landing inside a character "
            "reads from that character's first byte."
        ),
    )
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
    _table_options(set_)
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

    ingest_ = subcommands.add_parser(
        "ingest",
        help="convert one local file to Markdown and store it",
        description=(
            "Convert one local regular file with MarkItDown and store the resulting "
            "Markdown as one document. URLs are refused, converter plugins are disabled, "
            "and the optional documents extra must be installed. An existing destination "
            "is preserved unless --overwrite is passed. The title comes from --title, "
            "then the converted document, then the source filename stem."
        ),
    )
    _store_option(ingest_)
    _table_options(ingest_)
    ingest_.add_argument("source", metavar="SOURCE", help="Local regular file to convert.")
    ingest_.add_argument("key", metavar="KEY", help="Destination key for the Markdown document.")
    ingest_.add_argument(
        "--title", default=None, help="Title to store instead of the detected title."
    )
    ingest_.add_argument(
        "--overwrite", action="store_true", help="Replace a document already at the destination."
    )
    ingest_.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform conversion and report the result without writing anything.",
    )
    ingest_.set_defaults(handler=_ingest_command)

    make_contents = subcommands.add_parser(
        "make_contents",
        help="store a character-offset index of a Markdown document's headings",
        description=(
            "Read one stored Markdown document and write an index containing its "
            "literal headings and their zero-based character offsets. The "
            "source is unchanged. The generated index overwrites direct metadata "
            "named by --metadata-name, which defaults to contents."
        ),
    )
    _store_option(make_contents)
    _table_options(make_contents)
    make_contents.add_argument("key", metavar="KEY", help="Markdown document key to index.")
    make_contents.add_argument(
        "--metadata-name",
        default="contents",
        help="Direct metadata name to write, without the leading '!'. Default contents.",
    )
    make_contents.set_defaults(handler=_make_contents_command)

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
    _table_options(ls)
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
    _table_options(dump)
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

    copy = subcommands.add_parser(
        "copy",
        help="copy a range of documents within the mounted namespace",
        description=(
            "Copy documents from one part of the mounted namespace to another. "
            "SOURCE names the subtree to read and TARGET is a prefix grafted "
            "onto every key written, so `outrage copy ref/python archive` "
            "writes `ref/python/...` beneath `archive`, and --reroot is what "
            "lands them at `archive` itself instead. Documents may cross "
            "between backing stores, and metadata and original timestamps "
            "cross with them. The selection is the intersection of SOURCE, "
            "--depth, and every range bound supplied."
        ),
    )
    _store_option(copy)
    _table_options(copy)
    copy.add_argument("source", help="Key whose subtree to copy, or / for the root.")
    copy.add_argument(
        "target",
        help=(
            "Key prefix to graft the copied keys beneath. It must not be at "
            "or below SOURCE, because a copy streams rather than snapshots."
        ),
    )
    copy.add_argument(
        "--reroot",
        action="store_true",
        help=(
            "Land the copied keys at TARGET itself rather than beneath their "
            "own source key, so `outrage copy ref/python archive --reroot` "
            "writes `archive` and `archive/...` rather than "
            "`archive/ref/python/...`. This is the spelling that moves a "
            "subtree; without it a copy can only nest one deeper. SOURCE and "
            "TARGET must then be wholly separate subtrees, in either "
            "direction."
        ),
    )
    copy.add_argument(
        "--depth",
        type=int,
        default=None,
        help="Copy at most this many levels below SOURCE. Metadata adds no level.",
    )
    _range_options(copy)
    _conflict_option(copy, "A key already holding a document is", watermarked=True)
    _unchanged_since_option(copy, "anything under TARGET")
    copy.add_argument(
        "--dry-run", action="store_true", help="Report what would be copied without writing it."
    )
    copy.set_defaults(handler=_copy_command)

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
    _table_options(export)
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
    _table_options(import_)
    import_.add_argument("source", metavar="DIRECTORY", help="Directory to read documents from.")
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
        "--no-byte-lengths",
        dest="byte_lengths",
        action="store_false",
        help=(
            "Leave out the column holding each document's length in UTF-8 "
            "bytes. It is written by default because a parquet file is never "
            "updated, so a store packed without it can only gain it by being "
            "packed again."
        ),
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
    _table_options(rm)
    rm.add_argument("key", help="Key to delete, ?last for the newest.")
    rm.add_argument(
        "--recursive", "-r", action="store_true", help="Also delete everything beneath the key."
    )
    _unchanged_since_option(rm, "anything this would delete")
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

    mounts_ = subcommands.add_parser(
        "mounts",
        help="report the mount table a command line would open",
        description=(
            "Say which stores this command line names, and whether each one is "
            "there. Nothing is opened, which is the point: opening a "
            "read-write mount is what creates it, so a mistyped name in a "
            "configuration file becomes an empty store that reads exactly like "
            "a store with nothing in it yet. This reports that before it "
            "happens, and is safe to run on a fresh checkout. Every option the "
            "other commands take is taken here, so it answers for the line you "
            "would really run - including which configuration file, or the "
            "command line itself, each mount came from. What is *in* the "
            "stores is `outrage ls`, which does open them."
        ),
    )
    _store_option(mounts_)
    _table_options(mounts_)
    mounts_.set_defaults(handler=_mounts_command)

    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse an argument list and attach the selected command's handler.

    Separate from :func:`main` so that a test can ask what an argument list
    parses to without running anything.

    The subcommands in :data:`MOUNTED` have their mount options spliced in
    from a configuration file first -- see :mod:`outrage.mountfile`. Only
    those, because a subcommand that does not take the options would be handed
    ones it has never heard of; and the subcommand is read off the front of the
    argument list rather than parsed, since parsing is what has not happened
    yet. That is safe here for one reason worth keeping true: **no option on
    the top level parser takes a value**, so the first token that is not a flag
    is the subcommand.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    at = next((i for i, token in enumerate(argv) if not token.startswith("-")), None)
    written = None
    if at is not None and argv[at] in MOUNTED:
        # After the subcommand, which is where the front of its line is: an
        # option belonging to `outrage ls` written before the word `ls` is an
        # option on the top level parser, which has never heard of it.
        written = (list(argv), at + 1)
        argv = mountfile.spliced(argv, front=at + 1)
    parsed = argument_parser().parse_args(argv)
    # The list as it was *written*, kept for the one command that reports where
    # each mount came from. A namespace built from the spliced list cannot say:
    # by then every source has been flattened into one argument list, which is
    # the whole point of the splice and exactly what a reader needs undone.
    parsed.written = written
    return parsed


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


def _unchanged_since_option(parser: argparse.ArgumentParser, what: str) -> None:
    """``--unchanged-since``, the watermark saying when the caller looked.

    One spelling for both commands that take it, and the same word the library
    and the tools use. Absent, the command behaves exactly as it always has:
    an unwatermarked run is an unchecked one, which is why adding this moved no
    default.

    A --dry-run prints the time it looked, so the pair reads as what it is --
    look, then write only what has not moved since -- with the second call
    taking back what the first one printed.
    """
    parser.add_argument(
        "--unchanged-since",
        dest="unchanged_since",
        default=None,
        metavar="TIME",
        help=(
            f"Refuse if {what} changed since TIME, an ISO 8601 timestamp such "
            f"as 2026-09-03T10:15:00Z. Nothing is written when it has. "
            f"Unchecked by default."
        ),
    )


def _conflict_option(
    parser: argparse.ArgumentParser, what: str, *, watermarked: bool = False
) -> None:
    """What to do about something already at the far end, spelled once.

    Per item rather than for the run as a whole, which is the only promise a
    stream can keep: 'stop' stops at the first conflict and says what it had
    already done, rather than claiming an all-or-nothing it would have to
    abandon the moment the source stopped being a directory it can pre-walk.

    ``watermarked`` is what a command with ``--unchanged-since`` adds:
    overwrite-unchanged measures each collision against that time, so offering
    it to a command that cannot take one would be a choice whose only outcome
    is a refusal.
    """
    choices = store.CONFLICTS if watermarked else _UNWATERMARKED_CONFLICTS
    narrowed = (
        "replaced unless it changed since --unchanged-since (overwrite-unchanged), "
        if watermarked
        else ""
    )
    parser.add_argument(
        "--on-conflict",
        dest="on_conflict",
        choices=choices,
        default=store.SKIP,
        help=(
            f"{what} left alone (skip, the default), replaced (overwrite), "
            f"{narrowed}or stops the run where it stands (stop)."
        ),
    )


def _range_options(parser: argparse.ArgumentParser) -> None:
    """The six cuts a :class:`store.KeyRange` can put in the key order."""
    parser.add_argument(
        "--after-inclusive",
        default=None,
        metavar="KEY",
        help="Copy KEY and everything after it in the selection.",
    )
    parser.add_argument(
        "--after",
        default=None,
        metavar="KEY",
        help="Copy strictly after KEY, including keys beneath it.",
    )
    parser.add_argument(
        "--after-subtree",
        default=None,
        metavar="KEY",
        help="Copy strictly after KEY and its whole subtree.",
    )
    parser.add_argument(
        "--before",
        default=None,
        metavar="KEY",
        help="Copy strictly before KEY and its subtree.",
    )
    parser.add_argument(
        "--before-inclusive",
        default=None,
        metavar="KEY",
        help="Copy KEY and everything before it in the selection.",
    )
    parser.add_argument(
        "--final-subtree",
        default=None,
        metavar="KEY",
        help="Copy no later than the end of KEY's subtree.",
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
    """The stores a project's mount table holds, spelled once for init and config.

    Not to be confused with :func:`_table_options`, which opens those stores
    for one command. These *seed* the table - ``mounts.toml`` in the store
    directory, which the server and the command line both read - and it is
    written **once**: a file whose reason for existing is comments is not
    machine-rewritten, so a run naming a mount a table already there does not
    hold is told which lines to add.

    Every one of them is a file inside the store directory, so this is the one
    place that has to say so.
    """
    parser.add_argument(
        "--root-mount",
        dest="root_mount",
        metavar="FILE",
        default=None,
        help=(
            f"{verb} root-mount in the project's mount table: the store "
            f"answering for every key no mount claims, as a file inside --dir "
            f"(default: {store.default_store_file()}). Written only when it is "
            f"not the default."
        ),
    )
    parser.add_argument(
        "--mount",
        dest="mounts",
        action="append",
        default=[],
        metavar="KEY=FILE",
        help=(
            f"{verb} mount in the project's mount table: another store under "
            f"KEY, as in ref=reference.sqlite. FILE is relative to --dir, like "
            f"--root-mount. Repeatable, and refused here if the mount point is "
            f"not a valid key."
        ),
    )
    parser.add_argument(
        "--mount-ro",
        dest="read_only_mounts",
        action="append",
        default=[],
        metavar="KEY=FILE",
        help=(
            f"{verb} read-only mount: as --mount, but every write routed there "
            "is refused before it reaches the store. Repeatable."
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
        # The server's name for the same thing, and an alias rather than a
        # second option: a mount configuration file is defined as the options
        # it stands for, and it has one spelling for the root mount whichever
        # front end reads it.
        "--root-mount",
        dest="filename",
        metavar="FILE",
        default=store.default_store_file(),
        help=(
            f"Which store in that directory, as a file relative to it "
            f"(default: {store.default_store_file()}). On a command that takes "
            f"mounts this is the root mount -- the store answering for every "
            f"key no mount claims -- and --root-mount is the same option. "
            f"Takes the same options a --mount does, so --store "
            f"documents,{mounts.TYPE_OPTION}=files reads a directory of files "
            f"as the whole store."
        ),
    )


def _table_options(parser: argparse.ArgumentParser) -> None:
    """The mounts a command acts *across*, spelled once for every command that can.

    Not to be confused with :func:`_mount_options`, which records the same
    three options into a server entry for a client to launch later. These open
    the stores now: with them, ``outrage ls`` and ``outrage dump`` see the one
    namespace the MCP server sees rather than the root store alone -- which is
    what makes a table something a person can look at, and what stops a table
    typed for the command line from being a *different* namespace answering the
    same keys.

    The root mount is ``--store``, from :func:`_store_option`, and is not
    repeated here.
    """
    parser.add_argument(
        "--mount",
        dest="mounts",
        action="append",
        default=[],
        metavar=f"KEY{mounts.SPEC_DELIMITER}FILE",
        help=(
            "Also mount the store FILE under KEY for this command, as in "
            f"ref{mounts.SPEC_DELIMITER}reference.sqlite. FILE is relative to "
            "--dir, like --store, and may carry options after a comma: "
            f"docs,{mounts.TYPE_OPTION}=files says which backend keeps the "
            "store, for one whose name cannot -- a directory of files has no "
            f"extension to read. Types: {', '.join(store.backend_names())}. "
            "Repeatable. Reads, writes, surveys and recursive deletes cross "
            "mount boundaries."
        ),
    )
    parser.add_argument(
        "--mount-ro",
        dest="read_only_mounts",
        action="append",
        default=[],
        metavar=f"KEY{mounts.SPEC_DELIMITER}FILE",
        help=(
            "As --mount, but every write routed there is refused before it "
            "reaches the store. Repeatable. The store must already exist."
        ),
    )
    parser.add_argument(
        mountfile.DOCS_FLAG,
        dest="mount_docs",
        action="store_true",
        help=(
            "Also mount the documentation shipped with outrage, read-only, at "
            f"{keys.displayed(mountfile.DOCS_MOUNT)!r}: what a key is, what "
            f"the tools do, and the conventions worth following, as documents "
            f"in the namespace. Off here and on in the MCP server, so a bare "
            f"outrage command stays this project's own store."
        ),
    )
    parser.add_argument(
        mountfile.UNMOUNT_FLAG,
        dest="unmount",
        action="append",
        default=None,
        metavar="KEY",
        help=(
            "Do not mount the store mounted at KEY. The one thing an override "
            "cannot do -- naming a mount replaces it or adds it, and only this "
            "takes one away. Repeatable, and refused if nothing was mounted "
            "there to remove: the documentation the MCP server carries at "
            f"{mountfile.DOCS_MOUNT} is not mounted here unless "
            f"{mountfile.DOCS_FLAG} asks for it. A --mount for the same key "
            "written after this one mounts it again."
        ),
    )
    parser.add_argument(
        mountfile.CONFIG_FLAG,
        dest="mount_config",
        action="append",
        default=None,
        metavar="FILE",
        help=(
            "Read the mount options from a TOML file, as though they had been "
            "typed here: an option before it loses, an option after it wins, "
            f"and a mount named again replaces the one it names. Repeatable. "
            f"{mountfile.DEFAULT_NAME} in --dir is read first whenever it "
            "exists, so a project's own table needs no flag at all."
        ),
    )
    parser.add_argument(
        mountfile.NO_CONFIG_FLAG,
        dest="no_mount_config",
        action="store_true",
        help=(
            f"Ignore {mountfile.DEFAULT_NAME} in --dir for this run, mounting "
            "only what is named here. The way to read a store no table can "
            "hold: a mount table needs a writable store at the root, and a "
            "packed parquet one is not."
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
    _report_table(done.table, out, dry_run=args.dry_run)
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
    _report_assets(
        done.copilot_assets,
        out,
        dry_run=args.dry_run,
        root=done.project_dir / install.GITHUB_DIR,
        label="Copilot agents",
    )

    if args.dry_run and done.writes:
        # Where the report is long enough to scroll, one line on stderr is what
        # says the run did nothing after the reader has stopped reading.
        print("outrage: dry run, nothing changed", file=sys.stderr)
    return 0


def _sessionstart_command(args: argparse.Namespace, out: TextIO) -> int:
    """Emit the packaged prompt in the selected harness's hook payload."""
    payload = json.dumps(
        install.sessionstart_payload(copilot=args.copilot),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    print(payload, file=out)
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
    entry = config_module.server_entry(directory, log=args.log, log_content=args.log_content)
    table = mountfile.plan_starter(
        directory,
        root_mount=args.root_mount,
        mounts=args.mounts,
        read_only_mounts=args.read_only_mounts,
    )

    change, merged, original = config_module.plan(path, args.scope, entry, name=args.name)
    _report(change, out, dry_run=args.dry_run)
    _report_table(table, out, dry_run=args.dry_run)

    if not args.dry_run:
        if change.writes:
            config_module.write_config(path, merged, original)
        if table.writes:
            mountfile.write_starter(table)
    return 0


def _report_table(table: mountfile.Starter, out: TextIO, *, dry_run: bool) -> None:
    """Say what happened to the project's mount table, including nothing.

    Silent when no mount was named, because then there was no table to write
    and a line about one would be noise on every ``outrage init``.

    The two lines that earn their place are the other cases. **A table already
    there is never rewritten** - a file whose reason for existing is comments
    cannot be - so a run naming a mount it does not hold has to say so, and
    printing the entries is what keeps the answer useful rather than a dead
    end.
    """
    if not table.writes and not table.missing:
        return
    print(f"mount table: {table.path}", file=out)
    if table.writes:
        print(f"  {_said('created', dry_run)}", file=out)
        return
    print("  already there, and not rewritten: add these lines to it", file=out)
    for line in table.missing.splitlines():
        print(f"    {line}", file=out)


def _root(args: argparse.Namespace) -> mounts.Spec:
    """The root store this command line names: its file, and any option on it.

    ``--store`` takes the same grammar as a ``--mount``'s value half, so the
    root can name a backend the way any other mount can -- ``--store
    docs,type=files`` reads a tree as the whole store. Parsed in one place
    because several commands ask the same question of the same argument, and
    two of them ask it about a file that must already exist.
    """
    return mounts.parse_options(args.filename)


def _backup_command(args: argparse.Namespace, out: TextIO) -> int:
    """Snapshot the store, or say where the snapshot would go."""
    directory = store.resolve_directory(args.directory)
    root = _root(args)
    database = store.store_file(directory, root.path)
    if not database.exists():
        # Opening one would create it, and backing up a store the caller never
        # had is a success that answers the wrong question.
        raise store.BackupError("check-no-store", path=str(database))

    with store.open_store(directory, filename=root.path, backend=root.type) as opened:
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
    # At the joined bound when a table answers, because a ``?last`` there may
    # name a mount point and a key inside it -- the same reason the server
    # resolves one at that bound. A single store keeps its own, tighter one.
    args.key = keys.resolve_last(
        args.key,
        opened.last_child,
        max_segments=(
            keys.MAX_JOINED_SEGMENTS
            if isinstance(opened, mounts.MountedStore)
            else keys.MAX_SEGMENTS
        ),
    )
    print(f"outrage: {keys.LAST} is {keys.displayed(args.key)}", file=sys.stderr)


def _resolved_copy(opened: store.Store, args: argparse.Namespace) -> None:
    """Resolve every key-shaped argument accepted by ``outrage copy``."""
    for name in ("source", "target", *_RANGE_ARGUMENTS):
        value = getattr(args, name)
        if value is None or keys.LAST not in value.split(keys.DELIMITER):
            continue
        resolved = keys.resolve_last(
            value,
            opened.last_child,
            max_segments=(
                keys.MAX_JOINED_SEGMENTS
                if isinstance(opened, mounts.MountedStore)
                else keys.MAX_SEGMENTS
            ),
        )
        setattr(args, name, resolved)
        print(
            f"outrage: {keys.LAST} in {name.replace('_', '-')} is {keys.displayed(resolved)}",
            file=sys.stderr,
        )


def _get_command(args: argparse.Namespace, out: TextIO) -> int:
    """Print a document, whole unless a slice was asked for."""
    with _open_table(args) as opened:
        _resolved(opened, args)
        slicing = {
            "offset": args.offset,
            "byte_offset": args.byte_offset,
            "length": args.length,
            "pattern": args.pattern,
            "occurrence": args.occurrence,
        }
        if args.max_chars is None:
            excerpt = store.read_all(opened, args.key, **slicing)
        else:
            excerpt = opened.retrieve_document(args.key, max_chars=args.max_chars, **slicing)

    # Said out loud, because the content alone does not show it: a byte offset
    # inside a character reads from that character's first byte, and a person
    # who worked the number out by arithmetic is owed the news that it moved.
    # Not where a --pattern was given: that is *asked* to move the read, and
    # reporting it as a snap told a live run its search had landed inside a
    # character when what had happened was that it had found the pattern.
    if (
        args.byte_offset is not None
        and args.pattern is None
        and excerpt.byte_offset != args.byte_offset
    ):
        print(
            f"outrage: --byte-offset {args.byte_offset} is inside a character; "
            f"read from {excerpt.byte_offset}",
            file=sys.stderr,
        )

    # No trailing newline of our own: the content is the output, and a document
    # round-tripped through `outrage get > f` and `outrage set < f` has to come back
    # the same length it went in.
    out.write(excerpt.content)
    if excerpt.truncated:
        # Told in the unit it was asked in. A byte-addressed read has no
        # character *positions* -- converting one means decoding the prefix,
        # which is the cost a byte offset exists to avoid -- so the window it
        # reports and the flag it recommends are both in bytes. Telling a
        # caller to resume at a character offset the read never computed would
        # send them somewhere else in the document. The character *total* is a
        # separate question and some backends do now answer it, but a total is
        # not a position and mixing the two units in one sentence is how this
        # message went wrong before.
        if excerpt.next_byte_offset is not None and excerpt.next_offset is None:
            note = (
                f"{excerpt.returned} characters, bytes {excerpt.byte_offset} to "
                f"{excerpt.next_byte_offset} of {excerpt.total_bytes}; "
                f"more from --byte-offset {excerpt.next_byte_offset}"
            )
        else:
            note = (
                f"{excerpt.returned} of {excerpt.total} characters; "
                f"more from --offset {excerpt.next_offset}"
            )
        print(f"\noutrage: {note}", file=sys.stderr)
    return 0


def _set_command(args: argparse.Namespace, out: TextIO) -> int:
    """Write a document from an argument, a file, or standard input."""
    content = _content(args)
    with _open_table(args, create=True) as opened:
        _resolved(opened, args)
        written = opened.store_document(args.key, content, args.format, title=args.title)
        # Which file, resolved through the table rather than assumed to be the
        # root: a key below a mount point lands in that mount's store, and a
        # report naming the root would be naming a store the document is not in.
        where = _file_holding(opened, written)

    # The resolved path, not the one asked for: a mistyped --dir creates a
    # store rather than failing, so the only defence is saying where it went.
    print(f"{keys.displayed(written)}  {len(content)} characters in {where}", file=out)
    return 0


def _ingest_command(args: argparse.Namespace, out: TextIO) -> int:
    """Convert one local file and report the document and store it lands in."""
    with _open_table(args, create=True) as opened:
        _resolved(opened, args)
        converted = ingest.ingest_document(
            opened,
            args.source,
            args.key,
            title=args.title,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
        where = _file_holding(opened, converted.key)

    action = "would store" if converted.dry_run else "stored"
    title_at = (
        f"with title {converted.title!r} (not written)"
        if converted.title_key is None
        else f"with title {converted.title!r} at {keys.displayed(converted.title_key)}"
    )
    print(
        f"{action} {converted.source} at {keys.displayed(converted.key)}: "
        f"{converted.characters} characters as {converted.format}, {title_at}, in {where}",
        file=out,
    )
    return 0


def _make_contents_command(args: argparse.Namespace, out: TextIO) -> int:
    """Build a Markdown heading index and report the metadata destination."""
    with _open_table(args, create=True) as opened:
        _resolved(opened, args)
        made = contents.make_contents(opened, args.key, metadata_name=args.metadata_name)
        where = _file_holding(opened, made.metadata_key)

    print(
        f"stored {made.headings} headings from {keys.displayed(made.source_key)} "
        f"({made.source_characters} characters, {made.source_bytes} bytes) at "
        f"{keys.displayed(made.metadata_key)}: {made.characters} characters in {where}",
        file=out,
    )
    return 0


def _content(args: argparse.Namespace) -> str:
    """Content from --content, --file, or standard input, in that order.

    A file and a pipe are both read with ``newline=""``, so ``outrage set
    --file`` and ``outrage set < file`` store the line endings they were
    handed rather than LF -- a transfer carries content, it does not author it.
    Same reason as :func:`outrage.bulk._read_file`. ``--content`` is already a
    string and has nothing to convert.
    """
    if args.content is not None and args.file is not None:
        raise ConflictingSourceError("content-two-sources")
    if args.content is not None:
        return args.content
    if args.file is not None:
        path = Path(args.file).expanduser()
        try:
            with path.open(encoding="utf-8", newline="") as handle:
                return handle.read()
        except OSError as exc:
            raise ConflictingSourceError(
                "content-unreadable", path=str(path), reason=str(exc)
            ) from exc
    if sys.stdin.isatty():
        # Otherwise the command hangs on an empty terminal looking like it
        # worked, and the store ends up with an empty document at a good key.
        raise ConflictingSourceError("content-missing")
    return _untranslated(sys.stdin).read()


def _untranslated(stream: TextIO) -> TextIO:
    """``stream`` with line-ending translation turned off, where it can be.

    A real stdin or stdout is a :class:`io.TextIOWrapper` and can be told to
    stop translating. Anything else -- a :class:`io.StringIO` a test passes as
    its output, the stand-in pytest puts in place of stdin -- is handed back
    untouched, because it is not translating in the first place.
    """
    if isinstance(stream, io.TextIOWrapper):
        stream.reconfigure(newline="")
    return stream


class ConflictingSourceError(OutrageError):
    """Raised when the content to store cannot be determined from the arguments."""


def _ls_command(args: argparse.Namespace, out: TextIO) -> int:
    """List one level, or the whole subtree, printing as it goes."""
    shown = 0
    with _open_table(args) as opened:
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
    with _open_table(args) as opened:
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
    with _open_table(args) as opened:
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
    with _open_table(args, create=True) as opened:
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
        where = _file_holding(opened, keys.ROOT)
        if isinstance(opened, mounts.MountedStore) and opened.multiple:
            # An import spanning a table lands in more than one file, and which
            # documents went where is a routing question this line cannot
            # answer. It says how many stores were open instead, which is the
            # part a reader can act on.
            where += f", across {len(opened)} mounted stores"
    print(f"outrage: into {where}", file=sys.stderr)
    return status


def _copy_command(args: argparse.Namespace, out: TextIO) -> int:
    """Copy a bounded selection beneath another key in the mounted namespace."""
    with _open_table(args, create=True) as opened:
        _resolved_copy(opened, args)
        maximum = (
            keys.MAX_JOINED_SEGMENTS
            if isinstance(opened, mounts.MountedStore)
            else keys.MAX_SEGMENTS
        )
        source = keys.parse(args.source, max_segments=maximum).key
        target = keys.parse(args.target, max_segments=maximum).key
        # Refused here rather than inside the copy, which is a generator and
        # would raise on the first key rather than before the first write. The
        # rule itself is `bulk`'s, so the server refuses the same pairs.
        bulk.overlapping(source, target, reroot=args.reroot)
        key_range = store.KeyRange(**{name: getattr(args, name) for name in _RANGE_ARGUMENTS})
        # Read before the walk starts, so that anything written while the copy
        # runs is later than what a second call would be measured against.
        checked_at = store._now()
        transfers = opened.copy_from(
            opened,
            store.BoundedSubtree(source, args.depth),
            key_range=key_range,
            prefix=target,
            reroot=args.reroot,
            on_conflict=args.on_conflict,
            unchanged_since=args.unchanged_since,
            dry_run=args.dry_run,
        )
        status = _report_transfers(transfers, args, out, source_first=None)
        _report_watermark(args, checked_at)
        return status


def _report_transfers(
    transfers: Iterator[store.Transfer],
    args: argparse.Namespace,
    out: TextIO,
    *,
    source_first: bool | None,
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
        if source_first is None:
            line = f"{_verb(transfer.action, args.dry_run):<11} {left}"
        else:
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
    # status is the only part of that a script can see. A key left behind
    # because it changed counts here too: the guard did its job, and the copy
    # still did not do all of what it was asked, which is what a script that
    # goes on to delete the source has to notice.
    return (
        1
        if counted.get(store.FAILED) or counted.get(store.STOPPED) or counted.get(store.CHANGED)
        else 0
    )


def _report_watermark(args: argparse.Namespace, checked_at: str) -> None:
    """After a dry run, the time to hand back as ``--unchanged-since``.

    The other half of "look, then write only what has not moved": a preview
    that reports what would cross and not *when it looked* leaves the caller to
    type a timestamp of their own, which is the one part of this they cannot
    get right by hand -- too early refuses a run nothing is wrong with, and too
    late is a guard that was never armed.
    """
    if not args.dry_run:
        return
    # `--on-conflict overwrite` beside a watermark is the pairing `bulk`
    # refuses, so the repeat has to name the rule that takes one. Unconditional,
    # this recommended the call that fails. `rm` carries no --on-conflict.
    guarded = (
        " --on-conflict overwrite-unchanged"
        if getattr(args, "on_conflict", None) == store.OVERWRITE
        else ""
    )
    print(
        f"outrage: looked at {checked_at}; repeat with "
        f"--unchanged-since {checked_at}{guarded} to refuse if anything moves first",
        file=sys.stderr,
    )


#: What to call each action when counting them up, as against when reporting
#: one as it happens: "5 written" rather than "5 wrote".
_NOUNS = {
    store.READ: "packed",
    store.WROTE: "written",
    store.SKIPPED: "skipped",
    store.CHANGED: "changed since",
    store.FAILED: "failed",
    store.STOPPED: "stopped",
}


def _verb(action: str, dry_run: bool) -> str:
    """What to call an action that a dry run did not take."""
    if not dry_run:
        return action
    return {
        store.WROTE: "would write",
        store.READ: "would pack",
        store.SKIPPED: "would skip",
        store.CHANGED: "would leave",
        store.STOPPED: "would stop",
    }.get(action, action)


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
        with _open_existing(
            argparse.Namespace(directory=args.directory, filename=args.from_store)
        ) as opened:
            _resolved(opened, args)
            status = _report_transfers(
                bulk.pack(
                    target,
                    bulk.documents_from_store(opened, args.key),
                    overwrite=args.overwrite,
                    dry_run=args.dry_run,
                    byte_lengths=args.byte_lengths,
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
                byte_lengths=args.byte_lengths,
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
    with _open_table(args) as opened:
        _resolved(opened, args)
        checked_at = store._now()
        beneath = opened.descendant_count(args.key)
        if args.dry_run:
            # The delete's own selection, asked of the store: it walked the
            # subtree itself before, which is a second spelling of the rule and
            # drifted from it -- a plain delete takes the key's metadata unit
            # and the preview did not say so, so `rm notes/1 --dry-run` named
            # one key and `rm notes/1` removed two. The watermark is checked by
            # the same call, so a preview of a delete that would be refused
            # says so rather than listing keys it would never take.
            would_take = opened.delete(
                args.key,
                recursive=args.recursive,
                unchanged_since=args.unchanged_since,
                dry_run=True,
            )
            # Shaped like the run below it, line for line: the key itself
            # where the delete would take it, everything else as what lies
            # below, and the same sentence when there is nothing to take. A
            # headline naming a key the run never reports is the drift again,
            # one key smaller.
            if not would_take:
                print(f"nothing stored at {keys.displayed(args.key)}", file=out)
            if args.key in would_take:
                print(f"would delete {keys.displayed(args.key)}", file=out)
            # The whole subtree rather than one level of it, since that is what
            # the delete takes.
            below = [key for key in would_take if key != args.key]
            for shown, key in enumerate(below):
                if args.limit is not None and shown >= args.limit:
                    print(f"  and {len(below) - shown} more", file=out)
                    break
                print(f"  and below: {key}", file=out)
            _report_remainder(args, beneath, out, dry_run=True)
            _report_watermark(args, checked_at)
            return 0

        removed = opened.delete(
            args.key, recursive=args.recursive, unchanged_since=args.unchanged_since
        )

    for key in removed:
        print(f"deleted {keys.displayed(key)}", file=out)
    if not removed:
        print(f"nothing stored at {keys.displayed(args.key)}", file=out)
    # `beneath` unadjusted, and the same number the dry run above passes. It
    # counts what a plain delete would *keep*, which is already what is left
    # once one has happened; a recursive delete has no remainder to report at
    # all, and `_report_remainder` decides that for itself. A `len(removed)`
    # correction here would apply only when `recursive` -- which is exactly when
    # nothing is printed -- so it could never reach an output.
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


def _mounts_command(args: argparse.Namespace, out: TextIO) -> int:
    """Report the table this command line names, without opening any of it.

    The gap this closes: **a read-write mount naming a store that is not there
    is created**, empty, by the first command that opens the table - and then
    reads exactly like a store with nothing in it yet. ``--mount-ro`` refuses
    for that reason and the read-write half never could, because creating is
    what a first write needs. A configuration file makes it likelier rather
    than less: the name was typed on a different day, possibly by somebody
    else, possibly for a different checkout.

    So this opens nothing. It resolves the same table ``_open_table`` would,
    asks the filesystem whether each store is there, and says where each mount
    was written down - which is the other question the splice created, since a
    table is now a merge of the default file, each ``--mount-config`` and what
    was typed.

    Non-zero when the table would not open: a read-only mount that is missing,
    or two mounts at one point. A read-write mount that is not there is
    reported and is not a failure - it is what a store looks like before its
    first write, and telling the two apart is the whole job.
    """
    directory = store.resolve_directory(args.directory)
    written, front = args.written or ([], 0)
    sources = {
        origin.mount: (origin.file, origin.source)
        for origin in mountfile.origins(written, directory=directory, front=front)
    }

    # The root is the one entry nobody has to name, so it is the one whose
    # source may be neither a file nor the line: "default" is a third answer
    # and saying "the command line" instead would be a small lie in the column
    # that exists to stop people guessing.
    named = {"--store", mountfile.ROOT_FLAG}
    typed = any(token.partition("=")[0] in named for token in written)
    rows = [
        _mount_row(
            directory,
            keys.ROOT,
            _root(args),
            MOUNT_KIND,
            sources,
            unnamed=mountfile.TYPED_SOURCE if typed else "default",
        )
    ]
    seen = {keys.ROOT}
    failed = False
    if args.mount_docs:
        # Named by where it really is, absolute, rather than by a file inside
        # --dir: it is in the installation, which is the whole reason it is a
        # flag rather than a spec. "missing" here is a build that dropped the
        # tree, and it is a failure for the same reason a read-only mount that
        # names nothing is one.
        state = "ok" if shipped.available() else "missing"
        rows.append(
            (
                mountfile.DOCS_MOUNT,
                str(shipped.tree()),
                READ_ONLY_MOUNT_KIND,
                state,
                sources.get(mountfile.DOCS_MOUNT, ("", mountfile.TYPED_SOURCE))[1],
            )
        )
        seen.add(mountfile.DOCS_MOUNT)
        failed = failed or state == "missing"
    for specs, kind in ((args.mounts, MOUNT_KIND), (args.read_only_mounts, READ_ONLY_MOUNT_KIND)):
        for spec in specs:
            point, named = mounts.parse_spec(spec)
            row = _mount_row(directory, point, named, kind, sources)
            if point in seen:
                # Reported rather than raised, unlike everywhere else: a report
                # that stopped at the first thing wrong with a table would be
                # the least useful moment to stop.
                row = (*row[:3], "duplicate", row[4])
            seen.add(point)
            rows.append(row)
            # "would create" is not one of these. A store that is not there yet
            # is what every store looks like before its first write, and a
            # check that failed on the ordinary case is one people stop
            # running. The column says it; the status does not.
            failed = failed or row[3] in ("missing", "duplicate")

    widths = [max(len(row[i]) for row in rows) for i in range(4)]
    for point, filename, kind, state, source in sorted(rows, key=lambda r: keys.sort_form(r[0])):
        line = (
            f"{point:<{widths[0]}}  {filename:<{widths[1]}}  "
            f"{kind:<{widths[2]}}  {state:<{widths[3]}}  {source}"
        )
        print(line.rstrip(), file=out)
    return 1 if failed else 0


def _mount_row(
    directory: Path,
    point: str,
    spec: mounts.Spec,
    kind: str,
    sources: dict[str | None, tuple[str, str]],
    *,
    unnamed: str = mountfile.TYPED_SOURCE,
) -> tuple[str, str, str, str, str]:
    """One mount, as the five things worth knowing about it before it opens.

    The file column is the argument's value half rather than its path alone, so
    a mount that names a backend says so here: ``docs,type=files`` is a
    different mount from ``docs``, and a report that showed them alike would
    hide the one thing about it that cannot be inferred from the name.
    """
    filename = mounts.unparse(spec)
    if store.store_file(directory, spec.path).exists():
        state = "ok"
    elif kind == READ_ONLY_MOUNT_KIND:
        # The refusal `open_mounts` would make, said here instead of at the
        # moment a server failed to start inside somebody's client.
        state = "missing"
    else:
        state = "would create"

    # A file only accounts for this mount if it named the store this mount
    # actually has: the root arrives as `--store`, which no file wrote, and an
    # entry a later source replaced is not what is being reported.
    wrote = sources.get(None if point == keys.ROOT else point)
    source = wrote[1] if wrote is not None and wrote[0] == filename else unnamed
    return (
        keys.displayed(point),
        filename,
        "root" if point == keys.ROOT else kind,
        state,
        source,
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
            print(f"  {action.action}: {action.before} -> {action.after} {action.unit}", file=out)
        if not done:
            # An empty list is a backend saying there is nothing its storage
            # could need, which is not the same as finding nothing wrong. Said
            # rather than left as a blank, so the difference reaches the user.
            print(
                f"  nothing to repair: a {report.backend} store has no state a repair could move",
                file=out,
            )

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
        print(
            "  " + ", ".join(f"{label} {value}" for label, value in report.details.items()),
            file=out,
        )
    for problem in report.problems:
        print(f"  {problem.severity}: {problem.summary}", file=out)
        if problem.detail:
            print(f"    {problem.detail}", file=out)
    if report.sound and not report.problems:
        print("  nothing wrong", file=out)


def _open_existing(args: argparse.Namespace):
    """Open a store that is already there, refusing to create one.

    ``FileStore.__init__`` creates what is missing, so a command acting on an
    existing store has to check first - otherwise a mistyped --dir reports a
    perfectly healthy empty store, which is a wrong answer delivered as a clean
    bill of health.
    """
    root = _root(args)
    directory = maintenance.require_store(store.resolve_directory(args.directory), root.path)
    return store.open_store(directory, filename=root.path, backend=root.type)


@contextlib.contextmanager
def _open_table(args: argparse.Namespace, *, create: bool = False) -> Iterator[store.Store]:
    """Open every store this command acts across, as the one namespace.

    What the mounted subcommands use in place of :func:`_open_existing`. With
    nothing mounted it *is* :func:`_open_existing`, and deliberately, not as an
    optimisation: a mount table requires a writable store at the root, since
    the root owns every key no mount claims, so building one unconditionally
    would make ``outrage ls --store ref.parquet`` -- reading a packed store,
    which is what packing one is for -- fail on a table it never asked for.
    ``MountedStore.__init__`` says as much where it refuses: to simply read
    such a store, open it directly, which is what this does.

    ``create`` is the same distinction ``_open_existing`` draws, and it is
    about the *root* mount alone. A read of a store that is not there is a
    mistyped ``--dir`` reported as an empty store; a first write has to be able
    to make the store it writes to. Every other mount is opened the way
    ``open_mounts`` opens it either way, which is to say a read-only one must
    already exist and a read-write one is created.
    """
    directory = store.resolve_directory(args.directory)
    root = _root(args)
    if not create:
        maintenance.require_store(directory, root.path)
    if not (args.mounts or args.read_only_mounts or args.mount_docs):
        with store.open_store(directory, filename=root.path, backend=root.type) as opened:
            yield opened
        return
    with mounts.open_mounts(
        directory,
        args.mounts,
        args.read_only_mounts,
        root_mount=root,
        # Refused rather than warned about when the tree is not there, unlike
        # the server: here somebody typed the flag, and a mount that silently
        # was not made is the failure `--mount-ro` refuses for.
        attached=shipped.attached() if args.mount_docs else {},
    ) as table:
        for mount in table.shadowing():
            # The server's warning, in the same words and for the same reason:
            # the configuration is usable and the keys that vanish are in a
            # store the operator can still reach, so refusing would be worse.
            print(
                f"outrage: warning: the store at {mount.name!r} shadows keys already "
                f"held there; they are unreachable while it is mounted",
                file=sys.stderr,
            )
        yield table


def _file_holding(opened: store.Store, key: str) -> str:
    """The store file a key lands in, for a command that reports where it went.

    A table is several files, so "the store" is not a thing a report can name
    without asking which key it means. Falls back to the store's own repr for
    anything that is not a file, which nothing on this command line currently
    is.
    """
    owner = opened.resolve(key).store if isinstance(opened, mounts.MountedStore) else opened
    return str(owner.path) if isinstance(owner, store.FileStore) else repr(owner)


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

    still = config_module.mounts_in(change.entry.get("args", []))
    if still:
        # Not migrated, on purpose, and it goes on working: the entry's options
        # come after the file's and so win. Said out loud because a table in
        # two places, with only one of them the place anybody looks, is how
        # somebody edits the file and wonders why nothing changed.
        print(
            f"  note: this entry names {', '.join(sorted(set(still)))} in its args, "
            f"which is where a mount table used to live. What is there overrides "
            f"{mountfile.DEFAULT_NAME}, and removing it is an edit to this file.",
            file=out,
        )


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


def _flag(argument: str, value: Any = None) -> str:
    """An argument as this front end spells it, for :func:`outrage.messages.render`.

    ``argparse``'s own convention read backwards: a ``dest`` is its long option
    with the dashes turned into underscores, so the way back is mechanical. It
    is a rule rather than a table because a table is a second place to remember
    a flag, and ``test_messages`` keeps the rule honest by checking every flag a
    message can produce against the parser's own options -- inventing
    ``--against`` for an argument only the tools take would be this same defect
    one level down.

    The defect it exists for: a message spelled for the tools told a command
    line user to "Pass on_conflict='overwrite-unchanged'", which is not
    something anyone can type.
    """
    flag = f"--{argument.replace('_', '-')}"
    return flag if value is None else f"{flag} {value}"


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
    try:
        # Inside the try, because parsing now reads a mount configuration file
        # and a file that will not parse is an answer about the configuration,
        # rendered like any other rather than tracebacked.
        args = parse_args(argv)
        # `outrage get > file` writes the document and nothing else, so the
        # stream it goes to must not translate LF on the way out. This is the
        # write side of what `_content` does on the read side: a transfer hands
        # back the endings the document holds. The cost,
        # and it is a judgement rather than a mechanical fix: the command
        # line's own messages end in LF on Windows too, which is what every
        # other tool there does. Writing content to `sys.stdout.buffer`
        # instead would break every test that passes its own stream.
        return args.handler(args, _untranslated(out or sys.stdout))
    except OutrageError as exc:
        # One base rather than a tuple that grows with each command. A failure
        # that is not a OutrageError is a bug in outrage, and a traceback is the right
        # output for a bug.
        #
        # Rendered here, because this is a front end and the error is not. The
        # command line opens one store directory and knows nothing about a
        # mount table, so a key names itself: the default namer is the correct
        # one here and the mount-aware one would be wrong. An *argument* is the
        # other way about -- the default spelling is the tools', and this front
        # end has to say so. See `messages`.
        print(f"outrage: {messages.render(exc, spell=_flag)}", file=sys.stderr)
        return 1


__all__ = [
    "MOUNTED",
    "ConflictingSourceError",
    "argument_parser",
    "main",
    "parse_args",
]
