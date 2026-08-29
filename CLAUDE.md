# Outrage

This project keeps its working knowledge - decisions, findings, and where the
work got to - in its own outrage document store, reached through the `outrage` MCP
tools. That store is the record. **This file is only a pointer to it**, so that
nothing here can go stale against what the store says.

## Start here

Read the document at key `readme`, then `current`. `readme` holds the
conventions and the namespaces; `current` is where the work has got to and what
is next. `contents` is the index behind them, routing by *when* a document
applies: a survey by title (`get_documents(meta_name=["title"])`) tells you
what documents are about, and `contents` tells you which one you need before
you know to look.

## Before snapshotting the store

Read `reference/snapshots` first. Copying `.outrage/store.sqlite` with `cp`
succeeds and produces a **silently stale** store, potentially a whole schema
version behind. Use `outrage backup`.

## Conventions

The `outrage` skill (`.claude/skills/outrage/SKILL.md`) holds the key conventions and
what is worth storing. The tools themselves carry the key grammar and the
argument rules.
