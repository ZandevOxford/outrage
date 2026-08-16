# Implementation

## Currently implemented

Environment: conda environment `rage`, Python 3.14.6, SQLite 3.53.4. Package
installed in editable mode with `pip install -e ".[dev]"`. 147 tests passing;
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
picking the same number.

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

### 4. Integration with Claude Code — in progress

* `.mcp.json` written, registering the server for this project. Its `command` is
  an absolute path into the conda environment and so is machine specific.
* The server has been exercised end to end over stdio by an MCP client: tool
  listing, store, survey by `:title`, read and recursive delete.
* Still to do: use it from a real Claude Code session and see where the tool
  descriptions or result shapes get in the way.

Note that a running session holds the server's `instructions` and tool
descriptions from when it started, so the server has to be restarted for
changes to either to reach the agent.

### 5. Skills

* Skill and/or agent definitions telling the agent *when* to store and retrieve,
  and what key conventions to follow.

Expected to be the hardest part and the one that determines whether the system
is actually used in practice; deliberately last, so it can be written against
tools whose behaviour is already known.

The server's `instructions` string is a first, minimal attempt at this: it
describes the key shape and steers towards storing a `:title` alongside each
document, so a later session can survey the store cheaply before reading
anything in full.

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
