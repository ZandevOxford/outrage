# Outrage

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
also use `?` in place of a segment - storing at `tmp/?` writes to `tmp/1`, and
the store reports the key it chose.

## Purpose

To provide a hierarchical RAG (Retrieval-Augmented Generation) MCP store to use
with LLM based tools.

## Features

* Simple to get started with - built in initialisation configures everything.
* Hierarchical store of data and metadata.
* LLM search - LLM subagents add summary metadata to documents, and LLM subagents can
  search documents and metadata.
* Multiple data stores including parquet based stores for large-scale reference material.

## Status

The store, the MCP server, the key handling, the skill and the command line tool
are implemented. The tool covers the store operations (`outrage get`, `set`,
`ls`, `dump`, `rm`), bulk export and import to a directory of files (`outrage
export`, `outrage import`), building a read-only parquet store (`outrage pack`),
the MCP configuration (`outrage config`), a verified backup (`outrage backup`),
the event log (`outrage log`), and setting a project up (`outrage init`). See
[implementation.md](implementation.md) for what is done and what is next.

`outrage init` is the way in: run it in a project and it registers the MCP
server, installs the `SessionStart` hook, and copies the skill and the agents
into `.claude/`. It writes only the entries outrage owns, leaves the rest of
those files alone, and is safe to re-run - which is how a project is repaired
after an upgrade or after the environment moves. `--dry-run` reports what it
would change without writing.

## Documentation

* **[design.md](design.md)** - the design. Components, the key namespace and its
  grammar, tool semantics, and the SQLite schema. Decisions that are deferred or
  still open are recorded at the end.
* **[implementation.md](implementation.md)** - what is implemented so far, and
  the planned build order.

## Components

* **MCP server** - Python, stdio, for local use. Exposes the store as tools.
* **Data store** - a Python library, independent of MCP so that it can be tested
  and reused on its own. One interface with three backends behind it, and which
  one a store *file* uses follows from its extension. **SQLite** is the
  read-write default: a store accumulated a document at a time, which is what
  session context and notes on a codebase are. **Parquet** is one columnar file,
  written whole by `outrage pack` and read many times, for a reference base of
  tens of thousands of documents - 11× smaller than the same corpus in SQLite,
  and it seeks a range rather than scanning one. It refuses writes, which is the
  storage rather than a setting. **Files** is a directory with one file per key,
  which is what `outrage export` already wrote: the tree a person edits by hand,
  readable as a store rather than only as a transfer.
* **Skill** - `src/outrage/skills/outrage/SKILL.md`, initially for Claude Code,
  covering when to store and retrieve and what key conventions to follow. It
  ships inside the package so that an install carries it, and `outrage init`
  copies it into a project. A `SessionStart` hook in `.claude/settings.json`,
  installed by the same command, covers the moment a skill would not be reached
  for on its own.
* **Event log** - an optional JSON lines record of the requests made and the
  store accesses beneath them, for answering afterwards what a session actually
  did. Off unless `outrage config --log` or `outrage-server --log` asks for it.
* **Backup** - `outrage backup` copies the database through SQLite and checks
  what it wrote. In the library rather than the tool, because a store in WAL
  mode keeps recent writes in a sidecar file and copying the `.sqlite` alone
  yields a near-empty database that still opens cleanly.

## Development

```sh
conda env create -f environment.yml   # or: conda create -n outrage -c conda-forge python=3.14
conda activate outrage
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
```

The stores live in a directory given to the server by `--dir` or `OUTRAGE_DIR`,
defaulting to `./.outrage/` in the working directory, each as a file inside it:
`--root-mount FILE` names the one answering for everything (default
`store.sqlite`) and `--mount KEY=FILE` mounts another under a key. A store file
is always relative to the directory, so only `--dir` is a path. See
[design.md](design.md#store-location).

A table is usually written down rather than typed, in `mounts.toml` inside that
directory, and read by the server and by the command line alike:

```toml
# Every FILE is relative to this directory, the one --dir names.
root-mount = "store.sqlite"

[mount]
team = "team.sqlite"          # read-write

[mount-ro]
ref = "reference.sqlite"      # writes here are refused
```

The file behaves as if its options had been typed at the point where it is
named, so anything on the command line comes after it and wins - and a mount
named again *replaces* the one in the file rather than colliding with it, which
is how a committed table gets one entry overridden for a single run.
`--mount-config FILE` reads another file where the flag appears;
`--unmount KEY` removes one the file declares, which is the one thing an
override cannot do; `--no-mount-config` ignores the default file entirely.

`outrage get`, `set`, `ls`, `dump`, `rm`, `export` and `import` all take the
mount options, so a person sees the same namespace the MCP server serves.
`outrage check` and `backup` are about one file and say which with `--store`.

`outrage-server --log` records requests and store accesses as JSON lines, by
default in `log.jsonl` beside the store. It is off otherwise, since it records
document text. `--log-content none|excerpt|full` controls how much of that text
it keeps.

`.mcp.json` registers the server for this project. Its `command` is an absolute
path into the conda environment, so it is specific to the machine it was written
on; adjust it after creating the environment elsewhere.
