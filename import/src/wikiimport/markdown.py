"""A deliberately lossy, predictable wikitext-to-Markdown converter."""

from __future__ import annotations

import html
import re

import mwparserfromhell
from mwparserfromhell.nodes import (
    Argument,
    Comment,
    ExternalLink,
    Heading,
    HTMLEntity,
    Tag,
    Template,
    Text,
    Wikilink,
)

from .titles import link_to_key

_DROP_LINKS = {"category", "file", "image"}
_DROP_TAGS = {"gallery", "math", "ref", "references", "score", "timeline"}
_TABLE = re.compile(r"(?ms)^\{\|.*?^\|\}\s*")
_BLANKS = re.compile(r"\n[ \t]*\n(?:[ \t]*\n)+")
_BOLD = re.compile(r"'''(.*?)'''", re.DOTALL)
_ITALIC = re.compile(r"''(.*?)''", re.DOTALL)
_HEADING = re.compile(r"\x00H([1-6])\x00")


def _render(code: object) -> str:
    out: list[str] = []
    for node in code.nodes:
        if isinstance(node, Text):
            out.append(str(node.value))
        elif isinstance(node, (Template, Comment)):
            continue
        elif isinstance(node, Heading):
            level = min(max(int(node.level), 1), 6)
            out.append(f"\n\x00H{level}\x00 {_render(node.title).strip()}\n")
        elif isinstance(node, Wikilink):
            target = str(node.title).strip()
            prefix = target.partition(":")[0].casefold()
            if prefix in _DROP_LINKS:
                continue
            shown = _render(node.text).strip() if node.text is not None else target
            out.append(f"[{shown}]({link_to_key(target)})")
        elif isinstance(node, ExternalLink):
            url = str(node.url).strip()
            shown = _render(node.title).strip() if node.title is not None else ""
            out.append(f"[{shown}]({url})" if shown else url)
        elif isinstance(node, HTMLEntity):
            out.append(str(node.normalize()))
        elif isinstance(node, Tag):
            tag = str(node.tag).strip().casefold()
            if tag in _DROP_TAGS or tag == "table":
                continue
            if tag == "br":
                out.append("\n")
            elif tag in {"b", "strong"} and node.contents is not None:
                out.append(f"**{_render(node.contents)}**")
            elif tag in {"i", "em"} and node.contents is not None:
                out.append(f"*{_render(node.contents)}*")
            elif tag == "li":
                out.append(str(node.wiki_markup))
            elif node.contents is not None:
                out.append(_render(node.contents))
        elif isinstance(node, Argument):
            if node.default is not None:
                out.append(_render(node.default))
        else:
            out.append(str(node))
    return "".join(out)


def _lists(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^([*#:]+)[ \t]+(.*)$", line)
        if match is None:
            lines.append(line.rstrip())
            continue
        marks, body = match.groups()
        indent = "  " * (len(marks) - 1)
        marker = ">" if marks[-1] == ":" else ("1." if marks[-1] == "#" else "-")
        lines.append(f"{indent}{marker} {body.rstrip()}")
    return "\n".join(lines)


def to_markdown(wikitext: str) -> str:
    """Convert one article without mutating and reserialising its node tree."""
    without_tables = _TABLE.sub("", wikitext)
    rendered = _render(mwparserfromhell.parse(without_tables))
    rendered = _lists(rendered)
    rendered = _HEADING.sub(lambda match: "#" * int(match.group(1)), rendered)
    rendered = _BOLD.sub(r"**\1**", rendered)
    rendered = _ITALIC.sub(r"*\1*", rendered)
    rendered = html.unescape(rendered)
    rendered = _BLANKS.sub("\n\n", rendered)
    return rendered.strip() + "\n" if rendered.strip() else ""


__all__ = ["to_markdown"]
