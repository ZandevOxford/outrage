# Outrage

A simple RAG (Retrieval-Augmented Generation) system for LLMs, designed to just
work with minimal setup, and provide a memory that interoperates between
coding harnesses such as Claude Code, Codex, Cursor, and Copilot CLI.

## Features

* Simple to get started with - built in initialisation configures everything.
* Hierarchical key based store of data and arbitrary metadata.
* Search by exact text, by metadata, or optionally by meaning with a small
  classification model that screens title, keywords, summary, contents and
  body in turn. Search by meaning is experimental.
* Multiple data stores including parquet based stores for large-scale reference
  material, and an experimental PostgreSQL store shared by several devices.
* Explicit support for command-line coding agents: Claude Code, OpenAI Codex
  CLI, Cursor Agent, and GitHub Copilot CLI.
* Command line tools for manipulating the data stores.

## Getting started

Set up a 3.12 or later Python environment, then:

`pip install "outrage[all]"`

To set up a project to use Outrage, change directory to the root of the project
and run:

`outrage init`

And that's it. That will set up the MCP server, tools, skills, agents and hooks
such that when you run your LLM harness the agent will use the Outrage store
as a memory. [Getting started](src/outrage/documents/guides/getting-started.md)
has more.

## Guides

* [Getting started](src/outrage/documents/guides/getting-started.md)
* [Setting up projects](src/outrage/documents/guides/setting-up-projects.md)
* [Mounting data stores](src/outrage/documents/guides/mounting-data-stores.md)
* [Importing documents](src/outrage/documents/guides/importing-documents.md)
* [Export and backup](src/outrage/documents/guides/export-and-backup.md)
* [Parquet stores](src/outrage/documents/guides/parquet-stores.md)
* [Postgres](src/outrage/documents/guides/postgres.md) - experimental.
* [Smart search](src/outrage/documents/guides/smart-search.md) - experimental.

## Documentation

All of it is in `src/outrage/documents`, a documentation tree written to be read
*through the store*: it ships in the wheel, and the MCP server mounts it
read-only at the `outrage` key, so a session reads the manual with the same
tools it reads everything else with. It is ordinary markdown as well, so the
links here work too.

* **[the documents](src/outrage/documents/readme.md)** - the top of that tree,
  and where to start. The guides, keys, the command line, the tools and the
  conventions all hang off it.
* **[the command line](src/outrage/documents/cli.md)** and
  **[the MCP tools](src/outrage/documents/tools.md)** - the reference for each
  front end.
* **[the design](src/outrage/documents/design.md)** - why Outrage is built the
  way it is.
* **[development](src/outrage/documents/development.md)** - the development
  environment, for working on Outrage itself.
