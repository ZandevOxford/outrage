# outrage.store
0 0

### outrage.store.BACKUP_DIR_NAME *= 'backups'*
3022 3022

### outrage.store.BACKUP_STAMP *= '%Y%m%d-%H%M%S'*
3152 3152

### outrage.store.CHANGED *= 'changed'*
3427 3427

### outrage.store.CONFLICTS *= ('skip', 'overwrite', 'overwrite-unchanged', 'stop')*
3813 3813

### outrage.store.DEFAULT_BACKEND *= 'sqlite'*
3958 3958

### outrage.store.backend_names() → tuple[str, ...]
4201 4201

### outrage.store.check_read_position(key: str, \*, offset: int, byte_offset: int | None, pattern: str | None, occurrence: int) → None
4612 4614

### outrage.store.check_unchanged(opened: Store, key: str, unchanged_since: str | None, \*, action: str = 'write over', subtree: bool = True, key_range: KeyRange = UNBOUNDED) → None
5601 5605

### outrage.store.DEFAULT_BULK_MAX_CHARS *= 2000*
7600 7606

### outrage.store.DEFAULT_DIR_NAME *= '.outrage'*
7751 7757

### outrage.store.DEFAULT_MAX_CHARS *= 8000*
7907 7913

### outrage.store.ENCODINGS *: tuple[str, ...]* *= ('json-string',)*
8094 8100

### outrage.store.ENV_DIR *= 'OUTRAGE_DIR'*
8362 8368

### outrage.store.EVERYTHING *= BoundedSubtree(key=None, depth=None)*
8601 8607

### outrage.store.FAILED *= 'failed'*
8810 8816

### outrage.store.FORMATS *: tuple[str, ...]* *= ('markdown', 'json', 'text', 'html')*
8926 8932

### outrage.store.OVERWRITE *= 'overwrite'*
9430 9436

### outrage.store.OVERWRITE_UNCHANGED *= 'overwrite-unchanged'*
9507 9513

### outrage.store.READ *= 'read'*
9959 9965

### outrage.store.SKIP *= 'skip'*
10320 10326

### outrage.store.SKIPPED *= 'skipped'*
10486 10492

### outrage.store.STOP *= 'stop'*
10605 10611

### outrage.store.STOPPED *= 'stopped'*
10786 10792

### outrage.store.UNBOUNDED *= KeyRange(after=None, after_inclusive=None, after_subtree=None, before=None, before_inclusive=None, final_subtree=None)*
11023 11029

### outrage.store.WROTE *= 'wrote'*
11421 11427

### *class* outrage.store.AuditRow(key: str, doc_key: str, meta_name: str | None, parent: str, chars: int)
11536 11542

#### key *: str*
12752 12758

#### doc_key *: str*
12825 12831

#### meta_name *: str | None*
12990 12996

#### parent *: str*
13184 13190

#### chars *: int*
13416 13422

### *class* outrage.store.Backup(path: Path, bytes: int, documents: int, integrity: str)
13492 13498

#### path *: Path*
13948 13954

#### bytes *: int*
14031 14037

#### documents *: int*
14107 14113

#### integrity *: str*
14249 14255

### *exception* outrage.store.BackendError(code: str, \*\*details: Any)
14386 14392

### *exception* outrage.store.BackupError(code: str, \*\*details: Any)
14805 14811

### *class* outrage.store.BoundedSubtree(key: str | None = None, depth: int | None = None)
15208 15214

#### key *: str | None*
16229 16235

#### depth *: int | None*
16366 16372

### *exception* outrage.store.ChangedSinceError(code: str, \*\*details: Any)
16506 16512

### *class* outrage.store.DocumentMatch(document: Entry, witnesses: tuple[MatchWitness, ...])
17582 17588

#### document *: Entry*
17929 17935

#### witnesses *: tuple[MatchWitness, ...]*
17978 17984

### outrage.store.Encoding
18111 18117

### *class* outrage.store.Entry(key: str, kind: str, size: int | None, format: str | None, updated_at: str | None, descendants: int | None = None, descendant_documents: int | None = None, descendant_chars: int | None = None)
18461 18467

#### key *: str*
19798 19804

#### kind *: str*
19871 19877

#### size *: int | None*
20046 20052

#### format *: str | None*
20185 20191

#### updated_at *: str | None*
20325 20331

#### descendants *: int | None*
20469 20475

#### descendant_documents *: int | None*
20794 20800

#### descendant_chars *: int | None*
21403 21409

### *class* outrage.store.Excerpt(key: str, content: str, format: str | None, updated_at: str, offset: int | None, returned: int, total: int | None, next_offset: int | None, byte_offset: int, total_bytes: int, next_byte_offset: int | None)
21614 21620

#### key *: str*
22868 22874

#### content *: str*
22941 22947

#### format *: str | None*
23018 23024

#### updated_at *: str*
23158 23164

#### offset *: int | None*
23238 23244

#### returned *: int*
23758 23764

#### total *: int | None*
23869 23875

#### next_offset *: int | None*
24215 24221

#### byte_offset *: int*
24516 24522

#### total_bytes *: int*
24873 24879

#### next_byte_offset *: int | None*
25001 25007

#### *property* truncated *: bool*
25302 25308

### *class* outrage.store.FileStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
25882 25888

#### default_filename *: ClassVar[str]*
28078 28084

#### format_version *: ClassVar[int]*
28630 28636

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Self
29229 29235

#### opened_at(path: Path) → Self
31729 31737

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
32484 32494

#### verified_backup(target: Path) → Backup
34244 34256

#### backup_path(destination: str | PathLike[str] | None, \*, overwrite: bool) → Path
35259 35273

#### *abstract property* stored_format_version *: int*
36289 36305

#### *abstractmethod* audit_rows() → Iterator[AuditRow]
36861 36877

#### *abstractmethod* check_file(report: Report) → None
37631 37649

#### *abstractmethod* repair() → list[Repaired]
38407 38427

### outrage.store.Format
39197 39219

### *exception* outrage.store.InvalidArgumentError(code: str, \*\*details: Any)
39763 39785

### *exception* outrage.store.KeyNotFoundError(code: str, \*\*details: Any)
41091 41113

### *class* outrage.store.KeyRange(after: str | None = None, after_inclusive: str | None = None, after_subtree: str | None = None, before: str | None = None, before_inclusive: str | None = None, final_subtree: str | None = None)
41464 41486

#### after *: str | None*
44426 44448

#### after_inclusive *: str | None*
44565 44587

#### after_subtree *: str | None*
44714 44736

#### before *: str | None*
44861 44883

#### before_inclusive *: str | None*
45001 45023

#### final_subtree *: str | None*
45151 45173

### outrage.store.MatchMode
45298 45320

### *class* outrage.store.MatchWitness(criterion: int, source_key: str, source: Literal['document', 'metadata'], start: int, end: int)
45508 45530

#### criterion *: int*
46063 46085

#### source_key *: str*
46143 46165

#### source *: Literal['document', 'metadata']*
46223 46245

#### start *: int*
46336 46358

#### end *: int*
46412 46434

### outrage.store.MetaReader
46486 46508

### *class* outrage.store.MissingMeta(total: int, total_chars: int, sample: list[str])
47407 47429

#### total *: int*
48086 48108

#### total_chars *: int*
48225 48247

#### sample *: list[str]*
48431 48453

### *class* outrage.store.Page(items: list[T], returned: int, total: int, total_chars: int, next_cursor: str | None)
48643 48665

#### items *: list[T]*
49570 49592

#### returned *: int*
49650 49672

#### total *: int*
49750 49772

#### total_chars *: int*
49894 49916

#### next_cursor *: str | None*
50203 50225

#### *property* truncated *: bool*
50409 50431

### *exception* outrage.store.PatternNotFoundError(code: str, \*\*details: Any)
50794 50816

### *exception* outrage.store.ReadOnlyStoreError(code: str, \*\*details: Any)
51194 51216

### outrage.store.SearchCombination
52065 52087

### *class* outrage.store.SearchCriterion(pattern: str, match: Literal['contains', 'line', 'regex'], target: Literal['document', 'metadata'], meta_name: tuple[str, ...] | None = None)
52262 52284

#### pattern *: str*
52921 52943

#### match *: Literal['contains', 'line', 'regex']*
52998 53020

#### target *: Literal['document', 'metadata']*
53115 53137

#### meta_name *: tuple[str, ...] | None*
53228 53250

### *class* outrage.store.SearchPage(matches: tuple[DocumentMatch, ...], matched: int, matched_chars: int, scanned: int, total_candidates: int, total_candidate_chars: int, next_cursor: str | None)
53440 53462

#### matches *: tuple[DocumentMatch, ...]*
54460 54482

#### matched *: int*
54593 54615

#### matched_chars *: int*
54671 54693

#### scanned *: int*
54755 54777

#### total_candidates *: int*
54833 54855

#### total_candidate_chars *: int*
54920 54942

#### next_cursor *: str | None*
55012 55034

### outrage.store.SearchTarget
55157 55179

### *class* outrage.store.Store(\*, log: EventLog | None = None, mount_point: str | None = None)
55354 55376

#### writable *: ClassVar[bool]* *= True*
56740 56762

#### writes_deferred *: ClassVar[bool]* *= False*
57385 57407

#### backend_name *: ClassVar[str]*
57930 57952

#### *abstractmethod* close() → None
58286 58308

#### *abstractmethod* store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
58663 58687

#### copy_from(source: Store, subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
61923 61949

#### located(key: str, format: str | None = None) → Path | None
67229 67257

#### *abstractmethod* delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
68167 68197

#### *abstractmethod* descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
71031 71063

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
72786 72820

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
74787 74823

#### *abstractmethod* exists(key: str) → bool
77500 77538

#### *abstractmethod* level_entry(key: str) → Entry | None
78010 78050

#### *abstractmethod* retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
78893 78935

#### *abstractmethod* list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
80605 80649

#### last_child(key: str) → str | None
83747 83793

#### *abstractmethod* get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
85460 85508

#### find_documents(subtree: BoundedSubtree = EVERYTHING, \*, criteria: Sequence[SearchCriterion], combine: Literal['any', 'all'] = 'any', key_range: KeyRange = UNBOUNDED, cursor: str | None = None, scan_limit: int | None = None) → SearchPage
87633 87683

#### *abstractmethod* missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
88881 88933

#### *abstractmethod* keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
90738 90792

### *exception* outrage.store.StoreFileError(code: str, \*\*details: Any)
91942 91998

### *class* outrage.store.SubtreeTotals(keys: int, documents: int, chars: int | None)
92689 92745

#### keys *: int*
93741 93797

#### documents *: int*
94318 94374

#### chars *: int | None*
94901 94957

### *class* outrage.store.Transfer(action: str, key: str | None, path: Path | None, reason: str | None = None, characters: int = 0, error: OutrageError | None = None)
95438 95494

#### action *: str*
97658 97714

#### key *: str | None*
97734 97790

#### path *: Path | None*
97871 97927

#### reason *: str | None*
98018 98074

#### characters *: int*
98158 98214

#### error *: OutrageError | None*
98239 98295

### outrage.store.default_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → FileStore
98373 98429

### outrage.store.default_store_file() → str
100580 100638

### outrage.store.entry_kind(key: str) → str
101235 101295

### outrage.store.meta_reader(scope: str) → Callable[[str, str | None, str | None], tuple[str | None, str | None]]
101908 101970

### outrage.store.open_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Iterator[FileStore]
103590 103654

### outrage.store.read_all(store: Store, key: str, \*\*kwargs: Any) → Excerpt
104885 104951

### outrage.store.resolve_directory(explicit: str | PathLike[str] | None = None) → Path
105889 105957

### outrage.store.store_file(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → Path
106433 106503
