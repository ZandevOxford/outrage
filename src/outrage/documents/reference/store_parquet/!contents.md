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
10543 10543

#### backend_name *: ClassVar[str]* *= 'parquet'*
11049 11049

#### format_version *: ClassVar[int]* *= 2*
11419 11419

#### writable *: ClassVar[bool]* *= False*
12035 12035

#### close() → None
12644 12644

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
13092 13094

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
14877 14881

#### exists(key: str) → bool
15976 15982

#### level_entry(key: str) → Entry | None
16168 16176

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
16565 16575

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
17252 17264

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
18734 18748

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
19509 19525

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
20941 20959

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
22772 22792

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
24387 24409

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
25569 25593

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
26736 26762

#### *property* stored_format_version *: int*
27844 27872

#### audit_rows() → Iterator[AuditRow]
28273 28301

#### check_file(report: Report) → None
29540 29570

#### repair() → list[Repaired]
30256 30288

#### *classmethod* check_target(path: str | PathLike[str], \*, overwrite: bool = False) → Path
31035 31069

#### *classmethod* build(path: str | PathLike[str], documents: Iterable[tuple[str, str, str | None, str | None]], \*, overwrite: bool = False, byte_lengths: bool = BYTE_LENGTHS) → int
31930 31966

#### *classmethod* build_part(path: str | PathLike[str], documents: Iterable[tuple[str, str, str | None, str | None]], \*, overwrite: bool = False, byte_lengths: bool = BYTE_LENGTHS) → int
34178 34216
