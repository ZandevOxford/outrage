# outrage.bulk
0 0

### *class* outrage.bulk.Check(file: Path, record: ExportRecord | None, previous: int | None, changed_at: str | None = None, unchecked_code: str | None = None, unchecked_from: str | None = None, overwritten: bool = False)
1628 1628

#### file *: Path*
2924 2924

#### record *: ExportRecord | None*
3126 3126

#### previous *: int | None*
3467 3467

#### changed_at *: str | None*
3756 3756

#### unchecked_code *: str | None*
3970 3970

#### unchecked_from *: str | None*
4239 4239

#### overwritten *: bool*
4443 4443

### outrage.bulk.Document
4723 4723

### outrage.bulk.DEFAULT_EXTENSIONS *= 'strip'*
5535 5535

### outrage.bulk.EXPORT_DIR_PREFIX *= 'outrage-export'*
5805 5805

### outrage.bulk.EXPORT_MAX_AGE *= datetime.timedelta(days=7)*
6546 6546

### outrage.bulk.CONTAINER_PREFIX *= '.!'*
6904 6904

### outrage.bulk.EXTENSION_BY_FORMAT *= {'html': '.html', 'json': '.json', 'markdown': '.md', 'text': '.txt'}*
9508 9508

### outrage.bulk.EXTENSION_MODES *= ('strip', 'keep')*
9973 9973

### *class* outrage.bulk.ExportRecord(key: str, content_sha256: str, exported_at: str, format: str | None = None, updated_at: str | None = None, store: str | None = None)
11231 11231

#### key *: str*
13018 13018

#### content_sha256 *: str*
13307 13307

#### exported_at *: str*
13570 13570

#### format *: str | None*
13684 13684

#### updated_at *: str | None*
13857 13857

#### store *: str | None*
14257 14257

#### *static* path_for(file: str | PathLike[str]) → Path
14653 14653

#### write(file: str | PathLike[str]) → Path
14995 14997

#### *classmethod* read(file: str | PathLike[str]) → ExportRecord | None
15321 15325

#### followed(opened: Store, key: str, content: str) → ExportRecord
16026 16032

### *class* outrage.bulk.Exported(path: Path, excerpt: Excerpt, record: ExportRecord)
16764 16772

#### path *: Path*
17127 17135

#### excerpt *: Excerpt*
17258 17266

#### record *: ExportRecord*
17354 17362

### outrage.bulk.FALLBACK_PREFIX *= 'document-'*
17458 17466

### outrage.bulk.FORMAT_BY_EXTENSION *= {'.html': 'html', '.json': 'json', '.md': 'markdown', '.txt': 'text'}*
17969 17977

### *class* outrage.bulk.Imported(key: str, stored: int, previous: int | None, unchecked_code: str | None = None, unchecked_from: str | None = None, unedited: bool = False, copied_from: str | None = None, overwritten: bool = False, changed_at: str | None = None, contents_key: str | None = None)
18712 18720

#### key *: str*
20068 20076

#### stored *: int*
20181 20189

#### previous *: int | None*
20280 20288

#### unchecked_code *: str | None*
20594 20602

#### unchecked_from *: str | None*
21294 21302

#### unedited *: bool*
21728 21736

#### copied_from *: str | None*
22091 22099

#### overwritten *: bool*
22573 22581

#### changed_at *: str | None*
22726 22734

#### contents_key *: str | None*
23008 23016

### outrage.bulk.PAGE *= 200*
23295 23303

### outrage.bulk.Packable
23612 23620

### outrage.bulk.RECORD_SUFFIX *= '.outrage.json'*
24574 24582

### outrage.bulk.TEMP_PREFIX *= '.outrage-'*
24859 24867

### outrage.bulk.TRAVERSAL *= ('.', '..')*
25270 25278

### *exception* outrage.bulk.ExportRootError(code: str, \*\*details: Any)
25549 25557

### *exception* outrage.bulk.FileMissingError(code: str, \*\*details: Any)
25878 25886

### *exception* outrage.bulk.OverlappingCopyError(code: str, \*\*details: Any)
26291 26299

### *exception* outrage.bulk.SourceMissingError(code: str, \*\*details: Any)
26700 26708

### *exception* outrage.bulk.StaleImportError(code: str, \*\*details: Any)
27107 27115

### *exception* outrage.bulk.UncheckedWriteError(code: str, \*\*details: Any)
27729 27737

### *exception* outrage.bulk.UnmappableError(code: str, \*\*details: Any)
28553 28561

### outrage.bulk.check_extensions(extensions: str) → str
28958 28966

### outrage.bulk.check_write(opened: Store, key: str, path: str | PathLike[str], root: str | PathLike[str], \*, storing: str | PathLike[str] | None = None, overwrite: bool = False) → Check
29585 29595

### outrage.bulk.contained_file(root: str | PathLike[str], path: str | PathLike[str], key: str) → Path
31919 31931

### outrage.bulk.contained_path(root: str | PathLike[str], relative: PurePosixPath, key: str) → Path
32905 32919

### outrage.bulk.container_name(segment: str) → str
34464 34480

### outrage.bulk.content_hash(content: str) → str
35489 35507

### outrage.bulk.copied(source: Store, target: Store, subtree: BoundedSubtree = store.EVERYTHING, \*, key_range: KeyRange = store.UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
35897 35917

### outrage.bulk.declared_format(name: str) → str | None
41132 41154

### outrage.bulk.documents_from_store(opened: Store, key: str | None = None) → Iterator[tuple[Transfer, tuple[str, str, str | None, str | None] | None]]
41551 41575

### outrage.bulk.documents_from_tree(source: str | PathLike[str], key: str | None = None, \*, hidden: bool = False, extensions: str = DEFAULT_EXTENSIONS) → Iterator[tuple[Transfer, tuple[str, str, str | None, str | None] | None]]
43079 43105

### outrage.bulk.export_document(opened: Store, key: str, root: str | PathLike[str]) → Exported
45186 45214

### outrage.bulk.export_root() → Path
46172 46202

### outrage.bulk.export_tree(opened: Store, key: str | None, target: str | PathLike[str], \*, on_conflict: str = SKIP, dry_run: bool = False, extensions: str = DEFAULT_EXTENSIONS) → Iterator[Transfer]
46996 47028

### outrage.bulk.file_name(segment: str, format: str | None = None) → str
49243 49277

### outrage.bulk.import_document(opened: Store, key: str, path: str | PathLike[str], root: str | PathLike[str], \*, against: str | PathLike[str] | None = None, overwrite: bool = False, generate_contents: bool = False) → Imported
49992 50028

### outrage.bulk.import_tree(opened: Store, source: str | PathLike[str], key: str | None = None, \*, on_conflict: str = SKIP, dry_run: bool = False, hidden: bool = False, extensions: str = DEFAULT_EXTENSIONS) → Iterator[Transfer]
52903 52941

### outrage.bulk.key_for_path(relative: PurePosixPath | str, prefix: str | None = None, \*, extensions: str = DEFAULT_EXTENSIONS) → tuple[str, str | None]
55494 55534

### outrage.bulk.levels(opened: Store, key: str | None, \*, descendant_counts: bool = False, descendant_chars: bool = False) → Iterator[Entry]
57736 57778

### outrage.bulk.new_export_file(root: str | PathLike[str], format: str | None = None) → Path
58937 58981

### outrage.bulk.notes_for(imported: Imported) → list[Note]
60276 60322

### outrage.bulk.notes_for_checked_write(key: str, check: Check, stored: int) → list[Note]
61592 61640

### outrage.bulk.notes_for_copy(landing: str, \*, dry_run: bool, on_conflict: str, unchanged_since: str | None, changed: Sequence[str], next_cursor: str | None, limit: int, failed: int, named: int, stopped: bool, mounts_kept: Sequence[str], unwritable: Sequence[str] = ()) → list[Note]
62494 62544

### outrage.bulk.notes_for_delete(key: str, \*, dry_run: bool, remaining: int, mounts_kept: Sequence[str], unwritable: Sequence[str] = ()) → list[Note]
64812 64864

### outrage.bulk.notes_for_export(exported: Exported) → list[Note]
66383 66437

### outrage.bulk.notes_for_write(previous: int | None, stored: int) → list[Note]
67244 67300

### outrage.bulk.overlapping(source: str, target: str, \*, reroot: bool = False) → None
68209 68267

### outrage.bulk.pack(target: str | PathLike[str], documents: Iterator[tuple[Transfer, tuple[str, str, str | None, str | None] | None]], \*, overwrite: bool = False, dry_run: bool = False, byte_lengths: bool = True) → Iterator[Transfer]
69813 69873

### outrage.bulk.path_for_key(key: str, format: str | None = None, \*, extensions: str = DEFAULT_EXTENSIONS) → PurePosixPath
71956 72018

### outrage.bulk.renew(opened: Store, key: str, check: Check, content: str | None = None) → None
74120 74184

### outrage.bulk.size_of(opened: Store, key: str) → int | None
75221 75287

### outrage.bulk.sweep_exports(root: str | PathLike[str], max_age: timedelta = EXPORT_MAX_AGE, now: datetime | None = None) → int
75915 75983

### outrage.bulk.walk(opened: Store, key: str | None, \*, descendant_counts: bool = False, descendant_chars: bool = False) → Iterator[Entry]
77026 77096
