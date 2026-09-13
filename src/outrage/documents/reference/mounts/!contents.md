# outrage.mounts
0 0

### outrage.mounts.EXTENSIONS_OPTION *= 'extensions'*
2172 2172

### outrage.mounts.MOUNT_KIND *= 'mount'*
3169 3169

### outrage.mounts.OPTIONS *= ('type', 'extensions', 'versioning')*
3561 3561

### outrage.mounts.OPTION_ASSIGNMENT *= '='*
3907 3907

### outrage.mounts.OPTION_DELIMITER *= ','*
4170 4170

### outrage.mounts.READ_ONLY_MOUNT_KIND *= 'read-only mount'*
4946 4946

### outrage.mounts.ROOT_KIND *= 'root'*
5752 5752

### outrage.mounts.SPEC_DELIMITER *= '='*
6154 6154

### outrage.mounts.TYPE_OPTION *= 'type'*
6467 6467

### outrage.mounts.VERSIONING_OPTION *= 'versioning'*
7165 7165

### *class* outrage.mounts.Mount(prefix: str, store: Store, read_only: bool = False, lent: bool = False)
7861 7861

#### prefix *: str*
8287 8287

#### store *: Store*
8436 8436

#### read_only *: bool*
8490 8490

#### lent *: bool*
8783 8783

#### *property* kind *: str*
9323 9323

#### *property* name *: str*
9448 9448

#### *property* is_root *: bool*
9600 9600

#### inner(key: str) → str | None
9691 9691

#### outer(key: str) → str
9964 9966

### *exception* outrage.mounts.MountError(code: str, \*\*details: Any)
10889 10893

### *class* outrage.mounts.MountedStore(stores: Mapping[str, Store], \*, read_only: Collection[str] = (), lent: Collection[str] = ())
11275 11279

#### writable *: ClassVar[bool]* *= True*
12686 12690

#### backend_name *: ClassVar[str]* *= 'mounts'*
13096 13100

#### *classmethod* single(store: Store) → MountedStore
13409 13413

#### remounted(\*, mount: Mapping[str, Store] = MappingProxyType({}), read_only: Collection[str] = (), lent: Collection[str] = (), unmount: Collection[str] = ()) → MountedStore
13776 13782

#### *property* root *: Mount*
16402 16410

#### *property* read_only *: list[Mount]*
16824 16832

#### *property* multiple *: bool*
16994 17002

#### resolve(key: str | None, \*, allow_wildcard: bool = False) → Resolved
17133 17141

#### below(key: str | None) → list[Mount]
18206 18216

#### directly_below(key: str | None) → list[Mount]
18758 18770

#### segments(key: str | None, depth: int | None = None, \*, key_range: KeyRange = UNBOUNDED) → list[Segment]
19594 19608

#### children(parent: str | None) → list[Entry]
21020 21036

#### last_child(key: str | None) → str | None
21688 21706

#### shadowing() → list[Mount]
22616 22636

#### read_only_below(key: str | None = None) → list[str]
23428 23450

#### read_only_at_or_below(key: str | None = None) → list[str]
24130 24154

#### unwritable(prefixes: Sequence[str]) → list[str]
25274 25300

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
26048 26076

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
29265 29295

#### exists(key: str) → bool
30968 31000

#### level_entry(key: str) → Entry | None
31461 31495

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
32057 32093

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
33803 33841

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
35378 35418

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
36280 36322

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
38335 38379

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
40067 40113

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
42255 42303

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
43466 43516

#### close() → None
44427 44479

### *exception* outrage.mounts.ReadOnlyMountError(code: str, \*\*details: Any)
44561 44615

### *class* outrage.mounts.Resolved(mount: Mount, key: str, outer: str)
45365 45419

#### mount *: Mount*
45704 45758

#### key *: str*
45751 45805

#### outer *: str*
45859 45913

#### *property* store *: Store*
45976 46030

#### *property* read_only *: bool*
46425 46479

#### writable(action: str = 'write') → Resolved
46571 46625

### *class* outrage.mounts.Segment(mount: Mount, subtree: BoundedSubtree, key_range: KeyRange)
48113 48169

#### mount *: Mount*
49039 49095

#### subtree *: BoundedSubtree*
49086 49142

#### key_range *: KeyRange*
49160 49216

#### *property* store *: Store*
49224 49280

#### resume_from(after: str | None) → tuple[str | None, bool]
49574 49630

### *class* outrage.mounts.Spec(path: Path, type: str | None = None, extensions: str | None = None, versioning: str | None = None)
51059 51117

#### path *: Path*
52191 52249

#### type *: str | None*
52274 52332

#### extensions *: str | None*
52486 52544

#### versioning *: str | None*
52812 52870

#### opened(directory: str | PathLike[str] | None = None, \*, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True) → FileStore
53121 53179

### outrage.mounts.mount_point(prefix: str, \*, spec: str | None = None) → str
54455 54515

### outrage.mounts.open_mounts(directory: str | PathLike[str] | None, specs: Sequence[str] = (), read_only_specs: Sequence[str] = (), \*, root_mount: str | PathLike[str] | Spec | None = None, log: EventLog | None = None, attached: Mapping[str, Store] = MappingProxyType({}), versioning: bool = True) → MountedStore
55233 55295

### outrage.mounts.parse_options(value: str, \*, spec: str | None = None) → Spec
59466 59530

### outrage.mounts.parse_spec(spec: str) → tuple[str, Spec]
60778 60844

### outrage.mounts.unparse(spec: Spec) → str
62069 62137
