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

### outrage.store.VERSIONING_OFF *= 'off'*
11421 11427

### outrage.store.VERSIONING_ON *= 'on'*
11534 11540

### outrage.store.VERSIONING_SETTINGS *= ('on', 'off')*
11845 11851

### outrage.store.WROTE *= 'wrote'*
11951 11957

### *class* outrage.store.AuditRow(key: str, doc_key: str, meta_name: str | None, parent: str, chars: int)
12066 12072

#### key *: str*
13282 13288

#### doc_key *: str*
13355 13361

#### meta_name *: str | None*
13520 13526

#### parent *: str*
13714 13720

#### chars *: int*
13946 13952

### *class* outrage.store.Backup(path: Path, bytes: int, documents: int, integrity: str)
14022 14028

#### path *: Path*
14478 14484

#### bytes *: int*
14561 14567

#### documents *: int*
14637 14643

#### integrity *: str*
14779 14785

### *exception* outrage.store.BackendError(code: str, \*\*details: Any)
14916 14922

### *exception* outrage.store.BackupError(code: str, \*\*details: Any)
15335 15341

### *class* outrage.store.BoundedSubtree(key: str | None = None, depth: int | None = None)
15738 15744

#### key *: str | None*
16759 16765

#### depth *: int | None*
16896 16902

### *exception* outrage.store.ChangedSinceError(code: str, \*\*details: Any)
17036 17042

### *class* outrage.store.DocumentMatch(document: Entry, witnesses: tuple[MatchWitness, ...])
18112 18118

#### document *: Entry*
18459 18465

#### witnesses *: tuple[MatchWitness, ...]*
18508 18514

### outrage.store.Encoding
18641 18647

### *class* outrage.store.Entry(key: str, kind: str, size: int | None, format: str | None, updated_at: str | None, descendants: int | None = None, descendant_documents: int | None = None, descendant_chars: int | None = None)
18991 18997

#### key *: str*
20328 20334

#### kind *: str*
20401 20407

#### size *: int | None*
20576 20582

#### format *: str | None*
20715 20721

#### updated_at *: str | None*
20855 20861

#### descendants *: int | None*
20999 21005

#### descendant_documents *: int | None*
21324 21330

#### descendant_chars *: int | None*
21933 21939

### *class* outrage.store.Excerpt(key: str, content: str, format: str | None, updated_at: str, offset: int | None, returned: int, total: int | None, next_offset: int | None, byte_offset: int, total_bytes: int, next_byte_offset: int | None)
22144 22150

#### key *: str*
23398 23404

#### content *: str*
23471 23477

#### format *: str | None*
23548 23554

#### updated_at *: str*
23688 23694

#### offset *: int | None*
23768 23774

#### returned *: int*
24288 24294

#### total *: int | None*
24399 24405

#### next_offset *: int | None*
24745 24751

#### byte_offset *: int*
25046 25052

#### total_bytes *: int*
25403 25409

#### next_byte_offset *: int | None*
25531 25537

#### *property* truncated *: bool*
25832 25838

### *class* outrage.store.FileStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
26412 26418

#### default_filename *: ClassVar[str]*
28608 28614

#### format_version *: ClassVar[int]*
29160 29166

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, log: EventLog | None = None, mount_point: str | None = None) → Self
29759 29765

#### opened_at(path: Path) → Self
32787 32795

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
33542 33552

#### verified_backup(target: Path) → Backup
35302 35314

#### backup_path(destination: str | PathLike[str] | None, \*, overwrite: bool) → Path
36317 36331

#### *abstract property* stored_format_version *: int*
37347 37363

#### *abstractmethod* audit_rows() → Iterator[AuditRow]
37919 37935

#### *abstractmethod* check_file(report: Report) → None
38689 38707

#### *abstractmethod* repair() → list[Repaired]
39465 39485

### outrage.store.Format
40255 40277

### *exception* outrage.store.InvalidArgumentError(code: str, \*\*details: Any)
40821 40843

### *exception* outrage.store.KeyNotFoundError(code: str, \*\*details: Any)
42149 42171

### *class* outrage.store.KeyRange(after: str | None = None, after_inclusive: str | None = None, after_subtree: str | None = None, before: str | None = None, before_inclusive: str | None = None, final_subtree: str | None = None)
42522 42544

#### after *: str | None*
45484 45506

#### after_inclusive *: str | None*
45623 45645

#### after_subtree *: str | None*
45772 45794

#### before *: str | None*
45919 45941

#### before_inclusive *: str | None*
46059 46081

#### final_subtree *: str | None*
46209 46231

### outrage.store.MatchMode
46356 46378

### *class* outrage.store.MatchWitness(criterion: int, source_key: str, source: Literal['document', 'metadata'], start: int, end: int)
46566 46588

#### criterion *: int*
47121 47143

#### source_key *: str*
47201 47223

#### source *: Literal['document', 'metadata']*
47281 47303

#### start *: int*
47394 47416

#### end *: int*
47470 47492

### outrage.store.MetaReader
47544 47566

### *class* outrage.store.MissingMeta(total: int, total_chars: int, sample: list[str])
48465 48487

#### total *: int*
49144 49166

#### total_chars *: int*
49283 49305

#### sample *: list[str]*
49489 49511

### *class* outrage.store.Page(items: list[T], returned: int, total: int, total_chars: int, next_cursor: str | None)
49701 49723

#### items *: list[T]*
50628 50650

#### returned *: int*
50708 50730

#### total *: int*
50808 50830

#### total_chars *: int*
50952 50974

#### next_cursor *: str | None*
51261 51283

#### *property* truncated *: bool*
51467 51489

### *exception* outrage.store.PatternNotFoundError(code: str, \*\*details: Any)
51852 51874

### *exception* outrage.store.ReadOnlyStoreError(code: str, \*\*details: Any)
52252 52274

### outrage.store.SearchCombination
53123 53145

### *class* outrage.store.SearchCriterion(pattern: str, match: Literal['contains', 'line', 'regex'], target: Literal['document', 'metadata'], meta_name: tuple[str, ...] | None = None)
53320 53342

#### pattern *: str*
53979 54001

#### match *: Literal['contains', 'line', 'regex']*
54056 54078

#### target *: Literal['document', 'metadata']*
54173 54195

#### meta_name *: tuple[str, ...] | None*
54286 54308

### *class* outrage.store.SearchPage(matches: tuple[DocumentMatch, ...], matched: int, matched_chars: int, scanned: int, total_candidates: int, total_candidate_chars: int, next_cursor: str | None)
54498 54520

#### matches *: tuple[DocumentMatch, ...]*
55518 55540

#### matched *: int*
55651 55673

#### matched_chars *: int*
55729 55751

#### scanned *: int*
55813 55835

#### total_candidates *: int*
55891 55913

#### total_candidate_chars *: int*
55978 56000

#### next_cursor *: str | None*
56070 56092

### outrage.store.SearchTarget
56215 56237

### *class* outrage.store.Store(\*, log: EventLog | None = None, mount_point: str | None = None)
56412 56434

#### writable *: ClassVar[bool]* *= True*
57798 57820

#### versioned *: ClassVar[bool]* *= False*
58443 58465

#### writes_deferred *: ClassVar[bool]* *= False*
58978 59000

#### backend_name *: ClassVar[str]*
59523 59545

#### *abstractmethod* close() → None
59879 59901

#### *abstractmethod* store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
60256 60280

#### copy_from(source: Store, subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
63516 63542

#### located(key: str, format: str | None = None) → Path | None
68822 68850

#### *abstractmethod* delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
69760 69790

#### *abstractmethod* descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
72624 72656

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
74379 74413

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
76380 76416

#### *abstractmethod* exists(key: str) → bool
79093 79131

#### *abstractmethod* level_entry(key: str) → Entry | None
79603 79643

#### *abstractmethod* retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
80486 80528

#### *abstractmethod* list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
82198 82242

#### last_child(key: str) → str | None
85340 85386

#### *abstractmethod* get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
87053 87101

#### find_documents(subtree: BoundedSubtree = EVERYTHING, \*, criteria: Sequence[SearchCriterion], combine: Literal['any', 'all'] = 'any', key_range: KeyRange = UNBOUNDED, cursor: str | None = None, scan_limit: int | None = None) → SearchPage
89226 89276

#### *abstractmethod* missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
90474 90526

#### *abstractmethod* keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
92331 92385

### *exception* outrage.store.StoreFileError(code: str, \*\*details: Any)
93535 93591

### *class* outrage.store.SubtreeTotals(keys: int, documents: int, chars: int | None)
94282 94338

#### keys *: int*
95334 95390

#### documents *: int*
95911 95967

#### chars *: int | None*
96494 96550

### *class* outrage.store.Transfer(action: str, key: str | None, path: Path | None, reason: str | None = None, characters: int = 0, error: OutrageError | None = None)
97031 97087

#### action *: str*
99778 99834

#### key *: str | None*
99854 99910

#### path *: Path | None*
99991 100047

#### reason *: str | None*
100138 100194

#### characters *: int*
100278 100334

#### error *: OutrageError | None*
100359 100415

### outrage.store.default_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, log: EventLog | None = None, mount_point: str | None = None) → FileStore
100493 100549

### outrage.store.default_store_file() → str
103490 103548

### outrage.store.entry_kind(key: str) → str
104145 104205

### outrage.store.meta_reader(scope: str) → Callable[[str, str | None, str | None], tuple[str | None, str | None]]
104818 104880

### outrage.store.open_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, log: EventLog | None = None, mount_point: str | None = None) → Iterator[FileStore]
106500 106564

### outrage.store.read_all(store: Store, key: str, \*\*kwargs: Any) → Excerpt
108028 108094

### outrage.store.resolve_directory(explicit: str | PathLike[str] | None = None) → Path
109032 109100

### outrage.store.store_file(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → Path
109576 109646
