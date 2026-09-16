# outrage.mounts
0 0

### outrage.mounts.EXTENSIONS_OPTION *= 'extensions'*
2172 2172

### outrage.mounts.LOCK_OPTION *= 'lock'*
3169 3169

### outrage.mounts.MOUNT_KIND *= 'mount'*
3989 3989

### outrage.mounts.OPTIONS *= ('type', 'extensions', 'versioning', 'lock')*
4381 4381

### outrage.mounts.OPTION_ASSIGNMENT *= '='*
4735 4735

### outrage.mounts.OPTION_DELIMITER *= ','*
4998 4998

### outrage.mounts.READ_ONLY_MOUNT_KIND *= 'read-only mount'*
5774 5774

### outrage.mounts.ROOT_KIND *= 'root'*
6580 6580

### outrage.mounts.SPEC_DELIMITER *= '='*
6982 6982

### outrage.mounts.TYPE_OPTION *= 'type'*
7295 7295

### outrage.mounts.VERSIONING_OPTION *= 'versioning'*
7993 7993

### *class* outrage.mounts.Mount(prefix: str, store: Store, read_only: bool = False, lent: bool = False, builtin: bool = False)
8689 8689

#### prefix *: str*
9200 9200

#### store *: Store*
9350 9350

#### read_only *: bool*
9404 9404

#### lent *: bool*
9698 9698

#### builtin *: bool*
10239 10239

#### *property* kind *: str*
10565 10565

#### *property* name *: str*
10691 10691

#### *property* is_root *: bool*
10844 10844

#### inner(key: str) → str | None
10936 10936

#### outer(key: str) → str
11212 11214

### *exception* outrage.mounts.MountError(code: str, \*\*details: Any)
12139 12143

### *class* outrage.mounts.MountedStore(stores: Mapping[str, Store], \*, read_only: Collection[str] = (), lent: Collection[str] = (), builtin: Collection[str] = ())
12527 12531

#### writable *: ClassVar[bool]* *= True*
14113 14117

#### backend_name *: ClassVar[str]* *= 'mounts'*
14524 14528

#### *classmethod* single(store: Store) → MountedStore
14838 14842

#### remounted(\*, mount: Mapping[str, Store] = MappingProxyType({}), read_only: Collection[str] = (), lent: Collection[str] = (), builtin: Collection[str] = (), unmount: Collection[str] = ()) → MountedStore
15205 15211

#### *property* root *: Mount*
18007 18015

#### *property* read_only *: list[Mount]*
18429 18437

#### *property* multiple *: bool*
18600 18608

#### resolve(key: str | None, \*, allow_wildcard: bool = False) → Resolved
18740 18748

#### below(key: str | None) → list[Mount]
19816 19826

#### directly_below(key: str | None) → list[Mount]
20371 20383

#### segments(key: str | None, depth: int | None = None, \*, key_range: KeyRange = UNBOUNDED) → list[Segment]
21210 21224

#### children(parent: str | None) → list[Entry]
22641 22657

#### last_child(key: str | None) → str | None
23312 23330

#### shadowing() → list[Mount]
24244 24264

#### read_only_below(key: str | None = None) → list[str]
25057 25079

#### read_only_at_or_below(key: str | None = None) → list[str]
25763 25787

#### unwritable(prefixes: Sequence[str]) → list[str]
26911 26937

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
27688 27716

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
30918 30948

#### exists(key: str) → bool
32631 32663

#### level_entry(key: str) → Entry | None
33126 33160

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
33724 33760

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
35473 35511

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
37050 37090

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
37956 37998

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
40018 40062

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
41758 41804

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
43956 44004

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
45174 45224

#### close() → None
46138 46190

### *exception* outrage.mounts.ReadOnlyMountError(code: str, \*\*details: Any)
46273 46327

### *class* outrage.mounts.Resolved(mount: Mount, key: str, outer: str)
47079 47133

#### mount *: Mount*
47421 47475

#### key *: str*
47468 47522

#### outer *: str*
47577 47631

#### *property* store *: Store*
47695 47749

#### *property* read_only *: bool*
48144 48198

#### writable(action: str = 'write') → Resolved
48291 48345

### *class* outrage.mounts.Segment(mount: Mount, subtree: BoundedSubtree, key_range: KeyRange)
49834 49890

#### mount *: Mount*
50761 50817

#### subtree *: BoundedSubtree*
50808 50864

#### key_range *: KeyRange*
50882 50938

#### *property* store *: Store*
50946 51002

#### resume_from(after: str | None) → tuple[str | None, bool]
51296 51352

### *class* outrage.mounts.Spec(path: Path, type: str | None = None, extensions: str | None = None, versioning: str | None = None, lock: str | None = None)
52787 52845

#### path *: Path*
54065 54123

#### type *: str | None*
54148 54206

#### extensions *: str | None*
54362 54420

#### versioning *: str | None*
54690 54748

#### lock *: str | None*
55001 55059

#### opened(directory: str | PathLike[str] | None = None, \*, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True) → FileStore
55285 55343

### outrage.mounts.mount_point(prefix: str, \*, spec: str | None = None) → str
56626 56686

### outrage.mounts.open_mounts(directory: str | PathLike[str] | None, specs: Sequence[str] = (), read_only_specs: Sequence[str] = (), \*, root_mount: str | PathLike[str] | Spec | None = None, log: EventLog | None = None, attached: Mapping[str, Store] = MappingProxyType({}), owned: Mapping[str, Store] = MappingProxyType({}), builtin: Collection[str] = (), versioning: bool = True, on_open_error: Callable[[str, Spec, bool, OutrageError], None] | None = None) → MountedStore
57408 57470

### outrage.mounts.parse_options(value: str, \*, spec: str | None = None) → Spec
63978 64042

### outrage.mounts.parse_spec(spec: str) → tuple[str, Spec]
65293 65359

### outrage.mounts.unparse(spec: Spec) → str
66587 66655
