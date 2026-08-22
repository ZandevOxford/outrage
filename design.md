# Outrage design

## Components

### MCP server

Python implemented MCP server primarily for use in local mode.

Provides access to the data store.

**The store introduces itself.** The document at the key `readme` is a store's
entry point - what it holds and what to read first - and the server carries it
at the *top* of its own instructions at startup, so it reaches a session
without a tool call and without the session knowing to ask. A line telling a
reader to go and read a key is a line that can be read past; this is the same
argument that puts `title` in the tool signature rather than in a convention
document. Instructions are sent once at initialisation, so a readme written
during a session reaches the next one.

**Delivery is a budget, not a promise.** A client may cut a server's
instructions at a length it does not announce - Claude Code cuts at
`DELIVERY_BUDGET` characters, which is an observation of one client and not a
protocol guarantee. So the static text is ordered by what must survive:
`ESSENTIALS` (the key grammar, allocation, and that a listing is a page) is
delivered after the readme and before `TAIL`, and nothing may be said *only*
in the tail. `README_MAX_CHARS` is computed from what the budget has left over
after the essentials rather than chosen, since the question the client actually
answers is how much room is left before the cut. Over that cap the length is
reported and nothing is inlined, because a silently shortened entry point is
the failure the entry point exists to prevent.

### Data store

Python library for storing data used by the MCP server.

Data is stored in an SQLite database local to the current project.

The store is kept independent of the MCP server: it has no knowledge of MCP and
can be tested and reused on its own.

**The interface and the backend are separate modules.** `outrage.store` says
what a store is - the operations, the value types every answer comes back as,
and the two ways a call bounds what it is asking about - as an abstract `Store`.
There are two implementations. `outrage.store_sqlite` is the read-write one -
the schema, its migrations, the connection handling, and the SQL - and is what a
store is opened as when its file says nothing else. `outrage.store_parquet` is
one columnar file, written whole and read many times, for a reference base of
tens of thousands of documents; it refuses writes, and `outrage pack` is how
documents get into one.

`store._backend_for` is the single place the package chooses between them, and
it chooses **by the store file's extension**: `.sqlite` and `.parquet`. So a
mount spec says `ref=python.parquet` and means it, with no new grammar and no
`--backend` flag threaded through the server, the command line and the mount
table. An unrecognised extension is the default backend rather than an error -
a store file has always been free to be called anything.

#### Store location

**A directory and a file within it**, and the two answer different questions.
The directory is the working area - it holds the stores, the event log, the
backups, and whatever an index or a vector store needs later. The file is
*which store*, and it is the half a backend other than SQLite would vary.

The directory is resolved in this order:

1. `--dir PATH` command line argument
2. `RAGE_DIR` environment variable
3. `./.rage/` relative to the server's working directory

The file is `--root-mount FILE`, defaulting to `store.sqlite`, and it is
**always relative to the directory**. An absolute path, or one climbing out
with `..`, is refused rather than resolved: an absolute path makes `--dir` a
lie, and it stops being true the moment a project is moved or checked out
somewhere else. The directory is created on demand, and so is a subdirectory a
store file names.

That the file is separately nameable is what lets one directory hold several
stores side by side - which is exactly what a mount table needs, and the reason
this is not simply a fixed name inside the directory.

The intended normal usage is a per-project MCP configuration passing `--dir`
explicitly, since an MCP server cannot be relied on to inherit the project
working directory. The working directory fallback exists for CLI and test use.
**One absolute path in the whole configuration**, and it is `--dir`; every
store in it is named relative to it.

The event log, when it is on, is `log.jsonl` in the same directory. It is the
first use of the room the directory was created to leave.

### Mounted stores

More than one database behind the one key namespace. A **mount table** maps a
key prefix to a store, the longest prefix matching a key owns it, and the store
`--root-mount` names is mounted at the root, so it owns everything no other
mount claims. A server with no `--mount` argument is a table of one, which is
the same code path rather than a second one.

Configuration, and only at startup: `--mount KEY=FILE`, repeatable. Nothing
adds or removes a mount on a running server.

**Every mount is a file in the one directory**, named the same way the root
mount is and by the same rule - relative to `--dir`, never absolute. So a
server holds one directory and several stores in it, rather than a directory
per store. Three things follow. A mount configuration survives the project
moving, because only `--dir` is a path. The stores a server serves are visible
together, in one place, rather than scattered across the filesystem. And what
distinguishes one store from another is reduced to a filename, which is the
seam a backend that is not SQLite fits into: the directory around it does not
change.

**A mount may be read-only**: `--mount-ro KEY=FILE`, and every write routed
there is refused before the store is reached. That is the case the whole
feature was pointed at - a shared reference base beside a local read-write
store - and the refusal is deliberately early, because a refusal that arrives
after the caller thought it had written is the failure class this project keeps
finding. It is enforced in the routing, so the database file is opened no
differently and nothing outside this server is prevented from writing to it. A
read-only mount is never *created*: a mistyped name would otherwise mount as an
empty store that no write could contradict.

The point of it is `project/reference/scale`: session context is small,
write-heavy and per-project, while a reference base of tens of thousands of
documents is large, read-mostly, and *the same corpus for every project that
mounts it*. One namespace, two very different stores behind it.

**Two translations, and nothing else.** Inward, a key loses the prefix of the
mount that owns it, so a mounted store is asked about keys in its own namespace
and never learns where it was mounted - the same database answers the same way
at `ref` as at `lib/ref`. Outward, every key it returns regains the prefix.
That is what makes a store distributable: it is self-contained and relocatable
because nothing inside it names its own mount point.

**The mount point is the inner store's root**, which is why the root had to
become a key first. Without it a store mounted at `ref` could not answer for
the document or the `!title` *at* `ref`, so a survey could not say what the
mount is.

**A mount shadows.** The store beneath a mount point is never consulted for the
keys the mount claims, so a document left at a key that later became a mount
point is unreachable rather than merged. That is the mount table rule, and
merging two stores that disagree about one key has no answer that is not
arbitrary. The server says so once on stderr at startup rather than refusing to
start, since the keys are still reachable in the store that holds them.

Shadowing binds a **traversal** as tightly as it binds a read. The store
beneath a mount still holds every one of those rows - mounting hides keys, it
does not delete them - so a survey that simply walks a subtree walks straight
through them and reports documents that reading them by key would refuse. That
is the failure the store exists to prevent, and it is the reason `Store` grew
range bounds: a subtree that a mount interrupts is read as the **windows**
either side of it. `before=k` ends the stretch in front of a mount point and
`after_subtree=k` begins the one behind, so the mount point is named from both
sides and neither name has to be a key that exists - there is no key "just past
the last thing under `k`" for a cursor to be given. The bounds narrow the
selection rather than the page, which is what lets each window carry its own
count and the counts be added up.

That leaves a subtree read bounded by **three separate things, all of which
must hold**: the part of the hierarchy to read, the stretch of the order to
read, and where the last page stopped. They stay three because a caller needs
to give any two of them at once - a range that excluded a mount would be
inexpressible if the subtree were folded into it, and a page's totals have
never depended on where the reader had got to, so the cursor cannot be a bound
on the selection.

**Reads and writes cross a boundary; queries do not.** A read, a write and a
delete route to one store and translate, and a write or a delete routed to a
read-only mount is refused there. A subtree read - `get_documents`,
`keys_missing_meta`, a recursive delete - covers the one store that owns its
key, minus the stretches its mounts claim, and *says which mounts it did not
descend into*. A partial answer must not
be indistinguishable from a whole one, which is the standing argument from
`context/8/decisions`. Aggregating across mounts is deferred, not abandoned:
`sort_key` is derived from the key alone and a cursor names a key rather than a
position, so a merge of two ordered streams is already feasible.

**A listing does cross**, and has to. A mount point is a key no store knows
about - the store beneath it has no row there, and the store above it cannot
see where it was mounted - so the table splices it into the level above as
`kind: "mount"` - or `"read-only mount"`, which is the only place that fact is
announced - described by the inner root. Without that a mounted store is
invisible to anyone who does not already know its prefix. Both halves are
merged before either is cut, for the same reason the store merges its own two
halves first.

**Every key has a name from outside, by construction.** A mount point and a
key inside a store are each bounded at 64 segments and the joined namespace
allows 128, so the two always join. This was not true until 2026-08-20: a store
mounted deep enough could hold keys that exceeded the limit once the prefix was
added, and every listing carried a path for dropping them and a `dropped` field
to say so. Halving the bound abolished the case instead of reporting it, which
also removed the one place a cursor could be a valid resume token and an
invalid key at the same time.

The only way the join can still fail is a store written before the bound was
halved. `Mount.outer` raises and names the store and the key rather than
handing back a string that would fail to parse a call later, and `outrage check`
reports such keys before anything mounts the store.

### Event log

An append-only record of what the server was asked for and what the store was
asked to do. Off unless `--log` is given.

It exists because of the failure that keeps recurring in this project: a
success that cannot be told from a real one. Unknown arguments dropped in
silence, truncation past `next_offset` that nothing downstream can detect,
scaffolding appended to a summary that reads correctly to its last sentence.
Each was found by hand, afterwards, from evidence that no longer existed.

It records at two grains, correlated by a call number:

* **Requests**, from a `ServerMiddleware` wrapping every inbound message. This
  tier rather than the tool functions, because an argument the server does not
  know is refused before any tool function is entered - so the one failure the
  server goes out of its way to catch is the one a tool-level log could not
  see. It also sees `initialize`, and so the client and the moment it connected.
* **Store accesses**, from a sink the store is given. One tool call is often
  more than one access, and this is also the grain the CLI will log at once it
  gains store operations.

The store takes the log as an argument and defaults it to a null object, so it
stays independent of MCP and unchanged when nothing is logging.

Document text is subject to a content policy, `--log-content`. The default
keeps a length, a hash of the whole, and - for anything long - both ends of it.
The tail is not symmetry: the leak that prompted this appended scaffolding
*after* content that read correctly to its last sentence, so a head-only
excerpt would miss the exact failure it was built to catch.

Two constraints the implementation follows from. Nothing may be written to
stdout, which carries the protocol. And a failure in the log must disable the
log rather than fail the call: a logging system that can take the store down is
a worse trade than no logging system.

The reading half - querying and summarising a log - is deliberately not built
yet. What it should answer is better decided by the first investigation that
uses one.

### Command line tool

Implemented, all five pieces, as of 2026-08-19: `outrage get`, `set`, `ls`,
`dump`, `rm`, `check`, `export`, `import`, `config`, `backup`, `log` and
`init` - the last of which writes the MCP entry, installs the `SessionStart`
hook and copies the packaged skill and agents into a project.

A CLI over the same store library, covering everything the MCP server exposes
plus the operations that only make sense from a shell:

* Bulk import of documents, for example a directory of markdown files mapped
  onto a key prefix, and the corresponding bulk export.
* Inspecting and repairing a store outside an agent session.
* Writing the MCP server configuration for a project, filling in the interpreter
  or entry point location and the store location.
* Installing the packaged skill and its hooks into a project, for the same
  reason: the skill ships inside the package, and the CLI is the thing that
  knows where the package is.

**Documents as files.** `outrage export` and `outrage import` map the key
namespace onto a directory by one rule: a segment is a path component, and a
document gains an extension naming its format - `.md` or `.json`. `a/b` is the
file `a/b.md`, and anything below `a/b` is in the directory `a/b/`. The
extension is what makes that possible at all, since a key is a document and a
container at once and a path cannot be both a file and a directory. Metadata is
a segment like any other, so a title is the file `a/b/!title.md`. Nothing is
escaped, which is what the widened character set bought: what a filename can
hold, a segment can hold. The two exceptions are the two segments a filesystem
reads as navigation - `.` and `..` are legal keys with no path, and an export
refuses them rather than climbing out of the directory it was given.

Paths are written from the top of the namespace rather than from the key being
exported, so an exported subtree imports back to where it came from and the
import's key prefix is what grafts it elsewhere. This is not a backup: it
carries documents and formats, and nothing else the database holds about them.

The last of these removes most of the friction in first time setup. The server
has to be launched by an absolute path into whichever environment it was
installed in, and that path is only reliably known from inside that environment
- which is exactly where the CLI is running. The initial `.mcp.json` in this
repository was written out by hand for that reason, and is machine specific as a
result.

It should be able to write project scoped or user scoped configuration, should
say what it is about to change and leave any unrelated servers in the file
alone, and should be safe to re-run when the environment moves.

It reads the same store directory, resolved the same way, so the working
directory fallback described above is the normal case for the CLI rather than
the exception.

Because both the CLI and the MCP server are thin wrappers over the store
library, neither should carry behaviour of its own.

### Skills

Skill and hook definitions, initially for Claude Code.

The skill carries judgment: when to survey the store, what is worth storing,
what the key namespaces are for, and when to write rather than wait. It does not
restate the key grammar or the argument rules, because those live in the tool
descriptions, where they are enforced rather than remembered. Step 4 is the
argument for that split - a session that had just read the `instructions`
asking for a title on every document stored one without.

The skill ships inside the package rather than only in this repository, so that
installing outrage anywhere carries the skill it is meant to be used with, and
the CLI has something to install. This project uses it through a symlink under
`.claude/skills`, so the copy being iterated on is the copy in use.

#### The trigger problem

A skill is only loaded when something decides to load it, and its description is
the only part that is always in context. That is enough for a skill invoked in
the middle of work, but the two moments that matter most for a store like this
are moments at which nothing prompts an agent to reach for one:

* *The start of a session*, when the store holds what the session is about to
  work out again from scratch.
* *Just before context is lost*, which is the last chance to write anything down
  and arrives without warning.

Neither is a request, so neither reliably triggers a skill. Both are events, and
events are what hooks are for, so a `SessionStart` hook points at the survey.
It emits static text and depends on nothing - not the store, not the interpreter
path - so it cannot fail in a way that blocks a session.

The second moment is **not** covered, and not for want of trying. A `PreCompact`
hook was written and removed on 2026-08-19: it delivers nothing to the model at
all, producing no attachment of any kind in the transcript - invisible rather
than rejected. The moment is still worth reaching and how to reach it is open;
see `planned/checkpoint-hook` in the rage store.

This is the same principle as putting `title` in the tool signature: the
convention should be reachable at the moment it applies, rather than requiring
that someone remembers it then.

## Key namespace

The key namespace is an arbitrary string, and `/` is the only delimiter there
is. A segment beginning with `!` is metadata about the document above it.

For example:

* context/<guid>/task  could contain a summary of the task for a particular context
* context/<guid>/design  could contain a design document
* context/<guid>/design/!title  could contain the title of the design document
* project/reference/implementation  could contain the implementation notes for the project
* notes/src/myfile.py  could contain notes about a particular source file

If A/B/C exists then A and A/B implicitly exist with no content.

Keys are *not* paths, and are never resolved against a filesystem, but the
delimiter is `/` so that a key may usefully mirror one. That is the reason the
character set is as wide as it is: a key naming a file has to carry that file's
name without transforming it. So `.` is an ordinary segment character, and so
are `..`, `:`, spaces and `?` - they can only *suggest* a navigation or a
meaning that does not exist here, and refusing them would mean a key that
cannot mirror a real name.

### Grammar

A key is a Unicode string naming a position in a hierarchy.

* A key is **zero or more segments** joined by `/`, and `/` is the only
  separator there is. The key with **no segments is the root**, spelled by the
  empty string. It is a key like any other - it holds a document, carries
  metadata, and is returned by a read - and it is also the parent of every top
  level key.
  * **The root is its own parent**, the way POSIX makes `/..` be `/`. That is
    what lets an ancestor walk terminate without a second value meaning
    "nowhere", and it is why every query listing a level has to exclude the
    root from its own listing. One clause does that, in `store`.
  * **A key is always a string, and `null` is not one.** A key parameter left
    out, or sent as `null`, means the root. It is resolved to `""` at the
    entry point, so nothing below carries a second spelling of "everywhere".
  * The cost, accepted: an empty string sent in error now addresses the root
    rather than failing. By convention nothing significant lives there, and
    the roots that will matter - a mounted store's own - are behind a mount
    prefix that an error does not produce.
* A segment is **1 to 1024 characters**; a key is **at most 64 segments
  within one store**, and at most **128 in the namespace a mount table
  presents**. Both are bounds on the absurd, not targets. A segment is
  typically well under 20 characters and a key a handful of segments, unless it
  is mirroring a structure that says otherwise.
  * The two numbers are one decision. A key in the joined namespace is a mount
    prefix followed by a key inside the store mounted there, and **a mount
    point is bounded as a store key is**, so bounding each half at half the
    total makes every joined key valid *by construction*. Nothing checks the
    sum, and no key can exist in a mounted store that the namespace above it
    cannot name.
  * The store bound was 128 until 2026-08-20. Halving it was cheaper than the
    alternative, which was a drop path through every listing for keys with no
    outer name - see the Mounted stores component.
  * A key at exactly the store bound can hold a document but **no metadata**,
    since a metadata segment is a segment. That is why the joined bound needs
    no allowance for one: the store refuses the title, so the namespace above
    never sees a key the store could not hold.
* A segment may hold **any character except `/` and anything below `\t`**
  (U+0009).
  * The excluded control range is a deliberate exception to "only `/` is
    reserved". Nothing worth mirroring addresses it, and reserving it is what
    lets the sort form mark segments without escaping. U+0000 would in any case
    truncate a key inside any C string that handled it.
  * Keys should *typically* be lower case ASCII with little punctuation. That
    is a convention for legibility; natural language and non-English keys are
    expected to break it, which is the point of the wide character set.
* Segments should typically be in **NFC**, but the system performs no Unicode
  normalisation and no validation of form. Two spellings of the same text are
  therefore two keys. Deliberate: normalising would mean a key that cannot
  round-trip the name it mirrors.
* Keys **are** normalised in two other ways, both before validation:
  * Leading and trailing `/` are stripped and runs of `/` are coalesced. Since
    this runs first, `"/"` and `"///"` reduce to the empty string, which is the
    root: they are spellings of it rather than errors, which is what a key
    mirroring a filesystem path ought to do.
  * A *wholly* numeric segment loses its leading zeros, so `context/01` and
    `context/1` are one key rather than two. `0` normalises to itself, and a
    segment that merely contains digits - `v01`, `1.2` - is left alone. This
    applies to metadata names too.
* A segment beginning with `!` names **metadata** about the document its
  segment sits under. A key splits at its **first** `!` segment: everything
  before it is the document key, everything from it onward is the metadata
  name. A key that is *only* metadata segments is metadata on the root, so
  `!title` is the store's own title. A path may continue below a metadata segment, so `a/!title/b` is an
  entry on `a` named `title/b`. **Everything below a `!` is metadata** - there
  is no document under a metadata path, which is what keeps `meta_name IS NULL`
  an honest test for "is a document".
* Sort order is **lexicographic by Unicode code point**, over a derived sort
  form rather than over the key. See Sorting.
* A key *being written* may use `?` in place of one whole segment, asking the
  store to allocate a number for it. See Autonumbering. **Only a whole segment
  is a wildcard**: `?` inside a segment is ordinary text, so `notes/where?.md`
  is a good key. A `?` segment is rejected by every operation but a write, so
  it can never read as a pattern.

Metadata may be attached to any key, including implicit keys with no content,
and one document may carry several entries. That is the intended mechanism for
alternative summaries and, in future, embedding vectors - for which the
metadata subtree is the natural shape, as `a/!embedding/<model>`.

### Sorting

Keys are never ordered as written. Every key has a **sort form**, stored
alongside it in `sort_key`, indexed, and used by every `ORDER BY`. It is never
returned: keys reaching a caller are always the normalised, unpadded key.

The sort form does three things to each segment, and each removes a defect:

* **Numeric segments are zero padded** to a fixed width, so `a/2` comes before
  `a/10`. Plain text ordering gives the reverse, which is untidy in a listing
  and unsafe under a cursor - a reader resuming after `a/9` would never see
  `a/10`, because a key written *later* sorts *earlier*. Since autonumbering is
  what parallel agents use to append findings for each other, that would
  silently lose exactly the documents the mechanism exists to deliver. The
  width is 16, which covers epoch milliseconds and microseconds; a longer
  number still sorts, just not numerically against other over-width numbers.
* **Every segment is marked** - `\x01` for metadata, `\x02` for a document -
  so a document's metadata sorts ahead of its subkeys.
* **Segments are joined with `\x03`** rather than `/`, so a subtree sorts
  immediately after its parent.
* **The root sorts as the empty string**, not as one marked empty segment, so
  it comes before its own metadata and before every top level key. Given a
  segment marker it would sort *after* `!title`, since the metadata marker is
  the lower of the two - the one place the marking would invert rather than
  order. It collides with nothing, because every other sort form begins with a
  marker.

The root is also the one document whose metadata is **not** its sort form plus
a fixed suffix: it contributes no segment, so `!title` is a first segment
rather than one joined onto a previous. Anything synthesising where a missing
metadata entry *would* have sorted has to say so - `missing_meta_stats` does,
with a `CASE`. Concatenating anyway would still tile, since the map stays
monotone, but it would file the root under a later window than the one its
title would really have sorted in.

All three markers sort below the lowest character a segment may hold, so none
can occur inside a segment: the encoding needs no escaping, and **two distinct
keys cannot share a sort form**. That last property is load bearing rather than
tidy - pagination resumes with `sort_key > ?` over a non-unique index, so a
collision would mean resuming past one row silently skipped another.

Together the marking and the delimiter make a metadata survey walk its
documents in the same order as a plain read. Two separate defects used to
prevent that, with two different causes:

* Until schema 4 the metadata separator was `:`, which sorts *above* `/`, so a
  document's metadata sorted after its whole subtree.
* Until schema 5 the sort form joined with `/`, and `-` (0x2D) and `.` (0x2E)
  are legal segment characters below it, so `a-x/!title` sorted before
  `a/!title` while `a` sorted before `a-x`.

Schema 4 fixed the first by choosing `!`, which then sorted below every
character a segment could begin with. Widening the character set removed that
guarantee, and the explicit marker replaces it. Schema 5 fixed the second by
changing the delimiter, at a price taken knowingly: **a subtree now sorts
immediately after its parent rather than after prefix-sharing siblings**, so
`a/b` comes before `a-x` in every listing.

Note that this does *not* license bounding a survey's window by document key.
`Store.missing_meta_stats` still measures at a synthesised position, because
that is correct under any ordering; see the note there.

### Autonumbering

Storing at `tmp/?` writes to `tmp/1` in an empty store, `tmp/2` next, and so on.
The wildcard may be any segment, not only the last, so `context/?/design` opens
a numbered context; the write reports the key it actually used, which is how a
caller learns the number and can then write `context/1/task` alongside it.

This exists so that an agent can create a container without inventing an
identifier. Inventing one is what a guid is for, but a guid is expensive to
carry in a prompt and impossible to type, and picking a name commits to a
description before the work is understood.

The allocated number is one past the highest number already used among the
children of the key enclosing the wildcard, counting keys that exist only
implicitly or only carry metadata. That makes the number unique but not
reserved: deleting the highest frees it again. Anything that needs a permanent
identity should use a name, not a number.

Because allocating reads the store before writing to it, the whole operation
runs in one immediate transaction, so two concurrent writers cannot pick the
same number.

#### Sorting numbered keys

Keys are ordered as though every numeric segment were zero padded, so `a/2`
comes before `a/10`. Plain text ordering gives the reverse, which is untidy in
a listing and unsafe under a cursor: a reader resuming after `a/9` would never
see `a/10`, because a key written *later* sorts *earlier*. Since autonumbering
is what agents working in parallel use to append findings for each other, that
would silently lose exactly the documents the mechanism exists to deliver.

The padding is a stored `sort_key` column, written alongside the key, indexed,
and used by every `ORDER BY`. It is never returned: keys reaching a caller are
always the normalised, unpadded form. Padding is to a fixed width, wide enough
that no parent will reach it; a longer number still sorts, just not numerically
against shorter ones.

Normalisation is what keeps the two forms from diverging. Without it `a/01` and
`a/1` would be distinct keys with identical sort keys, which is worse than
either problem alone.

## Values

Values are strings. A document records which of four formats its text is -
markdown, json, text or html - detected from the content when the caller does
not say, except that plain text is never detected: it is indistinguishable from
markdown, so it has to be asked for. The format is what the store knows about
the text and nothing more; nothing parses or renders on it.

## Tools

* Retrieve document: retrieves the content of a document. Optionally specify a character range. Optionally specify a search pattern and index to start the read from.
* Store document: stores document or metadata at a key.
* List keys: List keys immediately under a key, including subkeys and metadata.
* Get documents: Get multiple documents or metadata, with a key and or metadata filter. It should be possible to for example list the titles of all documents under a key.
* Delete keys: Delete a document and its metadata, optionally deleting the whole
  subtree beneath it.

### The argument contract

Tool arguments are a fixed, fully typed set. Every argument is declared with its
type and constraints, and anything else is an error: an unrecognised argument is
rejected and named, not quietly dropped.

This is the direction the whole tool surface should move in, and it is worth
being explicit about why, because permissiveness looks harmless. An argument
that is ignored produces a *success* result for a call that did only part of
what was asked. The caller cannot see the store, so it has no way to notice, and
a misspelled argument then behaves exactly like a server running stale code.
Strictness turns that into an error naming the argument, which is a better
outcome than a plausible wrong one.

The constraints belong in the declaration rather than in prose for the same
reason a title belongs in the signature: what is declared is enforced, and what
is merely described has to be remembered.

### Tool semantics

**Retrieve document.** The search pattern is a literal substring, not a regular
expression: it is predictable for a model to construct, needs no escaping, and
cannot backtrack pathologically on a large document. The index selects which
occurrence to start from. Reads are capped at a default of 8000 characters per
call; the response reports the offset, the number of characters returned, the
total document length, and the next offset, so a large document can be paged
without any single call flooding the agent's context.

**Store document.** Overwrite only. Versioning is deferred and is expected to be
implemented later as a separate archive table rather than by complicating reads.
The result reports the key written, which is the only way a caller learns a
number allocated for a `?` segment.

An optional `title` writes the `!title` metadata in the same transaction. The
saved call matters less than the fact that a separate call is one that can be
forgotten: the title is what makes a document findable later, so the convention
has to be reachable without remembering it. It follows an allocated number, so
`context/?/design` with a title titles `context/1/design`, not the wildcard. It
is rejected on a key that is itself metadata, since metadata does not nest.

**Get documents.** Matches the given key and everything beneath it at any depth,
with an optional depth limit. Recursion is the default because the motivating
case - listing the titles of all documents under `context` - spans a level of
nesting.

A survey by `meta_name` can only see documents that carry it, so on its own it
under-reports the store, and does so silently - the caller has no way to tell a
complete survey from a partial one. The result therefore also names the
documents in range carrying none of the requested names, under `without_meta`.

**Delete keys.** Deleting a key removes its content and all of its metadata.
Deleting a subtree requires an explicit recursive flag, so a mistyped key cannot
silently remove a whole context. Storing an empty document is *not* a deletion;
it leaves an empty document in place.

Deleting a key that holds nothing itself is a no-op, and an empty result is
indistinguishable from a successful deletion of a key holding an empty
document. A non-recursive
delete therefore reports how many keys it left standing beneath the target, so
the guard rail announces itself instead of looking like success.

**Reading a container.** A key with descendants but no content of its own is a
container, not a mistake, and the failure to read one should say so rather than
report the same "not found" as a key that does not exist anywhere. The two are
worth separating because they call for different next moves: list what is
beneath, versus check the key.

## Schema

This can be stored in a single table, with an index on the key.

```sql
CREATE TABLE documents (
  key        TEXT PRIMARY KEY,  -- full key, including any '!meta' segments
  doc_key    TEXT NOT NULL,     -- key with the metadata segment removed
  meta_name  TEXT,              -- metadata name, or NULL for a document
  parent     TEXT NOT NULL,     -- derived: enclosing key
  content    TEXT NOT NULL,
  format     TEXT,              -- 'markdown' | 'json'
  updated_at TEXT NOT NULL,
  sort_key   TEXT NOT NULL      -- derived: the sort form, see Sorting
);

CREATE INDEX idx_documents_parent ON documents(parent);
CREATE INDEX idx_documents_meta   ON documents(meta_name, doc_key);
CREATE INDEX idx_documents_sort   ON documents(sort_key);
```

`doc_key`, `meta_name`, `parent` and `sort_key` are all derived from `key` on
write. They are stored rather than computed at query time so that the main
access patterns are plain indexed lookups:

* *List keys immediately under X* is an equality match on `parent`. The parent
  of `A/B/!title` is `A/B`, so a document's metadata lists alongside its
  subkeys, as required. Implicit intermediate keys need never be materialised -
  they fall out of a `DISTINCT parent` query.

  The root is the one exception, and it costs one clause rather than a branch.
  Being its own parent, it would match its own listing, so every such query
  reads `parent = ? AND key <> ?` against the same value. No other key is its
  own parent, so the second test excludes nothing anywhere else.
* *Get one metadata name across a subtree* is a range scan on
  `(meta_name, doc_key)`.

Deriving these columns instead of using `LIKE 'A/B%'` also avoids the prefix
collision where `A/B` would match `A/Beta`.

A subtree is bounded by `["A/B/", "A/B0")` rather than by a prefix match. `/`
and `0` are adjacent code points, so the only strings in that range are `A/B/`
itself and the keys beneath it - a property of the delimiter alone, holding
whatever segments are allowed to contain.

The schema carries a version in `PRAGMA user_version`. **Version 5 is current.**

* **1 → 2.** Keys were period delimited; migrated by rewriting `.` to `/` in
  the three key columns. Exact, because no version 1 segment could contain
  either character.
* **2 → 3.** Numeric segments gained a normal form and `sort_key` was added.
  The table is rebuilt rather than altered, so a migrated store has exactly the
  schema a fresh one has. A store holding both `a/01` and `a/1` is refused
  rather than half merged.
* **3 → 4.** Metadata became a segment: `a/b:title` became `a/b/!title`, so `/`
  is the only separator. Rewritten in place, since `!` was not a legal
  character before.
* **4 → 5.** The sort form gained segment markers and its own delimiter. Only
  the derived `sort_key` changes, so this is a single `UPDATE`.

SQLite runs in WAL mode to tolerate concurrent readers.

## Deferred

* **Versioning**, as a separate archive table.

* **Semantic search**, implemented as additional metadata holding vectors. Not a
  current consideration, but the flat metadata namespace above is intended to
  accommodate it without a schema change.

* **Key move and rename.** Not possible today: a key is the identity of a
  document, so relocating a subtree means rewriting every key beneath it and
  every reference to them. Recorded under `scale` in the rage store rather than
  designed here.

* **Bootstrapping the skill configuration from the MCP server.** The server
  would help a session install or update the skills and configuration that make
  the store useful, either by editing local configuration or by returning
  instructions for doing so.

  Worth separating the two halves, because they are not equally risky. A tool
  that *returns* the configuration and instructions is unobjectionable: it is
  just a document, the agent and the user decide what to do with it, and it
  keeps the guidance versioned alongside the server that it describes. A tool
  that *edits* local configuration is a different proposition - an MCP server
  writing outside its own store directory is a surprising capability, it is
  hard for a user to audit, and the failure mode is a corrupted configuration
  rather than a bad answer.

  The middle option is for the server to write the files and for the CLI to be
  the thing that installs them, which keeps the write under a command the user
  ran deliberately. Worth prototyping the read only half first and seeing
  whether the editing half is still wanted afterwards.

  Note that the CLI already covers both halves under Components: it writes the
  MCP server configuration and installs the packaged skill. So what is deferred
  here is narrower than it first appears - only whether the *server* should be
  able to do either without the CLI, which is the half with the surprising
  capability and no obvious need.

## Open questions

None outstanding.
