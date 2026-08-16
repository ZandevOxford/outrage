# Implementation

## Currently implemented

Environment: conda environment `rage`, Python 3.14.6, SQLite 3.53.4. Package
installed in editable mode with `pip install -e ".[dev]"`. 170 tests passing;
`ruff check` and `ruff format --check` clean.

### 0. Project scaffolding — done

`pyproject.toml` with a hatchling build, package under `src/rage/`, a
`rage-server` console script, and `pytest` and `ruff` as development
dependencies.

### 1. Key handling — `src/rage/keys.py` — done

Parses and validates keys against the grammar, splits the metadata suffix, and
derives `doc_key`, `meta_name` and `parent`. Also `ancestors`, `depth`,
`subtree_range`, and the `?` wildcard: `parse` accepts one only when asked, so
reads and deletes reject it rather than treating it as a pattern.

`subtree_range` returns half open bounds rather than a `LIKE` prefix, for two
reasons: `_` is legal in a segment but is a `LIKE` wildcard, and a prefix match
would let `a/b` pick up `a/beta`. Everything under `a/b` sorts within
`["a/b/", "a/b0")` because `/` and `0` are adjacent code points, so subtree
scans stay exact index range scans no matter what a segment may contain.

### 2. Data store — `src/rage/store.py` — done

Directory resolution, schema creation and migration under `PRAGMA user_version`,
WAL mode, and all five operations with the semantics recorded in design.md. No
MCP dependency.

Formats are detected: content that parses as a JSON object or array is recorded
as `json`, everything else as `markdown`, and an explicit argument overrides
both.

`store_document` returns the key it wrote, which is how a caller learns the
number allocated for a `?` segment. Allocation reads before it writes, so that
path runs in an immediate transaction; concurrent writers block rather than
picking the same number. Its optional `title` writes the `:title` metadata in
the same transaction, after any wildcard has been resolved.

`descendant_count` and `keys_missing_meta` exist to let a caller report what a
result does *not* contain: what a non-recursive delete kept, and what a survey
by metadata could not see. Both were added in step 4.

Schema 2 changed the delimiter from `.` to `/`. Opening a schema 1 store
rewrites its keys in place — exact, because no schema 1 segment could contain
either character.

### 3. MCP server — `src/rage/server.py` — done

Stdio server built on `MCPServer` from the MCP Python SDK, exposing
`retrieve_document`, `store_document`, `list_keys`, `get_documents` and
`delete_keys`. Argument shaping and result shaping only; all behaviour lives in
the store. Argument constraints are declared with pydantic `Field`, so bad
arguments are rejected before reaching the store, and read only and destructive
tool annotations are set.

Tested through the server's own tool dispatch rather than by calling the
functions directly, so the generated schemas and the error paths are covered.

Note the SDK in use is **mcp 2.0**, where `FastMCP` has become
`mcp.server.MCPServer`, model fields are snake_case (`is_error`,
`structured_content`, `input_schema`), and a failing tool raises `ToolError`
rather than returning a result with an error flag.

## TODO

### 4. Integration with Claude Code — done

* `.mcp.json` written, registering the server for this project. Its `command` is
  an absolute path into the conda environment and so is machine specific.
* The server has been exercised end to end over stdio by an MCP client: tool
  listing, store, survey by `:title`, read and recursive delete.
* Used from a real Claude Code session, which is what turned up the five points
  below. Everything worked; what went wrong was that four results were
  misleading and one convention was too easy to skip.

Note that a running session holds the server's `instructions` and tool
descriptions from when it started, so the server has to be restarted for
changes to either to reach the agent. The changes below were made from within a
session and so are **not** live in it; they need another restart.

#### What the session use changed

1. *A non-recursive delete of a key with descendants was a silent no-op.*
   `delete_keys(key="context/2")` returned `{"deleted": [], "count": 0}` — the
   same shape as a successful delete of an empty key — while the whole context
   survived. Read as success, and the mistake is invisible. The result now
   carries `remaining` and a note naming the flag. New `Store.descendant_count`.

2. *Reading a container and reading a missing key gave the same error.* Both
   said `no content stored at X`, so a correct key aimed at a container looked
   like a wrong key. Now distinguished, and the container case points at
   `list_keys`. Deliberately not applied to a metadata key, whose `doc_key`
   descendants say nothing about whether the metadata exists.

3. *A survey by `:title` silently omitted untitled documents.* Storing four
   documents and surveying titles returned three, with nothing to say the
   fourth existed. The survey now reports `without_meta`. New
   `Store.keys_missing_meta`.

4. *Titling a document was a second call that is easy to forget* — forgotten
   once in this session despite the instructions pushing it. `store_document`
   now takes `title` and writes both rows in one transaction.

5. *The invalid segment error did not say what a segment may contain*, leaving a
   caller to guess. It now names the character set.

6. *Unknown arguments are accepted and silently dropped* — **not yet fixed, see
   below.** Found by calling the new `title` argument against the server still
   running the old code: the call succeeded, reported success, and wrote no
   title. Same failure as 1 to 3, and the worst of them, since it makes a stale
   server indistinguishable from a current one.

   The cause is in the SDK, not here: `ArgModelBase` in
   `mcp/server/mcpserver/utilities/func_metadata.py` leaves pydantic's default
   `extra="ignore"`, and the arguments are filtered before a tool function is
   entered, so a tool cannot see what was dropped. There is no per-tool strict
   flag.

   Fixing it means either forcing `extra="forbid"` onto the SDK's model config,
   which is a monkeypatch of a dependency's internals affecting every tool, or
   accepting the SDK's behaviour and relying on `additionalProperties: false` in
   the published schema to make well behaved clients check. Left open
   deliberately: it is a change to how strictly the server treats all client
   input and should be a decision, not a side effect.

Worth noting that five of the six are about result *shapes* rather than
behaviour, and four are the same failure: a result that cannot distinguish
"nothing happened" from "it worked". Tool results are read by something that
cannot see the store, so anything the result does not say is not merely absent,
it is misleading.

### 5. Skills — next

* Skill and/or agent definitions telling the agent *when* to store and retrieve,
  and what key conventions to follow.

Expected to be the hardest part and the one that determines whether the system
is actually used in practice; deliberately last, so it can be written against
tools whose behaviour is already known.

The server's `instructions` string is a first, minimal attempt at this: it
describes the key shape and steers towards giving each document a title, so a
later session can survey the store cheaply before reading anything in full.

Step 4 gave this one useful piece of evidence. The instructions asked for a
title on every document and a session that had just read them still stored one
without. That is an argument for putting a convention in the tool signature
where it can be complied with, rather than in prose that has to be remembered —
and a caution against expecting the skills alone to carry the conventions.

### 6. Command line tool

* A CLI over the store library, covering the same operations as the MCP server
  plus bulk import and export, and a command that writes the MCP server
  configuration for a project.

Not yet scheduled, and deliberately after the skills: bulk import is most useful
once the key conventions the skills establish are settled, since an import has
to choose keys for whatever it ingests.

The configuration writing command is the exception and could be pulled forward
at any point, since it depends on nothing else and replaces the hand written
`.mcp.json` currently in the repository.

## Not planned yet

Recorded in the Deferred section of design.md rather than here, since none of it
is scheduled: versioning, semantic search, Unicode keys, and bootstrapping the
skill configuration from the server.
