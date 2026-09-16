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

## Documentation

* [agents](agents.md) - canonical procedures shared by the harness
  integrations.
* [cli](cli.md) - the command line.
* [default_readme](default_readme.md) is a default readme suggesting a project
  structure.
* [home_readme](home_readme.md) is the smaller counterpart for the shared home
  store.
* [design](design.md) - why outrage is built the way it is. The components,
  the key namespace and its grammar, what text is and how it is encoded, the
  tool semantics and the schema, with the reasoning and the roads not taken.
* [development](development.md) - the development environment, and the store
  directory, mounts and logging a checkout runs with. About outrage's
  development rather than its use.
* [hooks](hooks.md) - the harness hooks.
* [implementation](implementation.md) - what is built and what is left, stage
  by stage. A snapshot of the project's own progress rather than a manual.
* [importers](importers.md) - separate distributions that turn an outside
  source into a store Outrage can mount. Only the MediaWiki importer so far.
* [instructions](instructions/instructions.md) - the text the MCP server
  delivers to every session when a client connects.
* [keys](keys.md) - detailed definition of keys. The short version;
  [design](design.md) argues it.
* [project files](project.md) - copies of the repository README, licence and
  changelog that correspond to this installed documentation.
* [reference](reference.md) - the API reference. The [reference](reference)
  folder contains the detailed pages generated from the code.
* [requirements](requirements.md) - the short human-readable requirements that
  the design and implementation satisfy.
* [tools](tools.md) - descriptions and schemas of the MCP tools.
* [workflow](workflow.md) - advice for LLMs for surveying, recording,
  editing and handing over work in a project store.

## Documentation used at runtime

* [agents](agents) contains the procedures read by harness-specific agents.
* [hooks](hooks) contains the prompts emitted by lifecycle-hook commands.
* [instructions](instructions) contains the server's instructions, kept as a
  document rather than inline in the server: read
  `outrage/instructions/instructions` there for the whole of what a client may
  have cut short.
* [tools](tools) contains the documents that the MCP server sends as tool
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
