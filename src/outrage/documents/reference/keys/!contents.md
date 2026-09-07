# outrage.keys
0 0

### outrage.keys.DELIMITER *= '/'*
2407 2407

### outrage.keys.LAST *= '?last'*
2518 2518

### outrage.keys.LEGACY_META *= ':'*
3041 3041

### outrage.keys.MAX_JOINED_SEGMENTS *= 128*
3295 3295

### outrage.keys.MAX_SEGMENTS *= 64*
3569 3569

### outrage.keys.MAX_SEGMENT_CHARS *= 1024*
4254 4254

### outrage.keys.META_PREFIX *= '!'*
4549 4549

### outrage.keys.MIN_SEGMENT_CHAR *= '\\t'*
4878 4878

### outrage.keys.NUMERIC_RE *= re.compile('\\\\A[0-9]+\\\\Z')*
5218 5218

### outrage.keys.RESERVED_PREFIX *= '?'*
5425 5425

### outrage.keys.RESERVED_SEGMENTS *= frozenset({'?', '?last'})*
6300 6300

### outrage.keys.ROOT *= ''*
6539 6539

### outrage.keys.WILDCARD *= '?'*
6911 6911

### *exception* outrage.keys.InvalidKeyError(code: str, \*\*details: Any)
7248 7248

### *class* outrage.keys.Key(key: str, doc_key: str, meta_name: str | None, meta_path: str | None, parent: str, wildcard_parent: str | None = None)
7841 7841

#### key *: str*
8616 8616

#### doc_key *: str*
8875 8875

#### meta_name *: str | None*
9009 9009

#### meta_path *: str | None*
9452 9452

#### parent *: str*
10047 10047

#### wildcard_parent *: str | None*
10403 10403

#### *property* is_metadata *: bool*
10743 10743

#### *property* is_meta_value *: bool*
10838 10838

#### *property* has_wildcard *: bool*
11300 11300

#### *property* has_last *: bool*
11396 11396

### outrage.keys.LastChild
11828 11828

### outrage.keys.ancestors(key: str) → list[str]
12554 12554

### outrage.keys.depth(key: str) → int
13322 13324

### outrage.keys.displayed(key: str) → str
13781 13785

### outrage.keys.fits(key: str) → bool
14325 14331

### outrage.keys.is_valid(key: str, \*, allow_wildcard: bool = False, allow_last: bool = False, max_segments: int = MAX_SEGMENTS) → bool
15086 15094

### outrage.keys.meta_range(key: str) → tuple[str, str]
15542 15552

### outrage.keys.meta_sort_suffix(meta_name: str) → str
16807 16819

### outrage.keys.migrate_legacy(key: str) → str
17774 17788

### outrage.keys.normalise_key(key: str) → str
18292 18308

### outrage.keys.normalise_segment(segment: str) → str
18877 18895

### outrage.keys.parse(key: str, \*, allow_wildcard: bool = False, allow_last: bool = False, max_segments: int = MAX_SEGMENTS) → Key
19427 19447

### outrage.keys.relative(key: str, scope: str) → Key
21073 21095

### outrage.keys.remaining_depth(budget: int | None, key: str, below: str) → int | None
22967 22991

### outrage.keys.resolve_last(key: str, last_child: Callable[[str], str | None], \*, max_segments: int = MAX_SEGMENTS) → str
24320 24346

### outrage.keys.sort_form(key: str) → str
26478 26506

### outrage.keys.sort_subtree_end(key: str) → str
28264 28294

### outrage.keys.strip_prefix(prefix: str, key: str) → str | None
29643 29675

### outrage.keys.substitute_wildcard(key: str, segment: str) → str
30670 30704

### outrage.keys.subtree_range(key: str) → tuple[str, str]
31043 31079

### outrage.keys.with_prefix(prefix: str, key: str) → str
31993 32031
