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
4518 4518 78

### outrage.store_postgres.ARCHIVE_TABLE *= 'document_archive'*
5054 5054 86

### outrage.store_postgres.AUDIT_CHUNK *= 8192*
5343 5343 92

### outrage.store_postgres.BATCH *= 64*
5421 5421 96

### outrage.store_postgres.BATCH_CEILING *= 4096*
5871 5871 105

### outrage.store_postgres.CLIENT_VERSION_SETTING *= 'outrage.client_version'*
5991 5991 109

### outrage.store_postgres.DEFAULT_SERVICE_FILE *= 'pg_service.conf'*
6330 6330 116

### outrage.store_postgres.MIGRATIONS *: Mapping[int, Sequence[str]]* *= {}*
6867 6867 125

### outrage.store_postgres.MIN_SCHEMA_VERSION *= 1*
7552 7552 133

### outrage.store_postgres.READAHEAD *= 1048576*
7830 7830 139

### outrage.store_postgres.RETRY_PAUSE *= 0.01*
8454 8454 150

### outrage.store_postgres.SCHEMA_TABLE *= 'outrage_schema'*
8675 8675 156

### outrage.store_postgres.SCHEMA_VERSION *= 1*
8788 8788 160

### outrage.store_postgres.VERSIONING_OFF *= 'off'*
8975 8975 165

### outrage.store_postgres.VERSIONING_SETTING *= 'outrage.versioning'*
9141 9141 169

### outrage.store_postgres.VERSIONS *: Mapping[int, SchemaVersion]* *= {1: SchemaVersion(version=1, read_floor=1, write_floor=1)}*
9571 9571 177

### outrage.store_postgres.WRITE_ATTEMPTS *= 5*
10306 10306 187

### outrage.store_postgres.WRITE_FLOOR_SQLSTATE *= 'OR001'*
10630 10630 194

### *class* outrage.store_postgres.Compatibility(stored: SchemaVersion, operating: int, writable: bool)
10980 10980 201

#### stored *: SchemaVersion*
11542 11542 211

#### operating *: int*
11709 11709 215

#### writable *: bool*
12137 12137 224

#### *property* read_only_reason *: Refusal | None*
12273 12273 228

### *class* outrage.store_postgres.PostgresStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True, report: bool = False)
12498 12498 232

#### default_filename *: ClassVar[str]* *= 'pg_service.conf'*
13806 13806 238

#### backend_name *: ClassVar[str]* *= 'postgres'*
14315 14315 246

#### format_version *: ClassVar[int]* *= 1*
14687 14687 252

#### writable *: ClassVar[bool]* *= True*
15306 15306 260

#### versioned *: ClassVar[bool]* *= True*
15665 15665 266

#### manages_schema *: ClassVar[bool]* *= True*
15942 15942 271

#### locates_own_store *: ClassVar[bool]* *= True*
16385 16385 278

#### service_name
16951 16951 286

#### service
17018 17018 290

#### path
17204 17204 295

#### versioning
17407 17407 301

#### problem *: Refusal | None*
17602 17602 306

#### encoding
17851 17851 311

#### schema
18030 18030 317

#### stored *: SchemaVersion | None*
18107 18107 321

#### compatibility *: Compatibility | None*
18359 18359 326

#### *static* service_file(directory: str | PathLike[str] | None, filename: str | PathLike[str] | None) → Path | None
18591 18591 331

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Self
20176 20178 350

#### *classmethod* reporting(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None) → Self
22216 22220 361

#### close() → None
23454 23460 370

#### *property* has_store *: bool*
24097 24105 384

#### schema_state() → SchemaState
24250 24258 388

#### create_schema(version: int | None = None) → SchemaVersion
24589 24599 396

#### *property* stored_format_version *: int*
25532 25544 412

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
25972 25984 421

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
27694 27708 438

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
29142 29158 456

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
29530 29548 460

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
30126 30146 469

#### exists(key: str) → bool
30841 30863 477

#### level_entry(key: str) → Entry | None
31032 31056 481

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
31503 31529 489

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
32945 32973 499

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
34496 34526 516

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
36211 36243 531

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
37293 37327 540

#### audit_rows() → Iterator[AuditRow]
38320 38356 547

#### check_file(report: Report) → None
38749 38787 556

#### repair() → list[Repaired]
39509 39549 570

### *exception* outrage.store_postgres.ServiceUnusable(code: str, \*\*details: Any)
40309 40351 584

### outrage.store_postgres.compatibility(stored: SchemaVersion) → Compatibility
41126 41168 597
