# outrage.store_postgres
0 0 1

## What is settled at the far end rather than at this one
493 493 11

## Where the store is, inside the database
2179 2179 35

## What is *not* here yet
2713 2713 45

### outrage.store_postgres.ARCHIVE_TABLE *= 'document_archive'*
3311 3311 55

### outrage.store_postgres.CLIENT_VERSION_SETTING *= 'outrage.client_version'*
3580 3580 61

### outrage.store_postgres.DEFAULT_SERVICE_FILE *= 'pg_service.conf'*
3916 3916 68

### outrage.store_postgres.MIGRATIONS *: Mapping[int, Sequence[str]]* *= {}*
4453 4453 77

### outrage.store_postgres.MIN_SCHEMA_VERSION *= 1*
5138 5138 85

### outrage.store_postgres.SCHEMA_TABLE *= 'outrage_schema'*
5416 5416 91

### outrage.store_postgres.SCHEMA_VERSION *= 1*
5529 5529 95

### outrage.store_postgres.VERSIONS *: Mapping[int, SchemaVersion]* *= {1: SchemaVersion(version=1, read_floor=1, write_floor=1)}*
5716 5716 100

### *class* outrage.store_postgres.Compatibility(stored: SchemaVersion, operating: int, writable: bool)
6451 6451 110

#### stored *: SchemaVersion*
7013 7013 120

#### operating *: int*
7180 7180 124

#### writable *: bool*
7608 7608 133

#### *property* read_only_reason *: Refusal | None*
7744 7744 137

### *class* outrage.store_postgres.PostgresStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, versioning: bool = True, report: bool = False)
7969 7969 141

#### default_filename *: ClassVar[str]* *= 'pg_service.conf'*
9277 9277 147

#### backend_name *: ClassVar[str]* *= 'postgres'*
9786 9786 155

#### format_version *: ClassVar[int]* *= 1*
10158 10158 161

#### writable *: ClassVar[bool]* *= True*
10777 10777 169

#### versioned *: ClassVar[bool]* *= True*
11136 11136 175

#### manages_schema *: ClassVar[bool]* *= True*
11432 11432 180

#### locates_own_store *: ClassVar[bool]* *= True*
11875 11875 187

#### service_name
12441 12441 195

#### service
12508 12508 199

#### path
12694 12694 204

#### versioning
12897 12897 210

#### problem *: Refusal | None*
12955 12955 214

#### encoding
13204 13204 219

#### schema
13383 13383 225

#### stored *: SchemaVersion | None*
13460 13460 229

#### compatibility *: Compatibility | None*
13712 13712 234

#### *static* service_file(directory: str | PathLike[str] | None, filename: str | PathLike[str] | None) → Path | None
13944 13944 239

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Self
15529 15531 258

#### *classmethod* reporting(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, service: str | None = None, log: EventLog | None = None) → Self
17569 17573 269

#### close() → None
18807 18813 278

#### *property* has_store *: bool*
19450 19458 292

#### schema_state() → SchemaState
19603 19611 296

#### create_schema(version: int | None = None) → SchemaVersion
19942 19952 304

#### *property* stored_format_version *: int*
20885 20897 320

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
21325 21337 329

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
22607 22621 338

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED) → int
23248 23264 342

#### subtree_totals(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED) → SubtreeTotals
24910 24928 372

#### latest_change(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED) → str | None
27611 27631 418

#### exists(key: str) → bool
29584 29606 450

#### level_entry(key: str) → Entry | None
30079 30103 461

#### retrieve_document(key: str, \*, offset: int = 0, max_chars: int = DEFAULT_MAX_CHARS, \*\*rest: Any) → Excerpt
30972 30998 476

#### list_keys(key: str | None = None, \*\*rest: Any) → Page
32392 32420 498

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, max_chars: int = DEFAULT_BULK_MAX_CHARS, \*\*rest: Any) → Page
34971 35001 545

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*\*rest: Any) → MissingMeta
36401 36433 571

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*\*rest: Any) → Page
38108 38142 600

#### audit_rows() → Iterator[AuditRow]
38749 38785 612

#### check_file(report: Report) → None
39483 39521 625

#### repair() → list[Repaired]
40243 40283 639

### *exception* outrage.store_postgres.ServiceUnusable(code: str, \*\*details: Any)
41043 41085 653

### outrage.store_postgres.compatibility(stored: SchemaVersion) → Compatibility
41860 41902 666
