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
  newer write. A write that carries no `updated_at` is stamped inside the
  statement that writes it (`_STAMP`), and [`PostgresStore.now()`](#outrage.store_postgres.PostgresStore.now)
  answers from the same clock, which is what a watermark is taken from.
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

## Round trips

Every statement is a round trip to a server that may be on another continent,
so each operation here is **one or two statements** where the SQLite backend
would issue a loop of cheap ones. The level walk is a recursive query that
the server steps through, a listing's totals and its page come back from the
statement that walks it, a bulk read cuts each document to its cap before it
is sent, and a byte read fetches only the window it asked for. The predicates
themselves -- which rows a subtree, a range or a survey means -- are the SQLite
backend's own functions, so that the two cannot come to disagree about what
a selection is.

## Concurrent writers

Several devices write one store, so what a transaction on SQLite gets by
holding the whole file has to be arranged here, and it is arranged in three
parts rather than one.

* **The archive is a trigger** (`_ARCHIVE_FUNCTION`). Two writers to one
  existing key are not an insert conflict, so nothing on the client could
  keep both of the versions they replaced; a row trigger runs after the
  update has taken the row's lock, so each one copies the version it actually
  replaced. The same function makes the archive complete for any writer,
  `psql` included. A statement trigger beside it refuses a session that
  declared a build below `write_floor`.
* **A \`\`?\`\` claims its number with a lock on the number**, taken without
  waiting, in a `READ COMMITTED` transaction -- see
  `PostgresStore._allocate()`, and `PostgresStore._writing()` for why
  that one transaction is not serializable.
* **Every other write is \`\`SERIALIZABLE\`\` and retried** when the server says
  it could not be serialised. The net under any read-decide-write that the
  two targeted fixes do not cover, a delete's `unchanged_since` among them.

## A backup is a SQLite file

The one thing a store on a server cannot give its operator is a copy they can
open without it. So [`PostgresStore.backup()`](#outrage.store_postgres.PostgresStore.backup) reads the store in one
snapshot and writes it into a local SQLite store, archive included, which can
be opened, mounted and checked on a machine that cannot reach the server.

### outrage.store_postgres.ARCHIVE_TABLE *= 'document_archive'*

Where a row goes when it leaves `documents`. The SQLite backend's archive
table, with the same columns and for the same reason; what fills it is a
trigger rather than a statement of the client's -- see `_ARCHIVE_FUNCTION`.

### outrage.store_postgres.AUDIT_CHUNK *= 8192*

Rows audited per statement.

### outrage.store_postgres.BATCH *= 64*

How many rows a paged read asks for when the caller named no limit, and
what a run of reads grows from, doubling up to [`BATCH_CEILING`](#outrage.store_postgres.BATCH_CEILING). The
DuckDB backend's scheme and for its reason: a short page is one small
statement, and a long walk is not one statement per handful of rows. Every
statement here is a round trip, which is the cost a remote server is
measured in.

### outrage.store_postgres.BATCH_CEILING *= 4096*

The largest read [`BATCH`](#outrage.store_postgres.BATCH) grows to.

### outrage.store_postgres.CLIENT_VERSION_SETTING *= 'outrage.client_version'*

The setting a session declares itself with, read by the write-floor trigger
so that a build below `write_floor` is refused at the server rather than
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

### outrage.store_postgres.READAHEAD *= 1048576*

How many bytes of a document a byte- or line-addressed read fetches at
once. The shared slicing asks for small windows -- a few bytes of run-up and
four bytes a character, or 64 KB at a time while counting lines -- and each
one would otherwise be a statement of its own. So the first statement
fetches this much from where the read starts, the windows are served out of
it, and a read that runs past it fetches this much again. A megabyte covers
every read of an ordinary document in the one statement that also finds the
row, and a line far into a large one in a handful.

### outrage.store_postgres.RETRY_PAUSE *= 0.01*

The first pause between attempts, in seconds, doubling each time and drawn
at random below that bound, so that two writers who collided once do not
collide again in step.

### outrage.store_postgres.SCHEMA_TABLE *= 'outrage_schema'*

Where the three numbers live at the Postgres end.

### outrage.store_postgres.SCHEMA_VERSION *= 1*

The newest schema this build knows -- `F`. What a store created by this
build is created at, and what this build declares to the server.

### outrage.store_postgres.TRIGGER_NAMES *= ('outrage_write_floor', 'outrage_archive_update', 'outrage_archive_delete')*

The triggers a store is kept by, by name, for a check to look for.

### outrage.store_postgres.VERSIONING_OFF *= 'off'*

The value of [`VERSIONING_SETTING`](#outrage.store_postgres.VERSIONING_SETTING) that stops a session archiving.

### outrage.store_postgres.VERSIONING_SETTING *= 'outrage.versioning'*

The setting that carries a mount's `versioning` to the archive trigger,
[`VERSIONING_OFF`](#outrage.store_postgres.VERSIONING_OFF) or anything else. A session that never set it --
`psql`, or any other client -- archives, because the trigger is there to
make the archive complete and a writer that knows nothing of outrage is the
one it most needs to cover.

### outrage.store_postgres.VERSIONS *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[int](https://docs.python.org/3/builtins/functions.html#int), [SchemaVersion](store.md#outrage.store.SchemaVersion)]* *= {1: SchemaVersion(version=1, read_floor=1, write_floor=1)}*

Every schema version this build knows, by number. One entry so far, and all
three of its numbers are 1: the first version locks nobody out because
there is nothing older than it.

The table rather than two constants, so that adding a version moves
[`MIN_SCHEMA_VERSION`](#outrage.store_postgres.MIN_SCHEMA_VERSION) and [`SCHEMA_VERSION`](#outrage.store_postgres.SCHEMA_VERSION) with it and cannot
leave one of them behind.

### outrage.store_postgres.WRITE_ATTEMPTS *= 5*

How many times a write is tried before contention is reported rather than
retried. A serialization failure here means two devices touched the same
rows at the same moment, which at this store's load is rare; five in a row
means something is writing those rows continuously.

### outrage.store_postgres.WRITE_FLOOR_SQLSTATE *= 'OR001'*

The SQLSTATE the write-floor trigger raises. Its own code rather than
PL/pgSQL's generic `P0001`, so the client recognises the refusal by what
it is rather than by the words of a message. Class `OR` is outside every
class the standard and PostgreSQL reserve, which start with 0-4 or A-H.

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

### *class* outrage.store_postgres.PostgresStore(directory: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, \*, filename: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, service: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, mount_point: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, versioning: [bool](https://docs.python.org/3/builtins/functions.html#bool) = True, report: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False, create: [bool](https://docs.python.org/3/builtins/functions.html#bool) = True)

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

Stated for the same reason from the other side. The archive is filled at
the server, by `_ARCHIVE_FUNCTION`.

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

Whether a write keeps what it replaces. Read by the archive trigger
through [`VERSIONING_SETTING`](#outrage.store_postgres.VERSIONING_SETTING), which every connection declares.

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

#### *classmethod* in_directory(directory: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, \*, filename: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, extensions: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, versioning: [bool](https://docs.python.org/3/builtins/functions.html#bool) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, lock: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, service: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, mount_point: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, create: [bool](https://docs.python.org/3/builtins/functions.html#bool) = True) → [Self](https://docs.python.org/3/library/typing.html#typing.Self)

This backend's store, named by a service file and an entry in it.

Overridden for one reason: [`service_file()`](#outrage.store_postgres.PostgresStore.service_file) rather than the base's
[`store_file()`](store.md#outrage.store.store_file), so that an absolute or `~` FILE
reaches the constructor as itself. The refusals are the base's, in the
base's words -- `extensions` and `lock` are a tree's options and
are refused here as everywhere else -- and `service` is the one this
backend is the reason for, so it is taken rather than refused.
`create` is checked by the store itself, since nothing on this
machine can say whether a schema on the server holds one.

#### *classmethod* reporting(directory: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, \*, filename: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, service: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/builtins/constants.html#None) = None) → [Self](https://docs.python.org/3/library/typing.html#typing.Self)

This store, opened to be asked about: `report=True`, nothing else.

The base refuses this, because for a store in a file on this machine
there is no difference between asking about one and opening it. Here
there is: an empty schema stays empty, and a version this build cannot
operate at is recorded rather than raised.

#### *property* target *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)]*

The service, the schema, and the connection with its secrets redacted.

[`outrage.pgservice.Service.redacted`](pgservice.md#outrage.pgservice.Service.redacted) whole, rather than chosen
fields, for the reason it gives: a report built from it cannot reach a
secret by growing a field.

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

The document and its supplied metadata, upserted in one transaction.

The rows go in one `executemany`, which psycopg sends as a pipeline:
a document with a title and an index is one round trip, not three.
Validated first, through the shared check, and then refused if this
build may not write the store -- the argument is wrong whoever is
asked, and the store is read only whatever the argument.

**U+0000 is refused here and nowhere else yet.** A PostgreSQL
`text` value cannot hold it, and escaping it would be a second
encoding of every document for one character nobody writes on
purpose. Every field holding one is named at once, so a caller fixes
them in one pass. The other backends store it; refusing it in the
shared check instead would close that difference for all of them.

#### delete(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str), recursive: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, unchanged_since: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, dry_run: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False) → [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]

One statement: `DELETE ... RETURNING key`, or the `SELECT` it would run.

The SQLite backend selects first and deletes by key, because its
`DELETE` cannot say what it removed. Here it can, so the selection
and the delete are the same predicate in one statement, and a dry run
is that predicate read rather than acted on. The key's own row and its
metadata unit are one unit whatever the key is, and `recursive` adds
everything else below -- the SQLite backend's rule, from the same
functions. Every row it takes is archived by the trigger.

**\`\`unchanged_since\`\` is checked inside the delete's transaction**, so
on this backend it is atomic: the check reads through the same
connection, and a write that lands between the check and the delete
makes the serializable transaction fail and start again, check and
all. A dry run checks it the ordinary way.

#### now(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str) = keys.ROOT, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED) → [str](https://docs.python.org/3/builtins/stdtypes.html#str)

The server's time, from the clock that stamps this store's writes.

One statement, and `key` does not change the answer: the whole store
is stamped by the one server.

#### descendant_count(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False) → [int](https://docs.python.org/3/builtins/functions.html#int)

A `count(*)` over the subtree, less the metadata unit a plain delete takes.

#### subtree_totals(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, chars: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False) → [SubtreeTotals](store.md#outrage.store.SubtreeTotals)

Rows, documents and optionally characters below `key`, in one aggregate.

The characters are the stored `chars` column, so a sum reads no
document -- but it stays behind the flag all the same, because a
surface that is opt in on one backend and always on in another is two
contracts wearing one name.

#### latest_change(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False) → [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)

The newest `updated_at` over exactly the rows [`descendant_count()`](#outrage.store_postgres.PostgresStore.descendant_count) counts.

A text `max` under `COLLATE "C"`, which is what makes it the newest:
every stamp is one spelling of UTC to the second, so bytewise order is
time order, and a locale collation is under no obligation to agree.

#### exists(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str)) → [bool](https://docs.python.org/3/builtins/functions.html#bool)

One primary key lookup, selecting no content.

#### level_entry(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str)) → [Entry](store.md#outrage.store.Entry) | [None](https://docs.python.org/3/builtins/constants.html#None)

The key's own row if it has one, else whether anything lies below: one statement.

The SQLite backend asks the two questions in turn. Here each is a
round trip, and the second is an `EXISTS` on a range of the primary
key, so it rides along with the first rather than following it.

#### retrieve_document(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str), \*, offset: [int](https://docs.python.org/3/builtins/functions.html#int) = 0, byte_offset: [int](https://docs.python.org/3/builtins/functions.html#int) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, line: [int](https://docs.python.org/3/builtins/functions.html#int) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, lines: [int](https://docs.python.org/3/builtins/functions.html#int) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, length: [int](https://docs.python.org/3/builtins/functions.html#int) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, pattern: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, occurrence: [int](https://docs.python.org/3/builtins/functions.html#int) = 0, max_chars: [int](https://docs.python.org/3/builtins/functions.html#int) = DEFAULT_MAX_CHARS) → [Excerpt](store.md#outrage.store.Excerpt)

One lookup on the primary key, sliced by the shared slicing.

A character read fetches the document, as the SQLite backend does:
a character offset cannot be turned into a position in the stored
text without counting up to it, and the whole value is detoasted on
the server either way. A **byte** or **line** read does not -- see
`_byte_read()`.

#### list_keys(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, \*, limit: [int](https://docs.python.org/3/builtins/functions.html#int) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, cursor: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, descendant_counts: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False, descendant_chars: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False) → [Page](store.md#outrage.store.Page)[[Entry](store.md#outrage.store.Entry)]

One level, its totals and one page of it, in a single statement.

The SQLite backend's walk is a loop of short queries, each seeking past
the child it has just named, and at a fraction of a millisecond a query
that is the right trade. Across a network each is a round trip, so the
walk is written as a recursive query instead -- `_walk()` -- and
the server takes every seek. The level it names is then counted, its
characters summed from `parent`, and the page cut past the cursor
and joined to each stored child's row, all in the same statement.

**The totals are over the whole level and unaffected by the cursor**,
as everywhere: 20 keys of 22 is a listing and 20 of 40000 is a sample.
The descendant flags stay opt in and cost one aggregate per child on
the page, through [`subtree_totals()`](#outrage.store_postgres.PostgresStore.subtree_totals).

#### get_documents(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, max_chars: [int](https://docs.python.org/3/builtins/functions.html#int) = DEFAULT_BULK_MAX_CHARS, limit: [int](https://docs.python.org/3/builtins/functions.html#int) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, max_total_chars: [int](https://docs.python.org/3/builtins/functions.html#int) | [None](https://docs.python.org/3/builtins/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[Excerpt](store.md#outrage.store.Excerpt)]

The selection's totals from one aggregate, and a page read in batches.

**Each document is cut to \`\`max_chars\`\` on the server**, so a page of
long documents sends what the page returns rather than every document
whole. What an excerpt reports beyond its text -- the totals and where
to resume -- comes from the stored lengths; see `_bulk_excerpt()`.

The page is read a batch at a time past the cursor, as the DuckDB
backend reads one, so that `limit` and `max_total_chars` decide
how much is fetched: a caller naming a limit gets one statement of
`limit + 1` rows, which is exactly enough to know whether another
page follows.

#### missing_meta_stats(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, window: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, meta_name: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] = 'title', sample: [int](https://docs.python.org/3/builtins/functions.html#int) = 0, coverage: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False) → [MissingMeta](store.md#outrage.store.MissingMeta)

Documents carrying none of `meta_name`, over one survey window.

The window is measured at the position the document's metadata
*would* have taken, synthesised in SQL exactly as the SQLite backend
does it -- see [`outrage.store_sqlite.SqliteStore.missing_meta_stats()`](store_sqlite.md#outrage.store_sqlite.SqliteStore.missing_meta_stats)
for why it is that position and not the document's own.

#### keys_missing_meta(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] = 'title', limit: [int](https://docs.python.org/3/builtins/functions.html#int) | [None](https://docs.python.org/3/builtins/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]

The selection [`missing_meta_stats()`](#outrage.store_postgres.PostgresStore.missing_meta_stats) counts, a page at a time.

Keys only, so a page is one statement of `limit + 1` rows beside the
totals, as the SQLite backend reads it.

#### audit_rows() → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[AuditRow](store.md#outrage.store.AuditRow)]

Every row, as written, a chunk at a time in key order.

A chunk per statement rather than a server-side cursor, which would
hold a transaction open for as long as the caller took to walk it --
and a caller walking this may ask the store something else between two
rows.

#### *property* backup_suffix *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

`.sqlite`, because that is what a backup of this store is.

The base takes the store file's extension, which here would name the
copy after the service file -- `store-<stamp>.conf`, a database
dressed as somebody's configuration.

#### backup(destination: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, \*, overwrite: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False) → [Backup](store.md#outrage.store.Backup)

A consistent snapshot of the store, written into a local SQLite store.

**A SQLite file rather than a copy of the schema**, John's call: the
point of a backup of a shared store is that it can be opened, mounted
and checked on a machine that cannot reach the server, and nothing
but a file on this machine does that. The two backends keep the same
nine stored columns in the same order, so a row goes across as it is,
`updated_at` and `sort_key` included, and so does the archive.

**Consistent** because every row is read in one `REPEATABLE READ`
transaction: several devices write this store, and a copy read over
several transactions could hold a document without the metadata
written beside it. The rows stream through a server-side cursor
rather than being fetched whole, since a store worth backing up is one
it would be foolish to hold in memory.

Verified against **the snapshot rather than the live store**, which
is the other half of being shared: the base's check compares the copy
with the store as it is by the time the copy is finished, and here
that is somebody else's writes away from the copy. So the snapshot's
own keys and counts are what the copy is held to, and SQLite's
integrity check says the file is sound.

#### check_file(report: [Report](maintenance.md#outrage.maintenance.Report)) → [None](https://docs.python.org/3/builtins/constants.html#None)

The schema's numbers, what this build makes of them, and the triggers.

**The version and the floors come from** [`schema_state()`](#outrage.store_postgres.PostgresStore.schema_state), which
is also what `outrage schema status` prints: two reports reaching
the same decision separately is how they come to disagree. A store
this build may only read is a note rather than a fault -- the store is
sound, and it is this client that is behind it.

**The triggers are the one thing about the storage that can be wrong
without anything failing**, which is what the SQLite backend's check
of its length cache is for too. Nothing in this package drops one, but
the schema is on a server anybody with the role can alter, and a
missing archive trigger loses every replaced version in silence.
Reported and not repaired: recreating one is a change to a shared
schema, which is the migration command's to make rather than a check's.

#### repair() → [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[Repaired](maintenance.md#outrage.maintenance.Repaired)]

Nothing, and deliberately.

The storage has no state a repair could move about: there is no log
to fold back and no cache to go stale, and the server keeps its own
files. What a check can find wrong -- a missing trigger -- is a change
to a schema other clients share, which is not a thing to do as a side
effect of looking at it.

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
