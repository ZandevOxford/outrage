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

### outrage.store.backend_for(filename: str | PathLike[str] | None = None, backend: str | None = None) → type[FileStore]
4377 4377 78

### outrage.store.backend_names() → tuple[str, ...]
5549 5551 93

### outrage.store.check_read_position(key: str, \*, offset: int, byte_offset: int | None, line: int | None, lines: int | None, pattern: str | None, occurrence: int) → None
6037 6041 102

### outrage.store.check_unchanged(opened: Store, key: str, unchanged_since: str | None, \*, action: str = 'write over', subtree: bool = True, key_range: KeyRange = UNBOUNDED) → None
7301 7307 112

### outrage.store.DEFAULT_BULK_MAX_CHARS *= 2000*
9306 9314 139

### outrage.store.DEFAULT_DIR_NAME *= '.outrage'*
9457 9465 144

### outrage.store.DEFAULT_MAX_CHARS *= 8000*
9613 9621 149

### outrage.store.ENCODINGS *: tuple[str, ...]* *= ('json-string',)*
9800 9808 154

### outrage.store.ENV_DIR *= 'OUTRAGE_DIR'*
10070 10078 158

### outrage.store.EVERYTHING *= BoundedSubtree(key=None, depth=None)*
10309 10317 164

### outrage.store.FAILED *= 'failed'*
10518 10526 169

### outrage.store.FORMATS *: tuple[str, ...]* *= ('markdown', 'json', 'text', 'html')*
10634 10642 173

### outrage.store.OVERWRITE *= 'overwrite'*
11140 11148 180

### outrage.store.OVERWRITE_UNCHANGED *= 'overwrite-unchanged'*
11217 11225 184

### outrage.store.READ *= 'read'*
11669 11677 192

### outrage.store.SKIP *= 'skip'*
12030 12038 199

### outrage.store.SKIPPED *= 'skipped'*
12196 12204 204

### outrage.store.STOP *= 'stop'*
12315 12323 208

### outrage.store.STOPPED *= 'stopped'*
12496 12504 213

### outrage.store.UNBOUNDED *= KeyRange(after=None, after_inclusive=None, after_subtree=None, before=None, before_inclusive=None, final_subtree=None)*
12733 12741 219

### outrage.store.VERSIONING_OFF *= 'off'*
13131 13139 225

### outrage.store.VERSIONING_ON *= 'on'*
13244 13252 229

### outrage.store.VERSIONING_SETTINGS *= ('on', 'off')*
13555 13563 236

### outrage.store.WROTE *= 'wrote'*
13661 13669 240

### *class* outrage.store.AuditRow(key: str, doc_key: str, meta_name: str | None, parent: str, chars: int)
13776 13784 244

#### key *: str*
14999 15007 260

#### doc_key *: str*
15073 15081 262

#### meta_name *: str | None*
15239 15247 267

#### parent *: str*
15435 15443 271

#### chars *: int*
15668 15676 276

### *class* outrage.store.Backup(path: Path, bytes: int, documents: int, integrity: str)
15745 15753 278

#### path *: Path*
16205 16213 284

#### bytes *: int*
16288 16296 286

#### documents *: int*
16365 16373 288

#### integrity *: str*
16508 16516 292

### *exception* outrage.store.BackendError(code: str, \*\*details: Any)
16646 16654 296

### *exception* outrage.store.BackupError(code: str, \*\*details: Any)
17067 17075 303

### *class* outrage.store.BoundedSubtree(key: str | None = None, depth: int | None = None)
17472 17480 309

#### key *: str | None*
18498 18506 325

#### depth *: int | None*
18637 18645 327

### *exception* outrage.store.ChangedSinceError(code: str, \*\*details: Any)
18779 18787 329

### *class* outrage.store.DocumentMatch(document: Entry, witnesses: tuple[MatchWitness, ...])
19857 19865 346

#### document *: Entry*
20206 20214 352

#### witnesses *: tuple[MatchWitness, ...]*
20255 20263 354

### outrage.store.Encoding
20389 20397 356

### *class* outrage.store.Entry(key: str, kind: str, size: int | None, format: str | None, updated_at: str | None, descendants: int | None = None, descendant_documents: int | None = None, descendant_chars: int | None = None)
20739 20747 364

#### key *: str*
22091 22099 374

#### kind *: str*
22165 22173 376

#### size *: int | None*
22341 22349 381

#### format *: str | None*
22482 22490 383

#### updated_at *: str | None*
22624 22632 385

#### descendants *: int | None*
22770 22778 387

#### descendant_documents *: int | None*
23097 23105 393

#### descendant_chars *: int | None*
23708 23716 402

### *class* outrage.store.Excerpt(key: str, content: str, format: str | None, updated_at: str, offset: int | None, returned: int, total: int | None, next_offset: int | None, byte_offset: int, total_bytes: int, next_byte_offset: int | None, line: int | None = None, next_line: int | None = None)
23921 23929 406

#### key *: str*
25477 25485 412

#### content *: str*
25551 25559 414

#### format *: str | None*
25629 25637 416

#### updated_at *: str*
25771 25779 418

#### offset *: int | None*
25852 25860 420

#### returned *: int*
26383 26391 429

#### total *: int | None*
26495 26503 433

#### next_offset *: int | None*
26852 26860 439

#### byte_offset *: int*
27155 27163 445

#### total_bytes *: int*
27513 27521 452

#### next_byte_offset *: int | None*
27642 27650 456

#### line *: int | None*
27945 27953 462

#### next_line *: int | None*
28224 28232 467

#### *property* truncated *: bool*
28562 28570 473

### *class* outrage.store.FileStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
29143 29151 486

#### default_filename *: ClassVar[str]*
31348 31356 512

#### format_version *: ClassVar[int]*
31901 31909 520

#### reads_patterns *: ClassVar[bool]* *= False*
32501 32509 528

#### locates_own_store *: ClassVar[bool]* *= False*
32925 32933 535

#### manages_schema *: ClassVar[bool]* *= False*
33946 33954 552

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Self
35025 35033 571

#### *classmethod* reporting(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None) → Self
38773 38783 613

#### opened_at(path: Path) → Self
40796 40808 635

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
41551 41565 649

#### verified_backup(target: Path) → Backup
43315 43331 676

#### backup_path(destination: str | PathLike[str] | None, \*, overwrite: bool) → Path
44330 44348 697

#### *abstract property* stored_format_version *: int*
45364 45384 711

#### *abstractmethod* audit_rows() → Iterator[AuditRow]
45937 45957 722

#### *abstractmethod* check_file(report: Report) → None
46707 46729 735

#### *abstractmethod* repair() → list[Repaired]
47484 47508 749

### outrage.store.Format
48275 48301 763

### *exception* outrage.store.InvalidArgumentError(code: str, \*\*details: Any)
48841 48867 774

### *exception* outrage.store.KeyNotFoundError(code: str, \*\*details: Any)
50171 50197 797

### *class* outrage.store.KeyRange(after: str | None = None, after_inclusive: str | None = None, after_subtree: str | None = None, before: str | None = None, before_inclusive: str | None = None, final_subtree: str | None = None)
50546 50572 803

#### after *: str | None*
53521 53547 841

#### after_inclusive *: str | None*
53662 53688 843

#### after_subtree *: str | None*
53813 53839 845

#### before *: str | None*
53962 53988 847

#### before_inclusive *: str | None*
54104 54130 849

#### final_subtree *: str | None*
54256 54282 851

### outrage.store.MatchMode
54405 54431 853

### *class* outrage.store.MatchWitness(criterion: int, source_key: str, source: Literal['document', 'metadata'], start: int, end: int, line: int = 1)
54615 54641 859

#### criterion *: int*
55247 55273 865

#### source_key *: str*
55328 55354 867

#### source *: Literal['document', 'metadata']*
55409 55435 869

#### start *: int*
55522 55548 871

#### end *: int*
55599 55625 873

#### line *: int*
55674 55700 875

### outrage.store.MetaReader
55809 55835 879

### *class* outrage.store.MissingMeta(total: int, total_chars: int, sample: list[str], selection_documents: int | None = None, selection_carried: dict[str, int] | None = None)
56740 56766 886

#### total *: int*
57856 57882 896

#### total_chars *: int*
57996 58022 900

#### sample *: list[str]*
58203 58229 905

#### selection_documents *: int | None*
58417 58443 909

#### selection_carried *: dict[str, int] | None*
58908 58934 917

### *class* outrage.store.Page(items: list[T], returned: int, total: int, total_chars: int, next_cursor: str | None)
59903 59929 934

#### items *: list[T]*
60836 60862 946

#### returned *: int*
60917 60943 948

#### total *: int*
61018 61044 952

#### total_chars *: int*
61163 61189 956

#### next_cursor *: str | None*
61473 61499 963

#### *property* truncated *: bool*
61681 61707 967

### *exception* outrage.store.PatternNotFoundError(code: str, \*\*details: Any)
62067 62093 976

### *exception* outrage.store.ReadOnlyStoreError(code: str, \*\*details: Any)
62469 62495 982

### outrage.store.SearchCombination
63342 63368 995

### *class* outrage.store.SearchCriterion(pattern: str, match: Literal['contains', 'line', 'regex'], target: Literal['document', 'metadata'], meta_name: tuple[str, ...] | None = None)
63539 63565 1001

#### pattern *: str*
64203 64229 1007

#### match *: Literal['contains', 'line', 'regex']*
64281 64307 1009

#### target *: Literal['document', 'metadata']*
64398 64424 1011

#### meta_name *: tuple[str, ...] | None*
64511 64537 1013

### *class* outrage.store.SearchPage(matches: tuple[DocumentMatch, ...], matched: int, matched_chars: int, scanned: int, total_candidates: int, total_candidate_chars: int, next_cursor: str | None)
64726 64752 1015

#### matches *: tuple[DocumentMatch, ...]*
65755 65781 1025

#### matched *: int*
65889 65915 1027

#### matched_chars *: int*
65968 65994 1029

#### scanned *: int*
66053 66079 1031

#### total_candidates *: int*
66132 66158 1033

#### total_candidate_chars *: int*
66220 66246 1035

#### next_cursor *: str | None*
66313 66339 1037

### outrage.store.SearchTarget
66460 66486 1039

### *class* outrage.store.Store(\*, log: EventLog | None = None, mount_point: str | None = None)
66657 66683 1045

#### writable *: ClassVar[bool]* *= True*
68046 68072 1068

#### versioned *: ClassVar[bool]* *= False*
68692 68718 1078

#### writes_deferred *: ClassVar[bool]* *= False*
69228 69254 1087

#### backend_name *: ClassVar[str]*
69774 69800 1095

#### *abstractmethod* close() → None
70131 70157 1101

#### *abstractmethod* store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
70509 70537 1110

#### copy_from(source: Store, subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
73782 73812 1156

#### located(key: str, format: str | None = None) → Path | None
79102 79134 1223

#### *abstractmethod* delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
80044 80078 1237

#### *abstractmethod* descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
82915 82951 1280

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
84673 84711 1310

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
86678 86718 1342

#### *abstractmethod* exists(key: str) → bool
89393 89435 1388

#### *abstractmethod* level_entry(key: str) → Entry | None
89905 89949 1399

#### *abstractmethod* retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
90790 90836 1414

#### *abstractmethod* list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
92934 92982 1436

#### last_child(key: str) → str | None
96084 96134 1483

#### *abstractmethod* get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
97800 97852 1513

#### find_documents(subtree: BoundedSubtree = EVERYTHING, \*, criteria: Sequence[SearchCriterion], combine: Literal['any', 'all'] = 'any', key_range: KeyRange = UNBOUNDED, cursor: str | None = None, scan_limit: int | None = None) → SearchPage
99983 100037 1539

#### *abstractmethod* missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
101235 101291 1552

#### *abstractmethod* keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
103382 103440 1581

### *exception* outrage.store.StoreFileError(code: str, \*\*details: Any)
104593 104653 1593

### *class* outrage.store.SchemaState(backend: str, service: str, path: Path, schema: str, stored: SchemaVersion | None, oldest: int, newest: int, operating: int | None, writable: bool, problem: Refusal | None = None)
105342 105402 1605

#### backend *: str*
107267 107327 1625

#### service *: str*
107405 107465 1629

#### path *: Path*
107533 107593 1633

#### schema *: str*
107660 107720 1637

#### stored *: SchemaVersion | None*
107800 107860 1641

#### oldest *: int*
107993 108053 1645

#### newest *: int*
108115 108175 1649

#### operating *: int | None*
108260 108320 1653

#### writable *: bool*
108473 108533 1657

#### problem *: Refusal | None*
108613 108673 1661

### *class* outrage.store.SchemaVersion(version: int, read_floor: int, write_floor: int)
108804 108864 1665

#### version *: int*
109502 109562 1676

#### read_floor *: int*
109581 109641 1678

#### write_floor *: int*
109663 109723 1680

### *class* outrage.store.SubtreeTotals(keys: int, documents: int, chars: int | None)
109746 109806 1682

#### keys *: int*
110803 110863 1698

#### documents *: int*
111381 111441 1709

#### chars *: int | None*
111965 112025 1719

### *class* outrage.store.Transfer(action: str, key: str | None, path: Path | None, reason: str | None = None, characters: int = 0, error: OutrageError | None = None)
112504 112564 1728

#### action *: str*
115260 115320 1764

#### key *: str | None*
115337 115397 1766

#### path *: Path | None*
115476 115536 1768

#### reason *: str | None*
115624 115684 1770

#### characters *: int*
115766 115826 1772

#### error *: OutrageError | None*
115848 115908 1774

### outrage.store.default_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → FileStore
115983 116043 1776

### outrage.store.default_store_file() → str
119348 119410 1806

### outrage.store.entry_kind(key: str) → str
120004 120068 1820

### outrage.store.is_pattern(filename: str | PathLike[str] | None) → bool
120679 120745 1833

### outrage.store.locates_own_store(backend: str | None = None, \*, unknown: bool | None = None) → bool
121422 121490 1842

### outrage.store.meta_reader(scope: str) → Callable[[str, str | None, str | None], tuple[str | None, str | None]]
123351 123421 1870

### outrage.store.open_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Iterator[FileStore]
125044 125116 1888

### outrage.store.pattern_matches(directory: str | PathLike[str], filename: str | PathLike[str]) → list[Path]
126869 126943 1892

### outrage.store.read_all(store: Store, key: str, \*\*kwargs: Any) → Excerpt
128011 128087 1904

### outrage.store.resolve_directory(explicit: str | PathLike[str] | None = None) → Path
129023 129101 1920

### outrage.store.store_file(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → Path
129570 129650 1927

### outrage.store.store_present(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → bool
131178 131260 1953
