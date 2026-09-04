# Markdown contents

Build a small offset index from the headings in a Markdown document.

### *class* outrage.contents.ContentsResult(source_key: [str](https://docs.python.org/3/library/stdtypes.html#str), metadata_key: [str](https://docs.python.org/3/library/stdtypes.html#str), headings: [int](https://docs.python.org/3/library/functions.html#int), source_characters: [int](https://docs.python.org/3/library/functions.html#int), characters: [int](https://docs.python.org/3/library/functions.html#int))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

The facts about one generated Markdown contents document.

#### source_key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The normalized key of the Markdown document read.

#### metadata_key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The metadata key where the generated contents were stored.

#### headings *: [int](https://docs.python.org/3/library/functions.html#int)*

The number of headings found.

#### source_characters *: [int](https://docs.python.org/3/library/functions.html#int)*

The number of characters scanned in the source document.

#### characters *: [int](https://docs.python.org/3/library/functions.html#int)*

The number of characters stored in the generated contents document.

### outrage.contents.make_contents(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, metadata_name: [str](https://docs.python.org/3/library/stdtypes.html#str) = 'contents') → [ContentsResult](#outrage.contents.ContentsResult)

Store a character-offset outline of one Markdown document as metadata.

The source document is not changed. Its ATX and setext headings are copied
to direct metadata named by `metadata_name`; all section bodies are
replaced by the heading's zero-based character offset. Regenerating the
contents overwrites that metadata value.

### outrage.contents.render_contents(markdown: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

Render each Markdown heading followed by its source character offset.

Heading spelling is kept literal. Everything between headings is omitted,
and the number beneath each heading is the zero-based character offset at
which that heading begins in `markdown`. Headings inside fenced code
blocks are ignored.
