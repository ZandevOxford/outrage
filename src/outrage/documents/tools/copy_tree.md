Copy a subtree to another key. `target` is a prefix the copied keys are grafted
beneath, so copy_tree('ref/python', 'archive') writes
`archive/ref/python/...`; pass `reroot` to land them at `target` itself
instead, which is what moving a subtree to a new key means. Documents cross
with their metadata and their original timestamps, and may cross between
mounted stores. **A copy never deletes**: it merges into whatever is already
there, and `on_conflict` decides one key at a time. To move, copy and then
delete_keys; to split one document into two keys, use document_file rather than
this. The result is counts rather than a list of keys, since a copy may cross
more keys than a result can hold, with `next_cursor` when the limit stopped it
- call again with `cursor` set to that and everything else unchanged. `target`
may not be at or below `source`, and with `reroot` the two subtrees must be
wholly separate, because the copy walks the source as it writes rather than
snapshotting it.
