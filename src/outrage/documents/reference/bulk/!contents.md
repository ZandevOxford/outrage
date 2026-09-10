# outrage.bulk
0 0

### *class* outrage.bulk.Check(file: Path, record: ExportRecord | None, previous: int | None, changed_at: str | None = None, unchecked_code: str | None = None, unchecked_from: str | None = None, overwritten: bool = False)
1628 1628

#### file *: Path*
2913 2913

#### record *: ExportRecord | None*
3115 3115

#### previous *: int | None*
3455 3455

#### changed_at *: str | None*
3742 3742

#### unchecked_code *: str | None*
3954 3954

#### unchecked_from *: str | None*
4221 4221

#### overwritten *: bool*
4423 4423

### outrage.bulk.Document
4702 4702

### outrage.bulk.DEFAULT_EXTENSIONS *= 'strip'*
5507 5507

### outrage.bulk.EXPORT_DIR_PREFIX *= 'outrage-export'*
5777 5777

### outrage.bulk.EXPORT_MAX_AGE *= datetime.timedelta(days=7)*
6518 6518

### outrage.bulk.CONTAINER_PREFIX *= '.!'*
6876 6876

### outrage.bulk.EXTENSION_BY_FORMAT *= {'html': '.html', 'json': '.json', 'markdown': '.md', 'text': '.txt'}*
9480 9480

### outrage.bulk.EXTENSION_MODES *= ('strip', 'keep')*
9945 9945

### *class* outrage.bulk.ExportRecord(key: str, content_sha256: str, exported_at: str, format: str | None = None, updated_at: str | None = None, store: str | None = None)
11203 11203

#### key *: str*
12980 12980

#### content_sha256 *: str*
13268 13268

#### exported_at *: str*
13530 13530

#### format *: str | None*
13643 13643

#### updated_at *: str | None*
13814 13814

#### store *: str | None*
14212 14212

#### *static* path_for(file: str | PathLike[str]) → Path
14606 14606

#### write(file: str | PathLike[str]) → Path
14946 14948

#### *classmethod* read(file: str | PathLike[str]) → ExportRecord | None
15270 15274

#### followed(opened: Store, key: str, content: str) → ExportRecord
15972 15978

### *class* outrage.bulk.Exported(path: Path, excerpt: Excerpt, record: ExportRecord)
16708 16716

#### path *: Path*
17070 17078

#### excerpt *: Excerpt*
17201 17209

#### record *: ExportRecord*
17297 17305

### outrage.bulk.FALLBACK_PREFIX *= 'document-'*
17401 17409

### outrage.bulk.FORMAT_BY_EXTENSION *= {'.html': 'html', '.json': 'json', '.md': 'markdown', '.txt': 'text'}*
17912 17920

### *class* outrage.bulk.Imported(key: str, stored: int, previous: int | None, unchecked_code: str | None = None, unchecked_from: str | None = None, unedited: bool = False, copied_from: str | None = None, overwritten: bool = False, changed_at: str | None = None, contents_key: str | None = None)
18655 18663

#### key *: str*
19994 20002

#### stored *: int*
20106 20114

#### previous *: int | None*
20204 20212

#### unchecked_code *: str | None*
20516 20524

#### unchecked_from *: str | None*
21214 21222

#### unedited *: bool*
21646 21654

#### copied_from *: str | None*
22008 22016

#### overwritten *: bool*
22488 22496

#### changed_at *: str | None*
22640 22648

#### contents_key *: str | None*
22920 22928

### outrage.bulk.PAGE *= 200*
23205 23213

### outrage.bulk.Packable
23522 23530

### outrage.bulk.RECORD_SUFFIX *= '.outrage.json'*
24475 24483

### outrage.bulk.TEMP_PREFIX *= '.outrage-'*
24760 24768

### outrage.bulk.TRAVERSAL *= ('.', '..')*
25171 25179

### *exception* outrage.bulk.ExportRootError(code: str, \*\*details: Any)
25450 25458

### *exception* outrage.bulk.FileMissingError(code: str, \*\*details: Any)
25778 25786

### *exception* outrage.bulk.OverlappingCopyError(code: str, \*\*details: Any)
26189 26197

### *exception* outrage.bulk.SourceMissingError(code: str, \*\*details: Any)
26596 26604

### *exception* outrage.bulk.StaleImportError(code: str, \*\*details: Any)
27001 27009

### *exception* outrage.bulk.UncheckedWriteError(code: str, \*\*details: Any)
27622 27630

### *exception* outrage.bulk.UnmappableError(code: str, \*\*details: Any)
28445 28453

### outrage.bulk.check_extensions(extensions: str) → str
28848 28856

### outrage.bulk.check_write(opened: Store, key: str, path: str | PathLike[str], root: str | PathLike[str], \*, storing: str | PathLike[str] | None = None, overwrite: bool = False) → Check
29473 29483

### outrage.bulk.contained_file(root: str | PathLike[str], path: str | PathLike[str], key: str) → Path
31798 31810

### outrage.bulk.contained_path(root: str | PathLike[str], relative: PurePosixPath, key: str) → Path
32779 32793

### outrage.bulk.container_name(segment: str) → str
34335 34351

### outrage.bulk.content_hash(content: str) → str
35358 35376

### outrage.bulk.copied(source: Store, target: Store, subtree: BoundedSubtree = store.EVERYTHING, \*, key_range: KeyRange = store.UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
35764 35784

### outrage.bulk.declared_format(name: str) → str | None
40985 41007

### outrage.bulk.documents_from_store(opened: Store, key: str | None = None) → Iterator[tuple[Transfer, tuple[str, str, str | None, str | None] | None]]
41401 41425

### outrage.bulk.documents_from_tree(source: str | PathLike[str], key: str | None = None, \*, hidden: bool = False, extensions: str = DEFAULT_EXTENSIONS) → Iterator[tuple[Transfer, tuple[str, str, str | None, str | None] | None]]
42918 42944

### outrage.bulk.export_document(opened: Store, key: str, root: str | PathLike[str]) → Exported
45010 45038

### outrage.bulk.export_root() → Path
45993 46023

### outrage.bulk.export_tree(opened: Store, key: str | None, target: str | PathLike[str], \*, on_conflict: str = SKIP, dry_run: bool = False, extensions: str = DEFAULT_EXTENSIONS) → Iterator[Transfer]
46817 46849

### outrage.bulk.file_name(segment: str, format: str | None = None) → str
49057 49091

### outrage.bulk.import_document(opened: Store, key: str, path: str | PathLike[str], root: str | PathLike[str], \*, against: str | PathLike[str] | None = None, overwrite: bool = False, generate_contents: bool = False) → Imported
49802 49838

### outrage.bulk.import_tree(opened: Store, source: str | PathLike[str], key: str | None = None, \*, on_conflict: str = SKIP, dry_run: bool = False, hidden: bool = False, extensions: str = DEFAULT_EXTENSIONS) → Iterator[Transfer]
52703 52741

### outrage.bulk.key_for_path(relative: PurePosixPath | str, prefix: str | None = None, \*, extensions: str = DEFAULT_EXTENSIONS) → tuple[str, str | None]
55286 55326

### outrage.bulk.levels(opened: Store, key: str | None, \*, descendant_counts: bool = False, descendant_chars: bool = False) → Iterator[Entry]
57520 57562

### outrage.bulk.new_export_file(root: str | PathLike[str], format: str | None = None) → Path
58717 58761

### outrage.bulk.notes_for(imported: Imported) → list[Note]
60052 60098

### outrage.bulk.notes_for_checked_write(key: str, check: Check, stored: int) → list[Note]
61367 61415

### outrage.bulk.notes_for_copy(landing: str, \*, dry_run: bool, on_conflict: str, unchanged_since: str | None, changed: Sequence[str], next_cursor: str | None, limit: int, failed: int, named: int, stopped: bool, mounts_kept: Sequence[str]) → list[Note]
62266 62316

### outrage.bulk.notes_for_delete(key: str, \*, dry_run: bool, remaining: int, mounts_kept: Sequence[str]) → list[Note]
64358 64410

### outrage.bulk.notes_for_export(exported: Exported) → list[Note]
65633 65687

### outrage.bulk.notes_for_write(previous: int | None, stored: int) → list[Note]
66493 66549

### outrage.bulk.overlapping(source: str, target: str, \*, reroot: bool = False) → None
67454 67512

### outrage.bulk.pack(target: str | PathLike[str], documents: Iterator[tuple[Transfer, tuple[str, str, str | None, str | None] | None]], \*, overwrite: bool = False, dry_run: bool = False, byte_lengths: bool = True) → Iterator[Transfer]
69054 69114

### outrage.bulk.path_for_key(key: str, format: str | None = None, \*, extensions: str = DEFAULT_EXTENSIONS) → PurePosixPath
71183 71245

### outrage.bulk.renew(opened: Store, key: str, check: Check, content: str | None = None) → None
73343 73407

### outrage.bulk.size_of(opened: Store, key: str) → int | None
74440 74506

### outrage.bulk.sweep_exports(root: str | PathLike[str], max_age: timedelta = EXPORT_MAX_AGE, now: datetime | None = None) → int
75131 75199

### outrage.bulk.walk(opened: Store, key: str | None, \*, descendant_counts: bool = False, descendant_chars: bool = False) → Iterator[Entry]
76238 76308
