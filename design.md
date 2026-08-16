# Rage design

## Components

### MCP server

Python implemented MCP server primarily for use in local mode.

Provides access to the data store.

### Data store

Python library for storing data used by the MCP server.

Data is stored in an SQLite database local to the current project.

The store is kept independent of the MCP server: it has no knowledge of MCP and
can be tested and reused on its own. Initially a single module; it may become a
package later.

#### Store location

The server is given a *directory*, not a file, so that additional files can be
added alongside the database later (indexes, exports, vector data).

Resolution order:

1. `--dir PATH` command line argument
2. `RAGE_DIR` environment variable
3. `./.rage/` relative to the server's working directory

The database is `store.sqlite` within that directory. The directory is created
on demand.

The intended normal usage is a per-project MCP configuration passing `--dir`
explicitly, since an MCP server cannot be relied on to inherit the project
working directory. The working directory fallback exists for CLI and test use.

### Command line tool

Not yet implemented.

A CLI over the same store library, covering everything the MCP server exposes
plus the operations that only make sense from a shell:

* Bulk import of documents, for example a directory of markdown files mapped
  onto a key prefix, and the corresponding bulk export.
* Inspecting and repairing a store outside an agent session.
* Writing the MCP server configuration for a project, filling in the interpreter
  or entry point location and the store location.

The last of these removes most of the friction in first time setup. The server
has to be launched by an absolute path into whichever environment it was
installed in, and that path is only reliably known from inside that environment
— which is exactly where the CLI is running. The initial `.mcp.json` in this
repository was written out by hand for that reason, and is machine specific as a
result.

It should be able to write project scoped or user scoped configuration, should
say what it is about to change and leave any unrelated servers in the file
alone, and should be safe to re-run when the environment moves.

It reads the same store directory, resolved the same way, so the working
directory fallback described above is the normal case for the CLI rather than
the exception.

Because both the CLI and the MCP server are thin wrappers over the store
library, neither should carry behaviour of its own.

### Skills

Appropriate skills and/or agent definitions.

Initially to support Claude Code.

## Key namespace

The key namespace is an arbitrary string, with slash delimiters. A colon instead
of a slash indicates metadata.

For example:

* context/<guid>/task  could contain a summary of the task for a particular context
* context/<guid>/design  could contain a design document
* context/<guid>/design:title  could contain the title of the design document
* project/reference/implementation  could contain the implementation notes for the project
* notes/src/myfile.py  could contain notes about a particular source file

If A/B/C exists then A and A/B implicitly exist with no content.

Keys are *not* paths, and are never resolved against a filesystem, but the
delimiter is `/` so that a key may usefully mirror one. That is why `.` is an
ordinary segment character: a key naming a file has to be able to carry its
extension. `.` and `..` are rejected as whole segments, since they can only
suggest a navigation that does not exist here.

### Grammar

* A key is one or more segments joined by `/`.
* A segment matches `[A-Za-z0-9_.-]+`, and is not `.` or `..`.
* A key may carry at most one metadata suffix, introduced by `:` and appearing
  only at the end of the key. The metadata name is a single segment and may not
  contain `/`, so the metadata namespace is flat.
* Metadata may be attached to any key, including implicit keys with no content.
* A key *being written* may use `?` in place of one whole segment, asking the
  store to allocate a number for it. See Autonumbering below. `?` is otherwise
  not a legal character, so it is unambiguous, and it is rejected outright by
  every other operation.

Multiple metadata entries may be attached to one document, which is the intended
mechanism for alternative summaries and, in future, embedding vectors to support
different kinds of search.

### Autonumbering

Storing at `tmp/?` writes to `tmp/1` in an empty store, `tmp/2` next, and so on.
The wildcard may be any segment, not only the last, so `context/?/design` opens
a numbered context; the write reports the key it actually used, which is how a
caller learns the number and can then write `context/1/task` alongside it.

This exists so that an agent can create a container without inventing an
identifier. Inventing one is what a guid is for, but a guid is expensive to
carry in a prompt and impossible to type, and picking a name commits to a
description before the work is understood.

The allocated number is one past the highest number already used among the
children of the key enclosing the wildcard, counting keys that exist only
implicitly or only carry metadata. That makes the number unique but not
reserved: deleting the highest frees it again. Anything that needs a permanent
identity should use a name, not a number.

Because allocating reads the store before writing to it, the whole operation
runs in one immediate transaction, so two concurrent writers cannot pick the
same number.

## Values

Values are strings which should either be markdown or json.

## Tools

* Retrieve document: retrieves the content of a document. Optionally specify a character range. Optionally specify a search pattern and index to start the read from.
* Store document: stores document or metadata at a key.
* List keys: List keys immediately under a key, including subkeys and metadata.
* Get documents: Get multiple documents or metadata, with a key and or metadata filter. It should be possible to for example list the titles of all documents under a key.
* Delete keys: Delete a document and its metadata, optionally deleting the whole
  subtree beneath it.

### Tool semantics

**Retrieve document.** The search pattern is a literal substring, not a regular
expression: it is predictable for a model to construct, needs no escaping, and
cannot backtrack pathologically on a large document. The index selects which
occurrence to start from. Reads are capped at a default of 8000 characters per
call; the response reports the offset, the number of characters returned, the
total document length, and the next offset, so a large document can be paged
without any single call flooding the agent's context.

**Store document.** Overwrite only. Versioning is deferred and is expected to be
implemented later as a separate archive table rather than by complicating reads.
The result reports the key written, which is the only way a caller learns a
number allocated for a `?` segment.

An optional `title` writes the `:title` metadata in the same transaction. The
saved call matters less than the fact that a separate call is one that can be
forgotten: the title is what makes a document findable later, so the convention
has to be reachable without remembering it. It follows an allocated number, so
`context/?/design` with a title titles `context/1/design`, not the wildcard. It
is rejected on a key that is itself metadata, since metadata does not nest.

**Get documents.** Matches the given key and everything beneath it at any depth,
with an optional depth limit. Recursion is the default because the motivating
case — listing the titles of all documents under `context` — spans a level of
nesting.

A survey by `meta_name` can only see documents that carry it, so on its own it
under-reports the store, and does so silently — the caller has no way to tell a
complete survey from a partial one. The result therefore also names the
documents in range carrying none of the requested names, under `without_meta`.

**Delete keys.** Deleting a key removes its content and all of its metadata.
Deleting a subtree requires an explicit recursive flag, so a mistyped key cannot
silently remove a whole context. Storing an empty document is *not* a deletion;
it leaves an empty document in place.

Deleting a key that holds nothing itself is a no-op, and an empty result is
indistinguishable from a successful deletion of an empty key. A non-recursive
delete therefore reports how many keys it left standing beneath the target, so
the guard rail announces itself instead of looking like success.

**Reading a container.** A key with descendants but no content of its own is a
container, not a mistake, and the failure to read one should say so rather than
report the same "not found" as a key that does not exist anywhere. The two are
worth separating because they call for different next moves: list what is
beneath, versus check the key.

## Schema

This can be stored in a single table, with an index on the key.

```sql
CREATE TABLE documents (
  key        TEXT PRIMARY KEY,  -- full key, including any ':meta' suffix
  doc_key    TEXT NOT NULL,     -- key with the metadata suffix removed
  meta_name  TEXT,              -- metadata name, or NULL for a document
  parent     TEXT NOT NULL,     -- derived: enclosing key
  content    TEXT NOT NULL,
  format     TEXT,              -- 'markdown' | 'json'
  updated_at TEXT NOT NULL
);

CREATE INDEX idx_documents_parent ON documents(parent);
CREATE INDEX idx_documents_meta   ON documents(meta_name, doc_key);
```

`doc_key`, `meta_name` and `parent` are all derived from `key` on write. They
are stored rather than computed at query time so that the two main access
patterns are plain indexed lookups:

* *List keys immediately under X* is an equality match on `parent`. The parent
  of `A/B:title` is `A/B`, so a document's metadata lists alongside its
  subkeys, as required. Implicit intermediate keys need never be materialised —
  they fall out of a `DISTINCT parent` query.
* *Get one metadata name across a subtree* is a range scan on
  `(meta_name, doc_key)`.

Deriving these columns instead of using `LIKE 'A/B%'` also avoids the prefix
collision where `A/B` would match `A/Beta`.

A subtree is bounded by `["A/B/", "A/B0")` rather than by a prefix match. `/`
and `0` are adjacent code points, so the only strings in that range are `A/B/`
itself and the keys beneath it — a property of the delimiter alone, holding
whatever segments are allowed to contain.

The schema carries a version in `PRAGMA user_version`. Version 2 is the current
one; version 1 was the same schema with period delimited keys, and is migrated
by rewriting `.` to `/` in the three key columns. That rewrite is exact because
no version 1 segment could contain either character.

SQLite runs in WAL mode to tolerate concurrent readers.

## Deferred

* **Versioning**, as a separate archive table.

* **Semantic search**, implemented as additional metadata holding vectors. Not a
  current consideration, but the flat metadata namespace above is intended to
  accommodate it without a schema change.

* **The command line tool** described under Components.

* **Unicode keys.** Segments are currently restricted to `[A-Za-z0-9_.-]`. The
  intent is to widen this to most of Unicode, so that keys can carry natural
  language. Two things need care when it happens:

  * *Normalisation.* The same key typed two ways must not become two rows, so
    keys should be normalised, presumably NFC, on the way in.
  * *The delimiters.* `/`, `:` and `?` must stay reserved, along with anything
    that could be confused with them — the fullwidth and division-slash
    lookalikes especially, since a key that displays as `a/b` but stores as one
    segment is a silent trap.

  Subtree bounds used to be the third concern here: under the period delimiter
  they depended on no segment character sorting between `.` and `/`. Bounding
  on the adjacent code points `/` and `0` removed that dependency, so widening
  the character set no longer threatens the range scans.

* **Bootstrapping the skill configuration from the MCP server.** The server
  would help a session install or update the skills and configuration that make
  the store useful, either by editing local configuration or by returning
  instructions for doing so.

  Worth separating the two halves, because they are not equally risky. A tool
  that *returns* the configuration and instructions is unobjectionable: it is
  just a document, the agent and the user decide what to do with it, and it
  keeps the guidance versioned alongside the server that it describes. A tool
  that *edits* local configuration is a different proposition — an MCP server
  writing outside its own store directory is a surprising capability, it is
  hard for a user to audit, and the failure mode is a corrupted configuration
  rather than a bad answer.

  The middle option is for the server to write the files and for the CLI to be
  the thing that installs them, which keeps the write under a command the user
  ran deliberately. Worth prototyping the read only half first and seeing
  whether the editing half is still wanted afterwards.

  Note that the CLI already covers the server half of this: it writes the MCP
  server configuration, as described under Components. So the question here is
  narrower than it first appears — it is only about the skills, and only about
  whether the server should be able to install them without the CLI.

## Open questions

None outstanding.
