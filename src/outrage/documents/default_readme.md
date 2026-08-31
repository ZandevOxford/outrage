# Outrage project structure

This store keeps decisions, findings and task state that would otherwise be
lost between sessions. Do not duplicate in bulk what the files or git history
already say; do record what was done and why.

For more guidance, read `outrage/workflow`.

## Working with the store

Survey before reading with `get_documents(meta_name=["title"])`, then read
only what looks relevant. Surveys are paged: compare `returned` with `total`,
follow `next_cursor` with `after`, and account for `without_meta`, whose
documents cannot appear in a title survey.

Give every document a title. Add a `!summary` when the title alone cannot say
enough to decide whether the document is worth reading.

Store durable knowledge as the work goes on, once it is settled, rather than
saving it all for the end. Keep current documents current instead of appending
stale snapshots. Before a session ends, is handed over or may be compacted,
record anything still held only in the conversation, update the thread's
state, and check that new documents have titles.

Keep one facet per document and about 8k characters or less, so it can be read
in one `read_document` call. Add a numbered subdocument for further detail
instead of making one document answer several questions.

## Where to store information

Suggested namespace for documents where `?` represents an auto-incremented
path segment. Create these as needed.

* `current`: a brief summary of the current state, routing to what has just
  been done and what is next.
* `readme`: the conventions used throughout this project. Every session is
  told to read it first, so routing to particular subject matter belongs in
  `contents` instead.
* `contents`: an index routing to the other documents, for when there are more
  than the conventions can name. Route by *when* a document applies, since a
  title survey already says what one is about.
* `context/?/task`: allocate one numbered thread for each significant piece
  of work, then use the returned number for its related documents:
  `context/<n>/state` for where it got to and what comes next, and documents
  such as `decisions`, `findings` or numbered notes for what it produced.
* `plans/<feature>`: plans for features and retained reasoning about features
  already built. Carry a `!status` so a survey separates open from completed.
* `issues/?`: bugs or other issues, with a `!status` likewise.
* `reference/<topic>`: durable project facts: conventions and processes,
  history and releases, environment and implementation detail.
* `glossary/<term>`: project-specific terms and keywords.
* `file_notes/<path>`: notes about one file, mirroring the project tree.
* `scratch/?`: temporary notes and mailboxes between simultaneous agents.
