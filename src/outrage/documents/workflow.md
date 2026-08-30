# Working with a project store

This is the longer working practice behind the concise conventions suggested
in `outrage/default_readme`. A project's own `readme` decides which of these
conventions it adopts.

## Survey before reading

Start with `get_documents(meta_name=["title"])`. It returns metadata rather
than full documents, so use it to decide what deserves a `read_document` call.

Treat the result as a page. Compare `returned` with `total` and pass
`next_cursor` back as `after` until the relevant range is covered. Check
`without_meta` as well: those documents have no title and therefore cannot
appear in the survey. Use `keys_missing_meta` when their keys need enumerating.

Titles should distinguish documents in a survey. Add `!summary` when a short
title cannot also carry enough of the conclusion to screen the document.

## Keep a thread live

Allocate a thread by storing its task at `context/?/task`; the result reports
the number to use for everything related to it. Keep `context/<n>/state`
current with what is complete, what remains and the next useful action. Put
decisions, verified findings and corrections in their own documents alongside
it.

Store a result when it becomes settled. Waiting to write everything at the end
loses the very knowledge the store exists to preserve if a session is cut
short or compacted. Rewrite a current state document instead of accumulating
contradictory snapshots, and update durable `reference/` documents when the
facts they describe change.

## One document, one facet

A document should normally fit in one `read_document` call — about 8k
characters — but scope matters more than the exact length. If one document
answers several questions, split those questions into subdocuments and leave
the parent as a short route to them. A key can hold a document and have keys
beneath it, and `?` can allocate numbered children such as
`context/12/findings/?`.

When changing a substantial document, prefer `document_file`: call it with the
key and no path to export the whole document, edit the returned file with
ordinary file tools, then call it with the key and returned path to import.
The import reports the old and new sizes, making accidental truncation visible,
and unchanged text need not pass through the conversation twice.

To split a document, export it, place one facet at a new child key, and import
the shortened parent. Use `copy_tree` for whole subtrees, not for splitting
one document; a move is a successful copy followed by an explicit delete.

## Before handoff or compaction

Before the session ends, is handed over or may be compacted:

* update the thread's `state` with what actually remains and the next step;
* store settled knowledge that still exists only in the conversation;
* update any durable reference made stale by the work;
* check that every new document has a useful title, and add a summary where
  the title is not enough to screen it.
