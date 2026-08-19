"""Parsing and validation for the Rage key namespace.

A key is one or more segments joined by ``/``, and ``/`` is the only
separator there is. A document segment matches ``[A-Za-z0-9_.-]+``. A segment
beginning with ``!`` names metadata about the document its segment sits under,
so ``context/5/state/!title`` is the title of ``context/5/state``; it is legal
only as the last segment, so metadata is always a leaf. ``!`` sorts below every
character a document segment may begin with, which is what keeps a document's
metadata ordered alongside the document rather than after its whole subtree.

A key being written may use ``?`` as a whole segment to ask the store to
allocate a number for it. A segment that is purely numeric is normalised by
stripping its leading zeros, so ``context/01`` and ``context/1`` are the same
key, and is sorted as though zero padded, so ``context/2`` comes before
``context/10``. See design.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import RageError

#: Separates the segments of a key, and the only separator in the namespace.
DELIMITER = "/"

#: Begins a segment naming metadata about the document above it. Chosen to sort
#: below ``/`` and below every character a document segment may start with, so
#: that ``a/!title`` sorts before ``a/b`` and therefore before ``a/b/!title``.
#: That is what makes the order of a metadata survey the order of the documents
#: it describes; with the old ``:`` suffix, which sorts *above* ``/``, the two
#: orderings disagreed for every document that had a subtree.
META_PREFIX = "!"

#: The metadata suffix this namespace used until schema 4. Rejected on sight
#: rather than accepted quietly, because a key that still parses under the old
#: spelling would name a second document beside the one it was meant to name.
LEGACY_META = ":"

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
#: the keys beneath ``k``, whatever segments are made of -- metadata included,
#: since ``!`` sorts above ``/`` as a character even though it sorts below
#: every segment start.
_AFTER_DELIMITER = "0"

#: A segment that names nothing but a number. Deliberately not str.isdigit,
#: which accepts superscripts and other digits that int() then rejects.
NUMERIC_RE = re.compile(r"\A[0-9]+\Z")

#: Width a numeric segment is padded to in sort form. No parent will hold
#: 10**16 children, and a longer number still sorts -- just not numerically
#: against shorter ones, which is the same failure this padding removes.
_SORT_WIDTH = 16


def normalise_segment(segment: str) -> str:
    """A numeric segment without its leading zeros; anything else unchanged.

    This makes ``01`` and ``1`` the same segment rather than two, which is what
    keeps a padded key from naming a second document alongside the one it was
    meant to name.

    >>> normalise_segment("007"), normalise_segment("000"), normalise_segment("x0")
    ('7', '0', 'x0')
    """
    if NUMERIC_RE.match(segment):
        return segment.lstrip("0") or "0"
    return segment


def sort_form(key: str) -> str:
    """``key`` with its numeric segments zero padded, for ordering only.

    Sorting keys as plain text puts ``a/10`` before ``a/2``, which is wrong on
    its own and dangerous under a cursor: a reader resuming after ``a/9`` never
    sees ``a/10``, because the new key sorts *behind* the one it was written
    after. Padding restores the ordering the numbers imply.

    Since metadata is an ordinary segment, this is one rule applied uniformly
    rather than a document part and a suffix handled separately.

    Never stored in place of a key and never returned to a caller -- the key
    itself stays in the normalised, unpadded form.

    >>> sorted(["a/10", "a/2"]), sorted(["a/10", "a/2"], key=sort_form)
    (['a/10', 'a/2'], ['a/2', 'a/10'])
    >>> sort_form("a/!title") < sort_form("a/b/!title")
    True
    """
    return DELIMITER.join(_pad(part) for part in key.split(DELIMITER))


def _pad(segment: str) -> str:
    """Zero pad a numeric segment, seeing past a metadata prefix.

    A numeric metadata name pads like any other number, so ``!2`` still sorts
    before ``!10``.
    """
    if segment.startswith(META_PREFIX):
        return META_PREFIX + _pad(segment[len(META_PREFIX) :])
    return segment.zfill(_SORT_WIDTH) if NUMERIC_RE.match(segment) else segment


class InvalidKeyError(RageError, ValueError):
    """Raised when a key does not match the grammar.

    A ``RageError`` because a malformed key is *about the request*, so a front
    end should render it as one line. It matters more since schema 4: every key
    written in the old ``:`` spelling arrives here, and the message says what to
    write instead, which is no use buried in a traceback. Still a ``ValueError``
    as well, so existing callers catching that go on working.
    """


@dataclass(frozen=True, slots=True)
class Key:
    """A parsed key, with the columns derived from it."""

    key: str
    """The full key, normalised, including any metadata segment. Numeric
    segments have lost their leading zeros, so this may differ from the string
    that was parsed."""

    doc_key: str
    """The key with any metadata segment removed."""

    meta_name: str | None
    """The metadata name without its ``!``, or None if the key names a
    document."""

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


def migrate_legacy(key: str) -> str:
    """The schema 4 spelling of a key written with the old ``:`` suffix.

    >>> migrate_legacy("context/5/state:title")
    'context/5/state/!title'
    """
    doc_key, colon, meta_name = key.partition(LEGACY_META)
    if not colon:
        return key
    return f"{doc_key}{DELIMITER}{META_PREFIX}{meta_name}"


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

    # Named rather than merely rejected: every stored key and every piece of
    # prose used this spelling until schema 4, so the useful error is the one
    # that says what to write instead.
    if LEGACY_META in key:
        raise InvalidKeyError(
            f"key {key!r} uses the old {LEGACY_META!r} metadata suffix; metadata is now "
            f"a segment of its own, so write {migrate_legacy(key)!r}"
        )

    segments = key.split(DELIMITER)

    meta_name = None
    if segments[-1].startswith(META_PREFIX):
        meta_name = segments[-1][len(META_PREFIX) :]
        if not meta_name:
            raise InvalidKeyError(f"key {key!r} has no metadata name after {META_PREFIX!r}")
        _check_segment(meta_name, key, what="metadata name")
        segments = segments[:-1]
        if not segments:
            raise InvalidKeyError(
                f"key {key!r} has no document key before its metadata segment"
            )

    # Only the last segment may be metadata, so metadata stays a leaf and
    # nothing can be stored beneath it.
    for segment in segments:
        if segment.startswith(META_PREFIX):
            raise InvalidKeyError(
                f"segment {segment!r} in key {key!r} is not valid: "
                f"a {META_PREFIX!r} segment names metadata and may only come last"
            )

    wildcard_parent = None
    for index, segment in enumerate(segments):
        if segment == WILDCARD:
            if not allow_wildcard:
                raise InvalidKeyError(
                    f"key {key!r} may not contain {WILDCARD!r}; it is allowed only when storing"
                )
            if wildcard_parent is not None:
                raise InvalidKeyError(f"key {key!r} has more than one {WILDCARD!r} segment")
            wildcard_parent = DELIMITER.join(normalise_segment(part) for part in segments[:index])
        else:
            _check_segment(segment, key)

    # Normalised only after validation, so a complaint names the segment as it
    # was written rather than a tidied one the caller never typed.
    doc_key = DELIMITER.join(normalise_segment(segment) for segment in segments)

    if meta_name is not None:
        meta_name = normalise_segment(meta_name)
        parent = doc_key
        key = f"{doc_key}{DELIMITER}{META_PREFIX}{meta_name}"
    else:
        parent, _, _ = doc_key.rpartition(DELIMITER)
        key = doc_key

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
        raise InvalidKeyError(
            f"{what} {segment!r} in key {key!r} is not valid: "
            f"a {what} is one or more of A-Z a-z 0-9 _ . -"
        )


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
    if parsed.meta_name is None:
        return doc_key
    return f"{doc_key}{DELIMITER}{META_PREFIX}{parsed.meta_name}"


def ancestors(key: str) -> list[str]:
    """The enclosing document keys of ``key``, outermost first.

    These are the keys that exist implicitly. A metadata key's ancestors
    include the document it is attached to.

    >>> ancestors("context/a1b2/design/!title")
    ['context', 'context/a1b2', 'context/a1b2/design']
    """
    parsed = parse(key)
    segments = parsed.doc_key.split(DELIMITER)
    if not parsed.is_metadata:
        segments = segments[:-1]
    return [DELIMITER.join(segments[: i + 1]) for i in range(len(segments))]


def depth(key: str) -> int:
    """The number of segments in the document part of ``key``.

    A metadata segment does not add depth; ``a/b`` and ``a/b/!title`` are both
    at depth 2.
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
