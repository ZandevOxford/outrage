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
18461 18467

#### key *: str*
19143 19149

#### kind *: str*
19216 19222

#### size *: int | None*
19391 19397

#### format *: str | None*
19530 19536

#### updated_at *: str | None*
19670 19676

### *class* outrage.store.Excerpt(key: str, content: str, format: str | None, updated_at: str, offset: int | None, returned: int, total: int | None, next_offset: int | None, byte_offset: int, total_bytes: int, next_byte_offset: int | None)
19814 19820

#### key *: str*
21068 21074

#### content *: str*
21141 21147

#### format *: str | None*
21218 21224

#### updated_at *: str*
21358 21364

#### offset *: int | None*
21438 21444

#### returned *: int*
21958 21964

#### total *: int | None*
22069 22075

#### next_offset *: int | None*
22415 22421

#### byte_offset *: int*
22716 22722

#### total_bytes *: int*
23073 23079

#### next_byte_offset *: int | None*
23201 23207

#### *property* truncated *: bool*
23502 23508

### *class* outrage.store.FileStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
24082 24088

#### default_filename *: ClassVar[str]*
26278 26284

#### format_version *: ClassVar[int]*
26830 26836

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Self
27429 27435

#### opened_at(path: Path) → Self
29929 29937

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
30684 30694

#### verified_backup(target: Path) → Backup
32444 32456

#### backup_path(destination: str | PathLike[str] | None, \*, overwrite: bool) → Path
33459 33473

#### *abstract property* stored_format_version *: int*
34489 34505

#### *abstractmethod* audit_rows() → Iterator[AuditRow]
35061 35077

#### *abstractmethod* check_file(report: Report) → None
35831 35849

#### *abstractmethod* repair() → list[Repaired]
36607 36627

### outrage.store.Format
37397 37419

### *exception* outrage.store.InvalidArgumentError(code: str, \*\*details: Any)
37963 37985

### *exception* outrage.store.KeyNotFoundError(code: str, \*\*details: Any)
39291 39313

### *class* outrage.store.KeyRange(after: str | None = None, after_inclusive: str | None = None, after_subtree: str | None = None, before: str | None = None, before_inclusive: str | None = None, final_subtree: str | None = None)
39664 39686

#### after *: str | None*
42626 42648

#### after_inclusive *: str | None*
42765 42787

#### after_subtree *: str | None*
42914 42936

#### before *: str | None*
43061 43083

#### before_inclusive *: str | None*
43201 43223

#### final_subtree *: str | None*
43351 43373

### outrage.store.MatchMode
43498 43520

### *class* outrage.store.MatchWitness(criterion: int, source_key: str, source: Literal['document', 'metadata'], start: int, end: int)
43708 43730

#### criterion *: int*
44263 44285

#### source_key *: str*
44343 44365

#### source *: Literal['document', 'metadata']*
44423 44445

#### start *: int*
44536 44558

#### end *: int*
44612 44634

### outrage.store.MetaReader
44686 44708

### *class* outrage.store.MissingMeta(total: int, total_chars: int, sample: list[str])
45607 45629

#### total *: int*
46286 46308

#### total_chars *: int*
46425 46447

#### sample *: list[str]*
46631 46653

### *class* outrage.store.Page(items: list[T], returned: int, total: int, total_chars: int, next_cursor: str | None)
46843 46865

#### items *: list[T]*
47770 47792

#### returned *: int*
47850 47872

#### total *: int*
47950 47972

#### total_chars *: int*
48094 48116

#### next_cursor *: str | None*
48403 48425

#### *property* truncated *: bool*
48609 48631

### *exception* outrage.store.PatternNotFoundError(code: str, \*\*details: Any)
48994 49016

### *exception* outrage.store.ReadOnlyStoreError(code: str, \*\*details: Any)
49394 49416

### outrage.store.SearchCombination
50265 50287

### *class* outrage.store.SearchCriterion(pattern: str, match: Literal['contains', 'line', 'regex'], target: Literal['document', 'metadata'], meta_name: tuple[str, ...] | None = None)
50462 50484

#### pattern *: str*
51121 51143

#### match *: Literal['contains', 'line', 'regex']*
51198 51220

#### target *: Literal['document', 'metadata']*
51315 51337

#### meta_name *: tuple[str, ...] | None*
51428 51450

### *class* outrage.store.SearchPage(matches: tuple[DocumentMatch, ...], matched: int, matched_chars: int, scanned: int, total_candidates: int, total_candidate_chars: int, next_cursor: str | None)
51640 51662

#### matches *: tuple[DocumentMatch, ...]*
52660 52682

#### matched *: int*
52793 52815

#### matched_chars *: int*
52871 52893

#### scanned *: int*
52955 52977

#### total_candidates *: int*
53033 53055

#### total_candidate_chars *: int*
53120 53142

#### next_cursor *: str | None*
53212 53234

### outrage.store.SearchTarget
53357 53379

### *class* outrage.store.Store(\*, log: EventLog | None = None, mount_point: str | None = None)
53554 53576

#### writable *: ClassVar[bool]* *= True*
54940 54962

#### writes_deferred *: ClassVar[bool]* *= False*
55585 55607

#### backend_name *: ClassVar[str]*
56130 56152

#### *abstractmethod* close() → None
56486 56508

#### *abstractmethod* store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
56863 56887

#### copy_from(source: Store, subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
60123 60149

#### located(key: str, format: str | None = None) → Path | None
65429 65457

#### *abstractmethod* delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
66367 66397

#### *abstractmethod* descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
69231 69263

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
70986 71020

#### *abstractmethod* exists(key: str) → bool
72987 73023

#### *abstractmethod* level_entry(key: str) → Entry | None
73497 73535

#### *abstractmethod* retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
74380 74420

#### *abstractmethod* list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None) → Page[Entry]
76092 76134

#### last_child(key: str) → str | None
77272 77316

#### *abstractmethod* get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
78985 79031

#### find_documents(subtree: BoundedSubtree = EVERYTHING, \*, criteria: Sequence[SearchCriterion], combine: Literal['any', 'all'] = 'any', key_range: KeyRange = UNBOUNDED, cursor: str | None = None, scan_limit: int | None = None) → SearchPage
81158 81206

#### *abstractmethod* missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
82406 82456

#### *abstractmethod* keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
84263 84315

### *exception* outrage.store.StoreFileError(code: str, \*\*details: Any)
85467 85521

### *class* outrage.store.Transfer(action: str, key: str | None, path: Path | None, reason: str | None = None, characters: int = 0, error: OutrageError | None = None)
86214 86268

#### action *: str*
88434 88488

#### key *: str | None*
88510 88564

#### path *: Path | None*
88647 88701

#### reason *: str | None*
88794 88848

#### characters *: int*
88934 88988

#### error *: OutrageError | None*
89015 89069

### outrage.store.default_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → FileStore
89149 89203

### outrage.store.default_store_file() → str
91356 91412

### outrage.store.entry_kind(key: str) → str
92011 92069

### outrage.store.meta_reader(scope: str) → Callable[[str, str | None, str | None], tuple[str | None, str | None]]
92684 92744

### outrage.store.open_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Iterator[FileStore]
94366 94428

### outrage.store.read_all(store: Store, key: str, \*\*kwargs: Any) → Excerpt
95661 95725

### outrage.store.resolve_directory(explicit: str | PathLike[str] | None = None) → Path
96665 96731

### outrage.store.store_file(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → Path
97209 97277
