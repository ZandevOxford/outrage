# outrage.store_postgres
0 0 1

## What is settled at the far end rather than at this one
654 654 14

## Where the store is, inside the database
2682 2682 42

## Round trips
3216 3216 52

## Concurrent writers
3867 3867 64

## A backup is a SQLite file
5021 5021 85

### outrage.store_postgres.ARCHIVE_TABLE *= 'document_archive'*
5398 5398 92

### outrage.store_postgres.AUDIT_CHUNK *= 8192*
5687 5687 98

### outrage.store_postgres.BATCH *= 64*
5765 5765 102

### outrage.store_postgres.BATCH_CEILING *= 4096*
6215 6215 111

### outrage.store_postgres.CLIENT_VERSION_SETTING *= 'outrage.client_version'*
6335 6335 115

### outrage.store_postgres.DEFAULT_SERVICE_FILE *= 'pg_service.conf'*
6674 6674 122

### outrage.store_postgres.MIGRATIONS *: Mapping[int, Sequence[str]]* *= {}*
7211 7211 131

### outrage.store_postgres.MIN_SCHEMA_VERSION *= 1*
7896 7896 139

### outrage.store_postgres.POOL_IDLE *= 4*
8174 8174 145

### outrage.store_postgres.READAHEAD *= 1048576*
8500 8500 152

### outrage.store_postgres.RETRY_PAUSE *= 0.01*
9124 9124 163

### outrage.store_postgres.SCHEMA_TABLE *= 'outrage_schema'*
9345 9345 169

### outrage.store_postgres.SCHEMA_VERSION *= 1*
9458 9458 173

### outrage.store_postgres.TRIGGER_NAMES *= ('outrage_write_floor', 'outrage_archive_update', 'outrage_archive_delete')*
9645 9645 178

### outrage.store_postgres.VERSIONING_OFF *= 'off'*
9835 9835 182

### outrage.store_postgres.VERSIONING_SETTING *= 'outrage.versioning'*
10001 10001 186

### outrage.store_postgres.VERSIONS *: Mapping[int, SchemaVersion]* *= {1: SchemaVersion(version=1, read_floor=1, write_floor=1)}*
10431 10431 194

### outrage.store_postgres.WRITE_ATTEMPTS *= 5*
11166 11166 204

### outrage.store_postgres.WRITE_FLOOR_SQLSTATE *= 'OR001'*
11490 11490 211

### *class* outrage.store_postgres.Compatibility(stored: SchemaVersion, operating: int, writable: bool)
11840 11840 218

#### stored *: SchemaVersion*
12402 12402 228

#### operating *: int*
12569 12569 232

#### writable *: bool*
12997 12997 241

#### *property* read_only_reason *: Refusal | None*
13133 13133 245

### *class* outrage.store_postgres.PostgresStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True, report: bool = False, create: bool = True)
13358 13358 249

#### default_filename *: ClassVar[str]* *= 'pg_service.conf'*
14745 14745 255

#### backend_name *: ClassVar[str]* *= 'postgres'*
15254 15254 263

#### format_version *: ClassVar[int]* *= 1*
15626 15626 269

#### writable *: ClassVar[bool]* *= True*
16245 16245 277

#### versioned *: ClassVar[bool]* *= True*
16604 16604 283

#### manages_schema *: ClassVar[bool]* *= True*
16881 16881 288

#### locates_own_store *: ClassVar[bool]* *= True*
17324 17324 295

#### service_name
17890 17890 303

#### service
17957 17957 307

#### path
18143 18143 312

#### versioning
18346 18346 318

#### problem *: Refusal | None*
18541 18541 323

#### encoding
18790 18790 328

#### schema
18969 18969 334

#### stored *: SchemaVersion | None*
19046 19046 338

#### compatibility *: Compatibility | None*
19298 19298 343

#### *static* service_file(directory: str | PathLike[str] | None, filename: str | PathLike[str] | None) → Path | None
19530 19530 348

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, create: bool = True) → Self
21115 21117 367

#### *classmethod* reporting(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None) → Self
23355 23359 380

#### *property* target *: dict[str, str]*
24593 24599 389

#### close() → None
25090 25096 397

#### *property* has_store *: bool*
25741 25749 411

#### schema_state() → SchemaState
25894 25902 415

#### create_schema(version: int | None = None) → SchemaVersion
26233 26243 423

#### *property* stored_format_version *: int*
27176 27188 439

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
27616 27628 448

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
29338 29352 465

#### now(key: str = keys.ROOT, \*, key_range: KeyRange = UNBOUNDED) → str
30786 30802 483

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
31927 31945 503

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
32315 32335 507

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
32911 32933 516

#### exists(key: str) → bool
33626 33650 524

#### level_entry(key: str) → Entry | None
33817 33843 528

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
34288 34316 536

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
35730 35760 546

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
37281 37313 563

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
38996 39030 578

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
40078 40114 587

#### audit_rows() → Iterator[AuditRow]
41105 41143 594

#### *property* backup_suffix *: str*
41534 41574 603

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
41860 41900 611

#### check_file(report: Report) → None
43509 43551 636

#### repair() → list[Repaired]
44574 44618 654

### *exception* outrage.store_postgres.ServiceUnusable(code: str, \*\*details: Any)
45041 45087 664

### outrage.store_postgres.compatibility(stored: SchemaVersion) → Compatibility
45858 45904 677
