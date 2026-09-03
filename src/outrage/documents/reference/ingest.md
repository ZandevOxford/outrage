# outrage.ingest

Convert one local document to Markdown and store it under an Outrage key.

MarkItDown is an optional dependency and is imported only when conversion is
requested.  This keeps importing `outrage` and running every unrelated
command independent of the document-conversion stack.

### *exception* outrage.ingest.IngestError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`RuntimeError`](https://docs.python.org/3/library/exceptions.html#RuntimeError)

A local document could not be converted or safely stored.

### *class* outrage.ingest.IngestResult(source: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), key: [str](https://docs.python.org/3/library/stdtypes.html#str), title: [str](https://docs.python.org/3/library/stdtypes.html#str), characters: [int](https://docs.python.org/3/library/functions.html#int), format: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['markdown'], title_key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), dry_run: [bool](https://docs.python.org/3/library/functions.html#bool))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

The facts about one converted document, whether previewed or written.

#### source *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

The absolute, resolved local file converted.

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The normalized destination key.

#### title *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The title chosen for the document.

#### characters *: [int](https://docs.python.org/3/library/functions.html#int)*

The number of Markdown characters produced.

#### format *: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['markdown']*

The stored format, always `"markdown"`.

#### title_key *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

The metadata key written for the title, or `None` for a dry run.

#### dry_run *: [bool](https://docs.python.org/3/library/functions.html#bool)*

Whether conversion was performed without writing the document.

### outrage.ingest.ingest_document(store: [Store](store.md#outrage.store.Store), source: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, title: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [IngestResult](#outrage.ingest.IngestResult)

Convert a local file to Markdown and store it at `key`.

Only `markitdown.MarkItDown.convert_local()` is used and converter
plugins are disabled.  URLs, directories and missing files are refused.
An existing destination is preserved unless `overwrite` is true.
`dry_run` still performs the conversion but writes neither the document
nor its title.

The title is selected from the explicit `title`, MarkItDown's title, and
finally the source filename stem, in that order.  The source path is
returned to the caller but is not stored as metadata.
