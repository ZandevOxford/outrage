"""Build a small offset index from the headings in a Markdown or HTML document.

Each heading carries **two** numbers, character offset then byte offset. The
character offset is a fact about the document as a Python string; the byte
offset is the same position in its UTF-8, which is what survives the document
being written out to a file. So an index generated here can drive a seeking
read of a 20 MB document, and can also drive anything byte-addressed that was
handed the exported file -- which is what the pair is for.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

from . import keys, store

_ATX = re.compile(r"^ {0,3}#{1,6}(?:[ \t]+|$)")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_SETEXT = re.compile(r"^ {0,3}(?:=+|-+)[ \t]*$")
_HTML_HEADING = re.compile(r"h([1-6])\Z")
_HTML_SPACE = re.compile(r"[ \t\r\n\f]+")
_HTML_HIDDEN = frozenset({"script", "style", "template"})


@dataclass(frozen=True, slots=True)
class ContentsResult:
    """The facts about one generated Markdown contents document."""

    source_key: str
    """The normalized key of the source document read."""

    metadata_key: str
    """The metadata key where the generated contents were stored."""

    headings: int
    """The number of headings found."""

    source_characters: int
    """The number of characters scanned in the source document."""

    source_bytes: int
    """The number of UTF-8 bytes those characters occupy, which is the other
    number a caller needs to make sense of the second column."""

    characters: int
    """The number of characters stored in the generated contents document."""


@dataclass(frozen=True, slots=True)
class _Heading:
    markdown: str
    offset: int
    byte_offset: int


@dataclass(frozen=True, slots=True)
class _LocatedHTMLHeading:
    level: int
    text: str
    line: int
    column: int


class _HTMLHeadings(HTMLParser):
    """Collect source headings without building or repairing a document tree."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[_LocatedHTMLHeading] = []
        self._current: tuple[int, int, int] | None = None
        self._text: list[str] = []
        self._hidden: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._hidden:
            if tag in _HTML_HIDDEN:
                self._hidden.append(tag)
            return
        if tag in _HTML_HIDDEN:
            self._hidden.append(tag)
            return

        heading = _HTML_HEADING.fullmatch(tag)
        if heading is not None:
            self._finish_heading()
            line, column = self.getpos()
            self._current = (int(heading.group(1)), line, column)
            return
        if self._current is None:
            return
        if tag == "br":
            self._text.append(" ")
        elif tag == "img":
            alt = next((value for name, value in attrs if name == "alt"), None)
            if alt:
                self._text.append(alt)

    def handle_endtag(self, tag: str) -> None:
        if self._hidden:
            if tag == self._hidden[-1]:
                self._hidden.pop()
            return
        if _HTML_HEADING.fullmatch(tag) is not None:
            self._finish_heading()

    def handle_data(self, data: str) -> None:
        if self._current is not None and not self._hidden:
            self._text.append(data)

    def finish(self) -> list[_LocatedHTMLHeading]:
        """Close an unterminated final heading and return what was found."""
        self._finish_heading()
        return self.headings

    def _finish_heading(self) -> None:
        if self._current is None:
            return
        level, line, column = self._current
        text = _HTML_SPACE.sub(" ", "".join(self._text)).strip()
        self.headings.append(_LocatedHTMLHeading(level, text, line, column))
        self._current = None
        self._text = []


def _without_ending(line: str) -> str:
    """Remove one Markdown line ending without touching other whitespace."""
    if line.endswith("\r\n"):
        return line[:-2]
    if line.endswith("\n") or line.endswith("\r"):
        return line[:-1]
    return line


def _headings(markdown: str) -> list[_Heading]:
    """Return literal ATX and setext headings with character and byte offsets.

    The byte offset is accumulated line by line beside the character one
    rather than computed per heading: encoding each line once totals one
    encode of the document, where encoding the prefix of every heading would
    be one per heading and quadratic in a document with many. A line of pure
    ASCII spends no encode at all -- `isascii` is a flag the string already
    carries.
    """
    found: list[_Heading] = []
    fence_character: str | None = None
    fence_length = 0
    paragraph: list[tuple[str, int, int]] = []
    offset = 0
    byte_offset = 0

    for line in markdown.splitlines(keepends=True):
        text = _without_ending(line)
        line_bytes = len(line) if line.isascii() else len(line.encode())

        if fence_character is not None:
            closing = re.fullmatch(
                rf" {{0,3}}{re.escape(fence_character)}{{{fence_length},}}[ \t]*", text
            )
            if closing is not None:
                fence_character = None
                fence_length = 0
            paragraph = []
            offset += len(line)
            byte_offset += line_bytes
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
                byte_offset += line_bytes
                continue

        if _ATX.match(text) is not None:
            found.append(_Heading(text, offset, byte_offset))
            paragraph = []
        elif _SETEXT.fullmatch(text) is not None and paragraph:
            _, heading_offset, heading_byte_offset = paragraph[0]
            heading = "\n".join(line for line, _, _ in paragraph)
            found.append(_Heading(f"{heading}\n{text}", heading_offset, heading_byte_offset))
            paragraph = []
        elif text and not text.startswith(("    ", "\t")):
            paragraph.append((text, offset, byte_offset))
        else:
            paragraph = []

        offset += len(line)
        byte_offset += line_bytes

    return found


def _html_headings(html: str) -> list[_Heading]:
    """Return HTML h1-h6 elements as plain Markdown headings with source offsets."""
    parser = _HTMLHeadings()
    parser.feed(html)
    parser.close()
    located = parser.finish()
    if not located:
        return []

    line_starts = [0]
    line_starts.extend(position + 1 for position, character in enumerate(html) if character == "\n")
    found: list[_Heading] = []
    previous_offset = 0
    byte_offset = 0
    for heading in located:
        offset = line_starts[heading.line - 1] + heading.column
        between = html[previous_offset:offset]
        byte_offset += len(between) if between.isascii() else len(between.encode())
        marker = "#" * heading.level
        markdown = f"{marker} {heading.text}" if heading.text else marker
        found.append(_Heading(markdown, offset, byte_offset))
        previous_offset = offset
    return found


def _without_inline_link_targets(markdown: str) -> str:
    """Keep inline link text while dropping the destination around it.

    This is deliberately a small Markdown scanner rather than a regular
    expression: destinations may contain balanced parentheses and labels may
    contain brackets. Escapes protect the following character in both. An
    unmatched construct is left byte for byte as it arrived.
    """
    rendered: list[str] = []
    position = 0
    while position < len(markdown):
        if markdown[position] == "\\":
            rendered.append(markdown[position : position + 2])
            position += 2
            continue
        if markdown[position] == "`":
            end = position
            while end < len(markdown) and markdown[end] == "`":
                end += 1
            marker = markdown[position:end]
            closing = markdown.find(marker, end)
            if closing >= 0:
                rendered.append(markdown[position : closing + len(marker)])
                position = closing + len(marker)
                continue
        label_start = position + 1 if markdown[position : position + 2] == "![" else position
        if markdown[label_start : label_start + 1] != "[":
            rendered.append(markdown[position])
            position += 1
            continue

        depth = 1
        label_end = label_start + 1
        while label_end < len(markdown) and depth:
            if markdown[label_end] == "\\":
                label_end += 2
                continue
            if markdown[label_end] == "[":
                depth += 1
            elif markdown[label_end] == "]":
                depth -= 1
            label_end += 1
        if depth or markdown[label_end : label_end + 1] != "(":
            rendered.append(markdown[position])
            position += 1
            continue

        depth = 1
        destination_end = label_end + 1
        while destination_end < len(markdown) and depth:
            if markdown[destination_end] == "\\":
                destination_end += 2
                continue
            if markdown[destination_end] == "(":
                depth += 1
            elif markdown[destination_end] == ")":
                depth -= 1
            destination_end += 1
        if depth:
            rendered.append(markdown[position])
            position += 1
            continue

        rendered.append(markdown[label_start + 1 : label_end - 1])
        position = destination_end
    return "".join(rendered)


def render_contents(markdown: str, *, strip_links: bool = True) -> str:
    """Render each Markdown heading followed by its two source offsets.

    Heading spelling is kept literal apart from inline link destinations,
    which are removed by default while their text is kept. Pass
    ``strip_links=False`` to preserve the complete heading. Everything between
    headings is omitted, and the numbers beneath each heading are the
    zero-based offsets at which that heading begins in ``markdown``: the
    character offset first, then the UTF-8 byte offset, separated by a space.
    Headings inside fenced code blocks are ignored.

    Bare numbers, John's call, so **the token count on the line is the only
    thing that tells the two formats apart** -- an index written before this
    carries one number per heading. That is why regenerating an index is part
    of adopting this rather than housekeeping to get to later.
    """
    if not isinstance(markdown, str):
        raise TypeError(f"markdown must be a string, got {type(markdown).__name__}")
    return _render(_headings(markdown), strip_links=strip_links)


def render_html_contents(html: str) -> str:
    """Render each HTML h1-h6 element as a plain Markdown heading and two offsets.

    Nested markup and link targets are omitted while readable text, decoded
    character references and image alternative text remain. The zero-based
    character and UTF-8 byte offsets beneath each heading point to the opening
    ``<`` of its source element.
    """
    if not isinstance(html, str):
        raise TypeError(f"html must be a string, got {type(html).__name__}")
    return _render(_html_headings(html), strip_links=False)


def _render(headings: list[_Heading], *, strip_links: bool = True) -> str:
    """Render headings already parsed from one source document."""
    if not headings:
        return ""
    return (
        "\n\n".join(
            f"{_without_inline_link_targets(heading.markdown) if strip_links else heading.markdown}"
            f"\n{heading.offset} {heading.byte_offset}"
            for heading in headings
        )
        + "\n"
    )


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
    opened: store.Store,
    key: str,
    *,
    metadata_name: str = "contents",
    strip_links: bool = True,
) -> ContentsResult:
    """Store an offset outline of one Markdown or HTML document as metadata.

    The source document is not changed. Markdown ATX and setext headings or
    HTML h1-h6 elements are copied to direct metadata named by
    ``metadata_name``; all section bodies are replaced by the heading's two
    zero-based offsets, character then byte. HTML markup is flattened to plain
    visible text. Markdown inline link destinations are stripped by default
    while their text remains; ``strip_links=False`` keeps Markdown headings
    byte for byte. Regenerating the contents overwrites that metadata value.

    The byte number is what makes this more than a table of contents: paired
    with a byte-addressed :meth:`~outrage.store.Store.retrieve_document` it is
    random access into a document far too large to read, without splitting it
    into children first.
    """
    source_key = keys.parse(key, max_segments=keys.MAX_JOINED_SEGMENTS).key
    destination = _metadata_key(source_key, metadata_name)
    source = store.read_all(opened, source_key)
    if source.format not in ("markdown", "html"):
        raise store.InvalidArgumentError(
            "contents-not-markdown", key=source_key, format=source.format
        )

    if source.format == "html":
        headings = _html_headings(source.content)
        generated = _render(headings, strip_links=False)
    else:
        headings = _headings(source.content)
        generated = _render(headings, strip_links=strip_links)
    metadata_key = opened.store_document(destination, generated, format="markdown")
    return ContentsResult(
        source_key=source_key,
        metadata_key=metadata_key,
        headings=len(headings),
        source_characters=source.total,
        source_bytes=source.total_bytes,
        characters=len(generated),
    )


__all__ = ["ContentsResult", "make_contents", "render_contents", "render_html_contents"]
