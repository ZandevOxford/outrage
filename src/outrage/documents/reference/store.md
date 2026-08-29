# outrage.store

What a document store is, in terms every backend has to answer in.

A store maps a key to a document. This module says what that means -- the
constants a caller configures it with, the value types every answer comes back
as, the two ways a call bounds what it is asking about, and the abstract
[`Store`](#outrage.store.Store) that names the operations themselves. It says none of it in
terms of how the documents are kept.

The vocabulary is the interesting part, and it is worth reading in this order:

* [`KeyRange`](#outrage.store.KeyRange) is a stretch of the key *order*, and
  [`BoundedSubtree`](#outrage.store.BoundedSubtree) is a part of the *hierarchy*. A subtree read gives
  both, plus a page cursor, and the three bound different things -- which is
  the distinction [`KeyRange`](#outrage.store.KeyRange) exists to keep.
* [`Excerpt`](#outrage.store.Excerpt) is part of one document and [`Page`](#outrage.store.Page) is part of a
  collection, and each states the size of the whole it came from. A partial
  answer that does not is not actionable.
* [`Entry`](#outrage.store.Entry) is how one key appears in its parent's listing, which is the
  only place the difference between a stored key and an implicit one shows.

[`Store`](#outrage.store.Store) itself is abstract, and it says only what a store *does*.
[`FileStore`](#outrage.store.FileStore) is the half of that which needs a file to answer -- where it
lives, what version wrote it, how it is copied and checked -- and the three
backends are its implementations:
[`outrage.store_sqlite.SqliteStore`](store_sqlite.md#outrage.store_sqlite.SqliteStore) is a read-write database accumulated a
document at a time, [`outrage.store_parquet.ParquetStore`](store_parquet.md#outrage.store_parquet.ParquetStore) is one
columnar file written whole and read many times, for a reference base of tens
of thousands of documents, and
[`outrage.store_files.FilesystemStore`](store_files.md#outrage.store_files.FilesystemStore) is a directory of files, whose
"file" is that directory. They share none of the storage and every word of
the vocabulary below, which is the point of the split.
[`outrage.mounts.MountedStore`](mounts.md#outrage.mounts.MountedStore) is a [`Store`](#outrage.store.Store) and not a
[`FileStore`](#outrage.store.FileStore): it keeps nothing of its own and routes to the stores behind
it, and that is what the two classes are for.

`_backend_for()` is the one place in the package that chooses between
them, and it chooses by the store file's extension. So nothing above here --
not the server, not the command line, not the mount table -- names a backend
to open one.

Independent of MCP: everything here is callable and testable on its own. Read
[`outrage.keys`](keys.md#module-outrage.keys) first for what a key is, which everything below is written in
terms of; the key namespace and the tool semantics are argued in `design.md`
**at the root of the repository**, which is not part of this reference.

### outrage.store.BACKUP_DIR_NAME *= 'backups'*

Where backups go when no destination is given, relative to the store
directory.

### outrage.store.BACKUP_STAMP *= '%Y%m%d-%H%M%S'*

How a backup is named within that directory. Sortable, so a listing is in
age order without parsing anything, and to the second, because two backups
in one minute is a thing that happens while working on the store itself.

### outrage.store.CONFLICTS *= ('skip', 'overwrite', 'stop')*

What to do about something already there, at the far end.

### outrage.store.DEFAULT_BACKEND *= 'sqlite'*

The backend a store is kept in when nobody says otherwise, and so the one an
unrecognised extension falls back to. See `_backend_for()` for why the
fallback is a fallback rather than a refusal.

### outrage.store.backend_names() → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...]

Every backend a store may be opened as, by name.

What a `type=` option may say, for the front ends that document it and
the refusal that lists it -- one answer from the registry rather than a
list retyped in each place that needs to name them.

### outrage.store.DEFAULT_BULK_MAX_CHARS *= 2000*

Per document cap when several are returned at once, which is usually a
listing rather than a read.

### outrage.store.DEFAULT_DIR_NAME *= '.outrage'*

Default directory name, relative to the working directory, when neither
--dir nor OUTRAGE_DIR is given.

### outrage.store.DEFAULT_MAX_CHARS *= 8000*

Cap on a single retrieve, so one oversized document cannot flood an agent's
context window. The caller pages with the returned next_offset.

### outrage.store.ENCODINGS *= ('json-string',)*

Encodings a caller may use for the content and title it passes in. These
describe the argument in transit, not the stored document, which is always
decoded back to plain text before it is written. See `_decode`.

### outrage.store.ENV_DIR *= 'OUTRAGE_DIR'*

Environment variable naming the store directory, consulted when no `--dir`
is given. See [`resolve_directory()`](#outrage.store.resolve_directory) for the order the three sources
are tried in.

### outrage.store.EVERYTHING *= BoundedSubtree(key=None, depth=None)*

Every key at and below the root: the default selection for a call that puts
no bound of its own on which part of the hierarchy it reads.

### outrage.store.EXPORT_DIR_NAME *= 'export'*

Where a document exported for editing is written, relative to the store
directory. Beside the backups, and for the same reason: it is infrastructure
about the stores rather than one store's own file. See `context/66`.

### outrage.store.FAILED *= 'failed'*

This one could not cross, and the rest were still tried. `reason` says why.

### outrage.store.FORMATS *= ('markdown', 'json', 'text', 'html')*

What a document may be stored as, and the only thing the store knows about
a document's text. Detected from the content when a caller names none, but
only two of the four can be: JSON and HTML each open with something no other
format plausibly opens with, while 'text' and 'markdown' are the same
characters and only the caller knows which was meant. So plain text is asked
for, never inferred. See `_detect_format()`.

### outrage.store.OVERWRITE *= 'overwrite'*

Replace what is already there.

### outrage.store.READ *= 'read'*

Read and held for a store that is not written yet. A store written whole
cannot report a document as written while it goes -- nothing is written
until all of it is -- and calling it `wrote` in the meantime would be a
report an interrupted run made untrue. See [`Store.writes_deferred`](#outrage.store.Store.writes_deferred).

### outrage.store.SKIP *= 'skip'*

Leave what is already there and carry on. The default, because a transfer
that overwrites by accident cannot be undone from here.

### outrage.store.SKIPPED *= 'skipped'*

Something was already there and [`SKIP`](#outrage.store.SKIP) was asked for.

### outrage.store.STOP *= 'stop'*

Stop the whole transfer at the first collision, having written what came
before it. What a caller wants when a collision means the wrong target.

### outrage.store.STOPPED *= 'stopped'*

The collision that ended the run, under [`STOP`](#outrage.store.STOP). Reported rather than
swallowed, so a caller can see where the transfer stopped and why; nothing
after it is yielded at all.

### outrage.store.UNBOUNDED *= KeyRange(after=None, after_inclusive=None, after_subtree=None, before=None, before_inclusive=None, final_subtree=None)*

The whole of the order, bounded at neither end: the default for a call that
names no stretch. Distinct from [`EVERYTHING`](#outrage.store.EVERYTHING) on purpose -- one bounds
the hierarchy and the other the order, and a subtree read needs both.

### outrage.store.WROTE *= 'wrote'*

The outcome recorded on a [`Transfer`](#outrage.store.Transfer): it crossed.

### *class* outrage.store.AuditRow(key: [str](https://docs.python.org/3/library/stdtypes.html#str), doc_key: [str](https://docs.python.org/3/library/stdtypes.html#str), meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), parent: [str](https://docs.python.org/3/library/stdtypes.html#str), chars: [int](https://docs.python.org/3/library/functions.html#int))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One stored row as its backend actually holds it, bookkeeping included.

The reading surface deliberately does not expose `parent`: it is a
denormalisation, kept so that listing a level is a lookup rather than a
scan, and a caller reading documents has no business knowing a store keeps
one. [`outrage.maintenance.check()`](maintenance.md#outrage.maintenance.check) does, because a denormalisation that
can disagree with what it was derived from is exactly what a check is for.

So this is the audit surface and not a second way to read. It yields every
row, metadata included, in one pass and in no promised order, and it is the
only place a backend's own bookkeeping is named outside the backend.

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### doc_key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The document this row belongs to: itself, or the document its metadata
is attached to.

#### meta_name *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

None for a document, the metadata name otherwise.

#### parent *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The parent this row is *stored* under, which is the value being checked
and not the one [`outrage.keys.parse()`](keys.md#outrage.keys.parse) would derive.

#### chars *: [int](https://docs.python.org/3/library/functions.html#int)*

### *class* outrage.store.Backup(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), bytes: [int](https://docs.python.org/3/library/functions.html#int), documents: [int](https://docs.python.org/3/library/functions.html#int), integrity: [str](https://docs.python.org/3/library/stdtypes.html#str))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

A copy of a store, and the evidence that it is a real one.

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

#### bytes *: [int](https://docs.python.org/3/library/functions.html#int)*

#### documents *: [int](https://docs.python.org/3/library/functions.html#int)*

Rows copied, checked against the source rather than assumed.

#### integrity *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

What SQLite's own integrity_check said. 'ok' when sound.

### *exception* outrage.store.BackendError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`RuntimeError`](https://docs.python.org/3/library/exceptions.html#RuntimeError)

Raised when a backend cannot be used: absent, or asked for a file it
did not write.

### *exception* outrage.store.BackupError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`RuntimeError`](https://docs.python.org/3/library/exceptions.html#RuntimeError)

Raised when a backup cannot be taken, or cannot be shown to be good.

### *class* outrage.store.BoundedSubtree(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, depth: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

A key and how far below it to descend: what a subtree read is *about*.

Deliberately not a [`KeyRange`](#outrage.store.KeyRange), though a subtree is one. A range says
where in the order to look and a subtree says which part of the hierarchy
to read, and a caller gives **both** -- a key must be at or below `key`,
within `depth` of it, *and* inside whatever range was asked for. Folding
the two together would make the pair inexpressible, and it is the pair that
a traversal stepping over a mounted store needs.

`key` of None is the root, which is every key. `depth` is counted in
segments from `key`, and None is unlimited.

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

#### depth *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*

### *class* outrage.store.Entry(key: [str](https://docs.python.org/3/library/stdtypes.html#str), kind: [str](https://docs.python.org/3/library/stdtypes.html#str), size: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), updated_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One key immediately below some other key.

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### kind *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

'document', 'metadata', or 'implicit' for a key that exists only because
something beneath it does.

#### size *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*

#### format *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

#### updated_at *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

### *class* outrage.store.Excerpt(key: [str](https://docs.python.org/3/library/stdtypes.html#str), content: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), updated_at: [str](https://docs.python.org/3/library/stdtypes.html#str), offset: [int](https://docs.python.org/3/library/functions.html#int), returned: [int](https://docs.python.org/3/library/functions.html#int), total: [int](https://docs.python.org/3/library/functions.html#int), next_offset: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Some or all of one document's content.

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### content *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### format *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

#### updated_at *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### offset *: [int](https://docs.python.org/3/library/functions.html#int)*

Character offset within the document at which content starts.

#### returned *: [int](https://docs.python.org/3/library/functions.html#int)*

Number of characters returned.

#### total *: [int](https://docs.python.org/3/library/functions.html#int)*

Total length of the document.

#### next_offset *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*

Where to resume, or None if this excerpt reached the end.

#### *property* truncated *: [bool](https://docs.python.org/3/library/functions.html#bool)*

Whether part of the document was left unread.

The same fact as `next_offset is not None`, named so that a caller
deciding whether to read on does not have to know that. Reading on
means passing `next_offset` back as `offset`.

### *class* outrage.store.FileStore(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, filename: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None)

Bases: [`Store`](#outrage.store.Store)

A store kept in a file of its own, and everything that follows from it.

The half of a store that needs somewhere on disk to answer from: where it
lives, which version of its format wrote it, how it is copied, and what a
check can say about the storage rather than about the keys. Every backend
is one of these. [`MountedStore`](mounts.md#outrage.mounts.MountedStore) is not, and that is
the whole reason the two are separate classes -- a table that keeps nothing
cannot answer any of it, and saying so by *not having* the members is
better than having eight that exist to refuse.

Two things are settled here rather than per backend, because they are the
same question whatever the storage is: **where the file lives**, which
[`store_file()`](#outrage.store.store_file) decides from a directory and a name relative to it, and
**that a store is a file inside a directory** rather than a directory of
its own, so that several stores can share one -- see
`project/reference/planned/mounts`.

A backend whose "file" is a *directory* is still one of these:
[`FilesystemStore`](store_files.md#outrage.store_files.FilesystemStore) sets `path` to the tree
and `directory` to its parent, so a backup of it lands beside the
corpus rather than inside it. The name means the same thing -- the one
place on disk this store *is* -- and only its kind differs.

#### default_filename *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*

What this backend calls its store file when a caller names none. Set by
every concrete backend, and the only thing about the file a backend
decides: that it *is* a file inside a directory is settled above, by
[`store_file()`](#outrage.store.store_file). [`default_store_file()`](#outrage.store.default_store_file) is how the rest of the
package asks for it without naming a backend to ask.

#### format_version *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[int](https://docs.python.org/3/library/functions.html#int)]*

The version of its own on-disk format this build writes. Compared
against [`stored_format_version`](#outrage.store.FileStore.stored_format_version) by [`outrage.maintenance.check()`](maintenance.md#outrage.maintenance.check),
which is why the comparison is written once rather than per backend --
"written by a newer outrage than this" is the same fault whatever wrote it,
even though each backend records the number somewhere different.

#### *classmethod* in_directory(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, filename: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Self](https://docs.python.org/3/library/typing.html#typing.Self)

This backend's store, named as a file inside a store directory.

The constructor, for every backend whose store *is* a file: the
signature above is already the directory-plus-name one. It is a
classmethod of its own so that a backend whose store is a **directory**
has somewhere to spell the same thing --
[`FilesystemStore`](store_files.md#outrage.store_files.FilesystemStore) takes the tree itself,
because an export target is a path a person typed, and a mount is not:
a mount is a name inside `--dir` like every other store, and
[`store_file()`](#outrage.store.store_file) is the rule for both.

[`default_store()`](#outrage.store.default_store) opens every store through here, so which of the
two shapes a backend has stays the backend's business rather than
something a mount table has to know.

#### opened_at(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [Self](https://docs.python.org/3/library/typing.html#typing.Self)

Another store of this class, kept at `path`.

The one thing a copy of a store cannot work out for itself. Every
backend's constructor takes a directory and a name within it, so the
default splits `path` that way; a backend whose "file" is a directory
overrides this rather than being spelled as a special case here.

Whatever else distinguishes *this* store from a bare one travels across
in the override, because only the backend knows what that is -- and a
copy opened under a different policy from the store it was copied from
would compare short against it for a reason that is not a fault.

#### backup(destination: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Backup](#outrage.store.Backup)

Copy the store to `destination`, and verify the copy.

Both halves, and both here rather than in a caller: only the backend
knows what a complete copy of itself is, and a copy that opens cleanly
is not evidence of one. The result carries what the check found, so a
caller can report a backup it did not have to trust.

`destination` may name a file or a directory, and defaults to a
timestamped name under `backups/` in the store directory, taking the
store file's own extension. Missing parents are created. An existing
file is refused unless `overwrite`.

**This is the copy every store can make of itself**: open a fresh one
of the same class at the target and [`copy_from()`](#outrage.store.Store.copy_from) this one
into it, which carries every document, its format, its metadata and its
`updated_at`. A backend with a native copy of its file overrides
this and should -- [`SqliteStore`](store_sqlite.md#outrage.store_sqlite.SqliteStore) must,
because the file alone is not the store there, and
[`ParquetStore`](store_parquet.md#outrage.store_parquet.ParquetStore) does because a byte copy
is faster and exact. What a backend may not do is skip the verifying.

The copy is written through a store that is then closed, and reopened
to check it: what a still-open handle says about a file is what it
believes it wrote, which is the thing in question.

#### verified_backup(target: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [Backup](#outrage.store.Backup)

Read the copy at `target` back, and prove it holds what this does.

Every key, compared, rather than a count of them: a copy that lost one
document and gained another counts the same and is not a backup.
[`audit_rows()`](#outrage.store.FileStore.audit_rows) is what both ends are asked, because it is
the one read that yields *every* row a store holds, metadata included,
and a backup missing every `!title` would open cleanly and be
useless.

Public because a backend with its own copy still owes the same
evidence, and the two that have one answer it their own way -- from
row counts and a version their storage records natively, which is
cheaper and says more. This is the answer for a backend with nothing
better to ask.

`integrity` is `"ok"`: the keys agreeing *is* the check here, and
there is no second opinion to report. A backend whose storage has one
says what it said.

#### backup_path(destination: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None), \*, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool)) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

Settle where the copy goes, and refuse the destinations that destroy.

Public so that a caller can report the destination, and hit the same
refusals, without writing anything - which is what `--dry-run` needs.

The default name takes the store file's own extension rather than a
fixed one, so a backup of a store is recognisably the same kind of
thing as the store. Here rather than on a backend because the two
refusals are the point of it, and neither is about storage: a
destination that is the store itself destroys what it was copying, and
one that already exists destroys whatever was there.

#### *abstract property* stored_format_version *: [int](https://docs.python.org/3/library/functions.html#int)*

The format version recorded *in the file this store opened*.

Not [`format_version`](#outrage.store.FileStore.format_version), which is what this build writes. The two
differing is the whole question: below, and the file predates this
build; above, and something newer wrote it. Each backend records the
number its own way -- SQLite in `PRAGMA user_version`, parquet in the
file's key-value metadata -- and this is the one name the difference
does not reach.

#### *abstractmethod* audit_rows() → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[AuditRow](#outrage.store.AuditRow)]

Every row this store holds, bookkeeping included, in one pass.

For [`outrage.maintenance.check()`](maintenance.md#outrage.maintenance.check) and nothing else -- see
[`AuditRow`](#outrage.store.AuditRow) for why the reading surface does not offer this. One
pass rather than a query per check, because the checks that use it want
the same rows for different questions and a store large enough to be
worth checking is large enough for a second pass to be felt.

Order is not promised. Nothing auditing rows one at a time depends on
it, and a backend held in key order should not have to pay to prove it.

#### *abstractmethod* check_file(report: [Report](maintenance.md#outrage.maintenance.Report)) → [None](https://docs.python.org/3/library/constants.html#None)

Add what only this backend can say about its own file.

Called by [`outrage.maintenance.check()`](maintenance.md#outrage.maintenance.check) once the checks that any
backend can answer have run. Those are about rows and keys; this is
about *storage* -- whether SQLite still considers the database sound,
how much of it is sitting in the write-ahead log, whether a parquet
file is still in the sort order every read of it bisects.

Fills in [`details`](maintenance.md#outrage.maintenance.Report.details) with the numbers
worth printing whether or not anything is wrong, and appends to
`problems` for anything that is.

#### *abstractmethod* repair() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Repaired](maintenance.md#outrage.maintenance.Repaired)]

Fix what [`check_file()`](#outrage.store.FileStore.check_file) found and this backend can act on.

Returns what was actually done, which may be nothing: a backend whose
storage cannot get into a repairable state returns an empty list, and
that is an honest answer rather than a silence. It is not the same
answer as [`check_file()`](#outrage.store.FileStore.check_file) finding nothing -- one says there is
nothing that *could* need repairing, the other that nothing does.

Nothing here may lose a document. A repair moves bytes about; one that
could discard content would need a backup taken first, and no backend
offers such a repair.

### *exception* outrage.store.KeyNotFoundError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`LookupError`](https://docs.python.org/3/library/exceptions.html#LookupError)

Raised when a key holds no content.

### *class* outrage.store.KeyRange(after: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, after_inclusive: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, after_subtree: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, before: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, before_inclusive: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, final_subtree: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

A stretch of the key order, named by keys rather than by positions.

Six one-sided bounds, all optional, all combined with AND, so any window
the order supports can be described by one of these and nothing outside it
describes a range at all. Three cut from below and three from above, and
the three of each are the three places a cut can fall relative to a key:
in front of the key, behind the key, and behind its whole subtree.

| `after_inclusive`   | at that key or after it                             |
|---------------------|-----------------------------------------------------|
| `after`             | strictly after that key, its subtree included       |
| `after_subtree`     | strictly after that key **and** everything below it |
| `before`            | strictly before that key, and so before its subtree |
| `before_inclusive`  | at that key or before it                            |
| `final_subtree`     | no later than the end of that key's subtree         |

The distinction between `after` and `after_subtree` is the one worth
holding on to. `after` is what a cursor means -- exclusive of the key it
names and *inclusive of that key's children*, because the key after the
last one emitted may well be its child. `after_subtree` is what stepping
over a subtree means, and nothing else can say it. Together with `before`
it names a subtree from both sides, which is how a range excludes one:
`before=k` ends the stretch in front of `k` and `after_subtree=k`
begins the stretch behind it, and neither has to name a key that exists.
There is no key spelling "just past the last thing under `k`".

A range bounds the **selection**, so a count taken over one counts that
range. That is what makes the ranges either side of an excluded subtree add
up, and it is why a page cursor is a separate argument rather than an
`after` set here: a page's totals have never depended on where the reader
had got to.

Nothing set means no bound at all, so `KeyRange()` is every key.

#### after *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

#### after_inclusive *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

#### after_subtree *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

#### before *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

#### before_inclusive *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

#### final_subtree *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

### outrage.store.MetaReader

What [`meta_reader()`](#outrage.store.meta_reader) returns: a row's key and its stored metadata split,
in; the split as the scope sees it, out.

alias of [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None), [`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)], [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None), [`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)]]

### *class* outrage.store.MissingMeta(total: [int](https://docs.python.org/3/library/functions.html#int), total_chars: [int](https://docs.python.org/3/library/functions.html#int), sample: [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)])

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Documents one page of a metadata survey could not show, over its window.

Stats about a window rather than a page of one, so there is no cursor:
the window is already bounded at both ends by the page it describes, and a
cursor here would name a position in a collection no argument resumes.

#### total *: [int](https://docs.python.org/3/library/functions.html#int)*

Documents in the window carrying none of the names asked for.

#### total_chars *: [int](https://docs.python.org/3/library/functions.html#int)*

Characters stored across those documents, which is the other half of
what a caller needs to decide whether to go and look.

#### sample *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*

Up to a requested number of their keys. The count is exact; this is not.

### *class* outrage.store.Page(items: [list](https://docs.python.org/3/library/stdtypes.html#list)[T], returned: [int](https://docs.python.org/3/library/functions.html#int), total: [int](https://docs.python.org/3/library/functions.html#int), total_chars: [int](https://docs.python.org/3/library/functions.html#int), next_cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None))

Bases: [`Generic`](https://docs.python.org/3/library/typing.html#typing.Generic)

Some or all of a collection, and the size of the whole it came from.

The collection axis member of the same family as `Excerpt`, named to
match it rather than inventing a second vocabulary. A partial answer that
does not state the size of the whole is not actionable: 20 keys of 22 is a
listing, 20 keys of 40000 is a sample, and a caller that cannot tell them
apart treats them the same.

#### items *: [list](https://docs.python.org/3/library/stdtypes.html#list)[T]*

#### returned *: [int](https://docs.python.org/3/library/functions.html#int)*

Items in this page.

#### total *: [int](https://docs.python.org/3/library/functions.html#int)*

Items in the whole collection, which is what this page is part of.

#### total_chars *: [int](https://docs.python.org/3/library/functions.html#int)*

Characters stored across that whole collection. Named apart from
`total` deliberately: 12000 documents beneath a key is a different
prospect from 40 MB beneath it, and no caller should be able to read one
number as the other.

#### next_cursor *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

Key to resume after, or None when the page reached the end.

#### *property* truncated *: [bool](https://docs.python.org/3/library/functions.html#bool)*

Whether the collection continues past this page.

Deliberately not `returned < total`: `total` describes the whole
selection and `returned` only this page, so that comparison is true
of every page but the last *and* of a page that ended exactly at the
end. The cursor is the one that knows.

### *exception* outrage.store.PatternNotFoundError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`LookupError`](https://docs.python.org/3/library/exceptions.html#LookupError)

Raised when a search pattern does not occur in a document.

### *exception* outrage.store.ReadOnlyStoreError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`PermissionError`](https://docs.python.org/3/library/exceptions.html#PermissionError)

Raised when a store is asked to write and its backend cannot.

Distinct from [`outrage.mounts.ReadOnlyMountError`](mounts.md#outrage.mounts.ReadOnlyMountError), which is about a
*configuration*: a store that could be written was mounted with
`--mount-ro`, and starting the server without that flag would let the
write through. This one is about the storage. A parquet file is not
updated in place, so no flag exists that would make the same call succeed,
and telling a caller to drop one would be advice that does not work.

### *class* outrage.store.Store(\*, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None)

Bases: [`ABC`](https://docs.python.org/3/library/abc.html#abc.ABC)

A document store: the operations, without saying how they are kept.

Abstract, and deliberately narrow. Everything below is expressed in keys,
ranges, subtrees, pages and excerpts -- the vocabulary of the namespace --
so that a backend is free to answer them however its storage is shaped.
What a subclass adds is how a key becomes a stored thing and back; what it
may not add is a second way of saying which keys a call is about.

**A store is not necessarily kept in a file.** Everything about one that
is -- where it lives, which version of its format wrote it, how it is
copied and checked -- is [`FileStore`](#outrage.store.FileStore) below.
[`MountedStore`](mounts.md#outrage.mounts.MountedStore) is a store and not a file store: it
keeps nothing of its own and routes to the stores behind it. The split is
what says so, in place of the eight members it used to carry to refuse
them.

[`default_store()`](#outrage.store.default_store) is what a caller uses to get one of these without
naming a backend.

#### writable *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[bool](https://docs.python.org/3/library/functions.html#bool)]* *= True*

Whether this backend can be written at all. False says the *storage*
refuses, which is not the same as a store that was mounted read-only:
a mount's refusal comes off with a flag and this one does not. A caller
deciding whether to offer a write reads this; a caller that writes
anyway gets [`ReadOnlyStoreError`](#outrage.store.ReadOnlyStoreError) from the backend, since a class
var nobody consulted must not be the only thing standing between a
corpus and a half-written file.

#### writes_deferred *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[bool](https://docs.python.org/3/library/functions.html#bool)]* *= False*

Whether a write here is only visible once the whole store is written.
True for a store built in one pass, where nothing exists until all of it
does -- so a transfer into one reports [`READ`](#outrage.store.READ) rather than
[`WROTE`](#outrage.store.WROTE), because an interrupted run wrote nothing and a report
saying otherwise would be one the interruption made untrue.

#### backend_name *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*

What this backend is called where a report or a refusal has to name it.
A short lowercase word, matching the store file's extension, so that a
sentence about a store and the name of its file agree.

#### *abstractmethod* close() → [None](https://docs.python.org/3/library/constants.html#None)

Release whatever this store holds open.

Called by `__exit__`, and safe to call more than once. What is
released is the backend's business -- a store that holds nothing open
has nothing to do here -- but a caller is entitled to say it is
finished, and to have that mean something.

#### *abstractmethod* store_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), content: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, title: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, encoding: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, updated_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)

Store `content` at `key`, overwriting anything already there.

A `?` segment in `key` is replaced by a number unused among the
children of the key enclosing it, so `tmp/?` writes to `tmp/1` in
an empty store. Returns the key actually written, which is the only way
the caller learns an allocated number.

`format` is one of [`FORMATS`](#outrage.store.FORMATS). Left out, it defaults to 'json'
when the content parses as a JSON object or array, 'html' when it opens
with a doctype or an `<html>` element, and 'markdown' otherwise --
'text' is never detected and has to be asked for.

`title` writes the `!title` metadata alongside the document in the
same transaction. It saves a second call, but it exists mainly because
the title is what makes a document discoverable later, and a separate
call is one that can simply be forgotten. It may be given for a
metadata key too, and becomes that key's own `!title`: metadata is a
namespace and a namespace can be described, so `a/!changelog` may say
what its changelog is for at `a/!changelog/!title`.

`encoding` describes how `content` and `title` arrived, not what
is stored: 'json-string' means each is a JSON string literal, quotes
and all, which is decoded before it is written. The stored document is
plain text either way, so readers are unaffected. Its purpose is to
make damage in transit loud - see `_decode`.

`updated_at` is when the document was last written, and left out it
is now - which is what an ordinary write means by it. It is here for
the write that is a *copy* of a document that already exists: a
transfer between two stores carries the timestamp across, or the copy
says every document was written the moment it was copied and the store
loses the one fact about a document that nothing can reconstruct. An
ISO 8601 timestamp, normalised to UTC at second precision, which is
what `_now()` writes and so what every stored value already looks
like; a naive one is read as UTC.

Deliberately **not** offered by the MCP tool or by `outrage set`. A
client writing a document is writing it now, and a stamp it could
choose is one it could get wrong about its own work; the callers that
legitimately restamp are copying something that was already stamped.

Every refusal above is `_validated()`'s, which an implementation
calls before it writes anything.

#### copy_from(source: [Store](#outrage.store.Store), subtree: [BoundedSubtree](#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](#outrage.store.KeyRange) = UNBOUNDED, prefix: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, reroot: [bool](https://docs.python.org/3/library/functions.html#bool) = False, on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str) = SKIP, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Generator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Generator)[[Transfer](#outrage.store.Transfer), [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]

Write every document `source` holds in `subtree` into this store.

The one bulk operation, and it is a method on the **target** rather
than a function over a pair, because the target is what knows how it
is written: a database takes a document at a time, and a file written
whole takes all of them and writes once. A caller asks for the same
transfer either way and each store answers it appropriately, which is
what an export, an import, a repack and a backup all turn out to be.

`source` is any [`Store`](#outrage.store.Store) -- a database, a directory of files,
or a mount table presenting several of them as one namespace, which is
what makes a copy *out of* a table possible at all. `subtree` and
`key_range` bound what crosses exactly as they bound a read, so a
copy of part of a store is the same selection as a listing of it.
`prefix` grafts what crosses under a key here, and left out, each
document keeps the key it had. `reroot` changes what the graft keeps:
the subtree's own key is stripped first, so `a/b` copied to `tmp`
lands at `tmp` rather than at `tmp/a/b` and everything below it
keeps its position below that. Grafting the whole key is right for an
archive and is the default; re-rooting is the only spelling that says
"these documents now live at another key", which is what a caller
moving a subtree needs. Which pairs of keys are safe to stream between
differs between the two -- [`outrage.bulk.overlapping()`](bulk.md#outrage.bulk.overlapping) is the rule,
and the front ends apply it.

Metadata crosses as the keys it is: a copy that left every `!title`
behind would produce a store nothing can be surveyed by. So does each
document's `updated_at`, which is what makes this a copy rather than
a restamping -- see [`store_document()`](#outrage.store.Store.store_document).

`limit` bounds how many documents cross, and the generator returns
the source key of the last one so that `cursor` can pick the copy up
there. That pair is what a front end returning one value needs -- a
tool result cannot stream, and a copy of a large subtree cannot be one
answer -- and the cursor is a *source* key, which is why it is returned
rather than read off the last transfer. See [`outrage.bulk.copied()`](bulk.md#outrage.bulk.copied).

Yields a [`Transfer`](#outrage.store.Transfer) per document as it goes, so that a front end
can report the transfer while it happens and an interrupted one has
reported exactly what it did. `on_conflict` decides what happens to a
key already here, one key at a time: [`SKIP`](#outrage.store.SKIP) leaves it,
[`OVERWRITE`](#outrage.store.OVERWRITE) replaces it, [`STOP`](#outrage.store.STOP) ends the run at the first
collision having kept what it already wrote.

The default implementation reads each document and writes it here,
which is every store's answer until it has a better one. A backend
with a bulk way in overrides this; what it may not do is change what
the transfer *means*, which is why the report is the same either way.

The walk itself is [`outrage.bulk`](bulk.md#module-outrage.bulk)'s, imported where it is used
rather than at the top of this module: a store's own reads are pages,
deliberately, and the caller that legitimately wants all of it lives
there. A copy is that caller.

#### located(key: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/library/constants.html#None)

The file this store keeps `key` in, when there is one to name.

None by default, and that is not an omission: a row in a database has
no file of its own, and a store answering with the file the *whole*
corpus is in would be naming something a caller cannot open expecting
one document.

For reporting rather than for reading -- nothing here opens what it
returns. A copy into a directory of files is worth reading as key to
path, and the store on the far end is the only thing that knows which
path, so [`Transfer`](#outrage.store.Transfer) carries it and this is where it comes from.

#### *abstractmethod* delete(key: [str](https://docs.python.org/3/library/stdtypes.html#str), recursive: [bool](https://docs.python.org/3/library/functions.html#bool) = False, \*, key_range: [KeyRange](#outrage.store.KeyRange) = UNBOUNDED) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

Delete `key`, returning the keys actually removed.

A document key takes its metadata with it -- the whole metadata
subtree, since a document and its metadata are one unit and contiguous
in the order. Descendants are removed only when `recursive` is set,
so a mistyped key cannot silently discard a whole subtree. Note that
storing an empty document is not a deletion.

**A metadata key is a container like any other.** Deleting one takes
what is inside it, so `a/!changelog` with notes below refuses without
`recursive` rather than quietly discarding them. It is only a
document's *own* delete that carries metadata away unasked, and that is
because the metadata has no meaning once the document is gone.

`key_range` bounds which keys are in scope, exactly as it does for a
read: a delete that steps over a mounted store's stretch of the order
needs to say so in the same vocabulary a traversal does, or it removes
keys the mount has made unreachable and reports them as deleted. Those
keys read back fine from the mount on the very next call, which is the
defect this argument exists for -- see
`project/reference/planned/mounts/crossing`.

It bounds *both* halves. The key itself and its metadata are as capable
of lying inside a shadowed stretch as any descendant is.

#### *abstractmethod* descendant_count(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [int](https://docs.python.org/3/library/functions.html#int)

How many stored keys lie strictly below `key`.

Metadata counts: it is stored, and a caller deciding whether a subtree
is empty is asking about everything that would have to go.

**A metadata key has a real subtree of its own**, and this counts it.
`a/!changelog` holding twenty notes reports twenty, exactly as a
document holding twenty children does, which is what makes the delete
below refuse it without `recursive`.

Exists so a caller can report what a non-recursive delete left behind:
without it, deleting a key that holds nothing itself is indistinguishable
from deleting a key that does not exist.

What it leaves out is `key`'s **own** metadata unit, because a plain
delete takes that with the key -- so the default answers *what would a
plain delete keep*. **\`\`whole_subtree\`\` asks the other question**:
everything strictly below `key`, that unit included, which is what a
*recursive* delete takes and what [`outrage.bulk.walk()`](bulk.md#outrage.bulk.walk) reports.
A caller previewing a recursive delete needs the second, and answering
it with the first prints a remainder short by the unit -- negative,
once the preview reaches past the ordinary children.
See [`outrage.keys.meta_range()`](keys.md#outrage.keys.meta_range).

`key_range` bounds it for the reason it bounds `delete`: a count
that includes keys a mount has made unreachable tells a caller to pass
`recursive` to remove keys that are not there to remove.

#### *abstractmethod* exists(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [bool](https://docs.python.org/3/library/functions.html#bool)

Whether `key` itself holds a document.

Not the same question as whether anything is below it: a bulk import
asks this per file to decide about one key, and a container that holds
nothing itself is free for a document to be written to.

Deliberately cheaper than a read, since the answer is wanted for every
file in an import and the content is not.

#### *abstractmethod* level_entry(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Entry](#outrage.store.Entry) | [None](https://docs.python.org/3/library/constants.html#None)

How `key` appears in its parent's listing, or None if it does not.

The same three answers [`list_keys()`](#outrage.store.Store.list_keys) gives about one key without
listing the level to find it: a stored document, an implicit key that
exists only because something lies beneath it, or nothing at all.

Asked by a caller that has to reconcile this store's level with keys
from somewhere else and must not count the same position twice. A
cheaper pair of questions -- does the key exist, does it have
descendants -- gets one corner wrong: metadata sits *at* a key rather
than below it, so a key holding only metadata has no document and no
descendants and still appears in the listing.

#### *abstractmethod* retrieve_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, offset: [int](https://docs.python.org/3/library/functions.html#int) = 0, length: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, pattern: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, occurrence: [int](https://docs.python.org/3/library/functions.html#int) = 0, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_MAX_CHARS) → [Excerpt](#outrage.store.Excerpt)

Read the content stored at `key`.

`pattern` is a literal substring, not a regular expression; when
given, the read starts at its `occurrence`-th appearance at or after
`offset`. The result is capped at `length` or `max_chars`,
whichever is smaller, and carries a continuation offset.

#### *abstractmethod* list_keys(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](#outrage.store.Page)[[Entry](#outrage.store.Entry)]

List the keys immediately below `key`, or below the root.

Includes subkeys and metadata, and keys that exist only implicitly
because something beneath them has content.

`limit` and `cursor` page the level. Neither has a default: this
layer offers pagination and holds no opinion about how much a caller
can take, which is the tools' and the command line's question and they
answer it differently.

No [`KeyRange`](#outrage.store.KeyRange) here, deliberately. This reads one *level*, not a
stretch of the order, and the cursor is the only bound a level has ever
needed; a range would have to be honoured by every part of a level's
answer, for no caller that exists.

#### last_child(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)

The final segment of the last key immediately below `key`.

What `?last` resolves to, and the store half of
[`outrage.keys.resolve_last()`](keys.md#outrage.keys.resolve_last) -- so `notes/?last` names whatever
this returns for `notes`. None when nothing is below `key`, which
is what the caller turns into a refusal.

**Last in the order a listing walks**, which is `sort_form()`'s,
so a level of numbers gives the highest number and not the highest
spelling. Implicit keys count: a container holding only descendants is
as much the last key at that level as a document is, and `?last`
exists to name the newest thread of work whether or not somebody
wrote a document at the top of it.

Metadata does not count, **at whatever level this stands**. `?last`
stands where an ordinary segment goes -- it can no more resolve to
`!title` than `?` can allocate one -- so a level holding a document
and its title has one child here. Inside a metadata namespace the same
rule applies to that level: `a/!changelog/?last` is the newest note
kept in the changelog and never the changelog's own `!title`.

Concrete rather than abstract, on [`list_keys()`](#outrage.store.Store.list_keys), because it asks
nothing a backend answers differently. **It reads the whole level to
take its last row**, which is one round trip at the sizes a level
actually reaches and the wrong shape if one ever holds thousands: the
fix then is an override selecting one row in descending order, not a
second definition of what "last" means.

#### *abstractmethod* get_documents(subtree: [BoundedSubtree](#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_BULK_MAX_CHARS, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, max_total_chars: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](#outrage.store.Page)[[Excerpt](#outrage.store.Excerpt)]

Read everything `subtree` names, in key order.

With `meta_name` the result holds those metadata entries instead of
documents, which is how the titles of every document under a key are
listed in one call.

`key_range` narrows the subtree to a stretch of the order inside it,
and the two hold together: a key is returned when it is in the subtree
*and* in the range. It bounds the selection, so `total` and
`total_chars` describe that stretch, and a caller reading one subtree
as several ranges can add the answers up.

`cursor` is not one of the bounds. It is where the last page stopped,
it moves within the range as a caller pages, and it deliberately does
not reach the totals: what a caller cannot work out from a page is how
much of the whole they are holding.

Two axes bound the answer and both are needed. `max_chars` caps each
document, `limit` and `cursor` page the collection, and
`max_total_chars` caps the page as a whole -- without that last one
the two axes multiply, and a hundred documents at two thousand
characters each honours both stated bounds while returning two hundred
thousand characters.

#### *abstractmethod* missing_meta_stats(subtree: [BoundedSubtree](#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](#outrage.store.KeyRange) = UNBOUNDED, window: [KeyRange](#outrage.store.KeyRange) = UNBOUNDED, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', sample: [int](https://docs.python.org/3/library/functions.html#int) = 0) → [MissingMeta](#outrage.store.MissingMeta)

What a metadata survey could not see, over exactly one page's window.

**Two ranges, measured against two different things**, and a document
has to satisfy both. `key_range` is measured against a document's own
position, as everywhere else in the store. `window` is measured
against the position its metadata *would* have taken, which is the
order the survey walks, so this is where a survey's own cursors go --
`KeyRange(after=page_start, before_inclusive=page_end)` is a page,
exclusive below and inclusive above, each end left unset when the page
ran to that end of the collection.

The split is not a technicality. A document is inside a subtree that
was stepped over because of where the *document* is, and is inside a
page because of where its *title* would have sorted, and a survey
reading one subtree in several ranges needs to say both at once.

A document carrying none of the names appears nowhere in the ordering
the survey walks, so it has no position in it either. One is synthesised:
where it *would* have sorted had it carried the name, which is exactly
the position of `doc/!name`. That is part of the contract rather than
an implementation detail -- it is what decides which window a document
is counted in, and so what makes a caller's windows tile.

#### *abstractmethod* keys_missing_meta(subtree: [BoundedSubtree](#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](#outrage.store.Page)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

Document keys in `subtree` carrying none of `meta_name`.

A survey by `!title` only sees documents that have one, so on its own
it silently under-reports the store. This names what the survey missed.

`key_range` narrows the subtree exactly as it narrows a survey, and
for the same reason: the two have to be askable over one stretch of the
store, and to agree about what was in range, or they stop describing
the same one.

### *exception* outrage.store.StoreFileError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)

A store file that does not name a file inside its directory.

A store file is always relative to the directory holding it -- that is what
lets one directory hold several stores, and what keeps a configuration file
free of absolute paths that stop being true when a project moves. An
absolute path, or one climbing out with `..`, is refused here rather than
quietly opening a database somewhere nobody was looking.

### *class* outrage.store.Transfer(action: [str](https://docs.python.org/3/library/stdtypes.html#str), key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/library/constants.html#None), reason: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, characters: [int](https://docs.python.org/3/library/functions.html#int) = 0)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One document crossing from one store to another, or not, and why not.

Yielded per document rather than collected, so that a front end can print
a transfer as it happens and an interrupted one has reported exactly what
it did. `action` is what happened at the far end, and it says nothing
about a dry run: a caller that wrote nothing knows it, and it is the only
one that can render the difference honestly.

`key` is the key **written**, which is the source's own key unless the
copy grafted it somewhere else. `path` is the file behind it where
either end keeps its documents in files, which is what makes an export
report readable; None where neither does, and the report is key to key.

#### action *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/library/constants.html#None)*

#### reason *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

#### characters *: [int](https://docs.python.org/3/library/functions.html#int)*

### outrage.store.default_store(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, filename: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, backend: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [FileStore](#outrage.store.FileStore)

A store of the backend this build opens when nobody names one.

`filename` of None means whatever that backend calls its store file.
Any other name picks the backend that claims its extension, so a caller
holding a mount's file name opens the right storage without naming one --
see `_backend_for()`.

`backend` names one instead of reading it from the file, which is what a
mount's `type=` option and `--store FILE,type=NAME` reach: a directory
of files has no extension for the rule above to read, so the only way to
say `files` is to say it. Opening goes through
[`FileStore.in_directory()`](#outrage.store.FileStore.in_directory) rather than the constructor, because that is
the one thing a backend whose store is a directory spells differently.

### outrage.store.default_store_file() → [str](https://docs.python.org/3/library/stdtypes.html#str)

What the default backend calls its store file.

A store is addressed as a *file* within a directory rather than as a
directory of its own, so that one directory can hold several stores side by
side and so that a backend which is not SQLite can be named by the file it
keeps. That rule is this module's and does not vary; *which* name is the
backend's, and asking for it through here is what keeps the front ends from
having to name one to print a default.

It is the root mount when `--root-mount` names nothing else, and the file
a bare `--dir` opens.

### outrage.store.entry_kind(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

Whether `key` lists as `"metadata"` or as `"document"`.

Decided by the **last segment**, because a listing shows one level and a
`!` opens a namespace at whatever level it stands: `a/!changelog` lists
inside `a` as metadata, and the `22` inside it lists as the ordinary
document it is. The stored `meta_name` says where the whole key first
turns to metadata, which is a different question and the wrong one here.

Shared by all three backends, so a listing cannot mean one thing in SQL and
another on a filesystem.

### outrage.store.meta_reader(scope: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)], [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]]

How to read a row's metadata split from inside `scope`.

"Is this a document" and "is this the value of a name" are asked *relative
to the key a read was scoped at*, and the stored `meta_name` and
`meta_path` answer them only when that scope holds no `!`. They record
where the **key** first turns to metadata, which from inside
`a/!changelog` is a segment above the question: every row there carries
`changelog`, so the stored reading would match nothing at all.

So the stored pair for an ordinary scope -- which is every survey anyone
runs -- and [`outrage.keys.relative()`](keys.md#outrage.keys.relative) per row for a scope that is
itself metadata. **This is where the rule that a survey descends into a
metadata namespace only when scoped inside one lives** for the backends
that hold their rows in memory; `store_sqlite._meta_clauses` is the same
rule as SQL.

### outrage.store.open_store(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, filename: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, backend: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[FileStore](#outrage.store.FileStore)]

Open a store, closing it on exit.

### outrage.store.read_all(store: [Store](#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*kwargs: [Any](https://docs.python.org/3/library/typing.html#typing.Any)) → [Excerpt](#outrage.store.Excerpt)

Read a whole document, following `next_offset` until there is no more.

A function beside the store rather than a method on it, deliberately.
Whether the *library* should stop handing out silent partial documents is
an open design question - the options are weighed in
`project/reference/planned/agents` and none has been chosen. This settles
only what the command line does, which is a narrower question with an
obvious answer: a person redirecting a document to a file wants the
document, and a slice is available by asking for one.

Asked for the whole document, the result reports it with `next_offset` of
`None`, so a caller cannot tell it apart from a document that fitted.
That is the point. Asked for a `length`, the result stops there and
carries a continuation offset, exactly as a single capped read does.

### outrage.store.resolve_directory(explicit: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

Locate the store directory: explicit path, then OUTRAGE_DIR, then ./.outrage.

A directory rather than a file, so that other files can live beside the
database later.

### outrage.store.store_file(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], filename: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

The file a store keeps, from a name relative to its directory.

One rule, in one place, for every store this process opens: the root mount
and each `--mount` alike. The directory is shared infrastructure -- the
event log and the backups sit in it -- and the file is which store within
it, which is what lets several stores live in one directory and what a
backend other than SQLite would vary.

Relative, and only relative. An absolute path would make the directory a
lie and a configuration file unmovable; `..` would reach outside the
directory an operator named. Both are refused rather than resolved.

`filename` of None is whatever the default backend calls its store file
-- see [`default_store_file()`](#outrage.store.default_store_file). A store that already knows its backend
passes that backend's name instead, so a store is never opened under a
name a different backend chose.

```pycon
>>> store_file("/srv/project/.outrage").name
'store.sqlite'
>>> store_file("/srv/project/.outrage", "ref.sqlite").name
'ref.sqlite'
```
