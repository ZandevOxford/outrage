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

### *class* outrage.store.Entry(key: str, kind: str, size: int | None, format: str | None, updated_at: str | None)
18451 18457

#### key *: str*
19133 19139

#### kind *: str*
19206 19212

#### size *: int | None*
19381 19387

#### format *: str | None*
19520 19526

#### updated_at *: str | None*
19660 19666

### *class* outrage.store.Excerpt(key: str, content: str, format: str | None, updated_at: str, offset: int | None, returned: int, total: int | None, next_offset: int | None, byte_offset: int, total_bytes: int, next_byte_offset: int | None)
19804 19810

#### key *: str*
21058 21064

#### content *: str*
21131 21137

#### format *: str | None*
21208 21214

#### updated_at *: str*
21348 21354

#### offset *: int | None*
21428 21434

#### returned *: int*
21948 21954

#### total *: int | None*
22059 22065

#### next_offset *: int | None*
22405 22411

#### byte_offset *: int*
22706 22712

#### total_bytes *: int*
23063 23069

#### next_byte_offset *: int | None*
23191 23197

#### *property* truncated *: bool*
23492 23498

### *class* outrage.store.FileStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
24072 24078

#### default_filename *: ClassVar[str]*
26268 26274

#### format_version *: ClassVar[int]*
26820 26826

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Self
27419 27425

#### opened_at(path: Path) → Self
29919 29927

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
30674 30684

#### verified_backup(target: Path) → Backup
32434 32446

#### backup_path(destination: str | PathLike[str] | None, \*, overwrite: bool) → Path
33449 33463

#### *abstract property* stored_format_version *: int*
34479 34495

#### *abstractmethod* audit_rows() → Iterator[AuditRow]
35051 35067

#### *abstractmethod* check_file(report: Report) → None
35821 35839

#### *abstractmethod* repair() → list[Repaired]
36597 36617

### outrage.store.Format
37387 37409

### *exception* outrage.store.InvalidArgumentError(code: str, \*\*details: Any)
37953 37975

### *exception* outrage.store.KeyNotFoundError(code: str, \*\*details: Any)
39281 39303

### *class* outrage.store.KeyRange(after: str | None = None, after_inclusive: str | None = None, after_subtree: str | None = None, before: str | None = None, before_inclusive: str | None = None, final_subtree: str | None = None)
39654 39676

#### after *: str | None*
42616 42638

#### after_inclusive *: str | None*
42755 42777

#### after_subtree *: str | None*
42904 42926

#### before *: str | None*
43051 43073

#### before_inclusive *: str | None*
43191 43213

#### final_subtree *: str | None*
43341 43363

### outrage.store.MatchMode
43488 43510

### *class* outrage.store.MatchWitness(criterion: int, source_key: str, source: Literal['document', 'metadata'], start: int, end: int)
43698 43720

#### criterion *: int*
44253 44275

#### source_key *: str*
44333 44355

#### source *: Literal['document', 'metadata']*
44413 44435

#### start *: int*
44526 44548

#### end *: int*
44602 44624

### outrage.store.MetaReader
44676 44698

### *class* outrage.store.MissingMeta(total: int, total_chars: int, sample: list[str])
45597 45619

#### total *: int*
46276 46298

#### total_chars *: int*
46415 46437

#### sample *: list[str]*
46621 46643

### *class* outrage.store.Page(items: list[T], returned: int, total: int, total_chars: int, next_cursor: str | None)
46833 46855

#### items *: list[T]*
47760 47782

#### returned *: int*
47840 47862

#### total *: int*
47940 47962

#### total_chars *: int*
48084 48106

#### next_cursor *: str | None*
48393 48415

#### *property* truncated *: bool*
48599 48621

### *exception* outrage.store.PatternNotFoundError(code: str, \*\*details: Any)
48984 49006

### *exception* outrage.store.ReadOnlyStoreError(code: str, \*\*details: Any)
49384 49406

### outrage.store.SearchCombination
50255 50277

### *class* outrage.store.SearchCriterion(pattern: str, match: Literal['contains', 'line', 'regex'], target: Literal['document', 'metadata'], meta_name: tuple[str, ...] | None = None)
50452 50474

#### pattern *: str*
51111 51133

#### match *: Literal['contains', 'line', 'regex']*
51188 51210

#### target *: Literal['document', 'metadata']*
51305 51327

#### meta_name *: tuple[str, ...] | None*
51418 51440

### *class* outrage.store.SearchPage(matches: tuple[DocumentMatch, ...], matched: int, matched_chars: int, scanned: int, total_candidates: int, total_candidate_chars: int, next_cursor: str | None)
51630 51652

#### matches *: tuple[DocumentMatch, ...]*
52650 52672

#### matched *: int*
52783 52805

#### matched_chars *: int*
52861 52883

#### scanned *: int*
52945 52967

#### total_candidates *: int*
53023 53045

#### total_candidate_chars *: int*
53110 53132

#### next_cursor *: str | None*
53202 53224

### outrage.store.SearchTarget
53347 53369

### *class* outrage.store.Store(\*, log: EventLog | None = None, mount_point: str | None = None)
53544 53566

#### writable *: ClassVar[bool]* *= True*
54930 54952

#### writes_deferred *: ClassVar[bool]* *= False*
55575 55597

#### backend_name *: ClassVar[str]*
56120 56142

#### *abstractmethod* close() → None
56476 56498

#### *abstractmethod* store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
56853 56877

#### copy_from(source: Store, subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
59970 59996

#### located(key: str, format: str | None = None) → Path | None
65276 65304

#### *abstractmethod* delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
66214 66244

#### *abstractmethod* descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
69078 69110

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
70833 70867

#### *abstractmethod* exists(key: str) → bool
72834 72870

#### *abstractmethod* level_entry(key: str) → Entry | None
73344 73382

#### *abstractmethod* retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
74227 74267

#### *abstractmethod* list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None) → Page[Entry]
75939 75981

#### last_child(key: str) → str | None
77119 77163

#### *abstractmethod* get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
78832 78878

#### find_documents(subtree: BoundedSubtree = EVERYTHING, \*, criteria: Sequence[SearchCriterion], combine: Literal['any', 'all'] = 'any', key_range: KeyRange = UNBOUNDED, cursor: str | None = None, scan_limit: int | None = None) → SearchPage
81005 81053

#### *abstractmethod* missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
82253 82303

#### *abstractmethod* keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
84110 84162

### *exception* outrage.store.StoreFileError(code: str, \*\*details: Any)
85314 85368

### *class* outrage.store.Transfer(action: str, key: str | None, path: Path | None, reason: str | None = None, characters: int = 0, error: OutrageError | None = None)
86061 86115

#### action *: str*
88281 88335

#### key *: str | None*
88357 88411

#### path *: Path | None*
88494 88548

#### reason *: str | None*
88641 88695

#### characters *: int*
88781 88835

#### error *: OutrageError | None*
88862 88916

### outrage.store.default_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → FileStore
88996 89050

### outrage.store.default_store_file() → str
91203 91259

### outrage.store.entry_kind(key: str) → str
91858 91916

### outrage.store.meta_reader(scope: str) → Callable[[str, str | None, str | None], tuple[str | None, str | None]]
92531 92591

### outrage.store.open_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Iterator[FileStore]
94213 94275

### outrage.store.read_all(store: Store, key: str, \*\*kwargs: Any) → Excerpt
95508 95572

### outrage.store.resolve_directory(explicit: str | PathLike[str] | None = None) → Path
96512 96578

### outrage.store.store_file(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → Path
97056 97124
