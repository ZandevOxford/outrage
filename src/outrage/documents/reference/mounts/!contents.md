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
8291 8291

#### store *: Store*
8441 8441

#### read_only *: bool*
8495 8495

#### lent *: bool*
8789 8789

#### *property* kind *: str*
9330 9330

#### *property* name *: str*
9456 9456

#### *property* is_root *: bool*
9609 9609

#### inner(key: str) → str | None
9701 9701

#### outer(key: str) → str
9977 9979

### *exception* outrage.mounts.MountError(code: str, \*\*details: Any)
10904 10908

### *class* outrage.mounts.MountedStore(stores: Mapping[str, Store], \*, read_only: Collection[str] = (), lent: Collection[str] = ())
11292 11296

#### writable *: ClassVar[bool]* *= True*
12706 12710

#### backend_name *: ClassVar[str]* *= 'mounts'*
13117 13121

#### *classmethod* single(store: Store) → MountedStore
13431 13435

#### remounted(\*, mount: Mapping[str, Store] = MappingProxyType({}), read_only: Collection[str] = (), lent: Collection[str] = (), unmount: Collection[str] = ()) → MountedStore
13798 13804

#### *property* root *: Mount*
16428 16436

#### *property* read_only *: list[Mount]*
16850 16858

#### *property* multiple *: bool*
17021 17029

#### resolve(key: str | None, \*, allow_wildcard: bool = False) → Resolved
17161 17169

#### below(key: str | None) → list[Mount]
18237 18247

#### directly_below(key: str | None) → list[Mount]
18792 18804

#### segments(key: str | None, depth: int | None = None, \*, key_range: KeyRange = UNBOUNDED) → list[Segment]
19631 19645

#### children(parent: str | None) → list[Entry]
21062 21078

#### last_child(key: str | None) → str | None
21733 21751

#### shadowing() → list[Mount]
22665 22685

#### read_only_below(key: str | None = None) → list[str]
23478 23500

#### read_only_at_or_below(key: str | None = None) → list[str]
24184 24208

#### unwritable(prefixes: Sequence[str]) → list[str]
25332 25358

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
26109 26137

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
29339 29369

#### exists(key: str) → bool
31052 31084

#### level_entry(key: str) → Entry | None
31547 31581

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
32145 32181

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
33894 33932

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
35471 35511

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
36377 36419

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
38439 38483

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
40179 40225

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
42377 42425

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
43595 43645

#### close() → None
44559 44611

### *exception* outrage.mounts.ReadOnlyMountError(code: str, \*\*details: Any)
44694 44748

### *class* outrage.mounts.Resolved(mount: Mount, key: str, outer: str)
45500 45554

#### mount *: Mount*
45842 45896

#### key *: str*
45889 45943

#### outer *: str*
45998 46052

#### *property* store *: Store*
46116 46170

#### *property* read_only *: bool*
46565 46619

#### writable(action: str = 'write') → Resolved
46712 46766

### *class* outrage.mounts.Segment(mount: Mount, subtree: BoundedSubtree, key_range: KeyRange)
48255 48311

#### mount *: Mount*
49182 49238

#### subtree *: BoundedSubtree*
49229 49285

#### key_range *: KeyRange*
49303 49359

#### *property* store *: Store*
49367 49423

#### resume_from(after: str | None) → tuple[str | None, bool]
49717 49773

### *class* outrage.mounts.Spec(path: Path, type: str | None = None, extensions: str | None = None, versioning: str | None = None)
51208 51266

#### path *: Path*
52347 52405

#### type *: str | None*
52430 52488

#### extensions *: str | None*
52644 52702

#### versioning *: str | None*
52972 53030

#### opened(directory: str | PathLike[str] | None = None, \*, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True) → FileStore
53283 53341

### outrage.mounts.mount_point(prefix: str, \*, spec: str | None = None) → str
54624 54684

### outrage.mounts.open_mounts(directory: str | PathLike[str] | None, specs: Sequence[str] = (), read_only_specs: Sequence[str] = (), \*, root_mount: str | PathLike[str] | Spec | None = None, log: EventLog | None = None, attached: Mapping[str, Store] = MappingProxyType({}), versioning: bool = True) → MountedStore
55406 55468

### outrage.mounts.parse_options(value: str, \*, spec: str | None = None) → Spec
59650 59714

### outrage.mounts.parse_spec(spec: str) → tuple[str, Spec]
60965 61031

### outrage.mounts.unparse(spec: Spec) → str
62259 62327
