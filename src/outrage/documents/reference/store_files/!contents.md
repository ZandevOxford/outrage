# outrage.store_files
0 0 1

## What it costs
3046 3046 50

## Where it diverges from the contract, deliberately
4304 4304 71

### outrage.store_files.DEFAULT_TREE_NAME *= 'documents'*
5850 5850 96

### outrage.store_files.FORMAT_VERSION *= 1*
6284 6284 104

### outrage.store_files.LOCK_FILE_SUFFIX *= '.lock'*
6694 6694 111

### outrage.store_files.LOCK_INTERPROCESS *= 'interprocess'*
6823 6823 115

### outrage.store_files.LOCK_MODES *= ('process', 'interprocess')*
7057 7057 121

### outrage.store_files.LOCK_PROCESS *= 'process'*
7169 7169 125

### outrage.store_files.LOCK_TIMEOUT_SECONDS *= 5.0*
7343 7343 130

### *class* outrage.store_files.FilesystemStore(root: str | PathLike[str] | None = None, \*, log: EventLog | None = None, hidden: bool = True, create: bool = True, extensions: str = bulk.DEFAULT_EXTENSIONS, lock: str = LOCK_PROCESS, mount_point: str | None = None)
7750 7750 137

#### default_filename *: ClassVar[str]* *= 'documents'*
8788 8788 143

#### backend_name *: ClassVar[str]* *= 'files'*
9291 9291 151

#### format_version *: ClassVar[int]* *= 1*
9660 9660 157

#### writable *: ClassVar[bool]* *= True*
10278 10278 165

#### versioned *: ClassVar[bool]* *= False*
10887 10887 175

#### close() → None
11423 11423 184

#### located(key: str, format: str | None = None) → Path | None
11706 11708 191

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
12928 12932 211

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
14406 14412 223

#### exists(key: str) → bool
16176 16184 248

#### level_entry(key: str) → Entry | None
16525 16535 255

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
16991 17003 263

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
17803 17817 275

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
19131 19147 295

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
20699 20717 308

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
22205 22225 327

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
23528 23550 335

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
24739 24763 347

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, create: bool = True) → Self
25898 25924 356

#### opened_at(path: Path) → Self
28763 28791 382

#### *property* stored_format_version *: int*
30148 30178 406

#### audit_rows() → Iterator[AuditRow]
30777 30807 418

#### check_file(report: Report) → None
31318 31350 428

#### repair() → list[Repaired]
31883 31917 438

### *exception* outrage.store_files.NotTextError(code: str, \*\*details: Any)
32440 32476 448

### *exception* outrage.store_files.StoreBusyError(code: str, \*\*details: Any)
33046 33082 458
