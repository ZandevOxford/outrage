# outrage.store_duckdb
0 0

### outrage.store_duckdb.AUDIT_CHUNK *= 8192*
4877 4877

### outrage.store_duckdb.BATCH *= 64*
5114 5114

### outrage.store_duckdb.BATCH_CEILING *= 4096*
5449 5449

### outrage.store_duckdb.DEFAULT_STORE_DIR *= 'parts'*
5565 5565

### outrage.store_duckdb.MEMORY_LIMIT *= '1GB'*
5812 5812

### outrage.store_duckdb.PART_SUFFIX *= '.parquet'*
6313 6313

### *class* outrage.store_duckdb.DuckdbStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
6484 6484

#### default_filename *: ClassVar[str]* *= 'parts'*
7467 7467

#### backend_name *: ClassVar[str]* *= 'duckdb'*
7965 7965

#### format_version *: ClassVar[int]* *= 2*
8334 8334

#### writable *: ClassVar[bool]* *= False*
8948 8948

#### close() → None
9557 9557

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
10145 10147

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
11409 11413

#### exists(key: str) → bool
12110 12116

#### level_entry(key: str) → Entry | None
12292 12300

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
12745 12755

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
13456 13468

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
14233 14247

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
14723 14739

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
15791 15809

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
17863 17883

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
19319 19341

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
20316 20340

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
21344 21370

#### *property* stored_format_version *: int*
22103 22131

#### audit_rows() → Iterator[AuditRow]
22280 22308

#### check_file(report: Report) → None
22693 22723

#### repair() → list[Repaired]
23245 23277
