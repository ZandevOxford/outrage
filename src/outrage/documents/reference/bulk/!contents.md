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
14430 14430 239

#### *static* path_for(file: str | PathLike[str]) → Path
14826 14826 246

#### write(file: str | PathLike[str]) → Path
15168 15170 250

#### *classmethod* read(file: str | PathLike[str]) → ExportRecord | None
15494 15498 254

#### followed(opened: Store, key: str, content: str) → ExportRecord
16199 16205 264

### *class* outrage.bulk.Exported(path: Path, excerpt: Excerpt, record: ExportRecord)
16937 16945 277

#### path *: Path*
17300 17308 283

#### excerpt *: Excerpt*
17431 17439 287

#### record *: ExportRecord*
17527 17535 291

### outrage.bulk.FALLBACK_PREFIX *= 'document-'*
17631 17639 295

### outrage.bulk.FORMAT_BY_EXTENSION *= {'.html': 'html', '.json': 'json', '.md': 'markdown', '.txt': 'text'}*
18142 18150 305

### *class* outrage.bulk.Imported(key: str, stored: int, previous: int | None, unchecked_code: str | None = None, unchecked_from: str | None = None, unedited: bool = False, copied_from: str | None = None, overwritten: bool = False, changed_at: str | None = None, contents_key: str | None = None)
18885 18893 316

#### key *: str*
20241 20249 322

#### stored *: int*
20354 20362 326

#### previous *: int | None*
20453 20461 330

#### unchecked_code *: str | None*
20767 20775 336

#### unchecked_from *: str | None*
21467 21475 347

#### unedited *: bool*
21901 21909 354

#### copied_from *: str | None*
22264 22272 361

#### overwritten *: bool*
22746 22754 369

#### changed_at *: str | None*
22899 22907 373

#### contents_key *: str | None*
23181 23189 378

### outrage.bulk.PAGE *= 200*
23468 23476 383

### outrage.bulk.Packable
23785 23793 390

### outrage.bulk.RECORD_SUFFIX *= '.outrage.json'*
24747 24755 399

### outrage.bulk.TEMP_PREFIX *= '.outrage-'*
25032 25040 405

### outrage.bulk.TRAVERSAL *= ('.', '..')*
25443 25451 413

### *exception* outrage.bulk.ExportRootError(code: str, \*\*details: Any)
25722 25730 420

### *exception* outrage.bulk.FileMissingError(code: str, \*\*details: Any)
26051 26059 426

### *exception* outrage.bulk.OverlappingCopyError(code: str, \*\*details: Any)
26464 26472 432

### *exception* outrage.bulk.SourceMissingError(code: str, \*\*details: Any)
26873 26881 438

### *exception* outrage.bulk.StaleImportError(code: str, \*\*details: Any)
27280 27288 444

### *exception* outrage.bulk.UncheckedWriteError(code: str, \*\*details: Any)
27902 27910 455

### *exception* outrage.bulk.UnmappableError(code: str, \*\*details: Any)
28726 28734 470

### outrage.bulk.check_extensions(extensions: str) → str
29131 29139 476

### outrage.bulk.check_write(opened: Store, key: str, path: str | PathLike[str], root: str | PathLike[str], \*, storing: str | PathLike[str] | None = None, overwrite: bool = False) → Check
29758 29768 487

### outrage.bulk.contained_file(root: str | PathLike[str], path: str | PathLike[str], key: str) → Path
32092 32104 515

### outrage.bulk.contained_path(root: str | PathLike[str], relative: PurePosixPath, key: str) → Path
33078 33092 525

### outrage.bulk.container_name(segment: str) → str
34637 34653 545

### outrage.bulk.content_hash(content: str) → str
35662 35680 567

### outrage.bulk.copied(source: Store, target: Store, subtree: BoundedSubtree = store.EVERYTHING, \*, key_range: KeyRange = store.UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
36070 36090 575

### outrage.bulk.declared_format(name: str) → str | None
41305 41327 643

### outrage.bulk.documents_from_store(opened: Store, key: str | None = None) → Iterator[tuple[Transfer, tuple[str, str, str | None, str | None] | None]]
41724 41748 652

### outrage.bulk.documents_from_tree(source: str | PathLike[str], key: str | None = None, \*, hidden: bool = False, extensions: str = DEFAULT_EXTENSIONS) → Iterator[tuple[Transfer, tuple[str, str, str | None, str | None] | None]]
43252 43278 666

### outrage.bulk.export_document(opened: Store, key: str, root: str | PathLike[str]) → Exported
45359 45387 682

### outrage.bulk.export_root() → Path
46345 46375 696

### outrage.bulk.export_tree(opened: Store, key: str | None, target: str | PathLike[str], \*, on_conflict: str = SKIP, dry_run: bool = False, extensions: str = DEFAULT_EXTENSIONS) → Iterator[Transfer]
47169 47201 711

### outrage.bulk.file_name(segment: str, format: str | None = None) → str
49416 49450 738

### outrage.bulk.import_document(opened: Store, key: str, path: str | PathLike[str], root: str | PathLike[str], \*, against: str | PathLike[str] | None = None, overwrite: bool = False, generate_contents: bool = False) → Imported
50165 50201 753

### outrage.bulk.import_tree(opened: Store, source: str | PathLike[str], key: str | None = None, \*, on_conflict: str = SKIP, dry_run: bool = False, hidden: bool = False, extensions: str = DEFAULT_EXTENSIONS) → Iterator[Transfer]
53076 53114 793

### outrage.bulk.key_for_path(relative: PurePosixPath | str, prefix: str | None = None, \*, extensions: str = DEFAULT_EXTENSIONS) → tuple[str, str | None]
55667 55707 827

### outrage.bulk.levels(opened: Store, key: str | None, \*, descendant_counts: bool = False, descendant_chars: bool = False) → Iterator[Entry]
57909 57951 868

### outrage.bulk.new_export_file(root: str | PathLike[str], format: str | None = None) → Path
59110 59154 883

### outrage.bulk.notes_for(imported: Imported) → list[Note]
60449 60495 902

### outrage.bulk.notes_for_checked_write(key: str, check: Check, stored: int) → list[Note]
61765 61813 925

### outrage.bulk.notes_for_copy(landing: str, \*, dry_run: bool, on_conflict: str, unchanged_since: str | None, changed: Sequence[str], next_cursor: str | None, limit: int, failed: int, named: int, stopped: bool, mounts_kept: Sequence[str], unwritable: Sequence[str] = ()) → list[Note]
62667 62717 939

### outrage.bulk.notes_for_delete(key: str, \*, dry_run: bool, remaining: int, mounts_kept: Sequence[str], unwritable: Sequence[str] = ()) → list[Note]
64985 65037 957

### outrage.bulk.notes_for_export(exported: Exported) → list[Note]
66556 66610 975

### outrage.bulk.notes_for_write(previous: int | None, stored: int) → list[Note]
67417 67473 990

### outrage.bulk.overlapping(source: str, target: str, \*, reroot: bool = False) → None
68382 68440 1004

### outrage.bulk.pack(target: str | PathLike[str], documents: Iterator[tuple[Transfer, tuple[str, str, str | None, str | None] | None]], \*, overwrite: bool = False, dry_run: bool = False, byte_lengths: bool = True) → Iterator[Transfer]
69986 70046 1029

### outrage.bulk.path_for_key(key: str, format: str | None = None, \*, extensions: str = DEFAULT_EXTENSIONS) → PurePosixPath
72129 72191 1046

### outrage.bulk.renew(opened: Store, key: str, check: Check, content: str | None = None) → None
74293 74357 1089

### outrage.bulk.size_of(opened: Store, key: str) → int | None
75394 75460 1106

### outrage.bulk.sweep_exports(root: str | PathLike[str], max_age: timedelta = EXPORT_MAX_AGE, now: datetime | None = None) → int
76088 76156 1116

### outrage.bulk.walk(opened: Store, key: str | None, \*, descendant_counts: bool = False, descendant_chars: bool = False) → Iterator[Entry]
77199 77269 1129
