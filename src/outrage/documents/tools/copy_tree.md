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

To split one document into two keys use `document_edit` instead.

This copy is paged; pass `next_cursor` as `cursor` to continue.

`unchanged_since` says when you looked, and a dry run reports the moment to
pass back as `checked_at`. Nothing is written at all if anything under the keys
this would land on has changed since then; with
`on_conflict='overwrite-unchanged'` a key that changes after that check is left
as it is and named in `changed`. It sees edits, not deletions.

Resuming a paged copy takes a **fresh** moment rather than the one the first
call used: a copy carries the source's timestamps, so a page already written is
itself a change to `target` whenever the source is newer than the watermark. A
dry run from the cursor you are resuming reports the moment to use.

`target` may not be at or below `source`.

With `reroot` the two subtrees must not overlap.
