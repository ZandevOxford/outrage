# outrage.store_postgres
0 0 1

## What is settled at the far end rather than at this one
493 493 11

## Where the store is, inside the database
2420 2420 37

## Round trips
2954 2954 47

## Concurrent writers
3605 3605 59

## A backup is a SQLite file
4759 4759 80

### outrage.store_postgres.ARCHIVE_TABLE *= 'document_archive'*
5136 5136 87

### outrage.store_postgres.AUDIT_CHUNK *= 8192*
5425 5425 93

### outrage.store_postgres.BATCH *= 64*
5503 5503 97

### outrage.store_postgres.BATCH_CEILING *= 4096*
5953 5953 106

### outrage.store_postgres.CLIENT_VERSION_SETTING *= 'outrage.client_version'*
6073 6073 110

### outrage.store_postgres.DEFAULT_SERVICE_FILE *= 'pg_service.conf'*
6412 6412 117

### outrage.store_postgres.MIGRATIONS *: Mapping[int, Sequence[str]]* *= {}*
6949 6949 126

### outrage.store_postgres.MIN_SCHEMA_VERSION *= 1*
7634 7634 134

### outrage.store_postgres.READAHEAD *= 1048576*
7912 7912 140

### outrage.store_postgres.RETRY_PAUSE *= 0.01*
8536 8536 151

### outrage.store_postgres.SCHEMA_TABLE *= 'outrage_schema'*
8757 8757 157

### outrage.store_postgres.SCHEMA_VERSION *= 1*
8870 8870 161

### outrage.store_postgres.TRIGGER_NAMES *= ('outrage_write_floor', 'outrage_archive_update', 'outrage_archive_delete')*
9057 9057 166

### outrage.store_postgres.VERSIONING_OFF *= 'off'*
9247 9247 170

### outrage.store_postgres.VERSIONING_SETTING *= 'outrage.versioning'*
9413 9413 174

### outrage.store_postgres.VERSIONS *: Mapping[int, SchemaVersion]* *= {1: SchemaVersion(version=1, read_floor=1, write_floor=1)}*
9843 9843 182

### outrage.store_postgres.WRITE_ATTEMPTS *= 5*
10578 10578 192

### outrage.store_postgres.WRITE_FLOOR_SQLSTATE *= 'OR001'*
10902 10902 199

### *class* outrage.store_postgres.Compatibility(stored: SchemaVersion, operating: int, writable: bool)
11252 11252 206

#### stored *: SchemaVersion*
11814 11814 216

#### operating *: int*
11981 11981 220

#### writable *: bool*
12409 12409 229

#### *property* read_only_reason *: Refusal | None*
12545 12545 233

### *class* outrage.store_postgres.PostgresStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True, report: bool = False, create: bool = True)
12770 12770 237

#### default_filename *: ClassVar[str]* *= 'pg_service.conf'*
14157 14157 243

#### backend_name *: ClassVar[str]* *= 'postgres'*
14666 14666 251

#### format_version *: ClassVar[int]* *= 1*
15038 15038 257

#### writable *: ClassVar[bool]* *= True*
15657 15657 265

#### versioned *: ClassVar[bool]* *= True*
16016 16016 271

#### manages_schema *: ClassVar[bool]* *= True*
16293 16293 276

#### locates_own_store *: ClassVar[bool]* *= True*
16736 16736 283

#### service_name
17302 17302 291

#### service
17369 17369 295

#### path
17555 17555 300

#### versioning
17758 17758 306

#### problem *: Refusal | None*
17953 17953 311

#### encoding
18202 18202 316

#### schema
18381 18381 322

#### stored *: SchemaVersion | None*
18458 18458 326

#### compatibility *: Compatibility | None*
18710 18710 331

#### *static* service_file(directory: str | PathLike[str] | None, filename: str | PathLike[str] | None) → Path | None
18942 18942 336

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, create: bool = True) → Self
20527 20529 355

#### *classmethod* reporting(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None) → Self
22767 22771 368

#### *property* target *: dict[str, str]*
24005 24011 377

#### close() → None
24502 24508 385

#### *property* has_store *: bool*
25145 25153 399

#### schema_state() → SchemaState
25298 25306 403

#### create_schema(version: int | None = None) → SchemaVersion
25637 25647 411

#### *property* stored_format_version *: int*
26580 26592 427

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
27020 27032 436

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
28742 28756 453

#### now(key: str = keys.ROOT, \*, key_range: KeyRange = UNBOUNDED) → str
30190 30206 471

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
30580 30598 478

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
30968 30988 482

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
31564 31586 491

#### exists(key: str) → bool
32279 32303 499

#### level_entry(key: str) → Entry | None
32470 32496 503

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
32941 32969 511

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
34383 34413 521

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
35934 35966 538

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
37649 37683 553

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
38731 38767 562

#### audit_rows() → Iterator[AuditRow]
39758 39796 569

#### *property* backup_suffix *: str*
40187 40227 578

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
40513 40553 586

#### check_file(report: Report) → None
42162 42204 611

#### repair() → list[Repaired]
43227 43271 629

### *exception* outrage.store_postgres.ServiceUnusable(code: str, \*\*details: Any)
43694 43740 639

### outrage.store_postgres.compatibility(stored: SchemaVersion) → Compatibility
44511 44557 652
