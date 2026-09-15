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

### *class* outrage.mounts.Mount(prefix: str, store: Store, read_only: bool = False, lent: bool = False)
8689 8689

#### prefix *: str*
9119 9119

#### store *: Store*
9269 9269

#### read_only *: bool*
9323 9323

#### lent *: bool*
9617 9617

#### *property* kind *: str*
10158 10158

#### *property* name *: str*
10284 10284

#### *property* is_root *: bool*
10437 10437

#### inner(key: str) → str | None
10529 10529

#### outer(key: str) → str
10805 10807

### *exception* outrage.mounts.MountError(code: str, \*\*details: Any)
11732 11736

### *class* outrage.mounts.MountedStore(stores: Mapping[str, Store], \*, read_only: Collection[str] = (), lent: Collection[str] = ())
12120 12124

#### writable *: ClassVar[bool]* *= True*
13534 13538

#### backend_name *: ClassVar[str]* *= 'mounts'*
13945 13949

#### *classmethod* single(store: Store) → MountedStore
14259 14263

#### remounted(\*, mount: Mapping[str, Store] = MappingProxyType({}), read_only: Collection[str] = (), lent: Collection[str] = (), unmount: Collection[str] = ()) → MountedStore
14626 14632

#### *property* root *: Mount*
17256 17264

#### *property* read_only *: list[Mount]*
17678 17686

#### *property* multiple *: bool*
17849 17857

#### resolve(key: str | None, \*, allow_wildcard: bool = False) → Resolved
17989 17997

#### below(key: str | None) → list[Mount]
19065 19075

#### directly_below(key: str | None) → list[Mount]
19620 19632

#### segments(key: str | None, depth: int | None = None, \*, key_range: KeyRange = UNBOUNDED) → list[Segment]
20459 20473

#### children(parent: str | None) → list[Entry]
21890 21906

#### last_child(key: str | None) → str | None
22561 22579

#### shadowing() → list[Mount]
23493 23513

#### read_only_below(key: str | None = None) → list[str]
24306 24328

#### read_only_at_or_below(key: str | None = None) → list[str]
25012 25036

#### unwritable(prefixes: Sequence[str]) → list[str]
26160 26186

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
26937 26965

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
30167 30197

#### exists(key: str) → bool
31880 31912

#### level_entry(key: str) → Entry | None
32375 32409

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
32973 33009

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
34722 34760

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
36299 36339

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
37205 37247

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
39267 39311

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
41007 41053

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
43205 43253

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
44423 44473

#### close() → None
45387 45439

### *exception* outrage.mounts.ReadOnlyMountError(code: str, \*\*details: Any)
45522 45576

### *class* outrage.mounts.Resolved(mount: Mount, key: str, outer: str)
46328 46382

#### mount *: Mount*
46670 46724

#### key *: str*
46717 46771

#### outer *: str*
46826 46880

#### *property* store *: Store*
46944 46998

#### *property* read_only *: bool*
47393 47447

#### writable(action: str = 'write') → Resolved
47540 47594

### *class* outrage.mounts.Segment(mount: Mount, subtree: BoundedSubtree, key_range: KeyRange)
49083 49139

#### mount *: Mount*
50010 50066

#### subtree *: BoundedSubtree*
50057 50113

#### key_range *: KeyRange*
50131 50187

#### *property* store *: Store*
50195 50251

#### resume_from(after: str | None) → tuple[str | None, bool]
50545 50601

### *class* outrage.mounts.Spec(path: Path, type: str | None = None, extensions: str | None = None, versioning: str | None = None, lock: str | None = None)
52036 52094

#### path *: Path*
53314 53372

#### type *: str | None*
53397 53455

#### extensions *: str | None*
53611 53669

#### versioning *: str | None*
53939 53997

#### lock *: str | None*
54250 54308

#### opened(directory: str | PathLike[str] | None = None, \*, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True) → FileStore
54534 54592

### outrage.mounts.mount_point(prefix: str, \*, spec: str | None = None) → str
55875 55935

### outrage.mounts.open_mounts(directory: str | PathLike[str] | None, specs: Sequence[str] = (), read_only_specs: Sequence[str] = (), \*, root_mount: str | PathLike[str] | Spec | None = None, log: EventLog | None = None, attached: Mapping[str, Store] = MappingProxyType({}), versioning: bool = True) → MountedStore
56657 56719

### outrage.mounts.parse_options(value: str, \*, spec: str | None = None) → Spec
60901 60965

### outrage.mounts.parse_spec(spec: str) → tuple[str, Spec]
62216 62282

### outrage.mounts.unparse(spec: Spec) → str
63510 63578
