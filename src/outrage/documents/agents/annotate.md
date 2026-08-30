# Annotate one document

Derive one metadata value from one document. Inputs are a required document
key, a metadata name defaulting to `summary`, and an instruction defaulting to
a short summary of up to three paragraphs. Accept the metadata name with or
without its leading `!`. If the key is unclear, stop rather than guessing.

## Procedure

1. Read the document with
   `read_document(key=<document key>, max_chars=20000)` and follow
   `next_offset` until it is null. If the key is absent or is only a container,
   report that and stop; do not create it.

2. Follow the requested instruction using only the document's content. A
   default summary is prose without a heading, normally no more than a fifth
   of the source. State the substance rather than saying what the document is
   about. Do not add outside knowledge or resolve questions it leaves open.

3. Write the result to `<document key>/!<metadata name>` with
   `encoding="json-string"`. The `content` argument must be one valid JSON
   string literal: quote it, escape quotes and backslashes once, and represent
   newlines as `\n`. If validation rejects the literal, rebuild it and retry
   once; do not fall back to unencoded content.

   Omit `title`, because metadata cannot carry metadata of its own. Never
   write to the document key itself. Overwriting the requested metadata value
   is intended.

## Report

Give the metadata key written and, when useful, the short value. If nothing was
written, say whether the document was absent or the key was a container.
