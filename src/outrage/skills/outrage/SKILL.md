---
name: outrage
description: Keep and recover working knowledge in this project's outrage document store - notes, decisions, findings and task state that outlive one session. Use when starting or resuming work and the question is what earlier sessions established ("where were we", "what do we already know about X", "continue", "pick up where we left off"); when something worth keeping has just been settled (a decision and its reasoning, a finding that took effort to get, where the work got to); when asked to remember, store or save context; and before a session ends or its context is compacted.
---

# The outrage store

A document store for this project, reached through the `outrage` MCP tools. The
tools carry the key grammar and the argument rules; this skill covers when to
use them and what to name things.

## Start at `readme`

Every store's entry point is the document at `readme`: what this particular
store holds, and what to read before anything else. The server carries it at
the top of its instructions, so it arrives without being asked for and there is
normally nothing to do here. If it did not arrive, read it.

Three things follow from that. A readme long enough to be worth summarising is
too long - it routes, and the documents it points at explain. It has a hard cap
of a few hundred characters, because a client cuts the instructions at a length
it does not announce and the readme is what has to survive that cut; over the
cap the server reports its length instead of carrying it, which is the signal
to go and read it. And a store with no readme is asking for one: a session that
works out how the store is laid out, or what the next session should read
first, should write that there.

It is read once, when the server starts, so a readme stored now reaches the
next session rather than this one.

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
few of their keys - the ones the survey cannot show at all, since it can only
report documents that have one. A survey that omits them silently is a survey
you cannot trust. It is always present, and it covers exactly the stretch of
the store this page covers, so paging the survey walks the gaps alongside the
titles instead of repeating a subtree-wide total on every page.

It is a count, not a listing, and carries no cursor: `keys_missing_meta` is
what enumerates them, and `outrage-backfill` fills them in.

## Key conventions

Three top level namespaces. Nothing enforces them; they exist so that a later
session can guess where to look.

`context/<n>/…` - one numbered thread of work. Do not invent the number: store
at `context/?/task` first and the result reports the key it allocated, then put
everything else in that thread alongside it.

To read the newest thread without looking its number up, put `?last` in place
of the segment: `context/?last/state`. It names whatever sorts last at that
point, works on any key a tool takes, and the result reports which key it
resolved to. It is refused when there is nothing below that point rather than
answering about the level above.

* `context/<n>/task` - what is being attempted, in a few lines.
* `context/<n>/state` - where it got to, what is unfinished, what to do next.
* `context/<n>/design`, `…/findings`, `…/decisions` - whatever the work
  produced that is worth keeping.

`project/reference/<topic>` - durable facts about the project itself, belonging
to no single thread: the environment, conventions, current status. Updated in
place as they change.

`notes/<path>` - notes about one file, keyed to mirror its path, as in
`notes/src/outrage/store.py`.

Pass `title` on every document. It is what the survey above can see, and a
document without one is findable only by someone who already knows its key.

Store a `!summary` as well for any document whose subject its title cannot
carry. `outrage-search` screens on title *then* summary, so a document with a
title and no summary is judged on the title alone - and "Notes from the Tuesday
run" is an honest title that tells a reader nothing. Aim for about a fifth of
the document: a summary that approaches the length of its document costs as much
to screen as the document costs to read. `outrage-backfill` fills these in across a subtree,
which is the right thing to run after adding several documents at once.

## What is worth storing

Store what cost something to learn and that nothing else in the project
records:

* a decision, and why the alternative was rejected
* a finding from actually running the thing - an error, a behaviour, a
  constraint in a dependency
* where the work got to, and what the next step is
* a correction: something believed at the start of the session and found false

Do not store what the repository already holds - what the code does, what the
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
any depth - `context/1/findings/?` writes the next document under `findings` -
so adding one costs no naming decision and no thought about where it goes.

A document should be readable in one call. `retrieve_document` returns 8000
characters by default, so a longer document is read in slices, and a session
that judges it from the first slice judges it wrongly and silently.

Size is the symptom; scope is the cause. `project/reference/planned` reached
11389 characters because it answered five questions at once - what CLI pieces
remain, what is open on the agents, what the log reader should do, how the
checkpoint prompt gets delivered, which files are stale. No title and no
summary can route a reader to the right part of a document like that, so it is
read whole or not at all.

Split along the questions, not by length. A key can hold content *and* have
keys beneath it, so the general document stays where it is and the detail goes
below: `project/reference/planned` is now a short index over `planned/cli`,
`planned/agents`, `planned/log-reader` and the rest. Anything already pointing
at the old key still lands somewhere useful, which is what makes a split safe
to do late - but adding as you go is cheaper than splitting afterwards.

## Editing a long document without reading it twice

A document too long to hold comfortably in context does not have to pass
through the conversation to be changed. `document_file` puts it on disk and
takes it back:

```
document_file(key="context/1/state")        -> writes a file, returns its path
document_file(key="context/1/state", path=...) -> stores that file back
```

Between the two, edit the file with the ordinary shell tools - `sed`, a
heredoc, an editor. The direction is decided by `path` and nothing else. Give
the import the path the export handed back; a relative one is taken from the
export directory, not from where you are standing.

Two things worth knowing. The import stores at the key you name, whatever file
the content came from, so exporting one key and importing to another is how to
copy content across the store. And the answer reports the size written beside
the size that was there before: an edit script that truncated a document shows
up as a shrink, which is the only warning there is - nothing refuses a write
that empties a key.

The tool is offered when the server was told which directory it serves from.
Where it is not there, `outrage get > file`, edit, `outrage set --file` does the
same thing from the shell - chained with `&&`, and check the length before
writing back.

## Before the end

Whether the session is ending, being handed over, or about to be compacted:

* make sure `context/<n>/state` actually describes where things stand
* store anything settled that is still only in the conversation
* check the survey - anything under `without_meta` needs a title
