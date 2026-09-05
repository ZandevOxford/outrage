# outrage.ingest
0 0

### *exception* outrage.ingest.IngestError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
296 296

### *class* outrage.ingest.IngestResult(source: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), key: [str](https://docs.python.org/3/library/stdtypes.html#str), title: [str](https://docs.python.org/3/library/stdtypes.html#str), characters: [int](https://docs.python.org/3/library/functions.html#int), format: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['markdown'], title_key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), dry_run: [bool](https://docs.python.org/3/library/functions.html#bool))
689 689

#### source *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
1459 1459

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
1590 1590

#### title *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
1696 1696

#### characters *: [int](https://docs.python.org/3/library/functions.html#int)*
1807 1807

#### format *: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['markdown']*
1933 1933

#### title_key *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
2075 2075

#### dry_run *: [bool](https://docs.python.org/3/library/functions.html#bool)*
2284 2284

### outrage.ingest.available() → [bool](https://docs.python.org/3/library/functions.html#bool)
2428 2428

### outrage.ingest.ingest_document(store: [Store](store.md#outrage.store.Store), source: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, title: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [IngestResult](#outrage.ingest.IngestResult)
3208 3210
