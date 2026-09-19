# Outrage project structure

This store is a durable memory for decisions, findings and task state
across sessions.

Documents in `outrage/` are the documentation for Outrage itself.
You can read `outrage/workflow` for more advice on using the store,
and `outrage/agents` contains the default agent/skill definitions.

## Working with the store

Survey before reading with `get_documents(meta_name=["title"])`, then read
only what looks relevant. Surveys are paged: compare `returned` with `total`,
follow `next_cursor` with `after`, and account for `without_meta`, whose
documents cannot appear in a title survey.

Give every document a title. Add a `!summary` when the title alone cannot say
enough to decide whether the document is worth reading.

When linking to other documents, avoid recording the state of the target,
as this can easily get out of date.

Store durable knowledge especially user decisions immediately as they are
settled to avoid losing information if the session is interrupted.
If you do know a session is about to end or be compacted, make sure you
have recorded anything only held in the conversation; update the current
context and check new documents have metadata.

Usually keep to one facet per document and about 8k characters or less, so it
can be read in one `read_document` call. Add a numbered subdocument for
further detail instead of making one document answer several questions.
However, particularly for reference documents, they can be longer if that
makes sense as long as they have `!contents` metadata.

Documents that are read often, particularly status and routing documents,
should be as terse as possible.

Do not duplicate in bulk what the files or git history already say, but
record what was done and why.

**A document is not finished until there is a route to it**, though the
conventions may be enough, for example for issues. The conventions
live in `readme`; subject matter is linked from `contents`.

## Where to store information

Suggested namespace for documents where `?` represents an auto-incremented
path segment. Create these as needed.

* `current`: a brief summary of the current state, routing to what has just
  been done and what may be next. This should be kept short, with just
  routing and very brief notes on important open items.
* `readme`: the conventions used throughout this project. Every session is
  told to read it first, so routing to particular subject matter belongs in
  `contents` instead. This should mostly be a static document.
* `contents`: an index routing to the other documents, for when there are more
  than the conventions can name. Route by *when* a document applies, since a
  title survey already says what one is about. Use sub-documents where needed
  to keep this a reasonable size.
* `context/?/task`: allocate one numbered thread for each significant piece
  of work, then use the returned number for its related documents:
  `context/<n>/state` for where it got to and what comes next, and documents
  such as `decisions`, `findings` or numbered notes for what it produced.
* `plans/<feature>`: plans for features and retained reasoning about features
  already built. Carry a `!status` so a survey separates open from completed.
  Important open plans should have routing, but it's not essential for all
  plans.
* `issues/?`: bugs or other issues, with a `!status` likewise. Typically
  issues can be searched and don't need routing, but note in `current` if
  relevant.
* `reference/<topic>`: durable project facts: conventions and processes,
  history and releases, environment and implementation detail. Reference
  documents do not need routing, but can be referenced where relevant.
* `glossary/<term>`: project-specific terms and keywords. Glossary documents
  do not need routing, but can be referenced where relevant.
* `file_notes/<path>`: notes about one file, mirroring the project tree.
  File notes do not need routing, as they can be found by name.
* `scratch/?`: temporary notes and mailboxes between simultaneous agents.
  Scratch documents do not need routing.
* `agents/`: agents and skills specific to this project.
