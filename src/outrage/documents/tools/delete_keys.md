Delete a key and all metadata.

Non-metadata descendants are not deleted unless `recursive` is set.

Storing an empty document is not a delete.

`unchanged_since` refuses the whole delete, having removed nothing, when
anything it would take has been written since that time. It sees edits, not
what somebody else already deleted.

`dry_run` removes nothing and answers with the keys the delete would take, and
with the moment it looked as `checked_at` — pass that back as
`unchanged_since`, which is the pair `copy_tree` takes. The keys are the
delete's own selection rather than a second guess at it, so a preview of a
delete that would be refused is refused too.
