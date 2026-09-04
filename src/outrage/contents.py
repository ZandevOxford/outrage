"""Build a small offset index from the headings in a Markdown document."""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import keys, store

_ATX = re.compile(r"^ {0,3}#{1,6}(?:[ \t]+|$)")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_SETEXT = re.compile(r"^ {0,3}(?:=+|-+)[ \t]*$")


@dataclass(frozen=True, slots=True)
class ContentsResult:
    """The facts about one generated Markdown contents document."""

    source_key: str
    """The normalized key of the Markdown document read."""

    metadata_key: str
    """The metadata key where the generated contents were stored."""

    headings: int
    """The number of headings found."""

    source_characters: int
    """The number of characters scanned in the source document."""

    characters: int
    """The number of characters stored in the generated contents document."""


@dataclass(frozen=True, slots=True)
class _Heading:
    markdown: str
    offset: int


def _without_ending(line: str) -> str:
    """Remove one Markdown line ending without touching other whitespace."""
    if line.endswith("\r\n"):
        return line[:-2]
    if line.endswith("\n") or line.endswith("\r"):
        return line[:-1]
    return line


def _headings(markdown: str) -> list[_Heading]:
    """Return literal ATX and setext headings with character offsets."""
    found: list[_Heading] = []
    fence_character: str | None = None
    fence_length = 0
    paragraph: list[tuple[str, int]] = []
    offset = 0

    for line in markdown.splitlines(keepends=True):
        text = _without_ending(line)

        if fence_character is not None:
            closing = re.fullmatch(
                rf" {{0,3}}{re.escape(fence_character)}{{{fence_length},}}[ \t]*", text
            )
            if closing is not None:
                fence_character = None
                fence_length = 0
            paragraph = []
            offset += len(line)
            continue

        possible_fence = _FENCE.fullmatch(text)
        if possible_fence is not None:
            marker, info = possible_fence.groups()
            # Backticks in a backtick fence's info string make it ordinary
            # text under CommonMark; tildes have no corresponding restriction.
            if marker[0] == "~" or "`" not in info:
                fence_character = marker[0]
                fence_length = len(marker)
                paragraph = []
                offset += len(line)
                continue

        if _ATX.match(text) is not None:
            found.append(_Heading(text, offset))
            paragraph = []
        elif _SETEXT.fullmatch(text) is not None and paragraph:
            heading_offset = paragraph[0][1]
            heading = "\n".join(line for line, _ in paragraph)
            found.append(_Heading(f"{heading}\n{text}", heading_offset))
            paragraph = []
        elif text and not text.startswith(("    ", "\t")):
            paragraph.append((text, offset))
        else:
            paragraph = []

        offset += len(line)

    return found


def render_contents(markdown: str) -> str:
    """Render each Markdown heading followed by its source character offset.

    Heading spelling is kept literal. Everything between headings is omitted,
    and the number beneath each heading is the zero-based character offset at
    which that heading begins in ``markdown``. Headings inside fenced code
    blocks are ignored.
    """
    if not isinstance(markdown, str):
        raise TypeError(f"markdown must be a string, got {type(markdown).__name__}")
    return _render(_headings(markdown))


def _render(headings: list[_Heading]) -> str:
    """Render headings already parsed from one source document."""
    if not headings:
        return ""
    return "\n\n".join(f"{heading.markdown}\n{heading.offset}" for heading in headings) + "\n"


def _metadata_key(source_key: str, metadata_name: str) -> str:
    """Validate one direct metadata name and join it to ``source_key``."""
    if not isinstance(metadata_name, str):
        raise TypeError(f"metadata_name must be a string, got {type(metadata_name).__name__}")
    if (
        not metadata_name
        or metadata_name.startswith(keys.META_PREFIX)
        or keys.DELIMITER in metadata_name
    ):
        raise store.InvalidArgumentError("contents-metadata-name", metadata_name=metadata_name)
    joined = (
        f"{source_key}{keys.DELIMITER}{keys.META_PREFIX}{metadata_name}"
        if source_key
        else f"{keys.META_PREFIX}{metadata_name}"
    )
    return keys.parse(joined, max_segments=keys.MAX_JOINED_SEGMENTS).key


def make_contents(
    opened: store.Store, key: str, *, metadata_name: str = "contents"
) -> ContentsResult:
    """Store a character-offset outline of one Markdown document as metadata.

    The source document is not changed. Its ATX and setext headings are copied
    to direct metadata named by ``metadata_name``; all section bodies are
    replaced by the heading's zero-based character offset. Regenerating the
    contents overwrites that metadata value.
    """
    source_key = keys.parse(key, max_segments=keys.MAX_JOINED_SEGMENTS).key
    destination = _metadata_key(source_key, metadata_name)
    source = store.read_all(opened, source_key)
    if source.format != "markdown":
        raise store.InvalidArgumentError(
            "contents-not-markdown", key=source_key, format=source.format
        )

    headings = _headings(source.content)
    generated = _render(headings)
    metadata_key = opened.store_document(destination, generated, format="markdown")
    return ContentsResult(
        source_key=source_key,
        metadata_key=metadata_key,
        headings=len(headings),
        source_characters=source.total,
        characters=len(generated),
    )


__all__ = ["ContentsResult", "make_contents", "render_contents"]
