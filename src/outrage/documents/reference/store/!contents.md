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

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, lock: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Self
30566 30572

#### opened_at(path: Path) → Self
33974 33982

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
34729 34739

#### verified_backup(target: Path) → Backup
36493 36505

#### backup_path(destination: str | PathLike[str] | None, \*, overwrite: bool) → Path
37508 37522

#### *abstract property* stored_format_version *: int*
38542 38558

#### *abstractmethod* audit_rows() → Iterator[AuditRow]
39115 39131

#### *abstractmethod* check_file(report: Report) → None
39885 39903

#### *abstractmethod* repair() → list[Repaired]
40662 40682

### outrage.store.Format
41453 41475

### *exception* outrage.store.InvalidArgumentError(code: str, \*\*details: Any)
42019 42041

### *exception* outrage.store.KeyNotFoundError(code: str, \*\*details: Any)
43349 43371

### *class* outrage.store.KeyRange(after: str | None = None, after_inclusive: str | None = None, after_subtree: str | None = None, before: str | None = None, before_inclusive: str | None = None, final_subtree: str | None = None)
43724 43746

#### after *: str | None*
46699 46721

#### after_inclusive *: str | None*
46840 46862

#### after_subtree *: str | None*
46991 47013

#### before *: str | None*
47140 47162

#### before_inclusive *: str | None*
47282 47304

#### final_subtree *: str | None*
47434 47456

### outrage.store.MatchMode
47583 47605

### *class* outrage.store.MatchWitness(criterion: int, source_key: str, source: Literal['document', 'metadata'], start: int, end: int)
47793 47815

#### criterion *: int*
48353 48375

#### source_key *: str*
48434 48456

#### source *: Literal['document', 'metadata']*
48515 48537

#### start *: int*
48628 48650

#### end *: int*
48705 48727

### outrage.store.MetaReader
48780 48802

### *class* outrage.store.MissingMeta(total: int, total_chars: int, sample: list[str], selection_documents: int, selection_carried: dict[str, int])
49711 49733

#### total *: int*
50683 50705

#### total_chars *: int*
50823 50845

#### sample *: list[str]*
51030 51052

#### selection_documents *: int*
51244 51266

#### selection_carried *: dict[str, int]*
51621 51643

### *class* outrage.store.Page(items: list[T], returned: int, total: int, total_chars: int, next_cursor: str | None)
52501 52523

#### items *: list[T]*
53434 53456

#### returned *: int*
53515 53537

#### total *: int*
53616 53638

#### total_chars *: int*
53761 53783

#### next_cursor *: str | None*
54071 54093

#### *property* truncated *: bool*
54279 54301

### *exception* outrage.store.PatternNotFoundError(code: str, \*\*details: Any)
54665 54687

### *exception* outrage.store.ReadOnlyStoreError(code: str, \*\*details: Any)
55067 55089

### outrage.store.SearchCombination
55940 55962

### *class* outrage.store.SearchCriterion(pattern: str, match: Literal['contains', 'line', 'regex'], target: Literal['document', 'metadata'], meta_name: tuple[str, ...] | None = None)
56137 56159

#### pattern *: str*
56801 56823

#### match *: Literal['contains', 'line', 'regex']*
56879 56901

#### target *: Literal['document', 'metadata']*
56996 57018

#### meta_name *: tuple[str, ...] | None*
57109 57131

### *class* outrage.store.SearchPage(matches: tuple[DocumentMatch, ...], matched: int, matched_chars: int, scanned: int, total_candidates: int, total_candidate_chars: int, next_cursor: str | None)
57324 57346

#### matches *: tuple[DocumentMatch, ...]*
58353 58375

#### matched *: int*
58487 58509

#### matched_chars *: int*
58566 58588

#### scanned *: int*
58651 58673

#### total_candidates *: int*
58730 58752

#### total_candidate_chars *: int*
58818 58840

#### next_cursor *: str | None*
58911 58933

### outrage.store.SearchTarget
59058 59080

### *class* outrage.store.Store(\*, log: EventLog | None = None, mount_point: str | None = None)
59255 59277

#### writable *: ClassVar[bool]* *= True*
60644 60666

#### versioned *: ClassVar[bool]* *= False*
61290 61312

#### writes_deferred *: ClassVar[bool]* *= False*
61826 61848

#### backend_name *: ClassVar[str]*
62372 62394

#### *abstractmethod* close() → None
62729 62751

#### *abstractmethod* store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
63107 63131

#### copy_from(source: Store, subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
66380 66406

#### located(key: str, format: str | None = None) → Path | None
71700 71728

#### *abstractmethod* delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
72642 72672

#### *abstractmethod* descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
75513 75545

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
77271 77305

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
79276 79312

#### *abstractmethod* exists(key: str) → bool
81991 82029

#### *abstractmethod* level_entry(key: str) → Entry | None
82503 82543

#### *abstractmethod* retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
83388 83430

#### *abstractmethod* list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
85110 85154

#### last_child(key: str) → str | None
88260 88306

#### *abstractmethod* get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
89976 90024

#### find_documents(subtree: BoundedSubtree = EVERYTHING, \*, criteria: Sequence[SearchCriterion], combine: Literal['any', 'all'] = 'any', key_range: KeyRange = UNBOUNDED, cursor: str | None = None, scan_limit: int | None = None) → SearchPage
92159 92209

#### *abstractmethod* missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
93411 93463

#### *abstractmethod* keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
95271 95325

### *exception* outrage.store.StoreFileError(code: str, \*\*details: Any)
96482 96538

### *class* outrage.store.SubtreeTotals(keys: int, documents: int, chars: int | None)
97231 97287

#### keys *: int*
98288 98344

#### documents *: int*
98866 98922

#### chars *: int | None*
99450 99506

### *class* outrage.store.Transfer(action: str, key: str | None, path: Path | None, reason: str | None = None, characters: int = 0, error: OutrageError | None = None)
99989 100045

#### action *: str*
102745 102801

#### key *: str | None*
102822 102878

#### path *: Path | None*
102961 103017

#### reason *: str | None*
103109 103165

#### characters *: int*
103251 103307

#### error *: OutrageError | None*
103333 103389

### outrage.store.default_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, lock: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → FileStore
103468 103524

### outrage.store.default_store_file() → str
106676 106734

### outrage.store.entry_kind(key: str) → str
107332 107392

### outrage.store.is_pattern(filename: str | PathLike[str] | None) → bool
108007 108069

### outrage.store.meta_reader(scope: str) → Callable[[str, str | None, str | None], tuple[str | None, str | None]]
108750 108814

### outrage.store.open_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, lock: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Iterator[FileStore]
110443 110509

### outrage.store.pattern_matches(directory: str | PathLike[str], filename: str | PathLike[str]) → list[Path]
112126 112194

### outrage.store.read_all(store: Store, key: str, \*\*kwargs: Any) → Excerpt
113268 113338

### outrage.store.resolve_directory(explicit: str | PathLike[str] | None = None) → Path
114273 114345

### outrage.store.store_file(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → Path
114820 114894

### outrage.store.store_present(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → bool
116428 116504
