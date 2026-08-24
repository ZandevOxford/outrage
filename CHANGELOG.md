# Changelog

Notable changes to `outrage`. This project follows [semantic versioning](https://semver.org).

## 0.2.0 — unreleased

**Breaking.** Everything still called `rage` is now `outrage`, and one on-disk
format changed with it. The rename was finished in one go, deliberately, while
the installed base is still small.

### Parquet stores written by 0.1.x no longer open

The key the format version is recorded under changed:

    rage.format-version  ->  outrage.format-version

A parquet store written by any earlier release now fails to open, reporting
`parquet-not-a-store` — which reads as though the file is not a store at all.
**There is no migration and none is planned.** Rebuild affected files with
`outrage pack` from the corpus they were packed from.

### The MCP server is named `outrage`, so every tool is renamed

`mcp__rage__*` tools are now `mcp__outrage__*`. Anything naming the old tools —
saved permissions, prompts, your own agent and skill files — needs updating.

**This one needs a manual step.** `outrage config` and `outrage init` write the
new `outrage` entry but cannot recognise the old `rage` one, so `.mcp.json`
ends up holding both. Delete the `rage` entry by hand: the `rage-server`
command it names no longer exists, so a client left with it will report a
server that fails to start.

### Environment variables

`RAGE_DIR` → `OUTRAGE_DIR`, `RAGE_LOG` → `OUTRAGE_LOG`.

**This changes behaviour silently.** An unset variable is a default, not an
error, so a shell profile still exporting the old names is ignored rather than
refused — the store directory quietly becomes `./.outrage` again.

`RAGE_TEST_INSTALLED` → `OUTRAGE_TEST_INSTALLED` (test suite only).

### Public API

`RageError` → `OutrageError`. It is the base of every error this package
raises, so `except RageError` stops compiling against 0.2.0.

### Skill and agents

The packaged skill `rage` is now `outrage`, and the three agents
`rage-annotate`, `rage-backfill` and `rage-search` are `outrage-*`.
`outrage init` installs the new names; the files under the old names are left
where they are and can be deleted.

### Fixed

* **`outrage init` no longer appends a second `SessionStart` hook** when it
  meets one written by an earlier release under a different product name. The
  marker is matched on its stable part, so an entry written by 0.1.x is
  recognised and replaced rather than duplicated, and duplicates left behind by
  an upgrade that already ran are collapsed. This is why the session hook is
  the one item above that needs no manual step.

## 0.1.2 — 2026-08-23

* `?last` names the newest key, on every tool that takes a key, and `?` is
  reserved as a segment prefix.
* The session-start hook points at the `readme` instead of prescribing a survey.
* A session-start hook for Copilot CLI, and `init` no longer discards
  configured mounts.
* Packaging is tested: the built sdist and wheel are checked for every packaged
  data file, and the version has a single source.

## 0.1.1 — 2026-08-22

* Fixed: the 0.1.0 wheel was missing `outrage/skills/`, so `outrage init`
  aborted on a clean install without writing anything.

## 0.1.0 — 2026-08-22

First release. 0.1.0 remains installable and its `init` is broken; use 0.1.1 or
later.
