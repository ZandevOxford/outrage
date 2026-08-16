# Implementation

## Currently implemented

Environment: conda environment `rage`, Python 3.14.6, SQLite 3.53.4. Package
installed in editable mode with `pip install -e ".[dev]"`. 177 tests passing;
`ruff check` and `ruff format --check` clean.

### 0. Project scaffolding — done

`pyproject.toml` with a hatchling build, package under `src/rage/`, a
`rage-server` console script, and `pytest` and `ruff` as development
dependencies.

### 1. Key handling — `src/rage/keys.py` — done

Parses and validates keys against the grammar, splits the metadata suffix, and
derives `doc_key`, `meta_name` and `parent`. Also `ancestors`, `depth`,
`subtree_range`, and the `?` wildcard: `parse` accepts one only when asked, so
reads and deletes reject it rather than treating it as a pattern.

`subtree_range` returns half open bounds rather than a `LIKE` prefix, for two
reasons: `_` is legal in a segment but is a `LIKE` wildcard, and a prefix match
would let `a/b` pick up `a/beta`. Everything under `a/b` sorts within
`["a/b/", "a/b0")` because `/` and `0` are adjacent code points, so subtree
scans stay exact index range scans no matter what a segment may contain.

### 2. Data store — `src/rage/store.py` — done

Directory resolution, schema creation and migration under `PRAGMA user_version`,
WAL mode, and all five operations with the semantics recorded in design.md. No
MCP dependency.

Formats are detected: content that parses as a JSON object or array is recorded
as `json`, everything else as `markdown`, and an explicit argument overrides
both.

`store_document` returns the key it wrote, which is how a caller learns the
number allocated for a `?` segment. Allocation reads before it writes, so that
path runs in an immediate transaction; concurrent writers block rather than
picking the same number. Its optional `title` writes the `:title` metadata in
the same transaction, after any wildcard has been resolved.

`descendant_count` and `keys_missing_meta` exist to let a caller report what a
result does *not* contain: what a non-recursive delete kept, and what a survey
by metadata could not see. Both were added in step 4.

Schema 2 changed the delimiter from `.` to `/`. Opening a schema 1 store
rewrites its keys in place — exact, because no schema 1 segment could contain
either character.

### 3. MCP server — `src/rage/server.py` — done

Stdio server built on `MCPServer` from the MCP Python SDK, exposing
`retrieve_document`, `store_document`, `list_keys`, `get_documents` and
`delete_keys`. Argument shaping and result shaping only; all behaviour lives in
the store. Argument constraints are declared with pydantic `Field`, so bad
arguments are rejected before reaching the store, and read only and destructive
tool annotations are set.

Tested through the server's own tool dispatch rather than by calling the
functions directly, so the generated schemas and the error paths are covered.

Note the SDK in use is **mcp 2.0**, where `FastMCP` has become
`mcp.server.MCPServer`, model fields are snake_case (`is_error`,
`structured_content`, `input_schema`), and a failing tool raises `ToolError`
rather than returning a result with an error flag.

## TODO

### 4. Integration with Claude Code — done

* `.mcp.json` written, registering the server for this project. Its `command` is
  an absolute path into the conda environment and so is machine specific.
* The server has been exercised end to end over stdio by an MCP client: tool
  listing, store, survey by `:title`, read and recursive delete.
* Used from a real Claude Code session, which is what turned up the six points
  below. Everything worked; what went wrong was that five results were
  misleading and one convention was too easy to skip.
* The five fixed points were then confirmed live against the reconnected
  server, so they are known to work through the protocol and not only in the
  tests.

#### Getting a changed server to the agent

Reconnecting the server with `/mcp` and restarting the session are **not**
equivalent, and the difference is worth knowing when iterating on the server
from inside a session:

* *Reconnecting* restarts the server process and refreshes the tool list. New
  code, new arguments, new tool descriptions and new result shapes all take
  effect, verified here by calling every one of the five changes below.
* *The server's `instructions`* are delivered once and stayed at the old text
  across the reconnect. They reached the agent only on a full session restart.

So a reconnect is enough while changing tools, and only a change to
`instructions` needs the session restarted. That matters because `instructions`
is where the key conventions live, which is exactly what step 5 will be
iterating on — the slow loop is the one that step is stuck with.

#### What the session use changed

1. *A non-recursive delete of a key with descendants was a silent no-op.*
   `delete_keys(key="context/2")` returned `{"deleted": [], "count": 0}` — the
   same shape as a successful delete of an empty key — while the whole context
   survived. Read as success, and the mistake is invisible. The result now
   carries `remaining` and a note naming the flag. New `Store.descendant_count`.

2. *Reading a container and reading a missing key gave the same error.* Both
   said `no content stored at X`, so a correct key aimed at a container looked
   like a wrong key. Now distinguished, and the container case points at
   `list_keys`. Deliberately not applied to a metadata key, whose `doc_key`
   descendants say nothing about whether the metadata exists.

3. *A survey by `:title` silently omitted untitled documents.* Storing four
   documents and surveying titles returned three, with nothing to say the
   fourth existed. The survey now reports `without_meta`. New
   `Store.keys_missing_meta`.

4. *Titling a document was a second call that is easy to forget* — forgotten
   once in this session despite the instructions pushing it. `store_document`
   now takes `title` and writes both rows in one transaction.

5. *The invalid segment error did not say what a segment may contain*, leaving a
   caller to guess. It now names the character set.

6. *Unknown arguments were accepted and silently dropped.* Found by calling the
   new `title` argument against the server still running the old code: the call
   succeeded, reported success, and wrote no title. The same failure as 1 to 3
   and the worst of them, since it makes a stale server indistinguishable from
   a current one.

   The cause is in the SDK, not here: `ArgModelBase` in
   `mcp/server/mcpserver/utilities/func_metadata.py` leaves pydantic's default
   `extra="ignore"`, and arguments are filtered before a tool function is
   entered, so a tool cannot see what was dropped. There is no per-tool strict
   flag, and the middleware hook that might have served is documented as
   unstable before v2 is final.

   Fixed by `server._forbid_unknown_arguments`, which sets `extra="forbid"` on
   that config at import, before any tool is registered. One line, and it buys
   both halves: the SDK now rejects the call *and names the offending argument*,
   and `additionalProperties: false` appears in all five published schemas, so a
   validating client catches the mistake before calling.

Worth noting that five of the six are about result *shapes* rather than
behaviour, and four are the same failure: a result that cannot distinguish
"nothing happened" from "it worked". Tool results are read by something that
cannot see the store, so anything the result does not say is not merely absent,
it is misleading.

The reach into the SDK for point 6 is deliberate but load bearing, so it is
guarded rather than trusted. Four tests in `test_server.py` — the rejection, the
named misspelling, the published `additionalProperties`, and that known
arguments still pass — fail if a future SDK stops honouring it. Verified by
disabling the call and confirming three of them fail; a silent return to
permissive arguments is the one outcome that must not be possible, since it is
the failure the change exists to prevent.

### 5. Skills — done

Expected to be the hardest part and the one that determines whether the system
is actually used in practice; deliberately last, so it could be written against
tools whose behaviour was already known.

* `src/rage/skills/rage/SKILL.md` — the skill. Inside the package rather than
  only in the repository, so an install carries it and the CLI has something to
  install.
* `.claude/skills/rage` — a relative symlink to it, so this project uses the
  copy it is editing.
* `.claude/settings.json` — `SessionStart` and `PreCompact` hooks.
* `tests/test_skill.py` — the skill is packaged, its frontmatter names it, and
  the symlink still resolves to the packaged file.

The skill carries only judgment: survey before reading, what the three key
namespaces are for, what is worth storing and what the repository already
records, storing as the work goes rather than at the end, and what to check
before the end. It deliberately does not restate the key grammar or the argument
rules, which the tool descriptions carry and enforce.

The hooks exist because a skill has to be reached for, and the two moments that
matter most — the start of a session, and just before context is lost — are not
moments anything prompts an agent to reach. Both hooks emit static text and
depend on nothing, so neither can fail in a way that costs a session.

#### What is not yet confirmed

Both hooks were pipe tested: each emits valid JSON carrying
`hookSpecificOutput.additionalContext`. Neither can be fired from within the
session that wrote it, so what is confirmed is the output, not the delivery.
Three things a later session should check, in the order they will show up:

1. Whether the skill is listed at all, which is the test of whether a symlinked
   skill directory is discovered. If it is not, replace the symlink with a copy
   and let the CLI own keeping them in step with each other.
2. Whether the `SessionStart` text arrives in context.
3. Whether the `PreCompact` text arrives anywhere the model can still act on —
   the least certain of the three, since compaction is not a turn.

Also worth noting that `.claude/settings.json` did not exist when this session
started, so the hooks needed `/hooks` or a restart before taking effect here.

### 6. Command line tool — next

* A CLI over the store library, covering the same operations as the MCP server
  plus bulk import and export, a command that writes the MCP server
  configuration for a project, and a command that installs the skill and hooks
  into a project.

Deliberately after the skills: bulk import is most useful once the key
conventions the skills establish are settled, since an import has to choose keys
for whatever it ingests. Those conventions now exist, so the ordering constraint
is discharged.

Installing the skill is new to this step, and belongs with the configuration
writing rather than with the server: both are things a user runs deliberately,
which is the distinction design.md draws when it defers letting the server edit
local configuration.

The configuration writing command is the exception and could be pulled forward
at any point, since it depends on nothing else and replaces the hand written
`.mcp.json` currently in the repository.

## Not planned yet

Recorded in the Deferred section of design.md rather than here, since none of it
is scheduled: versioning, semantic search, Unicode keys, and bootstrapping the
skill configuration from the server.
