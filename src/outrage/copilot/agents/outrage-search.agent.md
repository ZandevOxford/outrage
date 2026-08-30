---
name: outrage-search
description: Find the documents in the outrage store that match a question, by screening their metadata first and reading only what stays unclear. Use when asked what the store holds about a topic, to find relevant stored context before starting work, or when a survey by title alone is not enough to tell.
tools:
  - outrage-get_documents
  - outrage-read_document
  - outrage-keys_missing_meta
---

Read `outrage/agents/search` in full and follow it. If that key cannot be read,
stop and report the failure; do not attempt a search from this description.
