# outrage.store_parquet
0 0

### outrage.store_parquet.CHUNK *= 8192*
4020 4020

### outrage.store_parquet.COMPRESSION *= 'zstd'*
4348 4348

### outrage.store_parquet.DEFAULT_STORE_FILE *= 'store.parquet'*
4610 4610

### outrage.store_parquet.ENCODABLE *= ('format', 'updated_at')*
4988 4988

### outrage.store_parquet.FORMAT_VERSION *= 2*
5575 5575

### outrage.store_parquet.BYTE_LENGTHS *= True*
6298 6298

### outrage.store_parquet.HELD_COLUMNS *= ('key', 'meta_name', 'meta_path', 'format', 'updated_at', 'sort_key', 'chars')*
7277 7277

### outrage.store_parquet.INDEX_COLUMNS *= ('key', 'doc_key', 'meta_name', 'meta_path', 'parent', 'format', 'updated_at', 'sort_key', 'chars', 'bytes')*
8179 8179

### outrage.store_parquet.PROBE *= 8*
8593 8593

### outrage.store_parquet.ROW_GROUP_SIZE *= 2048*
9063 9063

### outrage.store_parquet.VERSION_KEY *= b'outrage.format-version'*
9464 9464

### *class* outrage.store_parquet.ParquetStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
9565 9565

#### default_filename *: ClassVar[str]* *= 'store.parquet'*
10552 10552

#### backend_name *: ClassVar[str]* *= 'parquet'*
11059 11059

#### format_version *: ClassVar[int]* *= 2*
11430 11430

#### writable *: ClassVar[bool]* *= False*
12047 12047

#### versioned *: ClassVar[bool]* *= False*
12657 12657

#### close() → None
13193 13193

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
13642 13644

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
15440 15444

#### exists(key: str) → bool
16546 16552

#### level_entry(key: str) → Entry | None
16740 16748

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
17139 17149

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
17829 17841

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
19313 19327

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
20092 20108

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
21534 21552

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
23373 23393

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
24998 25020

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
26183 26207

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
27357 27383

#### *property* stored_format_version *: int*
28469 28497

#### audit_rows() → Iterator[AuditRow]
28899 28927

#### check_file(report: Report) → None
30166 30196

#### repair() → list[Repaired]
30883 30915

#### *classmethod* check_target(path: str | PathLike[str], \*, overwrite: bool = False) → Path
31663 31697

#### *classmethod* build(path: str | PathLike[str], documents: Iterable[tuple[str, str, str | None, str | None]], \*, overwrite: bool = False, byte_lengths: bool = BYTE_LENGTHS) → int
32561 32597

#### *classmethod* build_part(path: str | PathLike[str], documents: Iterable[tuple[str, str, str | None, str | None]], \*, overwrite: bool = False, byte_lengths: bool = BYTE_LENGTHS) → int
34821 34859
