# outrage.store_duckdb
0 0

### outrage.store_duckdb.AUDIT_CHUNK *= 8192*
4879 4879

### outrage.store_duckdb.BATCH *= 64*
5116 5116

### outrage.store_duckdb.BATCH_CEILING *= 4096*
5451 5451

### outrage.store_duckdb.DEFAULT_STORE_DIR *= 'parts'*
5567 5567

### outrage.store_duckdb.MEMORY_LIMIT *= '1GB'*
5814 5814

### outrage.store_duckdb.PART_SUFFIX *= '.parquet'*
6315 6315

### *class* outrage.store_duckdb.DuckdbStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
6486 6486

#### default_filename *: ClassVar[str]* *= 'parts'*
7469 7469

#### backend_name *: ClassVar[str]* *= 'duckdb'*
7967 7967

#### format_version *: ClassVar[int]* *= 2*
8336 8336

#### writable *: ClassVar[bool]* *= False*
8950 8950

#### close() → None
9559 9559

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
10147 10149

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
11411 11415

#### exists(key: str) → bool
12112 12118

#### level_entry(key: str) → Entry | None
12294 12302

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
12747 12757

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
13458 13470

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
14235 14249

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
14725 14741

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
15793 15811

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
17865 17885

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
19321 19343

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
20318 20342

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
21346 21372

#### *property* stored_format_version *: int*
22105 22133

#### audit_rows() → Iterator[AuditRow]
22282 22310

#### check_file(report: Report) → None
22695 22725

#### repair() → list[Repaired]
23247 23279
