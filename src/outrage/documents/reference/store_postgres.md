# outrage.store_postgres

The PostgreSQL backend: one store, shared by every device that can reach it.

The first backend whose store is not on this machine. Everything else in the
package is a file inside a directory an operator named; this one is a
*connection*, and the file a mount names is somebody else's configuration --
libpq's connection service file, read by [`outrage.pgservice`](pgservice.md#module-outrage.pgservice). What
follows from that is most of what is written down here.

## What is settled at the far end rather than at this one

* **The schema version lives in the database**, in [`SCHEMA_TABLE`](#outrage.store_postgres.SCHEMA_TABLE), with
  its own numbering starting at 1. A SQLite store is migrated in place when it
  is opened, because the build that opens it is the only build that has it. A
  shared store has several, on several devices, so a build opening one never
  changes its version: it operates at the version it finds, between
  [`MIN_SCHEMA_VERSION`](#outrage.store_postgres.MIN_SCHEMA_VERSION) and [`SCHEMA_VERSION`](#outrage.store_postgres.SCHEMA_VERSION), and migration is a
  command somebody runs. [`Compatibility`](#outrage.store_postgres.Compatibility) is the decision that comes
  out of that, and [`compatibility()`](#outrage.store_postgres.compatibility) states all four of its cases.
* **Ordering is declared, not inherited.** Every cursor, range and page in this
  package assumes keys sort bytewise, which is SQLite's `BINARY` and is
  *not* what an ordinary Postgres database does: this machine's test database
  orders seven perfectly ordinary keys differently from Python, and the two
  orders share no prefix at all. So every text column here carries
  `COLLATE "C"` -- see `_TABLE`.
* **The server's clock stamps writes**, not this process's, because two
  devices with skewed clocks would otherwise let a precondition pass over a
  newer write.
* **The database's encoding is checked on the way in.** `_utf8()`'s guard in
  the SQLite backend, moved to the one moment a connection can answer it: a
  database that is not UTF8 would make every byte-addressed read a conversion,
  and refusing is louder than converting.

## Where the store is, inside the database

A service file holds libpq parameters and nothing else, so there is no field
in it for outrage's own settings. The store is therefore the connection's
**current schema**, and a store of its own is asked for with libpq's own
spelling, `options=-csearch_path=<name>`. `PostgresStore._settle_schema()` is
the lookup, and it is not simply `current_schema()`: that is NULL when the
search path names a schema that does not exist yet, which is exactly the first
open this backend has to create.

## What is *not* here yet

Connecting, the schema, the version table and the compatibility rules are
here. The operations -- reading, writing, listing, the surveys -- are not, and
every one of them raises [`NotImplementedError`](https://docs.python.org/3/builtins/exceptions.html#NotImplementedError) below rather than being
absent, so that the class can be opened and the parts that are built can be
exercised. The backend is deliberately left **out** of
`outrage.store._BACKENDS` while that is true, so no mount spec can reach a
half-built store and no configuration can be written against one.

### outrage.store_postgres.ARCHIVE_TABLE *= 'document_archive'*

Where a row goes when it leaves `documents`. The SQLite backend's archive
table, with the same columns and for the same reason; what fills it is a
trigger rather than two statements, and that is step 6.

### outrage.store_postgres.CLIENT_VERSION_SETTING *= 'outrage.client_version'*

The setting a session declares itself with, read by the archive triggers so
that a build below `write_floor` is refused at the server rather than
trusted to have checked. A two-part name, which is how Postgres spells a
setting that is not one of its own.

### outrage.store_postgres.DEFAULT_SERVICE_FILE *= 'pg_service.conf'*

What a service file is called when a mount names one inside the store
directory. Not what this backend opens when a mount names nothing -- that
is libpq's own lookup, which is a search and not a path, and is why
[`PostgresStore.locates_own_store`](#outrage.store_postgres.PostgresStore.locates_own_store) is True. The name is here because
`FileStore` asks every backend what it calls its file, and this is the
honest answer for the case where there is one to name.

### outrage.store_postgres.MIGRATIONS *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[int](https://docs.python.org/3/builtins/functions.html#int), [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]]* *= {}*

What each version adds to the one below it. Empty while version 1 is the
only one, and the shape is load bearing all the same: **creating a store at
version N is version 1 plus the steps up to N**, never a separate script per
version, so that there is one definition of each version and every creation
exercises the migrations.

### outrage.store_postgres.MIN_SCHEMA_VERSION *= 1*

The oldest schema this build can still operate at. Raising it is a release
decision rather than a tidy-up, because it turns stores this build used to
open into stores it refuses, on devices whose owner did not ask for that.

### outrage.store_postgres.SCHEMA_TABLE *= 'outrage_schema'*

Where the three numbers live at the Postgres end.

### outrage.store_postgres.SCHEMA_VERSION *= 1*

The newest schema this build knows -- `F`. What a store created by this
build is created at, and what this build declares to the server.

### outrage.store_postgres.VERSIONS *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[int](https://docs.python.org/3/builtins/functions.html#int), [SchemaVersion](store.md#outrage.store.SchemaVersion)]* *= {1: SchemaVersion(version=1, read_floor=1, write_floor=1)}*

Every schema version this build knows, by number. One entry so far, and all
three of its numbers are 1: the first version locks nobody out because
there is nothing older than it.

The table rather than two constants, so that adding a version moves
[`MIN_SCHEMA_VERSION`](#outrage.store_postgres.MIN_SCHEMA_VERSION) and [`SCHEMA_VERSION`](#outrage.store_postgres.SCHEMA_VERSION) with it and cannot
leave one of them behind.

### *class* outrage.store_postgres.Compatibility(stored: [SchemaVersion](store.md#outrage.store.SchemaVersion), operating: [int](https://docs.python.org/3/builtins/functions.html#int), writable: [bool](https://docs.python.org/3/builtins/functions.html#bool))

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

What this build may do with the store it just found, and why.

The open rules as one value, so that `outrage check` and
`outrage schema status` answer from the same decision the open made
rather than each reaching it again.

#### stored *: [SchemaVersion](store.md#outrage.store.SchemaVersion)*

The store's own numbers, as [`SCHEMA_TABLE`](#outrage.store_postgres.SCHEMA_TABLE) holds them.

#### operating *: [int](https://docs.python.org/3/builtins/functions.html#int)*

The version whose shape this build reads and writes while it is open.

The store's own version when this build knows it, and
[`SCHEMA_VERSION`](#outrage.store_postgres.SCHEMA_VERSION) when the store is newer than this build and the
floors still admit it. A client writes what the store's version expects,
never what its own newest version would.

#### writable *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

False for a store this build may read and not write.

#### *property* read_only_reason *: [Refusal](errors.md#outrage.errors.Refusal) | [None](https://docs.python.org/3/builtins/constants.html#None)*

Why writing is refused, when it is, as the facts a sentence is written from.

### *class* outrage.store_postgres.PostgresStore(directory: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, \*, filename: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, service: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, mount_point: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, versioning: [bool](https://docs.python.org/3/builtins/functions.html#bool) = True, report: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False)

Bases: [`FileStore`](store.md#outrage.store.FileStore)

A document store held in a PostgreSQL schema, reached over a connection.

#### default_filename *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= 'pg_service.conf'*

What this backend calls its store file when a caller names none. Set by
every concrete backend, and the only thing about the file a backend
decides: that it *is* a file inside a directory is settled above, by
`store_file()`. `default_store_file()` is how the rest of the
package asks for it without naming a backend to ask.

#### backend_name *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= 'postgres'*

What this backend is called where a report or a refusal has to name it.
A short lowercase word, matching the store file's extension, so that a
sentence about a store and the name of its file agree.

#### format_version *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[int](https://docs.python.org/3/builtins/functions.html#int)]* *= 1*

The version of its own on-disk format this build writes. Compared
against [`stored_format_version`](#outrage.store_postgres.PostgresStore.stored_format_version) by [`outrage.maintenance.check()`](maintenance.md#outrage.maintenance.check),
which is why the comparison is written once rather than per backend --
"written by a newer outrage than this" is the same fault whatever wrote it,
even though each backend records the number somewhere different.

#### writable *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[bool](https://docs.python.org/3/builtins/functions.html#bool)]* *= True*

Stated rather than inherited, for the reason the SQLite backend states
it: the base says True, so a backend that forgets reports itself
writable, which is the wrong way for a mistake to fall.

#### versioned *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[bool](https://docs.python.org/3/builtins/functions.html#bool)]* *= True*

Stated for the same reason from the other side. The archive table is in
the schema from version 1, and what fills it is step 6.

#### manages_schema *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[bool](https://docs.python.org/3/builtins/functions.html#bool)]* *= True*

The one backend so far whose schema is managed rather than migrated in
place. It is what `outrage schema` dispatches on: the command is
generic across database backends, and a backend that keeps no managed
schema refuses it by name rather than being special-cased away.

#### locates_own_store *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[bool](https://docs.python.org/3/builtins/functions.html#bool)]* *= True*

The one backend so far that finds its own store. A mount naming no file
means libpq's own lookup, which is a search across two files and an
environment variable rather than a path -- so writing the usual path out
would say something narrower than the default rather than the same
thing. See [`outrage.store.FileStore.locates_own_store`](store.md#outrage.store.FileStore.locates_own_store).

#### service_name

Which entry of the service file this store is.

#### service

The entry this store connects with. Secrets reach the driver
through it and reach nothing else; see [`outrage.pgservice.Service`](pgservice.md#outrage.pgservice.Service).

#### path

The service file that was actually read. `path` on every other
backend is the store; here it is the configuration naming it, which
is the only thing about this store that is on this machine.

#### versioning

Whether a write keeps what it replaces.

#### problem *: [Refusal](errors.md#outrage.errors.Refusal) | [None](https://docs.python.org/3/builtins/constants.html#None)*

Why this build cannot operate at the version it found, on a
`report` open that met one. An ordinary open raises instead.

#### encoding

What the database stores text as. Asked before anything else
is, because a database that is not UTF8 is refused rather than
converted -- see `_settle_encoding()`.

#### schema

The schema the tables are in, settled on the first connection.

#### stored *: [SchemaVersion](store.md#outrage.store.SchemaVersion) | [None](https://docs.python.org/3/builtins/constants.html#None)*

The store's own three numbers, or None where the schema holds
no store. Only a `report` open ever sees the second.

#### compatibility *: [Compatibility](#outrage.store_postgres.Compatibility) | [None](https://docs.python.org/3/builtins/constants.html#None)*

What this build may do with what it found, or None where there is
nothing to do it to.

#### *static* service_file(directory: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None), filename: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None)) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/builtins/constants.html#None)

The service file a mount names, or None for libpq's own lookup.

**The one relaxation of the relative-only rule**, and it is this
backend's to make because the file is not the store. Every other
backend's file is a store inside the directory an operator named, so
an absolute path there would make the directory a lie and a mount
table unmovable. A service file is neither: the standard one is in the
home directory, it is shared with `psql` and everything else that
speaks libpq, and a copy of it inside `--dir` would be a second place
for a password to live.

So an absolute path, and a path opening with `~`, are taken as
written. Everything else is a name inside the store directory and
earns every refusal [`outrage.store.store_file()`](store.md#outrage.store.store_file) makes -- a `..`
climbing out of it included, which is the half of that rule that was
never about relocatability.

#### *classmethod* in_directory(directory: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, \*, filename: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, extensions: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, versioning: [bool](https://docs.python.org/3/builtins/functions.html#bool) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, lock: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, service: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, mount_point: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None) → [Self](https://docs.python.org/3/library/typing.html#typing.Self)

This backend's store, named by a service file and an entry in it.

Overridden for one reason: [`service_file()`](#outrage.store_postgres.PostgresStore.service_file) rather than the base's
[`store_file()`](store.md#outrage.store.store_file), so that an absolute or `~` FILE
reaches the constructor as itself. The refusals are the base's, in the
base's words -- `extensions` and `lock` are a tree's options and
are refused here as everywhere else -- and `service` is the one this
backend is the reason for, so it is taken rather than refused.

#### *classmethod* reporting(directory: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, \*, filename: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, service: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/builtins/constants.html#None) = None) → [Self](https://docs.python.org/3/library/typing.html#typing.Self)

This store, opened to be asked about: `report=True`, nothing else.

The base refuses this, because for a store in a file on this machine
there is no difference between asking about one and opening it. Here
there is: an empty schema stays empty, and a version this build cannot
operate at is recorded rather than raised.

#### close() → [None](https://docs.python.org/3/builtins/constants.html#None)

Close every connection this store opened, from whichever thread asks.

All of them, unlike the SQLite backend, which can only close its own:
sqlite3 refuses to let one thread touch another's connection at all,
and psycopg does not. A connection left open here is one the server
holds a backend process for, which is a resource at the far end rather
than a file handle at this one.

Safe to call twice, and a store closed while another thread is part
way through a call reports `BackendError` rather than opening a
replacement connection behind the caller's back.

#### *property* has_store *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

Whether the schema this store connected to holds one yet.

#### schema_state() → [SchemaState](store.md#outrage.store.SchemaState)

What this build makes of the store, for a report rather than a use.

One value, so that `outrage schema status` and `outrage check`
answer from the same decision rather than each reaching it again --
which is the way two reports of the same thing come to disagree.

#### create_schema(version: [int](https://docs.python.org/3/builtins/functions.html#int) | [None](https://docs.python.org/3/builtins/constants.html#None) = None) → [SchemaVersion](store.md#outrage.store.SchemaVersion)

Build a blank store at `version`, refusing a schema that holds one.

What `outrage schema create` reaches, and what a first open runs with
`version` of None -- which is [`SCHEMA_VERSION`](#outrage.store_postgres.SCHEMA_VERSION). A team whose
oldest client knows version 3 gets a store that client can use by
someone on a newer build naming 3 here.

The version is checked **before** the schema is looked at, because it
is a statement about the argument rather than about the store: a
version this build never knew is the same mistake whether or not
somebody else has already put a store where it was aimed, and
reporting the occupied schema first would send the reader to clear a
schema that was never going to be written.

#### *property* stored_format_version *: [int](https://docs.python.org/3/builtins/functions.html#int)*

The schema version recorded in the database this store opened.

Read at open and remembered, unlike the SQLite backend's, which reads
a pragma off a file it alone has: this one is a round trip, and the
number cannot change under an open store because nothing but the
migration command changes it and that takes the same advisory lock.

#### store_document(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str), content: [str](https://docs.python.org/3/builtins/stdtypes.html#str), format: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, \*, title: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, contents: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, encoding: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, updated_at: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None) → [str](https://docs.python.org/3/builtins/stdtypes.html#str)

Refused while the store is below this build's write floor; unbuilt otherwise.

Validation first, through the shared check, even though nothing here
writes yet: what a key and a format are is settled for every backend in
one place, and a backend that reached its own conclusion would be a
second namespace. See `outrage.store.Store._validated()`.

#### delete(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str), recursive: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, unchanged_since: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, dry_run: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False) → [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]

Refused below the write floor; unbuilt otherwise.

#### descendant_count(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED) → [int](https://docs.python.org/3/builtins/functions.html#int)

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

#### subtree_totals(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED) → [SubtreeTotals](store.md#outrage.store.SubtreeTotals)

What lies strictly below `key`, counted and optionally measured.

**The question about the territory**, where [`descendant_count()`](#outrage.store_postgres.PostgresStore.descendant_count) is
the question about a delete. That is the difference worth holding, and
it is why these are two methods rather than one with a mode: every
caller of `descendant_count` in this package asks it what a
non-recursive delete left behind, or whether anything is there at all,
and a count for that purpose has to include metadata because a delete
takes it. A caller mapping a subtree wants a different answer and says
so by calling something else.

So there is no `whole_subtree` here. This *is* that selection --
strictly below `key`, its own metadata unit included -- and offering
the other one would put the delete's question back into the method that
exists to be free of it. `keys` therefore equals
`descendant_count(key, whole_subtree=True)` exactly, which is asserted
rather than assumed: one meaning of "how many lie below" in the store,
not two that nearly agree.

The one call [`list_keys()`](#outrage.store_postgres.PostgresStore.list_keys)' descendant flags need, kept apart from
them so a backend overrides the *aggregate* and not the listing.
`SubtreeTotals` says what counts as a document, which is not what
counts as one in a listing.

`chars` is separate because it is separately expensive, and a backend
that can count without measuring should: this default cannot -- a walk
has the entry in hand -- but SQLite asks for a sum only when told to,
and on a directory of files a length means decoding every document.

`key_range` bounds it for the reason it bounds
[`descendant_count()`](#outrage.store_postgres.PostgresStore.descendant_count), and because
[`MountedStore`](mounts.md#outrage.mounts.MountedStore) cannot compose this without one:
the stretches of a store that a mount does not shadow are named as
ranges, and totals taken over the whole of it would count rows that
reading by key refuses.

**It reads the subtree**, so it costs what is under `key` rather than
what is beside it -- which is why [`list_keys()`](#outrage.store_postgres.PostgresStore.list_keys) asks for it only
when told to. Nothing here is maintained at write time.

The default walks, which is every store's answer until it has a better
one, and it is the answer [`MountedStore`](mounts.md#outrage.mounts.MountedStore) would
otherwise have no way to give for a store spliced under a prefix.

#### latest_change(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED) → [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)

The newest `updated_at` below `key`, or None where nothing is.

The aggregate a write precondition asks: one value whatever the size of
the subtree, so "has anything here moved since I looked" costs a query
rather than a walk. The selection is [`descendant_count()`](#outrage.store_postgres.PostgresStore.descendant_count)'s exactly
-- strictly below `key`, less the metadata unit a plain delete takes
with it, and `whole_subtree` keeps that unit -- so the two answer
about the same set of keys and a caller can hold one meaning for both.

**Metadata counts**, as it does there and for the same reason: a
`!title` written since the watermark is a change to the subtree, and
an aggregate with a second unstated meaning costs more than it saves.

**What it cannot see is a deletion.** The row that would carry the
timestamp is the row that has gone, so the newest change in a range
says nothing about what was *removed* from it. A guard built on this
covers edits and no more; when an archive exists, asking it the same
question over the same range is what answers the other half.

Timestamps are normalised to seconds ([`store_document()`](#outrage.store_postgres.PostgresStore.store_document)), so a
write inside the same second as a watermark is invisible to a
comparison against one. That is the weakness `content_sha256` exists
to avoid elsewhere, inherited here deliberately: a watermark over a
whole subtree has no single content to hash.

The default implementation walks the subtree and takes the maximum,
which is every store's answer until it has a better one: a database
has `max()`, a sorted file has a row range, and a directory of files
has the walk this does.

#### exists(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str)) → [bool](https://docs.python.org/3/builtins/functions.html#bool)

Whether `key` itself holds a document.

Not the same question as whether anything is below it: a bulk import
asks this per file to decide about one key, and a container that holds
nothing itself is free for a document to be written to.

Deliberately cheaper than a read, since the answer is wanted for every
file in an import and the content is not.

#### level_entry(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str)) → [Entry](store.md#outrage.store.Entry) | [None](https://docs.python.org/3/builtins/constants.html#None)

How `key` appears in its parent's listing, or None if it does not.

The same three answers [`list_keys()`](#outrage.store_postgres.PostgresStore.list_keys) gives about one key without
listing the level to find it: a stored document, an implicit key that
exists only because something lies beneath it, or nothing at all.

Asked by a caller that has to reconcile this store's level with keys
from somewhere else and must not count the same position twice. A
cheaper pair of questions -- does the key exist, does it have
descendants -- gets one corner wrong: metadata sits *at* a key rather
than below it, so a key holding only metadata has no document and no
descendants and still appears in the listing.

#### retrieve_document(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str), \*, offset: [int](https://docs.python.org/3/builtins/functions.html#int) = 0, max_chars: [int](https://docs.python.org/3/builtins/functions.html#int) = DEFAULT_MAX_CHARS, \*\*rest: [Any](https://docs.python.org/3/library/typing.html#typing.Any)) → [Excerpt](store.md#outrage.store.Excerpt)

Read the content stored at `key`.

`pattern` is a literal substring, not a regular expression; when
given, the read starts at its `occurrence`-th appearance at or after
the offset. The result is capped at `length` or `max_chars`,
whichever is smaller, and carries a continuation in the unit used.

`offset` counts characters, `byte_offset` counts UTF-8 bytes and
`line` counts lines from one. They are three positions in the same
document, so giving more than one is refused. `lines` limits a
line-addressed read to that many lines and is capped by `max_chars`.
A byte offset landing inside a character reads from that character's
first byte, and the excerpt says where it actually began.

**Every backend accepts a byte offset and returns identical content
for it.** Only the cost differs -- one that can seek does, one that
cannot converts and slices -- and that contract is what makes a byte
offset something a caller can carry between stores, and out of the
store altogether to a file [`bulk()`](bulk.md#module-outrage.bulk) exported.

#### list_keys(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, \*\*rest: [Any](https://docs.python.org/3/library/typing.html#typing.Any)) → [Page](store.md#outrage.store.Page)

List the keys immediately below `key`, or below the root.

Includes subkeys and metadata, and keys that exist only implicitly
because something beneath them has content.

`limit` and `cursor` page the level. Neither has a default: this
layer offers pagination and holds no opinion about how much a caller
can take, which is the tools' and the command line's question and they
answer it differently.

No `KeyRange` here, deliberately. This reads one *level*, not a
stretch of the order, and the cursor is the only bound a level has ever
needed; a range would have to be honoured by every part of a level's
answer, for no caller that exists.

**The two descendant flags turn a listing into a map of the subtree.**
`descendant_counts` fills `Entry.descendants` and
`Entry.descendant_documents`, `descendant_chars` fills
`Entry.descendant_chars`, and each is None where it was not
asked for. The selection is [`descendant_count()`](#outrage.store_postgres.PostgresStore.descendant_count)'s under
`whole_subtree` -- strictly below the listed key, its own metadata
unit included -- so an entry's own row and its descendant columns do
not overlap, and the two added together are the whole subtree.
`Entry` says what counts as a document there, which is not what
counts as one in a listing.

**Opt in because they cost**, which is the whole reason they are flags
and not columns. Naming a level is bounded by its fan-out -- one index
seek per child, whatever hangs below -- and a count over a child's
subtree reads that subtree, so asking for one puts the size of the
store back into a call that had stopped depending on it. Characters
cost more again and the length cache does not help them: measured over
a level of twenty children holding fifty thousand keys, naming the
level cost 0.19 ms, the counts took it to 8.6 ms, and the characters to
75 ms.

**They are filled over the page, not the level**, so `limit` bounds
what they cost as well as what comes back -- unlike `total` and
`total_chars`, which describe the level whatever the cursor is doing.
A caller paging a wide level pays per page and can stop.

Concrete where a backend has nothing faster: [`subtree_totals()`](#outrage.store_postgres.PostgresStore.subtree_totals) is
the one call each of these needs, and `_with_descendants()` fills a
page from it.

#### get_documents(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, max_chars: [int](https://docs.python.org/3/builtins/functions.html#int) = DEFAULT_BULK_MAX_CHARS, \*\*rest: [Any](https://docs.python.org/3/library/typing.html#typing.Any)) → [Page](store.md#outrage.store.Page)

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

#### missing_meta_stats(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*\*rest: [Any](https://docs.python.org/3/library/typing.html#typing.Any)) → [MissingMeta](store.md#outrage.store.MissingMeta)

What a metadata survey could not see, over exactly one page's window.

`coverage` adds counts for the whole selection. It is off by default
because each metadata name adds a selection-wide scan, while the three
window fields above are the bounded warning every survey needs.

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

#### keys_missing_meta(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*\*rest: [Any](https://docs.python.org/3/library/typing.html#typing.Any)) → [Page](store.md#outrage.store.Page)

Document keys in `subtree` carrying none of `meta_name`.

A survey by `!title` only sees documents that have one, so on its own
it silently under-reports the store. This names what the survey missed.

`key_range` narrows the subtree exactly as it narrows a survey, and
for the same reason: the two have to be askable over one stretch of the
store, and to agree about what was in range, or they stop describing
the same one.

#### audit_rows() → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[AuditRow](store.md#outrage.store.AuditRow)]

Every row this store holds, bookkeeping included, in one pass.

For [`outrage.maintenance.check()`](maintenance.md#outrage.maintenance.check) and nothing else -- see
`AuditRow` for why the reading surface does not offer this. One
pass rather than a query per check, because the checks that use it want
the same rows for different questions and a store large enough to be
worth checking is large enough for a second pass to be felt.

Order is not promised. Nothing auditing rows one at a time depends on
it, and a backend held in key order should not have to pay to prove it.

#### check_file(report: [Report](maintenance.md#outrage.maintenance.Report)) → [None](https://docs.python.org/3/builtins/constants.html#None)

Add what only this backend can say about its own file.

Called by [`outrage.maintenance.check()`](maintenance.md#outrage.maintenance.check) once the checks that any
backend can answer have run. Those are about rows and keys; this is
about *storage* -- whether SQLite still considers the database sound,
how much of it is sitting in the write-ahead log, whether a parquet
file is still in the sort order every read of it bisects.

Fills in [`details`](maintenance.md#outrage.maintenance.Report.details) with the numbers
worth printing whether or not anything is wrong, and appends to
`problems` for anything that is.

#### repair() → [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[Repaired](maintenance.md#outrage.maintenance.Repaired)]

Fix what [`check_file()`](#outrage.store_postgres.PostgresStore.check_file) found and this backend can act on.

Returns what was actually done, which may be nothing: a backend whose
storage cannot get into a repairable state returns an empty list, and
that is an honest answer rather than a silence. It is not the same
answer as [`check_file()`](#outrage.store_postgres.PostgresStore.check_file) finding nothing -- one says there is
nothing that *could* need repairing, the other that nothing does.

Nothing here may lose a document. A repair moves bytes about; one that
could discard content would need a backup taken first, and no backend
offers such a repair.

### *exception* outrage.store_postgres.ServiceUnusable(code: [str](https://docs.python.org/3/builtins/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`BackendError`](store.md#outrage.store.BackendError)

Every reason a service could not be read, as the one error an open raises.

[`outrage.pgservice.resolve()`](pgservice.md#outrage.pgservice.resolve) returns refusals rather than raising, so
that a file with three things wrong with it is reported once instead of
three runs running. An open has to raise, and this is the join: the code is
this class's own, the details carry every refusal, and
[`outrage.messages`](messages.md#module-outrage.messages) renders each of them through the template it
already has. Nothing composes a second sentence anywhere.

### outrage.store_postgres.compatibility(stored: [SchemaVersion](store.md#outrage.store.SchemaVersion)) → [Compatibility](#outrage.store_postgres.Compatibility)

Decide what this build may do with a store at `stored`, or refuse it.

The four cases, in one place:

* within `MIN..F`, operate at the store's own version;
* newer than this build but above `write_floor`, operate at `F`;
* newer, and between the floors, read only;
* older than `MIN`, or below `read_floor`, refused.

Refused by raising rather than by a fourth field, because a store this
build cannot read is not a store it half-opened: there is nothing for a
caller to do with such a value but raise it themselves.
