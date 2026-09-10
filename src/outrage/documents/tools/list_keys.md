List the keys immediately below a key, including subkeys and metadata.

Omit the key to list the top level. Keys of kind `implicit` hold no
content themselves but have something beneath them. A key of kind `mount`
is where another store is mounted, and `read-only mount` is one that refuses
writes.

`descendant_counts` reports how many keys and how many documents lie below
each listed key, which is how a level says which of its children is worth
descending into. `descendant_chars` reports how much text is down there.
Both are off by default because both read the subtree, where the listing
itself does not: ask for them when choosing where to go, not on every call.
A key with a metadata segment anywhere above it counts as metadata, so
`descendant_documents` never includes one. Both counts are of *stored* keys,
so a key of kind `implicit` is listed but is not counted below its own
parent - a level can show more children than the number beneath it.

Pages contain at most 100 keys. Pass `next_cursor` as `after` for the next
slice.
