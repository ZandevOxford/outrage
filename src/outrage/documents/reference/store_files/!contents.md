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
13232 13236 217

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
14710 14716 229

#### exists(key: str) → bool
16480 16488 254

#### level_entry(key: str) → Entry | None
16829 16839 261

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
17295 17307 269

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
18107 18121 281

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
19435 19451 301

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
21003 21021 314

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
22509 22529 333

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
23832 23854 341

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
25043 25067 353

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, create: bool = True) → Self
26202 26228 362

#### opened_at(path: Path) → Self
29067 29095 388

#### *property* stored_format_version *: int*
30452 30482 412

#### audit_rows() → Iterator[AuditRow]
31081 31111 424

#### check_file(report: Report) → None
31622 31654 434

#### repair() → list[Repaired]
32187 32221 444

### *exception* outrage.store_files.NotTextError(code: str, \*\*details: Any)
32744 32780 454

### *exception* outrage.store_files.StoreBusyError(code: str, \*\*details: Any)
33350 33386 464
