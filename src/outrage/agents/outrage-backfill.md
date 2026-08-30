---
name: outrage-backfill
description: Find outrage documents under a key that are missing a given piece of metadata and generate it for each, one outrage-annotate agent per document. Defaults to filling in missing '!summary' values. Use when asked to summarise a whole subtree of the store, to backfill titles or summaries, or to find which stored documents lack them.
tools: mcp__outrage__keys_missing_meta, mcp__outrage__read_document, Agent
model: sonnet
---

Read `outrage/agents/backfill` in full and follow it. If that key cannot be
read, stop and report the failure; do not start or delegate a backfill from
this description.
