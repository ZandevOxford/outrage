# outrage.store_pyarrow
0 0 1

### outrage.store_pyarrow.CHUNK *= 8192*
4236 4236 67

### outrage.store_pyarrow.COMPRESSION *= 'zstd'*
4564 4564 74

### outrage.store_pyarrow.DEFAULT_STORE_FILE *= 'store.parquet'*
4826 4826 80

### outrage.store_pyarrow.ENCODABLE *= ('format', 'updated_at')*
5204 5204 87

### outrage.store_pyarrow.FORMAT_VERSION *= 2*
5791 5791 98

### outrage.store_pyarrow.BYTE_LENGTHS *= True*
6514 6514 111

### outrage.store_pyarrow.HELD_COLUMNS *= ('key', 'meta_name', 'meta_path', 'format', 'updated_at', 'sort_key', 'chars')*
7493 7493 128

### outrage.store_pyarrow.INDEX_COLUMNS *= ('key', 'doc_key', 'meta_name', 'meta_path', 'parent', 'format', 'updated_at', 'sort_key', 'chars', 'bytes')*
8395 8395 143

### outrage.store_pyarrow.PROBE *= 8*
8809 8809 150

### outrage.store_pyarrow.ROW_GROUP_SIZE *= 2048*
9279 9279 159

### outrage.store_pyarrow.VERSION_KEY *= b'outrage.format-version'*
9680 9680 167

### *class* outrage.store_pyarrow.PyarrowStore(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, log: EventLog | None = None, mount_point: str | None = None)
9781 9781 171

#### default_filename *: ClassVar[str]* *= 'store.parquet'*
10768 10768 177

#### backend_name *: ClassVar[str]* *= 'pyarrow'*
11275 11275 185

#### format_version *: ClassVar[int]* *= 2*
11646 11646 191

#### writable *: ClassVar[bool]* *= False*
12263 12263 199

#### versioned *: ClassVar[bool]* *= False*
12873 12873 209

#### close() → None
13409 13409 218

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
13858 13860 229

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
15656 15660 249

#### exists(key: str) → bool
16762 16768 262

#### level_entry(key: str) → Entry | None
16956 16964 266

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
17355 17365 274

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
18045 18057 284

#### latest_change(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → str | None
19529 19543 308

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
20308 20324 318

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
22031 22049 333

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
23870 23890 357

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
25495 25517 370

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
26762 26786 383

#### backup(destination: str | PathLike[str] | None = None, \*, overwrite: bool = False) → Backup
27936 27962 392

#### *property* stored_format_version *: int*
29048 29076 408

#### audit_rows() → Iterator[AuditRow]
29478 29506 418

#### check_file(report: Report) → None
30745 30775 441

#### repair() → list[Repaired]
31467 31499 456

#### *classmethod* check_target(path: str | PathLike[str], \*, overwrite: bool = False) → Path
32247 32281 470

#### *classmethod* build(path: str | PathLike[str], documents: Iterable[tuple[str, str, str | None, str | None]], \*, overwrite: bool = False, byte_lengths: bool = BYTE_LENGTHS) → int
33145 33181 481

#### *classmethod* build_part(path: str | PathLike[str], documents: Iterable[tuple[str, str, str | None, str | None]], \*, overwrite: bool = False, byte_lengths: bool = BYTE_LENGTHS) → int
35405 35443 507
