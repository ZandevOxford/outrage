# Changelog

Notable changes to `outrage`. This project follows [semantic versioning](https://semver.org).

## 0.3.0 - unreleased

### A mount table is now a `Store`, and `Mounts` is renamed

`outrage.mounts.Mounts` is `outrage.mounts.MountedStore`, and it implements
`outrage.store.Store`. **Breaking** for anything importing the old name; there
is no alias. Nothing about the command line or the MCP tools changes.

It means the routing, the level merge and the subtree traversal that make
several stores answer as one namespace are no longer the MCP server's - so a
mount table can go in front of anything that speaks to a `Store`, and the same
contract tests cover it as cover SQLite.

A table has no file of its own, and says so rather than answering for its root
mount: `path`, `backup`, `check` and `repair` raise `mount-has-no-file`. A
check of one store out of three would be a clean bill of health for the two
nobody looked at.

### A directory of files is now a `Store`

`outrage.store_files.FilesystemStore` reads and writes a tree with one file per
key - the mapping `outrage export` has always written, expressed as a store. A
segment is a path component and an extension names the format, so `a/b` stored
as markdown is `a/b.md` and everything below `a/b` is in `a/b/`.

It passes the same contract tests as SQLite, and is compared against it
directly: one corpus in both, the same battery of reads put to each, every
answer asserted equal.

A tree has no extension for `--store` to read, so it is not addressed by file
name yet and is constructed at its path. Reads walk the tree per call, which is
the right shape for an export target and the wrong one for a large corpus; the
module says so where it costs.

Three divergences, each covered by a test that names it: `.` and `..` are legal
keys and impossible paths, so they are refused on write; a key whose path
leaves the tree is refused; and a file that does not hold UTF-8 text is
reported rather than mangled into a document.

### The root document can be exported, and comes back

**Breaking** for anything relying on `outrage export` refusing the document at
the root. It now writes it as the file named by its extension alone - `.md` at
the top of the tree - and an import reads it back, dotfile skip or not. Before
this, exporting a store that had a document at its root reported one failed
transfer and dropped it.

### A key can no longer be exported outside the directory it was given

An export resolves each path it is about to write and refuses one that has left
the target tree. A symlinked directory anywhere along the path was enough
before this - no unusual key required - and the per-segment `..` check could
not see it. The same guard covers the two Windows shapes a segment can take:
one holding a backslash, which re-parses into components, and one holding a
colon, which becomes a drive letter.

### Six fixes at a mount boundary

* **A key with a mount below it listed as an empty container.** A document with
  a mounted store somewhere beneath it came back from `list_keys` as `implicit`,
  with no size, format or timestamp, while `retrieve_document` returned its
  content. A mount *point* shadows what is under it; a mount below a key does
  not.
* **A count across a boundary was short by two rows per mount.** The mount point
  itself and its metadata were left out, so the `remaining` on a non-recursive
  `delete_keys` told you to pass `recursive` for fewer keys than were there.
* **A failure at the root printed `''` instead of `/`.** An error was named with
  the owning mount's own outward function, which for the root mount is the
  identity, so the empty string reached the reader where the root's name should
  have been.
* **The count in "N key(s) lie beneath it" stopped at the store's edge.** The
  store answering counted its own rows, so everything held by a mount below the
  key was missing from the number - live in this project's own store, a key with
  20,000 rows beneath it reported 536.
* **A key whose only content is a mount below it read as empty.** No store holds
  a row at `lib` when the mount is at `lib/deep`, so `retrieve_document('lib')`
  raised `key-not-found`, whose sentence is "nothing is stored at or below" and
  which was untrue. It is now `key-is-a-container`, with the advice that finds
  the mount.
* **`level_entry` returned `None` for a key its own listing offers.** The same
  key: `list_keys` splices `lib` into the level above, and asking what that
  entry is got nothing back.

## 0.2.0 - 2026-08-24

**Breaking.** Everything still called `rage` is now `outrage`, and one on-disk
format changed with it. The rename was finished in one go, deliberately, while
the installed base is still small.

### Parquet stores written by 0.1.x no longer open

The key the format version is recorded under changed:

    rage.format-version  ->  outrage.format-version

A parquet store written by any earlier release now fails to open, reporting
`parquet-not-a-store` - which reads as though the file is not a store at all.
**There is no migration and none is planned.** Rebuild affected files with
`outrage pack` from the corpus they were packed from.

### The MCP server is named `outrage`, so every tool is renamed

`mcp__rage__*` tools are now `mcp__outrage__*`. Anything naming the old tools -
saved permissions, prompts, your own agent and skill files - needs updating.

**This one needs a manual step.** `outrage config` and `outrage init` write the
new `outrage` entry but cannot recognise the old `rage` one, so `.mcp.json`
ends up holding both. Delete the `rage` entry by hand: the `rage-server`
command it names no longer exists, so a client left with it will report a
server that fails to start.

### Environment variables

`RAGE_DIR` → `OUTRAGE_DIR`, `RAGE_LOG` → `OUTRAGE_LOG`.

**This changes behaviour silently.** An unset variable is a default, not an
error, so a shell profile still exporting the old names is ignored rather than
refused - the store directory quietly becomes `./.outrage` again.

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

## 0.1.2 - 2026-08-23

* `?last` names the newest key, on every tool that takes a key, and `?` is
  reserved as a segment prefix.
* The session-start hook points at the `readme` instead of prescribing a survey.
* A session-start hook for Copilot CLI, and `init` no longer discards
  configured mounts.
* Packaging is tested: the built sdist and wheel are checked for every packaged
  data file, and the version has a single source.

## 0.1.1 - 2026-08-22

* Fixed: the 0.1.0 wheel was missing `outrage/skills/`, so `outrage init`
  aborted on a clean install without writing anything.

## 0.1.0 - 2026-08-22

First release. 0.1.0 remains installable and its `init` is broken; use 0.1.1 or
later.
