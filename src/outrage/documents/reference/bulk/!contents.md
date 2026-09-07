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

### *class* outrage.bulk.Imported(key: str, stored: int, previous: int | None, unchecked_code: str | None = None, unchecked_from: str | None = None, unedited: bool = False, copied_from: str | None = None, overwritten: bool = False, changed_at: str | None = None)
18655 18663

#### key *: str*
19849 19857

#### stored *: int*
19961 19969

#### previous *: int | None*
20059 20067

#### unchecked_code *: str | None*
20371 20379

#### unchecked_from *: str | None*
21069 21077

#### unedited *: bool*
21501 21509

#### copied_from *: str | None*
21863 21871

#### overwritten *: bool*
22343 22351

#### changed_at *: str | None*
22495 22503

### outrage.bulk.PAGE *= 200*
22775 22783

### outrage.bulk.Packable
23092 23100

### outrage.bulk.RECORD_SUFFIX *= '.outrage.json'*
24045 24053

### outrage.bulk.TEMP_PREFIX *= '.outrage-'*
24330 24338

### outrage.bulk.TRAVERSAL *= ('.', '..')*
24741 24749

### *exception* outrage.bulk.ExportRootError(code: str, \*\*details: Any)
25020 25028

### *exception* outrage.bulk.FileMissingError(code: str, \*\*details: Any)
25348 25356

### *exception* outrage.bulk.OverlappingCopyError(code: str, \*\*details: Any)
25759 25767

### *exception* outrage.bulk.SourceMissingError(code: str, \*\*details: Any)
26166 26174

### *exception* outrage.bulk.StaleImportError(code: str, \*\*details: Any)
26571 26579

### *exception* outrage.bulk.UncheckedWriteError(code: str, \*\*details: Any)
27192 27200

### *exception* outrage.bulk.UnmappableError(code: str, \*\*details: Any)
28015 28023

### outrage.bulk.check_extensions(extensions: str) → str
28418 28426

### outrage.bulk.check_write(opened: Store, key: str, path: str | PathLike[str], root: str | PathLike[str], \*, storing: str | PathLike[str] | None = None, overwrite: bool = False) → Check
29043 29053

### outrage.bulk.contained_file(root: str | PathLike[str], path: str | PathLike[str], key: str) → Path
31368 31380

### outrage.bulk.contained_path(root: str | PathLike[str], relative: PurePosixPath, key: str) → Path
32349 32363

### outrage.bulk.container_name(segment: str) → str
33905 33921

### outrage.bulk.content_hash(content: str) → str
34928 34946

### outrage.bulk.copied(source: Store, target: Store, subtree: BoundedSubtree = store.EVERYTHING, \*, key_range: KeyRange = store.UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
35334 35354

### outrage.bulk.declared_format(name: str) → str | None
40555 40577

### outrage.bulk.documents_from_store(opened: Store, key: str | None = None) → Iterator[tuple[Transfer, tuple[str, str, str | None, str | None] | None]]
40971 40995

### outrage.bulk.documents_from_tree(source: str | PathLike[str], key: str | None = None, \*, hidden: bool = False, extensions: str = DEFAULT_EXTENSIONS) → Iterator[tuple[Transfer, tuple[str, str, str | None, str | None] | None]]
42488 42514

### outrage.bulk.export_document(opened: Store, key: str, root: str | PathLike[str]) → Exported
44580 44608

### outrage.bulk.export_root() → Path
45563 45593

### outrage.bulk.export_tree(opened: Store, key: str | None, target: str | PathLike[str], \*, on_conflict: str = SKIP, dry_run: bool = False, extensions: str = DEFAULT_EXTENSIONS) → Iterator[Transfer]
46387 46419

### outrage.bulk.file_name(segment: str, format: str | None = None) → str
48627 48661

### outrage.bulk.import_document(opened: Store, key: str, path: str | PathLike[str], root: str | PathLike[str], \*, against: str | PathLike[str] | None = None, overwrite: bool = False) → Imported
49372 49408

### outrage.bulk.import_tree(opened: Store, source: str | PathLike[str], key: str | None = None, \*, on_conflict: str = SKIP, dry_run: bool = False, hidden: bool = False, extensions: str = DEFAULT_EXTENSIONS) → Iterator[Transfer]
51832 51870

### outrage.bulk.key_for_path(relative: PurePosixPath | str, prefix: str | None = None, \*, extensions: str = DEFAULT_EXTENSIONS) → tuple[str, str | None]
54415 54455

### outrage.bulk.levels(opened: Store, key: str | None) → Iterator[Entry]
56649 56691

### outrage.bulk.new_export_file(root: str | PathLike[str], format: str | None = None) → Path
57403 57447

### outrage.bulk.notes_for(imported: Imported) → list[Note]
58738 58784

### outrage.bulk.notes_for_checked_write(key: str, check: Check, stored: int) → list[Note]
60053 60101

### outrage.bulk.notes_for_copy(landing: str, \*, dry_run: bool, on_conflict: str, unchanged_since: str | None, changed: Sequence[str], next_cursor: str | None, limit: int, failed: int, named: int, stopped: bool, mounts_kept: Sequence[str]) → list[Note]
60952 61002

### outrage.bulk.notes_for_delete(key: str, \*, dry_run: bool, remaining: int, mounts_kept: Sequence[str]) → list[Note]
63044 63096

### outrage.bulk.notes_for_export(exported: Exported) → list[Note]
64319 64373

### outrage.bulk.notes_for_write(previous: int | None, stored: int) → list[Note]
65179 65235

### outrage.bulk.overlapping(source: str, target: str, \*, reroot: bool = False) → None
66140 66198

### outrage.bulk.pack(target: str | PathLike[str], documents: Iterator[tuple[Transfer, tuple[str, str, str | None, str | None] | None]], \*, overwrite: bool = False, dry_run: bool = False, byte_lengths: bool = True) → Iterator[Transfer]
67740 67800

### outrage.bulk.path_for_key(key: str, format: str | None = None, \*, extensions: str = DEFAULT_EXTENSIONS) → PurePosixPath
69869 69931

### outrage.bulk.renew(opened: Store, key: str, check: Check, content: str | None = None) → None
72029 72093

### outrage.bulk.size_of(opened: Store, key: str) → int | None
73126 73192

### outrage.bulk.sweep_exports(root: str | PathLike[str], max_age: timedelta = EXPORT_MAX_AGE, now: datetime | None = None) → int
73817 73885

### outrage.bulk.walk(opened: Store, key: str | None) → Iterator[Entry]
74924 74994
