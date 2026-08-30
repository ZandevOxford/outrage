# Annotate one document

Use this operation to derive one metadata value from one document. The default
is a short `!summary`; accept a metadata name with or without its `!` prefix.
If the document key is unclear, stop rather than guessing.

1. Read the document with `read_document(key=..., max_chars=20000)` and
   follow `next_offset` until it is null. A missing key or a container key is a
   reportable failure, not a reason to create anything.
2. Follow the requested instruction. A default summary is prose with no
   heading, usually no more than a fifth of the source. State the document's
   substance only; do not add outside knowledge or resolve questions it leaves
   open.
3. Store the value at `<document key>/!<metadata name>`. Send generated text
   with `encoding="json-string"`: the `content` argument must be one valid JSON
   string literal. Retry once if that validation rejects a malformed literal.
   Omit `title`, because metadata cannot carry metadata of its own. Never
   overwrite the document key itself.

Report the metadata key written and, when useful, the short value. If nothing
was written, say whether the key was absent or was a container.

