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

### outrage.bulk.EXPORT_DIR_PREFIX *= 'outrage-export'*
5507 5507

### outrage.bulk.EXPORT_MAX_AGE *= datetime.timedelta(days=7)*
6248 6248

### outrage.bulk.EXTENSION_BY_FORMAT *= {'html': '.html', 'json': '.json', 'markdown': '.md', 'text': '.txt'}*
6606 6606

### *class* outrage.bulk.ExportRecord(key: [str](https://docs.python.org/3/library/stdtypes.html#str), content_sha256: [str](https://docs.python.org/3/library/stdtypes.html#str), exported_at: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, updated_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, store: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)
7071 7071

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
8848 8848

#### content_sha256 *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
9136 9136

#### exported_at *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
9398 9398

#### format *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
9511 9511

#### updated_at *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
9682 9682

#### store *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
10080 10080

#### *static* path_for(file: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
10474 10474

#### write(file: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
10814 10816

#### *classmethod* read(file: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [ExportRecord](#outrage.bulk.ExportRecord) | [None](https://docs.python.org/3/library/constants.html#None)
11138 11142

#### followed(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), content: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [ExportRecord](#outrage.bulk.ExportRecord)
11840 11846

### *class* outrage.bulk.Exported(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), excerpt: [Excerpt](store.md#outrage.store.Excerpt), record: [ExportRecord](#outrage.bulk.ExportRecord))
12576 12584

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
12938 12946

#### excerpt *: [Excerpt](store.md#outrage.store.Excerpt)*
13069 13077

#### record *: [ExportRecord](#outrage.bulk.ExportRecord)*
13165 13173

### outrage.bulk.FALLBACK_PREFIX *= 'document-'*
13269 13277

### outrage.bulk.FORMAT_BY_EXTENSION *= {'.html': 'html', '.json': 'json', '.md': 'markdown', '.txt': 'text'}*
13780 13788

### *class* outrage.bulk.Imported(key: [str](https://docs.python.org/3/library/stdtypes.html#str), stored: [int](https://docs.python.org/3/library/functions.html#int), previous: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None), unchecked_code: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, unchecked_from: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, unedited: [bool](https://docs.python.org/3/library/functions.html#bool) = False, copied_from: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, overwritten: [bool](https://docs.python.org/3/library/functions.html#bool) = False, changed_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)
14523 14531

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
15717 15725

#### stored *: [int](https://docs.python.org/3/library/functions.html#int)*
15829 15837

#### previous *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*
15927 15935

#### unchecked_code *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
16239 16247

#### unchecked_from *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
16937 16945

#### unedited *: [bool](https://docs.python.org/3/library/functions.html#bool)*
17369 17377

#### copied_from *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
17731 17739

#### overwritten *: [bool](https://docs.python.org/3/library/functions.html#bool)*
18211 18219

#### changed_at *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
18363 18371

### outrage.bulk.PAGE *= 200*
18643 18651

### outrage.bulk.Packable
18960 18968

### outrage.bulk.RECORD_SUFFIX *= '.outrage.json'*
19913 19921

### outrage.bulk.TEMP_PREFIX *= '.outrage-'*
20198 20206

### outrage.bulk.TRAVERSAL *= ('.', '..')*
20609 20617

### *exception* outrage.bulk.ExportRootError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
20888 20896

### *exception* outrage.bulk.FileMissingError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
21216 21224

### *exception* outrage.bulk.OverlappingCopyError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
21627 21635

### *exception* outrage.bulk.SourceMissingError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
22034 22042

### *exception* outrage.bulk.StaleImportError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
22439 22447

### *exception* outrage.bulk.UncheckedWriteError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
23060 23068

### *exception* outrage.bulk.UnmappableError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
23883 23891

### outrage.bulk.check_write(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, storing: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Check](#outrage.bulk.Check)
24286 24294

### outrage.bulk.contained_file(root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
26611 26621

### outrage.bulk.contained_path(root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], relative: [PurePosixPath](https://docs.python.org/3/library/pathlib.html#pathlib.PurePosixPath), key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
27592 27604

### outrage.bulk.content_hash(content: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
29148 29162

### outrage.bulk.copied(source: [Store](store.md#outrage.store.Store), target: [Store](store.md#outrage.store.Store), subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = store.EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = store.UNBOUNDED, prefix: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, reroot: [bool](https://docs.python.org/3/library/functions.html#bool) = False, on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str) = SKIP, unchanged_since: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Generator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Generator)[[Transfer](store.md#outrage.store.Transfer), [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]
29554 29570

### outrage.bulk.documents_from_store(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Transfer](store.md#outrage.store.Transfer), [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)] | [None](https://docs.python.org/3/library/constants.html#None)]]
34775 34793

### outrage.bulk.documents_from_tree(source: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, hidden: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Transfer](store.md#outrage.store.Transfer), [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)] | [None](https://docs.python.org/3/library/constants.html#None)]]
36292 36312

### outrage.bulk.export_document(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [Exported](#outrage.bulk.Exported)
38291 38313

### outrage.bulk.export_root() → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
39274 39298

### outrage.bulk.export_tree(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), target: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str) = SKIP, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Transfer](store.md#outrage.store.Transfer)]
40098 40124

### outrage.bulk.import_document(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, against: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Imported](#outrage.bulk.Imported)
41774 41802

### outrage.bulk.import_tree(opened: [Store](store.md#outrage.store.Store), source: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str) = SKIP, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, hidden: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Transfer](store.md#outrage.store.Transfer)]
44234 44264

### outrage.bulk.pack(target: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], documents: [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Transfer](store.md#outrage.store.Transfer), [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)] | [None](https://docs.python.org/3/library/constants.html#None)]], \*, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, byte_lengths: [bool](https://docs.python.org/3/library/functions.html#bool) = True) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Transfer](store.md#outrage.store.Transfer)]
46443 46475

### outrage.bulk.key_for_path(relative: [PurePosixPath](https://docs.python.org/3/library/pathlib.html#pathlib.PurePosixPath) | [str](https://docs.python.org/3/library/stdtypes.html#str), prefix: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]
48572 48606

### outrage.bulk.levels(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Entry](store.md#outrage.store.Entry)]
49687 49723

### outrage.bulk.new_export_file(root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
50441 50479

### outrage.bulk.notes_for(imported: [Imported](#outrage.bulk.Imported)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]
51776 51816

### outrage.bulk.notes_for_checked_write(key: [str](https://docs.python.org/3/library/stdtypes.html#str), check: [Check](#outrage.bulk.Check), stored: [int](https://docs.python.org/3/library/functions.html#int)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]
53091 53133

### outrage.bulk.notes_for_copy(landing: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool), on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str), unchanged_since: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), changed: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)], next_cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), limit: [int](https://docs.python.org/3/library/functions.html#int), failed: [int](https://docs.python.org/3/library/functions.html#int), named: [int](https://docs.python.org/3/library/functions.html#int), stopped: [bool](https://docs.python.org/3/library/functions.html#bool), mounts_kept: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]
53990 54034

### outrage.bulk.notes_for_delete(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool), remaining: [int](https://docs.python.org/3/library/functions.html#int), mounts_kept: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]
56082 56128

### outrage.bulk.notes_for_export(exported: [Exported](#outrage.bulk.Exported)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]
57357 57405

### outrage.bulk.notes_for_write(previous: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None), stored: [int](https://docs.python.org/3/library/functions.html#int)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]
58217 58267

### outrage.bulk.overlapping(source: [str](https://docs.python.org/3/library/stdtypes.html#str), target: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, reroot: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [None](https://docs.python.org/3/library/constants.html#None)
59178 59230

### outrage.bulk.path_for_key(key: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [PurePosixPath](https://docs.python.org/3/library/pathlib.html#pathlib.PurePosixPath)
60778 60832

### outrage.bulk.renew(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), check: [Check](#outrage.bulk.Check), content: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [None](https://docs.python.org/3/library/constants.html#None)
61470 61526

### outrage.bulk.size_of(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)
62567 62625

### outrage.bulk.sweep_exports(root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], max_age: [timedelta](https://docs.python.org/3/library/datetime.html#datetime.timedelta) = EXPORT_MAX_AGE, now: [datetime](https://docs.python.org/3/library/datetime.html#datetime.datetime) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [int](https://docs.python.org/3/library/functions.html#int)
63258 63318

### outrage.bulk.walk(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Entry](store.md#outrage.store.Entry)]
64365 64427
