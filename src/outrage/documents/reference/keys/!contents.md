# outrage.keys
0 0 1

### outrage.keys.DELIMITER *= '/'*
2562 2562 48

### outrage.keys.LAST *= '?last'*
2673 2673 52

### outrage.keys.LEGACY_META *= ':'*
3196 3196 61

### outrage.keys.MAX_JOINED_SEGMENTS *= 128*
3450 3450 67

### outrage.keys.MAX_SEGMENTS *= 64*
3724 3724 73

### outrage.keys.MAX_SEGMENT_CHARS *= 1024*
4409 4409 86

### outrage.keys.META_PREFIX *= '!'*
4704 4704 93

### outrage.keys.MIN_SEGMENT_CHAR *= '\\t'*
5033 5033 100

### outrage.keys.NUMERIC_RE *= re.compile('\\\\A[0-9]+\\\\Z')*
5373 5373 107

### outrage.keys.RESERVED_PREFIX *= '?'*
5580 5580 112

### outrage.keys.RESERVED_SEGMENTS *= frozenset({'?', '?last'})*
6455 6455 128

### outrage.keys.ROOT *= ''*
6694 6694 134

### outrage.keys.WILDCARD *= '?'*
7066 7066 142

### *exception* outrage.keys.InvalidKeyError(code: str, \*\*details: Any)
7403 7403 149

### *class* outrage.keys.Key(key: str, doc_key: str, meta_name: str | None, meta_path: str | None, parent: str, wildcard_parent: str | None = None)
7998 7998 159

#### key *: str*
8783 8783 165

#### doc_key *: str*
9043 9043 171

#### meta_name *: str | None*
9178 9178 175

#### meta_path *: str | None*
9623 9623 182

#### parent *: str*
10220 10220 193

#### wildcard_parent *: str | None*
10577 10577 200

#### *property* is_metadata *: bool*
10919 10919 206

#### *property* is_meta_value *: bool*
11015 11015 208

#### *property* has_wildcard *: bool*
11478 11478 217

#### *property* has_last *: bool*
11575 11575 219

### outrage.keys.LastChild
12008 12008 228

### outrage.keys.ancestors(key: str) → list[str]
12737 12737 238

### outrage.keys.depth(key: str) → int
13508 13510 257

### outrage.keys.displayed(key: str) → str
13969 13973 270

### outrage.keys.fits(key: str) → bool
14515 14521 284

### outrage.keys.is_valid(key: str, \*, allow_wildcard: bool = False, allow_last: bool = False, max_segments: int = MAX_SEGMENTS) → bool
15278 15286 302

### outrage.keys.meta_range(key: str) → tuple[str, str]
15739 15749 306

### outrage.keys.meta_sort_suffix(meta_name: str) → str
17008 17020 329

### outrage.keys.migrate_legacy(key: str) → str
17977 17991 349

### outrage.keys.normalise_key(key: str) → str
18497 18513 362

### outrage.keys.normalise_segment(segment: str) → str
19084 19102 376

### outrage.keys.parse(key: str, \*, allow_wildcard: bool = False, allow_last: bool = False, max_segments: int = MAX_SEGMENTS) → Key
19636 19656 389

### outrage.keys.relative(key: str, scope: str) → Key
21286 21308 415

### outrage.keys.remaining_depth(budget: int | None, key: str, below: str) → int | None
23182 23206 455

### outrage.keys.resolve_last(key: str, last_child: Callable[[str], str | None], \*, max_segments: int = MAX_SEGMENTS) → str
24541 24567 478

### outrage.keys.sort_form(key: str) → str
26705 26733 515

### outrage.keys.sort_subtree_end(key: str) → str
28493 28523 553

### outrage.keys.strip_prefix(prefix: str, key: str) → str | None
29874 29906 582

### outrage.keys.substitute_wildcard(key: str, segment: str) → str
30905 30939 602

### outrage.keys.subtree_range(key: str) → tuple[str, str]
31281 31317 611

### outrage.keys.with_prefix(prefix: str, key: str) → str
32235 32273 626
