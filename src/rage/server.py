"""MCP server exposing the document store.

A thin wrapper: argument shaping and result shaping only. All behaviour lives
in :mod:`rage.store`, so it can be exercised without a protocol harness.
"""

from __future__ import annotations

import argparse
import dataclasses
from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from . import __version__
from .store import DEFAULT_BULK_MAX_CHARS, DEFAULT_MAX_CHARS, Excerpt, Store

INSTRUCTIONS = """\
A store for notes, designs and task context that outlives a single session.

Keys are hierarchical, period delimited strings such as
`context.<id>.design`. A colon introduces metadata attached to a key, such as
`context.<id>.design:title`. Intermediate keys exist implicitly; nothing needs
to be created before writing to a key beneath it.

Prefer storing a document under a descriptive key and giving it a `:title`
metadata entry, so that later sessions can survey what is stored with
`get_documents(meta_name="title")` before reading anything in full.
"""


def build_server(store: Store) -> MCPServer:
    """Build a server exposing ``store``."""
    server = MCPServer(
        name="rage",
        version=__version__,
        instructions=INSTRUCTIONS,
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
        key: Annotated[str, Field(description="Key to read, e.g. context.a1b2.design")],
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
            "is there. Content should be markdown or JSON."
        ),
    )
    def store_document(
        key: Annotated[
            str,
            Field(
                description="Key to write, e.g. context.a1b2.design or context.a1b2.design:title"
            ),
        ],
        content: Annotated[str, Field(description="Document content")],
        format: Annotated[
            str | None,
            Field(description="'markdown' or 'json'; detected from the content when omitted"),
        ] = None,
    ) -> dict[str, Any]:
        store.store_document(key, content, format)
        return {"key": key, "stored": len(content)}

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
            "what is stored: `get_documents(key='context', meta_name='title')` "
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
        return {"key": key, "count": len(found), "documents": [_excerpt_result(e) for e in found]}

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
        return {"key": key, "deleted": removed, "count": len(removed)}

    return server


def _excerpt_result(excerpt: Excerpt) -> dict[str, Any]:
    return dataclasses.asdict(excerpt) | {"truncated": excerpt.truncated}


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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    with Store(args.directory) as store:
        build_server(store).run("stdio")


__all__ = ["INSTRUCTIONS", "build_server", "main", "parse_args"]
