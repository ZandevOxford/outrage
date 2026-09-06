# outrage.store
0 0

### outrage.store.BACKUP_DIR_NAME *= 'backups'*
3022 3022

### outrage.store.BACKUP_STAMP *= '%Y%m%d-%H%M%S'*
3152 3152

### outrage.store.CHANGED *= 'changed'*
3427 3427

### outrage.store.CONFLICTS *= ('skip', 'overwrite', 'overwrite-unchanged', 'stop')*
3813 3813

### outrage.store.DEFAULT_BACKEND *= 'sqlite'*
3958 3958

### outrage.store.backend_names() → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...]
4201 4201

### outrage.store.check_read_position(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, offset: [int](https://docs.python.org/3/library/functions.html#int), byte_offset: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None), pattern: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), occurrence: [int](https://docs.python.org/3/library/functions.html#int)) → [None](https://docs.python.org/3/library/constants.html#None)
4612 4614

### outrage.store.check_unchanged(opened: [Store](#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), unchanged_since: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), \*, action: [str](https://docs.python.org/3/library/stdtypes.html#str) = 'write over', subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = True, key_range: [KeyRange](#outrage.store.KeyRange) = UNBOUNDED) → [None](https://docs.python.org/3/library/constants.html#None)
5601 5605

### outrage.store.DEFAULT_BULK_MAX_CHARS *= 2000*
7600 7606

### outrage.store.DEFAULT_DIR_NAME *= '.outrage'*
7751 7757

### outrage.store.DEFAULT_MAX_CHARS *= 8000*
7907 7913

### outrage.store.ENCODINGS *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...]* *= ('json-string',)*
8094 8100

### outrage.store.ENV_DIR *= 'OUTRAGE_DIR'*
8362 8368

### outrage.store.EVERYTHING *= BoundedSubtree(key=None, depth=None)*
8601 8607

### outrage.store.FAILED *= 'failed'*
8810 8816

### outrage.store.FORMATS *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...]* *= ('markdown', 'json', 'text', 'html')*
8926 8932

### outrage.store.OVERWRITE *= 'overwrite'*
9430 9436

### outrage.store.OVERWRITE_UNCHANGED *= 'overwrite-unchanged'*
9507 9513

### outrage.store.READ *= 'read'*
9959 9965

### outrage.store.SKIP *= 'skip'*
10320 10326

### outrage.store.SKIPPED *= 'skipped'*
10486 10492

### outrage.store.STOP *= 'stop'*
10605 10611

### outrage.store.STOPPED *= 'stopped'*
10786 10792

### outrage.store.UNBOUNDED *= KeyRange(after=None, after_inclusive=None, after_subtree=None, before=None, before_inclusive=None, final_subtree=None)*
11023 11029

### outrage.store.WROTE *= 'wrote'*
11421 11427

### *class* outrage.store.AuditRow(key: [str](https://docs.python.org/3/library/stdtypes.html#str), doc_key: [str](https://docs.python.org/3/library/stdtypes.html#str), meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), parent: [str](https://docs.python.org/3/library/stdtypes.html#str), chars: [int](https://docs.python.org/3/library/functions.html#int))
11536 11542

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
12752 12758

#### doc_key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
12825 12831

#### meta_name *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
12990 12996

#### parent *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
13184 13190

#### chars *: [int](https://docs.python.org/3/library/functions.html#int)*
13416 13422

### *class* outrage.store.Backup(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), bytes: [int](https://docs.python.org/3/library/functions.html#int), documents: [int](https://docs.python.org/3/library/functions.html#int), integrity: [str](https://docs.python.org/3/library/stdtypes.html#str))
13492 13498

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
13948 13954

#### bytes *: [int](https://docs.python.org/3/library/functions.html#int)*
14031 14037

#### documents *: [int](https://docs.python.org/3/library/functions.html#int)*
14107 14113

#### integrity *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
14249 14255

### *exception* outrage.store.BackendError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
14386 14392

### *exception* outrage.store.BackupError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
14805 14811

### *class* outrage.store.BoundedSubtree(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, depth: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None)
15208 15214

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
16229 16235

#### depth *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*
16366 16372

### *exception* outrage.store.ChangedSinceError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
16506 16512

### *class* outrage.store.DocumentMatch(document: [Entry](#outrage.store.Entry), witnesses: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[MatchWitness](#outrage.store.MatchWitness), ...])
17582 17588

#### document *: [Entry](#outrage.store.Entry)*
17929 17935

#### witnesses *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[MatchWitness](#outrage.store.MatchWitness), ...]*
17978 17984

### outrage.store.Encoding
18111 18117

### *class* outrage.store.Entry(key: [str](https://docs.python.org/3/library/stdtypes.html#str), kind: [str](https://docs.python.org/3/library/stdtypes.html#str), size: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), updated_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None))
18451 18457

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
19133 19139

#### kind *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
19206 19212

#### size *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*
19381 19387

#### format *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
19520 19526

#### updated_at *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
19660 19666

### *class* outrage.store.Excerpt(key: [str](https://docs.python.org/3/library/stdtypes.html#str), content: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), updated_at: [str](https://docs.python.org/3/library/stdtypes.html#str), offset: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None), returned: [int](https://docs.python.org/3/library/functions.html#int), total: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None), next_offset: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None), byte_offset: [int](https://docs.python.org/3/library/functions.html#int), total_bytes: [int](https://docs.python.org/3/library/functions.html#int), next_byte_offset: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None))
19804 19810

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
21058 21064

#### content *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
21131 21137

#### format *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
21208 21214

#### updated_at *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
21348 21354

#### offset *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*
21428 21434

#### returned *: [int](https://docs.python.org/3/library/functions.html#int)*
21948 21954

#### total *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*
22059 22065

#### next_offset *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*
22405 22411

#### byte_offset *: [int](https://docs.python.org/3/library/functions.html#int)*
22706 22712

#### total_bytes *: [int](https://docs.python.org/3/library/functions.html#int)*
23063 23069

#### next_byte_offset *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*
23191 23197

#### *property* truncated *: [bool](https://docs.python.org/3/library/functions.html#bool)*
23492 23498

### *class* outrage.store.FileStore(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, filename: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None, mount_point: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)
24072 24078

#### default_filename *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*
26268 26274

#### format_version *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[int](https://docs.python.org/3/library/functions.html#int)]*
26820 26826

#### *classmethod* in_directory(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, filename: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None, mount_point: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Self](https://docs.python.org/3/library/typing.html#typing.Self)
27419 27425

#### opened_at(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [Self](https://docs.python.org/3/library/typing.html#typing.Self)
29919 29927

#### backup(destination: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Backup](#outrage.store.Backup)
30674 30684

#### verified_backup(target: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [Backup](#outrage.store.Backup)
32434 32446

#### backup_path(destination: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None), \*, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool)) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
33449 33463

#### *abstract property* stored_format_version *: [int](https://docs.python.org/3/library/functions.html#int)*
34479 34495

#### *abstractmethod* audit_rows() → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[AuditRow](#outrage.store.AuditRow)]
35051 35067

#### *abstractmethod* check_file(report: [Report](maintenance.md#outrage.maintenance.Report)) → [None](https://docs.python.org/3/library/constants.html#None)
35821 35839

#### *abstractmethod* repair() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Repaired](maintenance.md#outrage.maintenance.Repaired)]
36597 36617

### outrage.store.Format
37387 37409

### *exception* outrage.store.InvalidArgumentError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
37953 37975

### *exception* outrage.store.KeyNotFoundError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
39281 39303

### *class* outrage.store.KeyRange(after: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, after_inclusive: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, after_subtree: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, before: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, before_inclusive: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, final_subtree: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)
39654 39676

#### after *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
42616 42638

#### after_inclusive *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
42755 42777

#### after_subtree *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
42904 42926

#### before *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
43051 43073

#### before_inclusive *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
43191 43213

#### final_subtree *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
43341 43363

### outrage.store.MatchMode
43488 43510

### *class* outrage.store.MatchWitness(criterion: [int](https://docs.python.org/3/library/functions.html#int), source_key: [str](https://docs.python.org/3/library/stdtypes.html#str), source: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['document', 'metadata'], start: [int](https://docs.python.org/3/library/functions.html#int), end: [int](https://docs.python.org/3/library/functions.html#int))
43698 43720

#### criterion *: [int](https://docs.python.org/3/library/functions.html#int)*
44253 44275

#### source_key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
44333 44355

#### source *: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['document', 'metadata']*
44413 44435

#### start *: [int](https://docs.python.org/3/library/functions.html#int)*
44526 44548

#### end *: [int](https://docs.python.org/3/library/functions.html#int)*
44602 44624

### outrage.store.MetaReader
44676 44698

### *class* outrage.store.MissingMeta(total: [int](https://docs.python.org/3/library/functions.html#int), total_chars: [int](https://docs.python.org/3/library/functions.html#int), sample: [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)])
45597 45619

#### total *: [int](https://docs.python.org/3/library/functions.html#int)*
46276 46298

#### total_chars *: [int](https://docs.python.org/3/library/functions.html#int)*
46415 46437

#### sample *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*
46621 46643

### *class* outrage.store.Page(items: [list](https://docs.python.org/3/library/stdtypes.html#list)[T], returned: [int](https://docs.python.org/3/library/functions.html#int), total: [int](https://docs.python.org/3/library/functions.html#int), total_chars: [int](https://docs.python.org/3/library/functions.html#int), next_cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None))
46833 46855

#### items *: [list](https://docs.python.org/3/library/stdtypes.html#list)[T]*
47760 47782

#### returned *: [int](https://docs.python.org/3/library/functions.html#int)*
47840 47862

#### total *: [int](https://docs.python.org/3/library/functions.html#int)*
47940 47962

#### total_chars *: [int](https://docs.python.org/3/library/functions.html#int)*
48084 48106

#### next_cursor *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
48393 48415

#### *property* truncated *: [bool](https://docs.python.org/3/library/functions.html#bool)*
48599 48621

### *exception* outrage.store.PatternNotFoundError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
48984 49006

### *exception* outrage.store.ReadOnlyStoreError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
49384 49406

### outrage.store.SearchCombination
50255 50277

### *class* outrage.store.SearchCriterion(pattern: [str](https://docs.python.org/3/library/stdtypes.html#str), match: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['contains', 'line', 'regex'], target: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['document', 'metadata'], meta_name: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...] | [None](https://docs.python.org/3/library/constants.html#None) = None)
50452 50474

#### pattern *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
51111 51133

#### match *: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['contains', 'line', 'regex']*
51188 51210

#### target *: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['document', 'metadata']*
51305 51327

#### meta_name *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...] | [None](https://docs.python.org/3/library/constants.html#None)*
51418 51440

### *class* outrage.store.SearchPage(matches: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[DocumentMatch](#outrage.store.DocumentMatch), ...], matched: [int](https://docs.python.org/3/library/functions.html#int), matched_chars: [int](https://docs.python.org/3/library/functions.html#int), scanned: [int](https://docs.python.org/3/library/functions.html#int), total_candidates: [int](https://docs.python.org/3/library/functions.html#int), total_candidate_chars: [int](https://docs.python.org/3/library/functions.html#int), next_cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None))
51630 51652

#### matches *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[DocumentMatch](#outrage.store.DocumentMatch), ...]*
52650 52672

#### matched *: [int](https://docs.python.org/3/library/functions.html#int)*
52783 52805

#### matched_chars *: [int](https://docs.python.org/3/library/functions.html#int)*
52861 52883

#### scanned *: [int](https://docs.python.org/3/library/functions.html#int)*
52945 52967

#### total_candidates *: [int](https://docs.python.org/3/library/functions.html#int)*
53023 53045

#### total_candidate_chars *: [int](https://docs.python.org/3/library/functions.html#int)*
53110 53132

#### next_cursor *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
53202 53224

### outrage.store.SearchTarget
53347 53369

### *class* outrage.store.Store(\*, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None, mount_point: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)
53544 53566

#### writable *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[bool](https://docs.python.org/3/library/functions.html#bool)]* *= True*
54930 54952

#### writes_deferred *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[bool](https://docs.python.org/3/library/functions.html#bool)]* *= False*
55575 55597

#### backend_name *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*
56120 56142

#### *abstractmethod* close() → [None](https://docs.python.org/3/library/constants.html#None)
56476 56498

#### *abstractmethod* store_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), content: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, title: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, encoding: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, updated_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)
56853 56877

#### copy_from(source: [Store](#outrage.store.Store), subtree: [BoundedSubtree](#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](#outrage.store.KeyRange) = UNBOUNDED, prefix: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, reroot: [bool](https://docs.python.org/3/library/functions.html#bool) = False, on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str) = SKIP, unchanged_since: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Generator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Generator)[[Transfer](#outrage.store.Transfer), [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]
59970 59996

#### located(key: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/library/constants.html#None)
65276 65304

#### *abstractmethod* delete(key: [str](https://docs.python.org/3/library/stdtypes.html#str), recursive: [bool](https://docs.python.org/3/library/functions.html#bool) = False, \*, key_range: [KeyRange](#outrage.store.KeyRange) = UNBOUNDED, unchanged_since: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
66214 66244

#### *abstractmethod* descendant_count(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [int](https://docs.python.org/3/library/functions.html#int)
69078 69110

#### latest_change(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
70833 70867

#### *abstractmethod* exists(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [bool](https://docs.python.org/3/library/functions.html#bool)
72834 72870

#### *abstractmethod* level_entry(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Entry](#outrage.store.Entry) | [None](https://docs.python.org/3/library/constants.html#None)
73344 73382

#### *abstractmethod* retrieve_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, offset: [int](https://docs.python.org/3/library/functions.html#int) = 0, byte_offset: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, length: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, pattern: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, occurrence: [int](https://docs.python.org/3/library/functions.html#int) = 0, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_MAX_CHARS) → [Excerpt](#outrage.store.Excerpt)
74227 74267

#### *abstractmethod* list_keys(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](#outrage.store.Page)[[Entry](#outrage.store.Entry)]
75939 75981

#### last_child(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
77119 77163

#### *abstractmethod* get_documents(subtree: [BoundedSubtree](#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_BULK_MAX_CHARS, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, max_total_chars: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](#outrage.store.Page)[[Excerpt](#outrage.store.Excerpt)]
78832 78878

#### find_documents(subtree: [BoundedSubtree](#outrage.store.BoundedSubtree) = EVERYTHING, \*, criteria: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[SearchCriterion](#outrage.store.SearchCriterion)], combine: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['any', 'all'] = 'any', key_range: [KeyRange](#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, scan_limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [SearchPage](#outrage.store.SearchPage)
81005 81053

#### *abstractmethod* missing_meta_stats(subtree: [BoundedSubtree](#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](#outrage.store.KeyRange) = UNBOUNDED, window: [KeyRange](#outrage.store.KeyRange) = UNBOUNDED, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', sample: [int](https://docs.python.org/3/library/functions.html#int) = 0) → [MissingMeta](#outrage.store.MissingMeta)
82253 82303

#### *abstractmethod* keys_missing_meta(subtree: [BoundedSubtree](#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](#outrage.store.Page)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
84110 84162

### *exception* outrage.store.StoreFileError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
85314 85368

### *class* outrage.store.Transfer(action: [str](https://docs.python.org/3/library/stdtypes.html#str), key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/library/constants.html#None), reason: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, characters: [int](https://docs.python.org/3/library/functions.html#int) = 0, error: [OutrageError](errors.md#outrage.errors.OutrageError) | [None](https://docs.python.org/3/library/constants.html#None) = None)
86061 86115

#### action *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
88281 88335

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
88357 88411

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/library/constants.html#None)*
88494 88548

#### reason *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
88641 88695

#### characters *: [int](https://docs.python.org/3/library/functions.html#int)*
88781 88835

#### error *: [OutrageError](errors.md#outrage.errors.OutrageError) | [None](https://docs.python.org/3/library/constants.html#None)*
88862 88916

### outrage.store.default_store(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, filename: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, backend: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None, mount_point: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [FileStore](#outrage.store.FileStore)
88996 89050

### outrage.store.default_store_file() → [str](https://docs.python.org/3/library/stdtypes.html#str)
91203 91259

### outrage.store.entry_kind(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
91858 91916

### outrage.store.meta_reader(scope: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)], [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]]
92531 92591

### outrage.store.open_store(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, filename: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, backend: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None, mount_point: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[FileStore](#outrage.store.FileStore)]
94213 94275

### outrage.store.read_all(store: [Store](#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*kwargs: [Any](https://docs.python.org/3/library/typing.html#typing.Any)) → [Excerpt](#outrage.store.Excerpt)
95508 95572

### outrage.store.resolve_directory(explicit: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
96512 96578

### outrage.store.store_file(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], filename: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
97056 97124
