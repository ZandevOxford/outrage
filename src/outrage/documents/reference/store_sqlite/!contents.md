# outrage.store_sqlite
0 0

### outrage.store_sqlite.BUSY_TIMEOUT_MS *= 5000*
1660 1660

### outrage.store_sqlite.DEFAULT_STORE_FILE *= 'store.sqlite'*
2083 2083

### outrage.store_sqlite.LENGTH_CACHE_TABLE *= 'document_lengths'*
2517 2517

### outrage.store_sqlite.LENGTH_THRESHOLD *= 2048*
3016 3016

### outrage.store_sqlite.SCHEMA_VERSION *= 6*
3660 3660

### outrage.store_sqlite.WAL_RATIO *= 1.0*
3971 3971

### *class* outrage.store_sqlite.SqliteStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
4239 4239

#### default_filename *: ClassVar[str]* *= 'store.sqlite'*
5207 5207

#### backend_name *: ClassVar[str]* *= 'sqlite'*
5712 5712

#### format_version *: ClassVar[int]* *= 6*
6081 6081

#### writable *: ClassVar[bool]* *= True*
6695 6695

#### *property* connection *: Connection*
7123 7123

#### close() → None
7974 7974

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
8410 8412

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
9682 9686

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
10882 10888

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
11705 11713

#### exists(key: str) → bool
12538 12548

#### level_entry(key: str) → Entry | None
12899 12911

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
13362 13376

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None) → Page[Entry]
14664 14680

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
15564 15582

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
17023 17043

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
19081 19103

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
20173 20197

#### *property* stored_format_version *: int*
21103 21129

#### audit_rows() → Iterator[AuditRow]
21264 21290

#### check_file(report: Report) → None
21673 21701

#### repair() → list[Repaired]
22067 22097
