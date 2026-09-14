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
7843 7843

#### key *: str*
8628 8628

#### doc_key *: str*
8888 8888

#### meta_name *: str | None*
9023 9023

#### meta_path *: str | None*
9468 9468

#### parent *: str*
10065 10065

#### wildcard_parent *: str | None*
10422 10422

#### *property* is_metadata *: bool*
10764 10764

#### *property* is_meta_value *: bool*
10860 10860

#### *property* has_wildcard *: bool*
11323 11323

#### *property* has_last *: bool*
11420 11420

### outrage.keys.LastChild
11853 11853

### outrage.keys.ancestors(key: str) → list[str]
12582 12582

### outrage.keys.depth(key: str) → int
13353 13355

### outrage.keys.displayed(key: str) → str
13814 13818

### outrage.keys.fits(key: str) → bool
14360 14366

### outrage.keys.is_valid(key: str, \*, allow_wildcard: bool = False, allow_last: bool = False, max_segments: int = MAX_SEGMENTS) → bool
15123 15131

### outrage.keys.meta_range(key: str) → tuple[str, str]
15584 15594

### outrage.keys.meta_sort_suffix(meta_name: str) → str
16853 16865

### outrage.keys.migrate_legacy(key: str) → str
17822 17836

### outrage.keys.normalise_key(key: str) → str
18342 18358

### outrage.keys.normalise_segment(segment: str) → str
18929 18947

### outrage.keys.parse(key: str, \*, allow_wildcard: bool = False, allow_last: bool = False, max_segments: int = MAX_SEGMENTS) → Key
19481 19501

### outrage.keys.relative(key: str, scope: str) → Key
21131 21153

### outrage.keys.remaining_depth(budget: int | None, key: str, below: str) → int | None
23027 23051

### outrage.keys.resolve_last(key: str, last_child: Callable[[str], str | None], \*, max_segments: int = MAX_SEGMENTS) → str
24386 24412

### outrage.keys.sort_form(key: str) → str
26550 26578

### outrage.keys.sort_subtree_end(key: str) → str
28338 28368

### outrage.keys.strip_prefix(prefix: str, key: str) → str | None
29719 29751

### outrage.keys.substitute_wildcard(key: str, segment: str) → str
30750 30784

### outrage.keys.subtree_range(key: str) → tuple[str, str]
31126 31162

### outrage.keys.with_prefix(prefix: str, key: str) → str
32080 32118
