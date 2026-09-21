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

## What is *not* here yet
4759 4759 80

### outrage.store_postgres.ARCHIVE_TABLE *= 'document_archive'*
5175 5175 87

### outrage.store_postgres.AUDIT_CHUNK *= 8192*
5464 5464 93

### outrage.store_postgres.BATCH *= 64*
5542 5542 97

### outrage.store_postgres.BATCH_CEILING *= 4096*
5992 5992 106

### outrage.store_postgres.CLIENT_VERSION_SETTING *= 'outrage.client_version'*
6112 6112 110

### outrage.store_postgres.DEFAULT_SERVICE_FILE *= 'pg_service.conf'*
6451 6451 117

### outrage.store_postgres.MIGRATIONS *: Mapping[int, Sequence[str]]* *= {}*
6988 6988 126

### outrage.store_postgres.MIN_SCHEMA_VERSION *= 1*
7673 7673 134

### outrage.store_postgres.READAHEAD *= 1048576*
7951 7951 140

### outrage.store_postgres.RETRY_PAUSE *= 0.01*
8575 8575 151

### outrage.store_postgres.SCHEMA_TABLE *= 'outrage_schema'*
8796 8796 157

### outrage.store_postgres.SCHEMA_VERSION *= 1*
8909 8909 161

### outrage.store_postgres.VERSIONING_OFF *= 'off'*
9096 9096 166

### outrage.store_postgres.VERSIONING_SETTING *= 'outrage.versioning'*
9262 9262 170

### outrage.store_postgres.VERSIONS *: Mapping[int, SchemaVersion]* *= {1: SchemaVersion(version=1, read_floor=1, write_floor=1)}*
9692 9692 178

### outrage.store_postgres.WRITE_ATTEMPTS *= 5*
10427 10427 188

### outrage.store_postgres.WRITE_FLOOR_SQLSTATE *= 'OR001'*
10751 10751 195

### *class* outrage.store_postgres.Compatibility(stored: SchemaVersion, operating: int, writable: bool)
11101 11101 202

#### stored *: SchemaVersion*
11663 11663 212

#### operating *: int*
11830 11830 216

#### writable *: bool*
12258 12258 225

#### *property* read_only_reason *: Refusal | None*
12394 12394 229

### *class* outrage.store_postgres.PostgresStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True, report: bool = False, create: bool = True)
12619 12619 233

#### default_filename *: ClassVar[str]* *= 'pg_service.conf'*
14006 14006 239

#### backend_name *: ClassVar[str]* *= 'postgres'*
14515 14515 247

#### format_version *: ClassVar[int]* *= 1*
14887 14887 253

#### writable *: ClassVar[bool]* *= True*
15506 15506 261

#### versioned *: ClassVar[bool]* *= True*
15865 15865 267

#### manages_schema *: ClassVar[bool]* *= True*
16142 16142 272

#### locates_own_store *: ClassVar[bool]* *= True*
16585 16585 279

#### service_name
17151 17151 287

#### service
17218 17218 291

#### path
17404 17404 296

#### versioning
17607 17607 302

#### problem *: Refusal | None*
17802 17802 307

#### encoding
18051 18051 312

#### schema
18230 18230 318

#### stored *: SchemaVersion | None*
18307 18307 322

#### compatibility *: Compatibility | None*
18559 18559 327

#### *static* service_file(directory: str | PathLike[str] | None, filename: str | PathLike[str] | None) → Path | None
18791 18791 332

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, create: bool = True) → Self
20376 20378 351

#### *classmethod* reporting(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None) → Self
22616 22620 364

#### *property* target *: dict[str, str]*
23854 23860 373

#### close() → None
24351 24357 381

#### *property* has_store *: bool*
24994 25002 395

#### schema_state() → SchemaState
25147 25155 399

#### create_schema(version: int | None = None) → SchemaVersion
25486 25496 407

#### *property* stored_format_version *: int*
26429 26441 423

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
26869 26881 432

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
28591 28605 449

#### now(key: str = keys.ROOT, \*, key_range: KeyRange = UNBOUNDED) → str
30039 30055 467

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
30429 30447 474

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
30817 30837 478

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
31413 31435 487

#### exists(key: str) → bool
32128 32152 495

#### level_entry(key: str) → Entry | None
32319 32345 499

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
32790 32818 507

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
34232 34262 517

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
35783 35815 534

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
37498 37532 549

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
38580 38616 558

#### audit_rows() → Iterator[AuditRow]
39607 39645 565

#### check_file(report: Report) → None
40036 40076 574

#### repair() → list[Repaired]
40796 40838 588

### *exception* outrage.store_postgres.ServiceUnusable(code: str, \*\*details: Any)
41596 41640 602

### outrage.store_postgres.compatibility(stored: SchemaVersion) → Compatibility
42413 42457 615
