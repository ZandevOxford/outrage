# outrage.store
0 0

### outrage.store.BACKUP_DIR_NAME *= 'backups'*
3198 3198

### outrage.store.BACKUP_STAMP *= '%Y%m%d-%H%M%S'*
3328 3328

### outrage.store.CHANGED *= 'changed'*
3603 3603

### outrage.store.CONFLICTS *= ('skip', 'overwrite', 'overwrite-unchanged', 'stop')*
3989 3989

### outrage.store.DEFAULT_BACKEND *= 'sqlite'*
4134 4134

### outrage.store.backend_names() → tuple[str, ...]
4377 4377

### outrage.store.check_read_position(key: str, \*, offset: int, byte_offset: int | None, pattern: str | None, occurrence: int) → None
4865 4867

### outrage.store.check_unchanged(opened: Store, key: str, unchanged_since: str | None, \*, action: str = 'write over', subtree: bool = True, key_range: KeyRange = UNBOUNDED) → None
5862 5866

### outrage.store.DEFAULT_BULK_MAX_CHARS *= 2000*
7867 7873

### outrage.store.DEFAULT_DIR_NAME *= '.outrage'*
8018 8024

### outrage.store.DEFAULT_MAX_CHARS *= 8000*
8174 8180

### outrage.store.ENCODINGS *: tuple[str, ...]* *= ('json-string',)*
8361 8367

### outrage.store.ENV_DIR *= 'OUTRAGE_DIR'*
8631 8637

### outrage.store.EVERYTHING *= BoundedSubtree(key=None, depth=None)*
8870 8876

### outrage.store.FAILED *= 'failed'*
9079 9085

### outrage.store.FORMATS *: tuple[str, ...]* *= ('markdown', 'json', 'text', 'html')*
9195 9201

### outrage.store.OVERWRITE *= 'overwrite'*
9701 9707

### outrage.store.OVERWRITE_UNCHANGED *= 'overwrite-unchanged'*
9778 9784

### outrage.store.READ *= 'read'*
10230 10236

### outrage.store.SKIP *= 'skip'*
10591 10597

### outrage.store.SKIPPED *= 'skipped'*
10757 10763

### outrage.store.STOP *= 'stop'*
10876 10882

### outrage.store.STOPPED *= 'stopped'*
11057 11063

### outrage.store.UNBOUNDED *= KeyRange(after=None, after_inclusive=None, after_subtree=None, before=None, before_inclusive=None, final_subtree=None)*
11294 11300

### outrage.store.VERSIONING_OFF *= 'off'*
11692 11698

### outrage.store.VERSIONING_ON *= 'on'*
11805 11811

### outrage.store.VERSIONING_SETTINGS *= ('on', 'off')*
12116 12122

### outrage.store.WROTE *= 'wrote'*
12222 12228

### *class* outrage.store.AuditRow(key: str, doc_key: str, meta_name: str | None, parent: str, chars: int)
12337 12343

#### key *: str*
13560 13566

#### doc_key *: str*
13634 13640

#### meta_name *: str | None*
13800 13806

#### parent *: str*
13996 14002

#### chars *: int*
14229 14235

### *class* outrage.store.Backup(path: Path, bytes: int, documents: int, integrity: str)
14306 14312

#### path *: Path*
14766 14772

#### bytes *: int*
14849 14855

#### documents *: int*
14926 14932

#### integrity *: str*
15069 15075

### *exception* outrage.store.BackendError(code: str, \*\*details: Any)
15207 15213

### *exception* outrage.store.BackupError(code: str, \*\*details: Any)
15628 15634

### *class* outrage.store.BoundedSubtree(key: str | None = None, depth: int | None = None)
16033 16039

#### key *: str | None*
17059 17065

#### depth *: int | None*
17198 17204

### *exception* outrage.store.ChangedSinceError(code: str, \*\*details: Any)
17340 17346

### *class* outrage.store.DocumentMatch(document: Entry, witnesses: tuple[MatchWitness, ...])
18418 18424

#### document *: Entry*
18767 18773

#### witnesses *: tuple[MatchWitness, ...]*
18816 18822

### outrage.store.Encoding
18950 18956

### *class* outrage.store.Entry(key: str, kind: str, size: int | None, format: str | None, updated_at: str | None, descendants: int | None = None, descendant_documents: int | None = None, descendant_chars: int | None = None)
19300 19306

#### key *: str*
20652 20658

#### kind *: str*
20726 20732

#### size *: int | None*
20902 20908

#### format *: str | None*
21043 21049

#### updated_at *: str | None*
21185 21191

#### descendants *: int | None*
21331 21337

#### descendant_documents *: int | None*
21658 21664

#### descendant_chars *: int | None*
22269 22275

### *class* outrage.store.Excerpt(key: str, content: str, format: str | None, updated_at: str, offset: int | None, returned: int, total: int | None, next_offset: int | None, byte_offset: int, total_bytes: int, next_byte_offset: int | None)
22482 22488

#### key *: str*
23753 23759

#### content *: str*
23827 23833

#### format *: str | None*
23905 23911

#### updated_at *: str*
24047 24053

#### offset *: int | None*
24128 24134

#### returned *: int*
24650 24656

#### total *: int | None*
24762 24768

#### next_offset *: int | None*
25110 25116

#### byte_offset *: int*
25413 25419

#### total_bytes *: int*
25771 25777

#### next_byte_offset *: int | None*
25900 25906

#### *property* truncated *: bool*
26203 26209

### *class* outrage.store.FileStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
26784 26790

#### default_filename *: ClassVar[str]*
28989 28995

#### format_version *: ClassVar[int]*
29542 29548

#### reads_patterns *: ClassVar[bool]* *= False*
30142 30148

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, log: EventLog | None = None, mount_point: str | None = None) → Self
30566 30572

#### opened_at(path: Path) → Self
33607 33615

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
34362 34372

#### verified_backup(target: Path) → Backup
36126 36138

#### backup_path(destination: str | PathLike[str] | None, \*, overwrite: bool) → Path
37141 37155

#### *abstract property* stored_format_version *: int*
38175 38191

#### *abstractmethod* audit_rows() → Iterator[AuditRow]
38748 38764

#### *abstractmethod* check_file(report: Report) → None
39518 39536

#### *abstractmethod* repair() → list[Repaired]
40295 40315

### outrage.store.Format
41086 41108

### *exception* outrage.store.InvalidArgumentError(code: str, \*\*details: Any)
41652 41674

### *exception* outrage.store.KeyNotFoundError(code: str, \*\*details: Any)
42982 43004

### *class* outrage.store.KeyRange(after: str | None = None, after_inclusive: str | None = None, after_subtree: str | None = None, before: str | None = None, before_inclusive: str | None = None, final_subtree: str | None = None)
43357 43379

#### after *: str | None*
46332 46354

#### after_inclusive *: str | None*
46473 46495

#### after_subtree *: str | None*
46624 46646

#### before *: str | None*
46773 46795

#### before_inclusive *: str | None*
46915 46937

#### final_subtree *: str | None*
47067 47089

### outrage.store.MatchMode
47216 47238

### *class* outrage.store.MatchWitness(criterion: int, source_key: str, source: Literal['document', 'metadata'], start: int, end: int)
47426 47448

#### criterion *: int*
47986 48008

#### source_key *: str*
48067 48089

#### source *: Literal['document', 'metadata']*
48148 48170

#### start *: int*
48261 48283

#### end *: int*
48338 48360

### outrage.store.MetaReader
48413 48435

### *class* outrage.store.MissingMeta(total: int, total_chars: int, sample: list[str])
49344 49366

#### total *: int*
50028 50050

#### total_chars *: int*
50168 50190

#### sample *: list[str]*
50375 50397

### *class* outrage.store.Page(items: list[T], returned: int, total: int, total_chars: int, next_cursor: str | None)
50589 50611

#### items *: list[T]*
51522 51544

#### returned *: int*
51603 51625

#### total *: int*
51704 51726

#### total_chars *: int*
51849 51871

#### next_cursor *: str | None*
52159 52181

#### *property* truncated *: bool*
52367 52389

### *exception* outrage.store.PatternNotFoundError(code: str, \*\*details: Any)
52753 52775

### *exception* outrage.store.ReadOnlyStoreError(code: str, \*\*details: Any)
53155 53177

### outrage.store.SearchCombination
54028 54050

### *class* outrage.store.SearchCriterion(pattern: str, match: Literal['contains', 'line', 'regex'], target: Literal['document', 'metadata'], meta_name: tuple[str, ...] | None = None)
54225 54247

#### pattern *: str*
54889 54911

#### match *: Literal['contains', 'line', 'regex']*
54967 54989

#### target *: Literal['document', 'metadata']*
55084 55106

#### meta_name *: tuple[str, ...] | None*
55197 55219

### *class* outrage.store.SearchPage(matches: tuple[DocumentMatch, ...], matched: int, matched_chars: int, scanned: int, total_candidates: int, total_candidate_chars: int, next_cursor: str | None)
55412 55434

#### matches *: tuple[DocumentMatch, ...]*
56441 56463

#### matched *: int*
56575 56597

#### matched_chars *: int*
56654 56676

#### scanned *: int*
56739 56761

#### total_candidates *: int*
56818 56840

#### total_candidate_chars *: int*
56906 56928

#### next_cursor *: str | None*
56999 57021

### outrage.store.SearchTarget
57146 57168

### *class* outrage.store.Store(\*, log: EventLog | None = None, mount_point: str | None = None)
57343 57365

#### writable *: ClassVar[bool]* *= True*
58732 58754

#### versioned *: ClassVar[bool]* *= False*
59378 59400

#### writes_deferred *: ClassVar[bool]* *= False*
59914 59936

#### backend_name *: ClassVar[str]*
60460 60482

#### *abstractmethod* close() → None
60817 60839

#### *abstractmethod* store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
61195 61219

#### copy_from(source: Store, subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
64468 64494

#### located(key: str, format: str | None = None) → Path | None
69788 69816

#### *abstractmethod* delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
70730 70760

#### *abstractmethod* descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
73601 73633

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
75359 75393

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
77364 77400

#### *abstractmethod* exists(key: str) → bool
80079 80117

#### *abstractmethod* level_entry(key: str) → Entry | None
80591 80631

#### *abstractmethod* retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
81476 81518

#### *abstractmethod* list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
83198 83242

#### last_child(key: str) → str | None
86348 86394

#### *abstractmethod* get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
88064 88112

#### find_documents(subtree: BoundedSubtree = EVERYTHING, \*, criteria: Sequence[SearchCriterion], combine: Literal['any', 'all'] = 'any', key_range: KeyRange = UNBOUNDED, cursor: str | None = None, scan_limit: int | None = None) → SearchPage
90247 90297

#### *abstractmethod* missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
91499 91551

#### *abstractmethod* keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
93359 93413

### *exception* outrage.store.StoreFileError(code: str, \*\*details: Any)
94570 94626

### *class* outrage.store.SubtreeTotals(keys: int, documents: int, chars: int | None)
95319 95375

#### keys *: int*
96376 96432

#### documents *: int*
96954 97010

#### chars *: int | None*
97538 97594

### *class* outrage.store.Transfer(action: str, key: str | None, path: Path | None, reason: str | None = None, characters: int = 0, error: OutrageError | None = None)
98077 98133

#### action *: str*
100833 100889

#### key *: str | None*
100910 100966

#### path *: Path | None*
101049 101105

#### reason *: str | None*
101197 101253

#### characters *: int*
101339 101395

#### error *: OutrageError | None*
101421 101477

### outrage.store.default_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, log: EventLog | None = None, mount_point: str | None = None) → FileStore
101556 101612

### outrage.store.default_store_file() → str
104569 104627

### outrage.store.entry_kind(key: str) → str
105225 105285

### outrage.store.is_pattern(filename: str | PathLike[str] | None) → bool
105900 105962

### outrage.store.meta_reader(scope: str) → Callable[[str, str | None, str | None], tuple[str | None, str | None]]
106643 106707

### outrage.store.open_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, log: EventLog | None = None, mount_point: str | None = None) → Iterator[FileStore]
108336 108402

### outrage.store.pattern_matches(directory: str | PathLike[str], filename: str | PathLike[str]) → list[Path]
109880 109948

### outrage.store.read_all(store: Store, key: str, \*\*kwargs: Any) → Excerpt
111022 111092

### outrage.store.resolve_directory(explicit: str | PathLike[str] | None = None) → Path
112027 112099

### outrage.store.store_file(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → Path
112574 112648

### outrage.store.store_present(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → bool
114182 114258
