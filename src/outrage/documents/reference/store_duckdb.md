# outrage.store_duckdb

The duckdb backend: a directory of parquet parts, read as one store.

The fourth implementation of [`outrage.store.Store`](store.md#outrage.store.Store), and the one for a
reference base **too large for one file, or that arrives in pieces**. Each part
is a file `outrage pack` could have written -- the same columns and the same
format stamp as [`outrage.store_parquet`](store_parquet.md#module-outrage.store_parquet) -- and the store is every part
together. Nothing about the file format is redefined here.

**The parts may be in any order.** Not sorted, not disjoint. A store is in sort
order, but the source it was made from need not be: a producer holding its
corpus in page-id order, or crawl order, or one file per batch, cannot be asked
to sort across files before it can be read. That is what rules out answering
this with the parquet backend's own reads, which bisect a single sorted file
and hold its small columns resident to do it -- over parts in arbitrary order
that index would have to be merged at open and held over the whole corpus. Here
nothing is held between queries but duckdb's own buffers, and **what this
costs does not grow with the corpus**, which is the reason to have it. Reads are
slower than the parquet backend's -- several milliseconds where a bisect is
microseconds -- and every one of them is still far below the round trip of the
tool call carrying it.

**A directory names it**, and has no extension to name its backend, so it is
always asked for: `ref=refbase,type=duckdb`. The parts are the `.parquet`
files directly inside it, less dotfiles, which is what a producer writing a
part under a temporary name and renaming it into place needs. **The list is
taken when the store is opened**, and the store is those parts until it is
opened again: a part appearing later is picked up by the next open, and a part
half written while a store is being read is never read at all.

**A key held in more than one part is held more than once**, and nothing
resolves it. The store is the concatenation of its parts: reading the rows --
[`DuckdbStore.get_documents()`](#outrage.store_duckdb.DuckdbStore.get_documents), [`DuckdbStore.keys_missing_meta()`](#outrage.store_duckdb.DuckdbStore.keys_missing_meta) --
returns a repeated key once per row, their totals count rows, and every row is
reachable. Reading the *key* -- [`DuckdbStore.retrieve_document()`](#outrage.store_duckdb.DuckdbStore.retrieve_document),
[`DuckdbStore.exists()`](#outrage.store_duckdb.DuckdbStore.exists), [`DuckdbStore.level_entry()`](#outrage.store_duckdb.DuckdbStore.level_entry) -- answers with the
newest of them, and so does a listing, since a listing entry is by contract
what [`level_entry()`](#outrage.store_duckdb.DuckdbStore.level_entry) says about that key. What removes the
repeats is compaction, which is packing the directory into one file, and not
anything here.

What repeated rows do need is a rule about pages, because **a cursor names a
key and never a position**: two rows sharing a key cannot be told apart by one,
so a page ending between them would resume past both or before both. So **a
page never ends inside a run of one key**. It stops before the run and returns
fewer than `limit`, which a limit allows; and where one run is longer than a
whole page it returns the whole run, which is the only case in which
`returned` exceeds `limit`. That run is as long as the number of parts
repeating the key, and it overruns `max_total_chars` the way a first document
larger than the budget already does, for the same reason -- anything smaller
is a page that cannot move. A mount table pages across stores by asking each
for its own pages and never cutting one, so the rule holds through a mount with
nothing there knowing about it.

**It does not write**, like the parquet backend and for a related reason: the
directory changes by gaining a part, which is a file somebody else writes, and
nothing here updates a part in place. So [`store_document()`](#outrage.store_duckdb.DuckdbStore.store_document)
and [`delete()`](#outrage.store_duckdb.DuckdbStore.delete) refuse, and the refusal is the storage's rather
than a mount's.

**Every part must be in the same format version, and it must be this build's.**
A version 1 part carries no `meta_path` column and splits `meta_name`
under an older rule; reading one would mean re-deriving that split in SQL,
which is a second definition of the key grammar. So an older part is refused
with the advice to repack it, and a directory mixing versions -- a repack left
half done -- is refused naming both.

duckdb is an optional dependency: `pip install outrage[duckdb]`. It is
imported inside this module, and this module only when something names the
backend, so an install without it is unaffected until then. pyarrow is not
needed to read a directory; only building a part is its business.

### outrage.store_duckdb.AUDIT_CHUNK *= 8192*

Rows audited at a time. The same figure the parquet backend walks in, for
the same reason: large enough to amortise a fetch, small enough that the
rows are freed long before the walk ends.

### outrage.store_duckdb.BATCH *= 64*

How many rows a page's read asks for when the caller named no limit, and
what a run of reads grows from. Doubled on each further read up to
[`BATCH_CEILING`](#outrage.store_duckdb.BATCH_CEILING), so a short page costs one small query and a long walk
does not cost one query per handful of rows.

### outrage.store_duckdb.BATCH_CEILING *= 4096*

The largest read [`BATCH`](#outrage.store_duckdb.BATCH) grows to.

### outrage.store_duckdb.DEFAULT_STORE_DIR *= 'parts'*

What a duckdb store's directory is called when a caller names none. It has
no extension because a directory has none to give, which is why this backend
is always named rather than inferred.

### outrage.store_duckdb.MEMORY_LIMIT *= '1GB'*

The ceiling on what duckdb may hold in memory. Set because its own default
is most of the machine's RAM, which is the wrong answer for a server sharing
a machine with the editor it serves. Measured to make almost no difference to
what it actually holds -- a reference base of 2.7 million rows sat near 140 MB
whatever this said -- and every read here is bounded by a key rather than an
offset, so none of them sorts a whole selection to reach a page.

### outrage.store_duckdb.PART_SUFFIX *= '.parquet'*

What a part's file name ends with. The only files in the directory that are
read; anything else there is left alone.

### *class* outrage.store_duckdb.DuckdbStore(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, filename: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None, mount_point: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)

Bases: [`FileStore`](store.md#outrage.store.FileStore)

A document store held as a directory of parquet parts, read only.

#### default_filename *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[str](https://docs.python.org/3/library/stdtypes.html#str)]* *= 'parts'*

What this backend calls its store file when a caller names none. Set by
every concrete backend, and the only thing about the file a backend
decides: that it *is* a file inside a directory is settled above, by
`store_file()`. `default_store_file()` is how the rest of the
package asks for it without naming a backend to ask.

#### backend_name *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[str](https://docs.python.org/3/library/stdtypes.html#str)]* *= 'duckdb'*

What this backend is called where a report or a refusal has to name it.
A short lowercase word, matching the store file's extension, so that a
sentence about a store and the name of its file agree.

#### format_version *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[int](https://docs.python.org/3/library/functions.html#int)]* *= 2*

The version of its own on-disk format this build writes. Compared
against [`stored_format_version`](#outrage.store_duckdb.DuckdbStore.stored_format_version) by [`outrage.maintenance.check()`](maintenance.md#outrage.maintenance.check),
which is why the comparison is written once rather than per backend --
"written by a newer outrage than this" is the same fault whatever wrote it,
even though each backend records the number somewhere different.

#### writable *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[bool](https://docs.python.org/3/library/functions.html#bool)]* *= False*

Whether this backend can be written at all. False says the *storage*
refuses, which is not the same as a store that was mounted read-only:
a mount's refusal comes off with a flag and this one does not. A caller
deciding whether to offer a write reads this; a caller that writes
anyway gets `ReadOnlyStoreError` from the backend, since a class
var nobody consulted must not be the only thing standing between a
corpus and a half-written file.

#### close() → [None](https://docs.python.org/3/library/constants.html#None)

Drop the database, and every thread's cursor into it with it.

Safe more than once. Unlike the parquet backend, which closes only this
thread's file, this closes the one database every cursor is a
connection to -- duckdb has no other way to give the memory back -- so
a thread still mid-read when the store is closed has that read fail.
That is the same promise a mount table already keeps by closing a store
only once nothing is serving it. The next read from any thread opens a
new database and carries on.

#### store_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), content: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, title: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, contents: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, encoding: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, updated_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)

Refused: a part is added by writing a file, not through a store.

Validated first, then refused, for the reason
[`outrage.store_parquet.ParquetStore.store_document()`](store_parquet.md#outrage.store_parquet.ParquetStore.store_document) gives: a
malformed argument is a bug, and "this store does not write" would hide
it behind a limitation.

#### delete(key: [str](https://docs.python.org/3/library/stdtypes.html#str), recursive: [bool](https://docs.python.org/3/library/functions.html#bool) = False, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, unchanged_since: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

Refused, dry run included, for the reason [`store_document()`](#outrage.store_duckdb.DuckdbStore.store_document) is.

#### exists(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [bool](https://docs.python.org/3/library/functions.html#bool)

Whether any part holds a row at `key`.

#### level_entry(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Entry](store.md#outrage.store.Entry) | [None](https://docs.python.org/3/library/constants.html#None)

The newest row at `key` if there is one, else whether anything lies below.

The newest rather than one per row, although a listing shows each: this
answers how one key appears, and a caller reconciling it against
another store's level wants one answer for one key.

#### descendant_count(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [int](https://docs.python.org/3/library/functions.html#int)

A count of the rows below `key`, less the metadata unit a delete takes.

The SQLite backend's query over the parts, and deliberately the same
predicates: `outrage.store_sqlite._below()` and
[`outrage.keys.meta_range()`](keys.md#outrage.keys.meta_range) say which keys, and a count here that
drew the line elsewhere would be a second meaning of "below". A key
repeated across parts counts once per row.

#### subtree_totals(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, chars: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [SubtreeTotals](store.md#outrage.store.SubtreeTotals)

One aggregate over the subtree: rows, documents, and optionally characters.

Documents are the rows with no `meta_name`, which the column records
for every row below a metadata segment -- the definition
[`SubtreeTotals`](store.md#outrage.store.SubtreeTotals) states. The characters come from
`chars`, so a total never reads a document; they stay behind the flag
all the same, because a surface that is opt in on one backend and
always on in another is two contracts wearing one name.

#### latest_change(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)

The newest `updated_at` over the rows [`descendant_count()`](#outrage.store_duckdb.DuckdbStore.descendant_count) counts.

#### retrieve_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, offset: [int](https://docs.python.org/3/library/functions.html#int) = 0, byte_offset: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, length: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, pattern: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, occurrence: [int](https://docs.python.org/3/library/functions.html#int) = 0, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_MAX_CHARS) → [Excerpt](store.md#outrage.store.Excerpt)

The newest row at `key`, sliced by the shared slicing.

**A byte offset is honoured and not accelerated**, as in the parquet
backend: a value comes out of its part whole, so the content is
encoded and sliced, and answers the same bytes a backend that seeks
does.

#### list_keys(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, descendant_counts: [bool](https://docs.python.org/3/library/functions.html#bool) = False, descendant_chars: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Page](store.md#outrage.store.Page)[[Entry](store.md#outrage.store.Entry)]

One level, grouped from the rows below it.

Each row below `key` names the child it is under by its next segment,
and grouping on that names the level: a child whose own key is among
its rows is stored, and one whose rows all lie beneath it is implicit.
**This reads the subtree rather than the level**, which is the one
read here whose cost is not bounded by what it returns. The parquet
backend bisects past each child's run; SQL has no bisect-and-skip, so
a level costs its subtree. Listing the root groups the whole store.

**A key is listed once, whatever number of parts hold it**, as the
newest of its rows -- the entry [`level_entry()`](#outrage.store_duckdb.DuckdbStore.level_entry) gives for it, which
is the contract: that method answers how one key appears in this
listing. So `total` counts keys and `total_chars` their newest rows.
The repeats stay visible where rows are read, in [`get_documents()`](#outrage.store_duckdb.DuckdbStore.get_documents)
and [`keys_missing_meta()`](#outrage.store_duckdb.DuckdbStore.keys_missing_meta), and are counted by
[`subtree_totals()`](#outrage.store_duckdb.DuckdbStore.subtree_totals), so a listing's `descendants` counts every row
below an entry.

Two queries: the totals over the whole level, then the page, ordered
and cut at the cursor. Each child's newest row comes out of the same
grouping, so a page reads nothing further.

#### get_documents(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_BULK_MAX_CHARS, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, max_total_chars: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[Excerpt](store.md#outrage.store.Excerpt)]

The selection's totals from one aggregate, and a page read in order.

The selection is the SQLite backend's predicate, which is why a total
here and a total there can be compared at all. The page is read a
batch at a time past the cursor rather than in one query, so that the
two caps -- `limit` and `max_total_chars` -- decide how much is
read, and `_page()` decides where it ends.

#### missing_meta_stats(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, window: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', sample: [int](https://docs.python.org/3/library/functions.html#int) = 0) → [MissingMeta](store.md#outrage.store.MissingMeta)

Documents carrying none of `meta_name`, over one survey window.

The window is measured at the position the document's metadata *would*
have taken, synthesised in SQL exactly as the SQLite backend does it --
see [`outrage.store_sqlite.SqliteStore.missing_meta_stats()`](store_sqlite.md#outrage.store_sqlite.SqliteStore.missing_meta_stats) for why
it is that position and not the document's own.

#### keys_missing_meta(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

The selection [`missing_meta_stats()`](#outrage.store_duckdb.DuckdbStore.missing_meta_stats) counts, listed a page at a time.

A document repeated across parts is listed once per row, like any
other listing here, and paged by the same rule.

#### backup(destination: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Backup](store.md#outrage.store.Backup)

A copy of every part into a directory of its own, and a re-read of it.

The parts are the store, so copying them is the whole copy, and the
parts copied are the ones this store opened -- not whatever the
directory holds by now. The copy is then opened as a store of its own,
which checks every part's format, and its rows counted against these.

#### *property* stored_format_version *: [int](https://docs.python.org/3/library/functions.html#int)*

The version every part carries, which opening has checked they agree on.

#### audit_rows() → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[AuditRow](store.md#outrage.store.AuditRow)]

Every row every part holds, as written, a chunk at a time.

On a cursor of its own rather than the thread's: a caller walking this
may ask the store something else between two rows, and a query on the
same cursor would end the one this is still reading.

#### check_file(report: [Report](maintenance.md#outrage.maintenance.Report)) → [None](https://docs.python.org/3/library/constants.html#None)

How many parts, how many rows, and how many of them repeat a key.

Order is not checked, because nothing here depends on it: the parquet
backend checks its file is sorted since every read of it bisects, and
every read here is a query. A repeated key is not a problem either --
it is legal, and a listing shows it -- so it is reported as the number
of rows compacting the directory into one file would remove.

#### repair() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Repaired](maintenance.md#outrage.maintenance.Repaired)]

Nothing, and provably so.

A part is never updated in place, so there is no state a repair could
move bytes about to fix. A part that is wrong is rebuilt from a source
that is still right, and a directory with repeated keys is compacted by
packing it into one file.
