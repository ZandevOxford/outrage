"""Parsing and validation for the Rage key namespace.

A key is zero or more segments joined by ``/``, and ``/`` is the only separator
there is. A segment may hold almost any text: the intent is that a key can
mirror a filesystem path without transforming the names it carries, so the only
exclusions are ``/`` itself and the control characters below ``\\t``.

The key with no segments is the **root**, spelled by the empty string. It is a
key like any other: it holds a document, carries metadata as ``!title``, and is
the parent of every top level key. A ``None`` key arriving at a front end means
the root, so that nothing below the boundary carries two spellings of
"everywhere".

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

#: The most segments a key may have **within one store**, and the most a mount
#: point may have. Two bounds in one number, deliberately: a key in the joined
#: namespace is a mount prefix followed by a key inside the store mounted
#: there, so bounding each half at half the total makes every joined key valid
#: *by construction*. Nothing has to check the sum, and no key can exist in a
#: mounted store that the namespace above it cannot name.
#:
#: This was 128 until 2026-08-20, when it was halved to buy that property.
#: 128 was overkill — a key is typically a handful of segments — and the
#: alternative was carrying a drop path through every listing for keys that
#: had no name from outside. See ``project/reference/planned/mounts/cursors``.
MAX_SEGMENTS = 64

#: The most segments a key may have in the namespace a mount table presents,
#: which is the only place the two halves are ever seen joined. Derived rather
#: than chosen, so that halving one cannot be done without the other following.
MAX_JOINED_SEGMENTS = 2 * MAX_SEGMENTS

#: The root: the key with no segments, and the parent of every top level key.
#: It is its own parent, the way POSIX makes ``/..`` be ``/``. That is what
#: lets an ancestor walk terminate without a second value meaning "nowhere",
#: and it is why every query listing a level has to exclude the root from its
#: own listing -- which ``store`` does in one place.
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
    in. ``"/"`` and ``"///"`` reduce to the empty string, which is the root:
    they are spellings of it rather than errors, which is what a key mirroring
    a filesystem path ought to do.

    >>> normalise_key("/a//b/"), normalise_key("a/b"), normalise_key("///")
    ('a/b', 'a/b', '')
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


def displayed(key: str) -> str:
    """How a key is written for a person to read. The root is spelled ``/``.

    The empty string is invisible in a report: it reads as a missing name, or
    as stray indentation, and a reader cannot tell which. ``/`` is a legal
    spelling of the root and normalises straight back to it, so what is printed
    is also what can be typed in again.

    >>> displayed("a/b"), displayed(ROOT)
    ('a/b', '/')
    """
    return key or DELIMITER


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
    * the root sorts as the empty string rather than as one empty segment, so
      it comes before its own metadata and before every top level key. Marked
      as a segment it would sort *after* ``!title``, the metadata marker being
      the lower of the two: the one place the marking would invert rather than
      order. Nothing can collide with it, since every other sort form begins
      with a marker.

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
    >>> sort_form("") < sort_form("!title") < sort_form("a")
    True
    """
    if not key:
        return ROOT
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
    subkeys. The root is its own parent, which is what makes an ancestor walk
    terminate and what every listing of a level has to allow for."""

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


def parse(
    key: str,
    *,
    allow_wildcard: bool = False,
    max_segments: int = MAX_SEGMENTS,
) -> Key:
    """Parse and validate ``key``.

    With ``allow_wildcard`` a single segment of the document key may be ``?``,
    which the store replaces with a number it allocates. Reads and deletes
    parse without it, so a wildcard cannot be mistaken for a search.

    ``max_segments`` defaults to the bound on a key **within one store**, which
    is what almost every caller wants. Only a front end resolving a key across
    a mount table passes ``MAX_JOINED_SEGMENTS``, and it has to ask: defaulting
    to the wider bound would let a store quietly accept a key too deep to be
    named from a namespace it was mounted into, and that key would then be
    invisible rather than refused. The tighter default fails in the safe
    direction.

    Raises InvalidKeyError if it does not match the grammar.
    """
    if not isinstance(key, str):
        raise InvalidKeyError(f"key must be a string, got {type(key).__name__}")

    original = key
    key = normalise_key(key)
    # The root is the key with *no* segments, not one empty segment: splitting
    # "" would give a single empty name, which would then be length checked,
    # counted towards MAX_SEGMENTS and padded into a sort form as though it
    # were something a caller had typed.
    segments = key.split(DELIMITER) if key else []
    if len(segments) > max_segments:
        raise InvalidKeyError(
            f"key {original!r} has {len(segments)} segments; at most {max_segments} are allowed"
        )

    # Everything from the first metadata segment onward is metadata, so a path
    # may continue below one and nothing under it is a document.
    meta_at = next(
        (i for i, segment in enumerate(segments) if segment.startswith(META_PREFIX)),
        None,
    )
    # meta_at == 0 is metadata on the root, which is a document like any
    # other: `!title` alone is the store's own title.
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
        # The document key is left out of the join when there is none, or
        # metadata on the root would spell itself "/!title" and normalise back
        # to something else on the next parse.
        parts = [doc_key, *meta_parts] if doc_key else meta_parts
        key = DELIMITER.join(parts)
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


def is_valid(
    key: str,
    *,
    allow_wildcard: bool = False,
    max_segments: int = MAX_SEGMENTS,
) -> bool:
    """Whether ``key`` matches the grammar."""
    try:
        parse(key, allow_wildcard=allow_wildcard, max_segments=max_segments)
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

    The root is not among them, though it encloses everything. It is not
    brought into being by what sits below it the way the others are -- it is
    always there -- so counting it as implicit would say something untrue about
    every key in the store.

    >>> ancestors("context/a1b2/design/!title")
    ['context', 'context/a1b2', 'context/a1b2/design']
    >>> ancestors("a"), ancestors("")
    ([], [])
    """
    segments = parse(key).key.split(DELIMITER)
    return [DELIMITER.join(segments[: i + 1]) for i in range(len(segments) - 1)]


def depth(key: str) -> int:
    """The number of segments in the document part of ``key``.

    Metadata segments do not add depth; ``a/b`` and ``a/b/!title`` are both at
    depth 2. The root is depth 0, and so is metadata on it: neither has a
    segment to count.

    >>> depth("a/b"), depth("a/b/!title"), depth(""), depth("!title")
    (2, 2, 0, 0)
    """
    doc_key = parse(key).doc_key
    return 0 if doc_key == ROOT else doc_key.count(DELIMITER) + 1


def subtree_range(key: str) -> tuple[str, str]:
    """Half open bounds on the document keys strictly beneath ``key``.

    Everything under ``a`` starts with ``a/``, so ``lo <= doc_key < hi``
    selects exactly the subtree, as an index range scan rather than a prefix
    match. This is what keeps ``a/b`` from picking up ``a/beta``.

    **The root has no such bounds.** Everything is beneath it, and no string
    bounds every key from above. This raises rather than returning something
    that looks usable, because the bounds the formula gives for it -- ``"/"``
    to ``"0"`` -- match nothing at all: a caller that forgot to check would get
    a confident zero from a store full of documents. Select with no range
    predicate instead, which is what ``store`` does.
    """
    doc_key = parse(key).doc_key
    if doc_key == ROOT:
        raise ValueError(
            "the root has no subtree bounds, since everything is beneath it; "
            "select without a range predicate instead"
        )
    return doc_key + DELIMITER, doc_key + _AFTER_DELIMITER


def with_prefix(prefix: str, key: str) -> str:
    """``key``, as seen from a namespace that holds it under ``prefix``.

    The inverse of :func:`strip_prefix`. Joining by hand is what this exists to
    stop: the inner root is the empty string, so ``prefix + "/" + key`` spells
    the mount point itself as ``ref/``, which normalises back to ``ref`` only
    if somebody remembers to normalise it.

    >>> with_prefix("ref", "a/b"), with_prefix("ref", ROOT), with_prefix(ROOT, "a")
    ('ref/a/b', 'ref', 'a')
    """
    if not prefix:
        return key
    if not key:
        return prefix
    return f"{prefix}{DELIMITER}{key}"


def strip_prefix(prefix: str, key: str) -> str | None:
    """``key`` as named from inside ``prefix``, or None if it is not below it.

    The mount point itself maps to the root, which is the whole reason the root
    had to become a key: a store mounted at ``ref`` has to be able to answer
    for the document *at* ``ref``, and that position is its own empty key.

    Matching is by segment, not by character: ``ref`` does not contain
    ``reference``, however much the two strings look alike. That is the same
    trap :func:`subtree_range` exists to avoid, and getting it wrong here would
    route a key to a store that has never heard of it.

    >>> strip_prefix("ref", "ref/a"), strip_prefix("ref", "ref")
    ('a', '')
    >>> strip_prefix("ref", "reference/a"), strip_prefix(ROOT, "a")
    (None, 'a')
    """
    if not prefix:
        return key
    if key == prefix:
        return ROOT
    if key.startswith(prefix + DELIMITER):
        return key[len(prefix) + 1 :]
    return None


def fits(key: str) -> bool:
    """Whether ``key`` is a valid key in the joined namespace a mount table shows.

    ``MAX_SEGMENTS`` bounds each half and this bounds the pair, so a prefix and
    an inner key that each parsed can always be joined: **this cannot return
    False for a key built that way**. It is kept as the statement of that
    property, to be asserted at the join rather than assumed, since the
    alternative is a silently unnameable key -- which is what the bounds were
    halved to abolish.

    >>> fits("a/b"), fits("a/" * MAX_JOINED_SEGMENTS + "b")
    (True, False)
    >>> fits("a/" * MAX_SEGMENTS + "b")  # two full halves still join
    True
    """
    return is_valid(key, max_segments=MAX_JOINED_SEGMENTS)
