# outrage.mounts
0 0 1

### outrage.mounts.EXTENSIONS_OPTION *= 'extensions'*
2172 2172 41

### outrage.mounts.LOCK_OPTION *= 'lock'*
3169 3169 59

### outrage.mounts.MOUNT_KIND *= 'mount'*
3989 3989 73

### outrage.mounts.OPTIONS *= ('type', 'extensions', 'versioning', 'lock')*
4381 4381 81

### outrage.mounts.OPTION_ASSIGNMENT *= '='*
4735 4735 88

### outrage.mounts.OPTION_DELIMITER *= ','*
4998 4998 94

### outrage.mounts.READ_ONLY_MOUNT_KIND *= 'read-only mount'*
5774 5774 108

### outrage.mounts.ROOT_KIND *= 'root'*
6580 6580 123

### outrage.mounts.SPEC_DELIMITER *= '='*
6982 6982 131

### outrage.mounts.TYPE_OPTION *= 'type'*
7295 7295 138

### outrage.mounts.VERSIONING_OPTION *= 'versioning'*
7993 7993 151

### *class* outrage.mounts.Mount(prefix: str, store: Store, read_only: bool = False, lent: bool = False, builtin: bool = False)
8689 8689 163

#### prefix *: str*
9200 9200 169

#### store *: Store*
9350 9350 173

#### read_only *: bool*
9404 9404 175

#### lent *: bool*
9698 9698 183

#### builtin *: bool*
10239 10239 194

#### *property* kind *: str*
10565 10565 202

#### *property* name *: str*
10691 10691 206

#### *property* is_root *: bool*
10844 10844 210

#### inner(key: str) → str | None
10936 10936 212

#### outer(key: str) → str
11212 11214 216

### *exception* outrage.mounts.MountError(code: str, \*\*details: Any)
12139 12143 234

### *class* outrage.mounts.MountedStore(stores: Mapping[str, Store], \*, read_only: Collection[str] = (), lent: Collection[str] = (), builtin: Collection[str] = ())
12527 12531 240

#### writable *: ClassVar[bool]* *= True*
14113 14117 258

#### backend_name *: ClassVar[str]* *= 'mounts'*
14524 14528 265

#### *classmethod* single(store: Store) → MountedStore
14838 14842 270

#### remounted(\*, mount: Mapping[str, Store] = MappingProxyType({}), read_only: Collection[str] = (), lent: Collection[str] = (), builtin: Collection[str] = (), unmount: Collection[str] = ()) → MountedStore
15205 15211 278

#### *property* root *: Mount*
18007 18015 314

#### *property* read_only *: list[Mount]*
18429 18437 323

#### *property* multiple *: bool*
18600 18608 327

#### resolve(key: str | None, \*, allow_wildcard: bool = False) → Resolved
18740 18748 331

#### below(key: str | None) → list[Mount]
19816 19826 348

#### directly_below(key: str | None) → list[Mount]
20371 20383 357

#### segments(key: str | None, depth: int | None = None, \*, key_range: KeyRange = UNBOUNDED) → list[Segment]
21210 21224 372

#### children(parent: str | None) → list[Entry]
22641 22657 393

#### last_child(key: str | None) → str | None
23312 23330 404

#### shadowing() → list[Mount]
24244 24264 419

#### read_only_below(key: str | None = None) → list[str]
25057 25079 435

#### read_only_at_or_below(key: str | None = None) → list[str]
25763 25787 445

#### unwritable(prefixes: Sequence[str]) → list[str]
26911 26937 461

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
27688 27716 472

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
30918 30948 518

#### exists(key: str) → bool
33053 33085 540

#### level_entry(key: str) → Entry | None
33548 33582 551

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
34146 34182 560

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
35895 35933 590

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
37472 37512 614

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
38378 38420 628

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
40440 40484 658

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
42180 42226 678

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
44378 44426 704

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
45596 45646 716

#### close() → None
47348 47400 739

### *exception* outrage.mounts.ReadOnlyMountError(code: str, \*\*details: Any)
47483 47537 743

### *class* outrage.mounts.Resolved(mount: Mount, key: str, outer: str)
48289 48343 757

#### mount *: Mount*
48631 48685 763

#### key *: str*
48678 48732 765

#### outer *: str*
48787 48841 769

#### *property* store *: Store*
48905 48959 773

#### *property* read_only *: bool*
49354 49408 783

#### writable(action: str = 'write') → Resolved
49501 49555 787

### *class* outrage.mounts.Segment(mount: Mount, subtree: BoundedSubtree, key_range: KeyRange)
51044 51100 816

#### mount *: Mount*
51971 52027 832

#### subtree *: BoundedSubtree*
52018 52074 834

#### key_range *: KeyRange*
52092 52148 836

#### *property* store *: Store*
52156 52212 838

#### resume_from(after: str | None) → tuple[str | None, bool]
52506 52562 847

### *class* outrage.mounts.Spec(path: Path, type: str | None = None, extensions: str | None = None, versioning: str | None = None, lock: str | None = None)
53997 54055 871

#### path *: Path*
55275 55333 886

#### type *: str | None*
55358 55416 888

#### extensions *: str | None*
55572 55630 892

#### versioning *: str | None*
55900 55958 898

#### lock *: str | None*
56211 56269 903

#### opened(directory: str | PathLike[str] | None = None, \*, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True) → FileStore
56495 56553 908

### outrage.mounts.mount_point(prefix: str, \*, spec: str | None = None) → str
57836 57896 923

### outrage.mounts.open_mounts(directory: str | PathLike[str] | None, specs: Sequence[str] = (), read_only_specs: Sequence[str] = (), \*, root_mount: str | PathLike[str] | Spec | None = None, log: EventLog | None = None, attached: Mapping[str, Store] = MappingProxyType({}), owned: Mapping[str, Store] = MappingProxyType({}), builtin: Collection[str] = (), versioning: bool = True, on_open_error: Callable[[str, Spec, bool, OutrageError], None] | None = None) → MountedStore
58618 58680 934

### outrage.mounts.parse_options(value: str, \*, spec: str | None = None) → Spec
65188 65252 1010

### outrage.mounts.parse_spec(spec: str) → tuple[str, Spec]
66503 66569 1032

### outrage.mounts.unparse(spec: Spec) → str
67797 67865 1053
