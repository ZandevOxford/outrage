# Changelog

Notable changes to `outrage`. This project follows [semantic versioning](https://semver.org).

## 0.4.0 - 2026-08-29

0.4.0 is about what a store and its server *say*: the documentation outrage
ships about itself, the sentence a caller reads when a call is refused, and the
readme a store introduces itself with. The main changes are:

* **Outrage's own documentation is a mounted store**, generated from the
  docstrings and shipped in the wheel, so a session can read the API reference
  through the same tools it reads anything else with.
* **A store's `readme` is named in the server's instructions rather than
  carried in them**, so it may be any length, and it is read live by the
  session that needs it.
* **A failure a caller can correct now reaches them as a sentence**, against
  mcp 2.1, which stopped carrying the text of anything that is not a
  deliberate `ToolError`.
* **`document_file` and `copy_tree`** are new tools: one document through a
  file, and a subtree copied or re-rooted.
* **A mount may name its backend**, so a directory of files is mountable.

`requires-python` drops to **3.12**. For library callers this is a breaking
release in one place only: five names are gone from `outrage.server`, listed
below.

### Python 3.12 is enough

`requires-python` asked for **3.14**, which was the interpreter to hand when
the first commit was written rather than a decision. Nothing in the package
needs it: the only feature ever argued for is `tomllib`, in the standard
library since 3.11, and compiling the whole of `src` and `tests` under 3.12 is
clean. Asking for an interpreter released in October 2025 excluded most of the
ones outrage would otherwise install into, for nothing gained.

The floor is now **3.12**, and `environment.yml` moves with it so that the
environment the README tells a contributor to create is the one the package
asks for. The suite, the doctests, `ruff` and the strict docs build were run on
3.12 and on 3.14; nothing in the package changed.

### A failure a caller can fix now says so

mcp 2.1 stopped carrying the text of anything raised out of a tool that is not
a `ToolError`: a deliberate failure keeps its message, and everything else
reaches the client as `Error executing tool <name>` and nothing more, its own
text logged server-side. That is the distinction `outrage.errors` already drew,
and it caught **seven** places where this package was on the wrong side of it.
A damaged `json-string` value, an unknown `encoding` or `format`, an empty
`pattern` and an empty `meta_name` were each a bare `ValueError`, so a model
that had emitted scaffolding into its own tool call - the thing the encoding
exists to catch - was told only that something went wrong, when what it needed
was to be told to send the call again.

* **`store.InvalidArgumentError`** is an argument value the caller can correct,
  as against the checks that guard a front end's own mistake. Three message
  codes follow it, carrying the wording that used to be written at the raise
  site.
* **`format` and `encoding` are typed rather than described.** The tool schema
  listed the values in prose and said `string`; it now carries a real `enum`
  and `const`, so a bad one is refused before the tool body runs.
  `store.Format` and `store.Encoding` are the new source, and `store.FORMATS`
  and `store.ENCODINGS` are `get_args()` of them. `meta_name` takes at least
  one entry.
* **`outrage get --pattern ''` printed a traceback** and prints a sentence now.
  The command line was never about the SDK; it had the same misclassification
  underneath.

The package still supports `mcp>=1.2`, and the one test asserting the 2.1
behaviour skips where the SDK does not draw the distinction.

### The store's `readme` is named in the server's instructions, not carried in them

A client cuts a server's instructions at a length it does not announce, so
carrying the readme meant capping it: `DELIVERY_BUDGET` less whatever the
static text cost, which was **667 characters**. Over that, nothing was inlined
and the length was reported instead - a store whose readme had grown was
silently no longer introducing itself, and only a freshly started session could
see it. Both readmes in this repository were over it: this project's own at
1898 characters, and the `default_readme` shipped as a template at 2560.

Capping was the wrong bound. How long a store's entry point should be is the
project's business, and different projects' conventions will not fit one
number. The instructions now carry a fixed sentence saying there is a `readme`
and to read it first, whatever length it is; a store with none is still told
the convention, so the store is still consulted, just not quoted.

* **`README_HEADING`, `README_NOTE`, `README_MAX_CHARS`, `README_FLOOR_CHARS`
  and `SCAFFOLDING_CHARS` are gone** from `outrage.server`, and `READ_README`
  and `PROTECTED_CHARS` replace them. `PROTECTED_CHARS` measures what is
  delivered ahead of the tail - the readme line plus the essentials - which is
  everything that has to survive the cut. It is 1328 of the 2048 budgeted.
* The readme is now read **live** by the session that needs it, rather than at
  server startup, so a readme written during a session reaches that session.

### A mount can say which backend keeps it, so a directory of files is mountable

Which backend keeps a store followed from its file extension, and a directory
has none - so `FilesystemStore`, the backend whose store *is* a directory, was
the one thing a mount table could not describe. A mount argument now takes
options after its store file, and `type` is the first of them:

```sh
outrage ls --mount docs=documents,type=files
outrage export DIR --store documents,type=files
```

```toml
[mount]
docs = { path = "documents", type = "files" }
short = "documents,type=files"   # the same thing, as the argument it stands for
```

* **`KEY=FILE[,NAME=VALUE]...`**, which is `mount(8)`'s own shape. The option
  lives inside the argument's value rather than in a second flag beside it, so
  one mount stays one option occurrence and overriding an entry from a mount
  table remains a matter of replacing it whole. The price is a comma, which a
  store file may no longer hold; it is refused in both directions rather than
  being quietly the first option's name.
* **An entry in `mounts.toml` may be a table**, `{ path = "...", type = "..." }`,
  whose fields are the option names. A string entry is still the value half of
  a `--mount`, options and all, so nothing is expressible typed and not in a
  file.
* **The type is a backend's own name** - `sqlite`, `parquet`, `files` - which
  is the word a report already uses for it. An unrecognised *extension* still
  falls back to the default backend; an unrecognised *name* is refused, because
  one is a guess at what somebody meant and the other is what they said.
* `--root-mount`/`--store` takes the same options, so a tree can be the whole
  store: `outrage check --store documents,type=files`.
* `outrage mounts` reports the type in the file column, since it is the one
  thing about a mount that cannot be read off the name.

### A subtree copy, as a tool

The MCP server offers `copy_tree`, so a session working through the tools can
move a subtree from one key to another without shelling out to `outrage copy`.
It is the same call the command line makes - `Store.copy_from` over the mounted
namespace - with the argument shaping and the result shaping a tool needs:

* **The result is statistics, not keys.** A copy may cross more keys than a
  result can hold, so it reports counts by action, the characters that crossed,
  and a bounded sample of what failed. The command line still prints a line per
  document, because a person reads it as it goes and an interrupted run has
  then said exactly what it did - a property one return value cannot have.
* **A `limit` and a `cursor`, so a copy resumes.** `next_cursor` is the source
  key of the last document that crossed; call again with `cursor` set to it and
  everything else unchanged. The cursor is a separate argument from the six
  range cuts, which stay the selection.
* **Read-only mounts under where the documents land are listed in full**, as
  `delete_keys` already does: there are never many mount points, and a count
  alone reads as a copy that mostly worked.
* `Store.copy_from` and `outrage.bulk.copied` grew the same `cursor` and
  `limit`. The copy stops in front of the key it would have written next, so a
  bounded run crosses exactly `limit` documents, and the generator *returns*
  the resume cursor - a source key, which is not what any transfer carries.

### A copy can re-root a subtree, not only nest it deeper

`Store.copy_from` and `outrage copy` take `reroot`/`--reroot`, which strips the
source subtree's own key before grafting: `outrage copy a/b tmp --reroot` lands
the documents at `tmp` and `tmp/one` rather than at `tmp/a/b` and
`tmp/a/b/one`. Without it a copy could only nest a subtree deeper - "these
documents now live at another key" was inexpressible, and a round trip through
a temporary namespace did not come home, because the second hop grafted the
temporary prefix along with everything else.

Grafting the whole source key is still the default and still what an archive or
a backup wants. What changes with the flag is which pairs of keys are safe: a
copy streams a live walk, so grafted only a target inside the source is
refused, while re-rooted the two subtrees must be disjoint in either direction
- `a/b` re-rooted onto `a` would send `a/b/b/x` to `a/b/x`, back inside the walk
that is still running. The rule is `bulk.overlapping`, applied by the front
ends, so the command line and the server refuse the same pairs.

### Outrage's own documentation, as a store

A read-only store of documents about outrage itself ships inside the package
and is mounted at `outrage`, so the manual is reached with the same tools as
everything else rather than through a second retrieval path. It holds a readme,
and documents on keys, the tools, the command line and the conventions.

* **The MCP server mounts it unless told otherwise; the command line does not
  unless `--mount-docs` asks for it.** A bare `outrage` command stays a clean
  namespace over the project's own store.
* **It is an ordinary mount once it is there.** It shadows, it appears in a
  listing as a read-only mount, and a `mounts.toml` naming `outrage` overrides
  it silently by the ordinary rule that a later source wins. `--unmount
  outrage` is the off switch on either front end; there is no second flag for
  it.
* **It announces itself in a listing and is not delivered.** The server's
  instructions still carry only the root store's readme, on the delivery-budget
  argument that has always governed them.
* **A build that dropped the tree warns on the server and refuses on the
  command line.** Nobody asked for the mount on the server, so a missing tree
  must not stop a session starting; `--mount-docs` was typed, so it is a
  refusal there.

`mounts.open_mounts` gains `attached`, a mapping of already-open stores mounted
read-only at their keys - the one way in for a store that is not a file
relative to `--dir`, which a tree in `site-packages` cannot be. New module
`outrage.shipped` says where the tree is and opens it.

### One document through a file, as a tool

The MCP server offers `document_file`, which moves a single document between
the store and a file so that a long document can be edited with `sed`, a
heredoc or an editor without its unchanged text passing through an agent's
context twice. The direction is decided by one argument and nothing else: with
no `path` the document at `key` is written to a file under `export/` in the
store directory and the path returned; with a `path` that file's content is
stored at `key`.

* **The export path is the key's own**, by the same mapping `outrage export`
  uses, so `context/60/state` is `export/context/60/state.md` and exporting a
  key twice reuses one file rather than accumulating copies. The answer says
  whether a file was already there. A key that has no path at all - one with a
  `.` or `..` segment - gets a random name carrying the format's extension
  instead.
* **The key and the path need not agree.** An import stores at the key it is
  given, whatever file the content came from, so exporting one key and
  importing to another copies content across the store.
* **Only a file under the export directory can be imported**, which is the
  whole of the check: the same containment rule the bulk export is guarded by.
  A relative path is taken from that directory rather than from the working
  directory, and a file missing at one says so.
* **An empty file is stored rather than refused**, and both sizes are reported
  instead - the characters written and the characters that were there before,
  with a note when the document shrank. Emptying a document is a thing a person
  may mean; an edit script that truncated silently is not.

`build_server` takes the store directory as a third argument to make this
possible, since what it serves is a `MountedStore` and cannot be asked where it
is. The tool is registered only when that directory is given.

Library callers gain `bulk.export_document`, `bulk.import_document`,
`bulk.file_for_key` and `bulk.contained_file`, and `store.EXPORT_DIR_NAME`.

## 0.3.0 - 2026-08-27

0.3.0 makes multiple stores and their mounted namespace first-class throughout
the library and command line. The main additions are:

* **Filesystem-backed stores.** `FilesystemStore` presents a directory with one
  file per key through the same `Store` interface as SQLite, Parquet and a
  mounted table. It can participate in a `MountedStore` through the library;
  command-line mount specifications still select file backends by extension.
* **File-based mount configuration.** `mounts.toml` records the root,
  read-write and read-only mounts once for both the MCP server and CLI, with
  command-line overrides, `--unmount`, additional config files and a safe
  `outrage mounts` inspection command.
* **Expanded database editing from the CLI.** `get`, `set`, `ls`, `dump`, `rm`,
  `export` and `import` now operate across the mounted namespace, and the new
  `copy` command transfers depth- and range-bounded document selections between
  its prefixes without a filesystem round trip.

This is a breaking release for library callers: the mount table is now
`MountedStore(Store)`, `Store` and `FileStore` are separate interfaces, and
metadata is a namespace rather than a leaf. The detailed changes and migration
notes follow.

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
what makes a committed table safe to override one entry of.

`--unmount KEY` removes a mount a file declares, which is the one thing an
override cannot do - naming a mount replaces it or adds it. An unmount is a
deletion rather than a second claim, so it takes away every earlier mount at
that point whatever source it came from, and a `--mount` written after it
mounts again. An unmount that removed nothing is refused, on the same ground
`--mount-ro` refuses an unmatched mount point: it reads as though it worked,
and what it leaves behind is the mount somebody meant to take away.
`--no-mount-config` ignores the default file for a run.

**`outrage get`, `set`, `ls`, `dump`, `rm`, `export` and `import` now take
`--mount`, `--mount-ro`, `--unmount`, `--mount-config` and
`--no-mount-config`**, and act across the whole table,
so the command line sees the namespace the MCP server serves rather than the
root store alone. `--store` is the root mount on those commands and
`--root-mount` is an accepted alias for it. `outrage check` and `outrage
backup` stay per-file by nature, and already say which file with `--store`.

**`outrage init` and `outrage config` write the mounts to `mounts.toml`, not
into `.mcp.json`.** That is the payoff: registering the server stops being
"write the whole table into a client's JSON, correctly, from a command" and
becomes "point at a directory", so the entry's `args` are `--dir` and whatever
`--log` says. `config.server_entry` no longer takes `root_mount`, `mounts` or
`read_only_mounts` - **breaking for library callers** - and
`install.Installation` gained a `table` field saying what happened to the file.

The table is written **once**, commented, and never rewritten: a file whose
reason for existing is comments cannot be machine-rewritten, because a rewrite
is what loses them. A run naming a mount an existing table does not hold prints
the lines to add. A run naming no mount writes nothing at all - `config` and
`init` register a server, and creating a store directory to drop an empty file
into it is not something either was asked to do.

**Nothing migrates an installed configuration.** An entry an earlier release
wrote keeps its `--mount` arguments and goes on working: `merge_entry` inherits
what a new entry does not mention, and those arguments still win because the
command line comes after the file. `outrage config` reports that they are there
and that removing them is an edit to `.mcp.json`, which is the migration, done
by hand and only when somebody wants it.

**`outrage mounts` reports the table a command line would open, and opens
none of it.** Opening a read-write mount is what creates it, so a mistyped name
in a committed table becomes an empty store that reads exactly like a store
with nothing in it yet - `--mount-ro` refuses for that reason and the
read-write half never could. This says so first, and is safe to run on a fresh
checkout. It takes every option the other commands take, so it answers for the
line you would really run, and names the source each mount came from - the
question a table merged from a default file, each `--mount-config` and what was
typed created. Non-zero when the table would not open: a read-only mount that
is missing, or two mounts at one point. A read-write mount that is not there
yet is reported and is not a failure.

`mountfile.origins` is that provenance, and `mountfile.Origin` what it returns.

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

### Copying ranges from the command line

**`outrage copy SOURCE TARGET`** exposes `Store.copy_from` over the mounted
namespace. It selects the subtree at `SOURCE`, optionally bounded by `--depth`
and any combination of the six `KeyRange` cuts, and grafts every selected key
beneath `TARGET`. That makes a copy between mounted stores a single command,
with metadata and original timestamps crossing beside document content.

The existing `skip`, `overwrite` and `stop` conflict modes and `--dry-run`
apply unchanged. A target at or below the source is refused: the transfer is a
live stream rather than a snapshot, so otherwise it could discover and copy
what it had just written.

The shared mount-option help now correctly says that surveys and recursive
deletes cross mount boundaries; the previous text described the staging
behaviour retired when boundary crossing landed.

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
