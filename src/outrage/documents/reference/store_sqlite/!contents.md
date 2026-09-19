# outrage.store_sqlite
0 0 1

### outrage.store_sqlite.ARCHIVE_TABLE *= 'document_archive'*
1660 1660 29

### outrage.store_sqlite.BUSY_TIMEOUT_MS *= 5000*
2756 2756 51

### outrage.store_sqlite.CHILD_BATCH *= 8*
3100 3100 58

### outrage.store_sqlite.CHILD_BATCH_CEILING *= 256*
3710 3710 69

### outrage.store_sqlite.DEFAULT_STORE_FILE *= 'store.sqlite'*
3885 3885 74

### outrage.store_sqlite.LENGTH_CACHE_TABLE *= 'document_lengths'*
4319 4319 82

### outrage.store_sqlite.LENGTH_THRESHOLD *= 2048*
4818 4818 91

### outrage.store_sqlite.SCHEMA_VERSION *= 7*
5462 5462 102

### outrage.store_sqlite.WAL_RATIO *= 1.0*
5773 5773 109

### *class* outrage.store_sqlite.SqliteStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True)
6041 6041 115

#### default_filename *: ClassVar[str]* *= 'store.sqlite'*
7101 7101 121

#### backend_name *: ClassVar[str]* *= 'sqlite'*
7607 7607 129

#### format_version *: ClassVar[int]* *= 7*
7977 7977 135

#### writable *: ClassVar[bool]* *= True*
8592 8592 143

#### versioned *: ClassVar[bool]* *= True*
9021 9021 150

#### *property* connection *: Connection*
9329 9329 155

#### close() → None
10180 10180 170

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
10617 10619 180

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
12056 12060 193

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
13263 13269 209

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
14089 14097 222

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
15348 15358 242

#### exists(key: str) → bool
16185 16197 252

#### level_entry(key: str) → Entry | None
16548 16562 260

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
17013 17029 269

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
18606 18624 282

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
20549 20569 306

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
22018 22040 316

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
24161 24185 345

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
25260 25286 353

#### *property* stored_format_version *: int*
26194 26222 366

#### audit_rows() → Iterator[AuditRow]
26356 26384 370

#### check_file(report: Report) → None
26765 26795 378

#### repair() → list[Repaired]
27160 27192 386
