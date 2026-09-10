# outrage.mounts
0 0

### outrage.mounts.EXTENSIONS_OPTION *= 'extensions'*
2172 2172

### outrage.mounts.MOUNT_KIND *= 'mount'*
3169 3169

### outrage.mounts.OPTIONS *= ('type', 'extensions')*
3561 3561

### outrage.mounts.OPTION_ASSIGNMENT *= '='*
3893 3893

### outrage.mounts.OPTION_DELIMITER *= ','*
4156 4156

### outrage.mounts.READ_ONLY_MOUNT_KIND *= 'read-only mount'*
4932 4932

### outrage.mounts.ROOT_KIND *= 'root'*
5738 5738

### outrage.mounts.SPEC_DELIMITER *= '='*
6140 6140

### outrage.mounts.TYPE_OPTION *= 'type'*
6453 6453

### *class* outrage.mounts.Mount(prefix: str, store: Store, read_only: bool = False)
7151 7151

#### prefix *: str*
7500 7500

#### store *: Store*
7649 7649

#### read_only *: bool*
7703 7703

#### *property* kind *: str*
7996 7996

#### *property* name *: str*
8121 8121

#### *property* is_root *: bool*
8273 8273

#### inner(key: str) → str | None
8364 8364

#### outer(key: str) → str
8637 8639

### *exception* outrage.mounts.MountError(code: str, \*\*details: Any)
9562 9566

### *class* outrage.mounts.MountedStore(stores: Mapping[str, Store], \*, read_only: Collection[str] = ())
9948 9952

#### writable *: ClassVar[bool]* *= True*
11191 11195

#### backend_name *: ClassVar[str]* *= 'mounts'*
11601 11605

#### *classmethod* single(store: Store) → MountedStore
11914 11918

#### remounted(\*, mount: Mapping[str, Store] = MappingProxyType({}), read_only: Collection[str] = (), unmount: Collection[str] = ()) → MountedStore
12281 12287

#### *property* root *: Mount*
14589 14597

#### *property* read_only *: list[Mount]*
15011 15019

#### *property* multiple *: bool*
15181 15189

#### resolve(key: str | None, \*, allow_wildcard: bool = False) → Resolved
15320 15328

#### below(key: str | None) → list[Mount]
16393 16403

#### directly_below(key: str | None) → list[Mount]
16945 16957

#### segments(key: str | None, depth: int | None = None, \*, key_range: KeyRange = UNBOUNDED) → list[Segment]
17781 17795

#### children(parent: str | None) → list[Entry]
19207 19223

#### last_child(key: str | None) → str | None
19875 19893

#### shadowing() → list[Mount]
20803 20823

#### read_only_below(key: str | None = None) → list[str]
21615 21637

#### read_only_at_or_below(key: str | None = None) → list[str]
22317 22341

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
23461 23487

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
26678 26706

#### exists(key: str) → bool
28381 28411

#### level_entry(key: str) → Entry | None
28874 28906

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
29470 29504

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
31216 31252

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
32791 32829

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
33693 33733

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
35748 35790

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
37480 37524

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
39668 39714

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
40879 40927

#### close() → None
41840 41890

### *exception* outrage.mounts.ReadOnlyMountError(code: str, \*\*details: Any)
41974 42026

### *class* outrage.mounts.Resolved(mount: Mount, key: str, outer: str)
42778 42830

#### mount *: Mount*
43117 43169

#### key *: str*
43164 43216

#### outer *: str*
43272 43324

#### *property* store *: Store*
43389 43441

#### *property* read_only *: bool*
43838 43890

#### writable(action: str = 'write') → Resolved
43984 44036

### *class* outrage.mounts.Segment(mount: Mount, subtree: BoundedSubtree, key_range: KeyRange)
45526 45580

#### mount *: Mount*
46452 46506

#### subtree *: BoundedSubtree*
46499 46553

#### key_range *: KeyRange*
46573 46627

#### *property* store *: Store*
46637 46691

#### resume_from(after: str | None) → tuple[str | None, bool]
46987 47041

### *class* outrage.mounts.Spec(path: Path, type: str | None = None, extensions: str | None = None)
48472 48528

#### path *: Path*
49461 49517

#### type *: str | None*
49544 49600

#### extensions *: str | None*
49756 49812

#### opened(directory: str | PathLike[str] | None = None, \*, log: EventLog | None = None, mount_point: str | None = None) → FileStore
50082 50138

### outrage.mounts.mount_point(prefix: str, \*, spec: str | None = None) → str
51263 51321

### outrage.mounts.open_mounts(directory: str | PathLike[str] | None, specs: Sequence[str] = (), read_only_specs: Sequence[str] = (), \*, root_mount: str | PathLike[str] | Spec | None = None, log: EventLog | None = None, attached: Mapping[str, Store] = MappingProxyType({})) → MountedStore
52041 52101

### outrage.mounts.parse_options(value: str, \*, spec: str | None = None) → Spec
56032 56094

### outrage.mounts.parse_spec(spec: str) → tuple[str, Spec]
57344 57408

### outrage.mounts.unparse(spec: Spec) → str
58635 58701
