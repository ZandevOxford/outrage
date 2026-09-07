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

#### close() → None
9557 9557

#### located(key: str, format: str | None = None) → Path | None
9839 9841

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
11057 11061

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
12292 12298

#### exists(key: str) → bool
13934 13942

#### level_entry(key: str) → Entry | None
14281 14291

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
14745 14757

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
15554 15568

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None) → Page[Entry]
16831 16847

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
17851 17869

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
19164 19184

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
20290 20312

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Self
21442 21466

#### opened_at(path: Path) → Self
23400 23426

#### *property* stored_format_version *: int*
24673 24701

#### audit_rows() → Iterator[AuditRow]
25301 25329

#### check_file(report: Report) → None
25842 25872

#### repair() → list[Repaired]
26406 26438

### *exception* outrage.store_files.NotTextError(code: str, \*\*details: Any)
26962 26996
