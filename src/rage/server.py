"""MCP server exposing the document store.

A thin wrapper: argument shaping and result shaping only. All behaviour lives
in :mod:`rage.store`, so it can be exercised without a protocol harness.
"""

from __future__ import annotations

import argparse
import dataclasses
import itertools
import time
from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.server.context import CallNext, HandlerResult, ServerRequestContext
from mcp.server.mcpserver.utilities.func_metadata import ArgModelBase
from mcp.types import ToolAnnotations
from pydantic import Field

from . import __version__, eventlog, keys
from . import store as store_module
from .eventlog import EventLog
from .store import DEFAULT_BULK_MAX_CHARS, DEFAULT_MAX_CHARS, Excerpt, KeyNotFoundError, Store


def _scope(key: str | None) -> str:
    """The key a scope argument names, with an omitted one meaning the root.

    A client that sends `null` for a key it did not fill in means the same as
    one that left it out, and both mean the whole store -- which is the root,
    now that the root is a key. Resolved here so the result echoes the scope
    that was actually used rather than the absence the caller sent.
    """
    return "" if key is None else key


def _forbid_unknown_arguments() -> None:
    """Make an unrecognised tool argument an error rather than a silent no-op.

    The SDK builds each tool's argument model on ``ArgModelBase``, which leaves
    pydantic's default ``extra="ignore"``, so an argument the server does not
    know is dropped before the tool function is entered — the tool cannot even
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
DEFAULT_PAGE_CHARS = 20000

#: Keys named in `without_meta` before it stops listing and only counts. Its
#: job is to warn that a survey under-reports the store, and a count does that
#: at any size; at reference scale the list would *be* the corpus.
WITHOUT_META_SAMPLE = 10

#: What a client is assumed to deliver of a server's instructions before it
#: cuts them. An observation of one client, not a protocol guarantee: Claude
#: Code truncates at 2048 characters, measured on 2026-08-19 across this
#: project's own transcripts and again the day after. Whether the number is
#: fixed, shared between servers, or really a token count is unestablished —
#: 2047 characters landing on a power of two is the argument for characters.
#: Everything ordered before this point survives on that client; everything
#: after it may not, and nothing may be *only* said after it.
DELIVERY_BUDGET = 2048

#: The half that has to survive truncation: the grammar of a key, how one is
#: allocated, and that a listing is a page. Ordered second, after the store's
#: own readme, because a session that gets this and nothing else can still read
#: and write correctly, while one that gets the protocol and no routing does
#: not know where anything is.
ESSENTIALS = """\
A store for notes, designs and task context that outlives a single session.

Keys are hierarchical, slash delimited strings such as `context/<id>/design`,
and `/` is the only separator there is. A segment beginning with `!` is
metadata about the document above it, such as `context/<id>/design/!title`.
Intermediate keys exist implicitly; nothing needs creating before writing
beneath one.

When storing, a `?` in place of a whole segment asks the store to allocate a
number for it, at any depth: `context/?/design` writes to `context/1/design` in
an empty store. The result reports the key actually written, which is what to
use for anything else belonging with it, such as `context/1/task`.

Store a document under a descriptive key and pass a `title`, so that later
sessions can survey what is here with `get_documents(meta_name=["title"])`
before reading anything in full.

Every listing is a page, not the whole store. Each one reports `returned`
beside `total`, and a `next_cursor` when more remains: pass it back as `after`
to continue from exactly where the page stopped. Read `total` before treating a
result as everything there is — 20 of 22 is a listing, 20 of 40000 is a sample.
"""

#: The half that can be lost. Not one word of it is unimportant; every part is
#: recoverable somewhere a session reaches anyway — the tool descriptions, the
#: packaged skill, or a failure that explains itself when it happens. That is
#: the whole test for putting something here rather than in `ESSENTIALS`.
TAIL = """\
A segment may hold almost any text — `/` and the control characters below tab
are the only exclusions — so a key can mirror a real name without transforming
it. Keys are not file paths, but they read like them: notes about a file can
live at `notes/src/myfile.py`. A path may continue below a metadata segment,
and everything under one is metadata rather than a document.

A survey also reports the untitled documents under `without_meta`, as a count
and a few examples covering the same stretch of the store as the page itself.
It is stats, not a listing, so it carries no cursor: page the survey and the
windows tile; to enumerate what it counts, call `keys_missing_meta`.

Prefer several small documents to one large one. A document should answer one
question and be readable in a single call, and a key can hold content *and*
have keys beneath it, so a general document can stay where it is with the
detail below it. When there is more to add, add a document rather than growing
one — `?` allocates the key, so this costs no naming decision.

A key that holds nothing itself but has keys beneath it is a container: reading
it fails, listing it does not.

The empty key is the root, and omitting a key means the same thing. It holds a
document like any other key and carries metadata as `!title`, so a store can
title itself. Nothing else about it is special, and by convention nothing much
is kept there.

The document at `readme` is a store's entry point: what that particular store
holds, and what to read before anything else. It is carried at the top of these
instructions when there is one, so a session starts with it rather than having
to know to ask. If you work out how a store is organised, or what a later
session should read first, `readme` is where that belongs.
"""

#: The static text entire, in delivery order. Kept as one name because it is
#: what a client that does not truncate receives, and what anything documenting
#: the server should quote.
INSTRUCTIONS = f"{ESSENTIALS}\n{TAIL}"

#: The key whose document introduces the store. One name, so that a session
#: arriving at a store nobody described to it has somewhere to look, and a
#: session that learns how one is organised has somewhere to write it.
README_KEY = "readme"

#: How the readme is introduced, and the one thing about it a session cannot
#: work out for itself. Both are paid for out of the same budget as the readme
#: they wrap, so both say the least that is still true: the heading carries why
#: the document is here, the note carries when it was read. Everything else
#: about the convention is in ``TAIL``, where it can afford to be.
README_HEADING = f"--- `{README_KEY}`: this store's own introduction, so you start with it ---"
README_NOTE = (
    f"Read once, when the server started — a `{README_KEY}` changed during a "
    f"session reaches the next one, not this one."
)

#: What is said when the store has no readme. The empty store is exactly where
#: naming the convention is worth most, since the session that goes on to learn
#: the layout is the one that can write it down.
NO_README = (
    f"This store has no `{README_KEY}` document. If you work out how it is "
    f"organised, or what a later session should read first, store that there."
)


def _compose(opening: str) -> str:
    """The delivered text: the opening block, then the essentials, then the tail.

    One function so that what is measured against ``DELIVERY_BUDGET`` is built
    the same way as the string actually sent, rather than by a second estimate
    of it that can drift out of step.
    """
    return f"{opening}\n\n{ESSENTIALS}\n{TAIL}"


def _protected(opening: str) -> str:
    """The part of a composition that has to survive the cut: everything but the tail."""
    return _compose(opening).removesuffix(f"\n{TAIL}")


#: What the readme's own block costs before a word of it is written: the
#: heading, the note below it, the blank lines between, and the essentials that
#: follow. Measured from the real strings, so editing any of them moves the cap.
SCAFFOLDING_CHARS = len(_protected(f"{README_HEADING}\n\n\n\n{README_NOTE}"))

#: How much of the readme is carried, computed rather than chosen: whatever the
#: budget has left once the scaffolding is paid for. The old constant bounded
#: the wrong thing — it asked how long a routing document ought to be, when the
#: question the client actually answers is how much room is left before the
#: cut. That number was negative, so no readme of any length was ever
#: delivered. See `project/reference/planned/instructions-budget`.
README_MAX_CHARS = DELIVERY_BUDGET - SCAFFOLDING_CHARS

#: The smallest readme worth having a mechanism for: enough to name what a
#: store holds and point at two or three keys. ``test_the_essentials_leave_room``
#: fails if the static text grows back over the cut, which is the failure that
#: produced all of this.
README_FLOOR_CHARS = 600

#: What is said when the store has no readme. The empty store is exactly where
#: naming the convention is worth most, since the session that goes on to learn
#: the layout is the one that can write it down.
NO_README = (
    f"This store has no `{README_KEY}` document. If you work out how it is "
    f"organised, or what a later session should read first, store that there."
)


def instructions(store: Store) -> str:
    """This store's own readme, then the essentials, then the tail.

    Delivered rather than requested. A line telling a session to go and read a
    key is a line that can be read past, and this project has two records of
    exactly that happening -- see `planned/agents` on trap 2, and
    `project/reference/agents` on the search cascade. The readme costs no tool
    call and cannot be skipped, which is the same argument that puts `title` in
    the tool signature: reachable at the moment it applies, rather than
    depending on somebody remembering it then.

    The order is the whole point. A client cuts this text at some length it
    does not announce -- ``DELIVERY_BUDGET`` records the one measurement there
    is -- so what is written first is what survives, and the readme was last
    for long enough that it never arrived once. What is at risk now is
    ``TAIL``, which is chosen to be the recoverable half.

    Over ``README_MAX_CHARS`` nothing is inlined and the length is reported
    instead. A silently shortened entry point would be the project's own
    recurring failure at the one document meant to prevent it, and a reader
    told the size can decide to go and read the rest.
    """
    try:
        excerpt = store.retrieve_document(README_KEY, max_chars=README_MAX_CHARS)
    except KeyNotFoundError:
        # Also the container case: a key with documents beneath it and nothing
        # of its own introduces nothing.
        return _compose(NO_README)

    if excerpt.truncated:
        return _compose(
            f"The `{README_KEY}` document here is {excerpt.total} characters, too long to "
            f"carry in these instructions. Read it before starting."
        )
    return _compose(f"{README_HEADING}\n\n{excerpt.content.rstrip()}\n\n{README_NOTE}")


class RequestLog:
    """Record every inbound message, from the layer that can still see the failures.

    Wrapping the five tool functions instead would be simpler and would miss
    the calls that matter most. An argument the server does not know is refused
    by the tool's own argument model — see ``_forbid_unknown_arguments`` — and
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


def build_server(store: Store, log: EventLog | None = None) -> MCPServer:
    """Build a server exposing ``store``."""
    log = log if log is not None else eventlog.NULL
    server = MCPServer(
        name="rage",
        version=__version__,
        instructions=instructions(store),
        # Registered only when there is somewhere to write, so that the default
        # configuration adds nothing to the SDK's chain at all.
        middleware=[RequestLog(log)] if log.enabled else None,
    )

    @server.tool(
        annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True),
        description=(
            "Read the document stored at a key. Long documents are returned in "
            "capped slices: when `next_offset` is set, call again with that "
            "`offset` to continue. To jump to a section, pass `pattern` as a "
            "literal substring to start the read from."
        ),
    )
    def retrieve_document(
        key: Annotated[str, Field(description="Key to read, e.g. context/a1b2/design")],
        offset: Annotated[int, Field(description="Character offset to start at", ge=0)] = 0,
        length: Annotated[
            int | None, Field(description="Characters to return; capped by max_chars", ge=0)
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
    ) -> dict[str, Any]:
        return _excerpt_result(
            store.retrieve_document(
                key,
                offset=offset,
                length=length,
                pattern=pattern,
                occurrence=occurrence,
                max_chars=max_chars,
            )
        )

    @server.tool(
        annotations=ToolAnnotations(idempotent_hint=True),
        description=(
            "Store a document or a metadata value at a key, overwriting whatever "
            "is there. Content should be markdown or JSON. A whole segment given "
            "as `?` is replaced by a number the store allocates, so `tmp/?` "
            "writes to `tmp/1` in an empty store; the returned `key` is the one "
            "actually written, and is what to use for related keys afterwards. "
            "Pass `title` whenever you store a document: it is what later "
            "sessions survey the store by, and a document stored without one is "
            "hard to find again."
        ),
    )
    def store_document(
        key: Annotated[
            str,
            Field(
                description=(
                    "Key to write, e.g. context/a1b2/design, "
                    "context/a1b2/design/!title, or context/?/design to allocate"
                )
            ),
        ],
        content: Annotated[str, Field(description="Document content")],
        format: Annotated[
            str | None,
            Field(description="'markdown' or 'json'; detected from the content when omitted"),
        ] = None,
        title: Annotated[
            str | None,
            Field(
                description=(
                    "Short title, stored as the key's '!title' metadata in the "
                    "same write. Omit only when key is itself metadata."
                )
            ),
        ] = None,
        encoding: Annotated[
            str | None,
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
    ) -> dict[str, Any]:
        written = store.store_document(key, content, format, title=title, encoding=encoding)
        # `content` is what arrived, which is not what was stored once it has
        # been decoded, so the encoded path asks the store rather than guessing.
        stored = len(content) if encoding is None else store.retrieve_document(written).total
        result: dict[str, Any] = {
            "key": written,
            "stored": stored,
            "generated": written != key,
        }
        if title is not None:
            # Parsed rather than joined: the root's title is `!title`, not
            # `/!title`, and a caller told the wrong key cannot read it back.
            result["title_key"] = keys.parse(
                f"{written}{keys.DELIMITER}{keys.META_PREFIX}title"
            ).key
        return result

    @server.tool(
        annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True),
        description=(
            "List the keys immediately below a key, including subkeys and "
            "metadata. Omit the key to list the top level. Keys of kind "
            "'implicit' hold no content themselves but have something beneath "
            f"them. Returns at most {DEFAULT_ITEM_LIMIT} keys: compare `returned` with "
            "`total` to see whether that was the whole level, and pass "
            "`next_cursor` back as `after` to continue."
        ),
    )
    def list_keys(
        key: Annotated[
            str | None, Field(description="Key to list below; omit for the top level")
        ] = None,
        limit: Annotated[
            int, Field(description="Maximum keys to return", gt=0)
        ] = DEFAULT_ITEM_LIMIT,
        after: Annotated[
            str | None,
            Field(description="Resume after this key, from a previous result's next_cursor"),
        ] = None,
    ) -> dict[str, Any]:
        key = _scope(key)
        listing = store.list_keys(key, limit=limit, after=after)
        return {
            "key": key,
            "entries": [dataclasses.asdict(e) for e in listing.items],
            "returned": listing.returned,
            "total": listing.total,
            "total_chars": listing.total_chars,
            "next_cursor": listing.next_cursor,
        }

    @server.tool(
        annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True),
        description=(
            "Read every document at and below a key. Pass `meta_name` to get that "
            "metadata across the subtree instead, which is the cheap way to survey "
            "what is stored: `get_documents(key='context', meta_name=['title'])` "
            "lists the titles of everything under `context`. Each document is "
            f"truncated to `max_chars`; use retrieve_document to read one in full. "
            f"The page holds at most {DEFAULT_ITEM_LIMIT} documents and "
            f"{DEFAULT_PAGE_CHARS} characters in total, whichever comes first, "
            "so a survey of short metadata usually arrives whole while a read "
            "of real documents does not: "
            "compare `returned` with `total`, and pass `next_cursor` back as "
            "`after` to continue from where it stopped. With `meta_name`, "
            "`without_meta` counts the documents in this same page's window "
            "that carry none of it — what the survey structurally cannot "
            "show. It is always present, and describes exactly the stretch "
            "this page covers, so paging the survey tiles those windows "
            "without gap or overlap. Use keys_missing_meta to list them."
        ),
    )
    def get_documents(
        key: Annotated[
            str | None, Field(description="Key whose subtree to read; omit for everything")
        ] = None,
        meta_name: Annotated[
            list[str] | None,
            Field(description="Metadata names to return instead of documents, e.g. ['title']"),
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
    ) -> dict[str, Any]:
        key = _scope(key)
        found = store.get_documents(
            key,
            meta_name=meta_name,
            depth=depth,
            max_chars=max_chars,
            limit=limit,
            after=after,
            max_total_chars=max_total_chars,
        )
        result: dict[str, Any] = {
            "key": key,
            "count": found.returned,
            "returned": found.returned,
            "total": found.total,
            "total_chars": found.total_chars,
            "next_cursor": found.next_cursor,
            "documents": [_excerpt_result(e) for e in found.items],
        }
        if meta_name is not None:
            # A survey by metadata cannot see documents that lack it, so left
            # alone it quietly under-reports the store. Reported over this
            # page's own window -- the same bounds that produced `documents`,
            # so the two halves describe one stretch of the store and the
            # windows tile as a caller pages. Always present, because "no block"
            # and "none missing here" are answers a caller must be able to tell
            # apart. No cursor: pass the same `key` to keys_missing_meta to
            # enumerate them, which is the collection this only counts.
            gap = store.missing_meta_stats(
                key,
                meta_name=meta_name,
                depth=depth,
                after=after,
                before=found.next_cursor,
                sample=WITHOUT_META_SAMPLE,
            )
            result["without_meta"] = {
                "total": gap.total,
                "total_chars": gap.total_chars,
                "sample": gap.sample,
            }
        return result

    @server.tool(
        annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True),
        description=(
            "List the document keys at and below a key that carry none of the "
            "named metadata: exactly what a `get_documents` survey by that "
            "metadata cannot show, since a survey can only report documents "
            "that have it, and which `without_meta` only counts. A document "
            "counts as covered when it "
            "has any one of the names given, so ask for one name at a time "
            "unless you mean 'none of these'."
        ),
    )
    def keys_missing_meta(
        key: Annotated[
            str | None, Field(description="Key whose subtree to check; omit for everything")
        ] = None,
        meta_name: Annotated[
            list[str] | None,
            Field(description="Metadata names to look for; defaults to ['title']"),
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
    ) -> dict[str, Any]:
        key = _scope(key)
        missing = store.keys_missing_meta(
            key,
            meta_name=meta_name if meta_name is not None else "title",
            depth=depth,
            limit=limit,
            after=after,
        )
        return {
            "key": key,
            "keys": missing.items,
            "returned": missing.returned,
            "total": missing.total,
            "total_chars": missing.total_chars,
            "next_cursor": missing.next_cursor,
        }

    @server.tool(
        annotations=ToolAnnotations(destructive_hint=True, idempotent_hint=True),
        description=(
            "Delete a key. A document key takes its metadata with it. Descendants "
            "survive unless `recursive` is set. Note that storing an empty "
            "document does not delete anything."
        ),
    )
    def delete_keys(
        key: Annotated[str, Field(description="Key to delete")],
        recursive: Annotated[
            bool, Field(description="Also delete everything beneath the key")
        ] = False,
    ) -> dict[str, Any]:
        removed = store.delete(key, recursive=recursive)
        result: dict[str, Any] = {"key": key, "deleted": removed, "count": len(removed)}
        if not recursive:
            # Without this a no-op delete and a successful one look identical,
            # so a key left standing reads as a key removed.
            remaining = store.descendant_count(key)
            if remaining:
                result["remaining"] = remaining
                result["note"] = (
                    f"{remaining} key(s) below {key!r} were kept; "
                    f"pass recursive=true to delete them too"
                )
        return result

    return server


def _excerpt_result(excerpt: Excerpt) -> dict[str, Any]:
    return dataclasses.asdict(excerpt) | {"truncated": excerpt.truncated}


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
    spelling reports every rejected call as a success — which is the exact
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
    parser = argparse.ArgumentParser(
        prog="rage-server", description="MCP server for the Rage document store"
    )
    parser.add_argument(
        "--dir",
        dest="directory",
        default=None,
        metavar="PATH",
        help=(
            "Store directory. Defaults to the RAGE_DIR environment variable, "
            "then ./.rage in the working directory."
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    # Resolved here rather than left to the store, because the log defaults to
    # a file beside the database and so needs the same answer.
    directory = store_module.resolve_directory(args.directory)
    log = EventLog(
        eventlog.resolve_path(args.log, directory),
        content=args.log_content,
    )
    log.start(version=__version__, directory=str(directory), log=str(log.path))
    try:
        with Store(directory, log=log) as store:
            build_server(store, log).run("stdio")
    finally:
        # A process that is killed writes no stop event, which is itself worth
        # being able to see in the log.
        log.stop()
        log.close()


__all__ = [
    "DELIVERY_BUDGET",
    "ESSENTIALS",
    "INSTRUCTIONS",
    "README_KEY",
    "README_MAX_CHARS",
    "TAIL",
    "RequestLog",
    "build_server",
    "instructions",
    "main",
    "parse_args",
]
