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

### outrage.store.backend_names() → tuple[str, ...]
4377 4377 78

### outrage.store.check_read_position(key: str, \*, offset: int, byte_offset: int | None, line: int | None, lines: int | None, pattern: str | None, occurrence: int) → None
4865 4867 87

### outrage.store.check_unchanged(opened: Store, key: str, unchanged_since: str | None, \*, action: str = 'write over', subtree: bool = True, key_range: KeyRange = UNBOUNDED) → None
6129 6133 97

### outrage.store.DEFAULT_BULK_MAX_CHARS *= 2000*
8134 8140 124

### outrage.store.DEFAULT_DIR_NAME *= '.outrage'*
8285 8291 129

### outrage.store.DEFAULT_MAX_CHARS *= 8000*
8441 8447 134

### outrage.store.ENCODINGS *: tuple[str, ...]* *= ('json-string',)*
8628 8634 139

### outrage.store.ENV_DIR *= 'OUTRAGE_DIR'*
8898 8904 143

### outrage.store.EVERYTHING *= BoundedSubtree(key=None, depth=None)*
9137 9143 149

### outrage.store.FAILED *= 'failed'*
9346 9352 154

### outrage.store.FORMATS *: tuple[str, ...]* *= ('markdown', 'json', 'text', 'html')*
9462 9468 158

### outrage.store.OVERWRITE *= 'overwrite'*
9968 9974 165

### outrage.store.OVERWRITE_UNCHANGED *= 'overwrite-unchanged'*
10045 10051 169

### outrage.store.READ *= 'read'*
10497 10503 177

### outrage.store.SKIP *= 'skip'*
10858 10864 184

### outrage.store.SKIPPED *= 'skipped'*
11024 11030 189

### outrage.store.STOP *= 'stop'*
11143 11149 193

### outrage.store.STOPPED *= 'stopped'*
11324 11330 198

### outrage.store.UNBOUNDED *= KeyRange(after=None, after_inclusive=None, after_subtree=None, before=None, before_inclusive=None, final_subtree=None)*
11561 11567 204

### outrage.store.VERSIONING_OFF *= 'off'*
11959 11965 210

### outrage.store.VERSIONING_ON *= 'on'*
12072 12078 214

### outrage.store.VERSIONING_SETTINGS *= ('on', 'off')*
12383 12389 221

### outrage.store.WROTE *= 'wrote'*
12489 12495 225

### *class* outrage.store.AuditRow(key: str, doc_key: str, meta_name: str | None, parent: str, chars: int)
12604 12610 229

#### key *: str*
13827 13833 245

#### doc_key *: str*
13901 13907 247

#### meta_name *: str | None*
14067 14073 252

#### parent *: str*
14263 14269 256

#### chars *: int*
14496 14502 261

### *class* outrage.store.Backup(path: Path, bytes: int, documents: int, integrity: str)
14573 14579 263

#### path *: Path*
15033 15039 269

#### bytes *: int*
15116 15122 271

#### documents *: int*
15193 15199 273

#### integrity *: str*
15336 15342 277

### *exception* outrage.store.BackendError(code: str, \*\*details: Any)
15474 15480 281

### *exception* outrage.store.BackupError(code: str, \*\*details: Any)
15895 15901 288

### *class* outrage.store.BoundedSubtree(key: str | None = None, depth: int | None = None)
16300 16306 294

#### key *: str | None*
17326 17332 310

#### depth *: int | None*
17465 17471 312

### *exception* outrage.store.ChangedSinceError(code: str, \*\*details: Any)
17607 17613 314

### *class* outrage.store.DocumentMatch(document: Entry, witnesses: tuple[MatchWitness, ...])
18685 18691 331

#### document *: Entry*
19034 19040 337

#### witnesses *: tuple[MatchWitness, ...]*
19083 19089 339

### outrage.store.Encoding
19217 19223 341

### *class* outrage.store.Entry(key: str, kind: str, size: int | None, format: str | None, updated_at: str | None, descendants: int | None = None, descendant_documents: int | None = None, descendant_chars: int | None = None)
19567 19573 349

#### key *: str*
20919 20925 359

#### kind *: str*
20993 20999 361

#### size *: int | None*
21169 21175 366

#### format *: str | None*
21310 21316 368

#### updated_at *: str | None*
21452 21458 370

#### descendants *: int | None*
21598 21604 372

#### descendant_documents *: int | None*
21925 21931 378

#### descendant_chars *: int | None*
22536 22542 387

### *class* outrage.store.Excerpt(key: str, content: str, format: str | None, updated_at: str, offset: int | None, returned: int, total: int | None, next_offset: int | None, byte_offset: int, total_bytes: int, next_byte_offset: int | None, line: int | None = None, next_line: int | None = None)
22749 22755 391

#### key *: str*
24305 24311 397

#### content *: str*
24379 24385 399

#### format *: str | None*
24457 24463 401

#### updated_at *: str*
24599 24605 403

#### offset *: int | None*
24680 24686 405

#### returned *: int*
25211 25217 414

#### total *: int | None*
25323 25329 418

#### next_offset *: int | None*
25680 25686 424

#### byte_offset *: int*
25983 25989 430

#### total_bytes *: int*
26341 26347 437

#### next_byte_offset *: int | None*
26470 26476 441

#### line *: int | None*
26773 26779 447

#### next_line *: int | None*
27052 27058 452

#### *property* truncated *: bool*
27390 27396 458

### *class* outrage.store.FileStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
27971 27977 471

#### default_filename *: ClassVar[str]*
30176 30182 497

#### format_version *: ClassVar[int]*
30729 30735 505

#### reads_patterns *: ClassVar[bool]* *= False*
31329 31335 513

#### locates_own_store *: ClassVar[bool]* *= False*
31753 31759 520

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Self
32774 32780 537

#### opened_at(path: Path) → Self
36522 36530 579

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
37277 37287 593

#### verified_backup(target: Path) → Backup
39041 39053 620

#### backup_path(destination: str | PathLike[str] | None, \*, overwrite: bool) → Path
40056 40070 641

#### *abstract property* stored_format_version *: int*
41090 41106 655

#### *abstractmethod* audit_rows() → Iterator[AuditRow]
41663 41679 666

#### *abstractmethod* check_file(report: Report) → None
42433 42451 679

#### *abstractmethod* repair() → list[Repaired]
43210 43230 693

### outrage.store.Format
44001 44023 707

### *exception* outrage.store.InvalidArgumentError(code: str, \*\*details: Any)
44567 44589 718

### *exception* outrage.store.KeyNotFoundError(code: str, \*\*details: Any)
45897 45919 741

### *class* outrage.store.KeyRange(after: str | None = None, after_inclusive: str | None = None, after_subtree: str | None = None, before: str | None = None, before_inclusive: str | None = None, final_subtree: str | None = None)
46272 46294 747

#### after *: str | None*
49247 49269 785

#### after_inclusive *: str | None*
49388 49410 787

#### after_subtree *: str | None*
49539 49561 789

#### before *: str | None*
49688 49710 791

#### before_inclusive *: str | None*
49830 49852 793

#### final_subtree *: str | None*
49982 50004 795

### outrage.store.MatchMode
50131 50153 797

### *class* outrage.store.MatchWitness(criterion: int, source_key: str, source: Literal['document', 'metadata'], start: int, end: int, line: int = 1)
50341 50363 803

#### criterion *: int*
50973 50995 809

#### source_key *: str*
51054 51076 811

#### source *: Literal['document', 'metadata']*
51135 51157 813

#### start *: int*
51248 51270 815

#### end *: int*
51325 51347 817

#### line *: int*
51400 51422 819

### outrage.store.MetaReader
51535 51557 823

### *class* outrage.store.MissingMeta(total: int, total_chars: int, sample: list[str], selection_documents: int | None = None, selection_carried: dict[str, int] | None = None)
52466 52488 830

#### total *: int*
53582 53604 840

#### total_chars *: int*
53722 53744 844

#### sample *: list[str]*
53929 53951 849

#### selection_documents *: int | None*
54143 54165 853

#### selection_carried *: dict[str, int] | None*
54634 54656 861

### *class* outrage.store.Page(items: list[T], returned: int, total: int, total_chars: int, next_cursor: str | None)
55629 55651 878

#### items *: list[T]*
56562 56584 890

#### returned *: int*
56643 56665 892

#### total *: int*
56744 56766 896

#### total_chars *: int*
56889 56911 900

#### next_cursor *: str | None*
57199 57221 907

#### *property* truncated *: bool*
57407 57429 911

### *exception* outrage.store.PatternNotFoundError(code: str, \*\*details: Any)
57793 57815 920

### *exception* outrage.store.ReadOnlyStoreError(code: str, \*\*details: Any)
58195 58217 926

### outrage.store.SearchCombination
59068 59090 939

### *class* outrage.store.SearchCriterion(pattern: str, match: Literal['contains', 'line', 'regex'], target: Literal['document', 'metadata'], meta_name: tuple[str, ...] | None = None)
59265 59287 945

#### pattern *: str*
59929 59951 951

#### match *: Literal['contains', 'line', 'regex']*
60007 60029 953

#### target *: Literal['document', 'metadata']*
60124 60146 955

#### meta_name *: tuple[str, ...] | None*
60237 60259 957

### *class* outrage.store.SearchPage(matches: tuple[DocumentMatch, ...], matched: int, matched_chars: int, scanned: int, total_candidates: int, total_candidate_chars: int, next_cursor: str | None)
60452 60474 959

#### matches *: tuple[DocumentMatch, ...]*
61481 61503 969

#### matched *: int*
61615 61637 971

#### matched_chars *: int*
61694 61716 973

#### scanned *: int*
61779 61801 975

#### total_candidates *: int*
61858 61880 977

#### total_candidate_chars *: int*
61946 61968 979

#### next_cursor *: str | None*
62039 62061 981

### outrage.store.SearchTarget
62186 62208 983

### *class* outrage.store.Store(\*, log: EventLog | None = None, mount_point: str | None = None)
62383 62405 989

#### writable *: ClassVar[bool]* *= True*
63772 63794 1012

#### versioned *: ClassVar[bool]* *= False*
64418 64440 1022

#### writes_deferred *: ClassVar[bool]* *= False*
64954 64976 1031

#### backend_name *: ClassVar[str]*
65500 65522 1039

#### *abstractmethod* close() → None
65857 65879 1045

#### *abstractmethod* store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
66235 66259 1054

#### copy_from(source: Store, subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
69508 69534 1100

#### located(key: str, format: str | None = None) → Path | None
74828 74856 1167

#### *abstractmethod* delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
75770 75800 1181

#### *abstractmethod* descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
78641 78673 1224

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
80399 80433 1254

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
82404 82440 1286

#### *abstractmethod* exists(key: str) → bool
85119 85157 1332

#### *abstractmethod* level_entry(key: str) → Entry | None
85631 85671 1343

#### *abstractmethod* retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
86516 86558 1358

#### *abstractmethod* list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
88660 88704 1380

#### last_child(key: str) → str | None
91810 91856 1427

#### *abstractmethod* get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
93526 93574 1457

#### find_documents(subtree: BoundedSubtree = EVERYTHING, \*, criteria: Sequence[SearchCriterion], combine: Literal['any', 'all'] = 'any', key_range: KeyRange = UNBOUNDED, cursor: str | None = None, scan_limit: int | None = None) → SearchPage
95709 95759 1483

#### *abstractmethod* missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
96961 97013 1496

#### *abstractmethod* keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
99108 99162 1525

### *exception* outrage.store.StoreFileError(code: str, \*\*details: Any)
100319 100375 1537

### *class* outrage.store.SubtreeTotals(keys: int, documents: int, chars: int | None)
101068 101124 1549

#### keys *: int*
102125 102181 1565

#### documents *: int*
102703 102759 1576

#### chars *: int | None*
103287 103343 1586

### *class* outrage.store.Transfer(action: str, key: str | None, path: Path | None, reason: str | None = None, characters: int = 0, error: OutrageError | None = None)
103826 103882 1595

#### action *: str*
106582 106638 1631

#### key *: str | None*
106659 106715 1633

#### path *: Path | None*
106798 106854 1635

#### reason *: str | None*
106946 107002 1637

#### characters *: int*
107088 107144 1639

#### error *: OutrageError | None*
107170 107226 1641

### outrage.store.default_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → FileStore
107305 107361 1643

### outrage.store.default_store_file() → str
110670 110728 1673

### outrage.store.entry_kind(key: str) → str
111326 111386 1687

### outrage.store.is_pattern(filename: str | PathLike[str] | None) → bool
112001 112063 1700

### outrage.store.locates_own_store(backend: str | None = None) → bool
112744 112808 1709

### outrage.store.meta_reader(scope: str) → Callable[[str, str | None, str | None], tuple[str | None, str | None]]
113718 113784 1725

### outrage.store.open_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Iterator[FileStore]
115411 115479 1743

### outrage.store.pattern_matches(directory: str | PathLike[str], filename: str | PathLike[str]) → list[Path]
117236 117306 1747

### outrage.store.read_all(store: Store, key: str, \*\*kwargs: Any) → Excerpt
118378 118450 1759

### outrage.store.resolve_directory(explicit: str | PathLike[str] | None = None) → Path
119390 119464 1775

### outrage.store.store_file(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → Path
119937 120013 1782

### outrage.store.store_present(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → bool
121545 121623 1808
