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
7471 7471

#### backend_name *: ClassVar[str]* *= 'files'*
7974 7974

#### format_version *: ClassVar[int]* *= 1*
8343 8343

#### writable *: ClassVar[bool]* *= True*
8961 8961

#### versioned *: ClassVar[bool]* *= False*
9570 9570

#### close() → None
10106 10106

#### located(key: str, format: str | None = None) → Path | None
10389 10391

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
11611 11615

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
13000 13006

#### exists(key: str) → bool
14649 14657

#### level_entry(key: str) → Entry | None
14998 15008

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
15464 15476

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
16276 16290

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
17604 17620

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
18891 18909

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
20397 20417

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0) → MissingMeta
21720 21742

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
22849 22873

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, log: EventLog | None = None, mount_point: str | None = None) → Self
24008 24034

#### opened_at(path: Path) → Self
26259 26287

#### *property* stored_format_version *: int*
27532 27562

#### audit_rows() → Iterator[AuditRow]
28161 28191

#### check_file(report: Report) → None
28702 28734

#### repair() → list[Repaired]
29267 29301

### *exception* outrage.store_files.NotTextError(code: str, \*\*details: Any)
29824 29860
