# Document contents

Build a small offset index from the headings in a Markdown or HTML document.

Each heading carries **two** numbers, character offset then byte offset. The
character offset is a fact about the document as a Python string; the byte
offset is the same position in its UTF-8, which is what survives the document
being written out to a file. So an index generated here can drive a seeking
read of a 20 MB document, and can also drive anything byte-addressed that was
handed the exported file -- which is what the pair is for.

### *class* outrage.contents.ContentsResult(source_key: [str](https://docs.python.org/3/library/stdtypes.html#str), metadata_key: [str](https://docs.python.org/3/library/stdtypes.html#str), headings: [int](https://docs.python.org/3/library/functions.html#int), source_characters: [int](https://docs.python.org/3/library/functions.html#int), source_bytes: [int](https://docs.python.org/3/library/functions.html#int), characters: [int](https://docs.python.org/3/library/functions.html#int))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

The facts about one generated Markdown contents document.

#### source_key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The normalized key of the source document read.

#### metadata_key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The metadata key where the generated contents were stored.

#### headings *: [int](https://docs.python.org/3/library/functions.html#int)*

The number of headings found.

#### source_characters *: [int](https://docs.python.org/3/library/functions.html#int)*

The number of characters scanned in the source document.

#### source_bytes *: [int](https://docs.python.org/3/library/functions.html#int)*

The number of UTF-8 bytes those characters occupy, which is the other
number a caller needs to make sense of the second column.

#### characters *: [int](https://docs.python.org/3/library/functions.html#int)*

The number of characters stored in the generated contents document.

### outrage.contents.make_contents(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, metadata_name: [str](https://docs.python.org/3/library/stdtypes.html#str) = 'contents', strip_links: [bool](https://docs.python.org/3/library/functions.html#bool) = True) → [ContentsResult](#outrage.contents.ContentsResult)

Store an offset outline of one Markdown or HTML document as metadata.

The source document is not changed. Markdown ATX and setext headings or
HTML h1-h6 elements are copied to direct metadata named by
`metadata_name`; all section bodies are replaced by the heading's two
zero-based offsets, character then byte. HTML markup is flattened to plain
visible text. Markdown inline link destinations are stripped by default
while their text remains; `strip_links=False` keeps Markdown headings
byte for byte. Regenerating the contents overwrites that metadata value.

The byte number is what makes this more than a table of contents: paired
with a byte-addressed [`retrieve_document()`](store.md#outrage.store.Store.retrieve_document) it is
random access into a document far too large to read, without splitting it
into children first.

### outrage.contents.render_contents(markdown: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, strip_links: [bool](https://docs.python.org/3/library/functions.html#bool) = True) → [str](https://docs.python.org/3/library/stdtypes.html#str)

Render each Markdown heading followed by its two source offsets.

Heading spelling is kept literal apart from inline link destinations,
which are removed by default while their text is kept. Pass
`strip_links=False` to preserve the complete heading. Everything between
headings is omitted, and the numbers beneath each heading are the
zero-based offsets at which that heading begins in `markdown`: the
character offset first, then the UTF-8 byte offset, separated by a space.
Headings inside fenced code blocks are ignored.

Bare numbers, John's call, so **the token count on the line is the only
thing that tells the two formats apart** -- an index written before this
carries one number per heading. That is why regenerating an index is part
of adopting this rather than housekeeping to get to later.

### outrage.contents.render_html_contents(html: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

Render each HTML h1-h6 element as a plain Markdown heading and two offsets.

Nested markup and link targets are omitted while readable text, decoded
character references and image alternative text remain. The zero-based
character and UTF-8 byte offsets beneath each heading point to the opening
`<` of its source element.
