# outrage.store_sqlite
0 0 1

### outrage.store_sqlite.ARCHIVE_TABLE *= 'document_archive'*
1857 1857 31

### outrage.store_sqlite.BUSY_TIMEOUT_MS *= 5000*
2953 2953 53

### outrage.store_sqlite.CHILD_BATCH *= 8*
3297 3297 60

### outrage.store_sqlite.CHILD_BATCH_CEILING *= 256*
3907 3907 71

### outrage.store_sqlite.DEFAULT_STORE_FILE *= 'store.sqlite'*
4082 4082 76

### outrage.store_sqlite.LENGTH_CACHE_TABLE *= 'document_lengths'*
4516 4516 84

### outrage.store_sqlite.LENGTH_THRESHOLD *= 2048*
5015 5015 93

### outrage.store_sqlite.SCHEMA_VERSION *= 7*
5659 5659 104

### outrage.store_sqlite.WAL_RATIO *= 1.0*
5970 5970 111

### *class* outrage.store_sqlite.SqliteStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True)
6238 6238 117

#### default_filename *: ClassVar[str]* *= 'store.sqlite'*
7298 7298 123

#### backend_name *: ClassVar[str]* *= 'sqlite'*
7804 7804 131

#### format_version *: ClassVar[int]* *= 7*
8174 8174 137

#### writable *: ClassVar[bool]* *= True*
8789 8789 145

#### versioned *: ClassVar[bool]* *= True*
9218 9218 152

#### *property* connection *: Connection*
9526 9526 157

#### close() → None
10377 10377 172

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
10814 10816 182

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
12253 12257 195

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
13460 13466 211

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
14286 14294 224

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
15545 15555 244

#### exists(key: str) → bool
16382 16394 254

#### level_entry(key: str) → Entry | None
16745 16759 262

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
17210 17226 271

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
18803 18821 284

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
20746 20766 308

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
22215 22237 318

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
24358 24382 347

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
25457 25483 355

#### *property* stored_format_version *: int*
26391 26419 368

#### audit_rows() → Iterator[AuditRow]
26553 26581 372

#### check_file(report: Report) → None
26962 26992 380

#### repair() → list[Repaired]
27357 27389 388
