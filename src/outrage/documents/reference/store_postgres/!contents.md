# outrage.store_postgres
0 0 1

## What is settled at the far end rather than at this one
493 493 11

## Where the store is, inside the database
2179 2179 35

## Round trips
2713 2713 45

## What is *not* here yet
3364 3364 57

### outrage.store_postgres.ARCHIVE_TABLE *= 'document_archive'*
4108 4108 68

### outrage.store_postgres.AUDIT_CHUNK *= 8192*
4377 4377 74

### outrage.store_postgres.BATCH *= 64*
4455 4455 78

### outrage.store_postgres.BATCH_CEILING *= 4096*
4905 4905 87

### outrage.store_postgres.CLIENT_VERSION_SETTING *= 'outrage.client_version'*
5025 5025 91

### outrage.store_postgres.DEFAULT_SERVICE_FILE *= 'pg_service.conf'*
5361 5361 98

### outrage.store_postgres.MIGRATIONS *: Mapping[int, Sequence[str]]* *= {}*
5898 5898 107

### outrage.store_postgres.MIN_SCHEMA_VERSION *= 1*
6583 6583 115

### outrage.store_postgres.READAHEAD *= 1048576*
6861 6861 121

### outrage.store_postgres.SCHEMA_TABLE *= 'outrage_schema'*
7485 7485 132

### outrage.store_postgres.SCHEMA_VERSION *= 1*
7598 7598 136

### outrage.store_postgres.VERSIONS *: Mapping[int, SchemaVersion]* *= {1: SchemaVersion(version=1, read_floor=1, write_floor=1)}*
7785 7785 141

### *class* outrage.store_postgres.Compatibility(stored: SchemaVersion, operating: int, writable: bool)
8520 8520 151

#### stored *: SchemaVersion*
9082 9082 161

#### operating *: int*
9249 9249 165

#### writable *: bool*
9677 9677 174

#### *property* read_only_reason *: Refusal | None*
9813 9813 178

### *class* outrage.store_postgres.PostgresStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True, report: bool = False)
10038 10038 182

#### default_filename *: ClassVar[str]* *= 'pg_service.conf'*
11346 11346 188

#### backend_name *: ClassVar[str]* *= 'postgres'*
11855 11855 196

#### format_version *: ClassVar[int]* *= 1*
12227 12227 202

#### writable *: ClassVar[bool]* *= True*
12846 12846 210

#### versioned *: ClassVar[bool]* *= True*
13205 13205 216

#### manages_schema *: ClassVar[bool]* *= True*
13501 13501 221

#### locates_own_store *: ClassVar[bool]* *= True*
13944 13944 228

#### service_name
14510 14510 236

#### service
14577 14577 240

#### path
14763 14763 245

#### versioning
14966 14966 251

#### problem *: Refusal | None*
15024 15024 255

#### encoding
15273 15273 260

#### schema
15452 15452 266

#### stored *: SchemaVersion | None*
15529 15529 270

#### compatibility *: Compatibility | None*
15781 15781 275

#### *static* service_file(directory: str | PathLike[str] | None, filename: str | PathLike[str] | None) → Path | None
16013 16013 280

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Self
17598 17600 299

#### *classmethod* reporting(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None) → Self
19638 19642 310

#### close() → None
20876 20882 319

#### *property* has_store *: bool*
21519 21527 333

#### schema_state() → SchemaState
21672 21680 337

#### create_schema(version: int | None = None) → SchemaVersion
22011 22021 345

#### *property* stored_format_version *: int*
22954 22966 361

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
23394 23406 370

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
25116 25130 387

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
26200 26216 399

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
26588 26606 403

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
27184 27204 412

#### exists(key: str) → bool
27899 27921 420

#### level_entry(key: str) → Entry | None
28090 28114 424

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
28561 28587 432

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
30003 30031 442

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
31554 31584 459

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
33269 33301 474

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
34351 34385 483

#### audit_rows() → Iterator[AuditRow]
35378 35414 490

#### check_file(report: Report) → None
35807 35845 499

#### repair() → list[Repaired]
36567 36607 513

### *exception* outrage.store_postgres.ServiceUnusable(code: str, \*\*details: Any)
37367 37409 527

### outrage.store_postgres.compatibility(stored: SchemaVersion) → Compatibility
38184 38226 540
