# Setting up projects

`outrage init`, run from a project's root, is all most projects need. This
guide says what it writes, how to change that, and how to give the store
conventions an agent will follow.

## What `init` writes

* **The MCP server entry** - in `.mcp.json`, `.codex/config.toml` for Codex and
  `.cursor/mcp.json` for Cursor. It carries the absolute path to this
  environment's server and to the store directory.
* **A session-start hook** for each harness - `.claude/settings.json`,
  `.github/hooks/outrage.json`, `.codex/hooks.json` and `.cursor/hooks.json`.
  It tells each new session to read the store's `readme`.
* **The packaged skills and agents** - in `.claude/`, `.github/agents/` and
  `.codex/`. They cover when to store and retrieve, and searching and
  annotating the store.
* **The mount table**, `mounts.toml` in the store directory, if a mount was
  asked for. [Mounting data stores](mounting-data-stores.md).

Only the entries Outrage owns are written; anything else in those files is left
alone. **`init` is safe to re-run**, and re-running it is how a project is
repaired after upgrading Outrage or moving its environment. A packaged skill or
agent you have edited is not replaced unless you pass `--force`, and every such
file is named first.

`outrage init --dry-run` reports what would change without writing anything.

## Choosing options

Options given to `init` are recorded on the server entry:

* `--dir PATH` - keep the store somewhere other than `.outrage/`.
* `--log` - record the server's requests and store accesses as JSON lines,
  read back with `outrage log`. Off by default, since it records document
  text.
* `--no-versioning` - keep no earlier version of what is overwritten or
  deleted. Versioning is on by default in SQLite stores.
* `--no-info`, `--no-remount` - withhold the `info` tool, or the `mount` and
  `unmount` tools, from sessions.
* `--smart-search` - offer the experimental `smart_search` tool.
  [Smart search](smart-search.md).

A re-run adds options but never removes one: taking an option away is an edit
to the configuration file.

`outrage config` writes the server entry alone, without hooks, skills or
agents. `--scope user` writes it to `~/.claude.json` instead of the project.

## The store's readme

A session's first read is the store's `readme`: the conventions for where
things go and how they are written. A new store has none, so the agent reads
[`outrage/default_readme`](../default_readme.md) and asks whether to adopt it.
It suggests a namespace - `current` for where work stands, `context/<n>` for a
thread of work, `plans`, `issues`, `reference` and so on - and practices such
as giving every document a title.

Adopt it, adapt it, or write your own; it is an ordinary document at `readme`.
`outrage set readme < conventions.md` stores one from a file. Advice that
applies to every project belongs in `home/readme` instead.

[Workflow](../workflow.md) has the longer advice for agents working in a
project store.

## Undoing it

`outrage uninit` removes what `init` installed - server entries, hooks, skills
and agents - and nothing else. The store directory is not touched. It refuses,
writing nothing, where removing something would destroy what Outrage did not
write, and names every such case at once.
