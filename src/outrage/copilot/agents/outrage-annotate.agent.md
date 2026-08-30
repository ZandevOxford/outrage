---
name: outrage-annotate
description: Derive a value from a single outrage document and write it to that document's metadata. Defaults to a short summary stored under '!summary'. Use when asked to summarise, describe, index or otherwise annotate one stored document, and when another agent is filling in metadata document by document.
tools:
  - outrage-read_document
  - outrage-store_document
---

Read `outrage/agents/annotate` in full and follow it. If that key cannot be
read, stop and report the failure; do not write metadata from this description.
