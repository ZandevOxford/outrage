# Implementation

## Currently implemented

Nothing.

Repository initialised. Conda environment `rage` created with Python 3.14.6
(SQLite 3.53.4).

## TODO

Build order. Each step is intended to be independently testable, and the store
is completed before the MCP server is written so that it can be exercised
without a protocol harness.

### 0. Project scaffolding

* `pyproject.toml`, package under `src/rage/`, console entry point for the
  server.
* `pytest` and `ruff` as development dependencies.

### 1. Key handling — `src/rage/keys.py`

* Parse and validate keys against the grammar in the design.
* Split the metadata suffix; derive `doc_key`, `meta_name` and `parent`.
* Tests covering valid and invalid keys, metadata on implicit keys, and the
  `A.B` / `A.Beta` prefix collision.

Done first because it pins the namespace semantics cheaply, before anything
depends on them.

### 2. Data store — `src/rage/store.py`

* Directory resolution and schema creation, WAL mode.
* Retrieve, with character range, literal substring search with occurrence
  index, and capped reads with a continuation offset.
* Store, overwriting.
* List keys, including implicit intermediate keys and metadata.
* Get documents, recursive with optional depth, filtered by key and metadata
  name.
* Delete, with an explicit recursive flag for subtrees.
* Tests against a temporary directory.

### 3. MCP server — `src/rage/server.py`

* Stdio server exposing the five tools as a thin wrapper over the store.
* No logic beyond argument validation and result shaping; behaviour lives in the
  store.

### 4. Integration with Claude Code

* `.mcp.json` configuration passing `--dir`.
* Exercise the tools live against a real project store.

### 5. Skills

* Skill and/or agent definitions telling the agent *when* to store and retrieve,
  and what key conventions to follow.

Expected to be the hardest part and the one that determines whether the system
is actually used in practice; deliberately last, so it can be written against
tools whose behaviour is already known.

### Also outstanding

* `README.md` is empty. It is intended to describe the documentation structure
  and link to the design documents.
