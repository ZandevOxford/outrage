Generate useful direct metadata from one stored Markdown or HTML document.

By default this writes both a Markdown offset index at `!contents` and a parsed
title at `!title`. Set `contents` or `title` false to leave that metadata
untouched. With both false, the source is validated and reported but nothing is
written.

Markdown contents include ATX and setext headings; HTML contents include `h1`
through `h6`. Each becomes a Markdown heading followed by its zero-based
character and UTF-8 byte offsets in the source. Markdown headings inside fenced
code blocks are ignored. HTML markup and link targets are removed while
readable text remains.

The title is the first non-empty level-one ATX heading in Markdown. For HTML, a
non-empty `title` element wins, with the first non-empty `h1` as fallback. If no
title can be parsed, `title` is returned as null and an existing `!title` is not
deleted or replaced.

`metadata_name` and `strip_links` apply only when generating contents.
`metadata_name` defaults to `contents` and is passed without its leading `!`.
`strip_links` removes Markdown inline link targets while retaining their text;
HTML is always flattened.

When both outputs are enabled, `metadata_name` cannot be `title`, because both
generated values would address the same `!title` metadata.
