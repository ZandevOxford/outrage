# Changelog

Notable changes to `outrage`. This project follows [semantic versioning](https://semver.org).

## 0.3.0 - unreleased

### A mount table in a file, and a command line that reads it

`mounts.toml` in the store directory describes the mounts, so a table is
maintained in one commented place rather than respelled on every command line -
and, for the server, rather than living inside a client's `.mcp.json` in an
array whose quoting belongs to argparse. It holds `root-mount`, a `[mount]`
table and a `[mount-ro]` table, each entry a `KEY = "FILE"` naming a store
inside `--dir`. TOML because a config file is the one place comments are
wanted, and `tomllib` is in the standard library.

**A file behaves as if its options had been typed at the point where it is
named.** The default file is spelled at the very front, so everything actually
typed comes after it and wins; `--mount-config FILE` splices another in where
the flag appears. There is no separate notion of a merge: precedence and
repetition are whatever argparse already does. The one deliberate exception is
duplicates - a mount point claimed twice within one source is still refused,
while claimed again from a later source it *replaces* the earlier one, which is
what makes a committed table safe to override one entry of. `--no-mount-config`
ignores the default file for a run.

**`outrage get`, `set`, `ls`, `dump`, `rm`, `export` and `import` now take
`--mount`, `--mount-ro` and `--mount-config`**, and act across the whole table,
so the command line sees the namespace the MCP server serves rather than the
root store alone. `--store` is the root mount on those commands and
`--root-mount` is an accepted alias for it. `outrage check` and `outrage
backup` stay per-file by nature, and already say which file with `--store`.

A mount point that is metadata is now refused when the spec is parsed rather
than when the table is built, so a mistyped one no longer leaves a database
behind named after the mistake.

### `Store` and `FileStore`: a store, and a store kept in a file

**Breaking for library callers.** `Store` now says only what a store *does* -
the vocabulary of keys, ranges, subtrees and pages that any store answers in.
Everything that needs somewhere on disk to answer from moves to a new
`FileStore(Store)`: `directory`, `path`, `default_filename`, `format_version`,
`stored_format_version`, `backup`, `backup_path`, `audit_rows`, `check_file`,
`repair`, and the constructor that settles where a store's file is.
`SqliteStore`, `ParquetStore` and `FilesystemStore` are `FileStore`s;
`MountedStore` is a `Store` and not a `FileStore`.

`outrage.maintenance.check` and `repair`, and `store.default_store` and
`open_store`, are typed as `FileStore` accordingly.

**A mount table no longer refuses those eleven members - it does not have
them.** Asking one for a `path` or a `backup` used to raise a written
`mount-has-no-file` sentence, which was a class saying in eight declarations
what one line of its inheritance now says. `isinstance(store, FileStore)` is
how a caller asks, and a caller that asks anyway gets Python's own
`AttributeError`. Nothing on the command line reaches this: `outrage backup`
and `outrage check` already name the store they mean with `--store`, which is
the honest answer for a table spanning three files.

### Every store can back itself up

`FileStore.backup` is no longer abstract. The default opens a fresh store of
the same class at the destination and copies this one into it with
`copy_from`, then reopens the copy and compares **every key** against the
source - not a count of them, since a copy that lost one document and gained
another counts the same and is not a backup. `FileStore.verified_backup` is
that check on its own, and `FileStore.opened_at(path)` is the one thing a
generic copy cannot work out for itself: another store of this class, kept
there.

`SqliteStore` and `ParquetStore` override it as before, and must: the file
alone is not the store for the first, and a byte copy is faster and exact for
the second.

**What changes for a user: a backup of a directory of files is now a copy of
its documents, not of its directory.** It was `shutil.copytree` until now. A
symbolic link, a file that is not UTF-8 text, a name that no key spells, and
the second of two files claiming one key are not documents - every read of that
store already passes them over - so they are no longer in the backup.
`outrage check` names three of the four; a link is the one it does not.

### `Store.copy_from`: every bulk move is a copy between two stores

New, and the shape the export, the import, the repack and the backup are being
folded onto. `store.copy_from(source, subtree, key_range=..., prefix=...,
on_conflict=..., dry_run=...)` writes every document the source holds in that
selection into `store`, yielding a `Transfer` per document as it goes.

A method on the **target** rather than a function over a pair, because the
target is what knows how it is written: a database takes a document at a time,
a file written whole takes all of them and writes once. Either end may be any
`Store`, so a copy out of a mount table spanning three files lands in one, and
a copy into one is routed to the store that owns each key. Metadata crosses as
the keys it is, and so does each document's `updated_at`.

**Breaking for library callers:** `Transfer` and the transfer vocabulary -
`SKIP`, `OVERWRITE`, `STOP`, `CONFLICTS`, `WROTE`, `SKIPPED`, `FAILED`, `READ`,
`STOPPED` - have moved from `outrage.bulk` to `outrage.store`, which is where
the operation they describe now lives. `outrage.bulk` keeps the file mapping
and the walkers. `Store.located(key, format)` is new beside them: the file a
store keeps a key in, or None where naming one would mean nothing, which is
what lets a transfer report key to path when a directory of files is one end.

### `outrage export` and `outrage import` are copies

Both are now thin wrappers over `copy_from` with a `FilesystemStore` on one
end, which is what they always were by hand. What changes for a user:

* **An import carries each file's modification time** as the document's
  `updated_at`, and an export sets each file's mtime from the document. The
  export/import round trip is lossless over content, format *and* timestamp; it
  used to stamp everything with the moment the import ran.
* **An import reports in key order**, not in the file walk's name order.
* **A conflict is decided by key**, at either end, so a document held as
  `a.md` collides with one arriving as json.
* **An export refuses to write through a symlink** at the target path rather
  than replacing it, and says so per document. It used to skip one under
  `skip` and replace it under `overwrite`.
* **What a tree does not hold as a document is no longer reported.** A
  symlink, a file that is not UTF-8 text, a name that no key spells, and the
  second file of two claiming one key are passed over silently, where the old
  file-by-file walk named each one. `FilesystemStore.check_file` knows all but
  the first, and nothing a person can run reaches it over a foreign tree yet.

`outrage pack` is unchanged and still builds through `ParquetStore.build`.

### A write may carry the timestamp it is copying

`Store.store_document` takes `updated_at`, an ISO 8601 timestamp normalised to
UTC at second precision; left out, it is now, which is what every ordinary
write means by it. It exists for the write that is a **copy** of a document
that already exists: a transfer between two stores carries the timestamp
across, or the copy says the whole corpus was written the moment it was
copied - the one fact about a document that nothing else can reconstruct. A
title written in the same call is stamped with it too.

Every backend honours it: SQLite writes the column, `ParquetStore.build`
records it, and a tree of files sets the file's mtime, which is what that
backend's `updated_at` *is*. Deliberately **not** offered by the MCP
`store_document` tool or by `outrage set` - a client writing a document is
writing it now.

### A `!` segment opens a metadata namespace

**Breaking**, and it changes what a metadata name *is*. A segment beginning
with `!` used to swallow everything below it: `a/!changelog/22` was metadata
called `changelog/22`, a key every read returned, no listing showed, and an
export dropped. It now opens a **namespace** on the key above it, inside which
everything is an ordinary namespace again - documents, `?`, `?last` and their
own metadata. So `a` carries `changelog`, `a/!changelog/22` is a document kept
inside it, and `a/!changelog/22/!title` is that document's title.

Metadata still changes exactly one thing, which is depth: `!` and everything
after it adds none, so `a`, `a/!changelog` and `a/!changelog/22/!title` are all
at depth 1. Levels and depth are therefore decoupled - a survey reaches a
namespace's contents by being *scoped* inside it, not by asking for more depth,
and that is what keeps depth across a mount boundary a constant offset.

What follows from it:

* **A survey descends into a metadata namespace only when scoped inside one.**
  `get_documents(meta_name=["title"])` at the root returns document titles, not
  the titles of things kept inside metadata. Scope it at `a/!changelog` to read
  those, and there `22` is a document and its `!title` is a title.
* `list_keys("a/!x")` lists what is in `a/!x`, and `?` and `?last` work at that
  level: `document/!changelog/?` allocates sequential notes.
* **A metadata key takes a `title`**, which becomes its own `!title`. Passing
  one used to be refused, on the grounds that metadata did not nest.
* **A delete of a key takes its whole metadata subtree** - one unit - and needs
  `recursive` for anything else below, a metadata namespace's contents
  included. `descendant_count` reports exactly what a plain delete would keep.
* **An export round-trips `a/!x/y`.** The shape on disk is the ordinary
  document-with-children one: `!x.md` beside the directory `!x/`.
* `outrage.keys.Key.meta_name` is now the **first** metadata segment only, with
  a new `meta_path` beside it carrying the remainder. **Breaking** for library
  callers reading `meta_name` on a key with a path below its first `!`; "this
  key is the metadata value" is `meta_name is not None and not meta_path`, and
  `Key.is_meta_value` says it in one place.
* `outrage.keys.relative(key, scope)` parses a key as it is named from inside a
  scope, which is what makes those questions answerable at any scope, and
  `outrage.keys.meta_range(key)` bounds the unit a plain delete takes.

**Stores are migrated, and no key moves.** SQLite goes to schema 6 in place,
rebuilding the table so a migrated file has exactly the schema a fresh one has.
A parquet file goes to format 2, and **a version 1 file is still read** - both
columns are derived from `key` on the way in, so nothing is repacked. A tree of
files is not versioned at all, because there the layout is the format and the
layout does not change.

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

### A shortened delete preview counts what it previews

`outrage rm --recursive --dry-run --limit N` printed a trailing "and N more"
that was short by the key's own metadata, and **went negative** once the limit
reached past the ordinary children - "and -1 more" where one key was left. The
preview walks what a recursive delete takes; the number it was subtracted from
was `descendant_count`, which reports what a *plain* delete would keep and so
leaves that unit out. Two questions, one variable.

`outrage.store.Store.descendant_count` gains a keyword-only **`whole_subtree`**,
false by default, which asks the second one: everything strictly below the key,
its own metadata unit included. No existing call changes meaning, and the front
end now counts the set it walks. **Breaking** only for a third-party `Store`
implementation, which has to accept the keyword.

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
