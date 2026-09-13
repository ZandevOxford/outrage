# outrage.store_files
0 0

## What it costs
2867 2867

## Where it diverges from the contract, deliberately
4125 4125

### outrage.store_files.DEFAULT_TREE_NAME *= 'documents'*
5671 5671

### outrage.store_files.FORMAT_VERSION *= 1*
6105 6105

### *class* outrage.store_files.FilesystemStore(root: str | PathLike[str] | None = None, \*, log: EventLog | None = None, hidden: bool = True, create: bool = True, extensions: str = bulk.DEFAULT_EXTENSIONS, mount_point: str | None = None)
6515 6515

#### default_filename *: ClassVar[str]* *= 'documents'*
7462 7462

#### backend_name *: ClassVar[str]* *= 'files'*
7964 7964

#### format_version *: ClassVar[int]* *= 1*
8332 8332

#### writable *: ClassVar[bool]* *= True*
8949 8949

#### versioned *: ClassVar[bool]* *= False*
9557 9557

#### close() → None
10092 10092

#### located(key: str, format: str | None = None) → Path | None
10374 10376

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
11592 11596

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
12968 12974

#### exists(key: str) → bool
14610 14618

#### level_entry(key: str) → Entry | None
14957 14967

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
15421 15433

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
16230 16244

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
17556 17572

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
18833 18851

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
20331 20351

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
21644 21666

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
22770 22794

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, log: EventLog | None = None, mount_point: str | None = None) → Self
23922 23948

#### opened_at(path: Path) → Self
26160 26188

#### *property* stored_format_version *: int*
27433 27463

#### audit_rows() → Iterator[AuditRow]
28061 28091

#### check_file(report: Report) → None
28602 28634

#### repair() → list[Repaired]
29166 29200

### *exception* outrage.store_files.NotTextError(code: str, \*\*details: Any)
29722 29758
