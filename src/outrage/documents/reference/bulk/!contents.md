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
9466 9466

### outrage.bulk.EXTENSION_MODES *= ('strip', 'keep')*
9931 9931

### *class* outrage.bulk.ExportRecord(key: [str](https://docs.python.org/3/library/stdtypes.html#str), content_sha256: [str](https://docs.python.org/3/library/stdtypes.html#str), exported_at: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, updated_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, store: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)
11189 11189

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
12966 12966

#### content_sha256 *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
13254 13254

#### exported_at *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
13516 13516

#### format *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
13629 13629

#### updated_at *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
13800 13800

#### store *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
14198 14198

#### *static* path_for(file: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
14592 14592

#### write(file: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
14932 14934

#### *classmethod* read(file: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [ExportRecord](#outrage.bulk.ExportRecord) | [None](https://docs.python.org/3/library/constants.html#None)
15256 15260

#### followed(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), content: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [ExportRecord](#outrage.bulk.ExportRecord)
15958 15964

### *class* outrage.bulk.Exported(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), excerpt: [Excerpt](store.md#outrage.store.Excerpt), record: [ExportRecord](#outrage.bulk.ExportRecord))
16694 16702

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
17056 17064

#### excerpt *: [Excerpt](store.md#outrage.store.Excerpt)*
17187 17195

#### record *: [ExportRecord](#outrage.bulk.ExportRecord)*
17283 17291

### outrage.bulk.FALLBACK_PREFIX *= 'document-'*
17387 17395

### outrage.bulk.FORMAT_BY_EXTENSION *= {'.html': 'html', '.json': 'json', '.md': 'markdown', '.txt': 'text'}*
17898 17906

### *class* outrage.bulk.Imported(key: [str](https://docs.python.org/3/library/stdtypes.html#str), stored: [int](https://docs.python.org/3/library/functions.html#int), previous: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None), unchecked_code: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, unchecked_from: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, unedited: [bool](https://docs.python.org/3/library/functions.html#bool) = False, copied_from: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, overwritten: [bool](https://docs.python.org/3/library/functions.html#bool) = False, changed_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)
18641 18649

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
19835 19843

#### stored *: [int](https://docs.python.org/3/library/functions.html#int)*
19947 19955

#### previous *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*
20045 20053

#### unchecked_code *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
20357 20365

#### unchecked_from *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
21055 21063

#### unedited *: [bool](https://docs.python.org/3/library/functions.html#bool)*
21487 21495

#### copied_from *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
21849 21857

#### overwritten *: [bool](https://docs.python.org/3/library/functions.html#bool)*
22329 22337

#### changed_at *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
22481 22489

### outrage.bulk.PAGE *= 200*
22761 22769

### outrage.bulk.Packable
23078 23086

### outrage.bulk.RECORD_SUFFIX *= '.outrage.json'*
24031 24039

### outrage.bulk.TEMP_PREFIX *= '.outrage-'*
24316 24324

### outrage.bulk.TRAVERSAL *= ('.', '..')*
24727 24735

### *exception* outrage.bulk.ExportRootError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
25006 25014

### *exception* outrage.bulk.FileMissingError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
25334 25342

### *exception* outrage.bulk.OverlappingCopyError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
25745 25753

### *exception* outrage.bulk.SourceMissingError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
26152 26160

### *exception* outrage.bulk.StaleImportError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
26557 26565

### *exception* outrage.bulk.UncheckedWriteError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
27178 27186

### *exception* outrage.bulk.UnmappableError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
28001 28009

### outrage.bulk.check_extensions(extensions: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
28404 28412

### outrage.bulk.check_write(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, storing: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Check](#outrage.bulk.Check)
29029 29039

### outrage.bulk.contained_file(root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
31354 31366

### outrage.bulk.contained_path(root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], relative: [PurePosixPath](https://docs.python.org/3/library/pathlib.html#pathlib.PurePosixPath), key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
32335 32349

### outrage.bulk.container_name(segment: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
33891 33907

### outrage.bulk.content_hash(content: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
34914 34932

### outrage.bulk.copied(source: [Store](store.md#outrage.store.Store), target: [Store](store.md#outrage.store.Store), subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = store.EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = store.UNBOUNDED, prefix: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, reroot: [bool](https://docs.python.org/3/library/functions.html#bool) = False, on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str) = SKIP, unchanged_since: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Generator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Generator)[[Transfer](store.md#outrage.store.Transfer), [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]
35320 35340

### outrage.bulk.declared_format(name: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
40541 40563

### outrage.bulk.documents_from_store(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Transfer](store.md#outrage.store.Transfer), [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)] | [None](https://docs.python.org/3/library/constants.html#None)]]
40957 40981

### outrage.bulk.documents_from_tree(source: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, hidden: [bool](https://docs.python.org/3/library/functions.html#bool) = False, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) = DEFAULT_EXTENSIONS) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Transfer](store.md#outrage.store.Transfer), [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)] | [None](https://docs.python.org/3/library/constants.html#None)]]
42474 42500

### outrage.bulk.export_document(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [Exported](#outrage.bulk.Exported)
44566 44594

### outrage.bulk.export_root() → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
45549 45579

### outrage.bulk.export_tree(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), target: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str) = SKIP, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) = DEFAULT_EXTENSIONS) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Transfer](store.md#outrage.store.Transfer)]
46373 46405

### outrage.bulk.file_name(segment: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)
48613 48647

### outrage.bulk.import_document(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, against: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Imported](#outrage.bulk.Imported)
49358 49394

### outrage.bulk.import_tree(opened: [Store](store.md#outrage.store.Store), source: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str) = SKIP, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, hidden: [bool](https://docs.python.org/3/library/functions.html#bool) = False, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) = DEFAULT_EXTENSIONS) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Transfer](store.md#outrage.store.Transfer)]
51818 51856

### outrage.bulk.key_for_path(relative: [PurePosixPath](https://docs.python.org/3/library/pathlib.html#pathlib.PurePosixPath) | [str](https://docs.python.org/3/library/stdtypes.html#str), prefix: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) = DEFAULT_EXTENSIONS) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]
54401 54441

### outrage.bulk.levels(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Entry](store.md#outrage.store.Entry)]
56520 56562

### outrage.bulk.new_export_file(root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
57274 57318

### outrage.bulk.notes_for(imported: [Imported](#outrage.bulk.Imported)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]
58609 58655

### outrage.bulk.notes_for_checked_write(key: [str](https://docs.python.org/3/library/stdtypes.html#str), check: [Check](#outrage.bulk.Check), stored: [int](https://docs.python.org/3/library/functions.html#int)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]
59924 59972

### outrage.bulk.notes_for_copy(landing: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool), on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str), unchanged_since: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), changed: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)], next_cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), limit: [int](https://docs.python.org/3/library/functions.html#int), failed: [int](https://docs.python.org/3/library/functions.html#int), named: [int](https://docs.python.org/3/library/functions.html#int), stopped: [bool](https://docs.python.org/3/library/functions.html#bool), mounts_kept: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]
60823 60873

### outrage.bulk.notes_for_delete(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool), remaining: [int](https://docs.python.org/3/library/functions.html#int), mounts_kept: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]
62915 62967

### outrage.bulk.notes_for_export(exported: [Exported](#outrage.bulk.Exported)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]
64190 64244

### outrage.bulk.notes_for_write(previous: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None), stored: [int](https://docs.python.org/3/library/functions.html#int)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]
65050 65106

### outrage.bulk.overlapping(source: [str](https://docs.python.org/3/library/stdtypes.html#str), target: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, reroot: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [None](https://docs.python.org/3/library/constants.html#None)
66011 66069

### outrage.bulk.pack(target: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], documents: [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Transfer](store.md#outrage.store.Transfer), [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)] | [None](https://docs.python.org/3/library/constants.html#None)]], \*, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, byte_lengths: [bool](https://docs.python.org/3/library/functions.html#bool) = True) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Transfer](store.md#outrage.store.Transfer)]
67611 67671

### outrage.bulk.path_for_key(key: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) = DEFAULT_EXTENSIONS) → [PurePosixPath](https://docs.python.org/3/library/pathlib.html#pathlib.PurePosixPath)
69740 69802

### outrage.bulk.renew(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), check: [Check](#outrage.bulk.Check), content: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [None](https://docs.python.org/3/library/constants.html#None)
71900 71964

### outrage.bulk.size_of(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)
72997 73063

### outrage.bulk.sweep_exports(root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], max_age: [timedelta](https://docs.python.org/3/library/datetime.html#datetime.timedelta) = EXPORT_MAX_AGE, now: [datetime](https://docs.python.org/3/library/datetime.html#datetime.datetime) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [int](https://docs.python.org/3/library/functions.html#int)
73688 73756

### outrage.bulk.walk(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Entry](store.md#outrage.store.Entry)]
74795 74865
