# outrage.store_sqlite
0 0

### outrage.store_sqlite.ARCHIVE_TABLE *= 'document_archive'*
1660 1660

### outrage.store_sqlite.BUSY_TIMEOUT_MS *= 5000*
2756 2756

### outrage.store_sqlite.CHILD_BATCH *= 8*
3179 3179

### outrage.store_sqlite.CHILD_BATCH_CEILING *= 256*
3789 3789

### outrage.store_sqlite.DEFAULT_STORE_FILE *= 'store.sqlite'*
3964 3964

### outrage.store_sqlite.LENGTH_CACHE_TABLE *= 'document_lengths'*
4398 4398

### outrage.store_sqlite.LENGTH_THRESHOLD *= 2048*
4897 4897

### outrage.store_sqlite.SCHEMA_VERSION *= 7*
5541 5541

### outrage.store_sqlite.WAL_RATIO *= 1.0*
5852 5852

### *class* outrage.store_sqlite.SqliteStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True)
6120 6120

#### default_filename *: ClassVar[str]* *= 'store.sqlite'*
7170 7170

#### backend_name *: ClassVar[str]* *= 'sqlite'*
7675 7675

#### format_version *: ClassVar[int]* *= 7*
8044 8044

#### writable *: ClassVar[bool]* *= True*
8658 8658

#### versioned *: ClassVar[bool]* *= True*
9086 9086

#### *property* connection *: Connection*
9393 9393

#### close() → None
10244 10244

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
10680 10682

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
12106 12110

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
13306 13312

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
14129 14137

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
15386 15396

#### exists(key: str) → bool
16219 16231

#### level_entry(key: str) → Entry | None
16580 16594

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
17043 17059

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
18345 18363

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
20280 20300

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
21739 21761

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
23797 23821

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
24889 24915

#### *property* stored_format_version *: int*
25819 25847

#### audit_rows() → Iterator[AuditRow]
25980 26008

#### check_file(report: Report) → None
26389 26419

#### repair() → list[Repaired]
26783 26815
