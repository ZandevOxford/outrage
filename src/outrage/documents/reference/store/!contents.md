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

### *class* outrage.store.Page(items: list[T], returned: int, total: int, total_chars: int, next_cursor: str | None)
61472 61498 960

#### items *: list[T]*
62405 62431 972

#### returned *: int*
62486 62512 974

#### total *: int*
62587 62613 978

#### total_chars *: int*
62732 62758 982

#### next_cursor *: str | None*
63042 63068 989

#### *property* truncated *: bool*
63250 63276 993

### *exception* outrage.store.PatternNotFoundError(code: str, \*\*details: Any)
63636 63662 1002

### *exception* outrage.store.ReadOnlyStoreError(code: str, \*\*details: Any)
64038 64064 1008

### outrage.store.SearchCombination
64911 64937 1021

### *class* outrage.store.SearchCriterion(pattern: str, match: Literal['contains', 'line', 'regex'], target: Literal['document', 'metadata'], meta_name: tuple[str, ...] | None = None)
65108 65134 1027

#### pattern *: str*
65772 65798 1033

#### match *: Literal['contains', 'line', 'regex']*
65850 65876 1035

#### target *: Literal['document', 'metadata']*
65967 65993 1037

#### meta_name *: tuple[str, ...] | None*
66080 66106 1039

### *class* outrage.store.SearchPage(matches: tuple[DocumentMatch, ...], matched: int, matched_chars: int, scanned: int, total_candidates: int, total_candidate_chars: int, next_cursor: str | None)
66295 66321 1041

#### matches *: tuple[DocumentMatch, ...]*
67324 67350 1051

#### matched *: int*
67458 67484 1053

#### matched_chars *: int*
67537 67563 1055

#### scanned *: int*
67622 67648 1057

#### total_candidates *: int*
67701 67727 1059

#### total_candidate_chars *: int*
67789 67815 1061

#### next_cursor *: str | None*
67882 67908 1063

### outrage.store.SearchTarget
68029 68055 1065

### *class* outrage.store.Store(\*, log: EventLog | None = None, mount_point: str | None = None)
68226 68252 1071

#### writable *: ClassVar[bool]* *= True*
69615 69641 1094

#### versioned *: ClassVar[bool]* *= False*
70261 70287 1104

#### writes_deferred *: ClassVar[bool]* *= False*
70797 70823 1113

#### backend_name *: ClassVar[str]*
71343 71369 1121

#### *abstractmethod* close() → None
71700 71726 1127

#### *abstractmethod* store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
72078 72106 1136

#### copy_from(source: Store, subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
75351 75381 1182

#### located(key: str, format: str | None = None) → Path | None
80671 80703 1249

#### *abstractmethod* delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
81613 81647 1263

#### *abstractmethod* descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
84484 84520 1306

#### now(key: str = keys.ROOT, \*, key_range: KeyRange = UNBOUNDED) → str
86242 86280 1336

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
87008 87048 1348

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
89130 89172 1382

#### *abstractmethod* exists(key: str) → bool
91845 91889 1428

#### *abstractmethod* level_entry(key: str) → Entry | None
92357 92403 1439

#### *abstractmethod* retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
93242 93290 1454

#### *abstractmethod* list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
95386 95436 1476

#### last_child(key: str) → str | None
98536 98588 1523

#### *abstractmethod* get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
100252 100306 1553

#### find_documents(subtree: BoundedSubtree = EVERYTHING, \*, criteria: Sequence[SearchCriterion], combine: Literal['any', 'all'] = 'any', key_range: KeyRange = UNBOUNDED, cursor: str | None = None, scan_limit: int | None = None) → SearchPage
102435 102491 1579

#### *abstractmethod* missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
103687 103745 1592

#### *abstractmethod* keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
105834 105894 1621

### *exception* outrage.store.StoreFileError(code: str, \*\*details: Any)
107045 107107 1633

### *class* outrage.store.SchemaState(backend: str, service: str, path: Path, schema: str, stored: SchemaVersion | None, oldest: int, newest: int, operating: int | None, writable: bool, problem: Refusal | None = None)
107794 107856 1645

#### backend *: str*
109719 109781 1665

#### service *: str*
109857 109919 1669

#### path *: Path*
109985 110047 1673

#### schema *: str*
110112 110174 1677

#### stored *: SchemaVersion | None*
110252 110314 1681

#### oldest *: int*
110445 110507 1685

#### newest *: int*
110567 110629 1689

#### operating *: int | None*
110712 110774 1693

#### writable *: bool*
110925 110987 1697

#### problem *: Refusal | None*
111065 111127 1701

### *class* outrage.store.SchemaVersion(version: int, read_floor: int, write_floor: int)
111256 111318 1705

#### version *: int*
111954 112016 1716

#### read_floor *: int*
112033 112095 1718

#### write_floor *: int*
112115 112177 1720

### *class* outrage.store.SubtreeTotals(keys: int, documents: int, chars: int | None)
112198 112260 1722

#### keys *: int*
113255 113317 1738

#### documents *: int*
113833 113895 1749

#### chars *: int | None*
114417 114479 1759

### *class* outrage.store.Transfer(action: str, key: str | None, path: Path | None, reason: str | None = None, characters: int = 0, error: OutrageError | None = None)
114956 115018 1768

#### action *: str*
117712 117774 1804

#### key *: str | None*
117789 117851 1806

#### path *: Path | None*
117928 117990 1808

#### reason *: str | None*
118076 118138 1810

#### characters *: int*
118218 118280 1812

#### error *: OutrageError | None*
118300 118362 1814

### outrage.store.default_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, create: bool = True) → FileStore
118435 118497 1816

### outrage.store.default_store_file() → str
122011 122075 1849

### outrage.store.entry_kind(key: str) → str
122667 122733 1863

### outrage.store.is_pattern(filename: str | PathLike[str] | None) → bool
123342 123410 1876

### outrage.store.locates_own_store(backend: str | None = None, \*, unknown: bool | None = None) → bool
124085 124155 1885

### outrage.store.meta_reader(scope: str) → Callable[[str, str | None, str | None], tuple[str | None, str | None]]
126014 126086 1913

### outrage.store.open_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Iterator[FileStore]
127707 127781 1931

### outrage.store.pattern_matches(directory: str | PathLike[str], filename: str | PathLike[str]) → list[Path]
129532 129608 1935

### outrage.store.read_all(store: Store, key: str, \*\*kwargs: Any) → Excerpt
130674 130752 1947

### outrage.store.resolve_directory(explicit: str | PathLike[str] | None = None) → Path
131686 131766 1963

### outrage.store.store_file(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → Path
132233 132315 1970

### outrage.store.store_present(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → bool
133841 133925 1996
