# Implementation

## Currently implemented

Environment: conda environment `rage`, Python 3.14.6, SQLite 3.53.4. Package
installed in editable mode with `pip install -e ".[dev]"`. 104 tests passing;
`ruff check` and `ruff format --check` clean.

### 0. Project scaffolding — done

`pyproject.toml` with a hatchling build, package under `src/rage/`, a
`rage-server` console script, and `pytest` and `ruff` as development
dependencies.

### 1. Key handling — `src/rage/keys.py` — done

Parses and validates keys against the grammar, splits the metadata suffix, and
derives `doc_key`, `meta_name` and `parent`. Also `ancestors`, `depth` and
`subtree_range`.

`subtree_range` returns half open bounds rather than a `LIKE` prefix, for two
reasons: `_` is legal in a segment but is a `LIKE` wildcard, and a prefix match
would let `a.b` pick up `a.beta`. Everything under `a.b` sorts within
`["a.b.", "a.b/")` because `.` immediately precedes `/`, so subtree scans stay
exact index range scans.

### 2. Data store — `src/rage/store.py` — done

Directory resolution, schema creation under `PRAGMA user_version`, WAL mode, and
all five operations with the semantics recorded in design.md. No MCP dependency.

Formats are detected: content that parses as a JSON object or array is recorded
as `json`, everything else as `markdown`, and an explicit argument overrides
both.

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
