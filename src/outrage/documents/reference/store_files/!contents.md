# outrage.store_files
0 0 1

## What it costs
2867 2867 47

## Where it diverges from the contract, deliberately
4125 4125 68

### outrage.store_files.DEFAULT_TREE_NAME *= 'documents'*
5671 5671 93

### outrage.store_files.FORMAT_VERSION *= 1*
6105 6105 101

### outrage.store_files.LOCK_FILE_SUFFIX *= '.lock'*
6515 6515 108

### outrage.store_files.LOCK_INTERPROCESS *= 'interprocess'*
6644 6644 112

### outrage.store_files.LOCK_MODES *= ('process', 'interprocess')*
6878 6878 118

### outrage.store_files.LOCK_PROCESS *= 'process'*
6990 6990 122

### outrage.store_files.LOCK_TIMEOUT_SECONDS *= 5.0*
7164 7164 127

### *class* outrage.store_files.FilesystemStore(root: str | PathLike[str] | None = None, \*, log: EventLog | None = None, hidden: bool = True, create: bool = True, extensions: str = bulk.DEFAULT_EXTENSIONS, lock: str = LOCK_PROCESS, mount_point: str | None = None)
7571 7571 134

#### default_filename *: ClassVar[str]* *= 'documents'*
8609 8609 140

#### backend_name *: ClassVar[str]* *= 'files'*
9112 9112 148

#### format_version *: ClassVar[int]* *= 1*
9481 9481 154

#### writable *: ClassVar[bool]* *= True*
10099 10099 162

#### versioned *: ClassVar[bool]* *= False*
10708 10708 172

#### close() → None
11244 11244 181

#### located(key: str, format: str | None = None) → Path | None
11527 11529 188

#### store_document(key: str, content: str, format: str | None = None, \*, title: str | None = None, contents: str | None = None, encoding: str | None = None, updated_at: str | None = None) → str
12749 12753 208

#### delete(key: str, recursive: bool = False, \*, key_range: KeyRange = UNBOUNDED, unchanged_since: str | None = None, dry_run: bool = False) → list[str]
14227 14233 220

#### exists(key: str) → bool
15997 16005 245

#### level_entry(key: str) → Entry | None
16346 16356 252

#### descendant_count(key: str, \*, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False) → int
16812 16824 260

#### subtree_totals(key: str, \*, key_range: KeyRange = UNBOUNDED, chars: bool = False) → SubtreeTotals
17624 17638 272

#### retrieve_document(key: str, \*, offset: int = 0, byte_offset: int | None = None, line: int | None = None, lines: int | None = None, length: int | None = None, pattern: str | None = None, occurrence: int = 0, max_chars: int = DEFAULT_MAX_CHARS) → Excerpt
18952 18968 292

#### list_keys(key: str | None = None, \*, limit: int | None = None, cursor: str | None = None, descendant_counts: bool = False, descendant_chars: bool = False) → Page[Entry]
20520 20538 305

#### get_documents(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] | None = None, max_chars: int = DEFAULT_BULK_MAX_CHARS, limit: int | None = None, max_total_chars: int | None = None) → Page[Excerpt]
22026 22046 324

#### missing_meta_stats(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, window: KeyRange = UNBOUNDED, meta_name: str | Sequence[str] = 'title', sample: int = 0, coverage: bool = False) → MissingMeta
23349 23371 332

#### keys_missing_meta(subtree: BoundedSubtree = EVERYTHING, \*, key_range: KeyRange = UNBOUNDED, cursor: str | None = None, meta_name: str | Sequence[str] = 'title', limit: int | None = None) → Page[str]
24560 24584 344

#### *classmethod* in_directory(directory: str | PathLike[str] | None = None, \*, filename: str | PathLike[str] | None = None, extensions: str | None = None, versioning: bool | None = None, lock: str | None = None, service: str | None = None, log: EventLog | None = None, mount_point: str | None = None, create: bool = True) → Self
25719 25745 353

#### opened_at(path: Path) → Self
28584 28612 379

#### *property* stored_format_version *: int*
29969 29999 403

#### audit_rows() → Iterator[AuditRow]
30598 30628 415

#### check_file(report: Report) → None
31139 31171 425

#### repair() → list[Repaired]
31704 31738 435

### *exception* outrage.store_files.NotTextError(code: str, \*\*details: Any)
32261 32297 445

### *exception* outrage.store_files.StoreBusyError(code: str, \*\*details: Any)
32867 32903 455
