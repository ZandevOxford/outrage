# Outrage project structure

## Storing information

The store is for what would otherwise be lost between sessions: a decision and
the reasoning behind it, a finding that took real effort to get, where the work
got to.

Do not duplicate in bulk information which is available from the files or
the git history. However, do feel free to make notes on what was done and why.

Unless there is a good reason, documents should be small (up to 8k or so,
which is one `retrieve_document`) and cover a single topic.

Where possible, avoid significant edits to documents, and instead use the ?
path segment to add additional notes rather than appending more information
to a document.

## Where to store information

Suggested namespace for documents - where ? represents an auto-incremented path
segment. Create these as needed.

* `readme` - the top level document containing conventions used in the
  project. The conventions only: every session is told to read this before it
  starts, so it is what has to be true of the whole store, and routing to a
  particular document belongs in `contents` below.
* `contents` - an index routing to the other documents, for when there are
  more of them than the conventions can name. Route by *when* a document
  applies, since a survey by title already says what one is about.
* `current` - a brief document containing a summary of the current state and
  routes to other documents (in context, plans, issues etc.) for what has just
  been done and what is next.
* `context/?` - one thread of work: its task, its decisions, its state. Create
  a new context at this level for every significant piece of work. Create further
  documents below this (typically with ? autoincrement) to record work done
  and decisions made.
* `plans/<feature>` - plans for features to implement and decisions made.
  Also archived notes on already implemented features. Carry a `!status` so
  that a survey separates what is still open from what has been built.
* `issues/?` - Notes on bugs or other issues, with a `!status` likewise.
* `reference/<topic>` - durable facts about the project.
* `glossary/<term>` - definitions and notes on terms and keywords used in the
  project.
* `file_notes/<path>` - <path> will mirror the project filesystem, so use this
  to make notes about files in the project.
* `scratch/?` - scratch space for temporary notes. Also can be used for
  communication between simultaneous agents by using another level of
  auto-incremented documents. Agents can write new notes, and other agents
  can find them by looking for keys greater than the last they have previously
  read.
