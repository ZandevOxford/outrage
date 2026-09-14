# outrage.store_duckdb
0 0

### outrage.store_duckdb.AUDIT_CHUNK *= 8192*
5632 5632

### outrage.store_duckdb.BATCH *= 64*
5869 5869

### outrage.store_duckdb.BATCH_CEILING *= 4096*
6204 6204

### outrage.store_duckdb.DEFAULT_STORE_DIR *= 'parts'*
6320 6320

### outrage.store_duckdb.MEMORY_LIMIT *= '1GB'*
6589 6589

### outrage.store_duckdb.PART_SUFFIX *= '.parquet'*
7090 7090

### *class* outrage.store_duckdb.DuckdbStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
7316 7316

#### default_filename *: ClassVar[str]* *= 'parts'*
8330 8330

#### backend_name *: ClassVar[str]* *= 'duckdb'*
8829 8829

#### format_version *: ClassVar[int]* *= 2*
9199 9199

#### writable *: ClassVar[bool]* *= False*
9814 9814

#### versioned *: ClassVar[bool]* *= False*
10424 10424

#### reads_patterns *: ClassVar[bool]* *= True*
10960 10960

#### close() → None
11383 11383

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
11972 11974

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
13249 13253

#### exists(key: str) → bool
13957 13963

#### level_entry(key: str) → Entry | None
14141 14149

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
14596 14606

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
15310 15322

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
16089 16103

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
16583 16599

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
17661 17679

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
19741 19761

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
21207 21229

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
22207 22231

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
23242 23268

#### *property* stored_format_version *: int*
24300 24328

#### audit_rows() → Iterator[AuditRow]
24478 24506

#### check_file(report: Report) → None
24891 24921

#### repair() → list[Repaired]
25440 25472
