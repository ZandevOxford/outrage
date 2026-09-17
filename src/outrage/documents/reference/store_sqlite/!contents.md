# outrage.store_sqlite
0 0

### outrage.store_sqlite.ARCHIVE_TABLE *= 'document_archive'*
1660 1660

### outrage.store_sqlite.BUSY_TIMEOUT_MS *= 5000*
2756 2756

### outrage.store_sqlite.CHILD_BATCH *= 8*
3100 3100

### outrage.store_sqlite.CHILD_BATCH_CEILING *= 256*
3710 3710

### outrage.store_sqlite.DEFAULT_STORE_FILE *= 'store.sqlite'*
3885 3885

### outrage.store_sqlite.LENGTH_CACHE_TABLE *= 'document_lengths'*
4319 4319

### outrage.store_sqlite.LENGTH_THRESHOLD *= 2048*
4818 4818

### outrage.store_sqlite.SCHEMA_VERSION *= 7*
5462 5462

### outrage.store_sqlite.WAL_RATIO *= 1.0*
5773 5773

### *class* outrage.store_sqlite.SqliteStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True)
6041 6041

#### default_filename *: ClassVar[str]* *= 'store.sqlite'*
7101 7101

#### backend_name *: ClassVar[str]* *= 'sqlite'*
7607 7607

#### format_version *: ClassVar[int]* *= 7*
7977 7977

#### writable *: ClassVar[bool]* *= True*
8592 8592

#### versioned *: ClassVar[bool]* *= True*
9021 9021

#### *property* connection *: Connection*
9329 9329

#### close() → None
10180 10180

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
10617 10619

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
12056 12060

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
13263 13269

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
14089 14097

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
15348 15358

#### exists(key: str) → bool
16185 16197

#### level_entry(key: str) → Entry | None
16548 16562

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
17013 17029

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
18325 18343

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
20268 20288

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
21737 21759

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
23880 23904

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
24979 25005

#### *property* stored_format_version *: int*
25913 25941

#### audit_rows() → Iterator[AuditRow]
26075 26103

#### check_file(report: Report) → None
26484 26514

#### repair() → list[Repaired]
26879 26911
