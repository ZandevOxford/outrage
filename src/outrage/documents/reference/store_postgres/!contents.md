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
5272 5272 88

### outrage.store_postgres.AUDIT_CHUNK *= 8192*
5561 5561 94

### outrage.store_postgres.BATCH *= 64*
5639 5639 98

### outrage.store_postgres.BATCH_CEILING *= 4096*
6089 6089 107

### outrage.store_postgres.CLIENT_VERSION_SETTING *= 'outrage.client_version'*
6209 6209 111

### outrage.store_postgres.DEFAULT_SERVICE_FILE *= 'pg_service.conf'*
6548 6548 118

### outrage.store_postgres.MIGRATIONS *: Mapping[int, Sequence[str]]* *= {}*
7085 7085 127

### outrage.store_postgres.MIN_SCHEMA_VERSION *= 1*
7770 7770 135

### outrage.store_postgres.READAHEAD *= 1048576*
8048 8048 141

### outrage.store_postgres.RETRY_PAUSE *= 0.01*
8672 8672 152

### outrage.store_postgres.SCHEMA_TABLE *= 'outrage_schema'*
8893 8893 158

### outrage.store_postgres.SCHEMA_VERSION *= 1*
9006 9006 162

### outrage.store_postgres.VERSIONING_OFF *= 'off'*
9193 9193 167

### outrage.store_postgres.VERSIONING_SETTING *= 'outrage.versioning'*
9359 9359 171

### outrage.store_postgres.VERSIONS *: Mapping[int, SchemaVersion]* *= {1: SchemaVersion(version=1, read_floor=1, write_floor=1)}*
9789 9789 179

### outrage.store_postgres.WRITE_ATTEMPTS *= 5*
10524 10524 189

### outrage.store_postgres.WRITE_FLOOR_SQLSTATE *= 'OR001'*
10848 10848 196

### *class* outrage.store_postgres.Compatibility(stored: SchemaVersion, operating: int, writable: bool)
11198 11198 203

#### stored *: SchemaVersion*
11760 11760 213

#### operating *: int*
11927 11927 217

#### writable *: bool*
12355 12355 226

#### *property* read_only_reason *: Refusal | None*
12491 12491 230

### *class* outrage.store_postgres.PostgresStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True, report: bool = False)
12716 12716 234

#### default_filename *: ClassVar[str]* *= 'pg_service.conf'*
14024 14024 240

#### backend_name *: ClassVar[str]* *= 'postgres'*
14533 14533 248

#### format_version *: ClassVar[int]* *= 1*
14905 14905 254

#### writable *: ClassVar[bool]* *= True*
15524 15524 262

#### versioned *: ClassVar[bool]* *= True*
15883 15883 268

#### manages_schema *: ClassVar[bool]* *= True*
16160 16160 273

#### locates_own_store *: ClassVar[bool]* *= True*
16603 16603 280

#### service_name
17169 17169 288

#### service
17236 17236 292

#### path
17422 17422 297

#### versioning
17625 17625 303

#### problem *: Refusal | None*
17820 17820 308

#### encoding
18069 18069 313

#### schema
18248 18248 319

#### stored *: SchemaVersion | None*
18325 18325 323

#### compatibility *: Compatibility | None*
18577 18577 328

#### *static* service_file(directory: str | PathLike[str] | None, filename: str | PathLike[str] | None) → Path | None
18809 18809 333

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Self
20394 20396 352

#### *classmethod* reporting(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None) → Self
22434 22438 363

#### close() → None
23672 23678 372

#### *property* has_store *: bool*
24315 24323 386

#### schema_state() → SchemaState
24468 24476 390

#### create_schema(version: int | None = None) → SchemaVersion
24807 24817 398

#### *property* stored_format_version *: int*
25750 25762 414

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
26190 26202 423

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
27912 27926 440

#### now(key: str = keys.ROOT, \*, key_range: KeyRange = UNBOUNDED) → str
29360 29376 458

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
29750 29768 465

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
30138 30158 469

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
30734 30756 478

#### exists(key: str) → bool
31449 31473 486

#### level_entry(key: str) → Entry | None
31640 31666 490

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
32111 32139 498

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
33553 33583 508

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
35104 35136 525

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
36819 36853 540

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
37901 37937 549

#### audit_rows() → Iterator[AuditRow]
38928 38966 556

#### check_file(report: Report) → None
39357 39397 565

#### repair() → list[Repaired]
40117 40159 579

### *exception* outrage.store_postgres.ServiceUnusable(code: str, \*\*details: Any)
40917 40961 593

### outrage.store_postgres.compatibility(stored: SchemaVersion) → Compatibility
41734 41778 606
