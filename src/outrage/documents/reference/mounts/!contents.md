# outrage.mounts
0 0 1

### outrage.mounts.EXTENSIONS_OPTION *= 'extensions'*
2324 2324 43

### outrage.mounts.LOCK_OPTION *= 'lock'*
3321 3321 61

### outrage.mounts.MOUNT_KIND *= 'mount'*
4141 4141 75

### outrage.mounts.OPTIONS *= ('type', 'extensions', 'versioning', 'lock', 'service')*
4533 4533 83

### outrage.mounts.OPTION_ASSIGNMENT *= '='*
4898 4898 90

### outrage.mounts.OPTION_DELIMITER *= ','*
5161 5161 96

### outrage.mounts.READ_ONLY_MOUNT_KIND *= 'read-only mount'*
5937 5937 110

### outrage.mounts.ROOT_KIND *= 'root'*
6743 6743 125

### outrage.mounts.SERVICE_OPTION *= 'service'*
7145 7145 133

### outrage.mounts.SPEC_DELIMITER *= '='*
8164 8164 152

### outrage.mounts.TYPE_OPTION *= 'type'*
8477 8477 159

### outrage.mounts.UNAVAILABLE_MOUNT_KIND *= 'unavailable mount'*
9175 9175 172

### outrage.mounts.VERSIONING_OPTION *= 'versioning'*
9485 9485 179

### *class* outrage.mounts.Mount(prefix: str, store: Store, read_only: bool = False, lent: bool = False, builtin: bool = False)
10181 10181 191

#### prefix *: str*
10692 10692 197

#### store *: Store*
10842 10842 201

#### read_only *: bool*
10896 10896 203

#### lent *: bool*
11190 11190 211

#### builtin *: bool*
11731 11731 222

#### *property* kind *: str*
12057 12057 230

#### *property* unavailable *: bool*
12183 12183 234

#### *property* name *: str*
12350 12350 238

#### *property* is_root *: bool*
12503 12503 242

#### inner(key: str) → str | None
12595 12595 244

#### outer(key: str) → str
12871 12873 248

### *exception* outrage.mounts.MountError(code: str, \*\*details: Any)
13798 13802 266

### *exception* outrage.mounts.MountUnavailableError(code: str, \*\*details: Any)
14186 14190 272

### *class* outrage.mounts.MountedStore(stores: Mapping[str, Store], \*, read_only: Collection[str] = (), lent: Collection[str] = (), builtin: Collection[str] = ())
14840 14844 283

#### writable *: ClassVar[bool]* *= True*
16426 16430 301

#### backend_name *: ClassVar[str]* *= 'mounts'*
16837 16841 308

#### *classmethod* single(store: Store) → MountedStore
17151 17155 313

#### remounted(\*, mount: Mapping[str, Store] = MappingProxyType({}), read_only: Collection[str] = (), lent: Collection[str] = (), builtin: Collection[str] = (), unmount: Collection[str] = ()) → MountedStore
17518 17524 321

#### *property* root *: Mount*
20320 20328 357

#### *property* read_only *: list[Mount]*
20742 20750 366

#### *property* multiple *: bool*
20913 20921 370

#### resolve(key: str | None, \*, allow_wildcard: bool = False) → Resolved
21053 21061 374

#### below(key: str | None) → list[Mount]
22129 22139 391

#### directly_below(key: str | None) → list[Mount]
22684 22696 400

#### segments(key: str | None, depth: int | None = None, \*, key_range: KeyRange = UNBOUNDED) → list[Segment]
23523 23537 415

#### children(parent: str | None) → list[Entry]
24954 24970 436

#### last_child(key: str | None) → str | None
25625 25643 447

#### shadowing() → list[Mount]
26557 26577 462

#### unavailable_at_or_below(key: str | None = None) → list[Mount]
27370 27392 478

#### read_only_below(key: str | None = None) → list[str]
27941 27965 486

#### read_only_at_or_below(key: str | None = None) → list[str]
28647 28673 496

#### unwritable(prefixes: Sequence[str]) → list[str]
29795 29823 512

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
30572 30602 523

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
33802 33834 569

#### exists(key: str) → bool
35937 35971 591

#### level_entry(key: str) → Entry | None
36432 36468 602

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
37030 37068 611

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
38779 38819 641

#### now(key: str = keys.ROOT, \*, key_range: KeyRange = UNBOUNDED) → str
40356 40398 665

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
41189 41233 680

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
42095 42141 694

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
44157 44205 724

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
45897 45947 744

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
48095 48147 770

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
49313 49367 782

#### close() → None
51065 51121 805

### *exception* outrage.mounts.ReadOnlyMountError(code: str, \*\*details: Any)
51200 51258 809

### *class* outrage.mounts.Resolved(mount: Mount, key: str, outer: str)
52006 52064 823

#### mount *: Mount*
52348 52406 829

#### key *: str*
52395 52453 831

#### outer *: str*
52504 52562 835

#### *property* store *: Store*
52622 52680 839

#### *property* read_only *: bool*
53071 53129 849

#### writable(action: str = 'write') → Resolved
53218 53276 853

### *class* outrage.mounts.Segment(mount: Mount, subtree: BoundedSubtree, key_range: KeyRange)
54761 54821 882

#### mount *: Mount*
55688 55748 898

#### subtree *: BoundedSubtree*
55735 55795 900

#### key_range *: KeyRange*
55809 55869 902

#### *property* store *: Store*
55873 55933 904

#### resume_from(after: str | None) → tuple[str | None, bool]
56223 56283 913

### *class* outrage.mounts.Spec(path: Path | None, type: str | None = None, extensions: str | None = None, versioning: str | None = None, lock: str | None = None, service: str | None = None)
57714 57776 937

#### path *: Path | None*
59354 59416 955

#### type *: str | None*
59622 59684 960

#### extensions *: str | None*
59836 59898 964

#### versioning *: str | None*
60164 60226 970

#### lock *: str | None*
60475 60537 975

#### service *: str | None*
60759 60821 980

#### opened(directory: str | PathLike[str] | None = None, \*, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True, create: bool = True) → FileStore
61063 61125 985

### *class* outrage.mounts.UnavailableStore(error: OutrageError, \*, mount_point: str, requested_read_only: bool = False)
63309 63373 1013

#### writable *: ClassVar[bool]* *= True*
64470 64534 1034

#### backend_name *: ClassVar[str]* *= 'unavailable'*
64914 64978 1041

#### error
65289 65353 1047

#### requested_read_only
65342 65406 1051

#### *property* reason *: dict[str, Any]*
65496 65560 1056

#### refuse(key: str | None = keys.ROOT) → NoReturn
65810 65874 1060

#### store_document(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
66302 66368 1068

#### delete(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
68920 68988 1114

#### descendant_count(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
71473 71543 1157

#### subtree_totals(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
73236 73308 1187

#### latest_change(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
75994 76068 1233

#### exists(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
78086 78162 1267

#### level_entry(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
78752 78830 1278

#### retrieve_document(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
79771 79851 1293

#### list_keys(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
81137 81219 1315

#### last_child(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
83757 83841 1362

#### get_documents(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
85594 85680 1392

#### find_documents(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
87032 87120 1418

#### missing_meta_stats(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
87855 87945 1431

#### keys_missing_meta(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
89658 89750 1460

#### copy_from(\*\_args: Any, \*\*\_kwargs: Any) → Any
90409 90503 1472

#### close() → None
94388 94484 1539

### outrage.mounts.mount_point(prefix: str, \*, spec: str | None = None) → str
94508 94606 1543

### outrage.mounts.open_mounts(directory: str | PathLike[str] | None, specs: Sequence[str] = (), read_only_specs: Sequence[str] = (), \*, root_mount: str | PathLike[str] | Spec | None = None, log: EventLog | None = None, attached: Mapping[str, Store] = MappingProxyType({}), owned: Mapping[str, Store] = MappingProxyType({}), builtin: Collection[str] = (), versioning: bool = True, on_open_error: Callable[[str, Spec, bool, OutrageError], None] | None = None) → MountedStore
95290 95390 1554

### outrage.mounts.parse_options(value: str, \*, spec: str | None = None) → Spec
101860 101962 1630

### outrage.mounts.parse_spec(spec: str) → tuple[str, Spec]
103666 103770 1660

### outrage.mounts.refuse_missing_read_only(directory: Path, prefix: str, file: str | PathLike[str] | None, backend: str | None) → None
104960 105066 1681

### outrage.mounts.refuse_unavailable(opened: Store, key: str | None, action: str) → None
106256 106364 1695

### outrage.mounts.tolerated(error: OutrageError) → bool
107144 107254 1708

### outrage.mounts.unparse(spec: Spec) → str
107543 107655 1716
