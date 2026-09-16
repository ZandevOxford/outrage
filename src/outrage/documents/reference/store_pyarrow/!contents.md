# outrage.store_pyarrow
0 0

### outrage.store_pyarrow.CHUNK *= 8192*
4090 4090

### outrage.store_pyarrow.COMPRESSION *= 'zstd'*
4418 4418

### outrage.store_pyarrow.DEFAULT_STORE_FILE *= 'store.parquet'*
4680 4680

### outrage.store_pyarrow.ENCODABLE *= ('format', 'updated_at')*
5058 5058

### outrage.store_pyarrow.FORMAT_VERSION *= 2*
5645 5645

### outrage.store_pyarrow.BYTE_LENGTHS *= True*
6368 6368

### outrage.store_pyarrow.HELD_COLUMNS *= ('key', 'meta_name', 'meta_path', 'format', 'updated_at', 'sort_key', 'chars')*
7347 7347

### outrage.store_pyarrow.INDEX_COLUMNS *= ('key', 'doc_key', 'meta_name', 'meta_path', 'parent', 'format', 'updated_at', 'sort_key', 'chars', 'bytes')*
8249 8249

### outrage.store_pyarrow.PROBE *= 8*
8663 8663

### outrage.store_pyarrow.ROW_GROUP_SIZE *= 2048*
9133 9133

### outrage.store_pyarrow.VERSION_KEY *= b'outrage.format-version'*
9534 9534

### *class* outrage.store_pyarrow.PyarrowStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
9635 9635

#### default_filename *: ClassVar[str]* *= 'store.parquet'*
10622 10622

#### backend_name *: ClassVar[str]* *= 'pyarrow'*
11129 11129

#### format_version *: ClassVar[int]* *= 2*
11500 11500

#### writable *: ClassVar[bool]* *= False*
12117 12117

#### versioned *: ClassVar[bool]* *= False*
12727 12727

#### close() → None
13263 13263

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
13712 13714

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
15510 15514

#### exists(key: str) → bool
16616 16622

#### level_entry(key: str) → Entry | None
16810 16818

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
17209 17219

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
17899 17911

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
19383 19397

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
20162 20178

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
21604 21622

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
23443 23463

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
25068 25090

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
26335 26359

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
27509 27535

#### *property* stored_format_version *: int*
28621 28649

#### audit_rows() → Iterator[AuditRow]
29051 29079

#### check_file(report: Report) → None
30318 30348

#### repair() → list[Repaired]
31040 31072

#### *classmethod* check_target(path: str | PathLike[str], \*, overwrite: bool = False) → Path
31820 31854

#### *classmethod* build(path: str | PathLike[str], documents: Iterable[tuple[str, str, str | None, str | None]], \*, overwrite: bool = False, byte_lengths: bool = BYTE_LENGTHS) → int
32718 32754

#### *classmethod* build_part(path: str | PathLike[str], documents: Iterable[tuple[str, str, str | None, str | None]], \*, overwrite: bool = False, byte_lengths: bool = BYTE_LENGTHS) → int
34978 35016
