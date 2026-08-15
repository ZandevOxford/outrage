"""Parsing and validation for the Rage key namespace.

A key is one or more segments joined by ``.``, where a segment matches
``[A-Za-z0-9_-]+``. A key may carry at most one metadata suffix, introduced by
``:`` at the end of the key, whose name is a single segment. See design.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SEGMENT_RE = re.compile(r"\A[A-Za-z0-9_-]+\Z")

#: The parent of a top level key. Not itself a valid key.
ROOT = ""

#: Sorts immediately after ``.``, and after every character legal in a segment.
#: Used to bound subtree scans without resorting to LIKE, whose ``_`` wildcard
#: would otherwise match the underscores that segments are allowed to contain.
_AFTER_DOT = "/"


class InvalidKeyError(ValueError):
    """Raised when a key does not match the grammar."""


@dataclass(frozen=True, slots=True)
class Key:
    """A parsed key, with the columns derived from it."""

    key: str
    """The full key as given, including any metadata suffix."""

    doc_key: str
    """The key with any metadata suffix removed."""

    meta_name: str | None
    """The metadata name, or None if the key names a document."""

    parent: str
    """The enclosing key. A document's metadata has that document as its
    parent, so metadata lists alongside subkeys."""

    @property
    def is_metadata(self) -> bool:
        return self.meta_name is not None


def parse(key: str) -> Key:
    """Parse and validate ``key``.

    Raises InvalidKeyError if it does not match the grammar.
    """
    if not isinstance(key, str):
        raise InvalidKeyError(f"key must be a string, got {type(key).__name__}")
    if not key:
        raise InvalidKeyError("key must not be empty")

    doc_key, colon, meta_name = key.partition(":")

    if not colon:
        meta_name = None
    else:
        if ":" in meta_name:
            raise InvalidKeyError(f"key {key!r} has more than one metadata suffix")
        if not SEGMENT_RE.match(meta_name):
            raise InvalidKeyError(
                f"metadata name {meta_name!r} in key {key!r} is not a single valid segment"
            )

    if not doc_key:
        raise InvalidKeyError(f"key {key!r} has no document key before its metadata suffix")
    for segment in doc_key.split("."):
        if not SEGMENT_RE.match(segment):
            raise InvalidKeyError(f"segment {segment!r} in key {key!r} is not valid")

    if meta_name is not None:
        parent = doc_key
    else:
        parent, _, _ = doc_key.rpartition(".")

    return Key(key=key, doc_key=doc_key, meta_name=meta_name, parent=parent)


def is_valid(key: str) -> bool:
    """Whether ``key`` matches the grammar."""
    try:
        parse(key)
    except InvalidKeyError:
        return False
    return True


def ancestors(key: str) -> list[str]:
    """The enclosing document keys of ``key``, outermost first.

    These are the keys that exist implicitly. A metadata key's ancestors
    include the document it is attached to.

    >>> ancestors("context.a1b2.design:title")
    ['context', 'context.a1b2', 'context.a1b2.design']
    """
    parsed = parse(key)
    segments = parsed.doc_key.split(".")
    if not parsed.is_metadata:
        segments = segments[:-1]
    return [".".join(segments[: i + 1]) for i in range(len(segments))]


def depth(key: str) -> int:
    """The number of segments in the document part of ``key``.

    A metadata suffix does not add depth; ``a.b`` and ``a.b:title`` are both at
    depth 2.
    """
    return parse(key).doc_key.count(".") + 1


def subtree_range(key: str) -> tuple[str, str]:
    """Half open bounds on the document keys strictly beneath ``key``.

    Everything under ``a`` starts with ``a.``, so ``lo <= doc_key < hi``
    selects exactly the subtree, as an index range scan rather than a prefix
    match. This is what keeps ``a.b`` from picking up ``a.beta``.
    """
    doc_key = parse(key).doc_key
    return doc_key + ".", doc_key + _AFTER_DOT
