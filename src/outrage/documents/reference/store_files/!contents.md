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

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
11057 11061

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
12433 12439

#### exists(key: str) → bool
14075 14083

#### level_entry(key: str) → Entry | None
14422 14432

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
14886 14898

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
15695 15709

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None) → Page[Entry]
16972 16988

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
17992 18010

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
19305 19325

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
20431 20453

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, log: EventLog | None = None, mount_point: str | None = None) → Self
21583 21607

#### opened_at(path: Path) → Self
23541 23567

#### *property* stored_format_version *: int*
24814 24842

#### audit_rows() → Iterator[AuditRow]
25442 25470

#### check_file(report: Report) → None
25983 26013

#### repair() → list[Repaired]
26547 26579

### *exception* outrage.store_files.NotTextError(code: str, \*\*details: Any)
27103 27137
