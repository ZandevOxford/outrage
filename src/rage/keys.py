"""Parsing and validation for the Rage key namespace.

A key is one or more segments joined by ``/``, where a segment matches
``[A-Za-z0-9_.-]+``. A key may carry at most one metadata suffix, introduced by
``:`` at the end of the key, whose name is a single segment. A key being
written may use ``?`` as a whole segment to ask the store to allocate a number
for it. See design.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Separates the segments of a key.
DELIMITER = "/"

#: Introduces the metadata suffix.
META = ":"

#: Stands in for a segment the store should allocate. Legal only when writing,
#: and only as a whole segment: it is not a pattern.
WILDCARD = "?"

SEGMENT_RE = re.compile(r"\A[A-Za-z0-9_.-]+\Z")

#: Segments that would read as path navigation. Keys are not paths and are
#: never resolved, so these can only mislead.
RESERVED_SEGMENTS = frozenset({".", ".."})

#: The parent of a top level key. Not itself a valid key.
ROOT = ""

#: Sorts immediately after ``/``. Used to bound subtree scans without resorting
#: to LIKE, whose ``_`` wildcard would otherwise match the underscores that
#: segments are allowed to contain. ``/`` and ``0`` are adjacent code points,
#: so nothing can sort between ``k + "/"`` and ``k + _AFTER_DELIMITER`` except
#: the keys beneath ``k``, whatever segments are made of.
_AFTER_DELIMITER = "0"


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

    wildcard_parent: str | None = None
    """The key enclosing the ``?`` segment, or None if there is no wildcard.
    ROOT when the wildcard is the first segment. This is the key whose children
    the allocated segment has to be unique among."""

    @property
    def is_metadata(self) -> bool:
        return self.meta_name is not None

    @property
    def has_wildcard(self) -> bool:
        return self.wildcard_parent is not None


def parse(key: str, *, allow_wildcard: bool = False) -> Key:
    """Parse and validate ``key``.

    With ``allow_wildcard`` a single segment of the document key may be ``?``,
    which the store replaces with a number it allocates. Reads and deletes
    parse without it, so a wildcard cannot be mistaken for a search.

    Raises InvalidKeyError if it does not match the grammar.
    """
    if not isinstance(key, str):
        raise InvalidKeyError(f"key must be a string, got {type(key).__name__}")
    if not key:
        raise InvalidKeyError("key must not be empty")

    doc_key, colon, meta_name = key.partition(META)

    if not colon:
        meta_name = None
    else:
        if META in meta_name:
            raise InvalidKeyError(f"key {key!r} has more than one metadata suffix")
        if DELIMITER in meta_name:
            raise InvalidKeyError(
                f"metadata name {meta_name!r} in key {key!r} must be a single segment"
            )
        _check_segment(meta_name, key, what="metadata name")

    if not doc_key:
        raise InvalidKeyError(f"key {key!r} has no document key before its metadata suffix")

    segments = doc_key.split(DELIMITER)
    wildcard_parent = None
    for index, segment in enumerate(segments):
        if segment == WILDCARD:
            if not allow_wildcard:
                raise InvalidKeyError(
                    f"key {key!r} may not contain {WILDCARD!r}; it is allowed only when storing"
                )
            if wildcard_parent is not None:
                raise InvalidKeyError(f"key {key!r} has more than one {WILDCARD!r} segment")
            wildcard_parent = DELIMITER.join(segments[:index])
        else:
            _check_segment(segment, key)

    if meta_name is not None:
        parent = doc_key
    else:
        parent, _, _ = doc_key.rpartition(DELIMITER)

    return Key(
        key=key,
        doc_key=doc_key,
        meta_name=meta_name,
        parent=parent,
        wildcard_parent=wildcard_parent,
    )


def _check_segment(segment: str, key: str, what: str = "segment") -> None:
    if WILDCARD in segment:
        raise InvalidKeyError(
            f"{what} {segment!r} in key {key!r} is not valid: "
            f"{WILDCARD!r} must stand alone as a whole segment"
        )
    if segment in RESERVED_SEGMENTS:
        raise InvalidKeyError(f"{what} {segment!r} in key {key!r} is reserved")
    if not SEGMENT_RE.match(segment):
        raise InvalidKeyError(f"{what} {segment!r} in key {key!r} is not valid")


def is_valid(key: str, *, allow_wildcard: bool = False) -> bool:
    """Whether ``key`` matches the grammar."""
    try:
        parse(key, allow_wildcard=allow_wildcard)
    except InvalidKeyError:
        return False
    return True


def substitute_wildcard(key: str, segment: str) -> str:
    """Return ``key`` with its ``?`` segment replaced by ``segment``.

    >>> substitute_wildcard("context/?/design", "7")
    'context/7/design'
    """
    parsed = parse(key, allow_wildcard=True)
    if not parsed.has_wildcard:
        raise InvalidKeyError(f"key {key!r} has no {WILDCARD!r} segment to substitute")
    doc_key = DELIMITER.join(
        segment if part == WILDCARD else part for part in parsed.doc_key.split(DELIMITER)
    )
    return doc_key if parsed.meta_name is None else f"{doc_key}{META}{parsed.meta_name}"


def ancestors(key: str) -> list[str]:
    """The enclosing document keys of ``key``, outermost first.

    These are the keys that exist implicitly. A metadata key's ancestors
    include the document it is attached to.

    >>> ancestors("context/a1b2/design:title")
    ['context', 'context/a1b2', 'context/a1b2/design']
    """
    parsed = parse(key)
    segments = parsed.doc_key.split(DELIMITER)
    if not parsed.is_metadata:
        segments = segments[:-1]
    return [DELIMITER.join(segments[: i + 1]) for i in range(len(segments))]


def depth(key: str) -> int:
    """The number of segments in the document part of ``key``.

    A metadata suffix does not add depth; ``a/b`` and ``a/b:title`` are both at
    depth 2.
    """
    return parse(key).doc_key.count(DELIMITER) + 1


def subtree_range(key: str) -> tuple[str, str]:
    """Half open bounds on the document keys strictly beneath ``key``.

    Everything under ``a`` starts with ``a/``, so ``lo <= doc_key < hi``
    selects exactly the subtree, as an index range scan rather than a prefix
    match. This is what keeps ``a/b`` from picking up ``a/beta``.
    """
    doc_key = parse(key).doc_key
    return doc_key + DELIMITER, doc_key + _AFTER_DELIMITER
