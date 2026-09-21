# outrage.store_postgres
0 0 1

## What is settled at the far end rather than at this one
493 493 11

## Where the store is, inside the database
2179 2179 35

## Round trips
2713 2713 45

## Concurrent writers
3364 3364 57

## What is *not* here yet
4475 4475 77

### outrage.store_postgres.ARCHIVE_TABLE *= 'document_archive'*
5011 5011 85

### outrage.store_postgres.AUDIT_CHUNK *= 8192*
5300 5300 91

### outrage.store_postgres.BATCH *= 64*
5378 5378 95

### outrage.store_postgres.BATCH_CEILING *= 4096*
5828 5828 104

### outrage.store_postgres.CLIENT_VERSION_SETTING *= 'outrage.client_version'*
5948 5948 108

### outrage.store_postgres.DEFAULT_SERVICE_FILE *= 'pg_service.conf'*
6287 6287 115

### outrage.store_postgres.MIGRATIONS *: Mapping[int, Sequence[str]]* *= {}*
6824 6824 124

### outrage.store_postgres.MIN_SCHEMA_VERSION *= 1*
7509 7509 132

### outrage.store_postgres.READAHEAD *= 1048576*
7787 7787 138

### outrage.store_postgres.RETRY_PAUSE *= 0.01*
8411 8411 149

### outrage.store_postgres.SCHEMA_TABLE *= 'outrage_schema'*
8632 8632 155

### outrage.store_postgres.SCHEMA_VERSION *= 1*
8745 8745 159

### outrage.store_postgres.VERSIONING_OFF *= 'off'*
8932 8932 164

### outrage.store_postgres.VERSIONING_SETTING *= 'outrage.versioning'*
9098 9098 168

### outrage.store_postgres.VERSIONS *: Mapping[int, SchemaVersion]* *= {1: SchemaVersion(version=1, read_floor=1, write_floor=1)}*
9528 9528 176

### outrage.store_postgres.WRITE_ATTEMPTS *= 5*
10263 10263 186

### outrage.store_postgres.WRITE_FLOOR_SQLSTATE *= 'OR001'*
10587 10587 193

### *class* outrage.store_postgres.Compatibility(stored: SchemaVersion, operating: int, writable: bool)
10937 10937 200

#### stored *: SchemaVersion*
11499 11499 210

#### operating *: int*
11666 11666 214

#### writable *: bool*
12094 12094 223

#### *property* read_only_reason *: Refusal | None*
12230 12230 227

### *class* outrage.store_postgres.PostgresStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True, report: bool = False)
12455 12455 231

#### default_filename *: ClassVar[str]* *= 'pg_service.conf'*
13763 13763 237

#### backend_name *: ClassVar[str]* *= 'postgres'*
14272 14272 245

#### format_version *: ClassVar[int]* *= 1*
14644 14644 251

#### writable *: ClassVar[bool]* *= True*
15263 15263 259

#### versioned *: ClassVar[bool]* *= True*
15622 15622 265

#### manages_schema *: ClassVar[bool]* *= True*
15899 15899 270

#### locates_own_store *: ClassVar[bool]* *= True*
16342 16342 277

#### service_name
16908 16908 285

#### service
16975 16975 289

#### path
17161 17161 294

#### versioning
17364 17364 300

#### problem *: Refusal | None*
17559 17559 305

#### encoding
17808 17808 310

#### schema
17987 17987 316

#### stored *: SchemaVersion | None*
18064 18064 320

#### compatibility *: Compatibility | None*
18316 18316 325

#### *static* service_file(directory: str | PathLike[str] | None, filename: str | PathLike[str] | None) → Path | None
18548 18548 330

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Self
20133 20135 349

#### *classmethod* reporting(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None) → Self
22173 22177 360

#### close() → None
23411 23417 369

#### *property* has_store *: bool*
24054 24062 383

#### schema_state() → SchemaState
24207 24215 387

#### create_schema(version: int | None = None) → SchemaVersion
24546 24556 395

#### *property* stored_format_version *: int*
25489 25501 411

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
25929 25941 420

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
27651 27665 437

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
29099 29115 455

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
29487 29505 459

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
30083 30103 468

#### exists(key: str) → bool
30798 30820 476

#### level_entry(key: str) → Entry | None
30989 31013 480

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
31460 31486 488

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
32902 32930 498

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
34453 34483 515

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
36168 36200 530

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
37250 37284 539

#### audit_rows() → Iterator[AuditRow]
38277 38313 546

#### check_file(report: Report) → None
38706 38744 555

#### repair() → list[Repaired]
39466 39506 569

### *exception* outrage.store_postgres.ServiceUnusable(code: str, \*\*details: Any)
40266 40308 583

### outrage.store_postgres.compatibility(stored: SchemaVersion) → Compatibility
41083 41125 596
