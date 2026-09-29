# outrage.bulk
0 0 1

### *class* outrage.bulk.Check(file: Path, record: ExportRecord | None, previous: int | None, changed_at: str | None = None, unchecked_code: str | None = None, unchecked_from: str | None = None, overwritten: bool = False)
1788 1788 35

#### file *: Path*
3084 3084 46

#### record *: ExportRecord | None*
3286 3286 51

#### previous *: int | None*
3627 3627 57

#### changed_at *: str | None*
3916 3916 62

#### unchecked_code *: str | None*
4130 4130 66

#### unchecked_from *: str | None*
4399 4399 71

#### overwritten *: bool*
4603 4603 75

### outrage.bulk.Document
4883 4883 81

### outrage.bulk.DEFAULT_EXTENSIONS *= 'strip'*
5695 5695 90

### outrage.bulk.EXPORT_DIR_PREFIX *= 'outrage-export'*
5965 5965 96

### outrage.bulk.EXPORT_MAX_AGE *= datetime.timedelta(days=7)*
6706 6706 109

### outrage.bulk.CONTAINER_PREFIX *= '.!'*
7064 7064 116

### outrage.bulk.EXTENSION_BY_FORMAT *= {'html': '.html', 'json': '.json', 'markdown': '.md', 'text': '.txt'}*
9668 9668 161

### outrage.bulk.EXTENSION_MODES *= ('strip', 'keep')*
10133 10133 169

### *class* outrage.bulk.ExportRecord(key: str, content_sha256: str, exported_at: str, format: str | None = None, updated_at: str | None = None, store: str | None = None)
11391 11391 191

#### key *: str*
13178 13178 213

#### content_sha256 *: str*
13467 13467 219

#### exported_at *: str*
13730 13730 225

#### format *: str | None*
13844 13844 229

#### updated_at *: str | None*
14017 14017 233

#### store *: str | None*
14590 14590 242

#### *static* path_for(file: str | PathLike[str]) → Path
14986 14986 249

#### write(file: str | PathLike[str]) → Path
15328 15330 253

#### *classmethod* read(file: str | PathLike[str]) → ExportRecord | None
15654 15658 257

#### followed(opened: Store, key: str, content: str) → ExportRecord
16359 16365 267

### *class* outrage.bulk.Exported(path: Path, excerpt: Excerpt, record: ExportRecord)
17097 17105 280

#### path *: Path*
17460 17468 286

#### excerpt *: Excerpt*
17591 17599 290

#### record *: ExportRecord*
17687 17695 294

### outrage.bulk.FALLBACK_PREFIX *= 'document-'*
17791 17799 298

### outrage.bulk.FORMAT_BY_EXTENSION *= {'.html': 'html', '.json': 'json', '.md': 'markdown', '.txt': 'text'}*
18302 18310 308

### *class* outrage.bulk.Imported(key: str, stored: int, previous: int | None, unchecked_code: str | None = None, unchecked_from: str | None = None, unedited: bool = False, copied_from: str | None = None, overwritten: bool = False, changed_at: str | None = None, contents_key: str | None = None)
19045 19053 319

#### key *: str*
20401 20409 325

#### stored *: int*
20514 20522 329

#### previous *: int | None*
20613 20621 333

#### unchecked_code *: str | None*
20927 20935 339

#### unchecked_from *: str | None*
21627 21635 350

#### unedited *: bool*
22061 22069 357

#### copied_from *: str | None*
22424 22432 364

#### overwritten *: bool*
22906 22914 372

#### changed_at *: str | None*
23059 23067 376

#### contents_key *: str | None*
23341 23349 381

### outrage.bulk.PAGE *= 200*
23628 23636 386

### outrage.bulk.Packable
23945 23953 393

### outrage.bulk.RECORD_SUFFIX *= '.outrage.json'*
24907 24915 402

### outrage.bulk.TEMP_PREFIX *= '.outrage-'*
25192 25200 408

### outrage.bulk.TRAVERSAL *= ('.', '..')*
25603 25611 416

### *exception* outrage.bulk.ExportRootError(code: str, \*\*details: Any)
25882 25890 423

### *exception* outrage.bulk.FileMissingError(code: str, \*\*details: Any)
26211 26219 429

### *exception* outrage.bulk.OverlappingCopyError(code: str, \*\*details: Any)
26624 26632 435

### *exception* outrage.bulk.SourceMissingError(code: str, \*\*details: Any)
27033 27041 441

### *exception* outrage.bulk.StaleImportError(code: str, \*\*details: Any)
27440 27448 447

### *exception* outrage.bulk.UncheckedWriteError(code: str, \*\*details: Any)
28062 28070 458

### *exception* outrage.bulk.UnmappableError(code: str, \*\*details: Any)
28886 28894 473

### outrage.bulk.check_extensions(extensions: str) → str
29291 29299 479

### outrage.bulk.check_write(opened: Store, key: str, path: str | PathLike[str], root: str | PathLike[str], \*, storing: str | PathLike[str] | None = None, overwrite: bool = False) → Check
29918 29928 490

### outrage.bulk.contained_file(root: str | PathLike[str], path: str | PathLike[str], key: str) → Path
32252 32264 518

### outrage.bulk.contained_path(root: str | PathLike[str], relative: PurePosixPath, key: str) → Path
33238 33252 528

### outrage.bulk.container_name(segment: str) → str
34797 34813 548

### outrage.bulk.content_hash(content: str) → str
35822 35840 570

### outrage.bulk.copied(source: Store, target: Store, subtree: BoundedSubtree = store.EVERYTHING, \*, key_range: KeyRange = store.UNBOUNDED, prefix: str | None = None, reroot: bool = False, on_conflict: str = SKIP, unchanged_since: str | None = None, dry_run: bool = False, cursor: str | None = None, limit: int | None = None) → Generator[Transfer, None, str | None]
36230 36250 578

### outrage.bulk.declared_format(name: str) → str | None
41465 41487 646

### outrage.bulk.documents_from_store(opened: Store, key: str | None = None) → Iterator[tuple[Transfer, tuple[str, str, str | None, str | None] | None]]
41884 41908 655

### outrage.bulk.documents_from_tree(source: str | PathLike[str], key: str | None = None, \*, hidden: bool = False, extensions: str = DEFAULT_EXTENSIONS) → Iterator[tuple[Transfer, tuple[str, str, str | None, str | None] | None]]
43412 43438 669

### outrage.bulk.export_document(opened: Store, key: str, root: str | PathLike[str]) → Exported
45519 45547 685

### outrage.bulk.export_root() → Path
46505 46535 699

### outrage.bulk.export_tree(opened: Store, key: str | None, target: str | PathLike[str], \*, on_conflict: str = SKIP, dry_run: bool = False, extensions: str = DEFAULT_EXTENSIONS) → Iterator[Transfer]
47329 47361 714

### outrage.bulk.file_name(segment: str, format: str | None = None) → str
49576 49610 741

### outrage.bulk.import_document(opened: Store, key: str, path: str | PathLike[str], root: str | PathLike[str], \*, against: str | PathLike[str] | None = None, overwrite: bool = False, generate_contents: bool = False) → Imported
50325 50361 756

### outrage.bulk.import_tree(opened: Store, source: str | PathLike[str], key: str | None = None, \*, on_conflict: str = SKIP, dry_run: bool = False, hidden: bool = False, extensions: str = DEFAULT_EXTENSIONS) → Iterator[Transfer]
53236 53274 796

### outrage.bulk.key_for_path(relative: PurePosixPath | str, prefix: str | None = None, \*, extensions: str = DEFAULT_EXTENSIONS) → tuple[str, str | None]
55827 55867 830

### outrage.bulk.levels(opened: Store, key: str | None, \*, descendant_counts: bool = False, descendant_chars: bool = False) → Iterator[Entry]
58069 58111 871

### outrage.bulk.new_export_file(root: str | PathLike[str], format: str | None = None) → Path
59270 59314 886

### outrage.bulk.notes_for(imported: Imported) → list[Note]
60609 60655 905

### outrage.bulk.notes_for_checked_write(key: str, check: Check, stored: int) → list[Note]
61925 61973 928

### outrage.bulk.notes_for_copy(landing: str, \*, dry_run: bool, on_conflict: str, unchanged_since: str | None, changed: Sequence[str], next_cursor: str | None, limit: int, failed: int, named: int, stopped: bool, mounts_kept: Sequence[str], unwritable: Sequence[str] = ()) → list[Note]
62827 62877 942

### outrage.bulk.notes_for_delete(key: str, \*, dry_run: bool, remaining: int, mounts_kept: Sequence[str], unwritable: Sequence[str] = ()) → list[Note]
65145 65197 960

### outrage.bulk.notes_for_export(exported: Exported) → list[Note]
66716 66770 978

### outrage.bulk.notes_for_survey(unavailable: Sequence[str]) → list[Note]
67577 67633 993

### outrage.bulk.notes_for_write(previous: int | None, stored: int) → list[Note]
68160 68218 1001

### outrage.bulk.overlapping(source: str, target: str, \*, reroot: bool = False) → None
69125 69185 1015

### outrage.bulk.pack(target: str | PathLike[str], documents: Iterator[tuple[Transfer, tuple[str, str, str | None, str | None] | None]], \*, overwrite: bool = False, dry_run: bool = False, byte_lengths: bool = True) → Iterator[Transfer]
70729 70791 1040

### outrage.bulk.path_for_key(key: str, format: str | None = None, \*, extensions: str = DEFAULT_EXTENSIONS) → PurePosixPath
72872 72936 1057

### outrage.bulk.renew(opened: Store, key: str, check: Check, content: str | None = None) → None
75036 75102 1100

### outrage.bulk.size_of(opened: Store, key: str) → int | None
76137 76205 1117

### outrage.bulk.sweep_exports(root: str | PathLike[str], max_age: timedelta = EXPORT_MAX_AGE, now: datetime | None = None) → int
76831 76901 1127

### outrage.bulk.walk(opened: Store, key: str | None, \*, descendant_counts: bool = False, descendant_chars: bool = False) → Iterator[Entry]
77942 78014 1140
