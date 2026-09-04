Create an offset index from the headings in one stored Markdown document.

The source document is left unchanged. Its ATX and setext headings are copied
in source order, with all intervening content replaced by the zero-based
character offset of the corresponding heading. Headings inside fenced code
blocks are ignored.

The generated Markdown overwrites direct metadata named by `metadata_name`,
which defaults to `contents`. Pass the name without its leading `!`.
