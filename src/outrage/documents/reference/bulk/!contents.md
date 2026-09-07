# outrage.bulk
0 0

### *class* outrage.bulk.Check(file: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), record: [ExportRecord](#outrage.bulk.ExportRecord) | [None](https://docs.python.org/3/library/constants.html#None), previous: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None), changed_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, unchecked_code: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, unchecked_from: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, overwritten: [bool](https://docs.python.org/3/library/functions.html#bool) = False)
1628 1628

#### file *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
2913 2913

#### record *: [ExportRecord](#outrage.bulk.ExportRecord) | [None](https://docs.python.org/3/library/constants.html#None)*
3115 3115

#### previous *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*
3455 3455

#### changed_at *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
3742 3742

#### unchecked_code *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
3954 3954

#### unchecked_from *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
4221 4221

#### overwritten *: [bool](https://docs.python.org/3/library/functions.html#bool)*
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

### *class* outrage.bulk.ExportRecord(key: [str](https://docs.python.org/3/library/stdtypes.html#str), content_sha256: [str](https://docs.python.org/3/library/stdtypes.html#str), exported_at: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, updated_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, store: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)
11203 11203

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
12980 12980

#### content_sha256 *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
13268 13268

#### exported_at *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
13530 13530

#### format *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
13643 13643

#### updated_at *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
13814 13814

#### store *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
14212 14212

#### *static* path_for(file: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
14606 14606

#### write(file: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
14946 14948

#### *classmethod* read(file: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [ExportRecord](#outrage.bulk.ExportRecord) | [None](https://docs.python.org/3/library/constants.html#None)
15270 15274

#### followed(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), content: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [ExportRecord](#outrage.bulk.ExportRecord)
15972 15978

### *class* outrage.bulk.Exported(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), excerpt: [Excerpt](store.md#outrage.store.Excerpt), record: [ExportRecord](#outrage.bulk.ExportRecord))
16708 16716

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
17070 17078

#### excerpt *: [Excerpt](store.md#outrage.store.Excerpt)*
17201 17209

#### record *: [ExportRecord](#outrage.bulk.ExportRecord)*
17297 17305

### outrage.bulk.FALLBACK_PREFIX *= 'document-'*
17401 17409

### outrage.bulk.FORMAT_BY_EXTENSION *= {'.html': 'html', '.json': 'json', '.md': 'markdown', '.txt': 'text'}*
17912 17920

### *class* outrage.bulk.Imported(key: [str](https://docs.python.org/3/library/stdtypes.html#str), stored: [int](https://docs.python.org/3/library/functions.html#int), previous: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None), unchecked_code: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, unchecked_from: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, unedited: [bool](https://docs.python.org/3/library/functions.html#bool) = False, copied_from: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, overwritten: [bool](https://docs.python.org/3/library/functions.html#bool) = False, changed_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)
18655 18663

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
19849 19857

#### stored *: [int](https://docs.python.org/3/library/functions.html#int)*
19961 19969

#### previous *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*
20059 20067

#### unchecked_code *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
20371 20379

#### unchecked_from *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
21069 21077

#### unedited *: [bool](https://docs.python.org/3/library/functions.html#bool)*
21501 21509

#### copied_from *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
21863 21871

#### overwritten *: [bool](https://docs.python.org/3/library/functions.html#bool)*
22343 22351

#### changed_at *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
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

### *exception* outrage.bulk.ExportRootError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
25020 25028

### *exception* outrage.bulk.FileMissingError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
25348 25356

### *exception* outrage.bulk.OverlappingCopyError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
25759 25767

### *exception* outrage.bulk.SourceMissingError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
26166 26174

### *exception* outrage.bulk.StaleImportError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
26571 26579

### *exception* outrage.bulk.UncheckedWriteError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
27192 27200

### *exception* outrage.bulk.UnmappableError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
28015 28023

### outrage.bulk.check_extensions(extensions: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
28418 28426

### outrage.bulk.check_write(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, storing: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Check](#outrage.bulk.Check)
29043 29053

### outrage.bulk.contained_file(root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
31368 31380

### outrage.bulk.contained_path(root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], relative: [PurePosixPath](https://docs.python.org/3/library/pathlib.html#pathlib.PurePosixPath), key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
32349 32363

### outrage.bulk.container_name(segment: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
33905 33921

### outrage.bulk.content_hash(content: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
34928 34946

### outrage.bulk.copied(source: [Store](store.md#outrage.store.Store), target: [Store](store.md#outrage.store.Store), subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = store.EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = store.UNBOUNDED, prefix: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, reroot: [bool](https://docs.python.org/3/library/functions.html#bool) = False, on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str) = SKIP, unchanged_since: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Generator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Generator)[[Transfer](store.md#outrage.store.Transfer), [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]
35334 35354

### outrage.bulk.declared_format(name: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
40555 40577

### outrage.bulk.documents_from_store(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Transfer](store.md#outrage.store.Transfer), [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)] | [None](https://docs.python.org/3/library/constants.html#None)]]
40971 40995

### outrage.bulk.documents_from_tree(source: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, hidden: [bool](https://docs.python.org/3/library/functions.html#bool) = False, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) = DEFAULT_EXTENSIONS) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Transfer](store.md#outrage.store.Transfer), [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)] | [None](https://docs.python.org/3/library/constants.html#None)]]
42488 42514

### outrage.bulk.export_document(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [Exported](#outrage.bulk.Exported)
44580 44608

### outrage.bulk.export_root() → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
45563 45593

### outrage.bulk.export_tree(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), target: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str) = SKIP, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) = DEFAULT_EXTENSIONS) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Transfer](store.md#outrage.store.Transfer)]
46387 46419

### outrage.bulk.file_name(segment: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)
48627 48661

### outrage.bulk.import_document(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, against: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Imported](#outrage.bulk.Imported)
49372 49408

### outrage.bulk.import_tree(opened: [Store](store.md#outrage.store.Store), source: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str) = SKIP, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, hidden: [bool](https://docs.python.org/3/library/functions.html#bool) = False, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) = DEFAULT_EXTENSIONS) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Transfer](store.md#outrage.store.Transfer)]
51832 51870

### outrage.bulk.key_for_path(relative: [PurePosixPath](https://docs.python.org/3/library/pathlib.html#pathlib.PurePosixPath) | [str](https://docs.python.org/3/library/stdtypes.html#str), prefix: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) = DEFAULT_EXTENSIONS) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]
54415 54455

### outrage.bulk.levels(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Entry](store.md#outrage.store.Entry)]
56649 56691

### outrage.bulk.new_export_file(root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
57403 57447

### outrage.bulk.notes_for(imported: [Imported](#outrage.bulk.Imported)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]
58738 58784

### outrage.bulk.notes_for_checked_write(key: [str](https://docs.python.org/3/library/stdtypes.html#str), check: [Check](#outrage.bulk.Check), stored: [int](https://docs.python.org/3/library/functions.html#int)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]
60053 60101

### outrage.bulk.notes_for_copy(landing: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool), on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str), unchanged_since: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), changed: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)], next_cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), limit: [int](https://docs.python.org/3/library/functions.html#int), failed: [int](https://docs.python.org/3/library/functions.html#int), named: [int](https://docs.python.org/3/library/functions.html#int), stopped: [bool](https://docs.python.org/3/library/functions.html#bool), mounts_kept: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]
60952 61002

### outrage.bulk.notes_for_delete(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool), remaining: [int](https://docs.python.org/3/library/functions.html#int), mounts_kept: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]
63044 63096

### outrage.bulk.notes_for_export(exported: [Exported](#outrage.bulk.Exported)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]
64319 64373

### outrage.bulk.notes_for_write(previous: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None), stored: [int](https://docs.python.org/3/library/functions.html#int)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]
65179 65235

### outrage.bulk.overlapping(source: [str](https://docs.python.org/3/library/stdtypes.html#str), target: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, reroot: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [None](https://docs.python.org/3/library/constants.html#None)
66140 66198

### outrage.bulk.pack(target: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], documents: [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Transfer](store.md#outrage.store.Transfer), [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)] | [None](https://docs.python.org/3/library/constants.html#None)]], \*, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, byte_lengths: [bool](https://docs.python.org/3/library/functions.html#bool) = True) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Transfer](store.md#outrage.store.Transfer)]
67740 67800

### outrage.bulk.path_for_key(key: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) = DEFAULT_EXTENSIONS) → [PurePosixPath](https://docs.python.org/3/library/pathlib.html#pathlib.PurePosixPath)
69869 69931

### outrage.bulk.renew(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), check: [Check](#outrage.bulk.Check), content: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [None](https://docs.python.org/3/library/constants.html#None)
72029 72093

### outrage.bulk.size_of(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)
73126 73192

### outrage.bulk.sweep_exports(root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], max_age: [timedelta](https://docs.python.org/3/library/datetime.html#datetime.timedelta) = EXPORT_MAX_AGE, now: [datetime](https://docs.python.org/3/library/datetime.html#datetime.datetime) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [int](https://docs.python.org/3/library/functions.html#int)
73817 73885

### outrage.bulk.walk(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Entry](store.md#outrage.store.Entry)]
74924 74994
