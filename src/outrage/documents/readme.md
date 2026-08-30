# Outrage

This is the documentation for Outrage, a MCP RAG store.

This is available in the Outrage repo, the python build and also by default
under the 'outrage' key in the Outrage store.

If you are an LLM reading this because you do not have a configured readme
file, then read the 'default_readme' file next to this file and ask the user
if they want the same conventions added to the store's readme for this
project. When reading files from the store, drop the '.md' extension.

If reading this via the MCP server,
`get_documents(key="outrage", meta_name=["title"])` will list all the titles.

## Documentation

At this level:

* [keys](keys.md) contains the definition of keys.
* [cli](cli.md) contains the documentation for the command line.
* [workflow](workflow.md) contains detailed advice for surveying, recording,
  editing and handing over work in a project store.
* [reference](reference.md) contains the API documentation, generated from the
  source, with a page per module below it.
* [agents](agents.md) contains the canonical search, annotation and backfill
  procedures shared by the harness integrations.

## Documentation used by the MCP server

* [default_readme](default_readme.md) is a default readme suggesting a project
  structure.
* [skills](skills.md) is the text the MCP server sends as its instructions when
  a client connects, kept as the two documents it is delivered in rather than
  inline in the server: read `outrage/skills/tail` there for the half a client
  may have cut off before it reached you.
* [tools](tools) are the documents that the MCP server sends as tool descriptions.

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
