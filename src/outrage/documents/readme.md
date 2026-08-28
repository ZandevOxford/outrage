# The outrage manual, as documents

You are reading a store. It ships inside the `outrage` package, is mounted
read-only at `outrage`, and holds what outrage itself has to say about how it
works - so the manual is reached the same way anything else is, with
`retrieve_document` and `get_documents`, and there is no second retrieval path
to learn.

## What is here

* `outrage/keys` - what a key is: the grammar, metadata, `?` and `?last`.
* `outrage/tools` - the tool surface, and which one answers which question.
* `outrage/cli` - the `outrage` command, for the shell rather than the tools.
* `outrage/conventions` - what is worth storing, and where to put it.

`get_documents(key="outrage", meta_name=["title"])` surveys the lot in one call.

## What this is not

It is **not** the project's own store. Everything outside `outrage/` is the
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
