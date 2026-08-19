"""Parsing and validation for the Rage key namespace.

A key is one or more segments joined by ``/``, and ``/`` is the only separator
there is. A segment may hold almost any text: the intent is that a key can
mirror a filesystem path without transforming the names it carries, so the only
exclusions are ``/`` itself and the control characters below ``\\t``.

A segment beginning with ``!`` names metadata about the document its segment
sits under, so ``context/5/state/!title`` is the title of ``context/5/state``.
Everything from the first ``!`` segment onward is metadata: paths may continue
below one, and ``a/!title/b`` is a second metadata entry on ``a`` rather than a
document.

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

#: Begins a segment naming metadata about the document above it. Nothing rests
#: on where ``!`` sorts any more -- the sort form discriminates metadata
#: explicitly -- so this is a spelling convention rather than a mechanism.
META_PREFIX = "!"

#: Stands in for a segment the store should allocate. Legal only when writing,
#: and only as a whole segment: elsewhere in a segment it is ordinary text, so
#: ``notes/where?.md`` is a perfectly good key.
WILDCARD = "?"

#: The metadata suffix this namespace used until schema 4, kept only so the
#: schema 2 to 3 migration can read keys written in it. No longer rejected by
#: ``parse``: ``:`` is an ordinary segment character now, like any other.
LEGACY_META = ":"

#: The lowest character a segment may contain. Excluding everything below tab
#: costs nothing worth mirroring -- no filesystem name addresses that range --
#: and it is what lets the sort form below discriminate segments without
#: escaping, since no legal segment character can collide with its markers.
MIN_SEGMENT_CHAR = "\t"

#: Bounds on a key, generous enough that only a generated key will meet them.
#: Both are guidelines made checkable rather than limits anyone should design
#: against: a segment is usually well under 20 characters and a key well under
#: half a dozen segments.
MAX_SEGMENT_CHARS = 1024
MAX_SEGMENTS = 128

#: The parent of a top level key. Not itself a valid key.
ROOT = ""

#: Sorts immediately after ``/``. Used to bound subtree scans over ``doc_key``
#: without resorting to LIKE, whose ``_`` wildcard would otherwise match the
#: underscores that segments are allowed to contain. ``/`` and ``0`` are
#: adjacent code points, so nothing can sort between ``k + "/"`` and
#: ``k + _AFTER_DELIMITER`` except the keys beneath ``k``, whatever segments are
#: made of. This bounds *stored keys*, not sort forms, so the markers below do
#: not reach it.
_AFTER_DELIMITER = "0"

#: Markers the sort form puts in front of every segment, and the delimiter it
#: joins them with. All three sort below ``MIN_SEGMENT_CHAR``, so none of them
#: can occur inside a segment and the encoding needs no escaping.
#:
#: ``_SORT_META`` before ``_SORT_DOC`` is what puts a document's metadata ahead
#: of its subkeys. ``_SORT_DELIMITER`` below every segment character is what
#: puts a subtree immediately after its parent: ``a/b`` sorts before ``a-x``,
#: where a plain ``/`` would put it after, because ``-`` sorts below ``/``.
#: Together they make the order of a metadata survey the order of the documents
#: it describes -- one ordering, not two that nearly agree.
_SORT_META = "\x01"
_SORT_DOC = "\x02"
_SORT_DELIMITER = "\x03"

#: A segment that names nothing but a number. Deliberately not str.isdigit,
#: which accepts superscripts and other digits that int() then rejects.
NUMERIC_RE = re.compile(r"\A[0-9]+\Z")

#: Width a numeric segment is padded to in sort form. No parent will hold
#: 10**16 children, and it is wide enough for epoch milliseconds and
#: microseconds, which are plausible segments. A longer number still sorts --
#: just not numerically against shorter ones, which is the same failure this
#: padding removes.
_SORT_WIDTH = 16


def normalise_key(key: str) -> str:
    """``key`` with its delimiters tidied: no leading, trailing or repeated ``/``.

    Runs before validation, so a key is judged in the form it will be stored
    in. Note that this cannot produce the root: ``"/"`` normalises to the empty
    string, which is then rejected like any other empty key rather than
    becoming a spelling of the top level.

    >>> normalise_key("/a//b/"), normalise_key("a/b")
    ('a/b', 'a/b')
    """
    return DELIMITER.join(part for part in key.split(DELIMITER) if part)


def normalise_segment(segment: str) -> str:
    """A numeric segment without its leading zeros; anything else unchanged.

    This makes ``01`` and ``1`` the same segment rather than two, which is what
    keeps a padded key from naming a second document alongside the one it was
    meant to name, and what keeps the sort form injective.

    >>> normalise_segment("007"), normalise_segment("000"), normalise_segment("x0")
    ('7', '0', 'x0')
    """
    if NUMERIC_RE.match(segment):
        return segment.lstrip("0") or "0"
    return segment


def _normalise(segment: str) -> str:
    """``normalise_segment``, seeing past a metadata prefix.

    A numeric metadata name normalises like any other number, so ``!007`` and
    ``!7`` are one metadata entry rather than two -- the same reason document
    segments are normalised, and the same reason ``_sort_segment`` pads past
    the prefix.
    """
    if segment.startswith(META_PREFIX):
        return META_PREFIX + normalise_segment(segment[len(META_PREFIX) :])
    return normalise_segment(segment)


def sort_form(key: str) -> str:
    """``key`` encoded for ordering only, never stored in place of the key.

    Three things happen at once, and each removes an ordering defect:

    * numeric segments are zero padded, so ``a/2`` sorts before ``a/10``.
      Plain text ordering gives the reverse, which is untidy in a listing and
      unsafe under a cursor: a reader resuming after ``a/9`` never sees
      ``a/10``, because the new key sorts *behind* the one it was written after.
    * every segment is marked as metadata or document, so a document's metadata
      sorts ahead of its subkeys.
    * segments are joined by a delimiter below every character they may
      contain, so a subtree sorts immediately after its parent.

    The marking is a prefix rather than a property of the segment text, so two
    different keys cannot share a sort form. That matters more than it looks:
    pagination resumes with ``sort_key > ?`` over a non-unique index, so two
    rows sharing a sort key would mean resuming past one silently skipped the
    other.

    >>> sorted(["a/10", "a/2"]), sorted(["a/10", "a/2"], key=sort_form)
    (['a/10', 'a/2'], ['a/2', 'a/10'])
    >>> sort_form("a/!title") < sort_form("a/b/!title")
    True
    >>> sort_form("a/!title") < sort_form("a-x/!title")
    True
    """
    return _SORT_DELIMITER.join(_sort_segment(part) for part in key.split(DELIMITER))


def _sort_segment(segment: str) -> str:
    """One segment marked and padded for ordering."""
    if segment.startswith(META_PREFIX):
        return _SORT_META + _pad(segment[len(META_PREFIX) :])
    return _SORT_DOC + _pad(segment)


def meta_sort_suffix(meta_name: str) -> str:
    """What to append to ``sort_form(doc)`` to get ``sort_form(doc/!meta_name)``.

    A caller that has a document's stored ``sort_key`` and wants to know where
    its metadata *would* have sorted can append this rather than reparsing the
    key. Exposed because the alternative is composing it by hand out of
    ``DELIMITER``, which silently stopped being the sort delimiter in schema 5
    and put every synthesised position in the wrong place.

    >>> sort_form("a") + meta_sort_suffix("title") == sort_form("a/!title")
    True
    """
    return _SORT_DELIMITER + _sort_segment(META_PREFIX + meta_name)


def _pad(segment: str) -> str:
    """Zero pad a numeric segment, so ``!2`` still sorts before ``!10``."""
    return segment.zfill(_SORT_WIDTH) if NUMERIC_RE.match(segment) else segment


class InvalidKeyError(RageError, ValueError):
    """Raised when a key does not match the grammar.

    A ``RageError`` because a malformed key is *about the request*, so a front
    end should render it as one line rather than a traceback. Still a
    ``ValueError`` as well, so existing callers catching that go on working.
    """


@dataclass(frozen=True, slots=True)
class Key:
    """A parsed key, with the columns derived from it."""

    key: str
    """The full key, normalised, including any metadata segments. Delimiters
    are tidied and numeric segments have lost their leading zeros, so this may
    differ from the string that was parsed."""

    doc_key: str
    """The key up to but excluding its first metadata segment."""

    meta_name: str | None
    """Everything from the first metadata segment onward, without the leading
    ``!``, or None if the key names a document. May itself contain ``/``, since
    a path may continue below a metadata segment: ``a/!title/b`` has a
    ``meta_name`` of ``title/b``."""

    parent: str
    """The enclosing key: this key without its last segment. A document's
    metadata therefore has that document as its parent, and lists alongside its
    subkeys."""

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
    """The current spelling of a key written with the pre-schema-4 ``:`` suffix.

    Only for reading a store old enough to hold that spelling. ``:`` is an
    ordinary segment character now, so this must not be applied to a key a
    caller supplied -- it would rewrite one they meant literally.

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

    original = key
    key = normalise_key(key)
    if not key:
        raise InvalidKeyError(f"key {original!r} must not be empty")

    segments = key.split(DELIMITER)
    if len(segments) > MAX_SEGMENTS:
        raise InvalidKeyError(
            f"key {original!r} has {len(segments)} segments; at most {MAX_SEGMENTS} are allowed"
        )

    # Everything from the first metadata segment onward is metadata, so a path
    # may continue below one and nothing under it is a document.
    meta_at = next(
        (i for i, segment in enumerate(segments) if segment.startswith(META_PREFIX)),
        None,
    )
    if meta_at == 0:
        raise InvalidKeyError(
            f"key {original!r} has no document key before its metadata segment"
        )

    doc_segments = segments if meta_at is None else segments[:meta_at]
    meta_segments = [] if meta_at is None else segments[meta_at:]

    for segment in segments:
        _check_segment(segment, original)

    wildcard_parent = None
    for index, segment in enumerate(segments):
        if segment != WILDCARD:
            continue
        if not allow_wildcard:
            raise InvalidKeyError(
                f"key {original!r} may not contain {WILDCARD!r}; "
                f"it is allowed only when storing"
            )
        if meta_at is not None and index >= meta_at:
            raise InvalidKeyError(
                f"key {original!r} may not allocate a metadata segment; "
                f"{WILDCARD!r} is allowed only in the document part of a key"
            )
        if wildcard_parent is not None:
            raise InvalidKeyError(f"key {original!r} has more than one {WILDCARD!r} segment")
        wildcard_parent = DELIMITER.join(_normalise(p) for p in doc_segments[:index])

    # Normalised only after validation, so a complaint names the segment as it
    # was written rather than a tidied one the caller never typed.
    doc_key = DELIMITER.join(_normalise(segment) for segment in doc_segments)
    meta_parts = [_normalise(segment) for segment in meta_segments]

    if meta_parts:
        key = DELIMITER.join([doc_key, *meta_parts])
        meta_name = DELIMITER.join(meta_parts)[len(META_PREFIX) :]
    else:
        key = doc_key
        meta_name = None

    parent, _, _ = key.rpartition(DELIMITER)

    return Key(
        key=key,
        doc_key=doc_key,
        meta_name=meta_name,
        parent=parent,
        wildcard_parent=wildcard_parent,
    )


def _check_segment(segment: str, key: str) -> None:
    what = "metadata segment" if segment.startswith(META_PREFIX) else "segment"

    if segment == META_PREFIX:
        raise InvalidKeyError(f"key {key!r} has no metadata name after {META_PREFIX!r}")
    if len(segment) > MAX_SEGMENT_CHARS:
        raise InvalidKeyError(
            f"{what} in key {key!r} is {len(segment)} characters; "
            f"at most {MAX_SEGMENT_CHARS} are allowed"
        )
    for character in segment:
        if character < MIN_SEGMENT_CHAR:
            raise InvalidKeyError(
                f"{what} {segment!r} in key {key!r} is not valid: it contains "
                f"{character!r}, and a segment may not hold characters below "
                f"{MIN_SEGMENT_CHAR!r}"
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
    return DELIMITER.join(
        segment if part == WILDCARD else part for part in parsed.key.split(DELIMITER)
    )


def ancestors(key: str) -> list[str]:
    """The enclosing keys of ``key``, outermost first.

    These are the keys that exist implicitly. A metadata key's ancestors
    include the document it is attached to.

    >>> ancestors("context/a1b2/design/!title")
    ['context', 'context/a1b2', 'context/a1b2/design']
    """
    segments = parse(key).key.split(DELIMITER)
    return [DELIMITER.join(segments[: i + 1]) for i in range(len(segments) - 1)]


def depth(key: str) -> int:
    """The number of segments in the document part of ``key``.

    Metadata segments do not add depth; ``a/b`` and ``a/b/!title`` are both at
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
