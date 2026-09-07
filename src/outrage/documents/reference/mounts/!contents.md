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

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
23461 23487

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
26535 26563

#### exists(key: str) → bool
28238 28268

#### level_entry(key: str) → Entry | None
28731 28763

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
29327 29361

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
31073 31109

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
31975 32013

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None) → Page[Entry]
34030 34070

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
34863 34905

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
37051 37095

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
38262 38308

#### close() → None
39223 39271

### *exception* outrage.mounts.ReadOnlyMountError(code: str, \*\*details: Any)
39357 39407

### *class* outrage.mounts.Resolved(mount: Mount, key: str, outer: str)
40161 40211

#### mount *: Mount*
40500 40550

#### key *: str*
40547 40597

#### outer *: str*
40655 40705

#### *property* store *: Store*
40772 40822

#### *property* read_only *: bool*
41221 41271

#### writable(action: str = 'write') → Resolved
41367 41417

### *class* outrage.mounts.Segment(mount: Mount, subtree: BoundedSubtree, key_range: KeyRange)
42909 42961

#### mount *: Mount*
43835 43887

#### subtree *: BoundedSubtree*
43882 43934

#### key_range *: KeyRange*
43956 44008

#### *property* store *: Store*
44020 44072

#### resume_from(after: str | None) → tuple[str | None, bool]
44370 44422

### *class* outrage.mounts.Spec(path: Path, type: str | None = None, extensions: str | None = None)
45855 45909

#### path *: Path*
46844 46898

#### type *: str | None*
46927 46981

#### extensions *: str | None*
47139 47193

#### opened(directory: str | PathLike[str] | None = None, \*, log: EventLog | None = None, mount_point: str | None = None) → FileStore
47465 47519

### outrage.mounts.mount_point(prefix: str, \*, spec: str | None = None) → str
48646 48702

### outrage.mounts.open_mounts(directory: str | PathLike[str] | None, specs: Sequence[str] = (), read_only_specs: Sequence[str] = (), \*, root_mount: str | PathLike[str] | Spec | None = None, log: EventLog | None = None, attached: Mapping[str, Store] = MappingProxyType({})) → MountedStore
49424 49482

### outrage.mounts.parse_options(value: str, \*, spec: str | None = None) → Spec
53415 53475

### outrage.mounts.parse_spec(spec: str) → tuple[str, Spec]
54727 54789

### outrage.mounts.unparse(spec: Spec) → str
56018 56082
