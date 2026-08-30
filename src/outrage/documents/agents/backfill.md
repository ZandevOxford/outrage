# Backfill missing metadata

Find every document under a key that lacks one metadata value and coordinate
one annotation task per document. Inputs are an optional subtree key, a
metadata name defaulting to `summary`, and an optional annotation instruction.

## Procedure

1. Call `keys_missing_meta(key=<key>, meta_name=["<metadata name>"])`. Do
   not walk the tree or survey documents that already have the value. Follow
   pagination only after the count is accepted below.

2. If `total` is zero, report that there is nothing to do. If it exceeds 20,
   report the count and sample keys, then stop without generating or paging:
   that many model calls require explicit confirmation or a narrower key.

3. When the count is accepted, follow every `next_cursor` with `after` before
   starting work. Delegate one bounded annotation task per document, in
   batches of at most five. Each worker must first read
   `outrage/agents/annotate` in full and stop visibly if it cannot; then it
   follows that procedure with the document key, metadata name and supplied
   instruction. A harness with a named `outrage-annotate` agent may delegate
   to it; a harness with general subagents gives them that same task.

   One document per worker prevents content bleeding between annotations and
   isolates failures. The coordinator never writes metadata itself.

4. Report counts for missing, written and failed documents. Name every failed
   key and its reason.
