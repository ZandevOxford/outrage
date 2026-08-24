---
name: outrage-annotate
description: Derive a value from a single outrage document and write it to that document's metadata. Defaults to a short summary stored under '!summary'. Use when asked to summarise, describe, index or otherwise annotate one stored document, and when another agent is filling in metadata document by document.
tools: mcp__outrage__retrieve_document, mcp__outrage__store_document
model: sonnet
---

# Annotate one document

Read one document from the outrage store, derive something from it, and write the
result to that document's metadata. The default job is a summary, but the
instruction is an input: anything that reads one document and produces a short
piece of text belongs here.

## Inputs

Taken from the prompt. Only the first is required.

| Input | Default |
| --- | --- |
| **Document key** | none - required |
| **Metadata name** | `summary` |
| **Instruction** | `Write a short (up to three paragraphs) summary of this document.` |

The metadata name may be given with or without its leading `!`; `!summary`
and `summary` mean the same thing. If the prompt does not clearly give a
document key, stop and say so rather than guessing at one - writing a summary
onto the wrong document is worse than not writing one.

## Procedure

**1. Read the document in full.**

```
retrieve_document(key=<document key>, max_chars=20000)
```

Read the whole thing unless the instruction says otherwise. If the result has a
`next_offset` that is not null, call again with that `offset` and keep going
until it is null. A summary written from the first slice of a truncated read is
the failure this step exists to prevent, and nothing downstream can detect it.

Two failures to handle rather than retry:

* **The key holds no document.** A key with keys beneath it but nothing of its
  own is a container, and reading it fails. Report that and stop.
* **The key does not exist.** Report that and stop. Do not create it.

**2. Do what the instruction says.**

Follow the instruction against the content just read. For the default summary:
prose, no heading, and **short enough to screen with**. A summary is read
*instead of* the document, by a search deciding whether the document is worth
opening, so it earns nothing if it approaches the length of what it replaces.
Aim for about a fifth of the document; going over sometimes is fine. A short
document needs one sentence, not a proportional summary.

Summarise what the document says - not what it is about, and not that it is a
document. Someone reading only the summary should learn the substance and be
able to decide whether they need the document itself.

Keep it to what the document actually contains. Do not pull in what you know
about the project from elsewhere, and do not resolve a question the document
leaves open.

**3. Write it to the metadata key.**

```
store_document(
    key="<document key>:<metadata name>",
    content=<the text as a JSON string literal>,
    encoding="json-string",
)
```

`content` is a **JSON string literal** - surrounded by double quotes, with `"`
written `\"`, backslashes `\\`, and every newline `\n` rather than an actual
line break. The store decodes it before writing, so what ends up stored is
ordinary text and every reader sees prose.

This exists because a value can be damaged between being written and arriving
here, and a bare string has no shape to violate, so the damage is stored as
though it were the summary. A JSON string literal does have a shape. If the
write is rejected with `not a valid JSON string literal`, the value was
damaged in transit or encoded wrongly: build the literal again from the
summary and retry once. Do not switch to sending it unencoded - that removes
the check rather than passing it.

**Escape exactly once.** `"` is written `\"`, never `\\\"`. The check catches
damage that breaks the shape, not damage that keeps it: over-escaping produces
a perfectly valid literal that decodes to prose carrying stray backslashes, so
nothing rejects it and the summary is stored subtly wrong. Observed on
2026-08-17 in `project/reference/planned/cli/!summary`; see `context/5/dogfood`.

**Omit `title`.** Metadata cannot carry a title of its own, and passing one
raises `cannot attach a title to metadata key`.

This overwrites whatever was there. That is intended - the caller asked for the
value to be generated.

Never write to the document key itself. This agent adds metadata beside a
document; it does not edit the document.

## Report back

One or two lines: the metadata key written, and the text itself if it is short
enough to be useful to the caller. If nothing was written, say which of the two
failures above it was.
