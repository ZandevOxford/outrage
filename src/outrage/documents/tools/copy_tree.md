Copy a subtree to another key.

`target` is a prefix the copied keys are grafted beneath, so
`copy_tree('ref/python', 'archive')` writes
`archive/ref/python/...`; pass `reroot` to land them at `target` itself
instead, which is what moving a subtree to a new key means.

Documents cross with their metadata and their original timestamps, and may
cross between mounted stores.

This does not delete keys in `target`; it merges into whatever is already there,
and `on_conflict` decides one key at a time.

To move, copy and then delete_keys.

To split one document into two keys use `document_file` instead.

This copy is paged; pass `next_cursor` as `cursor` to continue.

`target` may not be at or below `source`.

With `reroot` the two subtrees must not overlap.
