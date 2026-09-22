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

### outrage.mounts.UNAVAILABLE_MOUNT_KIND *= 'unavailable mount'*
9023 9023 170

### outrage.mounts.VERSIONING_OPTION *= 'versioning'*
9333 9333 177

### *class* outrage.mounts.Mount(prefix: str, store: Store, read_only: bool = False, lent: bool = False, builtin: bool = False)
10029 10029 189

#### prefix *: str*
10540 10540 195

#### store *: Store*
10690 10690 199

#### read_only *: bool*
10744 10744 201

#### lent *: bool*
11038 11038 209

#### builtin *: bool*
11579 11579 220

#### *property* kind *: str*
11905 11905 228

#### *property* unavailable *: bool*
12031 12031 232

#### *property* name *: str*
12198 12198 236

#### *property* is_root *: bool*
12351 12351 240

#### inner(key: str) → str | None
12443 12443 242

#### outer(key: str) → str
12719 12721 246

### *exception* outrage.mounts.MountError(code: str, \*\*details: Any)
13646 13650 264

### *exception* outrage.mounts.MountUnavailableError(code: str, \*\*details: Any)
14034 14038 270

### *class* outrage.mounts.MountedStore(stores: Mapping[str, Store], \*, read_only: Collection[str] = (), lent: Collection[str] = (), builtin: Collection[str] = ())
14688 14692 281

#### writable *: ClassVar[bool]* *= True*
16274 16278 299

#### backend_name *: ClassVar[str]* *= 'mounts'*
16685 16689 306

#### *classmethod* single(store: Store) → MountedStore
16999 17003 311

#### remounted(\*, mount: Mapping[str, Store] = MappingProxyType({}), read_only: Collection[str] = (), lent: Collection[str] = (), builtin: Collection[str] = (), unmount: Collection[str] = ()) → MountedStore
17366 17372 319

#### *property* root *: Mount*
20168 20176 355

#### *property* read_only *: list[Mount]*
20590 20598 364

#### *property* multiple *: bool*
20761 20769 368

#### resolve(key: str | None, \*, allow_wildcard: bool = False) → Resolved
20901 20909 372

#### below(key: str | None) → list[Mount]
21977 21987 389

#### directly_below(key: str | None) → list[Mount]
22532 22544 398

#### segments(key: str | None, depth: int | None = None, \*, key_range: KeyRange = UNBOUNDED) → list[Segment]
23371 23385 413

#### children(parent: str | None) → list[Entry]
24802 24818 434

#### last_child(key: str | None) → str | None
25473 25491 445

#### shadowing() → list[Mount]
26405 26425 460

#### unavailable_at_or_below(key: str | None = None) → list[Mount]
27218 27240 476

#### read_only_below(key: str | None = None) → list[str]
27789 27813 484

#### read_only_at_or_below(key: str | None = None) → list[str]
28495 28521 494

#### unwritable(prefixes: Sequence[str]) → list[str]
29643 29671 510

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
30420 30450 521

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
33650 33682 567

#### exists(key: str) → bool
35785 35819 589

#### level_entry(key: str) → Entry | None
36280 36316 600

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
36878 36916 609

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
38627 38667 639

#### now(key: str = keys.ROOT, \*, key_range: KeyRange = UNBOUNDED) → str
40204 40246 663

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
41037 41081 678

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
41943 41989 692

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
44005 44053 722

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
45745 45795 742

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
47943 47995 768

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
49161 49215 780

#### close() → None
50913 50969 803

### *exception* outrage.mounts.ReadOnlyMountError(code: str, \*\*details: Any)
51048 51106 807

### *class* outrage.mounts.Resolved(mount: Mount, key: str, outer: str)
51854 51912 821

#### mount *: Mount*
52196 52254 827

#### key *: str*
52243 52301 829

#### outer *: str*
52352 52410 833

#### *property* store *: Store*
52470 52528 837

#### *property* read_only *: bool*
52919 52977 847

#### writable(action: str = 'write') → Resolved
53066 53124 851

### *class* outrage.mounts.Segment(mount: Mount, subtree: BoundedSubtree, key_range: KeyRange)
54609 54669 880

#### mount *: Mount*
55536 55596 896

#### subtree *: BoundedSubtree*
55583 55643 898

#### key_range *: KeyRange*
55657 55717 900

#### *property* store *: Store*
55721 55781 902

#### resume_from(after: str | None) → tuple[str | None, bool]
56071 56131 911

### *class* outrage.mounts.Spec(path: Path | None, type: str | None = None, extensions: str | None = None, versioning: str | None = None, lock: str | None = None, service: str | None = None)
57562 57624 935

#### path *: Path | None*
59202 59264 953

#### type *: str | None*
59470 59532 958

#### extensions *: str | None*
59684 59746 962

#### versioning *: str | None*
60012 60074 968

#### lock *: str | None*
60323 60385 973

#### service *: str | None*
60607 60669 978

#### opened(directory: str | PathLike[str] | None = None, \*, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True, create: bool = True) → FileStore
60911 60973 983

### *class* outrage.mounts.UnavailableStore(error: OutrageError, \*, mount_point: str, requested_read_only: bool = False)
63157 63221 1011

#### writable *: ClassVar[bool]* *= True*
64318 64382 1032

#### backend_name *: ClassVar[str]* *= 'unavailable'*
64762 64826 1039

#### error
65137 65201 1045

#### requested_read_only
65190 65254 1049

#### *property* reason *: dict[str, Any]*
65344 65408 1054

#### refuse(key: str | None = keys.ROOT) → NoReturn
65658 65722 1058

#### store_document(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
66150 66216 1066

#### delete(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
68768 68836 1112

#### descendant_count(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
71321 71391 1155

#### subtree_totals(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
73084 73156 1185

#### latest_change(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
75842 75916 1231

#### exists(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
77934 78010 1265

#### level_entry(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
78600 78678 1276

#### retrieve_document(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
79619 79699 1291

#### list_keys(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
80985 81067 1313

#### last_child(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
83605 83689 1360

#### get_documents(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
85442 85528 1390

#### find_documents(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
86880 86968 1416

#### missing_meta_stats(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
87703 87793 1429

#### keys_missing_meta(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
89506 89598 1458

#### copy_from(\*\_args: Any, \*\*\_kwargs: Any) → Any
90257 90351 1470

#### close() → None
94236 94332 1537

### outrage.mounts.mount_point(prefix: str, \*, spec: str | None = None) → str
94356 94454 1541

### outrage.mounts.open_mounts(directory: str | PathLike[str] | None, specs: Sequence[str] = (), read_only_specs: Sequence[str] = (), \*, root_mount: str | PathLike[str] | Spec | None = None, log: EventLog | None = None, attached: Mapping[str, Store] = MappingProxyType({}), owned: Mapping[str, Store] = MappingProxyType({}), builtin: Collection[str] = (), versioning: bool = True, on_open_error: Callable[[str, Spec, bool, OutrageError], None] | None = None) → MountedStore
95138 95238 1552

### outrage.mounts.parse_options(value: str, \*, spec: str | None = None) → Spec
101708 101810 1628

### outrage.mounts.parse_spec(spec: str) → tuple[str, Spec]
103514 103618 1658

### outrage.mounts.refuse_missing_read_only(directory: Path, prefix: str, file: str | PathLike[str] | None, backend: str | None) → None
104808 104914 1679

### outrage.mounts.refuse_unavailable(opened: Store, key: str | None, action: str) → None
106104 106212 1693

### outrage.mounts.unparse(spec: Spec) → str
106992 107102 1706
