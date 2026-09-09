# Changelog

Notable changes to `outrage`. This project follows [semantic versioning](https://semver.org).

## Unreleased

The command-line import report now names only the store files that received
documents, or would receive them in a dry run. It no longer presents every
open mounted store as though the import wrote there.

## 0.10.2 - 2026-09-08

The installed documentation now includes the project's requirements and copies
of its README, licence and changelog. The documentation build refreshes those
copies from the repository root.

`store_document` can now write supplied `!contents` metadata alongside a
document, in the same transaction where the backend supports one, just as it
already could for `!title`. The MCP `store_document` and `document_edit` tools
now use that path to generate a Markdown or HTML document's contents index by
default; pass `generate_contents=false` to leave it untouched. Explicit
contents supplied to `store_document` take precedence, and metadata writes do
not recursively generate metadata.

The new library-level `outrage.titles` utility extracts a document title from
Markdown or HTML without reading or writing a store. Markdown uses the first
level-one ATX heading; HTML prefers `<title>` and falls back to the first `<h1>`.
HTML markup and link targets are removed while readable text remains. The MCP
`make_metadata` tool replaces `make_contents` and generates both a title and
contents by default, with independent boolean controls for each. The Python
API and command-line `make_contents` names are unchanged. No dependency was
added.

`make_contents` now indexes stored HTML as well as Markdown. HTML `h1` through
`h6` elements become plain Markdown headings with their character and UTF-8
byte offsets into the original source; nested markup and link targets are
removed while readable text remains. The implementation uses Python's standard
library and adds no dependency.

## 0.10.1 - 2026-09-07

On Windows, the managed Claude Code `SessionStart` hook now selects PowerShell
explicitly instead of being routed through Git Bash, and paths written into
hook commands and `.mcp.json` use forward slashes. Windows accepts that spelling
directly, while JSON no longer has to escape every directory separator. Managed
Copilot hooks now likewise contain only the platform-appropriate `powershell`
or `bash` field.

Generated heading indexes now omit inline link destinations by default while
keeping their visible text. Pass `strip_links=false` to the `make_contents`
tool, `--no-strip-links` to either contents command, or `strip_links=False` to
the Python API to retain the full Markdown link. The mount tool now says when
opening a missing writable target created a new store, and copy failures name
mounted keys in the outer namespace.

A directory of files can now be read at the keys its own documents link to, so
a documentation bundle somebody else wrote is mountable as a store without
rewriting a single link inside it.

**Upgrading:** nothing. The mapping every existing tree is in is unchanged and
is still the default; `extensions=keep` is a thing a mount asks for. No public
name is removed or renamed.

* **`extensions=keep` makes a file name and a key segment the same string**, so
  `guide.md` is the key `guide.md`. **The reason is links rather than naming.**
  A bundle's documents link to each other by file name, and under the ordinary
  mapping — now spelled `extensions=strip`, and still the default — the
  extension comes off to make the key, so every one of those links names a key
  the store does not hold. The package's own shipped documents are the worked
  example: their readme names `agents.md`, `cli.md` and the rest, and under
  `keep` each of those is a key that reads.
* **It is sayable wherever a tree can be named**: `--mount
  docs=bundle,type=files,extensions=keep`, the same after `--store`, an
  `extensions` field in a `mounts.toml` entry, an `extensions` argument to the
  `mount` tool, and `--extensions strip|keep` on `outrage import`, `export` and
  `pack`. A store kept in one file has no such question and **refuses** the
  option rather than ignoring it, which is the rule a mount spec already
  follows for an option name it does not recognise; so does a value naming no
  mapping.
* **A document keeps the keys below it in a directory named `.!` and the
  document's name.** A name in a directory is a file or a directory and not
  both, so `guide.md` the document would otherwise have had nowhere to put so
  much as a title. Inside that container it is the ordinary mapping again — a
  title is `.!guide.md/!title.md` — so what a container holds is exactly what
  an ordinary export writes, and metadata carrying its extension is what lets a
  listing report its format without opening it. A bundle's own directories are
  left plain, so `guide/intro.md` is still `guide/intro.md`. The exception is
  symmetric when the directory was written first: `.!guide` is then the
  document beside `guide/`, while a prefixed directory remains the container
  beside a plain file. Entry type distinguishes them.
* **One cost, the mode's and not hidden.** A document whose
  key spells no extension is written to a file with none, so a format the key
  does not name does not survive the round trip: `notes` stored as text reads
  back as markdown. `notes` the document and `notes/` a bundle's own directory
  are the same string, so which spelling to use is the one thing this mapping
  asks the tree rather than the key.
* **A mount specification is now opened in one place.** Every field of one says
  how to open a store, and three command-line paths took a specification apart
  by hand and so quietly dropped the new field: the option parsed, the store
  opened, and every key was the key of a mapping nobody asked for. Fixed for
  good rather than one field at a time.

## 0.10.0 - 2026-09-06

A running server's stores are no longer fixed when it starts. A session that
finds it needs a reference base mounts one and carries on, instead of asking
for a restart and losing everything it was holding -- and a second new tool
tells it what the server it is talking to actually is.

**Upgrading:** one public name goes. `outrage.store_sqlite.WAL_UNCHECKPOINTED`
is gone for real this time: 0.9.0 said it had been removed, and the import that
replaced its definition brought the name back holding a different value, so a
caller matching on it stopped matching without anything failing. Read
`outrage.maintenance.WAL_UNCHECKPOINTED` instead, whose value is a problem
code. Nothing else in this release removes or renames anything.

* **New `mount` and `unmount` tools: a server's stores are no longer fixed
  when it starts.** A session that finds it needs a reference base had to ask
  for a restart and lose everything it was holding. `mount` takes a key, a
  store file relative to the store directory, an optional backend and a
  `read_only` flag; `unmount` takes a key. Both answer with the whole table as
  it now is, since what shadows what is not visible in an answer about one
  mount. A mount at a point something already holds replaces it. The root
  cannot be mounted over or unmounted: it owns every key no mount claims, and
  the instructions a client is given are built from its readme when it
  connects.

  MCP only, and deliberately: the command line builds its table from scratch on
  every run and has nothing to change. A change lasts as long as the server --
  a mount configuration file is still read and never written, because a machine
  rewrite is what loses the comments it exists for -- and every answer says so.

  Nothing changes at the store level. A mount table is immutable, a change
  builds a new one and swaps a single reference, and every call takes one
  snapshot of it at entry, so no read spanning several stores can see two
  tables. A page taken before a change and continued after it may still skip or
  repeat keys, which is the same class of thing as a document written between
  two pages.

* **`mount` with no `file` mounts the store outrage ships for that key**, which
  today is the `outrage` manual and nothing else. It exists so that unmounting
  the manual is reversible: the tree lives inside the installed package rather
  than in the store directory, so it has no spelling as a mount file at all.
  It is always mounted read-only.

* **`outrage-server --no-remount` withholds both tools**, with `outrage config
  --no-remount` and `outrage init --no-remount` recording the flag on the
  server entry. Offered by default, and a person keeps the capability either
  way: restarting the server with different flags is what an operator does.

* **A message never tells a reader to do something they cannot.** "Cannot
  write here" told every caller to restart the server with `--mount` rather
  than `--mount-ro`, which a tool caller cannot do -- and now need not, since
  mounting it again writable is a tool call. Both remedies are named, each said
  to be whose it is, and the notes on a copy and a delete that stopped at a
  read-only mount changed the same way. Four other refusals that named a server
  startup flag were reworded to say whose it is, rather than pretending it is
  something every reader can type.

* **Two remarks on one result no longer run together.** Nothing produced two
  until the mount tools did, and then an unmount answered "...without anything
  being written. this table lasts as long as this server", which is one
  sentence to whoever reads it. A remark that follows another is capitalised
  where they are joined.

* **What a mount change says about keeping it now depends on the change.** One
  sentence served all of them, and it was the mount's: an `unmount` ended by
  telling the caller to write the mount they had just removed into the mount
  configuration file, and mounting the shipped manual by name told them to
  write down a store that has no spelling in that file at all. A mount still
  says to write it down; an unmount says a restart brings it back, that the
  configuration file has no unmount to write, and names the two remedies that
  do work with whose each is; the shipped manual says it needs nothing written
  down, because it is mounted by default.

* **A copy into a read-only mount now names the mount.** It reported every
  document as a separate failure, each carrying the whole refusal, and said
  nothing about the mount that refused them all -- so with the failures sampled
  the one fact reached the caller five times as an excerpt and never once as a
  sentence. The table was being asked which read-only mounts lie *below* the
  landing, which is the right question for a delete, whose key is the top of
  what it removes, and the wrong one for a copy, which is as often landing
  inside such a mount. `MountedStore.read_only_at_or_below` is the question a
  copy asks.

* **A read of the shipped manual is logged under the key it was read by.** The
  documentation store was opened without being told where it mounts, so an
  event log recorded a read of `outrage/readme` as `readme` -- the same name as
  a document in the root store, and indistinguishable from it. This affected
  the default mount as well as one made with the `mount` tool.

* **A new `info` tool, and `outrage info` beside it.** A session could see
  everything in a store and nothing about the server holding it. The tool
  reports the Python environment the server runs in -- with the absolute path
  to the `outrage` command line in it, so a caller can drive the same
  installation rather than whatever is on their PATH -- the store directory,
  the mount configuration files that were read, every mount as it was opened
  with the file behind it, whether writes are refused there, and whether the
  server is logging. `outrage info` prints the same report, and `outrage
  mounts` is still the one to run before the stores exist, since it opens
  nothing.

* **`outrage-server --no-info` withholds that tool**, and `outrage config
  --no-info` / `outrage init --no-info` record the flag on the server entry.
  It is offered by default: what it reports is a list of absolute paths into
  the machine the server runs on, which is worth having and worth being able
  to keep back.

* **`make -C docs documents` rebuilds the whole shipped tree.** It ran the API
  reference generator and not the two beside it, so `cli.md` and `tools.md`
  were left to be regenerated by hand and a new subcommand or a changed tool
  schema shipped a stale page until a test caught it. All three generators are
  in the target now. No output changes; what changes is that one command
  produces it.

* **A read-only mount no longer offers a reason it cannot have.** "Cannot
  write here" listed a packed parquet store among the possible causes, and a
  parquet store never produces that refusal: the store is asked before the
  configuration is, so a backend that cannot be written raises its own message
  about repacking instead. What the sentence now names are the two cases that
  do reach it -- a mount made read-only by `--mount-ro`, and a store lent to
  the server already open, which is how the shipped documentation is mounted.

* **A failed copy is worded by the front end reading it.** A copy, an export
  and an import run inside the library, which turned each refusal into a
  sentence where it happened -- so the words reached both the command line and
  the MCP tools already written, spelled one way, and neither could say an
  argument the way its own reader types it. The refusal now travels whole and
  each front end renders it. No message changes today; what changes is that the
  next one to name an argument cannot come out wrong at one of them.

* **`outrage.store_sqlite.WAL_UNCHECKPOINTED` is really gone now.** 0.9.0 said
  it was removed and it was not: the import that replaced the definition
  brought the name back as a module attribute, holding the problem code where
  it used to hold that problem's summary -- so a caller matching a summary
  against it silently stopped matching, which is the one failure the removal
  was meant to avoid. The import is aliased private, so the old spelling raises
  where it is used and `outrage.maintenance.WAL_UNCHECKPOINTED` is the only one
  left. Found by the checks run against the published wheel.

## 0.9.0 - 2026-09-05

The command line remarks on two things it used to leave to the reader, and both
come out of the same change underneath: what an operation has to say about
itself is now worked out once, in the library, and each front end has a table
deciding whether that reader hears it.

**Upgrading:** two public names go, and both fail loudly rather than quietly.
A caller reading `unchecked` off a tool result or off `bulk.Imported` should
read `unchecked_code` instead -- the same reason in one word -- and one
importing `outrage.store_sqlite.WAL_UNCHECKPOINTED` should take
`outrage.maintenance.WAL_UNCHECKPOINTED`, whose value is now a problem code
rather than the sentence describing it. No store format moves, and nothing
about a store written by an earlier build changes.

**Correction, added after publication:** the second of those removals did not
happen in 0.9.0. `store_sqlite` imported the constant from `maintenance` by its
own name, so `outrage.store_sqlite.WAL_UNCHECKPOINTED` went on resolving --
with the code as its value where it had been the sentence. A caller comparing
a problem's summary against it stopped matching and was told nothing. Fixed
below.

* **`outrage set` says when a document shrank**, and by how much. The shell
  round trip -- `outrage get > file`, edit, `outrage set --file` -- is the
  documented way to change a long document, and the first use of it wrote an
  empty document over a good one: the write was right, the report said how many
  characters went in, and nothing said how many had been there. The measurement
  reads one character, so a store that keeps its lengths pays almost nothing.
* **`outrage rm` says which read-only mounts refused a delete.** Everything
  else a delete leaves behind is a key, and a key is printed or counted; a
  read-only mounted store is not a key, so a delete that stopped at one printed
  exactly what a delete that took everything printed.

* **`unchecked` is now a code, and the prose field is gone.** `store_document`
  and `document_edit` answer with `unchecked_code` -- `no-record` or
  `other-key` -- where they used to answer with a sentence a caller had to
  parse. `bulk.Check` and `bulk.Imported` carry that code and, where the record
  named another key, that key; their `unchecked` attribute is removed, as is
  `bulk.unchecked_prose`. Nothing a *person* reads has changed: the note beside
  the answer says the same words, written now by whichever front end is
  speaking.

* **`outrage check`'s problems carry a code.** `maintenance.Problem` gains
  `code` as its first field, one of the twelve in `maintenance.PROBLEM_CODES`,
  so anything with something to do about a particular fault selects on that
  rather than matching the sentence describing it. The report itself is
  unchanged: `summary` and `detail` are still what a person reads.

  **Removed:** `outrage.store_sqlite.WAL_UNCHECKPOINTED`, which was the WAL
  problem's summary exported so that callers could match on it. The name is
  now `maintenance.WAL_UNCHECKPOINTED` and its value is the code. An importer
  of the old name gets an `ImportError` rather than a string whose meaning has
  quietly changed.

What the MCP tools say is unchanged, word for word, with one exception: a
read-only mount below the root is named `/` rather than `''`.

## 0.8.1 - 2026-09-05

Document lengths are written down instead of being counted, and which length
gets written down is decided per backend, because which of the two is expensive
is a property of the storage rather than of the store.

**Upgrading:** nothing to do. No format version moves. A SQLite store gains a
cache table and its triggers the first time this build opens it, and a build
without this change goes on reading and writing that store; a parquet file
gains a column when it is next packed, and files packed before this are read
exactly as they were.

* **A byte-addressed read now reports `total`**, the document's length in
  characters, where the store can answer without reading the document — which
  is a SQLite store and a parquet one. A directory of files recomputes every
  derived fact and still reports `null` rather than paying for the scan a byte
  offset exists to avoid. `total_bytes` is given by all three, as before.
* **SQLite keeps a cache of document lengths**, for documents past 2 048
  characters — a quarter of the rows in a store like this project's own, and
  nine tenths of the text. A subtree total costs about 58% less as a result.
  It is a cache: a missing entry is counted instead, so nothing depends on it
  being complete, and a read that had to work a length out writes it down, so
  a document only pays for that once. Triggers on the document table empty it, so no writer can
  leave an entry describing text that has changed — including a build of
  `outrage` older than the cache, since the triggers live in the file. `outrage
  check` reports what the cache holds and warns if an entry ever disagrees with
  its document; `--repair` drops those entries.
* **Listing a level no longer reads the documents it lists.** The size of each
  entry was found by pulling every listed document's whole text into Python and
  measuring it.
* **`outrage pack` writes a `bytes` column**, each document's length in UTF-8,
  and takes `--no-byte-lengths` to leave it out. It is written by default
  because a parquet file is never updated in place: a store packed without it
  can only gain it by being packed again. `chars` was already there and is not
  optional.

## 0.8.0 - 2026-09-05

0.8.0 lets a caller address a document by byte as well as by character, so an
index can drive a seeking read of a very large document, and settles what
happens to line endings when text crosses into or out of the store.

**Upgrading:** `make_contents` now writes two numbers under each heading rather
than one, so an index generated by an earlier version is read wrongly rather
than rejected. Regenerate any `!contents` you rely on. Nothing else needs
migrating: documents already stored keep whatever line endings they have, and
character offsets mean exactly what they did.

* **`read_document` and `outrage get` take `byte_offset` / `--byte-offset`.**
  A character offset is a fact about a Python string and does not survive
  leaving the store; a byte offset does, so a number the store produced can be
  handed to anything byte-addressed downstream. A byte offset landing inside a
  character snaps backward to that character's first byte, and the result says
  where the read began. Passing both `offset` and `byte_offset` is refused.
  `pattern` composes: the search starts at or after that byte. `max_chars`
  remains a cap in *characters* whichever unit addressed the read, since that
  is the budget a caller is actually spending.
* **A byte-addressed read reports byte positions**, and the character offset of
  where it began is reported as unknown rather than computed, because deriving
  it means decoding the whole prefix. Take both numbers from `!contents`, where
  they are already a pair for the same position.
* **`make_contents` now writes two numbers under each heading**, the character
  offset then the byte offset, bare and space-separated. The token count on the
  line is the only thing that tells the two formats apart, which is why an
  earlier index has to be regenerated rather than left alone.
* **Seeking is now used where a backend can seek.** On an 8 MB document a
  random byte-addressed read costs about 2.4 ms in SQLite and 0.4 ms in a
  directory of files, against about 12 ms before. A character-addressed read
  cannot be accelerated by any of this on any backend, which is exactly why the
  index carries the byte number.
* **Text crossing into or out of the store keeps the line endings it arrived
  with.** An export and an unchanged re-import round-trip byte for byte, a
  directory of files returns what is on disk, and `outrage set --file`,
  `outrage set < file` and `outrage get > file` all preserve CRLF. Previously a
  CRLF document could be reported with text its own files did not hold, and the
  two numbers on a `!contents` line could name different places in it.
* **Where there is no line ending to preserve, LF is chosen.** A document the
  store *authors* rather than carries is written with `\n`: `ingest_document`
  now normalises converted output, so the character count it reports counts
  what was stored. Documents already in a store are untouched, and need no
  migration.
* **On Windows the command line's own messages now end in LF**, which is the
  cost of not translating the document content it writes to standard output.
  This is what every other tool there does.
* **`ingest_document` is offered only where the `documents` extra is
  installed.** A client shown a tool whose every call refuses has been told the
  store can do something it cannot.
* **The design and implementation guides ship in the package**, mounted as
  `outrage/design` and `outrage/implementation`, and every shipped document now
  carries a `!contents` offset index, so the guide can be navigated the same way
  any other large document can.

## 0.7.0 - 2026-09-04

0.7.0 makes a copy or a delete refusable when the target has moved since you
looked, previews a delete before it takes anything, brings local files into the
store as Markdown, and indexes a long document's headings so a reader can jump
into it.

* **`copy_tree`, `delete_keys` and their command line halves take
  `unchanged_since`, the time you looked at the target.** Nothing is written if
  anything there has changed since: a copy is refused before it starts rather
  than part way through, and a delete refuses rather than skipping the keys
  that moved, since a partial subtree cannot be put back. The window is
  measured over what the run would actually take - a key and its metadata unit,
  or the whole subtree under `recursive`. A deletion is invisible to the guard,
  because the row that would carry the timestamp is the row that has gone, and
  a write inside the same second as the watermark is invisible too.
* **`delete_keys` takes `dry_run`, and a preview now comes from the store.**
  `Store.delete` performs the selection and leaves the removal out, so a
  preview and the run it precedes name the same keys. This corrects
  `outrage rm --dry-run`, which walked the subtree itself and so named one key
  where the delete removed two - a plain delete carries the key's metadata unit
  away and the preview did not say so.
* **A dry run reports when it looked**, as `checked_at` from the tools and a
  line on standard error from the command line, so the pair reads as look, then
  write only what has not moved.
* **`ingest_document` and `outrage ingest` convert one local file to Markdown
  and store it.** The source must be a regular file on the server's
  filesystem; URLs and other non-file sources are refused, and converter
  plugins, remote fetching, Azure services and LLM conversion are not enabled.
  The title comes from `--title`, then the converted document, then the source
  filename. Needs the new optional `documents` extra, which carries MarkItDown
  and its `docx`, `pdf`, `pptx` and `xlsx` readers; it is kept out of the base
  installation so a store that only holds session context does not pay for it.
* **`make_contents` indexes a Markdown document's headings by character
  offset**, in the library, the MCP server and the command line. Each literal
  ATX or setext heading is kept in source order with its section body replaced
  by the zero-based character offset where that heading begins - the offset
  `read_document` already takes, so an entry in the index is a read that lands
  on its heading. The result is stored as direct metadata, `<key>/!contents` by
  default, and the source is never changed. Headings inside fenced code blocks
  are not headings, and a document whose headings did not survive conversion
  indexes as empty.
* **Messages now spell an argument the way its reader types it.** A command
  line user was being told to "pass `on_conflict='overwrite-unchanged'`", which
  is not a flag anybody can type; the command line renders the flag and the
  tools render the keyword. The four watermark messages are converted and the
  rest of the file still reads one way for both.
* **`on_conflict` lists all four of its choices** in the description of the
  argument that takes one, having gone on naming three after
  `overwrite-unchanged` became the fourth, and a dry run names
  `overwrite-unchanged` when that is the rule the advice needs.
* **The shipped default readme says which documents need a route** - important
  open plans do; issues are searched instead, and reference, glossary, file
  notes and scratch are found by name - and tells a new store to keep `current`
  to routing and brief notes on the open items rather than everything recent.

## 0.6.0 - 2026-09-02

0.6.0 makes editing a document through a file safe when more than one agent is
writing the store, and renames the tool that does it.

* **Breaking: the `document_file` MCP tool is now `document_edit`.** There is no
  alias and the old name no longer exists; callers naming it must be changed to
  the new one, whose arguments and behaviour are otherwise unchanged. The name
  now says what the tool does - take a document out for editing and put it back
  - rather than describing the file as the point of it.
* **An edit exported to a file now survives another writer.** Every export gets
  a file of its own and a record of what the document held when it came out, so
  an import whose document has been written since is refused rather than
  silently discarding that writer's work. `overwrite` stores it anyway, for a
  caller who has looked at what changed. A successful import renews the record,
  so one export can carry more than one edit.
* **`store_document` and `document_edit` accept `against`, the path of an
  exported file whose record checks the write.** Only the record is read and
  never the file's content, so a document exported and then edited in context
  gets the same staleness refusal as one edited on disk, and a cross-key import
  can take its content from one file and its claim about the target from
  another. A write that cannot be checked is refused as well as one that fails
  the check, both liftable with `overwrite`.
* **A verbatim cross-key copy is no longer reported as an edit that changed
  nothing.** Importing an unedited exported file into a different key is how
  content is copied around the store, and the document it lands on does change;
  the note now describes the file rather than contradicting the sizes reported
  beside it.

## 0.5.1 - 2026-09-02

0.5.1 corrects mounted-store event logs, makes large Parquet stores much less
expensive to open, and repairs the package's direct dependency metadata.

* **Events from a mounted store now log keys in the outer namespace.** Logged
  arguments, range bounds, cursors, allocated keys and bounded key lists carry
  the mount point, matching the keys callers use without changing routing,
  storage or returned values.
* **The Parquet index now keeps Arrow columns instead of a Python object per
  row.** It derives key lookup, child ranges and metadata names from the file's
  existing order, substantially reducing memory use while preserving the
  backend contract and improving its largest lookup paths.
* **Pydantic is now a direct runtime dependency.** The server imports its
  Pydantic 2 APIs directly, rather than relying on `mcp` to install them
  transitively. Omnidep is included as a development dependency and its check
  is documented alongside the existing test and lint commands.

## 0.5.0 - 2026-09-01

0.5.0 adds bounded programmatic document search to the Python and MCP
interfaces, including stable evidence for why each document matched.

* **`Store.find_documents` and the MCP `find_documents` tool search document
  bodies and direct metadata.** One to five case-sensitive criteria can use
  literal `contains`, exact whole-`line` or Python `regex` matching and can be
  combined with `any` or `all`.
* **Search results are grouped by document and carry bounded witnesses.** Each
  satisfied criterion reports its first matching source and character span.
  Candidate-window statistics and cursors keep expensive work bounded; an
  empty match page may still have a cursor when more documents remain.
* **Every backend shares the same search contract.** SQLite, filesystem,
  Parquet and mounted stores use the concrete Store baseline, with differential
  tests preserving identical results for future optimized implementations.
  The MCP tool defaults to scanning 20 candidates and publishes closed input
  and output schemas alongside generated tool and Python API documentation.

The README now describes all three storage backends and the current development
workflow, and the shipped documentation index lists every document the
distribution carries.

## 0.4.4 - 2026-08-31

0.4.4 makes both command-line and MCP documentation derive from the interfaces
they describe, and gives MCP clients complete result schemas.

* **Every MCP tool now publishes a closed, described output schema.** Nested
  results such as document excerpts, missing-metadata summaries and copy
  failures are typed too, while optional fields remain absent when they do not
  apply so existing wire results retain their shape.
* **The shipped MCP tool reference is generated from the built server.** Tool
  descriptions, parameters, defaults, constraints and return fields therefore
  stay aligned with the metadata clients receive, enforced by a freshness test.
* **The command-line reference is generated from the live argument parser.**
  Usage blocks have explicit headings and the checked-in document is tested
  against the parser rather than maintained as a second source of truth.

## 0.4.3 - 2026-08-31

0.4.3 gives Claude Code, Codex and Copilot CLI one maintained source for the
agent procedures they share, and expands the store guidance those procedures
rely on.

* **Search, annotation and metadata backfill procedures are now shipped once**
  under `outrage/agents/`. Harness-specific agents and skill references point
  to those documents instead of carrying copies that can drift.
* **`outrage init` installs native Copilot CLI agent profiles** alongside its
  session-start hook. The hook now runs the installed Python with the same v3
  managed marker used by Claude Code and Codex while preserving Copilot's
  required payload shape.
* **Project conventions live in each store's readme and workflow guidance,**
  leaving the packaged skills concise. The shipped key and workflow documents
  now cover ordering and range bounds, metadata, long-document editing,
  handoff, and safe deletion of current and historical records.
* **The annotation and search agents use the current `/!name` metadata form.**
  Their stale pre-schema-4 `:name` examples could create ordinary documents
  instead of metadata while reporting success.

The shipped documentation index now explains title surveys without repeating
the mounted-document inventory.

## 0.4.2 - 2026-08-30

0.4.2 simplifies the MCP surface and makes the text a client sees easier to
maintain and inspect.

* **The MCP tool `retrieve_document` is now `read_document`.** This is a
  breaking change for MCP clients that call tools by name. The Python Store API
  and store-event operation retain `retrieve_document`.
* **`read_document` no longer takes `length`; use `max_chars`**, consistently
  with `get_documents`.
* **Every MCP tool description is now a shipped document** under
  `outrage/tools/<name>`, read and cached when the server registers the tool.
  The descriptions and delivered store instructions are shorter while keeping
  their paging, limit and readme-routing rules.

The README has a shorter introduction and setup path.

## 0.4.1 - 2026-08-30

0.4.1 makes the session-start guidance installed by `outrage init` work the
same way across Claude Code and Codex, while retaining Copilot CLI's separately
verified hook shape.

* **`outrage init` now installs a Codex SessionStart hook** in
  `.codex/hooks.json`. It merges its entry with an existing file and leaves
  hooks it does not own untouched, just as it already does for Claude Code and
  Copilot CLI.
* **Claude Code and Codex now generate their hook JSON through the installed
  Python**, using `python -m outrage sessionstart`, instead of embedding it in
  an `echo` command. The command reads the shipped prompt when the hook runs,
  quotes the interpreter for the host platform, and carries its managed marker
  as an ordinary argument rather than a shell comment.
* **The installed prompt names `retrieve_document` explicitly** and falls back
  from the project's `readme` to `outrage/readme` when the project does not
  provide one.

The repository's own generated client configuration is no longer tracked, and
the README now links directly to the shipped documents and generated API
reference.

## 0.4.0 - 2026-08-29

0.4.0 is about what a store and its server *say*: the documentation outrage
ships about itself, the sentence a caller reads when a call is refused, and the
readme a store introduces itself with. The main changes are:

* **Outrage's own documentation is a mounted store**, generated from the
  docstrings and shipped in the wheel, so a session can read the API reference
  through the same tools it reads anything else with.
* **A store's `readme` is named in the server's instructions rather than
  carried in them**, so it may be any length, and it is read live by the
  session that needs it.
* **A failure a caller can correct now reaches them as a sentence**, against
  mcp 2.1, which stopped carrying the text of anything that is not a
  deliberate `ToolError`.
* **`document_file` and `copy_tree`** are new tools: one document through a
  file, and a subtree copied or re-rooted.
* **A mount may name its backend**, so a directory of files is mountable.

`requires-python` drops to **3.12**. For library callers it breaks in two
places: five names are gone from `outrage.server`, and
`install.HookTarget.template` is now relative to the hooks directory rather
than absolute, with `HookTarget.fragment` giving the path it used to hold.
Both are below.

### Nothing shipped names the machine it was built on

`outrage.install.CLAUDE_HOOK` carried the packaged hook fragment as an
**absolute** path, resolved at import. Sphinx renders a module constant by its
`repr`, so the build machine's checkout went into
`documents/reference/install.md` - a page that ships in the wheel and is
mounted as documentation a session reads. It also made
`test_the_reference_is_not_stale` fail for anybody whose clone was somewhere
else, which is the wrong way round: the person who could see it was the one who
had not caused it, and what they saw was an unrelated test failing in a fresh
clone.

* **`HookTarget.template` is now relative to the hooks directory**, as
  `HookTarget.relative` has always been relative to the project root, and the
  new **`HookTarget.fragment`** property is where it actually is. A property
  rather than a field, so it stays out of the `repr` the reference renders.
* **`.mcp.json` no longer ships in the sdist.** It is this repository
  registering the server for itself, with a `command` naming a conda
  environment and a `--dir` naming one OneDrive folder. `.claude` was already
  excluded for the same reason; this is its neighbour.
* Both have a test. `test_no_page_names_the_machine_it_was_built_on` reads the
  committed pages rather than re-rendering them, so it fails for whoever
  commits the defect instead of for whoever clones it next.

### Python 3.12 is enough

`requires-python` asked for **3.14**, which was the interpreter to hand when
the first commit was written rather than a decision. Nothing in the package
needs it: the only feature ever argued for is `tomllib`, in the standard
library since 3.11, and compiling the whole of `src` and `tests` under 3.12 is
clean. Asking for an interpreter released in October 2025 excluded most of the
ones outrage would otherwise install into, for nothing gained.

The floor is now **3.12**, and `environment.yml` moves with it so that the
environment the README tells a contributor to create is the one the package
asks for. The suite, the doctests, `ruff` and the strict docs build were run on
3.12 and on 3.14; nothing in the package changed.

### A failure a caller can fix now says so

mcp 2.1 stopped carrying the text of anything raised out of a tool that is not
a `ToolError`: a deliberate failure keeps its message, and everything else
reaches the client as `Error executing tool <name>` and nothing more, its own
text logged server-side. That is the distinction `outrage.errors` already drew,
and it caught **seven** places where this package was on the wrong side of it.
A damaged `json-string` value, an unknown `encoding` or `format`, an empty
`pattern` and an empty `meta_name` were each a bare `ValueError`, so a model
that had emitted scaffolding into its own tool call - the thing the encoding
exists to catch - was told only that something went wrong, when what it needed
was to be told to send the call again.

* **`store.InvalidArgumentError`** is an argument value the caller can correct,
  as against the checks that guard a front end's own mistake. Three message
  codes follow it, carrying the wording that used to be written at the raise
  site.
* **`format` and `encoding` are typed rather than described.** The tool schema
  listed the values in prose and said `string`; it now carries a real `enum`
  and `const`, so a bad one is refused before the tool body runs.
  `store.Format` and `store.Encoding` are the new source, and `store.FORMATS`
  and `store.ENCODINGS` are `get_args()` of them. `meta_name` takes at least
  one entry.
* **`outrage get --pattern ''` printed a traceback** and prints a sentence now.
  The command line was never about the SDK; it had the same misclassification
  underneath.

The package still supports `mcp>=1.2`, and the one test asserting the 2.1
behaviour skips where the SDK does not draw the distinction.

### The store's `readme` is named in the server's instructions, not carried in them

A client cuts a server's instructions at a length it does not announce, so
carrying the readme meant capping it: `DELIVERY_BUDGET` less whatever the
static text cost, which was **667 characters**. Over that, nothing was inlined
and the length was reported instead - a store whose readme had grown was
silently no longer introducing itself, and only a freshly started session could
see it. Both readmes in this repository were over it: this project's own at
1898 characters, and the `default_readme` shipped as a template at 2560.

Capping was the wrong bound. How long a store's entry point should be is the
project's business, and different projects' conventions will not fit one
number. The instructions now carry a fixed sentence saying there is a `readme`
and to read it first, whatever length it is; a store with none is still told
the convention, so the store is still consulted, just not quoted.

* **`README_HEADING`, `README_NOTE`, `README_MAX_CHARS`, `README_FLOOR_CHARS`
  and `SCAFFOLDING_CHARS` are gone** from `outrage.server`, and `READ_README`
  and `PROTECTED_CHARS` replace them. `PROTECTED_CHARS` measures what is
  delivered ahead of the tail - the readme line plus the essentials - which is
  everything that has to survive the cut. It is 1328 of the 2048 budgeted.
* The readme is now read **live** by the session that needs it, rather than at
  server startup, so a readme written during a session reaches that session.

### A mount can say which backend keeps it, so a directory of files is mountable

Which backend keeps a store followed from its file extension, and a directory
has none - so `FilesystemStore`, the backend whose store *is* a directory, was
the one thing a mount table could not describe. A mount argument now takes
options after its store file, and `type` is the first of them:

```sh
outrage ls --mount docs=documents,type=files
outrage export DIR --store documents,type=files
```

```toml
[mount]
docs = { path = "documents", type = "files" }
short = "documents,type=files"   # the same thing, as the argument it stands for
```

* **`KEY=FILE[,NAME=VALUE]...`**, which is `mount(8)`'s own shape. The option
  lives inside the argument's value rather than in a second flag beside it, so
  one mount stays one option occurrence and overriding an entry from a mount
  table remains a matter of replacing it whole. The price is a comma, which a
  store file may no longer hold; it is refused in both directions rather than
  being quietly the first option's name.
* **An entry in `mounts.toml` may be a table**, `{ path = "...", type = "..." }`,
  whose fields are the option names. A string entry is still the value half of
  a `--mount`, options and all, so nothing is expressible typed and not in a
  file.
* **The type is a backend's own name** - `sqlite`, `parquet`, `files` - which
  is the word a report already uses for it. An unrecognised *extension* still
  falls back to the default backend; an unrecognised *name* is refused, because
  one is a guess at what somebody meant and the other is what they said.
* `--root-mount`/`--store` takes the same options, so a tree can be the whole
  store: `outrage check --store documents,type=files`.
* `outrage mounts` reports the type in the file column, since it is the one
  thing about a mount that cannot be read off the name.

### A subtree copy, as a tool

The MCP server offers `copy_tree`, so a session working through the tools can
move a subtree from one key to another without shelling out to `outrage copy`.
It is the same call the command line makes - `Store.copy_from` over the mounted
namespace - with the argument shaping and the result shaping a tool needs:

* **The result is statistics, not keys.** A copy may cross more keys than a
  result can hold, so it reports counts by action, the characters that crossed,
  and a bounded sample of what failed. The command line still prints a line per
  document, because a person reads it as it goes and an interrupted run has
  then said exactly what it did - a property one return value cannot have.
* **A `limit` and a `cursor`, so a copy resumes.** `next_cursor` is the source
  key of the last document that crossed; call again with `cursor` set to it and
  everything else unchanged. The cursor is a separate argument from the six
  range cuts, which stay the selection.
* **Read-only mounts under where the documents land are listed in full**, as
  `delete_keys` already does: there are never many mount points, and a count
  alone reads as a copy that mostly worked.
* `Store.copy_from` and `outrage.bulk.copied` grew the same `cursor` and
  `limit`. The copy stops in front of the key it would have written next, so a
  bounded run crosses exactly `limit` documents, and the generator *returns*
  the resume cursor - a source key, which is not what any transfer carries.

### A copy can re-root a subtree, not only nest it deeper

`Store.copy_from` and `outrage copy` take `reroot`/`--reroot`, which strips the
source subtree's own key before grafting: `outrage copy a/b tmp --reroot` lands
the documents at `tmp` and `tmp/one` rather than at `tmp/a/b` and
`tmp/a/b/one`. Without it a copy could only nest a subtree deeper - "these
documents now live at another key" was inexpressible, and a round trip through
a temporary namespace did not come home, because the second hop grafted the
temporary prefix along with everything else.

Grafting the whole source key is still the default and still what an archive or
a backup wants. What changes with the flag is which pairs of keys are safe: a
copy streams a live walk, so grafted only a target inside the source is
refused, while re-rooted the two subtrees must be disjoint in either direction
- `a/b` re-rooted onto `a` would send `a/b/b/x` to `a/b/x`, back inside the walk
that is still running. The rule is `bulk.overlapping`, applied by the front
ends, so the command line and the server refuse the same pairs.

### Outrage's own documentation, as a store

A read-only store of documents about outrage itself ships inside the package
and is mounted at `outrage`, so the manual is reached with the same tools as
everything else rather than through a second retrieval path. It holds a readme,
and documents on keys, the tools, the command line and the conventions.

* **The MCP server mounts it unless told otherwise; the command line does not
  unless `--mount-docs` asks for it.** A bare `outrage` command stays a clean
  namespace over the project's own store.
* **It is an ordinary mount once it is there.** It shadows, it appears in a
  listing as a read-only mount, and a `mounts.toml` naming `outrage` overrides
  it silently by the ordinary rule that a later source wins. `--unmount
  outrage` is the off switch on either front end; there is no second flag for
  it.
* **It announces itself in a listing and is not delivered.** The server's
  instructions still carry only the root store's readme, on the delivery-budget
  argument that has always governed them.
* **A build that dropped the tree warns on the server and refuses on the
  command line.** Nobody asked for the mount on the server, so a missing tree
  must not stop a session starting; `--mount-docs` was typed, so it is a
  refusal there.

`mounts.open_mounts` gains `attached`, a mapping of already-open stores mounted
read-only at their keys - the one way in for a store that is not a file
relative to `--dir`, which a tree in `site-packages` cannot be. New module
`outrage.shipped` says where the tree is and opens it.

### One document through a file, as a tool

The MCP server offers `document_file`, which moves a single document between
the store and a file so that a long document can be edited with `sed`, a
heredoc or an editor without its unchanged text passing through an agent's
context twice. The direction is decided by one argument and nothing else: with
no `path` the document at `key` is written to a file under `export/` in the
store directory and the path returned; with a `path` that file's content is
stored at `key`.

* **The export path is the key's own**, by the same mapping `outrage export`
  uses, so `context/60/state` is `export/context/60/state.md` and exporting a
  key twice reuses one file rather than accumulating copies. The answer says
  whether a file was already there. A key that has no path at all - one with a
  `.` or `..` segment - gets a random name carrying the format's extension
  instead.
* **The key and the path need not agree.** An import stores at the key it is
  given, whatever file the content came from, so exporting one key and
  importing to another copies content across the store.
* **Only a file under the export directory can be imported**, which is the
  whole of the check: the same containment rule the bulk export is guarded by.
  A relative path is taken from that directory rather than from the working
  directory, and a file missing at one says so.
* **An empty file is stored rather than refused**, and both sizes are reported
  instead - the characters written and the characters that were there before,
  with a note when the document shrank. Emptying a document is a thing a person
  may mean; an edit script that truncated silently is not.

`build_server` takes the store directory as a third argument to make this
possible, since what it serves is a `MountedStore` and cannot be asked where it
is. The tool is registered only when that directory is given.

Library callers gain `bulk.export_document`, `bulk.import_document`,
`bulk.file_for_key` and `bulk.contained_file`, and `store.EXPORT_DIR_NAME`.

## 0.3.0 - 2026-08-27

0.3.0 makes multiple stores and their mounted namespace first-class throughout
the library and command line. The main additions are:

* **Filesystem-backed stores.** `FilesystemStore` presents a directory with one
  file per key through the same `Store` interface as SQLite, Parquet and a
  mounted table. It can participate in a `MountedStore` through the library;
  command-line mount specifications still select file backends by extension.
* **File-based mount configuration.** `mounts.toml` records the root,
  read-write and read-only mounts once for both the MCP server and CLI, with
  command-line overrides, `--unmount`, additional config files and a safe
  `outrage mounts` inspection command.
* **Expanded database editing from the CLI.** `get`, `set`, `ls`, `dump`, `rm`,
  `export` and `import` now operate across the mounted namespace, and the new
  `copy` command transfers depth- and range-bounded document selections between
  its prefixes without a filesystem round trip.

This is a breaking release for library callers: the mount table is now
`MountedStore(Store)`, `Store` and `FileStore` are separate interfaces, and
metadata is a namespace rather than a leaf. The detailed changes and migration
notes follow.

### A mount table in a file, and a command line that reads it

`mounts.toml` in the store directory describes the mounts, so a table is
maintained in one commented place rather than respelled on every command line -
and, for the server, rather than living inside a client's `.mcp.json` in an
array whose quoting belongs to argparse. It holds `root-mount`, a `[mount]`
table and a `[mount-ro]` table, each entry a `KEY = "FILE"` naming a store
inside `--dir`. TOML because a config file is the one place comments are
wanted, and `tomllib` is in the standard library.

**A file behaves as if its options had been typed at the point where it is
named.** The default file is spelled at the very front, so everything actually
typed comes after it and wins; `--mount-config FILE` splices another in where
the flag appears. There is no separate notion of a merge: precedence and
repetition are whatever argparse already does. The one deliberate exception is
duplicates - a mount point claimed twice within one source is still refused,
while claimed again from a later source it *replaces* the earlier one, which is
what makes a committed table safe to override one entry of.

`--unmount KEY` removes a mount a file declares, which is the one thing an
override cannot do - naming a mount replaces it or adds it. An unmount is a
deletion rather than a second claim, so it takes away every earlier mount at
that point whatever source it came from, and a `--mount` written after it
mounts again. An unmount that removed nothing is refused, on the same ground
`--mount-ro` refuses an unmatched mount point: it reads as though it worked,
and what it leaves behind is the mount somebody meant to take away.
`--no-mount-config` ignores the default file for a run.

**`outrage get`, `set`, `ls`, `dump`, `rm`, `export` and `import` now take
`--mount`, `--mount-ro`, `--unmount`, `--mount-config` and
`--no-mount-config`**, and act across the whole table,
so the command line sees the namespace the MCP server serves rather than the
root store alone. `--store` is the root mount on those commands and
`--root-mount` is an accepted alias for it. `outrage check` and `outrage
backup` stay per-file by nature, and already say which file with `--store`.

**`outrage init` and `outrage config` write the mounts to `mounts.toml`, not
into `.mcp.json`.** That is the payoff: registering the server stops being
"write the whole table into a client's JSON, correctly, from a command" and
becomes "point at a directory", so the entry's `args` are `--dir` and whatever
`--log` says. `config.server_entry` no longer takes `root_mount`, `mounts` or
`read_only_mounts` - **breaking for library callers** - and
`install.Installation` gained a `table` field saying what happened to the file.

The table is written **once**, commented, and never rewritten: a file whose
reason for existing is comments cannot be machine-rewritten, because a rewrite
is what loses them. A run naming a mount an existing table does not hold prints
the lines to add. A run naming no mount writes nothing at all - `config` and
`init` register a server, and creating a store directory to drop an empty file
into it is not something either was asked to do.

**Nothing migrates an installed configuration.** An entry an earlier release
wrote keeps its `--mount` arguments and goes on working: `merge_entry` inherits
what a new entry does not mention, and those arguments still win because the
command line comes after the file. `outrage config` reports that they are there
and that removing them is an edit to `.mcp.json`, which is the migration, done
by hand and only when somebody wants it.

**`outrage mounts` reports the table a command line would open, and opens
none of it.** Opening a read-write mount is what creates it, so a mistyped name
in a committed table becomes an empty store that reads exactly like a store
with nothing in it yet - `--mount-ro` refuses for that reason and the
read-write half never could. This says so first, and is safe to run on a fresh
checkout. It takes every option the other commands take, so it answers for the
line you would really run, and names the source each mount came from - the
question a table merged from a default file, each `--mount-config` and what was
typed created. Non-zero when the table would not open: a read-only mount that
is missing, or two mounts at one point. A read-write mount that is not there
yet is reported and is not a failure.

`mountfile.origins` is that provenance, and `mountfile.Origin` what it returns.

A mount point that is metadata is now refused when the spec is parsed rather
than when the table is built, so a mistyped one no longer leaves a database
behind named after the mistake.

### `Store` and `FileStore`: a store, and a store kept in a file

**Breaking for library callers.** `Store` now says only what a store *does* -
the vocabulary of keys, ranges, subtrees and pages that any store answers in.
Everything that needs somewhere on disk to answer from moves to a new
`FileStore(Store)`: `directory`, `path`, `default_filename`, `format_version`,
`stored_format_version`, `backup`, `backup_path`, `audit_rows`, `check_file`,
`repair`, and the constructor that settles where a store's file is.
`SqliteStore`, `ParquetStore` and `FilesystemStore` are `FileStore`s;
`MountedStore` is a `Store` and not a `FileStore`.

`outrage.maintenance.check` and `repair`, and `store.default_store` and
`open_store`, are typed as `FileStore` accordingly.

**A mount table no longer refuses those eleven members - it does not have
them.** Asking one for a `path` or a `backup` used to raise a written
`mount-has-no-file` sentence, which was a class saying in eight declarations
what one line of its inheritance now says. `isinstance(store, FileStore)` is
how a caller asks, and a caller that asks anyway gets Python's own
`AttributeError`. Nothing on the command line reaches this: `outrage backup`
and `outrage check` already name the store they mean with `--store`, which is
the honest answer for a table spanning three files.

### Every store can back itself up

`FileStore.backup` is no longer abstract. The default opens a fresh store of
the same class at the destination and copies this one into it with
`copy_from`, then reopens the copy and compares **every key** against the
source - not a count of them, since a copy that lost one document and gained
another counts the same and is not a backup. `FileStore.verified_backup` is
that check on its own, and `FileStore.opened_at(path)` is the one thing a
generic copy cannot work out for itself: another store of this class, kept
there.

`SqliteStore` and `ParquetStore` override it as before, and must: the file
alone is not the store for the first, and a byte copy is faster and exact for
the second.

**What changes for a user: a backup of a directory of files is now a copy of
its documents, not of its directory.** It was `shutil.copytree` until now. A
symbolic link, a file that is not UTF-8 text, a name that no key spells, and
the second of two files claiming one key are not documents - every read of that
store already passes them over - so they are no longer in the backup.
`outrage check` names three of the four; a link is the one it does not.

### `Store.copy_from`: every bulk move is a copy between two stores

New, and the shape the export, the import, the repack and the backup are being
folded onto. `store.copy_from(source, subtree, key_range=..., prefix=...,
on_conflict=..., dry_run=...)` writes every document the source holds in that
selection into `store`, yielding a `Transfer` per document as it goes.

A method on the **target** rather than a function over a pair, because the
target is what knows how it is written: a database takes a document at a time,
a file written whole takes all of them and writes once. Either end may be any
`Store`, so a copy out of a mount table spanning three files lands in one, and
a copy into one is routed to the store that owns each key. Metadata crosses as
the keys it is, and so does each document's `updated_at`.

**Breaking for library callers:** `Transfer` and the transfer vocabulary -
`SKIP`, `OVERWRITE`, `STOP`, `CONFLICTS`, `WROTE`, `SKIPPED`, `FAILED`, `READ`,
`STOPPED` - have moved from `outrage.bulk` to `outrage.store`, which is where
the operation they describe now lives. `outrage.bulk` keeps the file mapping
and the walkers. `Store.located(key, format)` is new beside them: the file a
store keeps a key in, or None where naming one would mean nothing, which is
what lets a transfer report key to path when a directory of files is one end.

### `outrage export` and `outrage import` are copies

Both are now thin wrappers over `copy_from` with a `FilesystemStore` on one
end, which is what they always were by hand. What changes for a user:

* **An import carries each file's modification time** as the document's
  `updated_at`, and an export sets each file's mtime from the document. The
  export/import round trip is lossless over content, format *and* timestamp; it
  used to stamp everything with the moment the import ran.
* **An import reports in key order**, not in the file walk's name order.
* **A conflict is decided by key**, at either end, so a document held as
  `a.md` collides with one arriving as json.
* **An export refuses to write through a symlink** at the target path rather
  than replacing it, and says so per document. It used to skip one under
  `skip` and replace it under `overwrite`.
* **What a tree does not hold as a document is no longer reported.** A
  symlink, a file that is not UTF-8 text, a name that no key spells, and the
  second file of two claiming one key are passed over silently, where the old
  file-by-file walk named each one. `FilesystemStore.check_file` knows all but
  the first, and nothing a person can run reaches it over a foreign tree yet.

`outrage pack` is unchanged and still builds through `ParquetStore.build`.

### Copying ranges from the command line

**`outrage copy SOURCE TARGET`** exposes `Store.copy_from` over the mounted
namespace. It selects the subtree at `SOURCE`, optionally bounded by `--depth`
and any combination of the six `KeyRange` cuts, and grafts every selected key
beneath `TARGET`. That makes a copy between mounted stores a single command,
with metadata and original timestamps crossing beside document content.

The existing `skip`, `overwrite` and `stop` conflict modes and `--dry-run`
apply unchanged. A target at or below the source is refused: the transfer is a
live stream rather than a snapshot, so otherwise it could discover and copy
what it had just written.

The shared mount-option help now correctly says that surveys and recursive
deletes cross mount boundaries; the previous text described the staging
behaviour retired when boundary crossing landed.

### A write may carry the timestamp it is copying

`Store.store_document` takes `updated_at`, an ISO 8601 timestamp normalised to
UTC at second precision; left out, it is now, which is what every ordinary
write means by it. It exists for the write that is a **copy** of a document
that already exists: a transfer between two stores carries the timestamp
across, or the copy says the whole corpus was written the moment it was
copied - the one fact about a document that nothing else can reconstruct. A
title written in the same call is stamped with it too.

Every backend honours it: SQLite writes the column, `ParquetStore.build`
records it, and a tree of files sets the file's mtime, which is what that
backend's `updated_at` *is*. Deliberately **not** offered by the MCP
`store_document` tool or by `outrage set` - a client writing a document is
writing it now.

### A `!` segment opens a metadata namespace

**Breaking**, and it changes what a metadata name *is*. A segment beginning
with `!` used to swallow everything below it: `a/!changelog/22` was metadata
called `changelog/22`, a key every read returned, no listing showed, and an
export dropped. It now opens a **namespace** on the key above it, inside which
everything is an ordinary namespace again - documents, `?`, `?last` and their
own metadata. So `a` carries `changelog`, `a/!changelog/22` is a document kept
inside it, and `a/!changelog/22/!title` is that document's title.

Metadata still changes exactly one thing, which is depth: `!` and everything
after it adds none, so `a`, `a/!changelog` and `a/!changelog/22/!title` are all
at depth 1. Levels and depth are therefore decoupled - a survey reaches a
namespace's contents by being *scoped* inside it, not by asking for more depth,
and that is what keeps depth across a mount boundary a constant offset.

What follows from it:

* **A survey descends into a metadata namespace only when scoped inside one.**
  `get_documents(meta_name=["title"])` at the root returns document titles, not
  the titles of things kept inside metadata. Scope it at `a/!changelog` to read
  those, and there `22` is a document and its `!title` is a title.
* `list_keys("a/!x")` lists what is in `a/!x`, and `?` and `?last` work at that
  level: `document/!changelog/?` allocates sequential notes.
* **A metadata key takes a `title`**, which becomes its own `!title`. Passing
  one used to be refused, on the grounds that metadata did not nest.
* **A delete of a key takes its whole metadata subtree** - one unit - and needs
  `recursive` for anything else below, a metadata namespace's contents
  included. `descendant_count` reports exactly what a plain delete would keep.
* **An export round-trips `a/!x/y`.** The shape on disk is the ordinary
  document-with-children one: `!x.md` beside the directory `!x/`.
* `outrage.keys.Key.meta_name` is now the **first** metadata segment only, with
  a new `meta_path` beside it carrying the remainder. **Breaking** for library
  callers reading `meta_name` on a key with a path below its first `!`; "this
  key is the metadata value" is `meta_name is not None and not meta_path`, and
  `Key.is_meta_value` says it in one place.
* `outrage.keys.relative(key, scope)` parses a key as it is named from inside a
  scope, which is what makes those questions answerable at any scope, and
  `outrage.keys.meta_range(key)` bounds the unit a plain delete takes.

**Stores are migrated, and no key moves.** SQLite goes to schema 6 in place,
rebuilding the table so a migrated file has exactly the schema a fresh one has.
A parquet file goes to format 2, and **a version 1 file is still read** - both
columns are derived from `key` on the way in, so nothing is repacked. A tree of
files is not versioned at all, because there the layout is the format and the
layout does not change.

### A mount table is now a `Store`, and `Mounts` is renamed

`outrage.mounts.Mounts` is `outrage.mounts.MountedStore`, and it implements
`outrage.store.Store`. **Breaking** for anything importing the old name; there
is no alias. Nothing about the command line or the MCP tools changes.

It means the routing, the level merge and the subtree traversal that make
several stores answer as one namespace are no longer the MCP server's - so a
mount table can go in front of anything that speaks to a `Store`, and the same
contract tests cover it as cover SQLite.

A table has no file of its own, and says so rather than answering for its root
mount: `path`, `backup`, `check` and `repair` raise `mount-has-no-file`. A
check of one store out of three would be a clean bill of health for the two
nobody looked at.

### A directory of files is now a `Store`

`outrage.store_files.FilesystemStore` reads and writes a tree with one file per
key - the mapping `outrage export` has always written, expressed as a store. A
segment is a path component and an extension names the format, so `a/b` stored
as markdown is `a/b.md` and everything below `a/b` is in `a/b/`.

It passes the same contract tests as SQLite, and is compared against it
directly: one corpus in both, the same battery of reads put to each, every
answer asserted equal.

A tree has no extension for `--store` to read, so it is not addressed by file
name yet and is constructed at its path. Reads walk the tree per call, which is
the right shape for an export target and the wrong one for a large corpus; the
module says so where it costs.

Three divergences, each covered by a test that names it: `.` and `..` are legal
keys and impossible paths, so they are refused on write; a key whose path
leaves the tree is refused; and a file that does not hold UTF-8 text is
reported rather than mangled into a document.

### The root document can be exported, and comes back

**Breaking** for anything relying on `outrage export` refusing the document at
the root. It now writes it as the file named by its extension alone - `.md` at
the top of the tree - and an import reads it back, dotfile skip or not. Before
this, exporting a store that had a document at its root reported one failed
transfer and dropped it.

### A key can no longer be exported outside the directory it was given

An export resolves each path it is about to write and refuses one that has left
the target tree. A symlinked directory anywhere along the path was enough
before this - no unusual key required - and the per-segment `..` check could
not see it. The same guard covers the two Windows shapes a segment can take:
one holding a backslash, which re-parses into components, and one holding a
colon, which becomes a drive letter.

### Six fixes at a mount boundary

* **A key with a mount below it listed as an empty container.** A document with
  a mounted store somewhere beneath it came back from `list_keys` as `implicit`,
  with no size, format or timestamp, while `retrieve_document` returned its
  content. A mount *point* shadows what is under it; a mount below a key does
  not.
* **A count across a boundary was short by two rows per mount.** The mount point
  itself and its metadata were left out, so the `remaining` on a non-recursive
  `delete_keys` told you to pass `recursive` for fewer keys than were there.
* **A failure at the root printed `''` instead of `/`.** An error was named with
  the owning mount's own outward function, which for the root mount is the
  identity, so the empty string reached the reader where the root's name should
  have been.
* **The count in "N key(s) lie beneath it" stopped at the store's edge.** The
  store answering counted its own rows, so everything held by a mount below the
  key was missing from the number - live in this project's own store, a key with
  20,000 rows beneath it reported 536.
* **A key whose only content is a mount below it read as empty.** No store holds
  a row at `lib` when the mount is at `lib/deep`, so `retrieve_document('lib')`
  raised `key-not-found`, whose sentence is "nothing is stored at or below" and
  which was untrue. It is now `key-is-a-container`, with the advice that finds
  the mount.
* **`level_entry` returned `None` for a key its own listing offers.** The same
  key: `list_keys` splices `lib` into the level above, and asking what that
  entry is got nothing back.

### A shortened delete preview counts what it previews

`outrage rm --recursive --dry-run --limit N` printed a trailing "and N more"
that was short by the key's own metadata, and **went negative** once the limit
reached past the ordinary children - "and -1 more" where one key was left. The
preview walks what a recursive delete takes; the number it was subtracted from
was `descendant_count`, which reports what a *plain* delete would keep and so
leaves that unit out. Two questions, one variable.

`outrage.store.Store.descendant_count` gains a keyword-only **`whole_subtree`**,
false by default, which asks the second one: everything strictly below the key,
its own metadata unit included. No existing call changes meaning, and the front
end now counts the set it walks. **Breaking** only for a third-party `Store`
implementation, which has to accept the keyword.

## 0.2.0 - 2026-08-24

**Breaking.** Everything still called `rage` is now `outrage`, and one on-disk
format changed with it. The rename was finished in one go, deliberately, while
the installed base is still small.

### Parquet stores written by 0.1.x no longer open

The key the format version is recorded under changed:

    rage.format-version  ->  outrage.format-version

A parquet store written by any earlier release now fails to open, reporting
`parquet-not-a-store` - which reads as though the file is not a store at all.
**There is no migration and none is planned.** Rebuild affected files with
`outrage pack` from the corpus they were packed from.

### The MCP server is named `outrage`, so every tool is renamed

`mcp__rage__*` tools are now `mcp__outrage__*`. Anything naming the old tools -
saved permissions, prompts, your own agent and skill files - needs updating.

**This one needs a manual step.** `outrage config` and `outrage init` write the
new `outrage` entry but cannot recognise the old `rage` one, so `.mcp.json`
ends up holding both. Delete the `rage` entry by hand: the `rage-server`
command it names no longer exists, so a client left with it will report a
server that fails to start.

### Environment variables

`RAGE_DIR` → `OUTRAGE_DIR`, `RAGE_LOG` → `OUTRAGE_LOG`.

**This changes behaviour silently.** An unset variable is a default, not an
error, so a shell profile still exporting the old names is ignored rather than
refused - the store directory quietly becomes `./.outrage` again.

`RAGE_TEST_INSTALLED` → `OUTRAGE_TEST_INSTALLED` (test suite only).

### Public API

`RageError` → `OutrageError`. It is the base of every error this package
raises, so `except RageError` stops compiling against 0.2.0.

### Skill and agents

The packaged skill `rage` is now `outrage`, and the three agents
`rage-annotate`, `rage-backfill` and `rage-search` are `outrage-*`.
`outrage init` installs the new names; the files under the old names are left
where they are and can be deleted.

### Fixed

* **`outrage init` no longer appends a second `SessionStart` hook** when it
  meets one written by an earlier release under a different product name. The
  marker is matched on its stable part, so an entry written by 0.1.x is
  recognised and replaced rather than duplicated, and duplicates left behind by
  an upgrade that already ran are collapsed. This is why the session hook is
  the one item above that needs no manual step.

## 0.1.2 - 2026-08-23

* `?last` names the newest key, on every tool that takes a key, and `?` is
  reserved as a segment prefix.
* The session-start hook points at the `readme` instead of prescribing a survey.
* A session-start hook for Copilot CLI, and `init` no longer discards
  configured mounts.
* Packaging is tested: the built sdist and wheel are checked for every packaged
  data file, and the version has a single source.

## 0.1.1 - 2026-08-22

* Fixed: the 0.1.0 wheel was missing `outrage/skills/`, so `outrage init`
  aborted on a clean install without writing anything.

## 0.1.0 - 2026-08-22

First release. 0.1.0 remains installable and its `init` is broken; use 0.1.1 or
later.
