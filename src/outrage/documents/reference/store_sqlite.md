# outrage.store_sqlite

The SQLite backend: one database file, one row per key.

The read-write implementation of [`outrage.store.Store`](store.md#outrage.store.Store), and the one a store
is opened as when its file says nothing else. Everything specific to SQLite
lives here -- the schema and its
migrations, the connection handling, and the SQL that every read and write is
expressed as -- so that [`outrage.store`](store.md#module-outrage.store) says what a store *is* without saying
how this one is kept.

The split was not speculative tidiness, and [`outrage.store_parquet`](store_parquet.md#module-outrage.store_parquet) is the
evidence: the parts of this module that did not survive a second backend are
exactly the parts that are here -- a row-per-key table with secondary indexes,
`NOT EXISTS` against a self-join, and a connection per thread -- while every
word of the vocabulary above was inherited unchanged. That vocabulary is keys,
ranges, subtrees, pages and excerpts, and it is backend independent because it
is about the namespace rather than about storage.

Read this one against [`outrage.store_parquet`](store_parquet.md#module-outrage.store_parquet) where the two answer the same
question differently. `_range_clauses` compiles a range to a predicate
because a row-per-key table evaluates one; the parquet backend bisects a sorted
file instead, and the two are written to be read side by side.

Nothing here is imported by a caller that only wants to read and write
documents: [`outrage.store.default_store()`](store.md#outrage.store.default_store) is what chooses this class, and it
is the one place in the package that names a backend.

### outrage.store_sqlite.BUSY_TIMEOUT_MS *= 5000*

How long a writer waits for another writer to finish before giving up, in
milliseconds. SQLite's own default is zero -- a busy database fails on the
spot rather than waiting -- which is invisible with one connection and the
usual cause of spurious "database is locked" with several. Generous, because
every write here is small and the alternative to waiting is an error.

### outrage.store_sqlite.DEFAULT_STORE_FILE *= 'store.sqlite'*

What a SQLite store's file is called when a caller names none. The name a
parquet backend's default sits beside, each in its own module, neither
needing a qualifier to say which storage it is for. That a store *is* a file
inside a directory is not decided here -- see [`outrage.store.store_file()`](store.md#outrage.store.store_file);
only what this backend calls one.

### outrage.store_sqlite.LENGTH_CACHE_TABLE *= 'document_lengths'*

Where the cache of document lengths lives, and the columns it holds. Not
part of `_SCHEMA` and not behind a schema version: it is a cache, so a
missing row is answered by counting and a store that has never been opened
by a build that knows about it is merely slower. That is what lets
[`SCHEMA_VERSION`](#outrage.store_sqlite.SCHEMA_VERSION) stay where it is, and an older build go on writing
this store rather than refusing it.

### outrage.store_sqlite.LENGTH_THRESHOLD *= 2048*

How long a document has to be before its length is worth writing down.
Measured rather than guessed, over this project's own store: the saving on a
subtree total is flat from 128 characters to here -- around 63% -- and falls
away above it, because what a threshold buys is the *characters* it covers
and not the rows. At this value a quarter of the rows carry nine tenths of
the text. Notably it is not the page size, so the tempting derivation from
`PRAGMA page_size` would have been wrong: counting characters decodes the
whole string whether or not the row spilled onto an overflow page.

### outrage.store_sqlite.SCHEMA_VERSION *= 6*

The schema this code writes, and the version a store is migrated up to when
it is opened. Every bump needs a migration that reads the version below it;
an older store is upgraded in place, and a newer one is refused rather than
read with the wrong shape assumed.

### outrage.store_sqlite.WAL_RATIO *= 1.0*

When the sidecar is worth reporting. A WAL always holds something between
checkpoints; it is only interesting once it holds more than the database it
belongs to, which is the state that makes a file copy lose real content.

### *class* outrage.store_sqlite.SqliteStore(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, filename: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None, mount_point: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)

Bases: [`FileStore`](store.md#outrage.store.FileStore)

A document store held in a single SQLite database.

#### default_filename *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[str](https://docs.python.org/3/library/stdtypes.html#str)]* *= 'store.sqlite'*

What this backend calls its store file when a caller names none. Set by
every concrete backend, and the only thing about the file a backend
decides: that it *is* a file inside a directory is settled above, by
`store_file()`. `default_store_file()` is how the rest of the
package asks for it without naming a backend to ask.

#### backend_name *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[str](https://docs.python.org/3/library/stdtypes.html#str)]* *= 'sqlite'*

What this backend is called where a report or a refusal has to name it.
A short lowercase word, matching the store file's extension, so that a
sentence about a store and the name of its file agree.

#### format_version *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[int](https://docs.python.org/3/library/functions.html#int)]* *= 6*

The version of its own on-disk format this build writes. Compared
against [`stored_format_version`](#outrage.store_sqlite.SqliteStore.stored_format_version) by [`outrage.maintenance.check()`](maintenance.md#outrage.maintenance.check),
which is why the comparison is written once rather than per backend --
"written by a newer outrage than this" is the same fault whatever wrote it,
even though each backend records the number somewhere different.

#### writable *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[bool](https://docs.python.org/3/library/functions.html#bool)]* *= True*

Stated rather than inherited. The default is True, so a backend that
forgets reports itself writable -- which is the wrong way round for a
mistake to fall, and test_every_backend_states_whether_it_can_be_written
is why this is here rather than left to the base.

#### *property* connection *: [Connection](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection)*

The open database, for asking questions about the file itself.

**Nothing inside the package reaches through this any more.** It was
exposed for [`outrage.maintenance`](maintenance.md#module-outrage.maintenance), which asked SQLite about integrity
and the write-ahead log from outside; those are now answered by
[`check_file()`](#outrage.store_sqlite.SqliteStore.check_file) here, off `_conn` directly, because they are
questions about *this* storage and have no meaning for any other.

Kept public for a caller outside the package with a question about the
database that no method answers, and because the tests ask them. It is
not a way in: reaching through it to read or write documents defeats
every guarantee the methods above make.

#### close() → [None](https://docs.python.org/3/library/constants.html#None)

Close this thread's connection.

Only this thread's: SQLite refuses to let one thread touch another's
connection at all, closing included, which is the same rule that makes
the per-thread connections safe in the first place. The rest are
released when their thread ends or the process exits -- the lifetime
the one shared connection effectively had anyway.

#### store_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), content: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, title: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, encoding: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, updated_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)

One row per key, upserted, with the title written in the same
transaction.

The transaction is `IMMEDIATE` only when a `?` has to be allocated:
that path reads the level before it writes, and a deferred transaction
would let two callers read the same highest number and pick it twice.

A caller's `updated_at` stamps the title row too. The pair is written
as one thing and read back as one thing, and a title dated later than
the document it titles would say an edit happened that did not.

#### delete(key: [str](https://docs.python.org/3/library/stdtypes.html#str), recursive: [bool](https://docs.python.org/3/library/functions.html#bool) = False, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, unchanged_since: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

The rows to remove are selected first, then deleted by key.

Which is what makes `dry_run` a branch rather than a second query:
the selection has already run, and a preview is that answer with the
`DELETE` left out.

Selected rather than deleted in one statement because the return value
is the keys actually removed, and `DELETE` does not report them. The
range bounds are appended to both halves of the selection -- the key's
own row and, when recursive, the subtree beneath it.

The watermark is checked over the same two halves before any of it
goes, which is one aggregate query rather than a second selection.

#### descendant_count(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [int](https://docs.python.org/3/library/functions.html#int)

A `count(*)` over the subtree, less the metadata unit inside it.

Two range scans, both on the primary key: everything below `key`, and
not the stretch a plain delete would take with it. That difference is
what this reports, and it is why a document's own title has never
counted here. See `_below()` and [`outrage.keys.meta_range()`](keys.md#outrage.keys.meta_range).

`whole_subtree` **drops** the second scan rather than adding a third:
the question is then the subtree itself, and one range scan is all of
it.

#### latest_change(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)

A `max(updated_at)` over the same bounds the count scans.

[`descendant_count()`](#outrage.store_sqlite.SqliteStore.descendant_count)'s query with the aggregate changed and nothing
else, deliberately: the two are one selection asked two questions, and
a guard that measured a different set of keys from the count beside it
would be answering about a subtree nobody named. `max()` over no rows
is NULL, which is the None a caller reads as "nothing here to change".

#### exists(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [bool](https://docs.python.org/3/library/functions.html#bool)

One indexed lookup on the primary key, selecting no content.

On `key` rather than `doc_key`, so a metadata key answers for
itself, and returning a literal so a large document is not read to
find out that it is there.

#### level_entry(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Entry](store.md#outrage.store.Entry) | [None](https://docs.python.org/3/library/constants.html#None)

One lookup on `key`, then a range scan for anything below it.

The lookup is on the `key` column, which metadata is part of, rather
than on `doc_key`, which it is not: a key holding only metadata has
no document and no descendants, and still appears in its parent's
listing.

#### retrieve_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, offset: [int](https://docs.python.org/3/library/functions.html#int) = 0, byte_offset: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, length: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, pattern: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, occurrence: [int](https://docs.python.org/3/library/functions.html#int) = 0, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_MAX_CHARS) → [Excerpt](store.md#outrage.store.Excerpt)

One lookup on the primary key, sliced in Python.

The whole document is read and then cut, because a row is stored as one
value and SQLite would have to read it either way; the cost the caps
exist to avoid is the one on the way out, not the one off the disk.

A **byte** offset is the exception, and the reason it can be: SQLite
can seek within a stored value, so `_seek_read()` opens the row's
blob and reads the window rather than the document. See it for what
that costs and what it cannot do.

#### list_keys(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[Entry](store.md#outrage.store.Entry)]

Two queries, merged: the rows stored at this level, and the keys
that exist only because something lies beneath them.

Both halves are taken past the same cursor and merged before either is
cut. Cutting them separately is what makes the two disagree about where
the page ends: whichever half is denser near the cursor pushes the
other's keys over the edge, and a cursor never looks back.

#### get_documents(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_BULK_MAX_CHARS, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, max_total_chars: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[Excerpt](store.md#outrage.store.Excerpt)]

One selection, streamed and cut against the caps as it arrives.

Streamed, not fetched: the caps are what make this answer bounded, and
a query that materialises the subtree before applying them has already
done the work the caps exist to avoid. The totals come from a separate
`count(*)` over the same predicate, which is what keeps them
describing the selection rather than the page.

#### missing_meta_stats(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, window: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', sample: [int](https://docs.python.org/3/library/functions.html#int) = 0) → [MissingMeta](store.md#outrage.store.MissingMeta)

The window is measured at a synthesised `sort_key`, in SQL.

A document carrying none of the names has no row in the ordering the
survey walks, so `sort_key || suffix` stands in for where its row
*would* have sorted. Since schema 5 the two orderings genuinely agree:
the sort form marks every segment and joins with a delimiter below
every legal segment character, so `sort_form(d + "/!name")` is
`sort_form(d)` plus a fixed suffix, and the map from document to
metadata order preserves it. A survey's window therefore *is* an
interval of document keys now, which schema 4 could not say --
`a-x/!title` used to sort before `a/!title` while `a` sorted
before `a-x`.

**That does not make it safe to bound this by document key**, and this
still measures at the synthesised position deliberately. Exactly that
simplification was made once before, on exactly this reasoning, and
reintroduced a double count that review did not catch.
`tests/test_store.py::test_survey_windows_tile_over_adversarial_keys`
is the guard, and the synthesised position is correct under any
ordering, which a document-key bound is not.

The synthesised position is not sargable, so this scans the selection
rather than seeking into the sort index. Measured at 20k documents it
costs about 6% against a plain range, because the query is driven by
`idx_documents_meta` on `meta_name` and neither bound could seek
anyway. The window is one page wide, which is what keeps it affordable.

#### keys_missing_meta(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

One query with a `NOT EXISTS` against the metadata rows.

Over the same range predicate the survey itself uses, so the two agree
about what was in range. It used to read every document in the subtree
through [`get_documents()`](#outrage.store_sqlite.SqliteStore.get_documents) and throw the content away.

#### backup(destination: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Backup](store.md#outrage.store.Backup)

Through SQLite's own backup API, because the file alone is not the
store.

Almost everything written since the last checkpoint is in the `-wal`
sidecar rather than the `.sqlite` file - 4 KB of database against
2 MB of WAL, observed on 2026-08-17 - so copying the file yields a
near-empty database that opens cleanly and passes an integrity check.
That is a failure indistinguishable from success, which is the one kind
worth paying for in the library, and it is why this is the backend's
job rather than a caller's.

#### *property* stored_format_version *: [int](https://docs.python.org/3/library/functions.html#int)*

SQLite keeps it in the header, as `PRAGMA user_version`.

#### audit_rows() → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[AuditRow](store.md#outrage.store.AuditRow)]

Every row, in one query, streamed rather than fetched whole.

`LENGTH(content)` rather than the content itself: a check counts
characters and never reads a document, and a store worth checking is
one it would be foolish to pull into memory to count.

#### check_file(report: [Report](maintenance.md#outrage.maintenance.Report)) → [None](https://docs.python.org/3/library/constants.html#None)

What SQLite knows about the database and its sidecar.

Both questions here are the store's and have no meaning above it:
whether SQLite still considers its own pages sound, and how much of the
store is in the write-ahead log rather than the database.

#### repair() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Repaired](maintenance.md#outrage.maintenance.Repaired)]

Fold the write-ahead log back and compact the database.

Both steps are safe to run on a healthy store and safe to run twice.
Sizes are measured either side rather than reported from the action's
own return value, because the question being asked is what the file
looks like now.
