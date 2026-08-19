# Rage

A simple retrieval system for coding agents: an MCP server, a data store, and
skills that let an agent keep notes, designs and task context in a store local
to the project it is working on.

Retrieval is by key rather than by similarity. Keys are hierarchical, slash
delimited strings such as `context/<guid>/design`, and any key may carry
metadata such as `context/<guid>/design/!title`. Since an agent knows the keys it
wrote, lexical addressing is enough, and the system stays deterministic and free
of external dependencies. Semantic search is a possible later addition, layered
on as metadata rather than as a change to the model.

Keys are not paths, but they are shaped like them, so a key can mirror one:
`notes/src/myfile.py` for notes about a source file. A key being written may
also use `?` in place of a segment — storing at `tmp/?` writes to `tmp/1`, and
the store reports the key it chose.

## Status

The store, the MCP server, the key handling, the skill and the command line
tool are implemented. The tool covers the store operations (`rage get`, `set`,
`ls`, `dump`, `rm`), bulk export and import to a directory of files (`rage
export`, `rage import`), the MCP configuration (`rage config`), a verified
backup (`rage backup`), the event log (`rage log`), and setting a project up
(`rage init`). See [implementation.md](implementation.md) for what is done and
what is next.

`rage init` is the way in: run it in a project and it registers the MCP server,
installs the `SessionStart` hook, and copies the skill and the agents into
`.claude/`. It writes only the entries rage owns, leaves the rest of those files
alone, and is safe to re-run — which is how a project is repaired after an
upgrade or after the environment moves. `--dry-run` reports what it would
change without writing.

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
  ships inside the package so that an install carries it, and `rage init`
  copies it into a project. A `SessionStart` hook in `.claude/settings.json`,
  installed by the same command, covers the moment a skill would not be reached
  for on its own.
* **Event log** — an optional JSON lines record of the requests made and the
  store accesses beneath them, for answering afterwards what a session actually
  did. Off unless `rage config --log` or `rage-server --log` asks for it.
* **Backup** — `rage backup` copies the database through SQLite and checks what
  it wrote. In the library rather than the tool, because a store in WAL mode
  keeps recent writes in a sidecar file and copying the `.sqlite` alone yields a
  near-empty database that still opens cleanly.

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

`rage-server --log` records requests and store accesses as JSON lines, by
default in `log.jsonl` beside the store. It is off otherwise, since it records
document text. `--log-content none|excerpt|full` controls how much of that text
it keeps.

`.mcp.json` registers the server for this project. Its `command` is an absolute
path into the conda environment, so it is specific to the machine it was written
on; adjust it after creating the environment elsewhere.
