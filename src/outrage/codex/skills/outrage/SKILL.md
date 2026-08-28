---
name: outrage
description: Recover and preserve a project's working knowledge in its Outrage MCP document store. Use when resuming work, finding earlier decisions or task state, saving durable findings, or searching, annotating, or backfilling store documents.
---

# The Outrage store

Outrage keeps decisions, findings, and task state that would otherwise be lost
between sessions. It is reached through the `mcp__outrage__*` tools.

Read `readme` when it has not already arrived with the MCP server, then read
`project` when the store directs you there. Survey cheaply before reading:

```
get_documents(meta_name=["title"])
```

Listings are pages. Compare `returned` with `total`, follow `next_cursor` with
`after`, and account for `without_meta`; a title survey cannot show documents
without titles.

`outrage/` is Outrage's own manual, mounted read-only from inside the package:
a readme and documents on keys, the tools, the command line and the
conventions. Read it for how Outrage works, not for anything about this
project, and do not write there.

## Store conventions

Use `context/<n>/…` for a thread of work, `project/reference/<topic>` for
durable project facts, and `notes/<path>` for file-specific notes. Allocate a
new thread with `context/?/task`, then use the returned key for related state,
findings, and decisions. Give every document a `title`; add `!summary` when
the title cannot say enough to screen the document.

Store what cost something to learn: a decision and its reasoning, a verified
finding, a correction, or the current state and next step. Do not restate code
or a diff that the repository already records. Keep one question per document
and rewrite a state document rather than appending stale snapshots.

Use `?last` to address the newest item in a hierarchy. Before ending a task,
update its state and check that the documents you wrote have titles.

## Specialised operations

Read only the reference needed for the operation:

* To answer what the store contains about a question, read
  [references/search.md](references/search.md).
* To derive metadata for one document, read
  [references/annotate.md](references/annotate.md).
* To fill missing metadata across a subtree, read
  [references/backfill.md](references/backfill.md). It uses Codex runtime
  subagents for the independent annotation work.

