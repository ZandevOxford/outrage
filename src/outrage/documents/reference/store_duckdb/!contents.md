# outrage.store_duckdb
0 0

### outrage.store_duckdb.AUDIT_CHUNK *= 8192*
5613 5613

### outrage.store_duckdb.BATCH *= 64*
5850 5850

### outrage.store_duckdb.BATCH_CEILING *= 4096*
6185 6185

### outrage.store_duckdb.DEFAULT_STORE_DIR *= 'parts'*
6301 6301

### outrage.store_duckdb.MEMORY_LIMIT *= '1GB'*
6570 6570

### outrage.store_duckdb.PART_SUFFIX *= '.parquet'*
7071 7071

### *class* outrage.store_duckdb.DuckdbStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
7297 7297

#### default_filename *: ClassVar[str]* *= 'parts'*
8311 8311

#### backend_name *: ClassVar[str]* *= 'duckdb'*
8810 8810

#### format_version *: ClassVar[int]* *= 2*
9180 9180

#### writable *: ClassVar[bool]* *= False*
9795 9795

#### versioned *: ClassVar[bool]* *= False*
10405 10405

#### reads_patterns *: ClassVar[bool]* *= True*
10941 10941

#### close() → None
11364 11364

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
11953 11955

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
13230 13234

#### exists(key: str) → bool
13938 13944

#### level_entry(key: str) → Entry | None
14122 14130

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
14577 14587

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
15291 15303

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
16070 16084

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
16564 16580

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
17642 17660

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
19722 19742

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
21188 21210

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
22188 22212

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
23223 23249

#### *property* stored_format_version *: int*
24281 24309

#### audit_rows() → Iterator[AuditRow]
24459 24487

#### check_file(report: Report) → None
24872 24902

#### repair() → list[Repaired]
25421 25453
