"""MCP server exposing the document store.

A thin wrapper: argument shaping and result shaping only. All behaviour lives
in :mod:`outrage.store`, so it can be exercised without a protocol harness.

**Including the mount table.** More than one store behind one key namespace is
not this module's work -- not the routing, the segment list a subtree is read
as, the merge of a level with the mounts standing in it, nor the cursor
recomputed at every boundary. All of it is
:class:`~outrage.mounts.MountedStore`, which *is* a
:class:`~outrage.store.Store`, so every handler here calls one store method and
shapes the answer. What is left that knows about mounts is configuration
(``--mount`` at startup) and the two sentences a result carries about what a
delete would not reach -- because those are sentences, and a sentence is a front
end's business.

Two things a front end still does before anything routes. ``?last`` is resolved
against the whole namespace, since a ``?last`` naming a mount decides which store
answers; and an error is rendered, by :mod:`outrage.messages`, from the code and
facts it carries.
"""

from __future__ import annotations

import argparse
import dataclasses
import functools
import itertools
import os
import sys
import time
from collections.abc import Callable, Generator, Sequence
from typing import Annotated, Any, Literal

from mcp.server import MCPServer
from mcp.server.context import CallNext, HandlerResult, ServerRequestContext
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.mcpserver.utilities.func_metadata import ArgModelBase
from mcp.types import ToolAnnotations
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    model_serializer,
)

from . import (
    __version__,
    bulk,
    contents,
    eventlog,
    ingest,
    keys,
    messages,
    mountfile,
    remount,
    shipped,
)
from . import info as info_module
from . import mounts as mounts_module
from . import store as store_module
from .errors import OutrageError
from .eventlog import EventLog
from .mounts import MountedStore
from .notes import Note
from .store import (
    DEFAULT_BULK_MAX_CHARS,
    DEFAULT_MAX_CHARS,
    BoundedSubtree,
    Encoding,
    Excerpt,
    Format,
    KeyRange,
    MatchMode,
    SearchCombination,
    SearchCriterion,
    SearchTarget,
    Store,
    _now,
)


def _scope(key: str | None) -> str:
    """The key a scope argument names, with an omitted one meaning the root.

    A client that sends `null` for a key it did not fill in means the same as
    one that left it out, and both mean the whole store -- which is the root,
    now that the root is a key. Resolved here so the result echoes the scope
    that was actually used rather than the absence the caller sent.
    """
    return "" if key is None else key


def _reported[**P, T](function: Callable[P, T]) -> Callable[P, T]:
    """Render a :class:`OutrageError` from a tool into the sentence a caller reads.

    The boundary the whole of :mod:`outrage.messages` exists for. Below here an
    error carries facts and a code; a caller gets one line, and gets it with
    keys named the way *this* front end names them -- which for a server with a
    mount table is not what the store that raised it would have said.

    Wrapped rather than caught inside each tool so that no tool can be added
    without it: forgetting would surface a developer rendering to a user, which
    is exactly the failure ``errors.__str__`` is shaped to make obvious.

    The default namer is right for everything raised *at* this boundary -- a
    bad key, a malformed cursor, a mount refusing a write -- because those name
    keys the caller sent. A store reached through a mount is the exception, and
    ``retrieve_document`` names the mount explicitly for it.
    """

    @functools.wraps(function)
    def reported(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return function(*args, **kwargs)
        except OutrageError as exc:
            raise ToolError(messages.render(exc)) from exc

    return reported


def _named_key(table: MountedStore, key: str | None, *, allow_wildcard: bool = False) -> str:
    """The key a tool was given: ``?last`` resolved, normalised, root for None.

    Resolved **here** and not in the table, and before anything routes: a
    ``?last`` in the part of a key that names a mount decides which store
    answers, so a table asked to route one has not been told enough to route it.

    Normalised too, because this is the key every tool echoes back. A caller who
    wrote ``context/?last`` is told which context they got, for the same reason a
    ``?`` reports the number it allocated.

    At the joined bound, since a key in this namespace may name a mount point
    and a key inside it. The store bound is the mounted stores' own, and
    ``keys.MAX_JOINED_SEGMENTS`` being twice it is what makes every such key
    nameable from out here.
    """
    resolved = keys.resolve_last(
        _scope(key), table.last_child, max_segments=keys.MAX_JOINED_SEGMENTS
    )
    return keys.parse(
        resolved, max_segments=keys.MAX_JOINED_SEGMENTS, allow_wildcard=allow_wildcard
    ).key


def _say(result: dict[str, Any], notes: list[Note]) -> None:
    """Put what the tools say about each note onto the result's ``note``.

    Which situations arose is a ``notes_for_*`` function in
    :mod:`outrage.bulk`, and how this reader hears them is
    :data:`outrage.messages.MCP`; neither is decided here. That is the whole of
    the change: the sentences used to be built in this file, where the other
    front end could not reach them and nothing checked them against the fields
    printed beside them.

    A table may render a note as ``None``, meaning this reader is not told.
    The tools are silent about none of them today, and the loop does not
    assume that.

    Each sentence is appended rather than assigned, and this is the only place
    the field is written. Three separate things want to say something on one
    delete -- keys kept back by a non-recursive one, keys with no name from
    outside, and mounts it stopped at -- and each used to assign, so the last
    to run erased the others. That is the failure mode of every note here: a
    caller reads a complete-looking answer and does not know what it left out.

    **A sentence that follows another is capitalised here**, not in the table.
    The tables are mixed -- some notes open with a word, some with a count, some
    with a capital -- and each reads correctly on its own, which is how they
    were written and checked. What did not read correctly is the *join*: until
    the mount tools nothing produced two notes on one result, and the day
    something did, an unmount answered "... without anything being written. this
    table lasts as long as this server", which is one run-on sentence to a
    reader. Fixed at the join because that is where the defect is: a table
    entry is a sentence and does not know what will precede it. John's call,
    2026-09-06, over a rule that every note must be written capitalised --
    which would have edited every existing template to fix a fault none of them
    has.
    """
    for note in notes:
        said = messages.MCP.render(note)
        if said is None:
            continue
        if result.get("note"):
            result["note"] = f"{result['note']} {said[:1].upper()}{said[1:]}"
        else:
            result["note"] = said


def _forbid_unknown_arguments() -> None:
    """Make an unrecognised tool argument an error rather than a silent no-op.

    The SDK builds each tool's argument model on ``ArgModelBase``, which leaves
    pydantic's default ``extra="ignore"``, so an argument the server does not
    know is dropped before the tool function is entered - the tool cannot even
    see that it happened. A caller then gets a success result for a call that
    did only part of what it asked, which is how a server running stale code
    comes to look like one running current code.

    Setting the config here, before any tool is registered, propagates to every
    argument model the SDK creates afterwards. It also puts
    ``additionalProperties: false`` into the published schemas, so a client that
    validates catches the mistake before the call is even made.

    This reaches into the SDK's internals because it offers no supported way to
    ask for strict tool arguments, though it does use ``extra="forbid"`` for its
    own resource models. ``test_unknown_arguments_are_rejected`` fails loudly if
    a future SDK stops honouring this, rather than letting the server quietly
    fall back to accepting anything.
    """
    ArgModelBase.model_config["extra"] = "forbid"


_forbid_unknown_arguments()

#: What one tool call may return. The store offers pagination and takes no view;
#: this is the view. A tool answers into a context window, so an unwitting call
#: must not be able to fill one, and every capped result says what it was part
#: of.
#:
#: Two caps rather than one tuned number, because the two failures are
#: different sizes. Characters are what fill a context window, so that is the
#: cap that binds a read of real documents: twenty thousand is ten documents at
#: the bulk cap. The item count is what keeps a page comprehensible when the
#: items are tiny -- a hundred titles is a survey a model can hold, and it is
#: the whole store for the session-scale case these defaults are mostly serving.
DEFAULT_ITEM_LIMIT = 100

#: Candidate documents one search call examines before returning a cursor.
DEFAULT_SEARCH_SCAN_LIMIT = 20

#: The character half of that pair: what one page may total before it stops,
#: whatever the item count still allows.
DEFAULT_PAGE_CHARS = 20000

#: How many documents one `copy_tree` call carries before it stops and hands
#: back a cursor. Larger than a page limit on purpose: this bounds a *run*
#: rather than a result, since the caller is told counts however many crossed
#: and pays nothing per document for the ones that did. What it protects is the
#: length of one call, against a subtree nobody has counted.
DEFAULT_COPY_LIMIT = 500

#: Failed transfers named in a copy's result before it stops listing and only
#: counts. A copy reports statistics because it may cross more keys than a
#: result can hold, and a bare `failed: 12` is a number nobody can act on: the
#: sample is what says *what* went wrong, at a size that cannot grow with the
#: store.
COPY_FAILURE_SAMPLE = 5

#: Keys named in `without_meta` before it stops listing and only counts. Its
#: job is to warn that a survey under-reports the store, and a count does that
#: at any size; at reference scale the list would *be* the corpus.
WITHOUT_META_SAMPLE = 10


class _ToolResult(BaseModel):
    """A validated tool result which does not invent absent optional fields."""

    model_config = ConfigDict(extra="forbid")

    @model_serializer(mode="wrap")
    def _omit_unset(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        serialized = handler(self)
        return {name: value for name, value in serialized.items() if name in self.model_fields_set}


class _ExcerptResult(_ToolResult):
    key: Annotated[str, Field(description="The normalized key read")]
    content: Annotated[str, Field(description="The returned document content")]
    format: Annotated[str | None, Field(description="The stored content format")]
    updated_at: Annotated[str, Field(description="When the document was last written")]
    offset: Annotated[
        int | None,
        Field(
            description=(
                "Character offset where this excerpt starts, absent when the "
                "read was addressed in bytes"
            )
        ),
    ] = None
    returned: Annotated[int, Field(description="Characters returned in this excerpt")]
    total: Annotated[
        int | None,
        Field(
            description=(
                "Total characters in the document. Absent only where the read "
                "was addressed in bytes and the store would have to read the "
                "whole document to count them; total_bytes is always given"
            )
        ),
    ] = None
    next_offset: Annotated[int | None, Field(description="Where to resume, or null at the end")] = (
        None
    )
    byte_offset: Annotated[
        int,
        Field(
            description=(
                "Byte offset where this excerpt starts, and where a byte offset "
                "given was snapped back to if it fell inside a character"
            )
        ),
    ]
    total_bytes: Annotated[int, Field(description="Total UTF-8 bytes in the document")]
    next_byte_offset: Annotated[
        int | None,
        Field(description="Where to resume in bytes, or null at the end"),
    ] = None
    truncated: Annotated[bool, Field(description="Whether part of the document remains unread")]


class _StoreDocumentResult(_ToolResult):
    key: Annotated[str, Field(description="The normalized key written")]
    stored: Annotated[int, Field(description="Characters stored")]
    generated: Annotated[bool, Field(description="Whether the store generated part of the key")]
    title_key: Annotated[
        str | None,
        Field(description="Key where the supplied title was stored, when one was supplied"),
    ] = None
    previous: Annotated[
        int | None,
        Field(
            description=(
                "Previous document size when the write was checked against an "
                "exported file, or null when the key held nothing"
            )
        ),
    ] = None
    unchecked_code: Annotated[
        str | None,
        Field(
            description=(
                "Why the write was not compared with what was exported, when "
                "'against' was given and 'overwrite' allowed it through "
                "uncompared: 'no-record' when nothing beside the file said what "
                "it held, 'other-key' when the record names the key it was "
                "exported from"
            )
        ),
    ] = None
    note: Annotated[str | None, Field(description="Important qualification of the result")] = None


class _IngestDocumentResult(_ToolResult):
    source: Annotated[str, Field(description="The absolute local source file converted")]
    key: Annotated[str, Field(description="The normalized destination key")]
    title: Annotated[str, Field(description="The title selected for the document")]
    characters: Annotated[int, Field(description="Markdown characters produced")]
    format: Annotated[
        Literal["markdown"], Field(description="The document format, always markdown")
    ]
    title_key: Annotated[
        str | None,
        Field(description="The metadata key written for the title, absent on a dry run"),
    ] = None
    dry_run: Annotated[bool, Field(description="Whether conversion was performed without writing")]


class _MakeContentsResult(_ToolResult):
    source_key: Annotated[str, Field(description="The normalized Markdown source key")]
    metadata_key: Annotated[str, Field(description="The metadata key written")]
    headings: Annotated[int, Field(description="Markdown headings found")]
    source_characters: Annotated[int, Field(description="Source characters scanned")]
    source_bytes: Annotated[
        int,
        Field(
            description=(
                "UTF-8 bytes those characters occupy, which the second number "
                "on each heading line is an offset into"
            )
        ),
    ]
    characters: Annotated[int, Field(description="Contents characters stored")]


class _EntryResult(_ToolResult):
    key: Annotated[str, Field(description="The listed key")]
    kind: Annotated[
        str, Field(description="Document, metadata, implicit, mount or read-only mount")
    ]
    size: Annotated[int | None, Field(description="Stored characters, when this key has content")]
    format: Annotated[str | None, Field(description="Stored content format, when applicable")]
    updated_at: Annotated[str | None, Field(description="Last write time, when applicable")]


class _SearchCriterionArgument(BaseModel):
    """A closed criterion object accepted by ``find_documents``."""

    model_config = ConfigDict(extra="forbid")

    pattern: Annotated[str, Field(description="Text or expression to match", min_length=1)]
    match: Annotated[
        MatchMode, Field(description="Literal contains, exact whole line, or Python regex")
    ]
    target: Annotated[
        SearchTarget, Field(description="Search the document body or its direct metadata values")
    ]
    meta_name: Annotated[
        list[str] | None,
        Field(
            description="Metadata names to search; omit for all direct metadata",
            min_length=1,
        ),
    ] = None


class _MatchWitnessResult(_ToolResult):
    criterion: Annotated[int, Field(description="Zero-based request criterion satisfied")]
    source_key: Annotated[str, Field(description="Exact document or metadata key that matched")]
    source: Annotated[SearchTarget, Field(description="Whether body or metadata content matched")]
    start: Annotated[int, Field(description="Inclusive character offset of the first match")]
    end: Annotated[int, Field(description="Exclusive character offset of the first match")]


class _DocumentMatchResult(_ToolResult):
    document: Annotated[_EntryResult, Field(description="The selected document")]
    witnesses: Annotated[
        list[_MatchWitnessResult], Field(description="One first match per satisfied criterion")
    ]


class _FindDocumentsResult(_ToolResult):
    key: Annotated[str, Field(description="The normalized subtree key")]
    matches: Annotated[
        list[_DocumentMatchResult], Field(description="Matches in this candidate window")
    ]
    matched: Annotated[int, Field(description="Documents matched in this window")]
    matched_chars: Annotated[
        int, Field(description="Body characters across documents matched in this window")
    ]
    scanned: Annotated[int, Field(description="Candidate documents examined in this window")]
    total_candidates: Annotated[
        int, Field(description="Candidate documents in the whole bounded selection")
    ]
    total_candidate_chars: Annotated[
        int, Field(description="Body characters across the whole candidate selection")
    ]
    next_cursor: Annotated[
        str | None, Field(description="Last candidate examined, or null when search is complete")
    ]


class _ListKeysResult(_ToolResult):
    key: Annotated[str, Field(description="The normalized key listed")]
    entries: Annotated[list[_EntryResult], Field(description="This page of immediate children")]
    returned: Annotated[int, Field(description="Entries returned in this page")]
    total: Annotated[int, Field(description="Entries in the whole level")]
    total_chars: Annotated[int, Field(description="Characters stored across the whole level")]
    next_cursor: Annotated[str | None, Field(description="Where to resume, or null at the end")]


class _MissingMetaResult(_ToolResult):
    total: Annotated[int, Field(description="Documents carrying none of the requested metadata")]
    total_chars: Annotated[int, Field(description="Characters stored across those documents")]
    sample: Annotated[list[str], Field(description="A bounded sample of their keys")]


class _GetDocumentsResult(_ToolResult):
    key: Annotated[str, Field(description="The normalized subtree key")]
    count: Annotated[int, Field(description="Documents returned in this page")]
    returned: Annotated[int, Field(description="Documents returned in this page")]
    total: Annotated[int, Field(description="Documents in the whole selection")]
    total_chars: Annotated[int, Field(description="Characters stored across the whole selection")]
    next_cursor: Annotated[str | None, Field(description="Where to resume, or null at the end")]
    documents: Annotated[list[_ExcerptResult], Field(description="This page of documents")]
    without_meta: Annotated[
        _MissingMetaResult | None,
        Field(description="Documents omitted by a metadata survey, when one was requested"),
    ] = None


class _KeysMissingMetaResult(_ToolResult):
    key: Annotated[str, Field(description="The normalized subtree key")]
    keys: Annotated[list[str], Field(description="This page of keys missing the metadata")]
    returned: Annotated[int, Field(description="Keys returned in this page")]
    total: Annotated[int, Field(description="Keys in the whole selection")]
    total_chars: Annotated[int, Field(description="Characters stored across the whole selection")]
    next_cursor: Annotated[str | None, Field(description="Where to resume, or null at the end")]


class _DeleteKeysResult(_ToolResult):
    key: Annotated[str, Field(description="The normalized key asked for")]
    deleted: Annotated[list[str], Field(description="Keys actually deleted")]
    count: Annotated[int, Field(description="Number of keys deleted")]
    remaining: Annotated[
        int | None,
        Field(description="Descendants kept by a non-recursive delete, when any remain"),
    ] = None
    mounts_kept: Annotated[
        list[str] | None,
        Field(description="Read-only mounted stores which refused the delete, when any"),
    ] = None
    checked_at: Annotated[
        str | None,
        Field(
            description=(
                "When this dry run looked, to pass back as `unchanged_since` on the real delete"
            )
        ),
    ] = None
    dry_run: Annotated[
        bool | None,
        Field(description="True when this result reports a dry run and nothing was deleted"),
    ] = None
    note: Annotated[str | None, Field(description="Important qualification of the result")] = None


class _CopyFailureResult(_ToolResult):
    key: Annotated[str | None, Field(description="Destination key that failed")]
    reason: Annotated[str | None, Field(description="Why it failed")]


class _CopyTreeResult(_ToolResult):
    source: Annotated[str, Field(description="The normalized source key")]
    target: Annotated[str, Field(description="The normalized target key")]
    copied: Annotated[dict[str, int], Field(description="Transfer counts by outcome")]
    documents: Annotated[int, Field(description="Documents considered in this call")]
    characters: Annotated[int, Field(description="Characters considered in this call")]
    failures: Annotated[list[_CopyFailureResult], Field(description="A bounded sample of failures")]
    changed: Annotated[
        list[str] | None,
        Field(
            description=(
                "Keys left alone because they changed since `unchanged_since`, when any did"
            )
        ),
    ] = None
    checked_at: Annotated[
        str | None,
        Field(
            description=(
                "When this dry run looked, to pass back as `unchanged_since` on the real copy"
            )
        ),
    ] = None
    next_cursor: Annotated[str | None, Field(description="Where to resume, or null at the end")]
    dry_run: Annotated[
        bool | None,
        Field(description="True when this result reports a dry run and nothing was written"),
    ] = None
    mounts_kept: Annotated[
        list[str] | None,
        Field(description="Read-only mounted stores which refused writes, when any"),
    ] = None
    note: Annotated[str | None, Field(description="Important qualification of the result")] = None


class _DocumentEditResult(_ToolResult):
    key: Annotated[str, Field(description="The normalized document key")]
    path: Annotated[str, Field(description="The exported file path")]
    exported: Annotated[
        int | None, Field(description="Characters exported, when exporting a document")
    ] = None
    format: Annotated[
        str | None, Field(description="The document format, when exporting a document")
    ] = None
    stored: Annotated[
        int | None, Field(description="Characters stored, when importing an edited file")
    ] = None
    previous: Annotated[
        int | None, Field(description="Previous document size, or null when it did not exist")
    ] = None
    unchecked_code: Annotated[
        str | None,
        Field(
            description=(
                "Why an import was not compared with what was exported, when "
                "'overwrite' allowed it through uncompared: 'no-record' when "
                "there was no export record, 'other-key' when the file came "
                "from another key and no 'against' file was given"
            )
        ),
    ] = None
    note: Annotated[str | None, Field(description="Important qualification of the result")] = None


class _MountInfoResult(_ToolResult):
    mount: Annotated[str, Field(description="The mount point, '/' for the root")]
    path: Annotated[
        str | None,
        Field(
            description=(
                "Absolute path of the file this store is kept in, or null for a "
                "store that keeps none"
            )
        ),
    ]
    kind: Annotated[str, Field(description="'root', 'mount' or 'read-only mount'")]
    read_only: Annotated[bool, Field(description="Whether this server refuses writes routed here")]


class _MountsResult(_ToolResult):
    """The namespace after a mount or an unmount, as its stores.

    The whole table rather than the one mount that changed, because what a
    caller has to know next is which store now answers for a key -- and a mount
    can shadow, replace, or reveal what another was hiding, none of which is
    visible in an answer about itself.
    """

    mounts: Annotated[
        list[_MountInfoResult],
        Field(description="The stores behind the namespace, as they now are"),
    ]
    note: Annotated[str | None, Field(description="Important qualification of the result")] = None


class _InfoResult(_ToolResult):
    version: Annotated[str, Field(description="The outrage version this server is running")]
    python: Annotated[
        str,
        Field(
            description=(
                "The interpreter running it, for running the command line in the same environment"
            )
        ),
    ]
    prefix: Annotated[str, Field(description="The Python environment that interpreter belongs to")]
    command: Annotated[
        list[str],
        Field(
            description=(
                "The `outrage` command line entry point in that environment, empty when it has none"
            )
        ),
    ]
    directory: Annotated[
        str | None,
        Field(description="The store directory holding the stores, the log and the backups"),
    ]
    mount_config: Annotated[
        list[str],
        Field(description="The mount configuration files read, in the order they were read"),
    ]
    log: Annotated[
        str | None,
        Field(description="Where this server records what it does, or null when it does not"),
    ]
    log_content: Annotated[
        str | None,
        Field(description="How much document text that log keeps: 'none', 'excerpt' or 'full'"),
    ]
    mounts: Annotated[
        list[_MountInfoResult],
        Field(description="The stores behind the namespace, as they were opened"),
    ]


#: What a client is assumed to deliver of a server's instructions before it
#: cuts them. An observation of one client, not a protocol guarantee: Claude
#: Code truncates at 2048 characters, measured on 2026-08-19 across this
#: project's own transcripts and again the day after. Whether the number is
#: fixed, shared between servers, or really a token count is unestablished -
#: 2047 characters landing on a power of two is the argument for characters.
#: Everything ordered before this point survives on that client; everything
#: after it may not, and nothing may be *only* said after it.
DELIVERY_BUDGET = 2048

#: Where the delivered text is kept, below the shipped documentation's root.
#: Prose in a document rather than a string literal here: it is diffable,
#: carries a title, and is readable with `read_document` like anything else
#: -- including by a session that was cut off mid-instructions and wants the
#: rest of them. The document at `outrage/skills` says which file is which.
SKILLS = "skills"

#: Where the MCP tools' descriptions are kept, below the shipped documentation
#: root. Like :data:`SKILLS`, these are documents rather than string literals:
#: they are diffable, readable through the mounted manual, and shipped in the
#: same package as the code that registers them.
TOOLS = "tools"


#: The documents delivered, in the order they are sent. The split is a delivery
#: order and not a subject: a client cuts these instructions at a length it does
#: not announce, so `essentials` is what has to survive the cut -- the grammar of
#: a key, how one is allocated, and that a listing is a page -- and `tail` is
#: chosen so that every part of it is recoverable somewhere a session reaches
#: anyway: a tool description, the packaged agent skill, or a failure that
#: explains itself. That test is the whole of what decides which document a
#: sentence belongs in, and `outrage/skills` is where it is written down for
#: whoever edits them.
DELIVERED = ("essentials", "tail")


@functools.cache
def skill(name: str) -> str:
    """The text of one delivered document, read from the installed files.

    The files rather than the mount, for two reasons. This is needed at import,
    to size the readme against ``DELIVERY_BUDGET``, which is before any store
    is opened; and a mount table naming ``outrage`` overrides the shipped
    documentation silently, which would otherwise let a project's own store
    decide what this server says about itself.
    :func:`outrage.shipped.tree` is the same directory the mount reads, so the
    two never disagree about what the text is.

    Read once per process, which is what the text itself promises a session:
    instructions are sent when a client connects, so a file edited afterwards
    reaches the next server rather than this one.

    A missing file is the build failure :func:`outrage.shipped.available`
    exists to notice, and is raised rather than served as instructions with a
    hole in them.
    """
    path = shipped.tree() / SKILLS / f"{name}.md"
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise shipped.DocumentsError("documents-not-installed", path=str(path)) from exc


@functools.cache
def tool_description(name: str) -> str:
    """The description of one MCP tool, read from the installed documents.

    The same contract as :func:`skill`: the installed file is read once per
    process, before the tool is registered, and a build that dropped it fails
    loudly instead of exposing a tool with an empty or stale description.
    Keeping the description in the documentation tree also makes the bytes a
    session receives available at ``outrage/tools/<name>``.
    """
    path = shipped.tree() / TOOLS / f"{name}.md"
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise shipped.DocumentsError("documents-not-installed", path=str(path)) from exc


def static_instructions() -> str:
    """Every delivered document, in order: what a client that does not truncate gets.

    A function rather than a constant, and not only because the text is read
    from files now. A module constant holding it is rendered *by value* into
    the API reference, which put the whole of both documents back into the
    generated page they had just been taken out of.
    """
    return "\n".join(skill(name) for name in DELIVERED)


#: The key whose document introduces the store. One name, so that a session
#: arriving at a store nobody described to it has somewhere to look, and a
#: session that learns how one is organised has somewhere to write it.
README_KEY = "readme"

#: What is said about the readme instead of carrying it: that there is one, and
#: to read it before anything else. A fixed cost, where the document itself cost
#: whatever that project's conventions happened to run to.
READ_README = (
    f"This store has a `{README_KEY}` document covering project conventions. "
    "Read it before starting."
)

#: What is said when the store has no readme. The empty store is exactly where
#: naming the convention is worth most, since the session that goes on to learn
#: the layout is the one that can write it down.
NO_README = (
    f"This store has no `{README_KEY}` document. Try reading `outrage/readme` "
    "instead for instructions."
)


def _compose(opening: str) -> str:
    """The delivered text: the opening block, then the essentials, then the tail.

    One function so that what is measured against ``DELIVERY_BUDGET`` is built
    the same way as the string actually sent, rather than by a second estimate
    of it that can drift out of step.
    """
    return f"{opening}\n\n{static_instructions()}"


def _protected(opening: str) -> str:
    """The part of a composition that has to survive the cut: everything but the tail."""
    return _compose(opening).removesuffix(f"\n{skill(DELIVERED[-1])}")


#: What is delivered ahead of the tail, and so everything that has to survive
#: the client's cut: the readme line and the essentials. Measured from the real
#: strings rather than estimated, so editing either moves it, and
#: ``test_the_delivered_text_fits_the_budget`` fails when it passes
#: ``DELIVERY_BUDGET``. It no longer varies with the store: what the readme
#: costs here is the length of the sentence naming it.
PROTECTED_CHARS = len(_protected(READ_README))


def instructions(store: Store) -> str:
    """A line naming the root store's readme, then the essentials, then the tail.

    The readme is **named, not carried**. The argument for inlining it holds as
    far as it goes: a line telling a session to go and read a key is a line that
    can be read past, and this project has watched exactly that happen twice.

    What settled it the other way is that the length of a store's entry point
    is the project's business, not this server's. Carrying it means capping it,
    and the cap was ``DELIVERY_BUDGET`` minus whatever the static text happened
    to cost -- 667 characters when this changed. No conventions worth writing
    down fit that reliably, and different projects' will not fit the same
    number at all: this store's own readme went to 1898 characters the moment
    it listed its namespaces, and the readme shipped as the default is 2560.
    Over the cap nothing was inlined and the length was reported instead, which
    is a failure mode that arrives *silently* at the one document meant to
    prevent silent failure -- it looks like delivery until somebody starts a
    fresh session and reads what actually came.

    So the cost is fixed and small, the readme can be whatever the project needs,
    and what makes the line hard to read past is that it is first and the
    session has not yet done anything. Two things carry the risk that it is
    read past anyway: the `tail` document says what a readme is for, and a
    host that loads project instructions of its own can say it a second time.

    The order still decides what survives. A client cuts this text at some
    length it does not announce, so what is written first is what a session
    gets, and the `tail` document is last because it is the recoverable half.
    ``PROTECTED_CHARS`` is what everything ahead of it costs.

    The **root** store's readme, when there is a mount table. A mounted store's
    own is not named either: a session that has not yet read the root's cannot
    act on a second, and a mount announces itself in a listing instead, where
    it costs nothing until somebody looks.
    """
    # The root mount's, when this is a table. Not a routed read of the key:
    # a mount at `readme` would then decide what a store introduces itself
    # with, and the reason only the root's is named is a budget rather than
    # a routing question. A bare store is its own root.
    root = store.root.store if isinstance(store, MountedStore) else store

    # `exists` rather than a read: the text no longer depends on the content,
    # only on whether there is any. It is also the container case -- a key with
    # documents beneath it and nothing of its own introduces nothing.
    if not root.exists(README_KEY):
        return _compose(NO_README)
    return _compose(READ_README)


class RequestLog:
    """Record every inbound message, from the layer that can still see the failures.

    Wrapping the five tool functions instead would be simpler and would miss
    the calls that matter most. An argument the server does not know is refused
    by the tool's own argument model - see ``_forbid_unknown_arguments`` - and
    that refusal becomes a ``CallToolResult`` carrying ``is_error`` without the
    tool function ever being entered. A log wired inside those functions is
    structurally blind to it, which would leave the one failure this server
    goes out of its way to catch as the one failure it cannot record.

    From here the raw parameters are visible before validation, ``initialize``
    is visible along with the client that sent it, and a refusal is visible
    either as a raised error or as an error result. Both are recorded.

    ``MCPServer.middleware`` is documented as provisional and expected to
    change before v2 is final, so this depends on something that may move. The
    risk is accepted on the same terms as ``extra="forbid"``: what a change
    would cost is logging silently ceasing to happen, and
    ``test_the_middleware_is_reached`` fails loudly rather than letting it.
    """

    def __init__(self, log: EventLog) -> None:
        self._log = log
        self._calls = itertools.count(1)

    async def __call__(
        self, ctx: ServerRequestContext[Any, Any], call_next: CallNext
    ) -> HandlerResult:
        if not self._log.enabled:
            return await call_next(ctx)

        # Every store access made while serving this message reads the call
        # number back out of the context variable, which is what groups the
        # accesses under the request that caused them.
        call = next(self._calls)
        token = eventlog.current_call.set(call)
        event = "request" if ctx.request_id is not None else "notify"
        params = _request_params(self._log, ctx.params)
        started = time.monotonic_ns()
        try:
            try:
                result = await call_next(ctx)
            except Exception as exc:
                self._log.emit(
                    event,
                    method=ctx.method,
                    params=params,
                    ms=_ms(started),
                    error={"type": type(exc).__name__, "message": str(exc)},
                )
                raise
            self._log.emit(
                event,
                method=ctx.method,
                params=params,
                ms=_ms(started),
                result=_result_summary(result),
            )
            return result
        finally:
            # After the emits, deliberately: resetting first would strip the
            # call number off the very event that reports the call.
            eventlog.current_call.reset(token)


def build_server(
    store: Store | remount.Live,
    log: EventLog | None = None,
    directory: str | os.PathLike[str] | None = None,
    *,
    all_tools: bool = False,
    info_tool: bool = True,
    remount_tool: bool = True,
    mount_config: Sequence[str] = (),
) -> MCPServer:
    """Build a server exposing ``store``, which may be one store or a mount table.

    A lone ``Store`` is wrapped in a table of one rather than served by a
    second path through this module. There is then no routing that only runs
    when something is mounted, and the single store case exercises the same
    code every call takes.

    ``store`` may also be an :class:`outrage.remount.Live`, and that is what
    :func:`main` passes: a table that can be replaced while this server runs.
    Anything else is wrapped in one, so there is a single path here too. Every
    tool body opens with ``table = live.table`` and uses what it got for its
    whole duration -- one snapshot per call, which is the whole of why a change
    is safe.

    ``directory`` is the store directory, and it has to be passed in: what is
    served is a :class:`~outrage.mounts.MountedStore`, which is a ``Store`` and
    not a :class:`~outrage.store.FileStore`, so it cannot be asked where it is.
    :func:`main` has already resolved it for the event log, which is what still
    wants it.

    ``document_edit`` does not need it. It writes to
    :func:`~outrage.bulk.export_root`, a per-user directory below the system
    temporary directory, which always exists -- so the tool is registered
    unconditionally rather than only where there is a store directory to write
    under.

    ``ingest_document`` is the one tool that is not. It needs the optional
    ``documents`` extra, and a client offered a tool whose every call refuses
    has been told the store can do something it cannot; the tools a session
    lists should be the tools it can use.

    ``all_tools`` registers it anyway, for ``tools/render_tools.py``. The
    shipped tool documentation describes the server rather than one
    installation of it, so it must not gain or lose a tool according to what
    happened to be installed where it was generated. It is the only caller that
    wants this: a real server passes nothing and offers what it can do.

    ``info_tool`` is the other tool that may be absent, and it is absent
    because somebody said so rather than because anything is missing. What it
    reports is a list of absolute paths into the machine the server runs on,
    which is worth having by default and worth being able to withhold; the
    server's ``--no-info`` is how it is withheld. ``all_tools`` overrides this
    too, for the same reason.

    ``mount_config`` is the one thing that tool needs and this server cannot
    work out: the configuration files the mount table was read from, which
    :func:`outrage.mountfile.sources` knows and which are flattened away by the
    time there is a table.

    ``remount_tool`` is the ``mount`` and ``unmount`` pair, on for the same
    reason and withheld the same way -- the server's ``--no-remount``. They are
    MCP-only, which is a decision rather than an omission: the command line
    builds its table from scratch on every run and has nothing to change.
    """
    log = log if log is not None else eventlog.NULL
    live = (
        store
        if isinstance(store, remount.Live)
        else remount.Live(
            store if isinstance(store, MountedStore) else MountedStore.single(store),
            directory=directory,
            log=log,
        )
    )
    server = MCPServer(
        name="outrage",
        version=__version__,
        # Built once, from the table as it is now, and that is what fixes the
        # root: a mount tool may change anything except the store whose readme
        # this was composed from, so what a connection was told stays true for
        # as long as the connection does.
        instructions=instructions(live.table),
        # Registered only when there is somewhere to write, so that the default
        # configuration adds nothing to the SDK's chain at all.
        middleware=[RequestLog(log)] if log.enabled else None,
    )

    @server.tool(
        annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True),
        description=tool_description("read_document"),
    )
    @_reported
    def read_document(
        key: Annotated[
            str,
            Field(description="Key to read"),
        ],
        offset: Annotated[int, Field(description="Character offset to start at", ge=0)] = 0,
        byte_offset: Annotated[
            int | None,
            Field(
                description=(
                    "UTF-8 byte offset to start at, instead of offset. One "
                    "landing inside a character reads from that character's "
                    "first byte, and byte_offset in the result says where the "
                    "read began"
                ),
                ge=0,
            ),
        ] = None,
        pattern: Annotated[
            str | None,
            Field(description="Literal substring to start the read from, not a regex"),
        ] = None,
        occurrence: Annotated[
            int, Field(description="Which appearance of pattern to use, 0 being the first", ge=0)
        ] = 0,
        max_chars: Annotated[
            int, Field(description="Maximum characters to return", gt=0)
        ] = DEFAULT_MAX_CHARS,
    ) -> _ExcerptResult:
        table = live.table
        return _excerpt_result(
            table.retrieve_document(
                _named_key(table, key),
                offset=offset,
                byte_offset=byte_offset,
                pattern=pattern,
                occurrence=occurrence,
                max_chars=max_chars,
            )
        )

    @server.tool(
        annotations=ToolAnnotations(idempotent_hint=True),
        description=tool_description("store_document"),
    )
    @_reported
    def store_document(
        key: Annotated[
            str,
            Field(description="Key to write"),
        ],
        content: Annotated[str, Field(description="Document content")],
        format: Annotated[
            Format | None,
            Field(
                description=(
                    "'markdown', 'json', 'text' or 'html'; detected from the content "
                    "when omitted, though detection never chooses 'text'"
                )
            ),
        ] = None,
        title: Annotated[
            str | None,
            Field(
                description=("Short title, stored as the key's '!title' metadata in the same write")
            ),
        ] = None,
        encoding: Annotated[
            Encoding | None,
            Field(
                description=(
                    "How `content` and `title` are encoded in this call, not how "
                    "they are stored. Pass 'json-string' to send each as a JSON "
                    "string literal, quotes and escapes included; it is decoded "
                    "before storing, so the stored document is plain text either "
                    "way. Use it when the value is long or generated: a damaged "
                    "value then fails loudly here instead of being stored as if "
                    "it were correct. Omit to send the text as-is."
                )
            ),
        ] = None,
        against: Annotated[
            str | None,
            Field(
                description=(
                    "Path of a file `document_edit` exported from `key`, to "
                    "check this write against. Its content is not read - only "
                    "its record of what the document held when it came out - "
                    "so the write is refused if somebody else has written the "
                    "document since. Pass it when storing back a document you "
                    "exported and edited without editing the file"
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(
                description=(
                    "Store the content even though `against` refuses it: the "
                    "document changed after that file came out, or the file "
                    "cannot say. Only for a caller who has looked at what "
                    "changed and means to replace it"
                )
            ),
        ] = False,
    ) -> _StoreDocumentResult:
        table = live.table
        at = _named_key(table, key, allow_wildcard=True)
        # Before the write, and the whole of what `against` does: it names a
        # file whose *record* says what this edit was made against, and the
        # content still comes from the call. An agent that exported a document
        # and edited it in context rather than on disk gets the staleness
        # refusal `document_edit` gets, without having to hand back a file.
        check = (
            None
            if against is None
            else bulk.check_write(table, at, against, bulk.export_root(), overwrite=overwrite)
        )
        written = table.store_document(at, content, format, title=title, encoding=encoding)
        result: dict[str, Any] = {
            "key": written,
            # `content` is what arrived, which is not what was stored once it
            # has been decoded, so the encoded path asks the store rather than
            # guessing.
            "stored": len(content) if encoding is None else table.retrieve_document(written).total,
            "generated": written != key,
        }
        if check is not None:
            # `content` only when it is what was stored; the encoded path sent
            # something else, and a record hashes what the store holds.
            bulk.renew(table, written, check, content if encoding is None else None)
            result["previous"] = check.previous
            result["unchecked_code"] = check.unchecked_code
            _say(result, bulk.notes_for_checked_write(written, check, result["stored"]))
        if title is not None:
            # Parsed rather than joined: the root's title is `!title`, not
            # `/!title`, and a caller told the wrong key cannot read it back.
            # At the joined bound, because `outer` has already crossed a mount:
            # the store refused the title if it did not fit *there*, so this
            # parse must not refuse it again on a narrower bound it was never
            # judged against.
            result["title_key"] = keys.parse(
                f"{written}{keys.DELIMITER}{keys.META_PREFIX}title",
                max_segments=keys.MAX_JOINED_SEGMENTS,
            ).key
        return _StoreDocumentResult.model_validate(result)

    if all_tools or ingest.available():

        @server.tool(
            annotations=ToolAnnotations(idempotent_hint=True),
            description=tool_description("ingest_document"),
        )
        @_reported
        def ingest_document(
            source: Annotated[str, Field(description="Path to a local regular file")],
            key: Annotated[str, Field(description="Destination key")],
            title: Annotated[
                str | None,
                Field(
                    description=(
                        "Title to store; MarkItDown's title and then the source filename "
                        "stem are used when omitted"
                    )
                ),
            ] = None,
            overwrite: Annotated[
                bool, Field(description="Replace a document already stored at the destination")
            ] = False,
            dry_run: Annotated[
                bool, Field(description="Convert and report without writing the document or title")
            ] = False,
        ) -> _IngestDocumentResult:
            table = live.table
            converted = ingest.ingest_document(
                table,
                source,
                _named_key(table, key),
                title=title,
                overwrite=overwrite,
                dry_run=dry_run,
            )
            result: dict[str, Any] = {
                "source": str(converted.source),
                "key": converted.key,
                "title": converted.title,
                "characters": converted.characters,
                "format": converted.format,
                "dry_run": converted.dry_run,
            }
            if converted.title_key is not None:
                result["title_key"] = converted.title_key
            return _IngestDocumentResult.model_validate(result)

    @server.tool(
        annotations=ToolAnnotations(idempotent_hint=True),
        description=tool_description("make_contents"),
    )
    @_reported
    def make_contents(
        key: Annotated[str, Field(description="Markdown document key")],
        metadata_name: Annotated[
            str,
            Field(
                description="Direct metadata name to write, without the leading '!'",
                min_length=1,
            ),
        ] = "contents",
    ) -> _MakeContentsResult:
        table = live.table
        made = contents.make_contents(table, _named_key(table, key), metadata_name=metadata_name)
        return _MakeContentsResult.model_validate(dataclasses.asdict(made))

    @server.tool(
        annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True),
        description=tool_description("list_keys"),
    )
    @_reported
    def list_keys(
        key: Annotated[
            str | None,
            Field(description="Key to list below"),
        ] = None,
        limit: Annotated[
            int, Field(description="Maximum keys to return", gt=0)
        ] = DEFAULT_ITEM_LIMIT,
        after: Annotated[
            str | None,
            Field(description="Resume after this key, from a previous result's next_cursor"),
        ] = None,
    ) -> _ListKeysResult:
        table = live.table
        at = _named_key(table, key)
        page = table.list_keys(at, limit=limit, cursor=after)
        return _ListKeysResult(
            key=at,
            entries=[
                _EntryResult.model_validate(dataclasses.asdict(entry)) for entry in page.items
            ],
            returned=page.returned,
            total=page.total,
            total_chars=page.total_chars,
            next_cursor=page.next_cursor,
        )

    @server.tool(
        annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True),
        description=tool_description("get_documents"),
    )
    @_reported
    def get_documents(
        key: Annotated[
            str | None,
            Field(description="Key whose subtree to read; omit for root"),
        ] = None,
        meta_name: Annotated[
            list[str] | None,
            Field(
                description="Metadata names to return instead of documents, e.g. ['title']",
                min_length=1,
            ),
        ] = None,
        depth: Annotated[
            int | None,
            Field(description="How many levels below key to descend; unlimited when omitted", ge=0),
        ] = None,
        max_chars: Annotated[
            int, Field(description="Maximum characters per document", gt=0)
        ] = DEFAULT_BULK_MAX_CHARS,
        limit: Annotated[
            int, Field(description="Maximum documents to return", gt=0)
        ] = DEFAULT_ITEM_LIMIT,
        after: Annotated[
            str | None,
            Field(description="Resume after this key, from a previous result's next_cursor"),
        ] = None,
        max_total_chars: Annotated[
            int,
            Field(description="Maximum characters across the whole page", gt=0),
        ] = DEFAULT_PAGE_CHARS,
    ) -> _GetDocumentsResult:
        table = live.table
        at = _named_key(table, key)
        subtree = BoundedSubtree(at, depth)
        page = table.get_documents(
            subtree,
            meta_name=meta_name,
            max_chars=max_chars,
            limit=limit,
            cursor=after,
            max_total_chars=max_total_chars,
        )
        result: dict[str, Any] = {
            "key": at,
            "count": page.returned,
            "returned": page.returned,
            "total": page.total,
            "total_chars": page.total_chars,
            "next_cursor": page.next_cursor,
            "documents": [_excerpt_result(excerpt) for excerpt in page.items],
        }
        if meta_name is not None:
            # A survey by metadata cannot see documents that lack it, so left
            # alone it quietly under-reports the store. Reported over this
            # page's own window -- `after` the cursor that opened the page and
            # `before_inclusive` the one it closed with -- so the two halves
            # describe one stretch of the store and the windows tile as a
            # caller pages. Both ends unset when the page covered the whole
            # collection, which is the same window said the other way.
            #
            # Always present, because "no block" and "none missing here" are
            # answers a caller must be able to tell apart. No cursor: pass the
            # same `key` to keys_missing_meta to enumerate them, which is the
            # collection this only counts.
            gap = table.missing_meta_stats(
                subtree,
                window=KeyRange(after=after, before_inclusive=page.next_cursor),
                meta_name=meta_name,
                sample=WITHOUT_META_SAMPLE,
            )
            result["without_meta"] = {
                "total": gap.total,
                "total_chars": gap.total_chars,
                "sample": gap.sample,
            }
        return _GetDocumentsResult.model_validate(result)

    @server.tool(
        annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True),
        description=tool_description("find_documents"),
    )
    @_reported
    def find_documents(
        criteria: Annotated[
            list[_SearchCriterionArgument],
            Field(description="One to five targeted search criteria", min_length=1, max_length=5),
        ],
        key: Annotated[
            str | None,
            Field(description="Key whose subtree to search; omit for root"),
        ] = None,
        depth: Annotated[
            int | None,
            Field(description="How many levels below key to descend; unlimited when omitted", ge=0),
        ] = None,
        combine: Annotated[
            SearchCombination,
            Field(description="Select documents satisfying any or all criteria"),
        ] = "any",
        scan_limit: Annotated[
            int,
            Field(description="Maximum candidate documents to examine in this call", gt=0),
        ] = DEFAULT_SEARCH_SCAN_LIMIT,
        after: Annotated[
            str | None,
            Field(description="Resume after this key, from a previous result's next_cursor"),
        ] = None,
    ) -> _FindDocumentsResult:
        table = live.table
        at = _named_key(table, key)
        page = table.find_documents(
            BoundedSubtree(at, depth),
            criteria=[
                SearchCriterion(
                    pattern=criterion.pattern,
                    match=criterion.match,
                    target=criterion.target,
                    meta_name=None if criterion.meta_name is None else tuple(criterion.meta_name),
                )
                for criterion in criteria
            ],
            combine=combine,
            cursor=after,
            scan_limit=scan_limit,
        )
        return _FindDocumentsResult.model_validate(
            {
                "key": at,
                "matches": [dataclasses.asdict(match) for match in page.matches],
                "matched": page.matched,
                "matched_chars": page.matched_chars,
                "scanned": page.scanned,
                "total_candidates": page.total_candidates,
                "total_candidate_chars": page.total_candidate_chars,
                "next_cursor": page.next_cursor,
            }
        )

    @server.tool(
        annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True),
        description=tool_description("keys_missing_meta"),
    )
    @_reported
    def keys_missing_meta(
        key: Annotated[
            str | None,
            Field(description="Key whose subtree to check; omit for everything"),
        ] = None,
        meta_name: Annotated[
            list[str] | None,
            Field(
                description="Metadata names to look for; defaults to ['title']",
                min_length=1,
            ),
        ] = None,
        depth: Annotated[
            int | None,
            Field(description="How many levels below key to descend; unlimited when omitted", ge=0),
        ] = None,
        limit: Annotated[
            int, Field(description="Maximum keys to return", gt=0)
        ] = DEFAULT_ITEM_LIMIT,
        after: Annotated[
            str | None,
            Field(description="Resume after this key, from a previous result's next_cursor"),
        ] = None,
    ) -> _KeysMissingMetaResult:
        table = live.table
        at = _named_key(table, key)
        page = table.keys_missing_meta(
            BoundedSubtree(at, depth),
            meta_name=meta_name if meta_name is not None else "title",
            limit=limit,
            cursor=after,
        )
        return _KeysMissingMetaResult(
            key=at,
            keys=page.items,
            returned=page.returned,
            total=page.total,
            total_chars=page.total_chars,
            next_cursor=page.next_cursor,
        )

    @server.tool(
        annotations=ToolAnnotations(destructive_hint=True, idempotent_hint=True),
        description=tool_description("delete_keys"),
    )
    @_reported
    def delete_keys(
        key: Annotated[
            str,
            Field(description="Key to delete"),
        ],
        recursive: Annotated[
            bool, Field(description="Also delete everything beneath the key")
        ] = False,
        unchanged_since: Annotated[
            str | None,
            Field(
                description=(
                    "Refuse the whole delete if anything it would remove has "
                    "changed since this ISO 8601 timestamp, e.g. "
                    "2026-09-03T10:15:00Z. Nothing is deleted when it has. "
                    "A dry run reports one as `checked_at`. Unchecked when "
                    "omitted"
                )
            ),
        ] = None,
        dry_run: Annotated[
            bool, Field(description="Report what would be deleted without deleting any of it")
        ] = False,
    ) -> _DeleteKeysResult:
        table = live.table
        at = _named_key(table, key)
        # A delete crosses a mount boundary, exactly as a read does, and the
        # table is what crosses it. It is the one call where crossing makes the
        # system more dangerous rather than less, and it is deliberate: a delete
        # that stopped at a boundary while every other tool crossed it would
        # leave the caller to discover the rule from the wreckage.
        # Read before the delete, so that anything written while this call runs
        # is later than the moment a second call is measured against. The copy's
        # dry run takes its watermark the same way and for the same reason.
        checked_at = _now()
        deleted = table.delete(
            at, recursive=recursive, unchanged_since=unchanged_since, dry_run=dry_run
        )
        # What a read-only mount kept back is not a key, so it is not in that
        # answer. Asked separately, and for a *non*-recursive delete too:
        # `remaining` is about to count what is below, and a caller told to pass
        # `recursive` deserves to know which part of that count it still would
        # not reach.
        refused = table.read_only_below(at)

        result: dict[str, Any] = {"key": at, "deleted": deleted, "count": len(deleted)}
        if dry_run:
            result["dry_run"] = True
            # The moment to hand back, which is the half of "look, then delete
            # only what has not moved" a caller cannot work out for itself. The
            # command line has printed one on `rm --dry-run` since the watermark
            # was built; a session had no way to ask for one at all, which is
            # what this tool exists to fix.
            result["checked_at"] = checked_at
        # Without this a no-op delete and a successful one look identical, so a
        # key left standing reads as a key removed. Counted across the whole
        # table, since "below this key" now means below it in whichever store
        # answers for each part of the subtree.
        remaining = 0 if recursive else table.descendant_count(at)
        if remaining:
            result["remaining"] = remaining
        if refused:
            result["mounts_kept"] = refused
        _say(
            result,
            bulk.notes_for_delete(key, dry_run=dry_run, remaining=remaining, mounts_kept=refused),
        )
        return _DeleteKeysResult.model_validate(result)

    @server.tool(
        # Idempotent as `store_document` is: the same call twice leaves the same
        # store, whichever `on_conflict` was asked for. Not read-only and not
        # declared non-destructive, because `overwrite` replaces documents.
        annotations=ToolAnnotations(idempotent_hint=True),
        description=tool_description("copy_tree"),
    )
    @_reported
    def copy_tree(
        source: Annotated[
            str,
            Field(description="Key whose subtree to copy, e.g. context/?last, or / for the root"),
        ],
        target: Annotated[
            str,
            Field(
                description=(
                    "Key to copy it to: a prefix to graft beneath, or the new "
                    "key itself with `reroot`"
                )
            ),
        ],
        reroot: Annotated[
            bool,
            Field(
                description=(
                    "Land the keys at `target` itself rather than beneath their "
                    "own source key, so source/x arrives as target/x"
                )
            ),
        ] = False,
        depth: Annotated[
            int | None,
            Field(
                description="How many levels below source to descend; unlimited when omitted",
                ge=0,
            ),
        ] = None,
        on_conflict: Annotated[
            str,
            Field(
                description=(
                    "What to do about a key already holding a document: "
                    "'skip' it, 'overwrite' it, 'overwrite-unchanged' to "
                    "replace only what has not moved since unchanged_since, "
                    "or 'stop' the whole copy there"
                )
            ),
        ] = store_module.SKIP,
        unchanged_since: Annotated[
            str | None,
            Field(
                description=(
                    "When you looked, as an ISO 8601 timestamp such as "
                    "2026-09-03T10:15:00Z: a dry run reports one as "
                    "`checked_at`. The copy is refused before anything is "
                    "written if the target changed since, and with "
                    "on_conflict='overwrite-unchanged' any key that changes "
                    "after that is left alone and named in `changed`"
                )
            ),
        ] = None,
        dry_run: Annotated[
            bool, Field(description="Report what would be copied without writing any of it")
        ] = False,
        limit: Annotated[
            int, Field(description="Maximum documents to copy in this call", gt=0)
        ] = DEFAULT_COPY_LIMIT,
        cursor: Annotated[
            str | None,
            Field(description="Resume a copy after this key, from a previous result's next_cursor"),
        ] = None,
        after: Annotated[
            str | None, Field(description="Copy only what is strictly after this key")
        ] = None,
        after_inclusive: Annotated[
            str | None, Field(description="Copy only what is at or after this key")
        ] = None,
        after_subtree: Annotated[
            str | None,
            Field(description="Copy only what is after this key and everything below it"),
        ] = None,
        before: Annotated[
            str | None, Field(description="Copy only what is strictly before this key")
        ] = None,
        before_inclusive: Annotated[
            str | None, Field(description="Copy only what is at or before this key")
        ] = None,
        final_subtree: Annotated[
            str | None,
            Field(description="Copy nothing later than the end of this key's subtree"),
        ] = None,
    ) -> _CopyTreeResult:
        # Resolved before anything routes, exactly as every other tool does it:
        # a `?last` in the part of a key that names a mount decides which store
        # answers. The cursor is not resolved with them - it is this server's
        # own output being handed back, and a `?last` in it would mean the
        # selection had moved under the caller.
        table = live.table
        at_source = _named_key(table, source)
        at_target = _named_key(table, target)
        # The rule is `bulk`'s and not this module's, so the command line
        # refuses the same pairs. Before the copy starts, because `copy_from`
        # is a generator and a refusal from inside one arrives after the first
        # write rather than instead of it.
        bulk.overlapping(at_source, at_target, reroot=reroot)
        key_range = KeyRange(
            **{
                name: None if value is None else _named_key(table, value)
                for name, value in (
                    ("after", after),
                    ("after_inclusive", after_inclusive),
                    ("after_subtree", after_subtree),
                    ("before", before),
                    ("before_inclusive", before_inclusive),
                    ("final_subtree", final_subtree),
                )
            }
        )
        # Read before the walk starts, so that a document written while this
        # call runs is later than the moment a second call is measured against.
        checked_at = _now()
        transfers = table.copy_from(
            table,
            BoundedSubtree(at_source, depth),
            key_range=key_range,
            prefix=at_target,
            reroot=reroot,
            on_conflict=on_conflict,
            unchanged_since=unchanged_since,
            dry_run=dry_run,
            cursor=cursor,
            limit=limit,
        )
        result = _copied_result(transfers)
        result = {"source": at_source, "target": at_target} | result
        if dry_run:
            result["dry_run"] = True
            # The moment to hand back, which is the half of "look, then write
            # only what has not moved" a caller cannot work out for itself.
            result["checked_at"] = checked_at
        # What a read-only mount kept back is not a failed key alone: the
        # failures are sampled, and a caller reading a count needs to know that
        # a whole stretch of what it wrote to refuses writes however often it
        # tries. `delete_keys` reports the same thing for the same reason.
        #
        # Asked of where the documents actually land rather than of `target`,
        # which under a graft is a level above them: a read-only mount beside
        # the landing zone refuses nothing, and naming it would be a warning
        # about a store this copy never touched.
        #
        # `at_or_below`, not `below`, and the difference is a whole case rather
        # than an edge of one: a copy *into* a read-only mount is refused by the
        # mount it is landing inside, which is above the landing and so invisible
        # to the question a delete asks. Every document failed and the answer
        # named no mount, sampling the same refusal five times instead.
        landing = at_target if reroot else keys.with_prefix(at_target, at_source)
        refused = table.read_only_at_or_below(landing)
        if refused:
            result["mounts_kept"] = refused
        _say(
            result,
            bulk.notes_for_copy(
                landing,
                dry_run=dry_run,
                on_conflict=on_conflict,
                unchanged_since=unchanged_since,
                changed=result.get("changed") or [],
                next_cursor=result["next_cursor"],
                limit=limit,
                failed=result["copied"].get(store_module.FAILED, 0),
                named=len(result["failures"]),
                stopped=bool(result["copied"].get(store_module.STOPPED)),
                mounts_kept=refused,
            ),
        )
        return _CopyTreeResult.model_validate(result)

    @server.tool(
        annotations=ToolAnnotations(idempotent_hint=True),
        description=tool_description("document_edit"),
    )
    @_reported
    def document_edit(
        key: Annotated[
            str,
            Field(
                description=(
                    "Key to export, or to import into, e.g. "
                    "context/a1b2/design or context/?last/design for the newest"
                )
            ),
        ],
        path: Annotated[
            str | None,
            Field(
                description=(
                    "Omit to export the document to a file. Pass the path of "
                    "a file this tool exported to store its content at `key` "
                    "instead; the file may have been edited, and may be one "
                    "exported for another key. Give the path the export "
                    "returned, or one relative to the export directory - a "
                    "relative path is taken from there, not from the working "
                    "directory"
                )
            ),
        ] = None,
        against: Annotated[
            str | None,
            Field(
                description=(
                    "Path of a second exported file, exported from `key`, whose "
                    "record checks the import. Only its record is read, never "
                    "its content. Pass it to import a file exported for another "
                    "key: the content then comes from `path` and the check that "
                    "nobody else has written `key` comes from here"
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(
                description=(
                    "Store the file even though the check refuses it: the "
                    "document changed after the checking file was exported, or "
                    "there is no record naming `key` to check against. Only for "
                    "a caller who has looked and means to replace it: the "
                    "refusal is there because another agent's write is about to "
                    "be lost"
                )
            ),
        ] = False,
    ) -> _DocumentEditResult:
        # No wildcard: `?` allocates a number, and a round trip is about a
        # key that already exists on one end or the other. Allocating one
        # is `store_document`'s business.
        table = live.table
        at = _named_key(table, key)
        if path is None and against is not None:
            # Refused rather than ignored, and before the export directory is
            # touched: a caller who passed a check meant a write to be checked,
            # and quietly exporting instead answers a question nobody asked.
            raise store_module.InvalidArgumentError("check-without-write", key=at)
        # Asked per call rather than once when the server is built, so that
        # building one costs nothing on disk and a directory removed under a
        # running server is remade rather than remembered.
        exports = bulk.export_root()
        if path is None:
            exported = bulk.export_document(table, at, exports)
            result: dict[str, Any] = {
                "key": at,
                "path": str(exported.path),
                "exported": exported.excerpt.total,
                "format": exported.excerpt.format,
            }
            _say(result, bulk.notes_for_export(exported))
            return _DocumentEditResult.model_validate(result)
        imported = bulk.import_document(
            table, at, path, exports, against=against, overwrite=overwrite
        )
        result = {
            "key": imported.key,
            "path": str(path),
            "stored": imported.stored,
            "previous": imported.previous,
            "unchecked_code": imported.unchecked_code,
        }
        _say(result, bulk.notes_for(imported))
        return _DocumentEditResult.model_validate(result)

    if all_tools or remount_tool:

        @server.tool(
            annotations=ToolAnnotations(idempotent_hint=True),
            description=tool_description("mount"),
        )
        @_reported
        def mount(
            key: Annotated[
                str,
                Field(description="Key to mount the store at; the root cannot be mounted over"),
            ],
            file: Annotated[
                str | None,
                Field(
                    description=(
                        "Store file, relative to the store directory. Omit it to "
                        "mount the store outrage ships for this key, which is how "
                        "the 'outrage' manual is put back after unmounting it"
                    )
                ),
            ] = None,
            type: Annotated[
                str | None,
                Field(
                    description=(
                        "Backend to open `file` with, when the file name does not "
                        "say: 'files' for a directory of files"
                    )
                ),
            ] = None,
            read_only: Annotated[
                bool,
                Field(description="Refuse every write routed here; the file itself is untouched"),
            ] = False,
        ) -> _MountsResult:
            changed = live.mount(key, file=file, type=type, read_only=read_only)
            return _mounts_result(changed)

        @server.tool(
            annotations=ToolAnnotations(idempotent_hint=True),
            description=tool_description("unmount"),
        )
        @_reported
        def unmount(
            key: Annotated[
                str,
                Field(description="Mount point to remove; the root cannot be unmounted"),
            ],
        ) -> _MountsResult:
            return _mounts_result(live.unmount(key))

    if all_tools or info_tool:

        @server.tool(
            annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True),
            description=tool_description("info"),
        )
        @_reported
        def info() -> _InfoResult:
            # Asked per call rather than built with the server, so that what is
            # reported is the table as it is now and the answer cannot outlive
            # what it describes.
            return _InfoResult.model_validate(
                dataclasses.asdict(
                    info_module.describe(
                        live.table,
                        directory=directory,
                        mount_config=mount_config,
                        log=log,
                    )
                )
            )

    return server


def _mounts_result(changed: remount.Changed) -> _MountsResult:
    """A finished change as the table it produced, with its notes said.

    The table comes from the change rather than from ``live.table``: another
    thread may have changed it again in between, and an answer describing a
    table that is no longer there is the one thing a report of a change must
    not be.
    """
    result: dict[str, Any] = {
        "mounts": [dataclasses.asdict(one) for one in info_module.mount_infos(changed.table)]
    }
    _say(result, list(changed.notes))
    return _MountsResult.model_validate(result)


def _copied_result(
    transfers: Generator[store_module.Transfer, None, str | None],
) -> dict[str, Any]:
    """A copy as counts, a sample of what failed, and where to resume.

    Statistics rather than one line per document, which is the one place this
    tool and ``outrage copy`` legitimately differ: the command line prints a
    transfer as it happens, so an interrupted run has reported exactly what it
    did, and a single return value cannot have that property at any size. What
    it can do is stay the same size as the copy grows.

    Consumed with ``next`` rather than a ``for`` loop because the resume cursor
    is the generator's **return** value: it names a source key, and a transfer
    carries the key written, which under a prefix or a reroot is a different
    key.
    """
    counted: dict[str, int] = {}
    characters = 0
    failures: list[dict[str, str | None]] = []
    changed: list[str] = []
    while True:
        try:
            transfer = next(transfers)
        except StopIteration as ended:
            answer: dict[str, Any] = {
                "copied": counted,
                "documents": sum(counted.values()),
                "characters": characters,
                "failures": failures,
                "next_cursor": ended.value,
            }
            if changed:
                # Absent rather than empty, so a copy that asked for no
                # watermark reports exactly what it always did, and a field
                # that is there means something was left behind.
                answer["changed"] = changed
            return answer
        counted[transfer.action] = counted.get(transfer.action, 0) + 1
        characters += transfer.characters
        if transfer.action == store_module.FAILED and len(failures) < COPY_FAILURE_SAMPLE:
            # The default speller is this reader's, since a tool argument is
            # spelled the way the library already spells it. What matters is
            # that the sentence is written *here* at all: the walk carries the
            # refusal and neither front end inherits the other's wording.
            said = transfer.reason if transfer.error is None else messages.render(transfer.error)
            failures.append({"key": transfer.key, "reason": said})
        # Named in full rather than sampled, unlike the failures: a caller told
        # that three keys moved and shown two has to go looking for the third,
        # and the whole value of this answer is that it is the list to look at.
        # It is bounded by what a page of the copy can collide with.
        if transfer.action == store_module.CHANGED and transfer.key is not None:
            changed.append(transfer.key)


def _excerpt_result(excerpt: Excerpt) -> _ExcerptResult:
    fields = dataclasses.asdict(excerpt) | {"truncated": excerpt.truncated}
    if excerpt.offset is None:
        # A byte-addressed read has no character numbers to report, and a null
        # `next_offset` already means something else here -- that the document
        # ended. So they are left out rather than sent as nulls that read as
        # "you have the whole thing", which is what `_ToolResult` omits absent
        # fields for.
        for absent in ("offset", "total", "next_offset"):
            del fields[absent]
    return _ExcerptResult.model_validate(fields)


def _ms(started: int) -> float:
    return round((time.monotonic_ns() - started) / 1_000_000, 3)


def _request_params(log: EventLog, params: Any) -> Any:
    """Apply the content policy to the arguments of a tool call.

    Without this the request layer would keep writing whole documents into the
    log after the store layer had been told not to, which would make
    ``--log-content=none`` a setting that reads as if it worked.
    """
    if not isinstance(params, dict):
        return params
    arguments = params.get("arguments")
    if not isinstance(arguments, dict):
        return params
    return params | {"arguments": log.arguments(arguments)}


def _result_summary(result: HandlerResult) -> dict[str, Any] | None:
    """Whether the call succeeded, and what it said if it did not.

    Not the result itself: what the tool returned is already described by the
    store events underneath it, and a request layer that repeated them would
    double the log to say nothing new. What only this layer knows is that a
    call failed without reaching a tool at all.
    """
    if result is None:
        return None
    failed = _failed(result)
    summary: dict[str, Any] = {"ok": not failed}
    if failed:
        summary["message"] = _error_text(result)
    return summary


def _failed(result: Any) -> bool:
    """Read the error flag from a result in either of the shapes it arrives in.

    ``HandlerResult`` is a model *or* a dict, and by the time a tool result
    reaches the middleware it has been serialised: the flag is the wire's
    ``isError`` rather than the model's ``is_error``. Reading only the model
    spelling reports every rejected call as a success - which is the exact
    failure this log was built to catch, so it is worth being careful about
    twice. ``test_a_rejected_call_is_recorded_as_an_error`` drives a real
    session rather than a stub for the same reason.
    """
    if isinstance(result, dict):
        return bool(result.get("isError") or result.get("is_error"))
    return bool(getattr(result, "is_error", False) or getattr(result, "isError", False))


def _error_text(result: Any) -> str | None:
    if isinstance(result, dict):
        content = result.get("content")
    else:
        content = getattr(result, "content", None)
    for block in content or ():
        text = block.get("text") if isinstance(block, dict) else getattr(block, "text", None)
        if text:
            return text
    return None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """The server's command line: which stores to serve, and what to record.

    Four groups of arguments, and the first two are the interesting pair.
    ``--dir`` says which *directory* holds the stores, ``--root-mount`` and the
    repeatable ``--mount``/``--mount-ro`` say which *files* inside it are
    mounted where. ``--log`` and
    ``--log-content`` say what is recorded about the calls that arrive,
    ``--no-info`` withholds the one tool that describes any of it, and
    ``--no-remount`` the pair that changes the mounts while the server runs.

    The mount options may also be written in a file rather than typed --
    :mod:`outrage.mountfile`, and the whole point of it here: with a table in
    the store directory, the ``args`` a client's JSON has to carry come down to
    ``--dir``. The file is spliced into ``argv`` before the parser sees it, so
    everything below describes both.

    Separate from :func:`main` so that a test can ask what an argument list
    parses to without opening a store or starting a server.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    # The list as it was *written*, kept because the splice is what flattens
    # several sources into one and a report of which files were read is the
    # one thing the flattened list can no longer say.
    written = list(argv)
    # ``builtin``: the server carries the shipped documentation unless told
    # otherwise, and it is spliced in as an option so that the table treats it
    # as one. The command line does not -- a bare ``outrage`` stays a clean
    # namespace over the project's own store.
    argv = mountfile.spliced(argv, builtin=True)
    parser = argparse.ArgumentParser(
        prog="outrage-server", description="MCP server for the Outrage document store"
    )
    parser.add_argument(
        "--dir",
        dest="directory",
        default=None,
        metavar="PATH",
        help=(
            "Store directory: the one directory holding every store this "
            "server serves, and the event log and backups beside them. "
            "Defaults to the OUTRAGE_DIR environment variable, then ./.outrage in "
            "the working directory."
        ),
    )
    parser.add_argument(
        "--root-mount",
        dest="root_mount",
        default=store_module.default_store_file(),
        metavar="FILE",
        help=(
            "The store answering for every key no mount claims, as a file "
            f"inside --dir (default: {store_module.default_store_file()}). A "
            "file rather than a directory, so that one directory holds several "
            "stores and so that a backend other than SQLite is named by the "
            "file it keeps."
        ),
    )
    parser.add_argument(
        "--mount",
        dest="mounts",
        action="append",
        default=[],
        metavar=f"KEY{mounts_module.SPEC_DELIMITER}FILE",
        help=(
            "Mount another store under KEY, as in "
            f"ref{mounts_module.SPEC_DELIMITER}reference.sqlite. FILE is "
            "relative to --dir, like --root-mount, and may carry options "
            f"after a comma: docs,{mounts_module.TYPE_OPTION}=files says which "
            "backend keeps the store, for a store whose name cannot -- a "
            "directory of files has no extension to read. Types: "
            f"{', '.join(store_module.backend_names())}. "
            "Repeatable. The root mount "
            "holds everything no mount claims, and a mount takes precedence "
            "over it for the keys below its mount point. Reads and writes "
            "cross a mount boundary; a query, a survey and a recursive delete "
            "stop at one and say so. This is the table the server starts "
            "with; the 'mount' and 'unmount' tools change it while it runs, "
            "unless --no-remount withheld them."
        ),
    )
    parser.add_argument(
        "--mount-ro",
        dest="read_only_mounts",
        action="append",
        default=[],
        metavar=f"KEY{mounts_module.SPEC_DELIMITER}FILE",
        help=(
            "Mount a store read-only: as --mount, but every write routed there "
            "is refused before it reaches the store. For a shared reference "
            "base beside a local read-write store. Repeatable. The store must "
            "already exist, since a mistyped name would otherwise be created "
            "and mount as an empty one. This refuses writes through this "
            "server; it does not make the file read-only to anything else."
        ),
    )
    parser.add_argument(
        mountfile.DOCS_FLAG,
        dest="mount_docs",
        action="store_true",
        help=(
            "Mount the documentation shipped with outrage, read-only, at "
            f"{keys.displayed(mountfile.DOCS_MOUNT)!r}. On by default here: "
            f"this flag is for the command line, which does not carry it, and "
            f"is accepted so that both front ends read one mount table the "
            f"same way. {mountfile.UNMOUNT_FLAG} "
            f"{mountfile.DOCS_MOUNT} turns it off."
        ),
    )
    parser.add_argument(
        mountfile.UNMOUNT_FLAG,
        dest="unmount",
        action="append",
        default=None,
        metavar="KEY",
        help=(
            "Do not mount the store mounted at KEY: the one thing an override "
            "cannot do, since naming a mount replaces it or adds it. "
            "Repeatable, and refused if nothing was mounted there -- which "
            f"includes {mountfile.DOCS_MOUNT}, mounted here by default and "
            f"only on request on the command line."
        ),
    )
    parser.add_argument(
        mountfile.CONFIG_FLAG,
        dest="mount_config",
        action="append",
        default=None,
        metavar="FILE",
        help=(
            "Read mount options from a TOML file, as though they had been "
            "typed here: an option before it loses, an option after it wins. "
            f"Repeatable. {mountfile.DEFAULT_NAME} in --dir is read first "
            "whenever it exists, so a project's own table needs no flag at all."
        ),
    )
    parser.add_argument(
        mountfile.NO_CONFIG_FLAG,
        dest="no_mount_config",
        action="store_true",
        help=(
            f"Ignore {mountfile.DEFAULT_NAME} in --dir for this run, serving "
            "only the stores named here."
        ),
    )
    parser.add_argument(
        "--log",
        nargs="?",
        const=eventlog.DEFAULT,
        default=None,
        metavar="PATH",
        help=(
            "Record requests and store accesses as JSON lines. Without a path, "
            f"writes {eventlog.DEFAULT_LOG_NAME} in the store directory. "
            f"Defaults to the {eventlog.ENV_LOG} environment variable, then to "
            "not logging at all."
        ),
    )
    parser.add_argument(
        "--log-content",
        dest="log_content",
        choices=eventlog.CONTENT_POLICIES,
        default="excerpt",
        help=(
            "How much document text the log keeps: 'none' for a length and a "
            "hash, 'excerpt' for both ends of it (default), 'full' for all of it."
        ),
    )
    parser.add_argument(
        "--no-info",
        dest="no_info",
        action="store_true",
        help=(
            "Do not offer the 'info' tool, which reports this server's Python "
            "environment, store directory, mount configuration files, mounts "
            "and log. On by default: a session that can see the environment "
            "can drive the same installation's command line. Withhold it where "
            "the absolute paths of the machine the server runs on should not "
            "be part of what a caller is told."
        ),
    )
    parser.add_argument(
        "--no-remount",
        dest="no_remount",
        action="store_true",
        help=(
            "Do not offer the 'mount' and 'unmount' tools, which add and "
            "remove mounts on this running server. On by default: a session "
            "that finds it needs a reference store should not have to be "
            "restarted to read one. A change made through them lasts only as "
            "long as this server, whatever it is."
        ),
    )
    args = parser.parse_args(argv)
    # Answered here rather than in `main` for the reason this function is
    # separate at all: what an argument list means is decided in one place, and
    # can be asked without opening a store.
    args.config_files = mountfile.sources(written, builtin=True)
    return args


def _documents(wanted: bool, log: EventLog | None = None) -> dict[str, Store]:
    """The shipped documentation to attach, warning rather than failing without it.

    A **warning**, and this is the one place the default differs from the flag.
    The command line mounts this because somebody typed ``--mount-docs``, so a
    tree that is not there is a refusal, exactly as a ``--mount-ro`` naming
    nothing is. Here nobody asked: the mount arrives with the server, and a
    build that dropped the tree would otherwise stop every session from
    starting over documentation that is not what anybody's store is for. So the
    server says so on stderr, beside the shadowing warning, and serves the rest.
    """
    if not wanted:
        return {}
    if not shipped.available():
        print(
            f"outrage: warning: the shipped documentation is not in this "
            f"installation ({shipped.tree()}), so nothing is mounted at "
            f"{keys.displayed(shipped.MOUNT_POINT)!r}",
            file=sys.stderr,
        )
        return {}
    return dict(shipped.attached(log=log))


def main(argv: list[str] | None = None) -> int:
    """Open the configured stores and serve them over stdio until the client
    stops.

    The console script ``outrage-server``, and the entry point an MCP client
    launches. It resolves the store directory once -- the event log defaults to
    a file beside it -- opens the mount table, warns on stderr about any mount that
    shadows keys already held, and hands it to :func:`build_server` as the
    :class:`outrage.remount.Live` table this process serves.

    Returns rather than exits, for the same reason :func:`outrage.cli.main` does.
    """
    try:
        args = parse_args(argv)
    except OutrageError as exc:
        # A mount configuration file that will not parse fails here, before
        # there is a log to record it in. Same rule as the block below: it is
        # an answer about the configuration, not a bug.
        #
        # Spelled as flags, not as keyword arguments: this goes to an
        # operator's stderr about the command line they just typed, and every
        # message reachable here is about that command line. It is a tool call
        # that is the exception in this module, not a shell.
        print(f"outrage: {messages.render(exc, spell=messages.flag)}", file=sys.stderr)
        return 1
    # Resolved here rather than left to the store, because the log defaults to
    # a file beside the database and so needs the same answer.
    directory = store_module.resolve_directory(args.directory)
    log = EventLog(
        eventlog.resolve_path(args.log, directory),
        content=args.log_content,
    )
    log.start(version=__version__, directory=str(directory), log=str(log.path))
    try:
        # `Live` is the context manager and `open_mounts` is not, which matters
        # rather than being a preference: a mount tool replaces the table, so
        # `with open_mounts(...)` would close a table that is no longer the one
        # being served -- and with it the stores the live one still shares.
        with remount.Live(
            mounts_module.open_mounts(
                directory,
                args.mounts,
                args.read_only_mounts,
                root_mount=args.root_mount,
                log=log,
                attached=_documents(args.mount_docs, log),
            ),
            directory=directory,
            log=log,
        ) as live:
            for mount in live.table.shadowing():
                # Stderr, not a refusal: the configuration is usable, and the
                # keys that vanish are in a store the operator can still reach.
                # Refusing to start over a stray key would be worse.
                #
                # A mount made later through the tool says the same thing as a
                # note on its own result, where a tool caller can read it.
                print(
                    f"outrage: warning: the store at {mount.name!r} shadows keys already "
                    f"held there; they are unreachable while it is mounted",
                    file=sys.stderr,
                )
            build_server(
                live,
                log,
                directory,
                info_tool=not args.no_info,
                remount_tool=not args.no_remount,
                mount_config=args.config_files,
            ).run("stdio")
    except OutrageError as exc:
        # The same rule `cli.main` follows, and for the same reason: a mount
        # table that cannot be built is an answer about the configuration, not
        # a bug, and a traceback in a client's stderr is where an operator is
        # least able to read one. Anything that is not a OutrageError still
        # tracebacks, because that is a bug in outrage.
        #
        # The default namer: nothing has been mounted yet when a table refuses
        # to build, and every key one of these names is a mount point, which is
        # already a name in the whole namespace. Flags for the same reason as
        # above -- the reader is whoever started the server.
        print(f"outrage: {messages.render(exc, spell=messages.flag)}", file=sys.stderr)
        return 1
    finally:
        # A process that is killed writes no stop event, which is itself worth
        # being able to see in the log.
        log.stop()
        log.close()
    return 0


__all__ = [
    "COPY_FAILURE_SAMPLE",
    "DEFAULT_COPY_LIMIT",
    "DEFAULT_ITEM_LIMIT",
    "DEFAULT_PAGE_CHARS",
    "DEFAULT_SEARCH_SCAN_LIMIT",
    "DELIVERED",
    "DELIVERY_BUDGET",
    "NO_README",
    "PROTECTED_CHARS",
    "READ_README",
    "README_KEY",
    "SKILLS",
    "TOOLS",
    "WITHOUT_META_SAMPLE",
    "RequestLog",
    "build_server",
    "instructions",
    "main",
    "parse_args",
    "skill",
    "static_instructions",
    "tool_description",
]
