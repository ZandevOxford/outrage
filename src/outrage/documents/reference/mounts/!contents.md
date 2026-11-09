# outrage.mounts
0 0 1

### outrage.mounts.EXTENSIONS_OPTION *= 'extensions'*
2317 2317 43

### outrage.mounts.LOCK_OPTION *= 'lock'*
3314 3314 61

### outrage.mounts.MOUNT_KIND *= 'mount'*
4134 4134 75

### outrage.mounts.OPTIONS *= ('type', 'extensions', 'versioning', 'lock', 'service')*
4526 4526 83

### outrage.mounts.OPTION_ASSIGNMENT *= '='*
4891 4891 90

### outrage.mounts.OPTION_DELIMITER *= ','*
5154 5154 96

### outrage.mounts.READ_ONLY_MOUNT_KIND *= 'read-only mount'*
5930 5930 110

### outrage.mounts.ROOT_KIND *= 'root'*
6736 6736 125

### outrage.mounts.SERVICE_OPTION *= 'service'*
7138 7138 133

### outrage.mounts.SPEC_DELIMITER *= '='*
8157 8157 152

### outrage.mounts.TYPE_OPTION *= 'type'*
8470 8470 159

### outrage.mounts.UNAVAILABLE_MOUNT_KIND *= 'unavailable mount'*
9168 9168 172

### outrage.mounts.VERSIONING_OPTION *= 'versioning'*
9478 9478 179

### *class* outrage.mounts.Mount(prefix: str, store: Store, read_only: bool = False, lent: bool = False, builtin: bool = False)
10174 10174 191

#### prefix *: str*
10685 10685 197

#### store *: Store*
10835 10835 201

#### read_only *: bool*
10889 10889 203

#### lent *: bool*
11183 11183 211

#### builtin *: bool*
11724 11724 222

#### *property* kind *: str*
12050 12050 230

#### *property* unavailable *: bool*
12176 12176 234

#### *property* name *: str*
12343 12343 238

#### *property* is_root *: bool*
12496 12496 242

#### inner(key: str) → str | None
12588 12588 244

#### outer(key: str) → str
12864 12866 248

### *exception* outrage.mounts.MountError(code: str, \*\*details: Any)
13791 13795 266

### *exception* outrage.mounts.MountUnavailableError(code: str, \*\*details: Any)
14179 14183 272

### *class* outrage.mounts.MountedStore(stores: Mapping[str, Store], \*, read_only: Collection[str] = (), lent: Collection[str] = (), builtin: Collection[str] = ())
14833 14837 283

#### writable *: ClassVar[bool]* *= True*
16419 16423 301

#### backend_name *: ClassVar[str]* *= 'mounts'*
16830 16834 308

#### *classmethod* single(store: Store) → MountedStore
17144 17148 313

#### remounted(\*, mount: Mapping[str, Store] = MappingProxyType({}), read_only: Collection[str] = (), lent: Collection[str] = (), builtin: Collection[str] = (), unmount: Collection[str] = ()) → MountedStore
17511 17517 321

#### *property* root *: Mount*
20313 20321 357

#### *property* read_only *: list[Mount]*
20735 20743 366

#### *property* multiple *: bool*
20906 20914 370

#### resolve(key: str | None, \*, allow_wildcard: bool = False) → Resolved
21046 21054 374

#### below(key: str | None) → list[Mount]
22122 22132 391

#### directly_below(key: str | None) → list[Mount]
22677 22689 400

#### segments(key: str | None, depth: int | None = None, \*, key_range: KeyRange = UNBOUNDED) → list[Segment]
23516 23530 415

#### children(parent: str | None) → list[Entry]
24947 24963 436

#### last_child(key: str | None) → str | None
25618 25636 447

#### shadowing() → list[Mount]
26550 26570 462

#### unavailable_at_or_below(key: str | None = None) → list[Mount]
27363 27385 478

#### read_only_below(key: str | None = None) → list[str]
27934 27958 486

#### read_only_at_or_below(key: str | None = None) → list[str]
28640 28666 496

#### unwritable(prefixes: Sequence[str]) → list[str]
29788 29816 512

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
30565 30595 523

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
33795 33827 569

#### exists(key: str) → bool
35930 35964 591

#### level_entry(key: str) → Entry | None
36425 36461 602

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
37023 37061 611

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
38772 38812 641

#### now(key: str = keys.ROOT, \*, key_range: KeyRange = UNBOUNDED) → str
40349 40391 665

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
41182 41226 680

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
42088 42134 694

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
44150 44198 724

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
45890 45940 744

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
48088 48140 770

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
49306 49360 782

#### close() → None
51058 51114 805

### *exception* outrage.mounts.ReadOnlyMountError(code: str, \*\*details: Any)
51193 51251 809

### *class* outrage.mounts.Resolved(mount: Mount, key: str, outer: str)
51999 52057 823

#### mount *: Mount*
52341 52399 829

#### key *: str*
52388 52446 831

#### outer *: str*
52497 52555 835

#### *property* store *: Store*
52615 52673 839

#### *property* read_only *: bool*
53064 53122 849

#### writable(action: str = 'write') → Resolved
53211 53269 853

### *class* outrage.mounts.Segment(mount: Mount, subtree: BoundedSubtree, key_range: KeyRange)
54754 54814 882

#### mount *: Mount*
55681 55741 898

#### subtree *: BoundedSubtree*
55728 55788 900

#### key_range *: KeyRange*
55802 55862 902

#### *property* store *: Store*
55866 55926 904

#### resume_from(after: str | None) → tuple[str | None, bool]
56216 56276 913

### *class* outrage.mounts.Spec(path: Path | None, type: str | None = None, extensions: str | None = None, versioning: str | None = None, lock: str | None = None, service: str | None = None)
57707 57769 937

#### path *: Path | None*
59347 59409 955

#### type *: str | None*
59615 59677 960

#### extensions *: str | None*
59829 59891 964

#### versioning *: str | None*
60157 60219 970

#### lock *: str | None*
60468 60530 975

#### service *: str | None*
60752 60814 980

#### opened(directory: str | PathLike[str] | None = None, \*, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True, create: bool = True) → FileStore
61056 61118 985

### *class* outrage.mounts.UnavailableStore(error: OutrageError, \*, mount_point: str, requested_read_only: bool = False)
63302 63366 1013

#### writable *: ClassVar[bool]* *= True*
64463 64527 1034

#### backend_name *: ClassVar[str]* *= 'unavailable'*
64907 64971 1041

#### error
65282 65346 1047

#### requested_read_only
65335 65399 1051

#### *property* reason *: dict[str, Any]*
65489 65553 1056

#### refuse(key: str | None = keys.ROOT) → NoReturn
65803 65867 1060

#### store_document(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
66295 66361 1068

#### delete(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
68913 68981 1114

#### descendant_count(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
71466 71536 1157

#### subtree_totals(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
73229 73301 1187

#### latest_change(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
75987 76061 1233

#### exists(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
78079 78155 1267

#### level_entry(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
78745 78823 1278

#### retrieve_document(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
79764 79844 1293

#### list_keys(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
81130 81212 1315

#### last_child(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
83750 83834 1362

#### get_documents(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
85587 85673 1392

#### find_documents(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
87025 87113 1418

#### missing_meta_stats(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
87848 87938 1431

#### keys_missing_meta(key: Any = keys.ROOT, \*\_args: Any, \*\*\_kwargs: Any) → Any
89651 89743 1460

#### copy_from(\*\_args: Any, \*\*\_kwargs: Any) → Any
90402 90496 1472

#### close() → None
94381 94477 1539

### outrage.mounts.mount_point(prefix: str, \*, spec: str | None = None) → str
94501 94599 1543

### outrage.mounts.open_mounts(directory: str | PathLike[str] | None, specs: Sequence[str] = (), read_only_specs: Sequence[str] = (), \*, root_mount: str | PathLike[str] | Spec | None = None, log: EventLog | None = None, attached: Mapping[str, Store] = MappingProxyType({}), owned: Mapping[str, Store] = MappingProxyType({}), builtin: Collection[str] = (), versioning: bool = True, on_open_error: Callable[[str, Spec, bool, OutrageError], None] | None = None) → MountedStore
95283 95383 1554

### outrage.mounts.parse_options(value: str, \*, spec: str | None = None) → Spec
101853 101955 1630

### outrage.mounts.parse_spec(spec: str) → tuple[str, Spec]
103659 103763 1660

### outrage.mounts.refuse_missing_read_only(directory: Path, prefix: str, file: str | PathLike[str] | None, backend: str | None) → None
104953 105059 1681

### outrage.mounts.refuse_unavailable(opened: Store, key: str | None, action: str) → None
106249 106357 1695

### outrage.mounts.tolerated(error: OutrageError) → bool
107137 107247 1708

### outrage.mounts.unparse(spec: Spec) → str
107536 107648 1716
