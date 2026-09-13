"""Stream current revisions from a compressed MediaWiki XML export."""

from __future__ import annotations

import bz2
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Page:
    """The fields conversion needs from one MediaWiki page."""

    title: str
    namespace: int
    timestamp: str
    text: str
    redirect: str | None


def _child(element: ET.Element | None, name: str) -> ET.Element | None:
    if element is None:
        return None
    for child in element:
        if child.tag.rpartition("}")[2] == name:
            return child
    return None


def _text(element: ET.Element | None) -> str:
    return "" if element is None or element.text is None else element.text


def read_pages(path: str | Path, namespaces: frozenset[int]) -> Iterator[Page]:
    """Yield selected pages while releasing each parsed XML element promptly."""
    with bz2.open(Path(path), "rb") as stream:
        for _, element in ET.iterparse(stream, events=("end",)):
            if element.tag.rpartition("}")[2] != "page":
                continue
            namespace = int(_text(_child(element, "ns")))
            if namespace in namespaces:
                revision = _child(element, "revision")
                redirect = _child(element, "redirect")
                yield Page(
                    title=_text(_child(element, "title")),
                    namespace=namespace,
                    timestamp=_text(_child(revision, "timestamp")),
                    text=_text(_child(revision, "text")),
                    redirect=None if redirect is None else redirect.attrib.get("title"),
                )
            element.clear()


__all__ = ["Page", "read_pages"]
