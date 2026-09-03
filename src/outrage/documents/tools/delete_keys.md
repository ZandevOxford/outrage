Delete a key and all metadata.

Non-metadata descendants are not deleted unless `recursive` is set.

Storing an empty document is not a delete.

`unchanged_since` refuses the whole delete, having removed nothing, when
anything it would take has been written since that time. It sees edits, not
what somebody else already deleted.
