"""The injective mapping from MediaWiki page titles to Outrage keys."""

from __future__ import annotations

import re

_LEADING_ZERO = re.compile(r"0\d+")


class TitleError(ValueError):
    """A title violates a MediaWiki invariant the key mapping relies on."""


def title_to_key(title: str) -> str:
    """Map a page title to a reversible Outrage key.

    Slash remains a hierarchy. Segments that Outrage would read as metadata,
    wildcards or normalised integers gain ``#``; MediaWiki forbids ``#`` in a
    title, which makes that prefix collision-free.
    """
    if "#" in title:
        raise TitleError(f"MediaWiki title unexpectedly contains #: {title!r}")
    segments = title.split("/")
    escaped = [
        "#" + segment
        if segment.startswith(("!", "?")) or _LEADING_ZERO.fullmatch(segment)
        else segment
        for segment in segments
    ]
    return "/".join(escaped)


def link_to_key(target: str) -> str:
    """Map a wikilink target, preserving its optional section fragment."""
    title, marker, fragment = target.partition("#")
    mapped = title_to_key(title)
    return mapped + (marker + fragment if marker else "")


__all__ = ["TitleError", "link_to_key", "title_to_key"]
