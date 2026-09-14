# Development

Outrage itself has been developed using Outrage as a memory store.

As a test of that functionality, development has spanned multiple LLM harnesses
and models: Claude Code, Codex and Copilot CLI.

## Development environment

```sh
conda env create -f environment.yml   # or: conda create -n outrage -c conda-forge python=3.12
conda activate outrage
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
omnidep --project pyproject.toml src/outrage
```

The stores live in a directory given to the server by `--dir` or `OUTRAGE_DIR`,
defaulting to `./.outrage/` in the working directory, each as a file inside it:
`--root-mount FILE` names the one answering for everything (default
`store.sqlite`) and `--mount KEY=FILE` mounts another under a key. A store file
is always relative to the directory, so only `--dir` is a path. See
[the design](design.md#store-location).

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

`outrage get`, `set`, `ingest`, `make_contents`, `ls`, `dump`, `copy`, `rm`,
`export` and `import` all take the mount options, so a person sees the same
namespace the MCP server serves.
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
