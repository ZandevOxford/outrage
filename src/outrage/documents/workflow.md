# Tips on using Outrage

This contains tips on standard workflows, but a project's own `readme` may
define other conventions.

## Survey before reading

When looking for information, start with `get_documents`,
`meta_name=["title"]` and an appropriate `key`. This can find candidate
documents and let you decide whether `read_document` is needed.

The result is paged. If `next_cursor` is returned, there are more results,
so pass that as `after` to the next call. A nonzero `without_meta` count means
the survey omitted documents that have no title. Use `keys_missing_meta` to
find them.

## Useful metadata

* Most documents should have a `title`.
* Complex documents, particularly where the title is not enough to screen
  the document, should also have a `summary`, which should be a short (up to
  around two paragraphs) overview.
* Particularly if the project makes use of a glossary, complex documents
  should also have `keywords`: a list, one per line, of the topics the document
  covers.

## Keep the current context thread live

When starting a new task, create a context thread at `context/?/task`.
The result reports the number to use for everything related to it.

Keep `context/<n>/state` current as a very short document with what is complete,
what remains and the next useful action.

Put decisions, verified findings and corrections in their own documents
alongside it.

Store a result when it becomes settled. Waiting to write everything at the end
loses the very knowledge the store exists to preserve if a session is cut
short or compacted.

Rewrite a current state document instead of accumulating contradictory
snapshots, and update durable `reference/` documents when the facts they
describe change.

## One document, one facet

A document should normally fit in one `read_document` call (8k characters) but
scope matters more than the exact length.

If one document answers several questions, you can split those questions into
subdocuments and leave the parent as a short route to them. A key can hold a
document and have keys beneath it, and `?` can allocate numbered children such
as `context/12/findings/?`.

## Editing files

When changing a substantial document, prefer `document_file`: call it with the
key and no path to export the whole document, edit the returned file with
ordinary file tools, then call it with the key and returned path to import.
The import reports the old and new sizes, making accidental truncation visible,
and unchanged text need not pass through the conversation twice.

To split a document, export it, place one facet at a new child key, and import
the shortened parent. Use `copy_tree` for whole subtrees, not for splitting
one document; a move is a successful copy followed by an explicit delete.

## Deleting allocated keys

Numbers allocated by `?` are unique among the siblings that currently exist;
they are not permanently reserved. Deleting the highest numbered sibling lets
the next allocation reuse that number. If readers use the last key seen as a
high-water mark, as a scratch mailbox may, treat the sequence as append-only:
correct or retract with a new document rather than deleting the newest one or
its containing numbered subtree.

## Before handoff or compaction

Most harnesses give no good way to catch session end or compaction, so
try to keep the store up to date as you go.

However, if the user indicates the session may end, the checklist is:

* update the context thread's `state` with what actually remains and the next
  step;
* store settled knowledge that still exists only in the conversation;
* update any durable reference made stale by the work;
* check that every new document has a useful title, and add a summary where
  the title is not enough to screen it.
