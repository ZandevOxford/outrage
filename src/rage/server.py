"""MCP server exposing the document store.

A thin wrapper: argument shaping and result shaping only. All behaviour lives
in :mod:`rage.store`, so it can be exercised without a protocol harness.
"""

from __future__ import annotations

import argparse
import dataclasses
import itertools
import sys
import time
from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.server.context import CallNext, HandlerResult, ServerRequestContext
from mcp.server.mcpserver.utilities.func_metadata import ArgModelBase
from mcp.types import ToolAnnotations
from pydantic import Field

from . import __version__, eventlog, keys
from . import mounts as mounts_module
from . import store as store_module
from .errors import RageError
from .eventlog import EventLog
from .mounts import Mounts, Resolved
from .store import (
    DEFAULT_BULK_MAX_CHARS,
    DEFAULT_MAX_CHARS,
    Excerpt,
    KeyNotFoundError,
    Store,
)


def _scope(key: str | None) -> str:
    """The key a scope argument names, with an omitted one meaning the root.

    A client that sends `null` for a key it did not fill in means the same as
    one that left it out, and both mean the whole store -- which is the root,
    now that the root is a key. Resolved here so the result echoes the scope
    that was actually used rather than the absence the caller sent.
    """
    return "" if key is None else key


def _resolve(table: Mounts, key: str | None, *, allow_wildcard: bool = False) -> Resolved:
    """Which store answers for ``key``, with an omitted key meaning the root."""
    return table.resolve(_scope(key), allow_wildcard=allow_wildcard)


def _resolve_for_write(
    table: Mounts, key: str, *, action: str = "write", allow_wildcard: bool = False
) -> Resolved:
    """As ``_resolve``, but refuse a key owned by a read-only mount.

    A second function rather than a flag on the first, so that the write paths
    name themselves and a tool that writes cannot pick up the reading one by
    default. The refusal happens **here**, before the store is touched, which
    is the whole requirement: "a refusal that arrives after the caller thought
    it had written is the failure class this project keeps finding".
    """
    return _resolve(table, key, allow_wildcard=allow_wildcard).writable(action)


def _inward_cursor(found: Resolved, after: str | None) -> str | None:
    """A caller's cursor as the answering store names it.

    A cursor is a key, so it crosses the boundary the same way every other key
    does. One that names nothing under the mount being listed is refused rather
    than dropped: silently ignoring it would restart the collection from the
    beginning, and a caller paging a large listing would loop over the first
    page forever without anything ever reporting an error.
    """
    if after is None:
        return None
    inner = found.mount.inner(after)
    if inner is None:
        raise keys.InvalidKeyError(
            f"cursor {after!r} is not below {found.mount.name!r}, which is the "
            f"store answering for {keys.displayed(found.outer)!r}"
        )
    return inner


def _outward_items[T](found: Resolved, items: list[T]) -> list[T]:
    """``items`` renamed into the whole namespace.

    Total, since the bounds were halved: a mount point and a key inside a store
    are each capped at ``keys.MAX_SEGMENTS`` and the joined namespace allows
    twice that, so every key a mounted store returns has a name here. This
    used to drop and count the ones that did not, and every listing carried a
    `dropped` field and a note to say so.
    """
    return [
        dataclasses.replace(item, key=found.mount.outer(item.key))  # type: ignore[arg-type]
        for item in items
    ]


def _outward_keys(found: Resolved, names: list[str]) -> list[str]:
    """:func:`_outward_items` for a plain list of keys."""
    return [found.mount.outer(name) for name in names]


def _outward_cursor(found: Resolved, cursor: str | None) -> str | None:
    """A store's cursor as the caller will send it back.

    A cursor is a key, so it crosses the boundary exactly as one, and since the
    join is total it is a *valid* key on the far side -- which matters because
    a cursor is handed to a caller that has every reason to try reading it.
    """
    return None if cursor is None else found.mount.outer(cursor)


def _covered(found: Resolved, outer_key: str) -> bool:
    """Whether the answering store already holds ``outer_key`` at its level.

    Asked only of the keys a mount contributes to a listing, and only so the
    level totals count them once. A mount point that the store beneath it also
    holds is a misconfiguration -- ``Mounts.shadowing`` reports it at startup --
    but a total that double counted it would be wrong every listing after.
    """
    inner = found.mount.inner(outer_key)
    if inner is None:
        return False
    return found.store.exists(inner) or found.store.descendant_count(inner) > 0


def _unsearched(table: Mounts, key: str | None) -> list[str]:
    """The mount points below ``key`` that a subtree read does not reach."""
    return [mount.prefix for mount in table.below(_scope(key))]


def _add_note(result: dict[str, Any], text: str) -> None:
    """Add a sentence to a result's ``note``, keeping whatever is already there.

    Three separate things want to say something on one result -- keys kept back
    by a non-recursive delete, keys with no name from outside, and mounts a
    delete stopped at -- and each used to assign the field. The last one to run
    then erased the others, which is the failure mode of every one of these
    notes: a caller reads a complete-looking answer and does not know what it
    left out.
    """
    result["note"] = f"{result['note']} {text}" if result.get("note") else text


def _note_unsearched(result: dict[str, Any], unsearched: list[str]) -> None:
    """Say which mounts a subtree read did not descend into, when there were any."""
    if not unsearched:
        return
    result["mounts_not_searched"] = unsearched
    _add_note(
        result,
        f"This answer covers one store. {len(unsearched)} mounted store(s) below "
        f"this key were not read: {', '.join(repr(m) for m in unsearched)}. Ask "
        f"again with one of those keys to see what is in it.",
    )


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


def instructions(store: Store | Mounts) -> str:
    """The root store's own readme, then the essentials, then the tail.

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

    The **root** store's readme, when there is a mount table. A mounted
    store's own readme is not carried: the budget is spent to nine
    characters -- see `project/reference/planned/instructions-budget` -- and
    a second one would push the first over the client's cut, which is the
    exact failure that ordering exists to prevent. A mount announces itself
    in a listing instead, where it costs nothing until somebody looks.
    """
    root = store.root.store if isinstance(store, Mounts) else store
    try:
        excerpt = root.retrieve_document(README_KEY, max_chars=README_MAX_CHARS)
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


def build_server(store: Store | Mounts, log: EventLog | None = None) -> MCPServer:
    """Build a server exposing ``store``, which may be one store or a mount table.

    A lone ``Store`` is wrapped in a table of one rather than served by a
    second path through this module. There is then no routing that only runs
    when something is mounted, and the single store case exercises the same
    code every call takes.
    """
    log = log if log is not None else eventlog.NULL
    table = store if isinstance(store, Mounts) else Mounts.single(store)
    server = MCPServer(
        name="rage",
        version=__version__,
        instructions=instructions(table),
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
        found = _resolve(table, key)
        excerpt = found.store.retrieve_document(
            found.key,
            offset=offset,
            length=length,
            pattern=pattern,
            occurrence=occurrence,
            max_chars=max_chars,
        )
        # Renamed to the key that was asked for: the store answered about its
        # own key, which is the mount point stripped off and means nothing here.
        return _excerpt_result(dataclasses.replace(excerpt, key=found.outer))

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
        found = _resolve_for_write(table, key, allow_wildcard=True)
        written = found.store.store_document(
            found.key, content, format, title=title, encoding=encoding
        )
        outer = found.mount.outer(written)
        # `content` is what arrived, which is not what was stored once it has
        # been decoded, so the encoded path asks the store rather than guessing.
        stored = len(content) if encoding is None else found.store.retrieve_document(written).total
        result: dict[str, Any] = {
            "key": outer,
            "stored": stored,
            "generated": outer != key,
        }
        if title is not None:
            # Parsed rather than joined: the root's title is `!title`, not
            # `/!title`, and a caller told the wrong key cannot read it back.
            # At the joined bound, because `outer` has already crossed a mount:
            # the store refused the title if it did not fit *there*, so this
            # parse must not refuse it again on a narrower bound it was never
            # judged against.
            result["title_key"] = keys.parse(
                f"{outer}{keys.DELIMITER}{keys.META_PREFIX}title",
                max_segments=keys.MAX_JOINED_SEGMENTS,
            ).key
        return result

    @server.tool(
        annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True),
        description=(
            "List the keys immediately below a key, including subkeys and "
            "metadata. Omit the key to list the top level. Keys of kind "
            "'implicit' hold no content themselves but have something beneath "
            + (
                "them. A key of kind 'mount' is where another store is mounted, "
                "and 'read-only mount' is one that refuses writes; "
                "it reads and lists like any other key, but a query or a survey "
                "does not cross into it, so ask again with the mount's own key. "
                if table.multiple
                else "them. "
            )
            + f"Returns at most {DEFAULT_ITEM_LIMIT} keys: compare `returned` with "
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
        found = _resolve(table, key)
        listing = found.store.list_keys(found.key, limit=limit, after=_inward_cursor(found, after))
        entries = _outward_items(found, listing.items)

        # A mount point is a key no store knows about: the store beneath it has
        # no row there, and the store above it cannot see where it was mounted.
        # Spliced in here or a mounted store is invisible to anyone who does
        # not already know its prefix.
        children = table.children(found.outer)
        bound = None if after is None else keys.sort_form(after)
        ahead = [e for e in children if bound is None or keys.sort_form(e.key) > bound]

        # A mount wins a collision, because a mount shadows: the same rule the
        # routing follows, so a listing cannot show a key that reading it would
        # not reach.
        merged = {e.key: e for e in entries} | {e.key: e for e in ahead}
        ordered = sorted(merged.values(), key=lambda e: keys.sort_form(e.key))

        # Both halves are merged before either is cut, for the reason the store
        # merges its own two halves first: cutting separately lets whichever
        # half is denser near the cursor push the other's keys over the edge,
        # and a cursor never looks back.
        cut = limit is not None and len(ordered) > limit
        items = ordered[:limit] if cut else ordered

        # Where to resume. When the page was cut, the last key emitted -- never
        # the store's own cursor, which lies past the rows the cut withheld and
        # would skip them. When it was not, the later of the two.
        #
        # The later of the two cannot skip a store row, and the argument is now
        # short: every key the store returned was emitted, since nothing is
        # dropped any more, so a child sorting past the store's page end would
        # make the merged page longer than the limit and the page would have
        # been cut instead. It used to rest on a much narrower coincidence
        # about how deep a mount point could be; halving `MAX_SEGMENTS` removed
        # the need for it. See `project/reference/planned/mounts/cursors`.
        marks = [items[-1].key] if items else []
        if not cut and listing.next_cursor is not None:
            marks.append(_outward_cursor(found, listing.next_cursor))
        more = cut or listing.next_cursor is not None
        added = [e for e in children if not _covered(found, e.key)]

        result: dict[str, Any] = {
            "key": _scope(key),
            "entries": [dataclasses.asdict(e) for e in items],
            "returned": len(items),
            "total": listing.total + len(added),
            "total_chars": listing.total_chars + sum(e.size or 0 for e in added),
            "next_cursor": max(marks, key=keys.sort_form) if more and marks else None,
        }
        return result

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
        at = _resolve(table, key)
        found = at.store.get_documents(
            at.key,
            meta_name=meta_name,
            depth=depth,
            max_chars=max_chars,
            limit=limit,
            after=_inward_cursor(at, after),
            max_total_chars=max_total_chars,
        )
        documents = _outward_items(at, found.items)
        result: dict[str, Any] = {
            "key": _scope(key),
            "count": len(documents),
            "returned": len(documents),
            "total": found.total,
            "total_chars": found.total_chars,
            "next_cursor": _outward_cursor(at, found.next_cursor),
            "documents": [_excerpt_result(e) for e in documents],
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
            gap = at.store.missing_meta_stats(
                at.key,
                meta_name=meta_name,
                depth=depth,
                after=_inward_cursor(at, after),
                before=found.next_cursor,
                sample=WITHOUT_META_SAMPLE,
            )
            sample = _outward_keys(at, gap.sample)
            result["without_meta"] = {
                "total": gap.total,
                "total_chars": gap.total_chars,
                "sample": sample,
            }
        # A subtree read covers one store. Said rather than left to be inferred
        # from a total that looks whole: `context/8/decisions` is the standing
        # argument, that a partial answer must not be indistinguishable from a
        # complete one.
        _note_unsearched(result, _unsearched(table, key))
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
        at = _resolve(table, key)
        missing = at.store.keys_missing_meta(
            at.key,
            meta_name=meta_name if meta_name is not None else "title",
            depth=depth,
            limit=limit,
            after=_inward_cursor(at, after),
        )
        names = _outward_keys(at, missing.items)
        result: dict[str, Any] = {
            "key": _scope(key),
            "keys": names,
            "returned": len(names),
            "total": missing.total,
            "total_chars": missing.total_chars,
            "next_cursor": _outward_cursor(at, missing.next_cursor),
        }
        _note_unsearched(result, _unsearched(table, key))
        return result

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
        found = _resolve_for_write(table, key, action="delete")
        removed = found.store.delete(found.key, recursive=recursive)
        deleted = _outward_keys(found, removed)
        result: dict[str, Any] = {"key": key, "deleted": deleted, "count": len(deleted)}
        if not recursive:
            # Without this a no-op delete and a successful one look identical,
            # so a key left standing reads as a key removed.
            remaining = found.store.descendant_count(found.key)
            if remaining:
                result["remaining"] = remaining
                _add_note(
                    result,
                    f"{remaining} key(s) below {key!r} were kept; "
                    f"pass recursive=true to delete them too",
                )
        # A recursive delete stops at a mount boundary, and saying so matters
        # more here than anywhere else: a caller who believes a subtree is gone
        # will not go looking for the part of it that is not.
        kept = _unsearched(table, key)
        if kept:
            result["mounts_kept"] = kept
            _add_note(
                result,
                f"{len(kept)} mounted store(s) below {key!r} were not touched: "
                f"{', '.join(repr(m) for m in kept)}. A delete stops at a mount "
                f"boundary; delete within each mount instead.",
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
        "--mount",
        dest="mounts",
        action="append",
        default=[],
        metavar=f"KEY{mounts_module.SPEC_DELIMITER}PATH",
        help=(
            "Mount another store's directory under KEY, as in "
            f"ref{mounts_module.SPEC_DELIMITER}/srv/reference/.rage. Repeatable. "
            "The store --dir names holds everything no mount claims, and a "
            "mount takes precedence over it for the keys below its mount "
            "point. Reads and writes cross a mount boundary; a query, a survey "
            "and a recursive delete stop at one and say so. Mounts are fixed "
            "when the server starts."
        ),
    )
    parser.add_argument(
        "--mount-ro",
        dest="read_only_mounts",
        action="append",
        default=[],
        metavar=f"KEY{mounts_module.SPEC_DELIMITER}PATH",
        help=(
            "Mount a store read-only: as --mount, but every write routed there "
            "is refused before it reaches the store. For a shared reference "
            "base beside a local read-write store. Repeatable. The store must "
            "already exist, since a mistyped path would otherwise be created "
            "and mount as an empty one. This refuses writes through this "
            "server; it does not make the file read-only to anything else."
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


def main(argv: list[str] | None = None) -> int:
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
        with mounts_module.open_mounts(
            directory, args.mounts, args.read_only_mounts, log=log
        ) as table:
            for mount in table.shadowing():
                # Stderr, not a refusal: the configuration is usable, and the
                # keys that vanish are in a store the operator can still reach.
                # Refusing to start over a stray key would be worse.
                print(
                    f"rage: warning: the store at {mount.name!r} shadows keys already "
                    f"held there; they are unreachable while it is mounted",
                    file=sys.stderr,
                )
            build_server(table, log).run("stdio")
    except RageError as exc:
        # The same rule `cli.main` follows, and for the same reason: a mount
        # table that cannot be built is an answer about the configuration, not
        # a bug, and a traceback in a client's stderr is where an operator is
        # least able to read one. Anything that is not a RageError still
        # tracebacks, because that is a bug in rage.
        print(f"rage: {exc}", file=sys.stderr)
        return 1
    finally:
        # A process that is killed writes no stop event, which is itself worth
        # being able to see in the log.
        log.stop()
        log.close()
    return 0


__all__ = [
    "DELIVERY_BUDGET",
    "ESSENTIALS",
    "INSTRUCTIONS",
    "README_KEY",
    "README_MAX_CHARS",
    "TAIL",
    "Mounts",
    "RequestLog",
    "build_server",
    "instructions",
    "main",
    "parse_args",
]
