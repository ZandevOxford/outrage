# Document titles

Extract a document title from Markdown or HTML without storing it.

### outrage.titles.html_title(html: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)

Return an HTML document's title, falling back to its first non-empty h1.

A non-empty `title` element wins wherever it occurs in the source. Nested
markup and link targets are omitted while readable text, decoded character
references and image alternative text remain.

### outrage.titles.markdown_title(markdown: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)

Return the first non-empty ATX level-one heading in `markdown`.

Up to three leading spaces are accepted. Headings of other levels and
apparent headings inside backtick or tilde fenced code blocks are ignored.
An optional closing hash sequence is omitted from the returned text.

### outrage.titles.parse_title(content: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)

Return the title parsed from Markdown or HTML `content`.

`format` must be `"markdown"` or `"html"`. This function only
parses the supplied string; it does not read from or write to a store.
