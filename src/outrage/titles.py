"""Extract a document title from Markdown or HTML without storing it."""

from __future__ import annotations

import re
from html.parser import HTMLParser

_ATX_H1 = re.compile(r"^ {0,3}#(?:[ \t]+|$)(.*)$")
_CLOSING_SEQUENCE = re.compile(r"(?:[ \t]+#+)?[ \t]*$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_HTML_SPACE = re.compile(r"[ \t\r\n\f]+")
_HTML_HIDDEN = frozenset({"script", "style", "template"})


class _HTMLTitle(HTMLParser):
    """Collect the first usable title and h1 without repairing the document."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.h1: str | None = None
        self._current: str | None = None
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

        if tag == "title" and self.title is None:
            self._finish()
            self._current = tag
            return
        if tag == "h1" and self.h1 is None and self._current != "title":
            self._finish()
            self._current = tag
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
        if tag == self._current:
            self._finish()

    def handle_data(self, data: str) -> None:
        if self._current is not None and not self._hidden:
            self._text.append(data)

    def finish(self) -> str | None:
        """Close an unterminated candidate and apply title-over-h1 precedence."""
        self._finish()
        return self.title or self.h1

    def _finish(self) -> None:
        if self._current is None:
            return
        candidate = _HTML_SPACE.sub(" ", "".join(self._text)).strip()
        if candidate:
            if self._current == "title" and self.title is None:
                self.title = candidate
            elif self._current == "h1" and self.h1 is None:
                self.h1 = candidate
        self._current = None
        self._text = []


def markdown_title(markdown: str) -> str | None:
    """Return the first non-empty ATX level-one heading in ``markdown``.

    Up to three leading spaces are accepted. Headings of other levels and
    apparent headings inside backtick or tilde fenced code blocks are ignored.
    An optional closing hash sequence is omitted from the returned text.
    """
    if not isinstance(markdown, str):
        raise TypeError(f"markdown must be a string, got {type(markdown).__name__}")

    fence_character: str | None = None
    fence_length = 0
    for line in markdown.splitlines():
        if fence_character is not None:
            closing = re.fullmatch(
                rf" {{0,3}}{re.escape(fence_character)}{{{fence_length},}}[ \t]*", line
            )
            if closing is not None:
                fence_character = None
                fence_length = 0
            continue

        possible_fence = _FENCE.fullmatch(line)
        if possible_fence is not None:
            marker, info = possible_fence.groups()
            if marker[0] == "~" or "`" not in info:
                fence_character = marker[0]
                fence_length = len(marker)
                continue

        heading = _ATX_H1.fullmatch(line)
        if heading is not None:
            candidate = _CLOSING_SEQUENCE.sub("", heading.group(1)).strip()
            if candidate:
                return candidate
    return None


def html_title(html: str) -> str | None:
    """Return an HTML document's title, falling back to its first non-empty h1.

    A non-empty ``title`` element wins wherever it occurs in the source. Nested
    markup and link targets are omitted while readable text, decoded character
    references and image alternative text remain.
    """
    if not isinstance(html, str):
        raise TypeError(f"html must be a string, got {type(html).__name__}")
    parser = _HTMLTitle()
    parser.feed(html)
    parser.close()
    return parser.finish()


def parse_title(content: str, format: str) -> str | None:
    """Return the title parsed from Markdown or HTML ``content``.

    ``format`` must be ``"markdown"`` or ``"html"``. This function only
    parses the supplied string; it does not read from or write to a store.
    """
    if not isinstance(format, str):
        raise TypeError(f"format must be a string, got {type(format).__name__}")
    if format == "markdown":
        return markdown_title(content)
    if format == "html":
        return html_title(content)
    raise ValueError(f"format must be 'markdown' or 'html', got {format!r}")


__all__ = ["html_title", "markdown_title", "parse_title"]
