# Backfill missing metadata

Use this operation to fill a missing metadata value, defaulting to `!summary`,
under a key or across the whole store.

1. Call `keys_missing_meta(key=..., meta_name=["<metadata name>"])`. Do not
   walk the tree or survey documents that already have the value.
2. If `total` is zero, report that there is nothing to do. If it exceeds 20,
   report the count and sample keys, then stop: a sweep of that size needs
   explicit confirmation or a narrower key.
3. Page through every returned key before work begins. For each key, spawn a
   bounded Codex subagent, in batches of at most five, with this task: read the
   document in full; derive the requested metadata using the supplied
   instruction (or the default short summary); write it only to
   `<key>/!<metadata name>` using `encoding="json-string"`; omit `title`; and
   report success or failure. One document per subagent prevents content from
   one document affecting another and lets failures remain isolated.
4. Report counts for missing, written, and failed documents, including the key
   and reason for every failure.

The coordinating agent does not write document metadata itself. This keeps the
write contract in the annotation task.

