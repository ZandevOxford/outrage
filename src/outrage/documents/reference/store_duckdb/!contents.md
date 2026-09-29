# outrage.store_duckdb
0 0 1

### outrage.store_duckdb.AUDIT_CHUNK *= 8192*
5754 5754 88

### outrage.store_duckdb.BATCH *= 64*
5991 5991 94

### outrage.store_duckdb.BATCH_CEILING *= 4096*
6326 6326 101

### outrage.store_duckdb.DEFAULT_STORE_DIR *= 'parts'*
6442 6442 105

### outrage.store_duckdb.MEMORY_LIMIT *= '1GB'*
6711 6711 111

### outrage.store_duckdb.PART_SUFFIX *= '.parquet'*
7212 7212 120

### *class* outrage.store_duckdb.DuckdbStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
7438 7438 126

#### default_filename *: ClassVar[str]* *= 'parts'*
8452 8452 132

#### backend_name *: ClassVar[str]* *= 'duckdb'*
8951 8951 140

#### format_version *: ClassVar[int]* *= 2*
9321 9321 146

#### writable *: ClassVar[bool]* *= False*
9936 9936 154

#### versioned *: ClassVar[bool]* *= False*
10546 10546 164

#### reads_patterns *: ClassVar[bool]* *= True*
11082 11082 173

#### close() → None
11505 11505 180

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
12094 12096 192

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
13371 13375 201

#### exists(key: str) → bool
14079 14085 205

#### level_entry(key: str) → Entry | None
14263 14271 209

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
14718 14728 217

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
15432 15444 227

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
16211 16225 238

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
16705 16721 242

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
18064 18082 251

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
20144 20164 276

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
21610 21632 286

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
22692 22716 295

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
23727 23753 302

#### *property* stored_format_version *: int*
24785 24813 316

#### audit_rows() → Iterator[AuditRow]
24963 24991 320

#### check_file(report: Report) → None
25376 25406 328

#### repair() → list[Repaired]
25925 25957 338
