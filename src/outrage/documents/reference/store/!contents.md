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

#### *property* target *: dict[str, str] | None*
35025 35033 571

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, create: bool = True) → Self
35627 35635 580

#### *classmethod* reporting(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None) → Self
39935 39945 630

#### opened_at(path: Path) → Self
41958 41970 652

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
42713 42727 666

#### verified_backup(target: Path) → Backup
44477 44493 693

#### backup_path(destination: str | PathLike[str] | None, \*, overwrite: bool) → Path
45492 45510 714

#### *property* backup_suffix *: str*
46560 46580 728

#### *abstract property* stored_format_version *: int*
46933 46953 737

#### *abstractmethod* audit_rows() → Iterator[AuditRow]
47506 47526 748

#### *abstractmethod* check_file(report: Report) → None
48276 48298 761

#### *abstractmethod* repair() → list[Repaired]
49053 49077 775

### outrage.store.Format
49844 49870 789

### *exception* outrage.store.InvalidArgumentError(code: str, \*\*details: Any)
50410 50436 800

### *exception* outrage.store.KeyNotFoundError(code: str, \*\*details: Any)
51740 51766 823

### *class* outrage.store.KeyRange(after: str | None = None, after_inclusive: str | None = None, after_subtree: str | None = None, before: str | None = None, before_inclusive: str | None = None, final_subtree: str | None = None)
52115 52141 829

#### after *: str | None*
55090 55116 867

#### after_inclusive *: str | None*
55231 55257 869

#### after_subtree *: str | None*
55382 55408 871

#### before *: str | None*
55531 55557 873

#### before_inclusive *: str | None*
55673 55699 875

#### final_subtree *: str | None*
55825 55851 877

### outrage.store.MatchMode
55974 56000 879

### *class* outrage.store.MatchWitness(criterion: int, source_key: str, source: Literal['document', 'metadata'], start: int, end: int, line: int = 1)
56184 56210 885

#### criterion *: int*
56816 56842 891

#### source_key *: str*
56897 56923 893

#### source *: Literal['document', 'metadata']*
56978 57004 895

#### start *: int*
57091 57117 897

#### end *: int*
57168 57194 899

#### line *: int*
57243 57269 901

### outrage.store.MetaReader
57378 57404 905

### *class* outrage.store.MissingMeta(total: int, total_chars: int, sample: list[str], selection_documents: int | None = None, selection_carried: dict[str, int] | None = None)
58309 58335 912

#### total *: int*
59425 59451 922

#### total_chars *: int*
59565 59591 926

#### sample *: list[str]*
59772 59798 931

#### selection_documents *: int | None*
59986 60012 935

#### selection_carried *: dict[str, int] | None*
60477 60503 943

### *class* outrage.store.Page(items: list[T], returned: int, total: int, total_chars: int, next_cursor: str | None, unavailable: tuple[str, ...] = ())
61472 61498 960

#### items *: list[T]*
62554 62580 972

#### returned *: int*
62635 62661 974

#### total *: int*
62736 62762 978

#### total_chars *: int*
62881 62907 982

#### next_cursor *: str | None*
63191 63217 989

#### unavailable *: tuple[str, ...]*
63399 63425 993

#### *property* truncated *: bool*
63786 63812 1000

### *exception* outrage.store.PatternNotFoundError(code: str, \*\*details: Any)
64172 64198 1009

### *exception* outrage.store.ReadOnlyStoreError(code: str, \*\*details: Any)
64574 64600 1015

### outrage.store.SearchCombination
65447 65473 1028

### *class* outrage.store.SearchCriterion(pattern: str, match: Literal['contains', 'line', 'regex'], target: Literal['document', 'metadata'], meta_name: tuple[str, ...] | None = None)
65644 65670 1034

#### pattern *: str*
66308 66334 1040

#### match *: Literal['contains', 'line', 'regex']*
66386 66412 1042

#### target *: Literal['document', 'metadata']*
66503 66529 1044

#### meta_name *: tuple[str, ...] | None*
66616 66642 1046

### *class* outrage.store.SearchPage(matches: tuple[DocumentMatch, ...], matched: int, matched_chars: int, scanned: int, total_candidates: int, total_candidate_chars: int, next_cursor: str | None, unavailable: tuple[str, ...] = ())
66831 66857 1048

#### matches *: tuple[DocumentMatch, ...]*
68009 68035 1058

#### matched *: int*
68143 68169 1060

#### matched_chars *: int*
68222 68248 1062

#### scanned *: int*
68307 68333 1064

#### total_candidates *: int*
68386 68412 1066

#### total_candidate_chars *: int*
68474 68500 1068

#### next_cursor *: str | None*
68567 68593 1070

#### unavailable *: tuple[str, ...]*
68714 68740 1072

### outrage.store.SearchTarget
68966 68992 1076

### *class* outrage.store.Store(\*, log: EventLog | None = None, mount_point: str | None = None)
69163 69189 1082

#### writable *: ClassVar[bool]* *= True*
70552 70578 1105

#### versioned *: ClassVar[bool]* *= False*
71198 71224 1115

#### writes_deferred *: ClassVar[bool]* *= False*
71734 71760 1124

#### backend_name *: ClassVar[str]*
72280 72306 1132

#### *abstractmethod* close() → None
72637 72663 1138

#### *abstractmethod* store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
73015 73043 1147

#### copy_from(source: Store, subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
76288 76318 1193

#### located(key: str, format: str | None = None) → Path | None
81608 81640 1260

#### *abstractmethod* delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
82550 82584 1274

#### *abstractmethod* descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
85421 85457 1317

#### now(key: str = keys.ROOT, \*, key_range: KeyRange = UNBOUNDED) → str
87179 87217 1347

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
87945 87985 1359

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
90067 90109 1393

#### *abstractmethod* exists(key: str) → bool
92782 92826 1439

#### *abstractmethod* level_entry(key: str) → Entry | None
93294 93340 1450

#### *abstractmethod* retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
94179 94227 1465

#### *abstractmethod* list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
96323 96373 1487

#### last_child(key: str) → str | None
99473 99525 1534

#### *abstractmethod* get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
101189 101243 1564

#### find_documents(subtree: BoundedSubtree = EVERYTHING, \*, criteria: Sequence[SearchCriterion], combine: Literal['any', 'all'] = 'any', key_range: KeyRange = UNBOUNDED, cursor: str | None = None, scan_limit: int | None = None) → SearchPage
103372 103428 1590

#### *abstractmethod* missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
104624 104682 1603

#### *abstractmethod* keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
106771 106831 1632

### *exception* outrage.store.StoreFileError(code: str, \*\*details: Any)
107982 108044 1644

### *class* outrage.store.SchemaState(backend: str, service: str, path: Path, schema: str, stored: SchemaVersion | None, oldest: int, newest: int, operating: int | None, writable: bool, problem: Refusal | None = None)
108731 108793 1656

#### backend *: str*
110656 110718 1676

#### service *: str*
110794 110856 1680

#### path *: Path*
110922 110984 1684

#### schema *: str*
111049 111111 1688

#### stored *: SchemaVersion | None*
111189 111251 1692

#### oldest *: int*
111382 111444 1696

#### newest *: int*
111504 111566 1700

#### operating *: int | None*
111649 111711 1704

#### writable *: bool*
111862 111924 1708

#### problem *: Refusal | None*
112002 112064 1712

### *class* outrage.store.SchemaVersion(version: int, read_floor: int, write_floor: int)
112193 112255 1716

#### version *: int*
112891 112953 1727

#### read_floor *: int*
112970 113032 1729

#### write_floor *: int*
113052 113114 1731

### *class* outrage.store.SubtreeTotals(keys: int, documents: int, chars: int | None)
113135 113197 1733

#### keys *: int*
114192 114254 1749

#### documents *: int*
114770 114832 1760

#### chars *: int | None*
115354 115416 1770

### *class* outrage.store.Transfer(action: str, key: str | None, path: Path | None, reason: str | None = None, characters: int = 0, error: OutrageError | None = None)
115893 115955 1779

#### action *: str*
118649 118711 1815

#### key *: str | None*
118726 118788 1817

#### path *: Path | None*
118865 118927 1819

#### reason *: str | None*
119013 119075 1821

#### characters *: int*
119155 119217 1823

#### error *: OutrageError | None*
119237 119299 1825

### outrage.store.default_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, create: bool = True) → FileStore
119372 119434 1827

### outrage.store.default_store_file() → str
122948 123012 1860

### outrage.store.entry_kind(key: str) → str
123604 123670 1874

### outrage.store.is_pattern(filename: str | PathLike[str] | None) → bool
124279 124347 1887

### outrage.store.locates_own_store(backend: str | None = None, \*, unknown: bool | None = None) → bool
125022 125092 1896

### outrage.store.meta_reader(scope: str) → Callable[[str, str | None, str | None], tuple[str | None, str | None]]
126951 127023 1924

### outrage.store.open_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Iterator[FileStore]
128644 128718 1942

### outrage.store.pattern_matches(directory: str | PathLike[str], filename: str | PathLike[str]) → list[Path]
130469 130545 1946

### outrage.store.read_all(store: Store, key: str, \*\*kwargs: Any) → Excerpt
131611 131689 1958

### outrage.store.resolve_directory(explicit: str | PathLike[str] | None = None) → Path
132623 132703 1974

### outrage.store.store_file(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → Path
133170 133252 1981

### outrage.store.store_present(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → bool
134778 134862 2007
