List the keys immediately below a key, including subkeys and metadata.

Omit the key to list the top level. Keys of kind `implicit` hold no
content themselves but have something beneath them. A key of kind `mount`
is where another store is mounted, and `read-only mount` is one that refuses
writes.

Pages contain at most 100 keys. Pass `next_cursor` as `after` for the next
slice.
