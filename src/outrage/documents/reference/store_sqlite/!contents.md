# outrage.store_sqlite
0 0

### outrage.store_sqlite.BUSY_TIMEOUT_MS *= 5000*
1660 1660

### outrage.store_sqlite.CHILD_BATCH *= 8*
2083 2083

### outrage.store_sqlite.CHILD_BATCH_CEILING *= 256*
2693 2693

### outrage.store_sqlite.DEFAULT_STORE_FILE *= 'store.sqlite'*
2868 2868

### outrage.store_sqlite.LENGTH_CACHE_TABLE *= 'document_lengths'*
3302 3302

### outrage.store_sqlite.LENGTH_THRESHOLD *= 2048*
3801 3801

### outrage.store_sqlite.SCHEMA_VERSION *= 6*
4445 4445

### outrage.store_sqlite.WAL_RATIO *= 1.0*
4756 4756

### *class* outrage.store_sqlite.SqliteStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
5024 5024

#### default_filename *: ClassVar[str]* *= 'store.sqlite'*
5992 5992

#### backend_name *: ClassVar[str]* *= 'sqlite'*
6497 6497

#### format_version *: ClassVar[int]* *= 6*
6866 6866

#### writable *: ClassVar[bool]* *= True*
7480 7480

#### *property* connection *: Connection*
7908 7908

#### close() → None
8759 8759

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
9195 9197

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
10621 10625

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
11821 11827

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
12644 12652

#### exists(key: str) → bool
13477 13487

#### level_entry(key: str) → Entry | None
13838 13850

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
14301 14315

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None) → Page[Entry]
15603 15619

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
16987 17005

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
18446 18466

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
20504 20526

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
21596 21620

#### *property* stored_format_version *: int*
22526 22552

#### audit_rows() → Iterator[AuditRow]
22687 22713

#### check_file(report: Report) → None
23096 23124

#### repair() → list[Repaired]
23490 23520
