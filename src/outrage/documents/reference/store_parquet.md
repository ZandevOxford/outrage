# outrage.store_parquet

The parquet backend: one columnar file, written once and read many times.

The second implementation of [`outrage.store.Store`](store.md#outrage.store.Store), and the one the
reference-base case is for: tens of thousands of small documents, built in one
pass rather than accumulated, and reached by survey and search. It answers the
same twelve operations [`SqliteStore`](store_sqlite.md#outrage.store_sqlite.SqliteStore) does, in the
same vocabulary, and shares none of the storage.

**It does not write.** A parquet file is not updated in place, so
[`store_document()`](#outrage.store_parquet.ParquetStore.store_document) and [`delete()`](#outrage.store_parquet.ParquetStore.delete) refuse
rather than pretend. Documents get in through [`ParquetStore.build()`](#outrage.store_parquet.ParquetStore.build),
which writes the whole file in one pass, and through `outrage pack`, which is
the command line over it. That refusal is the backend's own and not a mount's:
see [`outrage.store.ReadOnlyStoreError`](store.md#outrage.store.ReadOnlyStoreError) for the difference, which is that
no flag exists to take this one off.

The file is one row per key, carrying the columns
[`SqliteStore`](store_sqlite.md#outrage.store_sqlite.SqliteStore) keeps plus `chars`, sorted by
`sort_key`. Two of those are the whole design:

* **Sorted by \`\`sort_key\`\`** means every stretch of the key order this store's
  vocabulary can name -- a [`KeyRange`](store.md#outrage.store.KeyRange), a page cursor, a
  subtree -- is a *contiguous run of rows*. So a bound is found by bisecting
  rather than by testing every row, and the content of a page comes out of the
  one or two row groups it falls in. This is the columnar payoff.
* **\`\`chars\`\` is precomputed.** SQLite answers `total_chars` with
  `sum(length(content))`, which is per-row work over the column holding all
  the bytes. Written down at build time it is a small integer column, so
  **every total, and every listing, is answered without the content column
  being opened at all** -- `total_chars` over forty thousand documents costs
  a scan of a small integer column rather than of the corpus, and
  [`list_keys()`](#outrage.store_parquet.ParquetStore.list_keys) reports each entry's `size` from it.

  What that does *not* mean is that a survey reads no content. A survey
  returns the title text, and a title is a document like any other, so its
  rows are read -- but only the rows on the page, and never the documents
  being surveyed. The distinction is worth keeping straight, and
  `test_chars_is_stored_so_a_total_never_opens_the_content_column` pins
  which half is which.

What that buys is bounded by one thing worth knowing before reading further.
A [`Page`](store.md#outrage.store.Page) reports `total` and `total_chars` over the
whole *selection*, and a total over an arbitrary predicate cannot come from
row-group statistics -- it needs every row the predicate selects. So the
contract obliges this backend to hold the small columns whole, in memory, and
only `content` is read lazily. That is why `ParquetStore._index()` is
built once per file and `content` never joins it.

**How they are held is what decides how large a store can be.** They are the
file's own Arrow columns, searched by bisecting `sort_key` and converted a
row at a time for the rows an answer actually names. They were once a Python
object per key with three dictionaries over them, which measured at 865 bytes
a row -- fifteen times the file it came from, and 12.1 GB before a single read
of a seven-million-document reference base. Holding the columns instead is 120
bytes a row on the same corpus, and the eager dictionaries turn out to be
derivable from the order the file is already in: see `_Index`.

pyarrow is an optional dependency: `pip install outrage[parquet]`. It is
imported inside this module and this module is imported only by
`outrage.store._backend_for()`, so an install without it is unaffected until
something names a `.parquet` file.

### outrage.store_parquet.CHUNK *= 8192*

How many rows a chunked walk converts at a time. Big enough that the
per-call overhead of `to_pylist` is amortised away, small enough that the
Python strings it makes are freed long before the walk ends -- which is the
whole point of walking in chunks rather than converting a column.

### outrage.store_parquet.COMPRESSION *= 'zstd'*

How the content column is compressed. Reference text compresses very well
and zstd decompresses fast enough that a row group is cheap to open; it
ships in the pyarrow wheel, so this costs no further dependency.

### outrage.store_parquet.DEFAULT_STORE_FILE *= 'store.parquet'*

What a parquet store's file is called when a caller names none. Beside
[`outrage.store_sqlite.DEFAULT_STORE_FILE`](store_sqlite.md#outrage.store_sqlite.DEFAULT_STORE_FILE), each in its own module, and
it is the extension of this one that `outrage.store._backend_for()` reads
to know which backend a file wants.

### outrage.store_parquet.ENCODABLE *= ('format', 'updated_at')*

Columns worth dictionary encoding **if it helps**, tested rather than
assumed. In a store packed in one pass every row tends to carry the same
`updated_at` and one of three formats, and encoding those is 4 bytes a row
against 29; in a store imported from a corpus with a real timestamp per
document it is 4 bytes a row *on top* of the 29, so it is measured and kept
only when it wins. `key` and `sort_key` are never candidates -- they are
distinct by construction, and encoding them costs more than it saves every
time.

### outrage.store_parquet.FORMAT_VERSION *= 2*

The layout this build writes, recorded in the file's own key-value metadata
so a file from a later build is refused rather than read with the wrong
shape assumed. The same rule as [`outrage.store_sqlite.SCHEMA_VERSION`](store_sqlite.md#outrage.store_sqlite.SCHEMA_VERSION)
without the migrations: nothing here is ever updated in place, so an old
file is repacked rather than upgraded.

**Version 1 is still read**, and nothing is rewritten to do it. It has no
`meta_path` column and a `meta_name` written under the rule that a name
swallowed everything below the first `!`; both come off `key`, which the
file carries, so `ParquetStore._build()` derives them on the way in.

### outrage.store_parquet.BYTE_LENGTHS *= True*

Whether a pack writes `bytes`. On by default and omitted by `outrage pack
--no-byte-lengths`, and the only column here that is optional: `chars` is
what answers a total without opening `content`, so a file without it would
read every document to list a level.

**Written before anything reads it, which needs its reason.** Which of the
two lengths is expensive is a property of the storage: SQLite gets bytes
from a blob handle and a directory of files from `st_size`, while here
only the content column holds them. And a parquet file is never updated, so
a file packed without this can only gain it by being packed again -- unlike
the other two backends, where the same fact can be written down at any later
date for nothing. So it is written at the one moment it is cheap, for the
same reason `doc_key` and `parent` are written and not held: a column a
reader can recompute is still a column a query engine should not have to.

### outrage.store_parquet.HELD_COLUMNS *= ('key', 'meta_name', 'meta_path', 'format', 'updated_at', 'sort_key', 'chars')*

Of those, the ones actually read into memory. `doc_key` and `parent`
come off `key`, which the index is holding anyway, and between them they
were a quarter of what an open store cost. `doc_key` is derived where a
depth budget asks for it -- `ParquetStore._walked()`, the only question
anything asks of it -- and `parent` turns out not to be read by any read
at all: it was a denormalisation for listing a level, and a level is now
found by walking the order instead.

Both are written to the file all the same. The file is read by other things,
a column a reader can recompute is still a column a query engine should not
have to, and [`ParquetStore.audit_rows()`](#outrage.store_parquet.ParquetStore.audit_rows) checks the written ones against
the keys they claim to describe.

### outrage.store_parquet.INDEX_COLUMNS *= ('key', 'doc_key', 'meta_name', 'meta_path', 'parent', 'format', 'updated_at', 'sort_key', 'chars', 'bytes')*

The columns held whole once a file is opened: everything except `content`.
Naming them is what keeps the promise in the module docstring checkable --
the expensive column is absent from this list, and every read that does not
return document text stops here.

### outrage.store_parquet.PROBE *= 8*

How far a child walk probes forward before it gives up and bisects. Most
keys have a handful of rows beneath them -- a document, its title, perhaps a
note -- so the next sibling is usually two or three rows along and a linear
step finds it for the cost of one comparison. A bisect costs about twenty.
Past this many steps the subtree is big enough that the bisect is cheaper,
and the walk stops guessing. See `_Index.children()`.

### outrage.store_parquet.ROW_GROUP_SIZE *= 2048*

Rows per row group. The unit parquet reads content in, so it is the unit a
page's text is paid for in: too large and a five-document read decompresses
thousands, too small and the per-group statistics and headers outweigh the
data they describe. Sized for the reference case, where a document is a few
hundred characters and a page is tens of them.

### outrage.store_parquet.VERSION_KEY *= b'outrage.format-version'*

Where that version is written.

### *class* outrage.store_parquet.ParquetStore(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, filename: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None, mount_point: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)

Bases: [`FileStore`](store.md#outrage.store.FileStore)

A document store held in a single parquet file, read only.

#### default_filename *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[str](https://docs.python.org/3/library/stdtypes.html#str)]* *= 'store.parquet'*

What this backend calls its store file when a caller names none. Set by
every concrete backend, and the only thing about the file a backend
decides: that it *is* a file inside a directory is settled above, by
`store_file()`. `default_store_file()` is how the rest of the
package asks for it without naming a backend to ask.

#### backend_name *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[str](https://docs.python.org/3/library/stdtypes.html#str)]* *= 'parquet'*

What this backend is called where a report or a refusal has to name it.
A short lowercase word, matching the store file's extension, so that a
sentence about a store and the name of its file agree.

#### format_version *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[int](https://docs.python.org/3/library/functions.html#int)]* *= 2*

The version of its own on-disk format this build writes. Compared
against [`stored_format_version`](#outrage.store_parquet.ParquetStore.stored_format_version) by [`outrage.maintenance.check()`](maintenance.md#outrage.maintenance.check),
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

Drop the file handle and the index built over it.

Safe more than once, which the contract requires and a store held by a
mount table relies on: the table closes everything it opened when a
single failure part way through means unwinding.

Only this thread's handle, for the reason `_parquet()` gives. The
rest are released when their thread ends or the process exits.

#### store_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), content: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, title: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, contents: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, encoding: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, updated_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)

Refused: a parquet file is not updated in place.

Validated first, then refused, and the order is deliberate. A caller
who passed a malformed key and a caller who passed a good one are
asking different questions, and answering both with "this store does
not write" hides a bug behind a limitation -- the argument would be
just as wrong against the store they meant to write to. So this calls
`Store._validated()` exactly as a writing backend does, and every
refusal in it happens here too.

Logged like any other write, and for the same reason: what the event
log is for is what a store was *asked* to do, and a refused write is
one of the more interesting things anyone asks. `_logged` records the
refusal beside the arguments and re-raises.

[`build()`](#outrage.store_parquet.ParquetStore.build) is the way in, and `outrage pack` is the command line
over it.

#### delete(key: [str](https://docs.python.org/3/library/stdtypes.html#str), recursive: [bool](https://docs.python.org/3/library/functions.html#bool) = False, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, unchanged_since: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

Refused, for the reason [`store_document()`](#outrage.store_parquet.ParquetStore.store_document) is.

Before the watermark is looked at rather than after: a store that
cannot delete anything refuses whether or not the subtree moved, and
checking first would answer a caller's second question while leaving
their first one to a different sentence.

`dry_run` is refused with the rest of it. A preview whose answer is
"these keys would go" from a store where they never could is the one
thing a preview must not say.

#### exists(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [bool](https://docs.python.org/3/library/functions.html#bool)

One bisect, over the index rather than the file.

#### level_entry(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Entry](store.md#outrage.store.Entry) | [None](https://docs.python.org/3/library/constants.html#None)

The stored row if there is one, else whether anything lies below.

The second half is two bisects rather than a scan, and it finds an
implicit key the same way the listing does -- see
`_Index.has_children()`.

#### descendant_count(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [int](https://docs.python.org/3/library/functions.html#int)

How many rows lie strictly below `key`, within `key_range`.

Counted over the index. The subtree is a stretch of the order and the
range is bisected; what is left per row is whether the key is one a
plain delete of `key` would *keep*, which the bounds narrow but do
not answer -- and under `whole_subtree` there is nothing left to ask,
since the bisected stretch is the answer.

#### latest_change(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)

The newest `updated_at` over the rows [`descendant_count()`](#outrage.store_parquet.ParquetStore.descendant_count) counts.

The same bisected stretch and the same per-row question, taking a
maximum instead of a total. Two columns are converted rather than one,
in step and a chunk at a time: the timestamp is only wanted for a row
the key test keeps, and pairing them is what says which row it belongs
to.

#### retrieve_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, offset: [int](https://docs.python.org/3/library/functions.html#int) = 0, byte_offset: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, length: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, pattern: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, occurrence: [int](https://docs.python.org/3/library/functions.html#int) = 0, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_MAX_CHARS) → [Excerpt](store.md#outrage.store.Excerpt)

One index lookup, one row group, and the shared slicing.

The slicing is `outrage.store._excerpt()`, unchanged and unwrapped:
how `length` and `max_chars` combine is the store's policy and not
this backend's, and two backends that sliced differently would return
different documents for the same call.

**A byte offset is honoured and not accelerated**, which the plan says
rather than implying parity: a row's value is decompressed whole out of
its row group and there is no sub-value addressing to reach for. So the
content is encoded and sliced, which costs what it costs and answers
the same bytes as a backend that seeks.

#### list_keys(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, descendant_counts: [bool](https://docs.python.org/3/library/functions.html#bool) = False, descendant_chars: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Page](store.md#outrage.store.Page)[[Entry](store.md#outrage.store.Entry)]

One level, real and implicit keys together, walked in order.

`_Index.children()` yields both kinds in key order -- which is the
order the file is already in, so nothing is sorted here. That is the
difference this shape makes: the layout it replaced held a set of every
child of every key, and then called `sort_form` on every name in the
level on every call. At two hundred thousand keys a listing of the root
took most of a second, all of it re-deriving an order the file was
already written in.

**One pass, and it holds a page.** The totals are over the whole level
and so unaffected by the cursor, which means the level has to be walked
whatever happens; what does not have to happen is an `Entry` per key
surviving that walk. Only the page's worth is kept, plus one more --
which is how `more` is known without counting the rest twice.

The characters come from `chars` without any content being read.

The descendant flags are filled over the page afterwards, one
`_subtree_totals()` per child, and are the one part of this that is
linear in the subtree rather than in the level.

#### get_documents(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_BULK_MAX_CHARS, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, max_total_chars: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[Excerpt](store.md#outrage.store.Excerpt)]

The selection, then the page cut out of it against the two caps.

The totals come from the selection and the page from the cursor into
it, which is the same split SQLite makes with a separate `count(*)`:
a cursor moves as a caller pages and must not reach `total`.

**\`\`total_chars\`\` is answered from \`\`chars\`\` and touches no content.**
The page's documents are then read one row group at a time, so a survey
-- which returns metadata, and whose documents are short -- opens the
content column for a page's worth of rows and no more.

#### missing_meta_stats(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, window: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', sample: [int](https://docs.python.org/3/library/functions.html#int) = 0) → [MissingMeta](store.md#outrage.store.MissingMeta)

Documents carrying none of `meta_name`, over one window.

The window is measured at the position a document's metadata *would*
have taken, not at the document's own -- the contract says so, and
`test_survey_windows_tile_over_adversarial_keys` is the guard. That
synthesised position is `sort_key` plus a fixed suffix, which is
monotone in `sort_key`, so the rows satisfying a bound on it are
still a contiguous run and this still bisects. SQLite cannot: the
concatenation is not sargable there, so it scans the selection and pays
about 6% for it. Here the ordering does the work.

#### keys_missing_meta(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

The same selection [`missing_meta_stats()`](#outrage.store_parquet.ParquetStore.missing_meta_stats) counts, listed.

Shared rather than reimplemented, for the reason the SQLite backend
shares its `NOT EXISTS`: the survey, its count and the list of what
it could not see have to agree about what was in range, and two
expressions of the same predicate are two chances to disagree.

#### backup(destination: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Backup](store.md#outrage.store.Backup)

A file copy, and a re-read to show it is one.

**The file really is the store here**, which is the difference from
SQLite worth stating out loud. There is no WAL and no journal, so
nothing has been written anywhere else and a copy cannot be silently
short. The trap where a WAL lets a plain file copy succeed and be stale
is SQLite's rather than the store's, and this is the evidence.

The copy is still verified rather than assumed. What can go wrong is
the copy itself: a truncated write, a full disk. So the copy is
reopened, its version read and its rows counted against the source, on
the principle the SQLite backend states -- a copy that opens cleanly is
not evidence of a complete one.

#### *property* stored_format_version *: [int](https://docs.python.org/3/library/functions.html#int)*

From the file's own key-value metadata, where `build` wrote it.

`_check_version` has already refused anything newer than this build
by the time a check can run, so the error branch of
`maintenance._check_format_version` is unreachable here -- see the
note there. A file older than this build still opens, and still says
so.

#### audit_rows() → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[AuditRow](store.md#outrage.store.AuditRow)]

Every row **as the file stores it**, streamed a row group at a time.

From the file rather than from the index, and the difference is the
point. The index no longer holds `doc_key` or `parent` -- which is
what makes an open store a quarter of what it used to cost -- and what
it does not hold it cannot check. Worse, both come off `key`, and a
value derived from a key can never disagree with it. A check reading
the index would therefore pass unconditionally on exactly the defect
`_report_parents` exists to find -- a stored `parent` that does not
match its key, written by something that was not this build -- and
would report a clean file while saying nothing.

So this reads the stored columns. It is the one caller that wants what
is *written down* rather than what is true, and it is a check, which
is allowed to be the expensive path. `iter_batches` streams, so a
corpus that does not fit in memory is still checked without it.

`chars` is the column this backend has and SQLite does not, precisely
so that counting characters never costs a read of the text -- and this
never opens `content` either.

#### check_file(report: [Report](maintenance.md#outrage.maintenance.Report)) → [None](https://docs.python.org/3/library/constants.html#None)

Whether the file is still in the order every read of it assumes.

This is parquet's `integrity_check`, and it exists for the same
reason: a file that fails it reads *wrongly* rather than failing to
read. Every lookup here bisects `sort_key` -- that is what makes a
bounded range 0.04 ms rather than 14 -- and bisection over rows that
are not sorted returns a confidently wrong answer with nothing
anywhere to contradict it.

Cheap enough to do unconditionally: one pass over a column that is
resident already, against a file that promised to be sorted when it
was written.

#### repair() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Repaired](maintenance.md#outrage.maintenance.Repaired)]

Nothing, and that is the honest answer rather than a silence.

A repair moves bytes about inside a mutable file: a checkpoint folds a
sidecar back, a vacuum compacts free pages. A parquet store is one
immutable file with no sidecar and no free pages, so there is no state
it can reach that moving bytes would fix -- which is *provable* here,
and so different in kind from "nothing to check", a sentence that would
read as a clean bill of health for a store nothing looked at.

A file that fails [`check_file()`](#outrage.store_parquet.ParquetStore.check_file) is not repaired but rebuilt, by
`outrage pack`, from a source that is still right.

#### *classmethod* check_target(path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

Where a build would write, refusing a file already there.

Public and separate from [`build()`](#outrage.store_parquet.ParquetStore.build) so a caller can hit the refusal
**before** reading its source. A pack reads the whole corpus before it
writes anything, so leaving this to the write means a refusal that
arrives after forty thousand documents have been read - which is the
right answer delivered at the least useful moment. `build` calls it
too, so the guarantee does not depend on the caller remembering.

#### *classmethod* build(path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], documents: [Iterable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterable)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]], \*, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False, byte_lengths: [bool](https://docs.python.org/3/library/functions.html#bool) = BYTE_LENGTHS) → [int](https://docs.python.org/3/library/functions.html#int)

Write a whole parquet store in one pass, and return the row count.

`documents` yields `(key, content, format, updated_at)`. A format
of None is detected from the content and an `updated_at` of None is
now, so a caller with a directory of files supplies neither and a
caller copying an existing store supplies both -- which is what lets
`outrage pack` keep timestamps when packing a store and invent them when
packing a tree.

Every key goes through `Store._validated()`, the same check a
writing backend applies, because this is where a document enters the
namespace and a build that admitted a key `store_document` would
refuse would make this file a second namespace. A `?` is refused
rather than allocated: allocation reads the store to find a free number
and there is no store to read yet, and a number allocated against a
half-written file would not be the one a reader later sees.

**The rows are held before they are written.** They must be sorted by
`sort_key` for anything above to bisect, and a sort needs all of
them. For the corpus this is for -- tens of thousands of small
documents -- that is a few hundred megabytes at worst and one pass; a
corpus past that wants an external sort, and this should say so rather
than quietly swapping.
