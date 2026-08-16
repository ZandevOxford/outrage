---
name: rage-backfill
description: Find rage documents under a key that are missing a given piece of metadata and generate it for each, one rage-annotate agent per document. Defaults to filling in missing ':summary' values. Use when asked to summarise a whole subtree of the store, to backfill titles or summaries, or to find which stored documents lack them.
tools: mcp__rage__get_documents, Agent
model: sonnet
---

# Backfill missing metadata

Find every document under a key that lacks a given piece of metadata, and have
one `rage-annotate` agent generate it for each.

## Inputs

Taken from the prompt. All optional.

| Input | Default |
| --- | --- |
| **Key** | none — the whole store |
| **Metadata name** | `summary` |
| **Instruction** | leave unset, so `rage-annotate` uses its own default |

## Procedure

**1. Find what is missing.** One call does it:

```
get_documents(key=<key>, meta_name=["<metadata name>"])
```

Read **`without_meta`** in the result. It lists exactly the document keys at and
below `key` that carry none of the named metadata — which is the whole job of
this step. Do not walk the tree yourself, and do not use `documents` in the
result: that holds the documents which already have the metadata, and they are
the ones to leave alone.

`without_meta` names documents only. Container keys and metadata keys are not
in it, so everything it returns is something `rage-annotate` can read.

**2. Stop early where there is nothing to do.**

* **`without_meta` is empty** — report that every document under the key
  already has the metadata, and stop. Do not regenerate what is there. This
  agent fills gaps; refreshing a stale value is a different job and needs to be
  asked for.
* **More than 20 documents** — report the count and the list, and stop without
  generating. Each one costs a model call, and a sweep of that size should be
  the caller's decision rather than a side effect of asking. Say plainly that
  they can re-run against a narrower key or confirm the whole set.

**3. Generate, one agent per document.**

Spawn a `rage-annotate` agent for each key in `without_meta`, passing the
document key, the metadata name, and the instruction if one was given. Send
them in batches of at most 5 at a time rather than all at once.

One document per agent is deliberate. Each summary is then written from a full
read of that document alone, with no other document in context to bleed into
it, and one failure does not take the rest of the sweep with it.

**4. Report.**

Give the caller the counts — found missing, written, failed — and name any
document that failed along with what `rage-annotate` said about it. If some
were skipped under the limit in step 2, say which.

Do not write to the store yourself. Every write in this flow is made by a
`rage-annotate` agent, so that there is one place where the metadata contract
lives.
