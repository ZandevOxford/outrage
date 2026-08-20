# Implementation

## Currently implemented

Environment: conda environment `rage`, Python 3.14.6, SQLite 3.53.4. Package
installed in editable mode with `pip install -e ".[dev]"`. 638 tests and 11
doctests passing, `ruff check` clean, as of 2026-08-20. Doctests are not in
`testpaths` and need a second run: `pytest --doctest-modules src/rage`.
`ruff format --check` reports six files it would reformat and has done for
some time; the project lints and does not enforce the formatter.

### 0. Project scaffolding — done

`pyproject.toml` with a hatchling build, package under `src/rage/`, a
`rage-server` console script, and `pytest` and `ruff` as development
dependencies.

### 1. Key handling — `src/rage/keys.py` — done

Parses and validates keys against the grammar, splits off the metadata segment, and
derives `doc_key`, `meta_name` and `parent`. Also `ancestors`, `depth`,
`subtree_range`, and the `?` wildcard: `parse` accepts one only when asked, so
reads and deletes reject it rather than treating it as a pattern.

`subtree_range` returns half open bounds rather than a `LIKE` prefix, for two
reasons: `_` is legal in a segment but is a `LIKE` wildcard, and a prefix match
would let `a/b` pick up `a/beta`. Everything under `a/b` sorts within
`["a/b/", "a/b0")` because `/` and `0` are adjacent code points, so subtree
scans stay exact index range scans no matter what a segment may contain.

The root, added 2026-08-20, is the key with no segments. It parses, holds a
document, carries metadata as `!title`, and is its own parent. It has no
subtree bounds — everything is beneath it and no string bounds every key from
above — so `subtree_range` **raises** for it rather than returning the
`["/", "0")` the formula would give, which matches nothing at all and would
have read as a confident zero out of a full store. Callers select with no range
predicate instead. `depth` is 0 for it, and `displayed` spells it `/`, because
`""` in a report reads as a missing name rather than as a key.

### 2. Data store — `src/rage/store.py` — done

Directory resolution, schema creation and migration under `PRAGMA user_version`,
WAL mode, and all five operations with the semantics recorded in design.md. No
MCP dependency.

Formats are detected: content that parses as a JSON object or array is recorded
as `json`, everything else as `markdown`, and an explicit argument overrides
both.

A null key means the root wherever a call takes a subtree, resolved once on the
way in so nothing below carries a second spelling of "everywhere". Three shared
query fragments keep the root from needing a branch per caller: `_scope` for
that resolution, `_children_clause` — `parent = ? AND key <> ?` against the
same value, which is what stops the root listing as its own child — and
`_below`. Two `CASE` expressions handle the places SQL recomputes a key
property that the root breaks: the per-row segment count, which would make the
root depth 1, and the synthesised position in `missing_meta_stats`, which is
not the root's sort key plus a suffix because the root contributes no segment.

`store_document` returns the key it wrote, which is how a caller learns the
number allocated for a `?` segment. Allocation reads before it writes, so that
path runs in an immediate transaction; concurrent writers block rather than
picking the same number. Its optional `title` writes the `!title` metadata in
the same transaction, after any wildcard has been resolved.

`descendant_count` and `keys_missing_meta` exist to let a caller report what a
result does *not* contain: what a non-recursive delete kept, and what a survey
by metadata could not see. Both were added in step 4.

Schema 2 changed the delimiter from `.` to `/`. Opening a schema 1 store
rewrites its keys in place — exact, because no schema 1 segment could contain
either character.

`backup` copies the database through SQLite's own backup API and then checks
what came out: `integrity_check`, the schema version, and a row count against
the source. It is here rather than in the CLI because the reason it cannot be a
file copy — WAL mode keeps recent writes in a sidecar, and the `.sqlite` file
alone was observed at 4 KB against a 2 MB WAL — is knowledge this module
already has and no caller should need. A copied file opens cleanly and passes an
integrity check, so the row count is the only check that catches it. The count
is taken after the copy, which means a concurrent write can fail a good backup;
that is preferred to trusting a count nobody took.

### 3. MCP server — `src/rage/server.py` — done

Stdio server built on `MCPServer` from the MCP Python SDK, exposing
`retrieve_document`, `store_document`, `list_keys`, `get_documents`,
`keys_missing_meta` and `delete_keys`. Argument shaping and result shaping
only; all behaviour lives in the store. The three tools taking a scope resolve
an omitted or null key to the root before echoing it, so a result names the
scope that was used rather than the absence the caller sent. Argument constraints are declared with pydantic `Field`, so bad
arguments are rejected before reaching the store, and read only and destructive
tool annotations are set.

Tested through the server's own tool dispatch rather than by calling the
functions directly, so the generated schemas and the error paths are covered.

Note the SDK in use is **mcp 2.0**, where `FastMCP` has become
`mcp.server.MCPServer`, model fields are snake_case (`is_error`,
`structured_content`, `input_schema`), and a failing tool raises `ToolError`
rather than returning a result with an error flag.

### 3a. Mounted stores — `src/rage/mounts.py` — done

More than one database behind the one key namespace, configured at startup with
a repeatable `--mount KEY=FILE`. `Mounts` is a prefix to `Store` table; the
longest prefix matching a key owns it, and the store `--root-mount` names sits
at the root, so every key resolves. `build_server` wraps a lone `Store` in
`Mounts.single`, so there is no second code path that only runs when nothing is
mounted.

**One directory, several files.** A store is addressed as a file *inside* the
directory `--dir` names — `--root-mount FILE` for the root, `KEY=FILE` for each
mount, both defaulting to and named like `store.sqlite`. `store.store_file` is
the single rule and it refuses an absolute path and a `..`, raising
`StoreFileError`; `Store(directory, filename=...)` is the only way a database
path is built. The directory stays what it always was — the log, the backups
and any later index live in it — and the file is which store within it. That
split is what a backend other than SQLite would slot into, and it is why only
`--dir` is absolute in a configuration: `config.server_entry` records every
mount exactly as written, so moving a project is one line to fix rather than
one per store. `rage`'s own subcommands take the same pair, `--dir` and
`--store`.

The two translations are `keys.with_prefix` and `keys.strip_prefix`, in
`keys.py` rather than a module of their own because they are key grammar and
the bound they enforce (`MAX_SEGMENTS`, via `keys.fits`) is already there.
`strip_prefix` matches by segment, not by character: `ref` does not contain
`reference`, and getting that wrong would route a key to a store that has never
heard of it.

The storage layer needed almost nothing: `sort_key` is derived from the key
alone, so rows from different mounts already sort against each other, and
`Store` holds its own `threading.local`, so N stores in one thread is N
connections rather than one shared between them — the concurrency fix spans
mounts without an addition.

It needed one thing, added later: **range bounds**, so that a traversal can
step over the stretch a mount shadows. A subtree read in `Store` is now bounded
by three separate things, all of which must hold, and each is its own argument:

* **`BoundedSubtree(key, depth)`** — which part of the hierarchy to read.
  Measured on `doc_key`, because metadata shares its document's `doc_key`, so
  one predicate takes a document and its metadata together and a metadata key
  has the depth of the document it belongs to. `EVERYTHING` is the default.
* **`KeyRange`** — which stretch of the order to read, measured on `sort_key`.
  Six one-sided bounds, all optional and all ANDed: `after_inclusive`, `after`,
  `after_subtree`, `before`, `before_inclusive`, `final_subtree` — three cuts
  from below and three from above, which is every place a cut can fall relative
  to a key. `KeyRange.clauses(column, column_params)` renders them as SQL, with
  `column` an expression rather than a name. `UNBOUNDED` is the default.
* **`cursor`** — where the last page stopped, on the methods that page,
  including `list_keys`, whose `after` was renamed to it so the store has one
  word for it.

`KeyRange` knows nothing about mounts; `before` and `after_subtree` name the
same key from opposite sides, so a subtree can be cut out without naming a key
that does not exist. A range bounds the **selection**, not the page, so a count
taken over a window counts that window and the windows either side of a mount
add up to the whole — which is exactly why the cursor is *not* one of its
bounds. `BoundedSubtree` is deliberately not expressed as a `KeyRange` either:
a caller must be able to give both, and folding one into the other makes the
pair inexpressible. `missing_meta_stats` therefore takes **two** ranges,
`key_range` measured against a document's own position and `window` against the
position its metadata would have taken, because a document is inside a shadowed
subtree because of where the *document* is. `context/23/decisions/range-types`
in the store has the reasoning, including why `after_inclusive` and
`final_subtree` are kept with no caller. `Store.level_entry` was added with
these: how one key appears in its parent's listing, which is what the level
totals need in order to count a mount point once.

`keys.MAX_SEGMENTS` is **64**, half `keys.MAX_JOINED_SEGMENTS`, and bounds both
a key inside a store and a mount point. That is what makes the join total:
`Mount.outer` returns a `str`, not a `str | None`, and no listing has a drop
path. `keys.parse` defaults to the store bound and takes `max_segments`; the
only callers passing the joined bound are `Mounts.resolve`/`below`/`children`
and the `title_key` the server reports, which are the only places a key
spanning a mount point is seen whole. `rage check` gained `_check_depth` for
keys written before the bound was halved.

The routing lives in the server, which is where the argument and result shaping
already lives. Per tool: `retrieve_document`, `store_document` and
`delete_keys` route to the owning mount and translate; `list_keys` also splices
in the mount points at that level, merging before it cuts, and counts a mount
as *replacing* what it stands in front of rather than joining it;
`get_documents` and `keys_missing_meta` read their store as the windows the
mounts below the key leave between them (`_shadowed`, `_windows`,
`_across_windows`) and report `mounts_not_searched`. One limit and one
character budget are spent across all the windows of a page, the totals are
summed, and `without_meta` is asked once per window over exactly the stretch
the page covered, so a survey's windows still tile as a caller pages. With no
mount below the key there is a single unbounded window, which is the query it
always was. Results grow a field only when there is something to say, so a
single store answer is the shape it was before mounts existed.

**Read-only mounts** — `--mount-ro KEY=FILE`, and `rage config --mount-ro` to
record one. `Mount.read_only` carries it, `Resolved.writable(action)` raises
`ReadOnlyMountError`, and the two write tools resolve through
`_resolve_for_write` rather than `_resolve` so a write path names itself and
cannot pick up the reading one by default. The refusal happens before the store
is called; `Store` is still untouched. A listing reports the mount point as
`kind: "read-only mount"`, which is the only announcement — a `read_only` field
on `Entry` would appear as a null on every entry of every listing. `open_mounts`
refuses a read-only mount whose database does not exist, since `Store` would
otherwise create one, and `server.main` now renders a `RageError` as one line
and exits 1 rather than tracebacking, which is the rule `cli.main` already
followed.

Deliberately not done, and recorded in `project/reference/planned/mounts`:
aggregation across a boundary. The range bounds are the primitive it now needs:
reading a subtree as ordered windows is what a merge across two stores would
interleave. The CLI half is narrower than it was — `rage check`, `rage backup`
and the rest take `--store`, so each store in a directory can be reached by
name — but each command still acts on one store at a time rather than on a
mount table.

### 4. Integration with Claude Code — done

* `.mcp.json` written, registering the server for this project. Its `command` is
  an absolute path into the conda environment and so is machine specific.
* The server has been exercised end to end over stdio by an MCP client: tool
  listing, store, survey by `!title`, read and recursive delete.
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

3. *A survey by `!title` silently omitted untitled documents.* Storing four
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
* `.claude/settings.json` — a `SessionStart` hook. A `PreCompact` hook was
  installed here too until 2026-08-19; see below for why it is gone.
* `tests/test_skill.py` — the skill is packaged, its frontmatter names it, and
  the symlink still resolves to the packaged file.

The skill carries only judgment: survey before reading, what the three key
namespaces are for, what is worth storing and what the repository already
records, storing as the work goes rather than at the end, and what to check
before the end. It deliberately does not restate the key grammar or the argument
rules, which the tool descriptions carry and enforce.

Two hooks were written, because a skill has to be reached for and the two
moments that matter most — the start of a session, and just before context is
lost — are not moments anything prompts an agent to reach. Each emits static
text and depends on nothing, so neither can fail in a way that costs a session.

Only the `SessionStart` half survives. The `PreCompact` hook was removed on
2026-08-19 once it was clear it delivers nothing; the second moment is still
worth reaching, and how to reach it is `planned/checkpoint-hook`.

#### Delivery

Both hooks were pipe tested when written, so what was confirmed then was the
output and not the delivery — neither hook can fire inside the session that
wrote it, and `.claude/settings.json` did not exist when that session started.

All three are now settled. A symlinked skill directory *is* discovered, through
the link rather than its target. The `SessionStart` text *does* arrive in
context ahead of the first turn — 14 sessions out of 14, across the `startup`
and `compact` sources, and a live run in which the model echoed back a token
minted by the hook. And `PreCompact` delivers nothing at all: it produces no
attachment of any kind in the transcript, not even the `hook_success` every
other hook gets, so it is invisible rather than rejected.

The evidence is `tools/harness_delivery.py`, which reads the client's own
transcripts, and the standing answer is `project/reference/harness-delivery` in
the store. It is worth re-running after a client upgrade: a pipe test cannot
see past the process boundary, and this project has now been wrong about that
boundary three times.

### 8. Event log — `src/rage/eventlog.py` — done

Steps 6 and 7 — the CLI and the packaged agents — are recorded in the rage
store under `project/reference/implementation` rather than here.

Off unless `--log` is given, since it records document text. Design and
reasoning in design.md; what it is *for* is that every open question in this
project turned out to need evidence about what an agent actually did, and none
of it was being kept.

* `src/rage/eventlog.py` — the sink. One JSON object per line, written with a
  single `os.write` to an `O_APPEND` descriptor so that two processes sharing a
  log cannot interleave. Content is bounded by a policy, which is also what
  keeps a line short enough for that to hold.
* `src/rage/store.py` — a `_logged` decorator over the seven public methods,
  and a `log` argument defaulting to a null object. Method bodies are
  untouched, so the change that added logging could not have altered
  behaviour.
* `src/rage/server.py` — `RequestLog`, a `ServerMiddleware`. Registered only
  when there is somewhere to write.
* `--log`, `--log-content` on the server; the same two on `rage config`, which
  writes them into `.mcp.json`.
* `tests/test_eventlog.py`, plus additions to the store, server, config and CLI
  suites.

Two things the build found that prose would not have:

* The middleware receives a tool result **already serialised to a dict**, so
  the error flag is the wire's `isError`, not the model's `is_error`. Reading
  only the model spelling reported every rejected call as a success — the exact
  failure the log exists to catch, reproduced inside the log itself. Caught by
  driving a real client session rather than a stub, which is why that test
  stays end-to-end.
* `MCPServer.call_tool` does not run the middleware chain, so the existing test
  helper cannot reach it. `MCPServer.middleware` is also documented as
  provisional, so `test_the_middleware_is_reached` guards it the way the
  `extra="forbid"` tests guard that.

## Planned work

Not recorded here. The CLI and everything after it live in the rage store, under
`project/reference/planned`, so that a plan being worked from cannot go stale
against a file nobody reopened. Deferred and unscheduled work stays in the
Deferred section of design.md.
