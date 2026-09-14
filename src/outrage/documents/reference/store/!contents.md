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
4790 4792

### outrage.store.check_unchanged(opened: Store, key: str, unchanged_since: str | None, \*, action: str = 'write over', subtree: bool = True, key_range: KeyRange = UNBOUNDED) → None
5787 5791

### outrage.store.DEFAULT_BULK_MAX_CHARS *= 2000*
7792 7798

### outrage.store.DEFAULT_DIR_NAME *= '.outrage'*
7943 7949

### outrage.store.DEFAULT_MAX_CHARS *= 8000*
8099 8105

### outrage.store.ENCODINGS *: tuple[str, ...]* *= ('json-string',)*
8286 8292

### outrage.store.ENV_DIR *= 'OUTRAGE_DIR'*
8556 8562

### outrage.store.EVERYTHING *= BoundedSubtree(key=None, depth=None)*
8795 8801

### outrage.store.FAILED *= 'failed'*
9004 9010

### outrage.store.FORMATS *: tuple[str, ...]* *= ('markdown', 'json', 'text', 'html')*
9120 9126

### outrage.store.OVERWRITE *= 'overwrite'*
9626 9632

### outrage.store.OVERWRITE_UNCHANGED *= 'overwrite-unchanged'*
9703 9709

### outrage.store.READ *= 'read'*
10155 10161

### outrage.store.SKIP *= 'skip'*
10516 10522

### outrage.store.SKIPPED *= 'skipped'*
10682 10688

### outrage.store.STOP *= 'stop'*
10801 10807

### outrage.store.STOPPED *= 'stopped'*
10982 10988

### outrage.store.UNBOUNDED *= KeyRange(after=None, after_inclusive=None, after_subtree=None, before=None, before_inclusive=None, final_subtree=None)*
11219 11225

### outrage.store.VERSIONING_OFF *= 'off'*
11617 11623

### outrage.store.VERSIONING_ON *= 'on'*
11730 11736

### outrage.store.VERSIONING_SETTINGS *= ('on', 'off')*
12041 12047

### outrage.store.WROTE *= 'wrote'*
12147 12153

### *class* outrage.store.AuditRow(key: str, doc_key: str, meta_name: str | None, parent: str, chars: int)
12262 12268

#### key *: str*
13485 13491

#### doc_key *: str*
13559 13565

#### meta_name *: str | None*
13725 13731

#### parent *: str*
13921 13927

#### chars *: int*
14154 14160

### *class* outrage.store.Backup(path: Path, bytes: int, documents: int, integrity: str)
14231 14237

#### path *: Path*
14691 14697

#### bytes *: int*
14774 14780

#### documents *: int*
14851 14857

#### integrity *: str*
14994 15000

### *exception* outrage.store.BackendError(code: str, \*\*details: Any)
15132 15138

### *exception* outrage.store.BackupError(code: str, \*\*details: Any)
15553 15559

### *class* outrage.store.BoundedSubtree(key: str | None = None, depth: int | None = None)
15958 15964

#### key *: str | None*
16984 16990

#### depth *: int | None*
17123 17129

### *exception* outrage.store.ChangedSinceError(code: str, \*\*details: Any)
17265 17271

### *class* outrage.store.DocumentMatch(document: Entry, witnesses: tuple[MatchWitness, ...])
18343 18349

#### document *: Entry*
18692 18698

#### witnesses *: tuple[MatchWitness, ...]*
18741 18747

### outrage.store.Encoding
18875 18881

### *class* outrage.store.Entry(key: str, kind: str, size: int | None, format: str | None, updated_at: str | None, descendants: int | None = None, descendant_documents: int | None = None, descendant_chars: int | None = None)
19225 19231

#### key *: str*
20577 20583

#### kind *: str*
20651 20657

#### size *: int | None*
20827 20833

#### format *: str | None*
20968 20974

#### updated_at *: str | None*
21110 21116

#### descendants *: int | None*
21256 21262

#### descendant_documents *: int | None*
21583 21589

#### descendant_chars *: int | None*
22194 22200

### *class* outrage.store.Excerpt(key: str, content: str, format: str | None, updated_at: str, offset: int | None, returned: int, total: int | None, next_offset: int | None, byte_offset: int, total_bytes: int, next_byte_offset: int | None)
22407 22413

#### key *: str*
23678 23684

#### content *: str*
23752 23758

#### format *: str | None*
23830 23836

#### updated_at *: str*
23972 23978

#### offset *: int | None*
24053 24059

#### returned *: int*
24575 24581

#### total *: int | None*
24687 24693

#### next_offset *: int | None*
25035 25041

#### byte_offset *: int*
25338 25344

#### total_bytes *: int*
25696 25702

#### next_byte_offset *: int | None*
25825 25831

#### *property* truncated *: bool*
26128 26134

### *class* outrage.store.FileStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
26709 26715

#### default_filename *: ClassVar[str]*
28914 28920

#### format_version *: ClassVar[int]*
29467 29473

#### reads_patterns *: ClassVar[bool]* *= False*
30067 30073

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, log: EventLog | None = None, mount_point: str | None = None) → Self
30491 30497

#### opened_at(path: Path) → Self
33532 33540

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
34287 34297

#### verified_backup(target: Path) → Backup
36051 36063

#### backup_path(destination: str | PathLike[str] | None, \*, overwrite: bool) → Path
37066 37080

#### *abstract property* stored_format_version *: int*
38100 38116

#### *abstractmethod* audit_rows() → Iterator[AuditRow]
38673 38689

#### *abstractmethod* check_file(report: Report) → None
39443 39461

#### *abstractmethod* repair() → list[Repaired]
40220 40240

### outrage.store.Format
41011 41033

### *exception* outrage.store.InvalidArgumentError(code: str, \*\*details: Any)
41577 41599

### *exception* outrage.store.KeyNotFoundError(code: str, \*\*details: Any)
42907 42929

### *class* outrage.store.KeyRange(after: str | None = None, after_inclusive: str | None = None, after_subtree: str | None = None, before: str | None = None, before_inclusive: str | None = None, final_subtree: str | None = None)
43282 43304

#### after *: str | None*
46257 46279

#### after_inclusive *: str | None*
46398 46420

#### after_subtree *: str | None*
46549 46571

#### before *: str | None*
46698 46720

#### before_inclusive *: str | None*
46840 46862

#### final_subtree *: str | None*
46992 47014

### outrage.store.MatchMode
47141 47163

### *class* outrage.store.MatchWitness(criterion: int, source_key: str, source: Literal['document', 'metadata'], start: int, end: int)
47351 47373

#### criterion *: int*
47911 47933

#### source_key *: str*
47992 48014

#### source *: Literal['document', 'metadata']*
48073 48095

#### start *: int*
48186 48208

#### end *: int*
48263 48285

### outrage.store.MetaReader
48338 48360

### *class* outrage.store.MissingMeta(total: int, total_chars: int, sample: list[str])
49269 49291

#### total *: int*
49953 49975

#### total_chars *: int*
50093 50115

#### sample *: list[str]*
50300 50322

### *class* outrage.store.Page(items: list[T], returned: int, total: int, total_chars: int, next_cursor: str | None)
50514 50536

#### items *: list[T]*
51447 51469

#### returned *: int*
51528 51550

#### total *: int*
51629 51651

#### total_chars *: int*
51774 51796

#### next_cursor *: str | None*
52084 52106

#### *property* truncated *: bool*
52292 52314

### *exception* outrage.store.PatternNotFoundError(code: str, \*\*details: Any)
52678 52700

### *exception* outrage.store.ReadOnlyStoreError(code: str, \*\*details: Any)
53080 53102

### outrage.store.SearchCombination
53953 53975

### *class* outrage.store.SearchCriterion(pattern: str, match: Literal['contains', 'line', 'regex'], target: Literal['document', 'metadata'], meta_name: tuple[str, ...] | None = None)
54150 54172

#### pattern *: str*
54814 54836

#### match *: Literal['contains', 'line', 'regex']*
54892 54914

#### target *: Literal['document', 'metadata']*
55009 55031

#### meta_name *: tuple[str, ...] | None*
55122 55144

### *class* outrage.store.SearchPage(matches: tuple[DocumentMatch, ...], matched: int, matched_chars: int, scanned: int, total_candidates: int, total_candidate_chars: int, next_cursor: str | None)
55337 55359

#### matches *: tuple[DocumentMatch, ...]*
56366 56388

#### matched *: int*
56500 56522

#### matched_chars *: int*
56579 56601

#### scanned *: int*
56664 56686

#### total_candidates *: int*
56743 56765

#### total_candidate_chars *: int*
56831 56853

#### next_cursor *: str | None*
56924 56946

### outrage.store.SearchTarget
57071 57093

### *class* outrage.store.Store(\*, log: EventLog | None = None, mount_point: str | None = None)
57268 57290

#### writable *: ClassVar[bool]* *= True*
58657 58679

#### versioned *: ClassVar[bool]* *= False*
59303 59325

#### writes_deferred *: ClassVar[bool]* *= False*
59839 59861

#### backend_name *: ClassVar[str]*
60385 60407

#### *abstractmethod* close() → None
60742 60764

#### *abstractmethod* store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
61120 61144

#### copy_from(source: Store, subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
64393 64419

#### located(key: str, format: str | None = None) → Path | None
69713 69741

#### *abstractmethod* delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
70655 70685

#### *abstractmethod* descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
73526 73558

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
75284 75318

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
77289 77325

#### *abstractmethod* exists(key: str) → bool
80004 80042

#### *abstractmethod* level_entry(key: str) → Entry | None
80516 80556

#### *abstractmethod* retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
81401 81443

#### *abstractmethod* list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
83123 83167

#### last_child(key: str) → str | None
86273 86319

#### *abstractmethod* get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
87989 88037

#### find_documents(subtree: BoundedSubtree = EVERYTHING, \*, criteria: Sequence[SearchCriterion], combine: Literal['any', 'all'] = 'any', key_range: KeyRange = UNBOUNDED, cursor: str | None = None, scan_limit: int | None = None) → SearchPage
90172 90222

#### *abstractmethod* missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
91424 91476

#### *abstractmethod* keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
93284 93338

### *exception* outrage.store.StoreFileError(code: str, \*\*details: Any)
94495 94551

### *class* outrage.store.SubtreeTotals(keys: int, documents: int, chars: int | None)
95244 95300

#### keys *: int*
96301 96357

#### documents *: int*
96879 96935

#### chars *: int | None*
97463 97519

### *class* outrage.store.Transfer(action: str, key: str | None, path: Path | None, reason: str | None = None, characters: int = 0, error: OutrageError | None = None)
98002 98058

#### action *: str*
100758 100814

#### key *: str | None*
100835 100891

#### path *: Path | None*
100974 101030

#### reason *: str | None*
101122 101178

#### characters *: int*
101264 101320

#### error *: OutrageError | None*
101346 101402

### outrage.store.default_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, log: EventLog | None = None, mount_point: str | None = None) → FileStore
101481 101537

### outrage.store.default_store_file() → str
104494 104552

### outrage.store.entry_kind(key: str) → str
105150 105210

### outrage.store.is_pattern(filename: str | PathLike[str] | None) → bool
105825 105887

### outrage.store.meta_reader(scope: str) → Callable[[str, str | None, str | None], tuple[str | None, str | None]]
106568 106632

### outrage.store.open_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, log: EventLog | None = None, mount_point: str | None = None) → Iterator[FileStore]
108261 108327

### outrage.store.pattern_matches(directory: str | PathLike[str], filename: str | PathLike[str]) → list[Path]
109805 109873

### outrage.store.read_all(store: Store, key: str, \*\*kwargs: Any) → Excerpt
110947 111017

### outrage.store.resolve_directory(explicit: str | PathLike[str] | None = None) → Path
111952 112024

### outrage.store.store_file(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → Path
112499 112573

### outrage.store.store_present(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → bool
114107 114183
