# Outrage requirements

Why this exists and what has to hold true of it.

`design.md` describes how it is built. The rage store itself, under
`project/reference/`, holds the build discussion decision by decision. This
file is the short human-readable version that should outlive both.

## What outrage is for

Four uses. They pull in different directions, and most of the tension in the
design comes from that.

**Session context.** Notes, decisions, findings and task state that outlive a
single working session, so that the next one can pick the thread up rather than
re-derive it. Tens of documents. Written and re-read by their own author, who
can survey the whole store in one call and often does.

**A reference base.** A large corpus of small documents, imported in bulk and
reached by search rather than by browsing. The worked example is the complete
Python reference documentation split one key per function —
`reference/python/os/path/join` and so on. Tens of thousands of keys.

**Notes on a codebase.** Observations, findings and warnings about the files of
a large project, keyed to mirror the tree they describe — notes about
`src/myfile.py` living at `notes/src/myfile.py`. This is why key naming is
deliberately compatible with file path naming: `/` is the delimiter so that a
key can shadow a path without translation.

Like the reference base this is hierarchical and can reach a large number of
documents, one per interesting file. **Unlike it, it is write-heavy.** A
reference corpus is imported once and read thereafter; codebase notes are
written continuously, as the code they describe is read and changed, and they
go stale when it moves underneath them.

**Agents working in parallel.** Several agents running at once, collating
findings into one store and using it to pass work between them — one writes what
it found, another reads it. Autonumbering exists for this: a `?` segment lets an
agent add a document without coordinating over names and without risking a
clash with another agent doing the same thing at the same time.

This use has no single author. Documents arrive concurrently from processes
that cannot see each other, and a reader may be paging through a subtree while
it is still being written to.

Everything built up to 2026-08-19 assumed the first use. The other three were
always intended but had never been written down, which is how several parts of
the system came to quietly assume a store small enough to read in full.

## Requirements

### 1. Scale

The store must work at reference-base size. Not degrade gracefully at it —
work at it, as an ordinary case rather than a stressed one.

The concrete target is the Python reference example above: tens of thousands of
documents in one store, most of them small, mostly written once and read many
times.

Scale is not only a read problem. Codebase notes reach a comparable number of
documents by accumulation rather than import, so writes are frequent, spread
over time, and interleaved with reads — possibly from more than one session at
once. A store that answers reference-base reads well but serialises or loses
concurrent writes has met half the requirement.

### 2. Concurrent use loses nothing

Several writers at once is an ordinary case, not a stressed one — parallel
agents in use 4, and more than one session in use 3.

Two things follow. Allocating a `?` number must be atomic against other
writers, or the feature meant to prevent clashes causes them. And a reader
paging through a subtree while it is written to must not silently miss what
arrives, which is what requirement 3 is about.

Neither can be left to callers being careful. Agents cannot see each other by
construction, so there is nobody to be careful.

### 3. Everything that returns data is bounded

No call may return an amount of data determined by how much happens to be in
the store. This holds on both axes:

* **within a document** — how much of one document's content comes back;
* **across documents** — how many documents, keys or metadata entries come
  back.

A bounded call needs a way to ask for the next part, so bounding implies
pagination. The point is not to make big answers small; it is that the caller,
not the store's contents, decides how much arrives.

**A continuation must name a stable point, not a count.** "Resume after key K",
never "skip the first 200". Under uses 3 and 4 the store is being written to
while it is being read, and a positional cursor shifts whenever something lands
before it, so a page silently repeats or skips. A key does not move.

This is also why documents are expected to be small and usually read whole. The
collection axis is the one that has to be got right; the content axis matters
less when a document fits in one read, and keeping documents small is what
makes that true.

### 4. A partial answer says how big the whole is

Any component returning part of something must also report the size of the
whole — the library function, the MCP tool, and the skill's own guidance about
how to read results.

Without it "there is more" is not actionable. 500 characters of 520 and 500
characters of 500,000 are different situations calling for different next
moves, and a caller that cannot tell them apart will treat them the same. The
same holds for collections: 20 keys of 22 is a listing, 20 keys of 40,000 is a
sample.

`Excerpt` already does this on the content axis — it carries `returned`,
`total` and a continuation offset. That shape is the model; what is missing is
the same discipline everywhere else.

### 5. A subtree can be understood without reading it

There must be calls that describe a body of documents in a result whose size
does not depend on the size of that body: how many documents lie beneath a key,
how they are distributed across its children, which metadata they carry, what
values that metadata takes.

Pagination alone does not satisfy this. Paging through forty thousand titles
does answer "what is in here", but only by reading all of it, and reading all
of it is precisely what must not be required.

### 6. No success that cannot be told from a real one

The failure this project keeps meeting: an operation that reports success while
having done something less than it appears. Unknown arguments dropped in
silence. A read truncated past a continuation offset nobody follows. A file
copy of a database whose recent writes are still in the write-ahead log.
Scaffolding appended to a generated summary that reads correctly to its last
sentence.

Where a cheap check can tell a real success from a hollow one, the check
belongs in the library, paid for once, rather than in prose telling every
caller to remember. A rule that nothing enforces is a rule that survives until
the next edit.

### 7. Guidance must scale with the store

The advice the system gives about itself is part of the system. The MCP server
instructions and the packaged skill currently both say to survey the store by
fetching every title before reading anything, which is right for session
context and wrong for a reference base.

So guidance is version-specific to scale, and whatever replaces it has to keep
the small-store advice working while giving the large-store case a different
first move.

## What this does not cover

Deferred items — versioning, semantic search, Unicode keys, bootstrapping the
skill configuration from the server — are listed with their reasoning in the
Deferred section of `design.md`.

Bulk import, on-disk size, whether metadata values want their own index, and
whether a reference corpus belongs in the same store as session context all
follow from requirement 1 and none of them are settled.

Requirement 2 has a live defect behind it: allocated numbers are not padded, so
`findings/10` sorts before `findings/2` and a key-based cursor would skip what
arrives after it. Measured, and written up in the store under
`planned/pagination/key-ordering`. Allocation itself is already atomic.

The codebase-notes use raises two more, both open. There is no way to **move or
rename a key or a subtree** — the store can write and delete, nothing else — so
a renamed source file today means notes orphaned under their old path and
rewritten under the new one. And nothing detects **staleness**: a note keyed to
a file says nothing about which version of that file it was true of.
