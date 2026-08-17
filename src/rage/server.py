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

from . import __version__, eventlog
from . import store as store_module
from .eventlog import EventLog
from .store import DEFAULT_BULK_MAX_CHARS, DEFAULT_MAX_CHARS, Excerpt, Store


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

INSTRUCTIONS = """\
A store for notes, designs and task context that outlives a single session.

Keys are hierarchical, slash delimited strings such as `context/<id>/design`.
A colon introduces metadata attached to a key, such as
`context/<id>/design:title`. Intermediate keys exist implicitly; nothing needs
to be created before writing to a key beneath it.

Keys are not file paths, but they read like them, so a key may mirror one:
notes about a file can live at `notes/src/myfile.py`.

When storing, a `?` in place of a whole segment asks the store to allocate a
number for it: `context/?/design` writes to `context/1/design` in an empty
store. The result reports the key actually written, which is what to use for
anything else belonging with it, such as `context/1/task`.

Prefer storing a document under a descriptive key and passing a `title`, so
that later sessions can survey what is stored with
`get_documents(meta_name=["title"])` before reading anything in full. That
survey reports untitled documents separately, under `without_meta`.

A key that holds nothing itself but has keys beneath it is a container: reading
it fails, listing it does not.
"""


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
        instructions=INSTRUCTIONS,
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
                    "context/a1b2/design:title, or context/?/design to allocate"
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
                    "Short title, stored as the key's ':title' metadata in the "
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
            result["title_key"] = f"{written}:title"
        return result

    @server.tool(
        annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True),
        description=(
            "List the keys immediately below a key, including subkeys and "
            "metadata. Omit the key to list the top level. Keys of kind "
            "'implicit' hold no content themselves but have something beneath them."
        ),
    )
    def list_keys(
        key: Annotated[
            str | None, Field(description="Key to list below; omit for the top level")
        ] = None,
    ) -> dict[str, Any]:
        return {"key": key, "entries": [dataclasses.asdict(e) for e in store.list_keys(key)]}

    @server.tool(
        annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True),
        description=(
            "Read every document at and below a key. Pass `meta_name` to get that "
            "metadata across the subtree instead, which is the cheap way to survey "
            "what is stored: `get_documents(key='context', meta_name=['title'])` "
            "lists the titles of everything under `context`. Each result is "
            "truncated; use retrieve_document to read one in full."
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
    ) -> dict[str, Any]:
        found = store.get_documents(key, meta_name=meta_name, depth=depth, max_chars=max_chars)
        result: dict[str, Any] = {
            "key": key,
            "count": len(found),
            "documents": [_excerpt_result(e) for e in found],
        }
        if meta_name is not None:
            # A survey by metadata cannot see documents that lack it, so left
            # alone it quietly under-reports the store.
            missing = store.keys_missing_meta(key, meta_name=meta_name, depth=depth)
            if missing:
                result["without_meta"] = missing
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


__all__ = ["INSTRUCTIONS", "RequestLog", "build_server", "main", "parse_args"]
