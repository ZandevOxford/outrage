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

### *class* outrage.mounts.Mount(prefix: str, store: Store, read_only: bool = False, lent: bool = False)
7151 7151

#### prefix *: str*
7577 7577

#### store *: Store*
7726 7726

#### read_only *: bool*
7780 7780

#### lent *: bool*
8073 8073

#### *property* kind *: str*
8613 8613

#### *property* name *: str*
8738 8738

#### *property* is_root *: bool*
8890 8890

#### inner(key: str) → str | None
8981 8981

#### outer(key: str) → str
9254 9256

### *exception* outrage.mounts.MountError(code: str, \*\*details: Any)
10179 10183

### *class* outrage.mounts.MountedStore(stores: Mapping[str, Store], \*, read_only: Collection[str] = (), lent: Collection[str] = ())
10565 10569

#### writable *: ClassVar[bool]* *= True*
11976 11980

#### backend_name *: ClassVar[str]* *= 'mounts'*
12386 12390

#### *classmethod* single(store: Store) → MountedStore
12699 12703

#### remounted(\*, mount: Mapping[str, Store] = MappingProxyType({}), read_only: Collection[str] = (), lent: Collection[str] = (), unmount: Collection[str] = ()) → MountedStore
13066 13072

#### *property* root *: Mount*
15692 15700

#### *property* read_only *: list[Mount]*
16114 16122

#### *property* multiple *: bool*
16284 16292

#### resolve(key: str | None, \*, allow_wildcard: bool = False) → Resolved
16423 16431

#### below(key: str | None) → list[Mount]
17496 17506

#### directly_below(key: str | None) → list[Mount]
18048 18060

#### segments(key: str | None, depth: int | None = None, \*, key_range: KeyRange = UNBOUNDED) → list[Segment]
18884 18898

#### children(parent: str | None) → list[Entry]
20310 20326

#### last_child(key: str | None) → str | None
20978 20996

#### shadowing() → list[Mount]
21906 21926

#### read_only_below(key: str | None = None) → list[str]
22718 22740

#### read_only_at_or_below(key: str | None = None) → list[str]
23420 23444

#### unwritable(prefixes: Sequence[str]) → list[str]
24564 24590

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
25338 25366

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
28555 28585

#### exists(key: str) → bool
30258 30290

#### level_entry(key: str) → Entry | None
30751 30785

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
31347 31383

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
33093 33131

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
34668 34708

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
35570 35612

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
37625 37669

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
39357 39403

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
41545 41593

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
42756 42806

#### close() → None
43717 43769

### *exception* outrage.mounts.ReadOnlyMountError(code: str, \*\*details: Any)
43851 43905

### *class* outrage.mounts.Resolved(mount: Mount, key: str, outer: str)
44655 44709

#### mount *: Mount*
44994 45048

#### key *: str*
45041 45095

#### outer *: str*
45149 45203

#### *property* store *: Store*
45266 45320

#### *property* read_only *: bool*
45715 45769

#### writable(action: str = 'write') → Resolved
45861 45915

### *class* outrage.mounts.Segment(mount: Mount, subtree: BoundedSubtree, key_range: KeyRange)
47403 47459

#### mount *: Mount*
48329 48385

#### subtree *: BoundedSubtree*
48376 48432

#### key_range *: KeyRange*
48450 48506

#### *property* store *: Store*
48514 48570

#### resume_from(after: str | None) → tuple[str | None, bool]
48864 48920

### *class* outrage.mounts.Spec(path: Path, type: str | None = None, extensions: str | None = None)
50349 50407

#### path *: Path*
51338 51396

#### type *: str | None*
51421 51479

#### extensions *: str | None*
51633 51691

#### opened(directory: str | PathLike[str] | None = None, \*, log: EventLog | None = None, mount_point: str | None = None) → FileStore
51959 52017

### outrage.mounts.mount_point(prefix: str, \*, spec: str | None = None) → str
53140 53200

### outrage.mounts.open_mounts(directory: str | PathLike[str] | None, specs: Sequence[str] = (), read_only_specs: Sequence[str] = (), \*, root_mount: str | PathLike[str] | Spec | None = None, log: EventLog | None = None, attached: Mapping[str, Store] = MappingProxyType({})) → MountedStore
53918 53980

### outrage.mounts.parse_options(value: str, \*, spec: str | None = None) → Spec
57909 57973

### outrage.mounts.parse_spec(spec: str) → tuple[str, Spec]
59221 59287

### outrage.mounts.unparse(spec: Spec) → str
60512 60580
