# outrage.bulk
0 0 1

### *class* outrage.bulk.Check(file: Path, record: ExportRecord | None, previous: int | None, changed_at: str | None = None, unchecked_code: str | None = None, unchecked_from: str | None = None, overwritten: bool = False)
1628 1628 32

#### file *: Path*
2924 2924 43

#### record *: ExportRecord | None*
3126 3126 48

#### previous *: int | None*
3467 3467 54

#### changed_at *: str | None*
3756 3756 59

#### unchecked_code *: str | None*
3970 3970 63

#### unchecked_from *: str | None*
4239 4239 68

#### overwritten *: bool*
4443 4443 72

### outrage.bulk.Document
4723 4723 78

### outrage.bulk.DEFAULT_EXTENSIONS *= 'strip'*
5535 5535 87

### outrage.bulk.EXPORT_DIR_PREFIX *= 'outrage-export'*
5805 5805 93

### outrage.bulk.EXPORT_MAX_AGE *= datetime.timedelta(days=7)*
6546 6546 106

### outrage.bulk.CONTAINER_PREFIX *= '.!'*
6904 6904 113

### outrage.bulk.EXTENSION_BY_FORMAT *= {'html': '.html', 'json': '.json', 'markdown': '.md', 'text': '.txt'}*
9508 9508 158

### outrage.bulk.EXTENSION_MODES *= ('strip', 'keep')*
9973 9973 166

### *class* outrage.bulk.ExportRecord(key: str, content_sha256: str, exported_at: str, format: str | None = None, updated_at: str | None = None, store: str | None = None)
11231 11231 188

#### key *: str*
13018 13018 210

#### content_sha256 *: str*
13307 13307 216

#### exported_at *: str*
13570 13570 222

#### format *: str | None*
13684 13684 226

#### updated_at *: str | None*
13857 13857 230

#### store *: str | None*
14257 14257 237

#### *static* path_for(file: str | PathLike[str]) → Path
14653 14653 244

#### write(file: str | PathLike[str]) → Path
14995 14997 248

#### *classmethod* read(file: str | PathLike[str]) → ExportRecord | None
15321 15325 252

#### followed(opened: Store, key: str, content: str) → ExportRecord
16026 16032 262

### *class* outrage.bulk.Exported(path: Path, excerpt: Excerpt, record: ExportRecord)
16764 16772 275

#### path *: Path*
17127 17135 281

#### excerpt *: Excerpt*
17258 17266 285

#### record *: ExportRecord*
17354 17362 289

### outrage.bulk.FALLBACK_PREFIX *= 'document-'*
17458 17466 293

### outrage.bulk.FORMAT_BY_EXTENSION *= {'.html': 'html', '.json': 'json', '.md': 'markdown', '.txt': 'text'}*
17969 17977 303

### *class* outrage.bulk.Imported(key: str, stored: int, previous: int | None, unchecked_code: str | None = None, unchecked_from: str | None = None, unedited: bool = False, copied_from: str | None = None, overwritten: bool = False, changed_at: str | None = None, contents_key: str | None = None)
18712 18720 314

#### key *: str*
20068 20076 320

#### stored *: int*
20181 20189 324

#### previous *: int | None*
20280 20288 328

#### unchecked_code *: str | None*
20594 20602 334

#### unchecked_from *: str | None*
21294 21302 345

#### unedited *: bool*
21728 21736 352

#### copied_from *: str | None*
22091 22099 359

#### overwritten *: bool*
22573 22581 367

#### changed_at *: str | None*
22726 22734 371

#### contents_key *: str | None*
23008 23016 376

### outrage.bulk.PAGE *= 200*
23295 23303 381

### outrage.bulk.Packable
23612 23620 388

### outrage.bulk.RECORD_SUFFIX *= '.outrage.json'*
24574 24582 397

### outrage.bulk.TEMP_PREFIX *= '.outrage-'*
24859 24867 403

### outrage.bulk.TRAVERSAL *= ('.', '..')*
25270 25278 411

### *exception* outrage.bulk.ExportRootError(code: str, \*\*details: Any)
25549 25557 418

### *exception* outrage.bulk.FileMissingError(code: str, \*\*details: Any)
25878 25886 424

### *exception* outrage.bulk.OverlappingCopyError(code: str, \*\*details: Any)
26291 26299 430

### *exception* outrage.bulk.SourceMissingError(code: str, \*\*details: Any)
26700 26708 436

### *exception* outrage.bulk.StaleImportError(code: str, \*\*details: Any)
27107 27115 442

### *exception* outrage.bulk.UncheckedWriteError(code: str, \*\*details: Any)
27729 27737 453

### *exception* outrage.bulk.UnmappableError(code: str, \*\*details: Any)
28553 28561 468

### outrage.bulk.check_extensions(extensions: str) → str
28958 28966 474

### outrage.bulk.check_write(opened: Store, key: str, path: str | PathLike[str], root: str | PathLike[str], \*, storing: str | PathLike[str] | None = None, overwrite: bool = False) → Check
29585 29595 485

### outrage.bulk.contained_file(root: str | PathLike[str], path: str | PathLike[str], key: str) → Path
31919 31931 513

### outrage.bulk.contained_path(root: str | PathLike[str], relative: PurePosixPath, key: str) → Path
32905 32919 523

### outrage.bulk.container_name(segment: str) → str
34464 34480 543

### outrage.bulk.content_hash(content: str) → str
35489 35507 565

### outrage.bulk.copied(source: Store, target: Store, subtree: BoundedSubtree = store.EVERYTHING, \*, key_range: KeyRange = store.UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
35897 35917 573

### outrage.bulk.declared_format(name: str) → str | None
41132 41154 641

### outrage.bulk.documents_from_store(opened: Store, key: str | None = None) → Iterator[tuple[Transfer, tuple[str, str, str | None, str | None] | None]]
41551 41575 650

### outrage.bulk.documents_from_tree(source: str | PathLike[str], key: str | None = None, \*, hidden: bool = False, extensions: str = DEFAULT_EXTENSIONS) → Iterator[tuple[Transfer, tuple[str, str, str | None, str | None] | None]]
43079 43105 664

### outrage.bulk.export_document(opened: Store, key: str, root: str | PathLike[str]) → Exported
45186 45214 680

### outrage.bulk.export_root() → Path
46172 46202 694

### outrage.bulk.export_tree(opened: Store, key: str | None, target: str | PathLike[str], \*, on_conflict: str = SKIP, dry_run: bool = False, extensions: str = DEFAULT_EXTENSIONS) → Iterator[Transfer]
46996 47028 709

### outrage.bulk.file_name(segment: str, format: str | None = None) → str
49243 49277 736

### outrage.bulk.import_document(opened: Store, key: str, path: str | PathLike[str], root: str | PathLike[str], \*, against: str | PathLike[str] | None = None, overwrite: bool = False, generate_contents: bool = False) → Imported
49992 50028 751

### outrage.bulk.import_tree(opened: Store, source: str | PathLike[str], key: str | None = None, \*, on_conflict: str = SKIP, dry_run: bool = False, hidden: bool = False, extensions: str = DEFAULT_EXTENSIONS) → Iterator[Transfer]
52903 52941 791

### outrage.bulk.key_for_path(relative: PurePosixPath | str, prefix: str | None = None, \*, extensions: str = DEFAULT_EXTENSIONS) → tuple[str, str | None]
55494 55534 825

### outrage.bulk.levels(opened: Store, key: str | None, \*, descendant_counts: bool = False, descendant_chars: bool = False) → Iterator[Entry]
57736 57778 866

### outrage.bulk.new_export_file(root: str | PathLike[str], format: str | None = None) → Path
58937 58981 881

### outrage.bulk.notes_for(imported: Imported) → list[Note]
60276 60322 900

### outrage.bulk.notes_for_checked_write(key: str, check: Check, stored: int) → list[Note]
61592 61640 923

### outrage.bulk.notes_for_copy(landing: str, \*, dry_run: bool, on_conflict: str, unchanged_since: str | None, changed: Sequence[str], next_cursor: str | None, limit: int, failed: int, named: int, stopped: bool, mounts_kept: Sequence[str], unwritable: Sequence[str] = ()) → list[Note]
62494 62544 937

### outrage.bulk.notes_for_delete(key: str, \*, dry_run: bool, remaining: int, mounts_kept: Sequence[str], unwritable: Sequence[str] = ()) → list[Note]
64812 64864 955

### outrage.bulk.notes_for_export(exported: Exported) → list[Note]
66383 66437 973

### outrage.bulk.notes_for_write(previous: int | None, stored: int) → list[Note]
67244 67300 988

### outrage.bulk.overlapping(source: str, target: str, \*, reroot: bool = False) → None
68209 68267 1002

### outrage.bulk.pack(target: str | PathLike[str], documents: Iterator[tuple[Transfer, tuple[str, str, str | None, str | None] | None]], \*, overwrite: bool = False, dry_run: bool = False, byte_lengths: bool = True) → Iterator[Transfer]
69813 69873 1027

### outrage.bulk.path_for_key(key: str, format: str | None = None, \*, extensions: str = DEFAULT_EXTENSIONS) → PurePosixPath
71956 72018 1044

### outrage.bulk.renew(opened: Store, key: str, check: Check, content: str | None = None) → None
74120 74184 1087

### outrage.bulk.size_of(opened: Store, key: str) → int | None
75221 75287 1104

### outrage.bulk.sweep_exports(root: str | PathLike[str], max_age: timedelta = EXPORT_MAX_AGE, now: datetime | None = None) → int
75915 75983 1114

### outrage.bulk.walk(opened: Store, key: str | None, \*, descendant_counts: bool = False, descendant_chars: bool = False) → Iterator[Entry]
77026 77096 1127
