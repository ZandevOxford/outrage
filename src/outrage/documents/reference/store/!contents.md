# outrage.store
0 0 1

### outrage.store.BACKUP_DIR_NAME *= 'backups'*
3198 3198 50

### outrage.store.BACKUP_STAMP *= '%Y%m%d-%H%M%S'*
3328 3328 55

### outrage.store.CHANGED *= 'changed'*
3603 3603 61

### outrage.store.CONFLICTS *= ('skip', 'overwrite', 'overwrite-unchanged', 'stop')*
3989 3989 68

### outrage.store.DEFAULT_BACKEND *= 'sqlite'*
4134 4134 72

### outrage.store.backend_for(filename: str | PathLike[str] | None = None, backend: str | None = None) → type[FileStore]
4377 4377 78

### outrage.store.backend_names() → tuple[str, ...]
5549 5551 93

### outrage.store.check_read_position(key: str, \*, offset: int, byte_offset: int | None, line: int | None, lines: int | None, pattern: str | None, occurrence: int) → None
6037 6041 102

### outrage.store.check_unchanged(opened: Store, key: str, unchanged_since: str | None, \*, action: str = 'write over', subtree: bool = True, key_range: KeyRange = UNBOUNDED) → None
7301 7307 112

### outrage.store.DEFAULT_BULK_MAX_CHARS *= 2000*
9306 9314 139

### outrage.store.DEFAULT_DIR_NAME *= '.outrage'*
9457 9465 144

### outrage.store.DEFAULT_MAX_CHARS *= 8000*
9613 9621 149

### outrage.store.ENCODINGS *: tuple[str, ...]* *= ('json-string',)*
9800 9808 154

### outrage.store.ENV_DIR *= 'OUTRAGE_DIR'*
10070 10078 158

### outrage.store.EVERYTHING *= BoundedSubtree(key=None, depth=None)*
10309 10317 164

### outrage.store.FAILED *= 'failed'*
10518 10526 169

### outrage.store.FORMATS *: tuple[str, ...]* *= ('markdown', 'json', 'text', 'html')*
10634 10642 173

### outrage.store.OVERWRITE *= 'overwrite'*
11140 11148 180

### outrage.store.OVERWRITE_UNCHANGED *= 'overwrite-unchanged'*
11217 11225 184

### outrage.store.READ *= 'read'*
11669 11677 192

### outrage.store.SKIP *= 'skip'*
12030 12038 199

### outrage.store.SKIPPED *= 'skipped'*
12196 12204 204

### outrage.store.STOP *= 'stop'*
12315 12323 208

### outrage.store.STOPPED *= 'stopped'*
12496 12504 213

### outrage.store.UNBOUNDED *= KeyRange(after=None, after_inclusive=None, after_subtree=None, before=None, before_inclusive=None, final_subtree=None)*
12733 12741 219

### outrage.store.VERSIONING_OFF *= 'off'*
13131 13139 225

### outrage.store.VERSIONING_ON *= 'on'*
13244 13252 229

### outrage.store.VERSIONING_SETTINGS *= ('on', 'off')*
13555 13563 236

### outrage.store.WROTE *= 'wrote'*
13661 13669 240

### *class* outrage.store.AuditRow(key: str, doc_key: str, meta_name: str | None, parent: str, chars: int)
13776 13784 244

#### key *: str*
14999 15007 260

#### doc_key *: str*
15073 15081 262

#### meta_name *: str | None*
15239 15247 267

#### parent *: str*
15435 15443 271

#### chars *: int*
15668 15676 276

### *class* outrage.store.Backup(path: Path, bytes: int, documents: int, integrity: str)
15745 15753 278

#### path *: Path*
16205 16213 284

#### bytes *: int*
16288 16296 286

#### documents *: int*
16365 16373 288

#### integrity *: str*
16508 16516 292

### *exception* outrage.store.BackendError(code: str, \*\*details: Any)
16646 16654 296

### *exception* outrage.store.BackupError(code: str, \*\*details: Any)
17067 17075 303

### *class* outrage.store.BoundedSubtree(key: str | None = None, depth: int | None = None)
17472 17480 309

#### key *: str | None*
18498 18506 325

#### depth *: int | None*
18637 18645 327

### *exception* outrage.store.ChangedSinceError(code: str, \*\*details: Any)
18779 18787 329

### *class* outrage.store.DocumentMatch(document: Entry, witnesses: tuple[MatchWitness, ...])
19857 19865 346

#### document *: Entry*
20206 20214 352

#### witnesses *: tuple[MatchWitness, ...]*
20255 20263 354

### outrage.store.Encoding
20389 20397 356

### *class* outrage.store.Entry(key: str, kind: str, size: int | None, format: str | None, updated_at: str | None, descendants: int | None = None, descendant_documents: int | None = None, descendant_chars: int | None = None)
20739 20747 364

#### key *: str*
22091 22099 374

#### kind *: str*
22165 22173 376

#### size *: int | None*
22341 22349 381

#### format *: str | None*
22482 22490 383

#### updated_at *: str | None*
22624 22632 385

#### descendants *: int | None*
22770 22778 387

#### descendant_documents *: int | None*
23097 23105 393

#### descendant_chars *: int | None*
23708 23716 402

### *class* outrage.store.Excerpt(key: str, content: str, format: str | None, updated_at: str, offset: int | None, returned: int, total: int | None, next_offset: int | None, byte_offset: int, total_bytes: int, next_byte_offset: int | None, line: int | None = None, next_line: int | None = None)
23921 23929 406

#### key *: str*
25477 25485 412

#### content *: str*
25551 25559 414

#### format *: str | None*
25629 25637 416

#### updated_at *: str*
25771 25779 418

#### offset *: int | None*
25852 25860 420

#### returned *: int*
26383 26391 429

#### total *: int | None*
26495 26503 433

#### next_offset *: int | None*
26852 26860 439

#### byte_offset *: int*
27155 27163 445

#### total_bytes *: int*
27513 27521 452

#### next_byte_offset *: int | None*
27642 27650 456

#### line *: int | None*
27945 27953 462

#### next_line *: int | None*
28224 28232 467

#### *property* truncated *: bool*
28562 28570 473

### *class* outrage.store.FileStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
29143 29151 486

#### default_filename *: ClassVar[str]*
31348 31356 512

#### format_version *: ClassVar[int]*
31901 31909 520

#### reads_patterns *: ClassVar[bool]* *= False*
32501 32509 528

#### locates_own_store *: ClassVar[bool]* *= False*
32925 32933 535

#### manages_schema *: ClassVar[bool]* *= False*
33946 33954 552

#### *property* target *: dict[str, str] | None*
35025 35033 571

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, create: bool = True) → Self
35627 35635 580

#### *classmethod* reporting(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None) → Self
39935 39945 630

#### opened_at(path: Path) → Self
41958 41970 652

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
42713 42727 666

#### verified_backup(target: Path) → Backup
44477 44493 693

#### backup_path(destination: str | PathLike[str] | None, \*, overwrite: bool) → Path
45492 45510 714

#### *abstract property* stored_format_version *: int*
46526 46546 728

#### *abstractmethod* audit_rows() → Iterator[AuditRow]
47099 47119 739

#### *abstractmethod* check_file(report: Report) → None
47869 47891 752

#### *abstractmethod* repair() → list[Repaired]
48646 48670 766

### outrage.store.Format
49437 49463 780

### *exception* outrage.store.InvalidArgumentError(code: str, \*\*details: Any)
50003 50029 791

### *exception* outrage.store.KeyNotFoundError(code: str, \*\*details: Any)
51333 51359 814

### *class* outrage.store.KeyRange(after: str | None = None, after_inclusive: str | None = None, after_subtree: str | None = None, before: str | None = None, before_inclusive: str | None = None, final_subtree: str | None = None)
51708 51734 820

#### after *: str | None*
54683 54709 858

#### after_inclusive *: str | None*
54824 54850 860

#### after_subtree *: str | None*
54975 55001 862

#### before *: str | None*
55124 55150 864

#### before_inclusive *: str | None*
55266 55292 866

#### final_subtree *: str | None*
55418 55444 868

### outrage.store.MatchMode
55567 55593 870

### *class* outrage.store.MatchWitness(criterion: int, source_key: str, source: Literal['document', 'metadata'], start: int, end: int, line: int = 1)
55777 55803 876

#### criterion *: int*
56409 56435 882

#### source_key *: str*
56490 56516 884

#### source *: Literal['document', 'metadata']*
56571 56597 886

#### start *: int*
56684 56710 888

#### end *: int*
56761 56787 890

#### line *: int*
56836 56862 892

### outrage.store.MetaReader
56971 56997 896

### *class* outrage.store.MissingMeta(total: int, total_chars: int, sample: list[str], selection_documents: int | None = None, selection_carried: dict[str, int] | None = None)
57902 57928 903

#### total *: int*
59018 59044 913

#### total_chars *: int*
59158 59184 917

#### sample *: list[str]*
59365 59391 922

#### selection_documents *: int | None*
59579 59605 926

#### selection_carried *: dict[str, int] | None*
60070 60096 934

### *class* outrage.store.Page(items: list[T], returned: int, total: int, total_chars: int, next_cursor: str | None)
61065 61091 951

#### items *: list[T]*
61998 62024 963

#### returned *: int*
62079 62105 965

#### total *: int*
62180 62206 969

#### total_chars *: int*
62325 62351 973

#### next_cursor *: str | None*
62635 62661 980

#### *property* truncated *: bool*
62843 62869 984

### *exception* outrage.store.PatternNotFoundError(code: str, \*\*details: Any)
63229 63255 993

### *exception* outrage.store.ReadOnlyStoreError(code: str, \*\*details: Any)
63631 63657 999

### outrage.store.SearchCombination
64504 64530 1012

### *class* outrage.store.SearchCriterion(pattern: str, match: Literal['contains', 'line', 'regex'], target: Literal['document', 'metadata'], meta_name: tuple[str, ...] | None = None)
64701 64727 1018

#### pattern *: str*
65365 65391 1024

#### match *: Literal['contains', 'line', 'regex']*
65443 65469 1026

#### target *: Literal['document', 'metadata']*
65560 65586 1028

#### meta_name *: tuple[str, ...] | None*
65673 65699 1030

### *class* outrage.store.SearchPage(matches: tuple[DocumentMatch, ...], matched: int, matched_chars: int, scanned: int, total_candidates: int, total_candidate_chars: int, next_cursor: str | None)
65888 65914 1032

#### matches *: tuple[DocumentMatch, ...]*
66917 66943 1042

#### matched *: int*
67051 67077 1044

#### matched_chars *: int*
67130 67156 1046

#### scanned *: int*
67215 67241 1048

#### total_candidates *: int*
67294 67320 1050

#### total_candidate_chars *: int*
67382 67408 1052

#### next_cursor *: str | None*
67475 67501 1054

### outrage.store.SearchTarget
67622 67648 1056

### *class* outrage.store.Store(\*, log: EventLog | None = None, mount_point: str | None = None)
67819 67845 1062

#### writable *: ClassVar[bool]* *= True*
69208 69234 1085

#### versioned *: ClassVar[bool]* *= False*
69854 69880 1095

#### writes_deferred *: ClassVar[bool]* *= False*
70390 70416 1104

#### backend_name *: ClassVar[str]*
70936 70962 1112

#### *abstractmethod* close() → None
71293 71319 1118

#### *abstractmethod* store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
71671 71699 1127

#### copy_from(source: Store, subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
74944 74974 1173

#### located(key: str, format: str | None = None) → Path | None
80264 80296 1240

#### *abstractmethod* delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
81206 81240 1254

#### *abstractmethod* descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
84077 84113 1297

#### now(key: str = keys.ROOT, \*, key_range: KeyRange = UNBOUNDED) → str
85835 85873 1327

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
86601 86641 1339

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
88723 88765 1373

#### *abstractmethod* exists(key: str) → bool
91438 91482 1419

#### *abstractmethod* level_entry(key: str) → Entry | None
91950 91996 1430

#### *abstractmethod* retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
92835 92883 1445

#### *abstractmethod* list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
94979 95029 1467

#### last_child(key: str) → str | None
98129 98181 1514

#### *abstractmethod* get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
99845 99899 1544

#### find_documents(subtree: BoundedSubtree = EVERYTHING, \*, criteria: Sequence[SearchCriterion], combine: Literal['any', 'all'] = 'any', key_range: KeyRange = UNBOUNDED, cursor: str | None = None, scan_limit: int | None = None) → SearchPage
102028 102084 1570

#### *abstractmethod* missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
103280 103338 1583

#### *abstractmethod* keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
105427 105487 1612

### *exception* outrage.store.StoreFileError(code: str, \*\*details: Any)
106638 106700 1624

### *class* outrage.store.SchemaState(backend: str, service: str, path: Path, schema: str, stored: SchemaVersion | None, oldest: int, newest: int, operating: int | None, writable: bool, problem: Refusal | None = None)
107387 107449 1636

#### backend *: str*
109312 109374 1656

#### service *: str*
109450 109512 1660

#### path *: Path*
109578 109640 1664

#### schema *: str*
109705 109767 1668

#### stored *: SchemaVersion | None*
109845 109907 1672

#### oldest *: int*
110038 110100 1676

#### newest *: int*
110160 110222 1680

#### operating *: int | None*
110305 110367 1684

#### writable *: bool*
110518 110580 1688

#### problem *: Refusal | None*
110658 110720 1692

### *class* outrage.store.SchemaVersion(version: int, read_floor: int, write_floor: int)
110849 110911 1696

#### version *: int*
111547 111609 1707

#### read_floor *: int*
111626 111688 1709

#### write_floor *: int*
111708 111770 1711

### *class* outrage.store.SubtreeTotals(keys: int, documents: int, chars: int | None)
111791 111853 1713

#### keys *: int*
112848 112910 1729

#### documents *: int*
113426 113488 1740

#### chars *: int | None*
114010 114072 1750

### *class* outrage.store.Transfer(action: str, key: str | None, path: Path | None, reason: str | None = None, characters: int = 0, error: OutrageError | None = None)
114549 114611 1759

#### action *: str*
117305 117367 1795

#### key *: str | None*
117382 117444 1797

#### path *: Path | None*
117521 117583 1799

#### reason *: str | None*
117669 117731 1801

#### characters *: int*
117811 117873 1803

#### error *: OutrageError | None*
117893 117955 1805

### outrage.store.default_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, create: bool = True) → FileStore
118028 118090 1807

### outrage.store.default_store_file() → str
121604 121668 1840

### outrage.store.entry_kind(key: str) → str
122260 122326 1854

### outrage.store.is_pattern(filename: str | PathLike[str] | None) → bool
122935 123003 1867

### outrage.store.locates_own_store(backend: str | None = None, \*, unknown: bool | None = None) → bool
123678 123748 1876

### outrage.store.meta_reader(scope: str) → Callable[[str, str | None, str | None], tuple[str | None, str | None]]
125607 125679 1904

### outrage.store.open_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Iterator[FileStore]
127300 127374 1922

### outrage.store.pattern_matches(directory: str | PathLike[str], filename: str | PathLike[str]) → list[Path]
129125 129201 1926

### outrage.store.read_all(store: Store, key: str, \*\*kwargs: Any) → Excerpt
130267 130345 1938

### outrage.store.resolve_directory(explicit: str | PathLike[str] | None = None) → Path
131279 131359 1954

### outrage.store.store_file(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → Path
131826 131908 1961

### outrage.store.store_present(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → bool
133434 133518 1987
