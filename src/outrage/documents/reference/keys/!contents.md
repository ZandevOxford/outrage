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
4327 4327

### outrage.keys.META_PREFIX *= '!'*
4622 4622

### outrage.keys.MIN_SEGMENT_CHAR *= '\\t'*
4951 4951

### outrage.keys.NUMERIC_RE *= re.compile('\\\\A[0-9]+\\\\Z')*
5291 5291

### outrage.keys.RESERVED_PREFIX *= '?'*
5498 5498

### outrage.keys.RESERVED_SEGMENTS *= frozenset({'?', '?last'})*
6360 6360

### outrage.keys.ROOT *= ''*
6599 6599

### outrage.keys.WILDCARD *= '?'*
6971 6971

### *exception* outrage.keys.InvalidKeyError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
7308 7308

### *class* outrage.keys.Key(key: [str](https://docs.python.org/3/library/stdtypes.html#str), doc_key: [str](https://docs.python.org/3/library/stdtypes.html#str), meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), meta_path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), parent: [str](https://docs.python.org/3/library/stdtypes.html#str), wildcard_parent: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)
7901 7901

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
8676 8676

#### doc_key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
8935 8935

#### meta_name *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
9069 9069

#### meta_path *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
9512 9512

#### parent *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
10107 10107

#### wildcard_parent *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
10463 10463

#### *property* is_metadata *: [bool](https://docs.python.org/3/library/functions.html#bool)*
10803 10803

#### *property* is_meta_value *: [bool](https://docs.python.org/3/library/functions.html#bool)*
10898 10898

#### *property* has_wildcard *: [bool](https://docs.python.org/3/library/functions.html#bool)*
11360 11360

#### *property* has_last *: [bool](https://docs.python.org/3/library/functions.html#bool)*
11456 11456

### outrage.keys.LastChild
11888 11888

### outrage.keys.ancestors(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
12614 12614

### outrage.keys.depth(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [int](https://docs.python.org/3/library/functions.html#int)
13382 13384

### outrage.keys.displayed(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
13841 13845

### outrage.keys.fits(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [bool](https://docs.python.org/3/library/functions.html#bool)
14385 14391

### outrage.keys.is_valid(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, allow_wildcard: [bool](https://docs.python.org/3/library/functions.html#bool) = False, allow_last: [bool](https://docs.python.org/3/library/functions.html#bool) = False, max_segments: [int](https://docs.python.org/3/library/functions.html#int) = MAX_SEGMENTS) → [bool](https://docs.python.org/3/library/functions.html#bool)
15146 15154

### outrage.keys.meta_range(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)]
15602 15612

### outrage.keys.meta_sort_suffix(meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
16867 16879

### outrage.keys.migrate_legacy(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
17834 17848

### outrage.keys.normalise_key(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
18352 18368

### outrage.keys.normalise_segment(segment: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
18937 18955

### outrage.keys.parse(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, allow_wildcard: [bool](https://docs.python.org/3/library/functions.html#bool) = False, allow_last: [bool](https://docs.python.org/3/library/functions.html#bool) = False, max_segments: [int](https://docs.python.org/3/library/functions.html#int) = MAX_SEGMENTS) → [Key](#outrage.keys.Key)
19487 19507

### outrage.keys.relative(key: [str](https://docs.python.org/3/library/stdtypes.html#str), scope: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Key](#outrage.keys.Key)
21133 21155

### outrage.keys.remaining_depth(budget: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None), key: [str](https://docs.python.org/3/library/stdtypes.html#str), below: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)
23027 23051

### outrage.keys.resolve_last(key: [str](https://docs.python.org/3/library/stdtypes.html#str), last_child: [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[str](https://docs.python.org/3/library/stdtypes.html#str)], [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)], \*, max_segments: [int](https://docs.python.org/3/library/functions.html#int) = MAX_SEGMENTS) → [str](https://docs.python.org/3/library/stdtypes.html#str)
24426 24452

### outrage.keys.sort_form(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
26584 26612

### outrage.keys.sort_subtree_end(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
28370 28400

### outrage.keys.strip_prefix(prefix: [str](https://docs.python.org/3/library/stdtypes.html#str), key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
29749 29781

### outrage.keys.substitute_wildcard(key: [str](https://docs.python.org/3/library/stdtypes.html#str), segment: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
30776 30810

### outrage.keys.subtree_range(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)]
31149 31185

### outrage.keys.with_prefix(prefix: [str](https://docs.python.org/3/library/stdtypes.html#str), key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
32099 32137
