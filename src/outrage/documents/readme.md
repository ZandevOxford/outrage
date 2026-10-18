# Outrage

This is the documentation for Outrage, an MCP RAG store.

It is available in the Outrage repository and Python distribution, and is also
mounted by default under the `outrage` key in the Outrage store.

If you are an LLM reading this because you do not have a configured readme
file, then read the `default_readme` file next to this file and ask the user
if they want the same conventions added to the store's readme for this
project. When reading files from the store, drop the `.md` extension.

If reading this via the MCP server,
`get_documents(key="outrage", meta_name=["title"])` will list all the titles.

## Guides

How to do things with Outrage, a topic at a time.

* [Getting started](guides/getting-started.md) - installing Outrage and
  setting up a first project.
* [Setting up projects](guides/setting-up-projects.md) - what `outrage init`
  writes, its options, and the conventions in a store's readme.
* [Mounting data stores](guides/mounting-data-stores.md) - the mount table,
  the kinds of store, and adding one to the namespace.
* [Importing documents](guides/importing-documents.md) - bringing files,
  office documents and agent-written notes into a store, and packing a
  reference base.
* [Export and backup](guides/export-and-backup.md) - copying a store safely,
  and writing one out as files.
* [Parquet stores](guides/parquet-stores.md) - packing and mounting read-only
  reference material.
* [Postgres](guides/postgres.md) - a store shared between devices.
  Experimental.
* [Smart search](guides/smart-search.md) - finding documents by meaning.
  Experimental.
* [workflow](workflow.md) - advice for LLMs for surveying, recording,
  editing and handing over work in a project store.
* [keys](keys.md) - detailed definition of keys. The short version;
  [design](design.md) argues it.
* [importers](importers.md) - separate distributions that turn an outside
  source into a store Outrage can mount. Only the MediaWiki importer so far.

## Reference

* [cli](cli.md) - the command line.
* [tools](tools.md) - descriptions and schemas of the MCP tools.
* [reference](reference.md) - the API reference. The [reference](reference)
  folder contains the detailed pages generated from the code.
* [default_readme](default_readme.md) is a default readme suggesting a project
  structure.
* [home_readme](home_readme.md) is the smaller counterpart for the shared home
  store.
* [project files](project.md) - copies of the repository README, licence and
  changelog that correspond to this installed documentation.

## Background

* [design](design.md) - why outrage is built the way it is. The components,
  the key namespace and its grammar, what text is and how it is encoded, the
  tool semantics and the schema, with the reasoning and the roads not taken.
* [requirements](requirements.md) - the short human-readable requirements that
  the design and implementation satisfy.
* [implementation](implementation.md) - what is built and what is left, stage
  by stage. A snapshot of the project's own progress rather than a manual.
* [development](development.md) - the development environment, and the store
  directory, mounts and logging a checkout runs with. About outrage's
  development rather than its use.

## Documentation used at runtime

* [agents](agents.md) contains the procedures read by harness-specific agents.
* [hooks](hooks.md) contains the prompts emitted by lifecycle-hook commands.
* [instructions](instructions/instructions.md) contains the server's
  instructions, kept as a document rather than inline in the server: read
  `outrage/instructions/instructions` there for the whole of what a client may
  have cut short.
* [smart-search](smart-search/readme.md) contains the tuning smart search
  runs with, `tuning`, and a `readme` saying what each part of it means and
  how to tune it.
* [tools](tools.md) contains the documents that the MCP server sends as tool
  descriptions.

## What this is not

This is **not** the project's own store. Everything outside `outrage/` is the
store this project keeps for itself: its decisions, its findings, where the work
got to. This mount answers for outrage the tool; the root store answers for your
work.

It is also not writable. Every write routed here is refused before it reaches
the store, because it lives in the installation and would be replaced by the
next upgrade.

## Turning it off, or replacing it

`--unmount outrage` on either front end leaves it out. Mounting your own store
at `outrage` replaces it silently, by the ordinary rule that a later source
wins - so a project that would rather keep its own notes there can.

The MCP server mounts this without being asked; the `outrage` command line does
not, unless `--mount-docs` asks for it.
