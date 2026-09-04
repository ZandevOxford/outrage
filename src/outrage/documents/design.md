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
There are three **backends**. `outrage.store_sqlite` is the read-write one -
the schema, its migrations, the connection handling, and the SQL - and is what
a store is opened as when its file says nothing else. `outrage.store_parquet`
is one columnar file, written whole and read many times, for a reference base
of tens of thousands of documents; it refuses writes, and `outrage pack` is how
documents get into one. `outrage.store_files` is a directory of files, one per
key, which is what an export target and a working copy already were - the same
mapping `outrage.bulk` writes a tree with, expressed as a store, so that moving
documents between a database and a directory is a copy rather than a fourth
hand-written walker.

**Moving documents in bulk is one operation, and it is a method on the store
being written to.** `Store.copy_from` takes a source store, the same subtree
and range bounds a read takes, and yields a report per document as it crosses.
It is on the target rather than a function over a pair because the target is
what knows how it is written: a database takes a document at a time and a file
written whole takes all of them and writes once, and each answers the same ask
appropriately. Since any `Store` can be either end, an export is a copy into a
directory of files, an import is a copy out of one, a repack is a copy into a
file built whole, and a backup is a copy into a fresh store of the same class.
A document's `updated_at` crosses with it, which is what makes a copy a copy
rather than a restamping. `outrage export` and `outrage import` are wrappers
over it; `outrage pack` still builds a parquet file its own way, because what a
half-built file written whole looks like as a copy target is not settled.

**A store, and a store kept in a file, are two different things.** `Store` is
what any store answers: keys, ranges, subtrees, pages, excerpts. `FileStore` is
the half that needs somewhere on disk to answer from - where it lives, which
version of its format wrote it, how it is backed up, and what a check can say
about the storage rather than about the keys. The three backends are
`FileStore`s. A mount table is not, and that is the point of the split: it kept
eleven members whose only job was to raise "a mount table has no file of its
own", which is a class spelling out in eight declarations what one line of its
inheritance says. A caller wanting a file asks with `isinstance`.

The split is what lets `backup` stop being abstract. Every file store can copy
itself the same way: open a fresh one of the same class at the destination,
`copy_from` this one into it, reopen the copy and compare every key against the
source. A backend with a native copy of its file still overrides it -
`SqliteStore` must, because the file alone is not the store there, and
`ParquetStore` does because a byte copy is faster and exact - but what none of
them may do is skip the verifying, since a copy that opens cleanly is not
evidence of a complete one. What a backend cannot work out for itself is how to
open another of its own kind at a path, so that is the one thing the base asks
it: `opened_at`.

A backend is not the only kind of `Store`. `outrage.mounts.MountedStore` is one
too, and it keeps nothing at all: it answers the same interface and routes to
the stores behind it. That is what the abstraction bought - a mount table in
front of the server, the command line, or another table, with none of them
holding routing code - and it is why `Store` says the operations without saying
how they are kept.

`store._backend_for` is the single place the package chooses between them, and
it chooses **by the store file's extension**: `.sqlite` and `.parquet`. So a
mount spec says `ref=python.parquet` and means it, with no new grammar and no
`--backend` flag threaded through the server, the command line and the mount
table. An unrecognised extension is the default backend rather than an error -
a store file has always been free to be called anything.

A **tree is not addressed that way**, and claims no extension: a directory has
none to read, and reading the name of the directory instead would make
`.outrage/documents` a store and `.outrage/documents.d` a different one for no
reason a caller could see. An option that forces the backend type is what will
address one; until then `FilesystemStore` is constructed directly at a path,
which is also the shape an export target has - somebody's absolute path, which
the directory-and-file rule above correctly refuses.

#### Store location

**A directory and a file within it**, and the two answer different questions.
The directory is the working area - it holds the stores, the event log, the
backups, and whatever an index or a vector store needs later. The file is
*which store*, and it is the half a backend other than SQLite would vary.

The directory is resolved in this order:

1. `--dir PATH` command line argument
2. `OUTRAGE_DIR` environment variable
3. `./.outrage/` relative to the server's working directory

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

**A mount may name the backend that keeps it**: `--mount KEY=FILE,type=NAME`,
and `docs = { path = "docs", type = "files" }` in a mount table. Which backend
keeps a store otherwise follows from the store file's extension, which is what
lets `ref=python.parquet` mean what it obviously means without a second
grammar - but a **directory of files** has no extension to read, so the one
backend whose store is a directory is the one that has to be asked for. The
value is the backend's own name, the word a report already uses for it, rather
than a fourth vocabulary for the same three classes.

An **option inside the argument's value** rather than a second flag beside it,
and the reason is precedence. One mount is one option occurrence, so a `--mount`
at a point a mount table already claimed replaces that entry and everything said
about it - the override rule that was already there, needing nothing said about
options at all. A `--mount-type KEY=NAME` keyed by mount point would have needed
a new sentence about what a later claim on the path did to an earlier claim on
the type, and every future option would have needed another flag. The price is a
comma, which a store file may no longer contain: it is refused in both
directions rather than being quietly the first option's name.

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

**Everything crosses a boundary.** A read, a write and a single-key delete
route to one store and translate, and a write or a delete routed to a read-only
mount is refused there. A subtree read - `get_documents`, `keys_missing_meta`, a
count, a recursive delete - reads the subtree as an ordered list of *segments*:
the answering store's stretches between the mounts below it, and those mounts'
own subtrees, in the order the one namespace puts them. The items concatenate
and the totals add, because the segments are disjoint and tile the subtree, and
that is only true because a range bounds the **selection** rather than the page.
Stepping over a mount and reading it are the same operation with a different
list of segments.

It was not always so. A subtree read used to stop at the store that owned its
key and *say which mounts it did not descend into*, which was staging rather
than design - the standing argument from `context/8/decisions` is that a partial
answer must not be indistinguishable from a whole one, and naming what was
skipped satisfied it while a merge was still to be written. Since the merge
exists there is nothing to name. A recursive delete crosses too, deliberately
and with the risk accepted: a delete that stopped at a boundary while everything
else crossed would leave a caller to learn the rule from what survived. What a
read-only mount kept back is reported, because that is a refusal rather than a
silence.

A caller's own range crosses as well, spelled inward per mount and intersected
with the stretch each segment already was - so a range that excludes a mount
drops that segment rather than asking it with the bound quietly missing, which
is what would hand back the whole of it.

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

Implemented, all five original pieces, as of 2026-08-19: `outrage get`, `set`,
`ls`, `dump`, `copy`, `rm`, `check`, `export`, `import`, `config`, `backup`,
`log` and `init` - the last of which writes the MCP entry, installs the
`SessionStart` hook and copies the packaged skill and agents into a project.

A CLI over the same store library, covering everything the MCP server exposes
plus the operations that only make sense from a shell:

* Bulk import of documents, for example a directory of markdown files mapped
  onto a key prefix, and the corresponding bulk export.
* Copying a subtree or key-order range beneath another prefix in the mounted
  namespace, preserving metadata and timestamps and routing each write to the
  store that owns its destination key.
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
import's key prefix is what grafts it elsewhere. Both directions are
`copy_from` with a `FilesystemStore` on one end, so a document's `updated_at`
crosses too - as the file's modification time, which is what a tree's
`updated_at` *is*. What the round trip still does not carry is what only a
database holds about a document, and what a tree does not hold as a document
at all: a symlink, a file that is not text, a name that no key spells.

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
see `planned/checkpoint-hook` in the outrage store.

This is the same principle as putting `title` in the tool signature: the
convention should be reachable at the moment it applies, rather than requiring
that someone remembers it then.

## Key namespace

The key namespace is an arbitrary string, and `/` is the only delimiter there
is. A segment beginning with `!` opens a metadata namespace on the key above it.

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

The **first** character of a segment is the exception, and there are two of
them. `!` names metadata, and `?` is reserved: see Reserved segments. A name
starting with either still mirrors, since nothing stops it being carried a
level down.

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
* A segment beginning with `!` opens a **metadata namespace** on the key above
  it. Inside that namespace everything is an ordinary namespace again -
  documents, `?`, `?last` and their own metadata - so `a/!changelog/22` is a
  document kept inside `a`'s changelog and `a/!changelog/22/!title` is that
  document's title. A key that is *only* metadata segments is metadata on the
  root, so `!title` is the store's own title.
  * The **name is one segment**: a key splits at its first `!`, and what
    follows that segment is a path within the namespace. So `a` carries
    `changelog`, not `changelog/22`, and "is this the metadata value" is
    `meta_name` set with `meta_path` empty rather than `meta_name` set alone.
  * **Metadata changes exactly one thing, which is depth**: `!` and everything
    after it counts none. Levels and depth are therefore decoupled - reaching
    `a/!changelog/22` from `a` is two level walks and no depth - and that is
    what keeps depth across a mount boundary a constant offset.
  * A key and its whole metadata subtree are **one unit**: contiguous in the
    order ahead of that key's siblings, picked up together by any depth filter,
    and taken together by a plain delete. What a delete needs `recursive` for
    is everything else below, a metadata namespace's own contents included.
  * "Is this a document" is therefore **scope-relative**: it is the part of the
    key below the key a read was scoped at that must hold no `!`. A survey so
    descends into a metadata namespace only when it is scoped inside one.
* Sort order is **lexicographic by Unicode code point**, over a derived sort
  form rather than over the key. See Sorting.
* A segment **beginning** with `?` is reserved for the store to interpret
  rather than to store. See Reserved segments. Only the first character is
  reserved, so `notes/where?.md` is a good key.
* A key *being written* may use `?` in place of one whole segment, asking the
  store to allocate a number for it. See Autonumbering. **Only a whole segment
  is a wildcard**: `?` past the first character is ordinary text. A `?` segment
  is rejected by every operation but a write, so it can never read as a
  pattern.
* A key *being read, written or deleted* may use `?last` in place of one whole
  segment, naming the key that sorts last at that point. See Naming the newest
  key. Only a whole segment again, and several are allowed - each is resolved
  against the key the one before it produced.

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

### Reserved segments

A segment beginning with `?` is **reserved**. `?` and `?last` are the whole of
it today and everything else spelled that way is refused, which holds the space
open for the filters and logical operations a key will grow - a subtree filter,
a range, a choice between two keys. `keys.RESERVED_SEGMENTS` is the list, and a
third one is a constant and a line in it rather than a change to the grammar.

Reserved **before** anything needs it, and at a known cost: `a/?x` was a legal
key until 2026-08-23 and is not one now. The alternative is adding each
operator to a namespace that already allows it as ordinary text, where every
one of them silently changes what an existing key means and needs its own
migration. One refusal now, or an unbounded number of migrations later.

This is the second exception to "a segment may hold almost any text", and it
works the same way as the first: `!` and `?` are special at the **start** of a
segment and ordinary everywhere else. A key can still mirror a name holding a
question mark, and one that begins with a `?` can be carried a level down -
which is the same answer a metadata name gets.

### Naming the newest key

`?last` is the other half of that. Autonumbering hands out a key nobody chose,
which leaves the next session with a number it has to go and look up before it
can read anything: `context/?last/state` is that lookup written into the key.
It resolves to whatever sorts last at that point - `context/50`, not
`context/9`, because the sort form pads numbers - and it counts implicit keys,
since the newest thread of work is a container and rarely a document.

Resolution happens in the **front end**, before the key is parsed for routing
or handed to a store, and it costs one `last_child` call per `?last` segment.
That placement is not an implementation detail. A `?last` in the part of a key
that names a mount decides which store answers, so a mount table asked to route
one has not been told enough to route it; and every tool then accepts `?last`
without knowing it exists, because they all resolve through one function.
`keys.resolve_last` holds the walk and takes the lookup as an argument, so what
a key *is* stays decidable without opening a store.

Each front end reports what it resolved to - the tools echo the key on the
result, the command line says so on stderr - for the same reason a write
reports the number it allocated: reading the wrong document is the one outcome
the caller cannot see happening.

A `?last` with nothing below it is a refusal, not the parent and not an
invented key. The cost of all this is that `?last` was an ordinary segment
before, so a key spelled that way is no longer reachable; `keys.parse` refuses
one by default rather than letting an unresolved `?last` be written as a key.

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

## Text

### Encoding

**All text is UTF-8**: keys, documents and metadata values alike. There is no
other encoding and no per-document declaration of one, so a file that is not
UTF-8 is not a document - the filesystem backend reports such a file rather
than mangling it, and a read of one is refused naming the key it was asked
for.

Where the store counts bytes it counts UTF-8 bytes. A byte offset addresses
that encoding, which is what makes an offset the store hands out valid against
an exported file, and an offset landing inside a character reads from that
character's first byte rather than splitting it.

**Text should typically be in NFC, but nothing normalises and nothing
validates the form.** Two spellings of the same text are two different
strings, and for keys two different keys. This is the same call made for the
same reason as the key grammar's: normalising would mean text that cannot
round-trip the thing it came from, and a store whose job is to hand back what
it was given cannot quietly rewrite it. NFC is the convention to author in,
not a rule the store enforces.

### Line endings

Three rules, and between them they say where the choice of a line ending lives:
**whoever creates the text chooses it, and everything that merely carries it
keeps it.**

1. **A transfer without a format conversion converts nothing.** Text moving in
   or out of the store keeps the line endings it arrived with. An export and an
   import round-trip byte for byte, and a directory of files returns what is on
   disk rather than what a translating read would make of it.
2. **Where there is no line ending to preserve, prefer LF.** A document the
   store *authors* - the output of a format conversion, a generated index - is
   written with `\n`, because something has to choose and one canonical answer
   beats whatever the source happened to use.
3. **Every part of the system copes with LF or CRLF.** The first two rules make
   CRLF an ordinary document shape rather than a rare one, so nothing
   downstream may assume otherwise. More exotic endings - a lone `\r`, `\v`,
   `\f`, `\u2028` and the rest - are out of scope.

The first two are changes the code makes; the third is a standing invariant,
which is worth only the tests under it.

What follows from rule (a) is that **a store does not normalise on write**.
That was a real alternative - one canonical line ending, decided once, rather
than fidelity to whatever arrived - and it was rejected: the store's job is to
give back what it was given, and normalising is confined to the two places the
store is the author. It follows too that documents stored before this was
settled, with their endings already collapsed, are left alone. Nothing could
recover them, and under rule (b) LF is the preferred ending anyway, so such a
document is indistinguishable from one authored with LF.

The costs, stated rather than discovered. A CRLF document is one byte per line
longer, in every reported byte total, in every generated byte offset and
against every read's character budget. A slice can fall between the `\r` and
the `\n`, since they are two characters; paging rejoins them exactly, so
nothing is corrupted, but a slice may begin with a lone `\n`. And a caller's
own regular expression is their own: `$` sits after the carriage return, so an
anchored pattern matches nothing in a CRLF document, where the whole-line
matcher strips every ending before comparing.

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
is accepted on a metadata key too, where it becomes that namespace's own
`!title`: a namespace can be described like anything else.

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
  doc_key    TEXT NOT NULL,     -- key up to its first metadata segment
  meta_name  TEXT,              -- first metadata name, or NULL for a document
  meta_path  TEXT,              -- what follows it, or NULL for the value itself
  parent     TEXT NOT NULL,     -- derived: enclosing key
  content    TEXT NOT NULL,
  format     TEXT,              -- 'markdown' | 'json'
  updated_at TEXT NOT NULL,
  sort_key   TEXT NOT NULL      -- derived: the sort form, see Sorting
);

CREATE INDEX idx_documents_parent ON documents(parent);
CREATE INDEX idx_documents_meta   ON documents(meta_name, meta_path, doc_key);
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
  `(meta_name, meta_path, doc_key)`. A read scoped *inside* a metadata
  namespace is the one case those columns cannot answer - every row there
  carries the same `meta_name` - and it re-splits the key per row instead.

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
  every reference to them. Recorded under `scale` in the outrage store rather than
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
