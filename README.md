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
* Explicit support for command-line coding agents: Claude Code, OpenAI Codex
  CLI, and GitHub Copilot CLI.

## Status

The store, the MCP server, the key handling, the skill and the command line tool
are implemented. The tool covers the store operations (`outrage get`, `set`,
`ls`, `dump`, `copy`, `rm`), bulk export and import to a directory of files
(`outrage export`, `outrage import`), building a read-only parquet store
(`outrage pack`),
the MCP configuration (`outrage config`), a verified backup (`outrage backup`),
the event log (`outrage log`), and setting a project up (`outrage init`). See
[implementation.md](implementation.md) for what is done and what is next.

`outrage init` is the way in: run it in a project and it registers the MCP
server, installs the Claude Code skill, agents and `SessionStart` hook, installs
the project skill for OpenAI Codex CLI, and installs the session-start hook for
GitHub Copilot CLI. Outrage explicitly supports these command-line clients; it
does not claim integrations with similarly named desktop, web or IDE products.
It writes only the entries outrage owns, leaves the rest of those files alone,
and is safe to re-run - which is how a project is repaired after an upgrade or
after the environment moves. `--dry-run` reports what it would change without
writing.

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
* **Client integrations** - packaged project skills for Claude Code and OpenAI
  Codex CLI, plus session-start hooks for Claude Code and GitHub Copilot CLI.
  They cover when to store and retrieve, the key conventions, and the moment a
  skill would not be reached on its own. `outrage init` installs each client's
  files without replacing configuration it does not own.
* **Event log** - an optional JSON lines record of the requests made and the
  store accesses beneath them, for answering afterwards what a session actually
  did. Off unless `outrage config --log` or `outrage-server --log` asks for it.
* **Backup** - `outrage backup` copies the database through SQLite and checks
  what it wrote. In the library rather than the tool, because a store in WAL
  mode keeps recent writes in a sidecar file and copying the `.sqlite` alone
  yields a near-empty database that still opens cleanly.

## Development

```sh
conda env create -f environment.yml   # or: conda create -n outrage -c conda-forge python=3.12
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
docs = { path = "docs", type = "files" }   # a directory of files

[mount-ro]
ref = "reference.sqlite"      # writes here are refused
```

An entry is a store file, or a table saying more about one. `type` is which
backend keeps it - `sqlite`, `parquet` or `files` - and it is needed only where
the name cannot say: a directory of files has no extension to read. The same
option is written after a comma when it is typed, as `--mount
docs=docs,type=files` or `--store docs,type=files`, so one mount is still one
argument and overriding an entry still replaces it whole.

The file behaves as if its options had been typed at the point where it is
named, so anything on the command line comes after it and wins - and a mount
named again *replaces* the one in the file rather than colliding with it, which
is how a committed table gets one entry overridden for a single run.
`--mount-config FILE` reads another file where the flag appears;
`--unmount KEY` removes one the file declares, which is the one thing an
override cannot do; `--no-mount-config` ignores the default file entirely.

`outrage get`, `set`, `ls`, `dump`, `copy`, `rm`, `export` and `import` all take
the mount options, so a person sees the same namespace the MCP server serves.
`outrage copy SOURCE TARGET` copies a subtree or key-order range beneath another
prefix in that namespace, including between mounted stores; `--reroot` lands it
*at* TARGET instead of beneath its own source key, which is what moving a
subtree to another key needs.
`outrage check` and `backup` are about one file and say which with `--store`.

Outrage ships its own documentation as a store inside the package - a readme,
and documents on keys, the tools, the command line and the conventions - mounted
read-only at `outrage`. The MCP server mounts it unless told otherwise, so a
session reads the manual with the same tools it reads everything else; the
command line does not, unless `--mount-docs` asks for it, so a bare `outrage`
stays a clean namespace over the project's own store. It behaves as an ordinary
mount otherwise: `--unmount outrage` leaves it out, and mounting your own store
at `outrage` replaces it by the same rule that overrides any other entry.

`outrage mounts` reports the table a command line would open, without opening
any of it — which matters because opening a read-write mount is what *creates*
it, so a mistyped name becomes an empty store that reads like one with nothing
in it yet:

```
$ outrage mounts
/     store.sqlite      root             ok            default
notes notez.sqlite      mount            would create  the command line
ref   reference.sqlite  read-only mount  ok            .outrage/mounts.toml
```

It takes every option the other commands take, so it answers for the line you
would really run, and the last column says which source won.

`outrage init --mount KEY=FILE` and `outrage config --mount KEY=FILE` write
that file, commented, when a project has none - and never rewrite one, since a
rewrite is what would lose the comments. A run naming a mount an existing table
does not hold prints the lines to add instead. So `.mcp.json` carries `--dir`
and nothing else; an entry written by an earlier release keeps its `--mount`
arguments and goes on working, and `outrage config` says they are there.

`outrage-server --log` records requests and store accesses as JSON lines, by
default in `log.jsonl` beside the store. It is off otherwise, since it records
document text. `--log-content none|excerpt|full` controls how much of that text
it keeps.

`.mcp.json` registers the server for this project. Its `command` is an absolute
path into the conda environment, so it is specific to the machine it was written
on; adjust it after creating the environment elsewhere.
