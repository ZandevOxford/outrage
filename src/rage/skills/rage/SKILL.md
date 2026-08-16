---
name: rage
description: Keep and recover working knowledge in this project's rage document store — notes, decisions, findings and task state that outlive one session. Use when starting or resuming work and the question is what earlier sessions established ("where were we", "what do we already know about X", "continue", "pick up where we left off"); when something worth keeping has just been settled (a decision and its reasoning, a finding that took effort to get, where the work got to); when asked to remember, store or save context; and before a session ends or its context is compacted.
---

# The rage store

A document store for this project, reached through the `rage` MCP tools. The
tools carry the key grammar and the argument rules; this skill covers when to
use them and what to name things.

## Survey before reading

One call shows everything the store holds:

```
get_documents(meta_name=["title"])
```

That returns a title per document, not the documents, so it is cheap enough to
run at the start of any piece of work. Then read only what looks relevant, with
`retrieve_document`.

Check `without_meta` in the result. It names documents in range carrying no
title, which the survey could not otherwise show — a survey that omits them
silently is a survey you cannot trust.

## Key conventions

Three top level namespaces. Nothing enforces them; they exist so that a later
session can guess where to look.

`context/<n>/…` — one numbered thread of work. Do not invent the number: store
at `context/?/task` first and the result reports the key it allocated, then put
everything else in that thread alongside it.

* `context/<n>/task` — what is being attempted, in a few lines.
* `context/<n>/state` — where it got to, what is unfinished, what to do next.
* `context/<n>/design`, `…/findings`, `…/decisions` — whatever the work
  produced that is worth keeping.

`project/reference/<topic>` — durable facts about the project itself, belonging
to no single thread: the environment, conventions, current status. Updated in
place as they change.

`notes/<path>` — notes about one file, keyed to mirror its path, as in
`notes/src/rage/store.py`.

Pass `title` on every document. It is what the survey above can see, and a
document without one is findable only by someone who already knows its key.

## What is worth storing

Store what cost something to learn and that nothing else in the project
records:

* a decision, and why the alternative was rejected
* a finding from actually running the thing — an error, a behaviour, a
  constraint in a dependency
* where the work got to, and what the next step is
* a correction: something believed at the start of the session and found false

Do not store what the repository already holds — what the code does, what the
diff changed, what the commit messages say. A note restating the code is a note
that will go stale and then mislead, and it costs a later session the read.

The test is whether someone could act on the document without the session that
wrote it.

## Store as the work goes, not at the end

Store each thing once it is settled. A session that plans to write everything up
at the end stores nothing if it is cut short, and a full context window is
exactly the ending that arrives without warning.

Rewrite the same key rather than accumulating new ones: `context/1/state` should
be the current state, not the first of several. Storing overwrites, which is
what makes this cheap.

Keep `project/reference/…` current when the facts under it change. A stale
reference is worse than an absent one, because it is believed.

## Before the end

Whether the session is ending, being handed over, or about to be compacted:

* make sure `context/<n>/state` actually describes where things stand
* store anything settled that is still only in the conversation
* check the survey — anything under `without_meta` needs a title
