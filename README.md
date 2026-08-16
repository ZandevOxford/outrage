# Rage

A simple retrieval system for coding agents: an MCP server, a data store, and
skills that let an agent keep notes, designs and task context in a store local
to the project it is working on.

Retrieval is by key rather than by similarity. Keys are hierarchical, slash
delimited strings such as `context/<guid>/design`, and any key may carry
metadata such as `context/<guid>/design:title`. Since an agent knows the keys it
wrote, lexical addressing is enough, and the system stays deterministic and free
of external dependencies. Semantic search is a possible later addition, layered
on as metadata rather than as a change to the model.

Keys are not paths, but they are shaped like them, so a key can mirror one:
`notes/src/myfile.py` for notes about a source file. A key being written may
also use `?` in place of a segment — storing at `tmp/?` writes to `tmp/1`, and
the store reports the key it chose.

## Status

The store, the MCP server, the key handling and the skill are implemented. The
command line tool is next. See [implementation.md](implementation.md) for what
is done and what is next.

## Documentation

* **[design.md](design.md)** — the design. Components, the key namespace and its
  grammar, tool semantics, and the SQLite schema. Decisions that are deferred or
  still open are recorded at the end.
* **[implementation.md](implementation.md)** — what is implemented so far, and
  the planned build order.

## Components

* **MCP server** — Python, stdio, for local use. Exposes the store as tools.
* **Data store** — a Python library over SQLite, independent of MCP so that it
  can be tested and reused on its own.
* **Skill** — `src/rage/skills/rage/SKILL.md`, initially for Claude Code,
  covering when to store and retrieve and what key conventions to follow. It
  ships inside the package so that an install carries it. `SessionStart` and
  `PreCompact` hooks in `.claude/settings.json` cover the two moments a skill
  would not be reached for on its own.

## Development

```sh
conda env create -f environment.yml   # or: conda create -n rage -c conda-forge python=3.14
conda activate rage
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
```

The store lives in a directory given to the server by `--dir` or `RAGE_DIR`,
defaulting to `./.rage/` in the working directory. See
[design.md](design.md#store-location).

`.mcp.json` registers the server for this project. Its `command` is an absolute
path into the conda environment, so it is specific to the machine it was written
on; adjust it after creating the environment elsewhere.
