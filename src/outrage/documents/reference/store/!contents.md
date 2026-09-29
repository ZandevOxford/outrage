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

### outrage.store.check_read_position(key: str, \*, offset: int, byte_offset: int | None, line: int | None, lines: int | None, pattern: str | None, occurrence: int) → None
6186 6190 104

### outrage.store.check_unchanged(opened: Store, key: str, unchanged_since: str | None, \*, action: str = 'write over', subtree: bool = True, key_range: KeyRange = UNBOUNDED) → None
7450 7456 114

### outrage.store.DEFAULT_BULK_MAX_CHARS *= 2000*
9455 9463 141

### outrage.store.DEFAULT_DIR_NAME *= '.outrage'*
9606 9614 146

### outrage.store.DEFAULT_MAX_CHARS *= 8000*
9762 9770 151

### outrage.store.ENCODINGS *: tuple[str, ...]* *= ('json-string',)*
9949 9957 156

### outrage.store.ENV_DIR *= 'OUTRAGE_DIR'*
10219 10227 160

### outrage.store.EVERYTHING *= BoundedSubtree(key=None, depth=None)*
10458 10466 166

### outrage.store.FAILED *= 'failed'*
10667 10675 171

### outrage.store.FORMATS *: tuple[str, ...]* *= ('markdown', 'json', 'text', 'html')*
10783 10791 175

### outrage.store.OVERWRITE *= 'overwrite'*
11289 11297 182

### outrage.store.OVERWRITE_UNCHANGED *= 'overwrite-unchanged'*
11366 11374 186

### outrage.store.READ *= 'read'*
11818 11826 194

### outrage.store.SKIP *= 'skip'*
12179 12187 201

### outrage.store.SKIPPED *= 'skipped'*
12345 12353 206

### outrage.store.STOP *= 'stop'*
12464 12472 210

### outrage.store.STOPPED *= 'stopped'*
12645 12653 215

### outrage.store.UNBOUNDED *= KeyRange(after=None, after_inclusive=None, after_subtree=None, before=None, before_inclusive=None, final_subtree=None)*
12882 12890 221

### outrage.store.VERSIONING_OFF *= 'off'*
13280 13288 227

### outrage.store.VERSIONING_ON *= 'on'*
13393 13401 231

### outrage.store.VERSIONING_SETTINGS *= ('on', 'off')*
13704 13712 238

### outrage.store.WROTE *= 'wrote'*
13810 13818 242

### *class* outrage.store.AuditRow(key: str, doc_key: str, meta_name: str | None, parent: str, chars: int)
13925 13933 246

#### key *: str*
15148 15156 262

#### doc_key *: str*
15222 15230 264

#### meta_name *: str | None*
15388 15396 269

#### parent *: str*
15584 15592 273

#### chars *: int*
15817 15825 278

### *class* outrage.store.Backup(path: Path, bytes: int, documents: int, integrity: str)
15894 15902 280

#### path *: Path*
16354 16362 286

#### bytes *: int*
16437 16445 288

#### documents *: int*
16514 16522 290

#### integrity *: str*
16657 16665 294

### *exception* outrage.store.BackendError(code: str, \*\*details: Any)
16795 16803 298

### *exception* outrage.store.BackupError(code: str, \*\*details: Any)
17216 17224 305

### *class* outrage.store.BoundedSubtree(key: str | None = None, depth: int | None = None)
17621 17629 311

#### key *: str | None*
18647 18655 327

#### depth *: int | None*
18786 18794 329

### *exception* outrage.store.ChangedSinceError(code: str, \*\*details: Any)
18928 18936 331

### *class* outrage.store.DocumentMatch(document: Entry, witnesses: tuple[MatchWitness, ...])
20006 20014 348

#### document *: Entry*
20355 20363 354

#### witnesses *: tuple[MatchWitness, ...]*
20404 20412 356

### outrage.store.Encoding
20538 20546 358

### *class* outrage.store.Entry(key: str, kind: str, size: int | None, format: str | None, updated_at: str | None, descendants: int | None = None, descendant_documents: int | None = None, descendant_chars: int | None = None)
20888 20896 366

#### key *: str*
22240 22248 376

#### kind *: str*
22314 22322 378

#### size *: int | None*
22490 22498 383

#### format *: str | None*
22631 22639 385

#### updated_at *: str | None*
22773 22781 387

#### descendants *: int | None*
22919 22927 389

#### descendant_documents *: int | None*
23246 23254 395

#### descendant_chars *: int | None*
23857 23865 404

### *class* outrage.store.Excerpt(key: str, content: str, format: str | None, updated_at: str, offset: int | None, returned: int, total: int | None, next_offset: int | None, byte_offset: int, total_bytes: int, next_byte_offset: int | None, line: int | None = None, next_line: int | None = None)
24070 24078 408

#### key *: str*
25626 25634 414

#### content *: str*
25700 25708 416

#### format *: str | None*
25778 25786 418

#### updated_at *: str*
25920 25928 420

#### offset *: int | None*
26001 26009 422

#### returned *: int*
26532 26540 431

#### total *: int | None*
26644 26652 435

#### next_offset *: int | None*
27001 27009 441

#### byte_offset *: int*
27304 27312 447

#### total_bytes *: int*
27662 27670 454

#### next_byte_offset *: int | None*
27791 27799 458

#### line *: int | None*
28094 28102 464

#### next_line *: int | None*
28373 28381 469

#### *property* truncated *: bool*
28711 28719 475

### *class* outrage.store.FileStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
29292 29300 488

#### default_filename *: ClassVar[str]*
31497 31505 514

#### format_version *: ClassVar[int]*
32050 32058 522

#### reads_patterns *: ClassVar[bool]* *= False*
32650 32658 530

#### locates_own_store *: ClassVar[bool]* *= False*
33074 33082 537

#### manages_schema *: ClassVar[bool]* *= False*
34095 34103 554

#### *property* target *: dict[str, str] | None*
35174 35182 573

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, create: bool = True) → Self
35776 35784 582

#### *classmethod* reporting(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None) → Self
40084 40094 632

#### opened_at(path: Path) → Self
42107 42119 654

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
42862 42876 668

#### verified_backup(target: Path) → Backup
44626 44642 695

#### backup_path(destination: str | PathLike[str] | None, \*, overwrite: bool) → Path
45641 45659 716

#### *property* backup_suffix *: str*
46709 46729 730

#### *abstract property* stored_format_version *: int*
47082 47102 739

#### *abstractmethod* audit_rows() → Iterator[AuditRow]
47655 47675 750

#### *abstractmethod* check_file(report: Report) → None
48425 48447 763

#### *abstractmethod* repair() → list[Repaired]
49202 49226 777

### outrage.store.Format
49993 50019 791

### *exception* outrage.store.InvalidArgumentError(code: str, \*\*details: Any)
50559 50585 802

### *exception* outrage.store.KeyNotFoundError(code: str, \*\*details: Any)
51889 51915 825

### *class* outrage.store.KeyRange(after: str | None = None, after_inclusive: str | None = None, after_subtree: str | None = None, before: str | None = None, before_inclusive: str | None = None, final_subtree: str | None = None)
52264 52290 831

#### after *: str | None*
55239 55265 869

#### after_inclusive *: str | None*
55380 55406 871

#### after_subtree *: str | None*
55531 55557 873

#### before *: str | None*
55680 55706 875

#### before_inclusive *: str | None*
55822 55848 877

#### final_subtree *: str | None*
55974 56000 879

### outrage.store.MatchMode
56123 56149 881

### *class* outrage.store.MatchWitness(criterion: int, source_key: str, source: Literal['document', 'metadata'], start: int, end: int, line: int = 1)
56333 56359 887

#### criterion *: int*
56965 56991 893

#### source_key *: str*
57046 57072 895

#### source *: Literal['document', 'metadata']*
57127 57153 897

#### start *: int*
57240 57266 899

#### end *: int*
57317 57343 901

#### line *: int*
57392 57418 903

### outrage.store.MetaReader
57527 57553 907

### *class* outrage.store.MissingMeta(total: int, total_chars: int, sample: list[str], selection_documents: int | None = None, selection_carried: dict[str, int] | None = None)
58458 58484 914

#### total *: int*
59574 59600 924

#### total_chars *: int*
59714 59740 928

#### sample *: list[str]*
59921 59947 933

#### selection_documents *: int | None*
60135 60161 937

#### selection_carried *: dict[str, int] | None*
60626 60652 945

### *class* outrage.store.Page(items: list[T], returned: int, total: int, total_chars: int, next_cursor: str | None, unavailable: tuple[str, ...] = ())
61621 61647 962

#### items *: list[T]*
62703 62729 974

#### returned *: int*
62784 62810 976

#### total *: int*
62885 62911 980

#### total_chars *: int*
63030 63056 984

#### next_cursor *: str | None*
63340 63366 991

#### unavailable *: tuple[str, ...]*
63548 63574 995

#### *property* truncated *: bool*
63935 63961 1002

### *exception* outrage.store.PatternNotFoundError(code: str, \*\*details: Any)
64321 64347 1011

### *exception* outrage.store.ReadOnlyStoreError(code: str, \*\*details: Any)
64723 64749 1017

### outrage.store.SearchCombination
65596 65622 1030

### *class* outrage.store.SearchCriterion(pattern: str, match: Literal['contains', 'line', 'regex'], target: Literal['document', 'metadata'], meta_name: tuple[str, ...] | None = None)
65793 65819 1036

#### pattern *: str*
66457 66483 1042

#### match *: Literal['contains', 'line', 'regex']*
66535 66561 1044

#### target *: Literal['document', 'metadata']*
66652 66678 1046

#### meta_name *: tuple[str, ...] | None*
66765 66791 1048

### *class* outrage.store.SearchPage(matches: tuple[DocumentMatch, ...], matched: int, matched_chars: int, scanned: int, total_candidates: int, total_candidate_chars: int, next_cursor: str | None, unavailable: tuple[str, ...] = ())
66980 67006 1050

#### matches *: tuple[DocumentMatch, ...]*
68158 68184 1060

#### matched *: int*
68292 68318 1062

#### matched_chars *: int*
68371 68397 1064

#### scanned *: int*
68456 68482 1066

#### total_candidates *: int*
68535 68561 1068

#### total_candidate_chars *: int*
68623 68649 1070

#### next_cursor *: str | None*
68716 68742 1072

#### unavailable *: tuple[str, ...]*
68863 68889 1074

### outrage.store.SearchTarget
69115 69141 1078

### *class* outrage.store.Store(\*, log: EventLog | None = None, mount_point: str | None = None)
69312 69338 1084

#### writable *: ClassVar[bool]* *= True*
70701 70727 1107

#### versioned *: ClassVar[bool]* *= False*
71347 71373 1117

#### writes_deferred *: ClassVar[bool]* *= False*
71883 71909 1126

#### backend_name *: ClassVar[str]*
72429 72455 1134

#### *abstractmethod* close() → None
72786 72812 1140

#### *abstractmethod* store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
73164 73192 1149

#### copy_from(source: Store, subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
76437 76467 1195

#### located(key: str, format: str | None = None) → Path | None
81757 81789 1262

#### *abstractmethod* delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
82699 82733 1276

#### *abstractmethod* descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
85570 85606 1319

#### now(key: str = keys.ROOT, \*, key_range: KeyRange = UNBOUNDED) → str
87328 87366 1349

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
88094 88134 1361

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
90216 90258 1395

#### *abstractmethod* exists(key: str) → bool
92931 92975 1441

#### *abstractmethod* level_entry(key: str) → Entry | None
93443 93489 1452

#### *abstractmethod* retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
94328 94376 1467

#### *abstractmethod* list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
96472 96522 1489

#### last_child(key: str) → str | None
99622 99674 1536

#### *abstractmethod* get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
101338 101392 1566

#### find_documents(subtree: BoundedSubtree = EVERYTHING, \*, criteria: Sequence[SearchCriterion], combine: Literal['any', 'all'] = 'any', key_range: KeyRange = UNBOUNDED, cursor: str | None = None, scan_limit: int | None = None) → SearchPage
103521 103577 1592

#### *abstractmethod* missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
104773 104831 1605

#### *abstractmethod* keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
106920 106980 1634

### *exception* outrage.store.StoreFileError(code: str, \*\*details: Any)
108131 108193 1646

### *class* outrage.store.SchemaState(backend: str, service: str, path: Path, schema: str, stored: SchemaVersion | None, oldest: int, newest: int, operating: int | None, writable: bool, problem: Refusal | None = None)
108880 108942 1658

#### backend *: str*
110805 110867 1678

#### service *: str*
110943 111005 1682

#### path *: Path*
111071 111133 1686

#### schema *: str*
111198 111260 1690

#### stored *: SchemaVersion | None*
111338 111400 1694

#### oldest *: int*
111531 111593 1698

#### newest *: int*
111653 111715 1702

#### operating *: int | None*
111798 111860 1706

#### writable *: bool*
112011 112073 1710

#### problem *: Refusal | None*
112151 112213 1714

### *class* outrage.store.SchemaVersion(version: int, read_floor: int, write_floor: int)
112342 112404 1718

#### version *: int*
113040 113102 1729

#### read_floor *: int*
113119 113181 1731

#### write_floor *: int*
113201 113263 1733

### *class* outrage.store.SubtreeTotals(keys: int, documents: int, chars: int | None)
113284 113346 1735

#### keys *: int*
114341 114403 1751

#### documents *: int*
114919 114981 1762

#### chars *: int | None*
115503 115565 1772

### *class* outrage.store.Transfer(action: str, key: str | None, path: Path | None, reason: str | None = None, characters: int = 0, error: OutrageError | None = None)
116042 116104 1781

#### action *: str*
118798 118860 1817

#### key *: str | None*
118875 118937 1819

#### path *: Path | None*
119014 119076 1821

#### reason *: str | None*
119162 119224 1823

#### characters *: int*
119304 119366 1825

#### error *: OutrageError | None*
119386 119448 1827

### outrage.store.default_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, create: bool = True) → FileStore
119521 119583 1829

### outrage.store.default_store_file() → str
123097 123161 1862

### outrage.store.entry_kind(key: str) → str
123753 123819 1876

### outrage.store.is_pattern(filename: str | PathLike[str] | None) → bool
124428 124496 1889

### outrage.store.locates_own_store(backend: str | None = None, \*, unknown: bool | None = None) → bool
125171 125241 1898

### outrage.store.meta_reader(scope: str) → Callable[[str, str | None, str | None], tuple[str | None, str | None]]
127100 127172 1926

### outrage.store.open_store(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, backend: str | None = None, extensions: str | None = None, versioning: str | None = None, versioning_default: bool = True, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Iterator[FileStore]
128793 128867 1944

### outrage.store.pattern_matches(directory: str | PathLike[str], filename: str | PathLike[str]) → list[Path]
130618 130694 1948

### outrage.store.read_all(store: Store, key: str, \*\*kwargs: Any) → Excerpt
131760 131838 1960

### outrage.store.resolve_directory(explicit: str | PathLike[str] | None = None) → Path
132772 132852 1976

### outrage.store.store_file(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → Path
133319 133401 1983

### outrage.store.store_present(directory: str | PathLike[str], filename: str | PathLike[str] | None = None) → bool
134927 135011 2009
