# outrage.store_postgres
0 0 1

## What is settled at the far end rather than at this one
654 654 14

## Where the store is, inside the database
2581 2581 40

## Round trips
3115 3115 50

## Concurrent writers
3766 3766 62

## A backup is a SQLite file
4920 4920 83

### outrage.store_postgres.ARCHIVE_TABLE *= 'document_archive'*
5297 5297 90

### outrage.store_postgres.AUDIT_CHUNK *= 8192*
5586 5586 96

### outrage.store_postgres.BATCH *= 64*
5664 5664 100

### outrage.store_postgres.BATCH_CEILING *= 4096*
6114 6114 109

### outrage.store_postgres.CLIENT_VERSION_SETTING *= 'outrage.client_version'*
6234 6234 113

### outrage.store_postgres.DEFAULT_SERVICE_FILE *= 'pg_service.conf'*
6573 6573 120

### outrage.store_postgres.MIGRATIONS *: Mapping[int, Sequence[str]]* *= {}*
7110 7110 129

### outrage.store_postgres.MIN_SCHEMA_VERSION *= 1*
7795 7795 137

### outrage.store_postgres.READAHEAD *= 1048576*
8073 8073 143

### outrage.store_postgres.RETRY_PAUSE *= 0.01*
8697 8697 154

### outrage.store_postgres.SCHEMA_TABLE *= 'outrage_schema'*
8918 8918 160

### outrage.store_postgres.SCHEMA_VERSION *= 1*
9031 9031 164

### outrage.store_postgres.TRIGGER_NAMES *= ('outrage_write_floor', 'outrage_archive_update', 'outrage_archive_delete')*
9218 9218 169

### outrage.store_postgres.VERSIONING_OFF *= 'off'*
9408 9408 173

### outrage.store_postgres.VERSIONING_SETTING *= 'outrage.versioning'*
9574 9574 177

### outrage.store_postgres.VERSIONS *: Mapping[int, SchemaVersion]* *= {1: SchemaVersion(version=1, read_floor=1, write_floor=1)}*
10004 10004 185

### outrage.store_postgres.WRITE_ATTEMPTS *= 5*
10739 10739 195

### outrage.store_postgres.WRITE_FLOOR_SQLSTATE *= 'OR001'*
11063 11063 202

### *class* outrage.store_postgres.Compatibility(stored: SchemaVersion, operating: int, writable: bool)
11413 11413 209

#### stored *: SchemaVersion*
11975 11975 219

#### operating *: int*
12142 12142 223

#### writable *: bool*
12570 12570 232

#### *property* read_only_reason *: Refusal | None*
12706 12706 236

### *class* outrage.store_postgres.PostgresStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True, report: bool = False, create: bool = True)
12931 12931 240

#### default_filename *: ClassVar[str]* *= 'pg_service.conf'*
14318 14318 246

#### backend_name *: ClassVar[str]* *= 'postgres'*
14827 14827 254

#### format_version *: ClassVar[int]* *= 1*
15199 15199 260

#### writable *: ClassVar[bool]* *= True*
15818 15818 268

#### versioned *: ClassVar[bool]* *= True*
16177 16177 274

#### manages_schema *: ClassVar[bool]* *= True*
16454 16454 279

#### locates_own_store *: ClassVar[bool]* *= True*
16897 16897 286

#### service_name
17463 17463 294

#### service
17530 17530 298

#### path
17716 17716 303

#### versioning
17919 17919 309

#### problem *: Refusal | None*
18114 18114 314

#### encoding
18363 18363 319

#### schema
18542 18542 325

#### stored *: SchemaVersion | None*
18619 18619 329

#### compatibility *: Compatibility | None*
18871 18871 334

#### *static* service_file(directory: str | PathLike[str] | None, filename: str | PathLike[str] | None) → Path | None
19103 19103 339

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, create: bool = True) → Self
20688 20690 358

#### *classmethod* reporting(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None) → Self
22928 22932 371

#### *property* target *: dict[str, str]*
24166 24172 380

#### close() → None
24663 24669 388

#### *property* has_store *: bool*
25306 25314 402

#### schema_state() → SchemaState
25459 25467 406

#### create_schema(version: int | None = None) → SchemaVersion
25798 25808 414

#### *property* stored_format_version *: int*
26741 26753 430

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
27181 27193 439

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
28903 28917 456

#### now(key: str = keys.ROOT, \*, key_range: KeyRange = UNBOUNDED) → str
30351 30367 474

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
30741 30759 481

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
31129 31149 485

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
31725 31747 494

#### exists(key: str) → bool
32440 32464 502

#### level_entry(key: str) → Entry | None
32631 32657 506

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
33102 33130 514

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
34544 34574 524

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
36095 36127 541

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
37810 37844 556

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
38892 38928 565

#### audit_rows() → Iterator[AuditRow]
39919 39957 572

#### *property* backup_suffix *: str*
40348 40388 581

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
40674 40714 589

#### check_file(report: Report) → None
42323 42365 614

#### repair() → list[Repaired]
43388 43432 632

### *exception* outrage.store_postgres.ServiceUnusable(code: str, \*\*details: Any)
43855 43901 642

### outrage.store_postgres.compatibility(stored: SchemaVersion) → Compatibility
44672 44718 655
