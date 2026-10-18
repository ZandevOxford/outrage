# Getting started

Outrage gives a coding agent a memory: a store of documents under
hierarchical keys, served over MCP, that persists between sessions and is
shared between harnesses - Claude Code, Codex, Cursor and Copilot CLI.

## Install

Outrage needs Python 3.12 or later.

`pip install "outrage[all]"`

`all` brings in every optional backend and document reader. A plain
`pip install outrage` leaves them out, which is enough for a store that only
ever holds session context. The extras one at a time:

* `parquet` - read-only Parquet stores, for large reference material.
  [Parquet stores](parquet-stores.md).
* `postgres` - the experimental PostgreSQL store shared between devices.
  [Postgres](postgres.md).
* `documents` - converting PDF, Word, PowerPoint and Excel files to Markdown
  with `outrage ingest`.

## Set up a project

From the root of the project:

`outrage init`

That writes everything a harness needs: the MCP server entry, a session-start
hook for each harness, and the packaged skills and agents. The next session
you start in that directory has the store as its memory.
[Setting up projects](setting-up-projects.md) says what is written where, and
how to change it.

The store itself is created on first use, at `.outrage/store.sqlite` in the
project.

## What a session sees

The MCP server mounts three things by default:

* the **project store** at the root of the namespace - this project's own
  decisions, findings and state;
* this **documentation**, read-only, at `outrage`;
* a writable **home store** at `home`, kept in `~/.outrage/home.sqlite` and
  shared by every project for this user.

The session-start hook tells the agent to read the store's `readme` first. A
new store has none, so the agent reads `outrage/default_readme` instead and
offers to adopt its conventions. [Setting up projects](setting-up-projects.md)
covers that readme.

## Looking at the store yourself

The `outrage` command reads and writes the same store from a shell:

```text
outrage ls                 # the top level
outrage get readme         # one document
outrage dump context/12    # everything under a key
outrage set notes/idea < idea.md
```

`outrage info` reports what is answering: the version, the environment, the
store directory and every mount. The [command line](../cli.md) has the rest.

## Where next

* [Mounting data stores](mounting-data-stores.md) - adding further stores to
  the namespace.
* [Export and backup](export-and-backup.md) - copying a store safely.
* [Keys](../keys.md) - the grammar of the namespace.
