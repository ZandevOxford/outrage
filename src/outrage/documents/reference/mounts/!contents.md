# outrage.mounts
0 0 1

### outrage.mounts.EXTENSIONS_OPTION *= 'extensions'*
2172 2172 41

### outrage.mounts.LOCK_OPTION *= 'lock'*
3169 3169 59

### outrage.mounts.MOUNT_KIND *= 'mount'*
3989 3989 73

### outrage.mounts.OPTIONS *= ('type', 'extensions', 'versioning', 'lock', 'service')*
4381 4381 81

### outrage.mounts.OPTION_ASSIGNMENT *= '='*
4746 4746 88

### outrage.mounts.OPTION_DELIMITER *= ','*
5009 5009 94

### outrage.mounts.READ_ONLY_MOUNT_KIND *= 'read-only mount'*
5785 5785 108

### outrage.mounts.ROOT_KIND *= 'root'*
6591 6591 123

### outrage.mounts.SERVICE_OPTION *= 'service'*
6993 6993 131

### outrage.mounts.SPEC_DELIMITER *= '='*
8012 8012 150

### outrage.mounts.TYPE_OPTION *= 'type'*
8325 8325 157

### outrage.mounts.VERSIONING_OPTION *= 'versioning'*
9023 9023 170

### *class* outrage.mounts.Mount(prefix: str, store: Store, read_only: bool = False, lent: bool = False, builtin: bool = False)
9719 9719 182

#### prefix *: str*
10230 10230 188

#### store *: Store*
10380 10380 192

#### read_only *: bool*
10434 10434 194

#### lent *: bool*
10728 10728 202

#### builtin *: bool*
11269 11269 213

#### *property* kind *: str*
11595 11595 221

#### *property* name *: str*
11721 11721 225

#### *property* is_root *: bool*
11874 11874 229

#### inner(key: str) → str | None
11966 11966 231

#### outer(key: str) → str
12242 12244 235

### *exception* outrage.mounts.MountError(code: str, \*\*details: Any)
13169 13173 253

### *class* outrage.mounts.MountedStore(stores: Mapping[str, Store], \*, read_only: Collection[str] = (), lent: Collection[str] = (), builtin: Collection[str] = ())
13557 13561 259

#### writable *: ClassVar[bool]* *= True*
15143 15147 277

#### backend_name *: ClassVar[str]* *= 'mounts'*
15554 15558 284

#### *classmethod* single(store: Store) → MountedStore
15868 15872 289

#### remounted(\*, mount: Mapping[str, Store] = MappingProxyType({}), read_only: Collection[str] = (), lent: Collection[str] = (), builtin: Collection[str] = (), unmount: Collection[str] = ()) → MountedStore
16235 16241 297

#### *property* root *: Mount*
19037 19045 333

#### *property* read_only *: list[Mount]*
19459 19467 342

#### *property* multiple *: bool*
19630 19638 346

#### resolve(key: str | None, \*, allow_wildcard: bool = False) → Resolved
19770 19778 350

#### below(key: str | None) → list[Mount]
20846 20856 367

#### directly_below(key: str | None) → list[Mount]
21401 21413 376

#### segments(key: str | None, depth: int | None = None, \*, key_range: KeyRange = UNBOUNDED) → list[Segment]
22240 22254 391

#### children(parent: str | None) → list[Entry]
23671 23687 412

#### last_child(key: str | None) → str | None
24342 24360 423

#### shadowing() → list[Mount]
25274 25294 438

#### read_only_below(key: str | None = None) → list[str]
26087 26109 454

#### read_only_at_or_below(key: str | None = None) → list[str]
26793 26817 464

#### unwritable(prefixes: Sequence[str]) → list[str]
27941 27967 480

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
28718 28746 491

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
31948 31978 537

#### exists(key: str) → bool
34083 34115 559

#### level_entry(key: str) → Entry | None
34578 34612 570

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
35176 35212 579

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
36925 36963 609

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
38502 38542 633

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
39408 39450 647

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
41470 41514 677

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
43210 43256 697

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
45408 45456 723

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
46626 46676 735

#### close() → None
48378 48430 758

### *exception* outrage.mounts.ReadOnlyMountError(code: str, \*\*details: Any)
48513 48567 762

### *class* outrage.mounts.Resolved(mount: Mount, key: str, outer: str)
49319 49373 776

#### mount *: Mount*
49661 49715 782

#### key *: str*
49708 49762 784

#### outer *: str*
49817 49871 788

#### *property* store *: Store*
49935 49989 792

#### *property* read_only *: bool*
50384 50438 802

#### writable(action: str = 'write') → Resolved
50531 50585 806

### *class* outrage.mounts.Segment(mount: Mount, subtree: BoundedSubtree, key_range: KeyRange)
52074 52130 835

#### mount *: Mount*
53001 53057 851

#### subtree *: BoundedSubtree*
53048 53104 853

#### key_range *: KeyRange*
53122 53178 855

#### *property* store *: Store*
53186 53242 857

#### resume_from(after: str | None) → tuple[str | None, bool]
53536 53592 866

### *class* outrage.mounts.Spec(path: Path | None, type: str | None = None, extensions: str | None = None, versioning: str | None = None, lock: str | None = None, service: str | None = None)
55027 55085 890

#### path *: Path | None*
56667 56725 908

#### type *: str | None*
56935 56993 913

#### extensions *: str | None*
57149 57207 917

#### versioning *: str | None*
57477 57535 923

#### lock *: str | None*
57788 57846 928

#### service *: str | None*
58072 58130 933

#### opened(directory: str | PathLike[str] | None = None, \*, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True) → FileStore
58376 58434 938

### outrage.mounts.mount_point(prefix: str, \*, spec: str | None = None) → str
60365 60425 963

### outrage.mounts.open_mounts(directory: str | PathLike[str] | None, specs: Sequence[str] = (), read_only_specs: Sequence[str] = (), \*, root_mount: str | PathLike[str] | Spec | None = None, log: EventLog | None = None, attached: Mapping[str, Store] = MappingProxyType({}), owned: Mapping[str, Store] = MappingProxyType({}), builtin: Collection[str] = (), versioning: bool = True, on_open_error: Callable[[str, Spec, bool, OutrageError], None] | None = None) → MountedStore
61147 61209 974

### outrage.mounts.parse_options(value: str, \*, spec: str | None = None) → Spec
67717 67781 1050

### outrage.mounts.parse_spec(spec: str) → tuple[str, Spec]
69523 69589 1080

### outrage.mounts.unparse(spec: Spec) → str
70817 70885 1101
