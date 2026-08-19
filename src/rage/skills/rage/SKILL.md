---
name: rage
description: Keep and recover working knowledge in this project's rage document store — notes, decisions, findings and task state that outlive one session. Use when starting or resuming work and the question is what earlier sessions established ("where were we", "what do we already know about X", "continue", "pick up where we left off"); when something worth keeping has just been settled (a decision and its reasoning, a finding that took effort to get, where the work got to); when asked to remember, store or save context; and before a session ends or its context is compacted.
---

# The rage store

A document store for this project, reached through the `rage` MCP tools. The
tools carry the key grammar and the argument rules; this skill covers when to
use them and what to name things.

## Survey before reading

One call shows what the store holds:

```
get_documents(meta_name=["title"])
```

That returns a title per document, not the documents, so it is cheap enough to
run at the start of any piece of work. Then read only what looks relevant, with
`retrieve_document`.

**Read `total`, not just what came back.** The result is a page: `returned`
titles out of `total` documents, with `next_cursor` set when there are more.
Twenty of twenty-two is a listing and you have seen the store; twenty of four
thousand is a sample, and treating it as the store is how a session concludes
confidently from a fraction of it. To continue, pass `next_cursor` back as
`after`. To look at one part instead of everything, pass `key`.

Check `without_meta` too. It reports how many documents carry no title, with a
few of their keys — the ones the survey cannot show at all, since it can only
report documents that have one. A survey that omits them silently is a survey
you cannot trust. It is always present, and it covers exactly the stretch of
the store this page covers, so paging the survey walks the gaps alongside the
titles instead of repeating a subtree-wide total on every page.

It is a count, not a listing, and carries no cursor: `keys_missing_meta` is
what enumerates them, and `rage-backfill` fills them in.

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

Store a `:summary` as well for any document whose subject its title cannot
carry. `rage-search` screens on title *then* summary, so a document with a
title and no summary is judged on the title alone — and "Notes from the Tuesday
run" is an honest title that tells a reader nothing. Aim for about a fifth of
the document: a summary that approaches the length of its document costs as much
to screen as the document costs to read. `rage-backfill` fills these in across a subtree,
which is the right thing to run after adding several documents at once.

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

## One document, one question

Rewriting a key keeps it current; it is not licence to let it grow. When there
is more to keep, prefer **adding a document beneath it** to extending the one
that is there. Sub-documents are the intended shape, and `?` allocates a key at
any depth — `context/1/findings/?` writes the next document under `findings` —
so adding one costs no naming decision and no thought about where it goes.

A document should be readable in one call. `retrieve_document` returns 8000
characters by default, so a longer document is read in slices, and a session
that judges it from the first slice judges it wrongly and silently.

Size is the symptom; scope is the cause. `project/reference/planned` reached
11389 characters because it answered five questions at once — what CLI pieces
remain, what is open on the agents, what the log reader should do, how the
checkpoint prompt gets delivered, which files are stale. No title and no
summary can route a reader to the right part of a document like that, so it is
read whole or not at all.

Split along the questions, not by length. A key can hold content *and* have
keys beneath it, so the general document stays where it is and the detail goes
below: `project/reference/planned` is now a short index over `planned/cli`,
`planned/agents`, `planned/log-reader` and the rest. Anything already pointing
at the old key still lands somewhere useful, which is what makes a split safe
to do late — but adding as you go is cheaper than splitting afterwards.

## Before the end

Whether the session is ending, being handed over, or about to be compacted:

* make sure `context/<n>/state` actually describes where things stand
* store anything settled that is still only in the conversation
* check the survey — anything under `without_meta` needs a title
