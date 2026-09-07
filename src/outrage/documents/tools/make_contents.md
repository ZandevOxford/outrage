Create an offset index from the headings in one stored Markdown or HTML
document.

The source document is left unchanged. Markdown ATX and setext headings, or
HTML `h1` through `h6` elements, are copied in source order as Markdown, with
all intervening content replaced by the zero-based character and UTF-8 byte
offsets of the corresponding source heading. Headings inside Markdown fenced
code blocks are ignored. HTML markup and link targets are removed while
readable text remains.

`strip_links` applies to Markdown sources. HTML markup is always flattened.

The generated Markdown overwrites direct metadata named by `metadata_name`,
which defaults to `contents`. Pass the name without its leading `!`.
