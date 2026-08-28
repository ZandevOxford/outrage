# What is worth storing, and where

The store is for what would otherwise be lost between sessions: a decision and
the reasoning behind it, a finding that took real effort to get, where the work
got to. Not what the repository already records - the code, the git history, a
fix that is visible in the diff.

Three shapes cover most of it:

* `context/<n>/…` - one thread of work: its task, its decisions, its state.
* `project/reference/<topic>` - durable facts about the project.
* `notes/<path>` - a note mirroring a file in the tree.

**One document, one facet, one read.** When a document stops being either, split
it and leave a line in whatever routes to it. Store under a descriptive key and
pass a `title`, so a later session can survey by title before reading anything
in full.

*Placeholder: these are the conventions the outrage project follows for its own
store. Whether they are the recommended default for every project is still to be
settled.*
