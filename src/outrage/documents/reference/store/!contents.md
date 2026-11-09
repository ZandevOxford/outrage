# outrage.store
0 0 1

### outrage.store.BACKUP_DIR_NAME *= 'backups'*
3347 3347 52

### outrage.store.BACKUP_STAMP *= '%Y%m%d-%H%M%S'*
3477 3477 57

### outrage.store.CHANGED *= 'changed'*
3752 3752 63

### outrage.store.CONFLICTS *= ('skip', 'overwrite', 'overwrite-unchanged', 'stop')*
4138 4138 70

### outrage.store.DEFAULT_BACKEND *= 'sqlite'*
4283 4283 74

### outrage.store.backend_for(filename: str | PathLike[str] | None = None, backend: str | None = None) → type[FileStore]
4526 4526 80

### outrage.store.backend_names() → tuple[str, ...]
5698 5700 95

### outrage.store.changed_since(stamp: str | None, watermark: str) → bool
6186 6190 104

### outrage.store.check_read_position(key: str, \*, offset: int, byte_offset: int | None, line: int | None, lines: int | None, pattern: str | None, occurrence: int) → None
7107 7113 118

### outrage.store.check_unchanged(opened: Store, key: str, unchanged_since: str | None, \*, action: str = 'write over', subtree: bool = True, key_range: KeyRange = UNBOUNDED) → None
8371 8379 128

### outrage.store.DEFAULT_BULK_MAX_CHARS *= 2000*
10376 10386 155

### outrage.store.DEFAULT_DIR_NAME *= '.outrage'*
10527 10537 160

### outrage.store.DEFAULT_MAX_CHARS *= 8000*
10683 10693 165

### outrage.store.ENCODINGS *: tuple[str, ...]* *= ('json-string',)*
10870 10880 170

### outrage.store.ENV_DIR *= 'OUTRAGE_DIR'*
11140 11150 174

### outrage.store.EVERYTHING *= BoundedSubtree(key=None, depth=None)*
11379 11389 180

### outrage.store.FAILED *= 'failed'*
11588 11598 185

### outrage.store.FORMATS *: tuple[str, ...]* *= ('markdown', 'json', 'text', 'html')*
11704 11714 189

### outrage.store.OVERWRITE *= 'overwrite'*
12210 12220 196

### outrage.store.OVERWRITE_UNCHANGED *= 'overwrite-unchanged'*
12287 12297 200

### outrage.store.READ *= 'read'*
12739 12749 208

### outrage.store.SKIP *= 'skip'*
13100 13110 215

### outrage.store.SKIPPED *= 'skipped'*
13266 13276 220

### outrage.store.STOP *= 'stop'*
13385 13395 224

### outrage.store.STOPPED *= 'stopped'*
13566 13576 229

### outrage.store.UNBOUNDED *= KeyRange(after=None, after_inclusive=None, after_subtree=None, before=None, before_inclusive=None, final_subtree=None)*
13803 13813 235

### outrage.store.VERSIONING_OFF *= 'off'*
14201 14211 241

### outrage.store.VERSIONING_ON *= 'on'*
14314 14324 245

### outrage.store.VERSIONING_SETTINGS *= ('on', 'off')*
14625 14635 252

### outrage.store.WROTE *= 'wrote'*
14731 14741 256

### *class* outrage.store.AuditRow(key: str, doc_key: str, meta_name: str | None, parent: str, chars: int)
14846 14856 260

#### key *: str*
16069 16079 276

#### doc_key *: str*
16143 16153 278

#### meta_name *: str | None*
16309 16319 283

#### parent *: str*
16505 16515 287

#### chars *: int*
16738 16748 292

### *class* outrage.store.Backup(path: Path, bytes: int, documents: int, integrity: str)
16815 16825 294

#### path *: Path*
17275 17285 300

#### bytes *: int*
17358 17368 302

#### documents *: int*
17435 17445 304

#### integrity *: str*
17578 17588 308

### *exception* outrage.store.BackendError(code: str, \*\*details: Any)
17716 17726 312

### *exception* outrage.store.BackupError(code: str, \*\*details: Any)
18137 18147 319

### *class* outrage.store.BoundedSubtree(key: str | None = None, depth: int | None = None)
18542 18552 325

#### key *: str | None*
19568 19578 341

#### depth *: int | None*
19707 19717 343

### *exception* outrage.store.ChangedSinceError(code: str, \*\*details: Any)
19849 19859 345

### *class* outrage.store.DocumentMatch(document: Entry, witnesses: tuple[MatchWitness, ...])
20927 20937 362

#### document *: Entry*
21276 21286 368

#### witnesses *: tuple[MatchWitness, ...]*
21325 21335 370

### outrage.store.Encoding
21459 21469 372

### *class* outrage.store.Entry(key: str, kind: str, size: int | None, format: str | None, updated_at: str | None, descendants: int | None = None, descendant_documents: int | None = None, descendant_chars: int | None = None)
21809 21819 380

#### key *: str*
23161 23171 390

#### kind *: str*
23235 23245 392

#### size *: int | None*
23411 23421 397

#### format *: str | None*
23552 23562 399

#### updated_at *: str | None*
23694 23704 401

#### descendants *: int | None*
23840 23850 403

#### descendant_documents *: int | None*
24167 24177 409

#### descendant_chars *: int | None*
24778 24788 418

### *class* outrage.store.Excerpt(key: str, content: str, format: str | None, updated_at: str, offset: int | None, returned: int, total: int | None, next_offset: int | None, byte_offset: int, total_bytes: int, next_byte_offset: int | None, line: int | None = None, next_line: int | None = None)
24991 25001 422

#### key *: str*
26547 26557 428

#### content *: str*
26621 26631 430

#### format *: str | None*
26699 26709 432

#### updated_at *: str*
26841 26851 434

#### offset *: int | None*
26922 26932 436

#### returned *: int*
27453 27463 445

#### total *: int | None*
27565 27575 449

#### next_offset *: int | None*
27922 27932 455

#### byte_offset *: int*
28225 28235 461

#### total_bytes *: int*
28583 28593 468

#### next_byte_offset *: int | None*
28712 28722 472

#### line *: int | None*
29015 29025 478

#### next_line *: int | None*
29294 29304 483

#### *property* truncated *: bool*
29632 29642 489

### *class* outrage.store.FileStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
30213 30223 502

#### default_filename *: ClassVar[str]*
32418 32428 528

#### format_version *: ClassVar[int]*
32971 32981 536

#### reads_patterns *: ClassVar[bool]* *= False*
33571 33581 544

#### locates_own_store *: ClassVar[bool]* *= False*
33995 34005 551

#### manages_schema *: ClassVar[bool]* *= False*
35016 35026 568

#### *property* target *: dict[str, str] | None*
36095 36105 587

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, create: bool = True) → Self
36697 36707 596

#### *classmethod* reporting(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None) → Self
41005 41017 646

#### opened_at(path: Path) → Self
43028 43042 668

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
43783 43799 682

#### verified_backup(target: Path) → Backup
45547 45565 709

#### backup_path(destination: str | PathLike[str] | None, \*, overwrite: bool) → Path
46562 46582 730

#### *property* backup_suffix *: str*
47630 47652 744

#### *abstract property* stored_format_version *: int*
48003 48025 753

#### *abstractmethod* audit_rows() → Iterator[AuditRow]
48576 48598 764

#### *abstractmethod* check_file(report: Report) → None
49346 49370 777

#### *abstractmethod* repair() → list[Repaired]
50123 50149 791

### outrage.store.Format
50914 50942 805

### *exception* outrage.store.InvalidArgumentError(code: str, \*\*details: Any)
51480 51508 816

### *exception* outrage.store.KeyNotFoundError(code: str, \*\*details: Any)
52810 52838 839

### *class* outrage.store.KeyRange(after: str | None = None, after_inclusive: str | None = None, after_subtree: str | None = None, before: str | None = None, before_inclusive: str | None = None, final_subtree: str | None = None)
53185 53213 845

#### after *: str | None*
56160 56188 883

#### after_inclusive *: str | None*
56301 56329 885

#### after_subtree *: str | None*
56452 56480 887

#### before *: str | None*
56601 56629 889

#### before_inclusive *: str | None*
56743 56771 891

#### final_subtree *: str | None*
56895 56923 893

### outrage.store.MatchMode
57044 57072 895

### *class* outrage.store.MatchWitness(criterion: int, source_key: str, source: Literal['document', 'metadata'], start: int, end: int, line: int = 1)
57254 57282 901

#### criterion *: int*
57886 57914 907

#### source_key *: str*
57967 57995 909

#### source *: Literal['document', 'metadata']*
58048 58076 911

#### start *: int*
58161 58189 913

#### end *: int*
58238 58266 915

#### line *: int*
58313 58341 917

### outrage.store.MetaReader
58448 58476 921

### *class* outrage.store.MissingMeta(total: int, total_chars: int, sample: list[str], selection_documents: int | None = None, selection_carried: dict[str, int] | None = None)
59379 59407 928

#### total *: int*
60495 60523 938

#### total_chars *: int*
60635 60663 942

#### sample *: list[str]*
60842 60870 947

#### selection_documents *: int | None*
61056 61084 951

#### selection_carried *: dict[str, int] | None*
61547 61575 959

### *class* outrage.store.Page(items: list[T], returned: int, total: int, total_chars: int, next_cursor: str | None, unavailable: tuple[str, ...] = ())
62542 62570 976

#### items *: list[T]*
63624 63652 988

#### returned *: int*
63705 63733 990

#### total *: int*
63806 63834 994

#### total_chars *: int*
63951 63979 998

#### next_cursor *: str | None*
64261 64289 1005

#### unavailable *: tuple[str, ...]*
64469 64497 1009

#### *property* truncated *: bool*
64856 64884 1016

### *exception* outrage.store.PatternNotFoundError(code: str, \*\*details: Any)
65242 65270 1025

### *exception* outrage.store.ReadOnlyStoreError(code: str, \*\*details: Any)
65644 65672 1031

### outrage.store.SearchCombination
66517 66545 1044

### *class* outrage.store.SearchCriterion(pattern: str, match: Literal['contains', 'line', 'regex'], target: Literal['document', 'metadata'], meta_name: tuple[str, ...] | None = None)
66714 66742 1050

#### pattern *: str*
67378 67406 1056

#### match *: Literal['contains', 'line', 'regex']*
67456 67484 1058

#### target *: Literal['document', 'metadata']*
67573 67601 1060

#### meta_name *: tuple[str, ...] | None*
67686 67714 1062

### *class* outrage.store.SearchPage(matches: tuple[DocumentMatch, ...], matched: int, matched_chars: int, scanned: int, total_candidates: int, total_candidate_chars: int, next_cursor: str | None, unavailable: tuple[str, ...] = ())
67901 67929 1064

#### matches *: tuple[DocumentMatch, ...]*
69079 69107 1074

#### matched *: int*
69213 69241 1076

#### matched_chars *: int*
69292 69320 1078

#### scanned *: int*
69377 69405 1080

#### total_candidates *: int*
69456 69484 1082

#### total_candidate_chars *: int*
69544 69572 1084

#### next_cursor *: str | None*
69637 69665 1086

#### unavailable *: tuple[str, ...]*
69784 69812 1088

### outrage.store.SearchTarget
70036 70064 1092

### *class* outrage.store.Store(\*, log: EventLog | None = None, mount_point: str | None = None)
70233 70261 1098

#### writable *: ClassVar[bool]* *= True*
71622 71650 1121

#### versioned *: ClassVar[bool]* *= False*
72268 72296 1131

#### writes_deferred *: ClassVar[bool]* *= False*
72804 72832 1140

#### backend_name *: ClassVar[str]*
73350 73378 1148

#### *abstractmethod* close() → None
73707 73735 1154

#### *abstractmethod* store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
74085 74115 1163

#### copy_from(source: Store, subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
77358 77390 1209

#### located(key: str, format: str | None = None) → Path | None
82678 82712 1276

#### *abstractmethod* delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
83620 83656 1290

#### *abstractmethod* descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
86491 86529 1333

#### now(key: str = keys.ROOT, \*, key_range: KeyRange = UNBOUNDED) → str
88249 88289 1363

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
89015 89057 1375

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
91137 91181 1409

#### *abstractmethod* exists(key: str) → bool
93852 93898 1455

#### *abstractmethod* level_entry(key: str) → Entry | None
94364 94412 1466

#### *abstractmethod* retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
95249 95299 1481

#### *abstractmethod* list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
97393 97445 1503

#### last_child(key: str) → str | None
100543 100597 1550

#### *abstractmethod* get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
102259 102315 1580

#### find_documents(subtree: BoundedSubtree = EVERYTHING, \*, criteria: Sequence[SearchCriterion], combine: Literal['any', 'all'] = 'any', key_range: KeyRange = UNBOUNDED, cursor: str | None = None, scan_limit: int | None = None) → SearchPage
104442 104500 1606

#### *abstractmethod* missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
105694 105754 1619

#### *abstractmethod* keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
107841 107903 1648

### *exception* outrage.store.StoreFileError(code: str, \*\*details: Any)
109052 109116 1660

### *class* outrage.store.SchemaState(backend: str, service: str, path: Path, schema: str, stored: SchemaVersion | None, oldest: int, newest: int, operating: int | None, writable: bool, problem: Refusal | None = None)
109801 109865 1672

#### backend *: str*
111726 111790 1692

#### service *: str*
111864 111928 1696

#### path *: Path*
111992 112056 1700

#### schema *: str*
112119 112183 1704

#### stored *: SchemaVersion | None*
112259 112323 1708

#### oldest *: int*
112452 112516 1712

#### newest *: int*
112574 112638 1716

#### operating *: int | None*
112719 112783 1720

#### writable *: bool*
112932 112996 1724

#### problem *: Refusal | None*
113072 113136 1728

### *class* outrage.store.SchemaVersion(version: int, read_floor: int, write_floor: int)
113263 113327 1732

#### version *: int*
113961 114025 1743

#### read_floor *: int*
114040 114104 1745

#### write_floor *: int*
114122 114186 1747

### *class* outrage.store.SubtreeTotals(keys: int, documents: int, chars: int | None)
114205 114269 1749

#### keys *: int*
115262 115326 1765

#### documents *: int*
115840 115904 1776

#### chars *: int | None*
116424 116488 1786

### *class* outrage.store.Transfer(action: str, key: str | None, path: Path | None, reason: str | None = None, characters: int = 0, error: OutrageError | None = None)
116963 117027 1795

#### action *: str*
119719 119783 1831

#### key *: str | None*
119796 119860 1833

#### path *: Path | None*
119935 119999 1835

#### reason *: str | None*
120083 120147 1837

#### characters *: int*
120225 120289 1839

#### error *: OutrageError | None*
120307 120371 1841

### outrage.store.default_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, create: bool = True) → FileStore
120442 120506 1843

### outrage.store.default_store_file() → str
124018 124084 1876

### outrage.store.entry_kind(key: str) → str
124674 124742 1890

### outrage.store.is_pattern(filename: str | PathLike[str] | None) → bool
125349 125419 1903

### outrage.store.locates_own_store(backend: str | None = None, \*, unknown: bool | None = None) → bool
126092 126164 1912

### outrage.store.meta_reader(scope: str) → Callable[[str, str | None, str | None], tuple[str | None, str | None]]
128021 128095 1940

### outrage.store.open_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Iterator[FileStore]
129714 129790 1958

### outrage.store.pattern_matches(directory: str | PathLike[str], filename: str | PathLike[str]) → list[Path]
131539 131617 1962

### outrage.store.read_all(store: Store, key: str, \*\*kwargs: Any) → Excerpt
132681 132761 1974

### outrage.store.resolve_directory(explicit: str | PathLike[str] | None = None) → Path
133693 133775 1990

### outrage.store.store_file(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → Path
134240 134324 1997

### outrage.store.store_present(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → bool
135848 135934 2023
