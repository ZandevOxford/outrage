# Outrage

This project keeps its working knowledge - decisions, findings, and where the
work got to - in its own rage document store, reached through the `rage` MCP
tools. That store is the record. **This file is only a pointer to it**, so that
nothing here can go stale against what the store says.

## Start here

Read the document at key `project`. It is an index of what to read and *when it
applies*, and it routes to everything else. A survey by title
(`get_documents(meta_name=["title"])`) tells you what documents are about; the
`project` document tells you which one you need before you know to look.

## Before snapshotting the store

Read `project/reference/snapshots` first. Copying `.outrage/store.sqlite` with `cp`
succeeds and produces a **silently stale** store, potentially a whole schema
version behind. Use `outrage backup`.

## Conventions

The `rage` skill (`.claude/skills/rage/SKILL.md`) holds the key conventions and
what is worth storing. The tools themselves carry the key grammar and the
argument rules.
