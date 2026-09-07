# outrage.store_parquet
0 0

### outrage.store_parquet.CHUNK *= 8192*
4018 4018

### outrage.store_parquet.COMPRESSION *= 'zstd'*
4346 4346

### outrage.store_parquet.DEFAULT_STORE_FILE *= 'store.parquet'*
4608 4608

### outrage.store_parquet.ENCODABLE *= ('format', 'updated_at')*
4986 4986

### outrage.store_parquet.FORMAT_VERSION *= 2*
5573 5573

### outrage.store_parquet.BYTE_LENGTHS *= True*
6296 6296

### outrage.store_parquet.HELD_COLUMNS *= ('key', 'meta_name', 'meta_path', 'format', 'updated_at', 'sort_key', 'chars')*
7275 7275

### outrage.store_parquet.INDEX_COLUMNS *= ('key', 'doc_key', 'meta_name', 'meta_path', 'parent', 'format', 'updated_at', 'sort_key', 'chars', 'bytes')*
8177 8177

### outrage.store_parquet.PROBE *= 8*
8591 8591

### outrage.store_parquet.ROW_GROUP_SIZE *= 2048*
9061 9061

### outrage.store_parquet.VERSION_KEY *= b'outrage.format-version'*
9462 9462

### *class* outrage.store_parquet.ParquetStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
9563 9563

#### default_filename *: ClassVar[str]* *= 'store.parquet'*
10541 10541

#### backend_name *: ClassVar[str]* *= 'parquet'*
11047 11047

#### format_version *: ClassVar[int]* *= 2*
11417 11417

#### writable *: ClassVar[bool]* *= False*
12033 12033

#### close() → None
12642 12642

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
13090 13092

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
14734 14738

#### exists(key: str) → bool
15833 15839

#### level_entry(key: str) → Entry | None
16025 16033

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
16422 16432

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
17109 17121

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
17884 17898

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None) → Page[Entry]
19316 19332

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
20736 20754

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
22351 22371

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
23533 23555

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
24700 24724

#### *property* stored_format_version *: int*
25808 25834

#### audit_rows() → Iterator[AuditRow]
26237 26263

#### check_file(report: Report) → None
27504 27532

#### repair() → list[Repaired]
28220 28250

#### *classmethod* check_target(path: str | PathLike[str], \*, overwrite: bool = False) → Path
28999 29031

#### *classmethod* build(path: str | PathLike[str], documents: Iterable[tuple[str, str, str | None, str | None]], \*, overwrite: bool = False, byte_lengths: bool = BYTE_LENGTHS) → int
29894 29928
