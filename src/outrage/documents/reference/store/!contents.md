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

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, lock: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Self
31753 31759 520

#### opened_at(path: Path) → Self
35161 35169 558

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
35916 35926 572

#### verified_backup(target: Path) → Backup
37680 37692 599

#### backup_path(destination: str | PathLike[str] | None, \*, overwrite: bool) → Path
38695 38709 620

#### *abstract property* stored_format_version *: int*
39729 39745 634

#### *abstractmethod* audit_rows() → Iterator[AuditRow]
40302 40318 645

#### *abstractmethod* check_file(report: Report) → None
41072 41090 658

#### *abstractmethod* repair() → list[Repaired]
41849 41869 672

### outrage.store.Format
42640 42662 686

### *exception* outrage.store.InvalidArgumentError(code: str, \*\*details: Any)
43206 43228 697

### *exception* outrage.store.KeyNotFoundError(code: str, \*\*details: Any)
44536 44558 720

### *class* outrage.store.KeyRange(after: str | None = None, after_inclusive: str | None = None, after_subtree: str | None = None, before: str | None = None, before_inclusive: str | None = None, final_subtree: str | None = None)
44911 44933 726

#### after *: str | None*
47886 47908 764

#### after_inclusive *: str | None*
48027 48049 766

#### after_subtree *: str | None*
48178 48200 768

#### before *: str | None*
48327 48349 770

#### before_inclusive *: str | None*
48469 48491 772

#### final_subtree *: str | None*
48621 48643 774

### outrage.store.MatchMode
48770 48792 776

### *class* outrage.store.MatchWitness(criterion: int, source_key: str, source: Literal['document', 'metadata'], start: int, end: int, line: int = 1)
48980 49002 782

#### criterion *: int*
49612 49634 788

#### source_key *: str*
49693 49715 790

#### source *: Literal['document', 'metadata']*
49774 49796 792

#### start *: int*
49887 49909 794

#### end *: int*
49964 49986 796

#### line *: int*
50039 50061 798

### outrage.store.MetaReader
50174 50196 802

### *class* outrage.store.MissingMeta(total: int, total_chars: int, sample: list[str], selection_documents: int | None = None, selection_carried: dict[str, int] | None = None)
51105 51127 809

#### total *: int*
52221 52243 819

#### total_chars *: int*
52361 52383 823

#### sample *: list[str]*
52568 52590 828

#### selection_documents *: int | None*
52782 52804 832

#### selection_carried *: dict[str, int] | None*
53273 53295 840

### *class* outrage.store.Page(items: list[T], returned: int, total: int, total_chars: int, next_cursor: str | None)
54268 54290 857

#### items *: list[T]*
55201 55223 869

#### returned *: int*
55282 55304 871

#### total *: int*
55383 55405 875

#### total_chars *: int*
55528 55550 879

#### next_cursor *: str | None*
55838 55860 886

#### *property* truncated *: bool*
56046 56068 890

### *exception* outrage.store.PatternNotFoundError(code: str, \*\*details: Any)
56432 56454 899

### *exception* outrage.store.ReadOnlyStoreError(code: str, \*\*details: Any)
56834 56856 905

### outrage.store.SearchCombination
57707 57729 918

### *class* outrage.store.SearchCriterion(pattern: str, match: Literal['contains', 'line', 'regex'], target: Literal['document', 'metadata'], meta_name: tuple[str, ...] | None = None)
57904 57926 924

#### pattern *: str*
58568 58590 930

#### match *: Literal['contains', 'line', 'regex']*
58646 58668 932

#### target *: Literal['document', 'metadata']*
58763 58785 934

#### meta_name *: tuple[str, ...] | None*
58876 58898 936

### *class* outrage.store.SearchPage(matches: tuple[DocumentMatch, ...], matched: int, matched_chars: int, scanned: int, total_candidates: int, total_candidate_chars: int, next_cursor: str | None)
59091 59113 938

#### matches *: tuple[DocumentMatch, ...]*
60120 60142 948

#### matched *: int*
60254 60276 950

#### matched_chars *: int*
60333 60355 952

#### scanned *: int*
60418 60440 954

#### total_candidates *: int*
60497 60519 956

#### total_candidate_chars *: int*
60585 60607 958

#### next_cursor *: str | None*
60678 60700 960

### outrage.store.SearchTarget
60825 60847 962

### *class* outrage.store.Store(\*, log: EventLog | None = None, mount_point: str | None = None)
61022 61044 968

#### writable *: ClassVar[bool]* *= True*
62411 62433 991

#### versioned *: ClassVar[bool]* *= False*
63057 63079 1001

#### writes_deferred *: ClassVar[bool]* *= False*
63593 63615 1010

#### backend_name *: ClassVar[str]*
64139 64161 1018

#### *abstractmethod* close() → None
64496 64518 1024

#### *abstractmethod* store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
64874 64898 1033

#### copy_from(source: Store, subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
68147 68173 1079

#### located(key: str, format: str | None = None) → Path | None
73467 73495 1146

#### *abstractmethod* delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
74409 74439 1160

#### *abstractmethod* descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
77280 77312 1203

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
79038 79072 1233

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
81043 81079 1265

#### *abstractmethod* exists(key: str) → bool
83758 83796 1311

#### *abstractmethod* level_entry(key: str) → Entry | None
84270 84310 1322

#### *abstractmethod* retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
85155 85197 1337

#### *abstractmethod* list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
87299 87343 1359

#### last_child(key: str) → str | None
90449 90495 1406

#### *abstractmethod* get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
92165 92213 1436

#### find_documents(subtree: BoundedSubtree = EVERYTHING, \*, criteria: Sequence[SearchCriterion], combine: Literal['any', 'all'] = 'any', key_range: KeyRange = UNBOUNDED, cursor: str | None = None, scan_limit: int | None = None) → SearchPage
94348 94398 1462

#### *abstractmethod* missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
95600 95652 1475

#### *abstractmethod* keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
97747 97801 1504

### *exception* outrage.store.StoreFileError(code: str, \*\*details: Any)
98958 99014 1516

### *class* outrage.store.SubtreeTotals(keys: int, documents: int, chars: int | None)
99707 99763 1528

#### keys *: int*
100764 100820 1544

#### documents *: int*
101342 101398 1555

#### chars *: int | None*
101926 101982 1565

### *class* outrage.store.Transfer(action: str, key: str | None, path: Path | None, reason: str | None = None, characters: int = 0, error: OutrageError | None = None)
102465 102521 1574

#### action *: str*
105221 105277 1610

#### key *: str | None*
105298 105354 1612

#### path *: Path | None*
105437 105493 1614

#### reason *: str | None*
105585 105641 1616

#### characters *: int*
105727 105783 1618

#### error *: OutrageError | None*
105809 105865 1620

### outrage.store.default_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, lock: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → FileStore
105944 106000 1622

### outrage.store.default_store_file() → str
109152 109210 1652

### outrage.store.entry_kind(key: str) → str
109808 109868 1666

### outrage.store.is_pattern(filename: str | PathLike[str] | None) → bool
110483 110545 1679

### outrage.store.meta_reader(scope: str) → Callable[[str, str | None, str | None], tuple[str | None, str | None]]
111226 111290 1688

### outrage.store.open_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, lock: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Iterator[FileStore]
112919 112985 1706

### outrage.store.pattern_matches(directory: str | PathLike[str], filename: str | PathLike[str]) → list[Path]
114602 114670 1710

### outrage.store.read_all(store: Store, key: str, \*\*kwargs: Any) → Excerpt
115744 115814 1722

### outrage.store.resolve_directory(explicit: str | PathLike[str] | None = None) → Path
116756 116828 1738

### outrage.store.store_file(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → Path
117303 117377 1745

### outrage.store.store_present(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → bool
118911 118987 1771
