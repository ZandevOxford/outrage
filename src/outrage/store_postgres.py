"""The PostgreSQL backend: one store, shared by every device that can reach it.

The first backend whose store is not on this machine. Everything else in the
package is a file inside a directory an operator named; this one is a
*connection*, and the file a mount names is somebody else's configuration --
libpq's connection service file, read by :mod:`outrage.pgservice`. What
follows from that is most of what is written down here.

## What is settled at the far end rather than at this one

* **The schema version lives in the database**, in :data:`SCHEMA_TABLE`, with
  its own numbering starting at 1. A SQLite store is migrated in place when it
  is opened, because the build that opens it is the only build that has it. A
  shared store has several, on several devices, so a build opening one never
  changes its version: it operates at the version it finds, between
  :data:`MIN_SCHEMA_VERSION` and :data:`SCHEMA_VERSION`, and migration is a
  command somebody runs. :class:`Compatibility` is the decision that comes
  out of that, and :func:`compatibility` states all four of its cases.
* **Ordering is declared, not inherited.** Every cursor, range and page in this
  package assumes keys sort bytewise, which is SQLite's ``BINARY`` and is
  *not* what an ordinary Postgres database does: this machine's test database
  orders seven perfectly ordinary keys differently from Python, and the two
  orders share no prefix at all. So every text column here carries
  ``COLLATE "C"`` -- see :data:`_TABLE`.
* **The server's clock stamps writes**, not this process's, because two
  devices with skewed clocks would otherwise let a precondition pass over a
  newer write.
* **The database's encoding is checked on the way in.** ``_utf8()``'s guard in
  the SQLite backend, moved to the one moment a connection can answer it: a
  database that is not UTF8 would make every byte-addressed read a conversion,
  and refusing is louder than converting.

## Where the store is, inside the database

A service file holds libpq parameters and nothing else, so there is no field
in it for outrage's own settings. The store is therefore the connection's
**current schema**, and a store of its own is asked for with libpq's own
spelling, ``options=-csearch_path=<name>``. :meth:`PostgresStore._settle_schema` is
the lookup, and it is not simply ``current_schema()``: that is NULL when the
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

* **The archive is a trigger** (:data:`_ARCHIVE_FUNCTION`). Two writers to one
  existing key are not an insert conflict, so nothing on the client could
  keep both of the versions they replaced; a row trigger runs after the
  update has taken the row's lock, so each one copies the version it actually
  replaced. The same function makes the archive complete for any writer,
  ``psql`` included. A statement trigger beside it refuses a session that
  declared a build below ``write_floor``.
* **A ``?`` claims its number with a lock on the number**, taken without
  waiting, in a ``READ COMMITTED`` transaction -- see
  :meth:`PostgresStore._allocate`, and :meth:`PostgresStore._writing` for why
  that one transaction is not serializable.
* **Every other write is ``SERIALIZABLE`` and retried** when the server says
  it could not be serialised. The net under any read-decide-write that the
  two targeted fixes do not cover, a delete's ``unchanged_since`` among them.

## What is *not* here yet

The server's clock, or the maintenance half of the interface: :meth:`PostgresStore.check_file`
and :meth:`PostgresStore.repair` raise :class:`NotImplementedError`. The
backend is deliberately left **out** of ``outrage.store._BACKENDS`` while that
is true, so no mount spec can reach a half-built store and no configuration
can be written against one.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Self, TypeVar

from . import keys, pgservice
from .errors import Refusal
from .eventlog import EventLog
from .maintenance import Repaired, Report
from .store import (
    DEFAULT_BULK_MAX_CHARS,
    DEFAULT_MAX_CHARS,
    EVERYTHING,
    UNBOUNDED,
    AuditRow,
    BackendError,
    BoundedSubtree,
    Entry,
    Excerpt,
    FileStore,
    InvalidArgumentError,
    KeyNotFoundError,
    KeyRange,
    MissingMeta,
    Page,
    PatternNotFoundError,
    ReadOnlyStoreError,
    SchemaState,
    SchemaVersion,
    Store,
    SubtreeTotals,
    _byte_excerpt,
    _cursor_bound,
    _excerpt,
    _find_byte_occurrence,
    _find_occurrence,
    _line_at_byte,
    _line_byte_offset,
    _line_excerpt,
    _logged,
    _now,
    _scope,
    _with_descendants,
    check_read_position,
    check_unchanged,
    entry_kind,
    resolve_directory,
    store_file,
)
from .store_sqlite import _below, _meta_clauses, _range_clauses, _row_values, _subtree_clauses

_T = TypeVar("_T")

#: What a service file is called when a mount names one inside the store
#: directory. Not what this backend opens when a mount names nothing -- that
#: is libpq's own lookup, which is a search and not a path, and is why
#: :attr:`PostgresStore.locates_own_store` is True. The name is here because
#: ``FileStore`` asks every backend what it calls its file, and this is the
#: honest answer for the case where there is one to name.
DEFAULT_SERVICE_FILE = pgservice.SYSTEM_FILE_NAME


#: Every schema version this build knows, by number. One entry so far, and all
#: three of its numbers are 1: the first version locks nobody out because
#: there is nothing older than it.
#:
#: The table rather than two constants, so that adding a version moves
#: :data:`MIN_SCHEMA_VERSION` and :data:`SCHEMA_VERSION` with it and cannot
#: leave one of them behind.
VERSIONS: Mapping[int, SchemaVersion] = {1: SchemaVersion(1, 1, 1)}

#: The oldest schema this build can still operate at. Raising it is a release
#: decision rather than a tidy-up, because it turns stores this build used to
#: open into stores it refuses, on devices whose owner did not ask for that.
MIN_SCHEMA_VERSION = min(VERSIONS)

#: The newest schema this build knows -- ``F``. What a store created by this
#: build is created at, and what this build declares to the server.
SCHEMA_VERSION = max(VERSIONS)

#: Where the three numbers live at the Postgres end.
SCHEMA_TABLE = "outrage_schema"

#: Where a row goes when it leaves ``documents``. The SQLite backend's archive
#: table, with the same columns and for the same reason; what fills it is a
#: trigger rather than a statement of the client's -- see :data:`_ARCHIVE_FUNCTION`.
ARCHIVE_TABLE = "document_archive"

#: The setting a session declares itself with, read by the write-floor trigger
#: so that a build below ``write_floor`` is refused at the server rather than
#: trusted to have checked. A two-part name, which is how Postgres spells a
#: setting that is not one of its own.
CLIENT_VERSION_SETTING = "outrage.client_version"

#: The setting that carries a mount's ``versioning`` to the archive trigger,
#: :data:`VERSIONING_OFF` or anything else. A session that never set it --
#: ``psql``, or any other client -- archives, because the trigger is there to
#: make the archive complete and a writer that knows nothing of outrage is the
#: one it most needs to cover.
VERSIONING_SETTING = "outrage.versioning"

#: The value of :data:`VERSIONING_SETTING` that stops a session archiving.
VERSIONING_OFF = "off"

#: The SQLSTATE the write-floor trigger raises. Its own code rather than
#: PL/pgSQL's generic ``P0001``, so the client recognises the refusal by what
#: it is rather than by the words of a message. Class ``OR`` is outside every
#: class the standard and PostgreSQL reserve, which start with 0-4 or A-H.
WRITE_FLOOR_SQLSTATE = "OR001"

#: How many times a write is tried before contention is reported rather than
#: retried. A serialization failure here means two devices touched the same
#: rows at the same moment, which at this store's load is rare; five in a row
#: means something is writing those rows continuously.
WRITE_ATTEMPTS = 5

#: The first pause between attempts, in seconds, doubling each time and drawn
#: at random below that bound, so that two writers who collided once do not
#: collide again in step.
RETRY_PAUSE = 0.01

#: The SQLSTATEs that mean "try the whole transaction again": a serialization
#: failure, and a deadlock, which the server resolves by failing one side.
_RETRYABLE = frozenset({"40001", "40P01"})

#: The documents table, and the whole of why every text column names a
#: collation.
#:
#: **``COLLATE "C"`` is not a precaution.** A Postgres database normally has a
#: locale collation, and this was measured against one rather than reasoned
#: about: ``a_b``, ``a-b``, ``a!x``, ``a/b``, ``a/B``, ``A/b`` and ``a/x``
#: come back in one order under an ``en_US.UTF-8`` database's own collation
#: and in a completely different one bytewise, the two sharing no prefix at
#: all. Every cursor, range and page in this package assumes the second. A
#: store built without this pages wrongly on its first listing, skipping and
#: repeating keys, and raises nothing at all.
#:
#: **Every text column, not only the two that are ordered.** ``key`` and
#: ``sort_key`` are what a page bounds on, so they are the ones that would
#: fail loudly; but ``parent``, ``doc_key``, ``meta_name`` and ``meta_path``
#: are ordered by the metadata surveys, ``updated_at`` is compared as text by
#: ``latest_change`` and ``unchanged_since``, and a column left out is a
#: question nobody asked yet. One rule over the table is cheaper to hold than
#: six judgements about which comparisons are safe.
#:
#: ``chars`` and ``bytes`` are generated columns, which is what the SQLite
#: length cache and its three triggers become here: a value computed with the
#: row cannot go stale, so there is no threshold to tune and no cache to
#: check. They are ``STORED`` because a byte read wants the length without
#: touching the content.
_TABLE = """
CREATE TABLE IF NOT EXISTS {documents} (
  key        text COLLATE "C" PRIMARY KEY,
  doc_key    text COLLATE "C" NOT NULL,
  meta_name  text COLLATE "C",
  meta_path  text COLLATE "C",
  parent     text COLLATE "C" NOT NULL,
  content    text COLLATE "C" NOT NULL,
  format     text COLLATE "C",
  updated_at text COLLATE "C" NOT NULL,
  sort_key   text COLLATE "C" NOT NULL,
  chars      integer GENERATED ALWAYS AS (char_length(content)) STORED,
  bytes      integer GENERATED ALWAYS AS (octet_length(content)) STORED
)
"""

_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_documents_parent ON {documents} (parent)",
    "CREATE INDEX IF NOT EXISTS idx_documents_meta ON {documents} (meta_name, meta_path, doc_key)",
    "CREATE INDEX IF NOT EXISTS idx_documents_sort ON {documents} (sort_key)",
)

#: The archive: the live table's columns in the same order, no primary key,
#: and one index on what a reader would ask for first. The SQLite backend's
#: reasoning applies unchanged -- a key has many rows here, and ``updated_at``
#: is stamped to the second, so ``(key, updated_at)`` is not unique either.
_ARCHIVE = """
CREATE TABLE IF NOT EXISTS {archive} (
  key        text COLLATE "C" NOT NULL,
  doc_key    text COLLATE "C" NOT NULL,
  meta_name  text COLLATE "C",
  meta_path  text COLLATE "C",
  parent     text COLLATE "C" NOT NULL,
  content    text COLLATE "C" NOT NULL,
  format     text COLLATE "C",
  updated_at text COLLATE "C" NOT NULL,
  sort_key   text COLLATE "C" NOT NULL
)
"""

_ARCHIVE_INDEX = "CREATE INDEX IF NOT EXISTS idx_archive_key ON {archive} (key, updated_at)"

#: The stored columns of a row, in :func:`outrage.store_sqlite._row_values`'s order.
_COLUMNS = "(key, doc_key, meta_name, meta_path, parent, content, format, updated_at, sort_key)"

#: What an upsert moves when the key is already there: the three columns that
#: are not derived from the key.
_UPSERTED = "content = excluded.content, format = excluded.format, updated_at = excluded.updated_at"

#: Copy the row a write replaces or a delete takes into the archive.
#:
#: **A row trigger, not a statement of the client's**, for the case the SQLite
#: backend never meets: two devices writing one existing key at once. That is
#: not an insert conflict, so ``ON CONFLICT`` cannot see it, and a client that
#: copied the row before its upsert would copy whatever it read -- both
#: writers the same version, and the one in between never archived. A
#: ``BEFORE UPDATE`` trigger runs once the update holds the row's lock, so each
#: copies the version it actually replaced.
#:
#: Which updates count as a change is the trigger's ``WHEN``
#: (:data:`_TRIGGERS`), the SQLite backend's rule: ``content``, ``format`` or
#: ``updated_at``, the three columns an upsert can move.
#:
#: The body is a string handed to the server, so the archive's name is written
#: into it qualified when the store is created -- :meth:`PostgresStore._create`
#: -- rather than looked up on every row.
_ARCHIVE_FUNCTION = """
BEGIN
  IF current_setting({versioning}, true) IS DISTINCT FROM {off} THEN
    INSERT INTO {archive}
      (key, doc_key, meta_name, meta_path, parent, content, format, updated_at, sort_key)
    VALUES
      (OLD.key, OLD.doc_key, OLD.meta_name, OLD.meta_path, OLD.parent,
       OLD.content, OLD.format, OLD.updated_at, OLD.sort_key);
  END IF;
  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;
  RETURN NEW;
END
"""

#: Refuse a statement from a session that declared a build below ``write_floor``.
#:
#: What turns away a long-running server that connected before a migration
#: raised the floor: its own :class:`Compatibility` was decided at open and is
#: still saying yes. Per statement rather than per row, because the answer is
#: about the session and not about any row. A session that declared nothing is
#: let through -- that is ``psql``, or an operator's repair, and neither is a
#: build the floor could be about.
#:
#: The three numbers go out as the error's detail, so the client can say what
#: refused it without asking again.
_WRITE_FLOOR_FUNCTION = """
DECLARE
  declared text := current_setting({client_version}, true);
  stored record;
BEGIN
  IF coalesce(declared, '') = '' THEN
    RETURN NULL;
  END IF;
  SELECT version, read_floor, write_floor INTO stored FROM {versions};
  IF declared::integer < stored.write_floor THEN
    RAISE EXCEPTION
        'outrage build % may not write a store at schema version %, whose write floor is %',
        declared, stored.version, stored.write_floor
      USING ERRCODE = {sqlstate},
            DETAIL = json_build_object(
              'version', stored.version,
              'read_floor', stored.read_floor,
              'write_floor', stored.write_floor)::text;
  END IF;
  RETURN NULL;
END
"""

#: The two functions above, by the name each is created under in the schema.
_FUNCTIONS = {
    "outrage_archive": _ARCHIVE_FUNCTION,
    "outrage_write_floor": _WRITE_FLOOR_FUNCTION,
}

#: What calls them. ``TRUNCATE`` takes the floor check and not the archive,
#: which a statement that empties the table in one step has no rows to give.
_TRIGGERS = (
    "CREATE TRIGGER outrage_write_floor "
    "BEFORE INSERT OR UPDATE OR DELETE OR TRUNCATE ON {documents} "
    "FOR EACH STATEMENT EXECUTE FUNCTION {write_floor_function}()",
    "CREATE TRIGGER outrage_archive_update BEFORE UPDATE ON {documents} FOR EACH ROW "
    "WHEN (OLD.content IS DISTINCT FROM NEW.content "
    "OR OLD.format IS DISTINCT FROM NEW.format "
    "OR OLD.updated_at IS DISTINCT FROM NEW.updated_at) "
    "EXECUTE FUNCTION {archive_function}()",
    "CREATE TRIGGER outrage_archive_delete BEFORE DELETE ON {documents} FOR EACH ROW "
    "EXECUTE FUNCTION {archive_function}()",
)

#: The three numbers, and a unique index that makes the table hold exactly one
#: row. Expressed as an index on a constant rather than as an extra column,
#: because the three columns are the design and a fourth one carrying ``true``
#: would be a thing to explain in every reading of the table.
_SCHEMA_TABLE = """
CREATE TABLE IF NOT EXISTS {versions} (
  version     integer NOT NULL,
  read_floor  integer NOT NULL,
  write_floor integer NOT NULL
)
"""

_SCHEMA_TABLE_ONE_ROW = (
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_outrage_schema_one_row ON {versions} ((true))"
)

#: What each version adds to the one below it. Empty while version 1 is the
#: only one, and the shape is load bearing all the same: **creating a store at
#: version N is version 1 plus the steps up to N**, never a separate script per
#: version, so that there is one definition of each version and every creation
#: exercises the migrations.
MIGRATIONS: Mapping[int, Sequence[str]] = {}

#: What ``$user`` in a search path stands for. Postgres expands it to the
#: session user, and a first open has to expand it the same way rather than
#: creating a schema literally called that.
_USER_SCHEMA = "$user"

#: Salt for the advisory lock, so that the number this backend takes is its
#: own rather than one another application might arrive at. Hashed here rather
#: than with the server's ``hashtext``, which is undocumented and free to
#: change: a lock two builds compute differently is not a lock.
_LOCK_NAMESPACE = b"outrage.schema."

#: Salt for the parent half of the lock a ``?`` allocation takes on a number.
#: That lock is PostgreSQL's two-integer form, whose keys are a space apart
#: from the one-bigint form the schema lock uses, so the two cannot meet
#: whatever they hash to; the salt keeps the parent half this backend's own.
_ALLOCATION_NAMESPACE = b"outrage.allocate."

#: Try the lock on one candidate number, as SQL: the parent's half as a
#: parameter and the number's as the expression ``{number}``, which is
#: wrapped into 32 bits. PostgreSQL's two-integer form takes two ``int4``, and
#: a number is any run of digits. A wrap that lands two numbers on one lock
#: only makes an allocator skip a number it did not need to, which is the
#: whole cost of it.
_TRY_NUMBER = (
    "pg_try_advisory_xact_lock(%s, ((({number})::numeric %% 4294967296) - 2147483648)::int)"
)

#: A numeric segment, as the server tests it. The same rule as
#: :data:`outrage.keys.NUMERIC_RE`, ASCII digits and nothing else, which a
#: test holds the two to.
_NUMERIC_SQL = "'^[0-9]+$'"

#: How many rows a paged read asks for when the caller named no limit, and
#: what a run of reads grows from, doubling up to :data:`BATCH_CEILING`. The
#: DuckDB backend's scheme and for its reason: a short page is one small
#: statement, and a long walk is not one statement per handful of rows. Every
#: statement here is a round trip, which is the cost a remote server is
#: measured in.
BATCH = 64

#: The largest read :data:`BATCH` grows to.
BATCH_CEILING = 4096

#: Rows audited per statement.
AUDIT_CHUNK = 8192

#: How many bytes of a document a byte- or line-addressed read fetches at
#: once. The shared slicing asks for small windows -- a few bytes of run-up and
#: four bytes a character, or 64 KB at a time while counting lines -- and each
#: one would otherwise be a statement of its own. So the first statement
#: fetches this much from where the read starts, the windows are served out of
#: it, and a read that runs past it fetches this much again. A megabyte covers
#: every read of an ordinary document in the one statement that also finds the
#: row, and a line far into a large one in a handful.
READAHEAD = 1024 * 1024

#: How many times a byte read starts again when the document is rewritten
#: underneath it. Only a read that needed a second window can meet that, and
#: meeting it twice in a row means a writer is rewriting this one document
#: continuously, which is worth an error rather than a loop.
_REREADS = 3

#: The one character a PostgreSQL ``text`` value cannot hold.
_NUL = "\0"


def _psycopg() -> Any:
    """psycopg, or a sentence saying it is not installed.

    Imported through a function, like every other optional backend here, so
    that a mount on an install without the extra is answered rather than
    raising ``ModuleNotFoundError`` at whoever is watching.
    """
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - exercised by uninstalling
        raise BackendError("postgres-needs-psycopg", reason=str(exc)) from exc
    return psycopg


def _lock_number(schema: str) -> int:
    """The advisory lock a first open of ``schema`` takes, as a signed bigint.

    Per schema rather than per database, because two stores in one database
    are two stores and a lock they shared would serialise creations that have
    nothing to do with each other.
    """
    return _hashed_lock(_LOCK_NAMESPACE, schema)


def _allocation_space(schema: str, parent: str) -> int:
    """The parent's half of the lock an allocation takes on a number, as a signed int4.

    Per parent, because what an allocation must not share is a number among
    the children of one key. Two parents hashing alike only make an
    allocator skip a number held under the other one.
    """
    return _hashed_lock(_ALLOCATION_NAMESPACE, schema, parent, size=4)


def _hashed_lock(namespace: bytes, *parts: str, size: int = 8) -> int:
    """An advisory lock number of ``size`` bytes for ``parts`` under ``namespace``.

    The parts are joined with NUL, which neither a schema name nor a key can
    hold, so no two different tuples of parts join to the same bytes.
    """
    joined = "\0".join(parts).encode("utf-8")
    digest = hashlib.blake2b(namespace + joined, digest_size=size).digest()
    return int.from_bytes(digest, "big", signed=True)


@dataclass(frozen=True, slots=True)
class Compatibility:
    """What this build may do with the store it just found, and why.

    The open rules as one value, so that ``outrage check`` and
    ``outrage schema status`` answer from the same decision the open made
    rather than each reaching it again.
    """

    stored: SchemaVersion
    """The store's own numbers, as :data:`SCHEMA_TABLE` holds them."""

    operating: int
    """The version whose shape this build reads and writes while it is open.

    The store's own version when this build knows it, and
    :data:`SCHEMA_VERSION` when the store is newer than this build and the
    floors still admit it. A client writes what the store's version expects,
    never what its own newest version would.
    """

    writable: bool
    """False for a store this build may read and not write."""

    @property
    def read_only_reason(self) -> Refusal | None:
        """Why writing is refused, when it is, as the facts a sentence is written from."""
        if self.writable:
            return None
        return Refusal(
            "postgres-below-write-floor",
            overridable=False,
            version=self.stored.version,
            write_floor=self.stored.write_floor,
            build=SCHEMA_VERSION,
        )


def compatibility(stored: SchemaVersion) -> Compatibility:
    """Decide what this build may do with a store at ``stored``, or refuse it.

    The four cases, in one place:

    * within ``MIN..F``, operate at the store's own version;
    * newer than this build but above ``write_floor``, operate at ``F``;
    * newer, and between the floors, read only;
    * older than ``MIN``, or below ``read_floor``, refused.

    Refused by raising rather than by a fourth field, because a store this
    build cannot read is not a store it half-opened: there is nothing for a
    caller to do with such a value but raise it themselves.
    """
    if stored.version < MIN_SCHEMA_VERSION:
        raise BackendError(
            "postgres-schema-too-old",
            version=stored.version,
            supported=MIN_SCHEMA_VERSION,
            build=SCHEMA_VERSION,
        )
    if stored.version <= SCHEMA_VERSION:
        return Compatibility(stored=stored, operating=stored.version, writable=True)
    if SCHEMA_VERSION < stored.read_floor:
        raise BackendError(
            "postgres-schema-too-new",
            version=stored.version,
            read_floor=stored.read_floor,
            build=SCHEMA_VERSION,
        )
    return Compatibility(
        stored=stored,
        operating=SCHEMA_VERSION,
        writable=SCHEMA_VERSION >= stored.write_floor,
    )


class ServiceUnusable(BackendError):
    """Every reason a service could not be read, as the one error an open raises.

    :func:`outrage.pgservice.resolve` returns refusals rather than raising, so
    that a file with three things wrong with it is reported once instead of
    three runs running. An open has to raise, and this is the join: the code is
    this class's own, the details carry every refusal, and
    :mod:`outrage.messages` renders each of them through the template it
    already has. Nothing composes a second sentence anywhere.
    """


class PostgresStore(FileStore):
    """A document store held in a PostgreSQL schema, reached over a connection."""

    default_filename = DEFAULT_SERVICE_FILE
    backend_name = "postgres"
    format_version = SCHEMA_VERSION
    #: Stated rather than inherited, for the reason the SQLite backend states
    #: it: the base says True, so a backend that forgets reports itself
    #: writable, which is the wrong way for a mistake to fall.
    writable = True
    #: Stated for the same reason from the other side. The archive is filled at
    #: the server, by :data:`_ARCHIVE_FUNCTION`.
    versioned = True
    #: The one backend so far whose schema is managed rather than migrated in
    #: place. It is what ``outrage schema`` dispatches on: the command is
    #: generic across database backends, and a backend that keeps no managed
    #: schema refuses it by name rather than being special-cased away.
    manages_schema = True
    #: The one backend so far that finds its own store. A mount naming no file
    #: means libpq's own lookup, which is a search across two files and an
    #: environment variable rather than a path -- so writing the usual path out
    #: would say something narrower than the default rather than the same
    #: thing. See :attr:`outrage.store.FileStore.locates_own_store`.
    locates_own_store = True

    def __init__(
        self,
        directory: str | os.PathLike[str] | None = None,
        *,
        filename: str | os.PathLike[str] | None = None,
        service: str | None = None,
        log: EventLog | None = None,
        mount_point: str | None = None,
        versioning: bool = True,
        report: bool = False,
    ) -> None:
        """Resolve the service, connect, and settle the schema.

        ``filename`` is the service file. Unlike every other backend's it may
        be absolute or start with ``~`` -- see :meth:`service_file` -- and it
        may be left out, which means libpq's lookup.

        ``report`` opens the store **to be asked about** rather than to be
        used, which is what ``outrage schema`` does. It changes the two
        judgements an ordinary open makes on the way in: a schema holding no
        store is left holding none instead of being created, and a version
        this build cannot operate at is recorded instead of refused. Both
        differences are the same point -- a report on a store that cannot be
        opened is exactly the report worth having, and creating one is the
        opposite of asking about it. Nothing else changes, and a store opened
        this way still answers no operation: :meth:`_opened` refuses in the
        words the open would have used.

        The base constructor is deliberately not called. It settles two things
        this backend answers differently -- that the store file is a name
        inside the store directory, and that the directory should be made
        before the file is opened -- and calling it would mean unpicking both.
        What it settles that *does* apply, the store directory and the shared
        infrastructure beside it, is done here in the same order.
        """
        Store.__init__(self, log=log, mount_point=mount_point)
        self.directory = resolve_directory(directory)
        # The event log and the backups live here whatever the store is, so
        # the directory is made even though nothing of the store is in it.
        self.directory.mkdir(parents=True, exist_ok=True)

        #: Which entry of the service file this store is.
        self.service_name = pgservice.DEFAULT_SERVICE if service is None else service
        named = self.service_file(self.directory, filename)
        resolution = pgservice.resolve(named, self.service_name)
        if resolution.service is None:
            raise ServiceUnusable(
                "postgres-service-unusable",
                service=self.service_name,
                searched=[str(one) for one in resolution.searched],
                reasons=[
                    {"code": refusal.code, "details": dict(refusal.details)}
                    for refusal in resolution.refusals
                ],
            )
        #: The entry this store connects with. Secrets reach the driver
        #: through it and reach nothing else; see :class:`outrage.pgservice.Service`.
        self.service = resolution.service
        #: The service file that was actually read. ``path`` on every other
        #: backend is the store; here it is the configuration naming it, which
        #: is the only thing about this store that is on this machine.
        self.path = self.service.path

        #: Whether a write keeps what it replaces. Read by the archive trigger
        #: through :data:`VERSIONING_SETTING`, which every connection declares.
        self.versioning = versioning

        # One connection per thread, opened on first use, and every one of
        # them remembered so that `close` can close the lot. psycopg lets a
        # connection be closed from another thread, which sqlite3 does not,
        # so this backend need not leave a connection to its thread's lifetime.
        self._local = threading.local()
        self._connections: list[Any] = []
        self._guard = threading.Lock()
        self._closed = False

        #: Why this build cannot operate at the version it found, on a
        #: ``report`` open that met one. An ordinary open raises instead.
        self.problem: Refusal | None = None
        #: What this build may do with what it found, or None where there is
        #: nothing to do it to.
        self.compatibility: Compatibility | None = None
        # Everything from here talks to the server, so everything from here
        # can fail with a connection already open. A constructor that raises
        # never returns the object, so nothing else would ever close it -- and
        # at this end that is a file handle, while at the far end it is a
        # backend process the server keeps until it notices. `close` is safe
        # to call on a half-built store: it holds the connection list and
        # nothing else this far in.
        try:
            #: What the database stores text as. Asked before anything else
            #: is, because a database that is not UTF8 is refused rather than
            #: converted -- see :meth:`_settle_encoding`.
            self.encoding = self._settle_encoding()
            #: The schema the tables are in, settled on the first connection.
            self.schema = self._settle_schema()
            # The documents table as every statement below names it: qualified
            # by the schema, quoted by psycopg, and with any `%` doubled,
            # because the name is written into statement text that is also
            # given parameters and a schema is free to be called anything.
            self._documents = (
                _psycopg()
                .sql.Identifier(self.schema, "documents")
                .as_string(self._conn)
                .replace("%", "%%")
            )
            #: The store's own three numbers, or None where the schema holds
            #: no store. Only a ``report`` open ever sees the second.
            self.stored: SchemaVersion | None = self._settle_stored(report=report)
            if self.stored is not None:
                try:
                    self.compatibility = compatibility(self.stored)
                except BackendError as exc:
                    if not report:
                        raise
                    self.problem = Refusal.of(exc)
        except BaseException:
            self.close()
            raise

    # -- where the store is ----------------------------------------------

    @staticmethod
    def service_file(
        directory: str | os.PathLike[str] | None,
        filename: str | os.PathLike[str] | None,
    ) -> Path | None:
        """The service file a mount names, or None for libpq's own lookup.

        **The one relaxation of the relative-only rule**, and it is this
        backend's to make because the file is not the store. Every other
        backend's file is a store inside the directory an operator named, so
        an absolute path there would make the directory a lie and a mount
        table unmovable. A service file is neither: the standard one is in the
        home directory, it is shared with ``psql`` and everything else that
        speaks libpq, and a copy of it inside ``--dir`` would be a second place
        for a password to live.

        So an absolute path, and a path opening with ``~``, are taken as
        written. Everything else is a name inside the store directory and
        earns every refusal :func:`outrage.store.store_file` makes -- a ``..``
        climbing out of it included, which is the half of that rule that was
        never about relocatability.
        """
        if filename is None:
            return None
        expanded = Path(filename).expanduser()
        if expanded.is_absolute():
            return expanded
        return store_file(resolve_directory(directory), filename)

    @classmethod
    def in_directory(
        cls,
        directory: str | os.PathLike[str] | None = None,
        *,
        filename: str | os.PathLike[str] | None = None,
        extensions: str | None = None,
        versioning: bool | None = None,
        lock: str | None = None,
        service: str | None = None,
        log: EventLog | None = None,
        mount_point: str | None = None,
    ) -> Self:
        """This backend's store, named by a service file and an entry in it.

        Overridden for one reason: :meth:`service_file` rather than the base's
        :func:`~outrage.store.store_file`, so that an absolute or ``~`` FILE
        reaches the constructor as itself. The refusals are the base's, in the
        base's words -- ``extensions`` and ``lock`` are a tree's options and
        are refused here as everywhere else -- and ``service`` is the one this
        backend is the reason for, so it is taken rather than refused.
        """
        if lock is not None:
            raise BackendError(
                "backend-takes-no-lock",
                backend=cls.backend_name,
                filename="" if filename is None else str(filename),
                lock=lock,
            )
        if extensions is not None:
            raise BackendError(
                "backend-takes-no-extensions",
                backend=cls.backend_name,
                filename="" if filename is None else str(filename),
                extensions=extensions,
            )
        return cls(
            directory,
            filename=filename,
            service=service,
            log=log,
            mount_point=mount_point,
            **({} if versioning is None else {"versioning": versioning}),
        )

    @classmethod
    def reporting(
        cls,
        directory: str | os.PathLike[str] | None = None,
        *,
        filename: str | os.PathLike[str] | None = None,
        service: str | None = None,
        log: EventLog | None = None,
    ) -> Self:
        """This store, opened to be asked about: ``report=True``, nothing else.

        The base refuses this, because for a store in a file on this machine
        there is no difference between asking about one and opening it. Here
        there is: an empty schema stays empty, and a version this build cannot
        operate at is recorded rather than raised.
        """
        return cls(directory, filename=filename, service=service, log=log, report=True)

    # -- the connection ---------------------------------------------------

    def _connect(self) -> Any:
        """A new connection, configured exactly like every other one.

        The parameters are the service entry's, unchanged: what
        :mod:`outrage.pgservice` produces *is* psycopg's keyword mapping, which
        is what lets the reader be checked against a real libpq without this
        module being involved.

        A connection that cannot be made is ``postgres-unreachable``, which is
        **not** a configuration error: an offline laptop should start with its
        other mounts working, and a server that is down is the case that
        judgement exists for.

        **The classification is coarser than it will be.** psycopg reports a
        rejected password and a database that does not exist as
        ``OperationalError`` too, and those are configuration mistakes rather
        than a server to wait for -- so they are currently tolerated where
        they should be fatal, and the error names the reason in full. Telling
        them apart means reading the SQLSTATE, which is where the rest of the
        tolerant-open classification is done.

        **In autocommit**, so that a read is a statement and nothing more.
        psycopg otherwise opens a transaction on a connection's first
        statement and holds it until told, which would leave every
        connection that has only read sitting idle in a transaction -- holding
        back the server's vacuum and a lock on every table it touched -- for as
        long as the store is open. A write asks for its transaction by name,
        in :meth:`_transaction`.
        """
        psycopg = _psycopg()
        try:
            conn = psycopg.connect(**dict(self.service.parameters), autocommit=True)
        except psycopg.OperationalError as exc:
            raise BackendError(
                "postgres-unreachable",
                service=self.service_name,
                path=str(self.path),
                reason=str(exc).strip(),
            ) from exc
        try:
            with conn.cursor() as cursor:
                # Declared on every connection rather than once per store:
                # the triggers that read them run in whatever session made the
                # write, and a connection opened later by another thread is a
                # session that would otherwise declare nothing.
                cursor.execute(
                    "SELECT set_config(%s, %s, false), set_config(%s, %s, false)",
                    (
                        CLIENT_VERSION_SETTING,
                        str(SCHEMA_VERSION),
                        VERSIONING_SETTING,
                        "on" if self.versioning else VERSIONING_OFF,
                    ),
                )
        except BaseException:
            conn.close()
            raise
        return conn

    @property
    def _conn(self) -> Any:
        """This thread's connection, opened on first use."""
        conn = getattr(self._local, "conn", None)
        if conn is not None and not conn.closed:
            return conn
        conn = self._connect()
        with self._guard:
            if self._closed:
                conn.close()
                raise BackendError(
                    "postgres-store-closed", service=self.service_name, path=str(self.path)
                )
            self._connections.append(conn)
        self._local.conn = conn
        return conn

    @contextmanager
    def _transaction(self, *, serializable: bool = False) -> Iterator[Any]:
        """A cursor inside a transaction, committed on success and rolled back on failure.

        The connection is in autocommit, so this is the only place a
        transaction is ever opened. The isolation level is named every time,
        so a transaction never inherits the last one's, and psycopg sends it
        with the ``BEGIN`` rather than as a statement of its own.

        ``READ COMMITTED`` unless asked: what opening a store does is under an
        advisory lock, and a lock is only worth waiting for if the statements
        after it see what its last holder committed. A serializable
        transaction's snapshot is taken by its first statement, which is the
        one that waits -- measured against PostgreSQL 18, not inferred. A write
        that wants the net goes through :meth:`_writing`, which also retries it.
        """
        isolation = _psycopg().IsolationLevel
        conn = self._conn
        conn.isolation_level = isolation.SERIALIZABLE if serializable else isolation.READ_COMMITTED
        with conn.transaction(), conn.cursor() as cursor:
            yield cursor

    def _writing(
        self,
        work: Callable[[Any], _T],
        *,
        key: str,
        action: str,
        serializable: bool = True,
    ) -> _T:
        """``work(cursor)`` in a write transaction, tried again if the server could not order it.

        **``SERIALIZABLE`` is the net under every write**: any read that
        decides a write inside ``work`` -- a delete's ``unchanged_since`` is one
        -- either sees a state no concurrent writer has changed, or the
        transaction fails with SQLSTATE 40001 and is run again from the start.
        ``work`` is therefore called once per attempt and must compute
        everything it writes from what it reads through the cursor it is
        given, not from a previous attempt.

        **A ``?`` allocation asks for ``READ COMMITTED`` instead**, because its
        guard needs every statement to see what was committed before it: a
        lock on the number, then a check that nothing is there yet
        (:meth:`_allocate`). Under one serializable snapshot the check would
        read the level as it was when the transaction began. Without any lock
        at all, the server's own conflict detection does keep the numbers
        apart, but by failing every allocator but one each time they meet:
        eight under one parent were measured needing up to twelve attempts
        each against a simulated remote server.

        A refusal from the write-floor trigger becomes the refusal
        :meth:`_writable` makes, from the numbers the server refused on --
        which also moves this object's own idea of the store, so the next
        write is refused here without asking.
        """
        psycopg = _psycopg()
        for attempt in range(1, WRITE_ATTEMPTS + 1):
            try:
                with self._transaction(serializable=serializable) as cursor:
                    return work(cursor)
            except psycopg.Error as exc:
                if exc.sqlstate == WRITE_FLOOR_SQLSTATE:
                    raise self._refused_at_the_server(exc, key=key, action=action) from exc
                if exc.sqlstate not in _RETRYABLE:
                    raise
                if attempt == WRITE_ATTEMPTS:
                    raise BackendError(
                        "postgres-write-contended",
                        key=key,
                        action=action,
                        attempts=WRITE_ATTEMPTS,
                        reason=str(exc).strip(),
                    ) from exc
                time.sleep(random.uniform(0, RETRY_PAUSE * 2 ** (attempt - 1)))  # noqa: S311
        raise AssertionError("unreachable")  # pragma: no cover

    def _refused_at_the_server(self, exc: Any, *, key: str, action: str) -> ReadOnlyStoreError:
        """The write-floor trigger's refusal, as the one :meth:`_writable` makes.

        The store's numbers changed under this open store -- somebody migrated
        it -- so they are taken from the refusal and remembered, exactly as
        :meth:`create_schema` moves them. Where the new numbers would refuse
        reading too, the store stops answering anything, in the words an open
        would have used.
        """
        facts = json.loads(exc.diag.message_detail)
        self.stored = SchemaVersion(
            int(facts["version"]), int(facts["read_floor"]), int(facts["write_floor"])
        )
        try:
            self.compatibility = compatibility(self.stored)
        except BackendError as refused:
            self.compatibility = None
            self.problem = Refusal.of(refused)
        return ReadOnlyStoreError(
            "postgres-below-write-floor",
            key=key,
            action=action,
            version=self.stored.version,
            write_floor=self.stored.write_floor,
            build=SCHEMA_VERSION,
        )

    def _all(self, statement: str, params: Sequence[object] = ()) -> list[tuple[Any, ...]]:
        """Every row one statement returns, outside any transaction.

        Through :meth:`_opened` first, like every operation, so that a store
        opened only to be asked about answers none of them.
        """
        self._opened()
        with self._conn.cursor() as cursor:
            cursor.execute(statement, list(params))
            return cursor.fetchall()

    def _one(self, statement: str, params: Sequence[object] = ()) -> tuple[Any, ...] | None:
        """The first row one statement returns, or None, as :meth:`_all` asks it."""
        self._opened()
        with self._conn.cursor() as cursor:
            cursor.execute(statement, list(params))
            return cursor.fetchone()

    def close(self) -> None:
        """Close every connection this store opened, from whichever thread asks.

        All of them, unlike the SQLite backend, which can only close its own:
        sqlite3 refuses to let one thread touch another's connection at all,
        and psycopg does not. A connection left open here is one the server
        holds a backend process for, which is a resource at the far end rather
        than a file handle at this one.

        Safe to call twice, and a store closed while another thread is part
        way through a call reports :data:`BackendError` rather than opening a
        replacement connection behind the caller's back.
        """
        with self._guard:
            self._closed = True
            connections, self._connections = self._connections, []
        for conn in connections:
            conn.close()
        self._local.conn = None

    # -- the schema and its version ---------------------------------------

    def _settle_encoding(self) -> str:
        """The database's encoding, refusing anything but UTF8.

        :meth:`outrage.store_sqlite.SqliteStore._utf8`'s guard, asked at the
        one moment a connection can answer it. Every byte-addressed read here
        slices ``convert_to(content, 'UTF8')`` on the server, and every offset
        this package hands out is a UTF-8 one; a database in another encoding
        would make each of those a conversion whose cost and whose rounding
        nobody asked for. Refusing is louder, and it is a refusal about the
        database rather than about anything a caller did -- so it is made once,
        on the way in, rather than on the first read that would have been wrong.
        """
        with self._transaction() as cursor:
            cursor.execute(
                "SELECT pg_encoding_to_char(encoding), current_database() "
                "FROM pg_database WHERE datname = current_database()"
            )
            encoding, database = cursor.fetchone()
        if str(encoding).upper() != "UTF8":
            raise BackendError(
                "postgres-encoding",
                service=self.service_name,
                database=str(database),
                encoding=str(encoding),
            )
        return str(encoding)

    def _settle_schema(self) -> str:
        """Which schema the tables *are* in, or would be in if there were any.

        **Not ``current_schema()`` alone**, and the reason is measured rather
        than reasoned: ``options=-csearch_path=notes`` against a database with
        no ``notes`` schema gives ``current_schema()`` of NULL and no error at
        all -- measured against PostgreSQL 18, not inferred. That is
        precisely the first open
        this backend is meant to handle, so asking the connection where it
        already is answers nothing exactly when the answer is needed.

        So: the current schema when there is one, which is the ordinary case
        and is what the search path already resolved; otherwise the first
        entry of the search path, which is what the connection *asked* for.
        ``$user`` there is expanded as Postgres expands it, to the session
        user, rather than taken as a schema name.
        """
        with self._transaction() as cursor:
            cursor.execute("SELECT current_schema(), current_schemas(false), current_user")
            current, _existing, user = cursor.fetchone()
            if current is not None:
                return str(current)
            cursor.execute("SHOW search_path")
            (path,) = cursor.fetchone()
            wanted = _first_schema(str(path), user=str(user))
            if wanted is None:
                raise BackendError(
                    "postgres-no-schema",
                    service=self.service_name,
                    path=str(self.path),
                    search_path=str(path),
                )
            return wanted

    def _settle_stored(self, *, report: bool) -> SchemaVersion | None:
        """Read the store's three numbers, creating the store when there are none.

        Under an advisory lock held for the transaction, so that two devices
        opening an empty schema at the same moment do not both create it.
        ``CREATE TABLE IF NOT EXISTS`` alone would not do: two sessions racing
        it can deadlock, and the row in :data:`SCHEMA_TABLE` is not guarded by
        it at all.

        First-open creation is the ``create`` command at ``F`` and nothing
        else -- see :meth:`create_schema` -- so the two cannot come to disagree
        about what a new store is.

        ``report`` returns None where there is nothing there, rather than
        creating it: a command asking about a schema should leave an empty one
        empty, and ``create`` has to find nothing before it may write. A store
        in that state answers no operation -- :meth:`_opened` is what every
        one of them goes through.
        """
        with self._transaction() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", (_lock_number(self.schema),))
            stored = self._read_version(cursor)
            if stored is not None:
                return stored
            if report:
                return None
            self._create(cursor, SCHEMA_VERSION)
            created = self._read_version(cursor)
            assert created is not None
            return created

    @property
    def has_store(self) -> bool:
        """Whether the schema this store connected to holds one yet."""
        return self.stored is not None

    def _opened(self) -> Compatibility:
        """The compatibility decision, or refuse a store that is not there.

        Every operation goes through this rather than reading
        :attr:`compatibility` directly, so that "opened to ask about it" and
        "opened to use it" cannot come apart: only :meth:`schema_state` and
        :meth:`create_schema` are meant to see the empty case.
        """
        if self.compatibility is None:
            if self.problem is not None:
                raise self.problem.as_error()
            raise BackendError(
                "postgres-no-store",
                service=self.service_name,
                schema=self.schema,
                path=str(self.path),
            )
        return self.compatibility

    def schema_state(self) -> SchemaState:
        """What this build makes of the store, for a report rather than a use.

        One value, so that ``outrage schema status`` and ``outrage check``
        answer from the same decision rather than each reaching it again --
        which is the way two reports of the same thing come to disagree.
        """
        return SchemaState(
            backend=type(self).backend_name,
            service=self.service_name,
            path=self.path,
            schema=self.schema,
            stored=self.stored,
            oldest=MIN_SCHEMA_VERSION,
            newest=SCHEMA_VERSION,
            operating=None if self.compatibility is None else self.compatibility.operating,
            writable=self.compatibility is not None and self.compatibility.writable,
            problem=self.problem
            or (self.compatibility.read_only_reason if self.compatibility else None),
        )

    def _read_version(self, cursor: Any) -> SchemaVersion | None:
        """The store's three numbers, or None where there is no store here yet.

        A schema with no :data:`SCHEMA_TABLE` and a table with no row are the
        same answer: nothing has been created. They are distinct states only
        for a creation interrupted between its two statements, which cannot
        happen -- both are in the transaction the advisory lock is held for.
        """
        # Asked of the catalogue with the schema and the table as *parameters*
        # rather than of `to_regclass`, which takes one string and parses it
        # as a qualified name: a schema whose name needs quoting -- a capital
        # letter is enough -- would then be looked for under a name nobody
        # created.
        cursor.execute(
            "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = %s AND c.relname = %s AND c.relkind = 'r'",
            (self.schema, SCHEMA_TABLE),
        )
        if cursor.fetchone() is None:
            return None
        cursor.execute(
            _sql(
                "SELECT version, read_floor, write_floor FROM {versions}",
                schema=self.schema,
            )
        )
        row = cursor.fetchone()
        return None if row is None else SchemaVersion(int(row[0]), int(row[1]), int(row[2]))

    def _create(self, cursor: Any, version: int) -> None:
        """Build a store at ``version``: the base schema, then the steps up to it.

        Never a script per version. One definition of each version means a
        creation exercises every migration on the way, which is the only thing
        that tests a migration as often as it tests a create.
        """
        if version not in VERSIONS:
            raise BackendError(
                "postgres-version-unsupported",
                version=version,
                oldest=MIN_SCHEMA_VERSION,
                newest=SCHEMA_VERSION,
            )
        psycopg = _psycopg()
        cursor.execute(
            psycopg.sql.SQL("CREATE SCHEMA IF NOT EXISTS {schema}").format(
                schema=psycopg.sql.Identifier(self.schema)
            )
        )
        for statement in (_TABLE, *_INDEXES, _ARCHIVE, _ARCHIVE_INDEX, _SCHEMA_TABLE):
            cursor.execute(_sql(statement, schema=self.schema))
        cursor.execute(_sql(_SCHEMA_TABLE_ONE_ROW, schema=self.schema))
        for name, body in _FUNCTIONS.items():
            # The body is a string literal to the server, so the names inside
            # it are quoted into it first and the whole is then quoted as a
            # literal -- never dollar-quoted, which a schema name could close.
            written = _sql(body, schema=self.schema).as_string(cursor.connection)
            cursor.execute(
                psycopg.sql.SQL(
                    "CREATE OR REPLACE FUNCTION {function}() RETURNS trigger "
                    "LANGUAGE plpgsql AS {body}"
                ).format(
                    function=psycopg.sql.Identifier(self.schema, name),
                    body=psycopg.sql.Literal(written),
                )
            )
        for statement in _TRIGGERS:
            cursor.execute(_sql(statement, schema=self.schema))
        for step in range(MIN_SCHEMA_VERSION + 1, version + 1):
            for statement in MIGRATIONS.get(step, ()):
                cursor.execute(_sql(statement, schema=self.schema))
        floors = VERSIONS[version]
        cursor.execute(
            _sql(
                "INSERT INTO {versions} (version, read_floor, write_floor) VALUES (%s, %s, %s)",
                schema=self.schema,
            ),
            (floors.version, floors.read_floor, floors.write_floor),
        )

    def create_schema(self, version: int | None = None) -> SchemaVersion:
        """Build a blank store at ``version``, refusing a schema that holds one.

        What ``outrage schema create`` reaches, and what a first open runs with
        ``version`` of None -- which is :data:`SCHEMA_VERSION`. A team whose
        oldest client knows version 3 gets a store that client can use by
        someone on a newer build naming 3 here.

        The version is checked **before** the schema is looked at, because it
        is a statement about the argument rather than about the store: a
        version this build never knew is the same mistake whether or not
        somebody else has already put a store where it was aimed, and
        reporting the occupied schema first would send the reader to clear a
        schema that was never going to be written.
        """
        wanted = SCHEMA_VERSION if version is None else version
        if wanted not in VERSIONS:
            raise BackendError(
                "postgres-version-unsupported",
                version=wanted,
                oldest=MIN_SCHEMA_VERSION,
                newest=SCHEMA_VERSION,
            )
        with self._transaction() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", (_lock_number(self.schema),))
            if self._read_version(cursor) is not None:
                raise BackendError(
                    "postgres-store-exists",
                    service=self.service_name,
                    schema=self.schema,
                    path=str(self.path),
                )
            self._create(cursor, wanted)
        # The store this object is connected to has just changed, so what this
        # object says about it has to change with it. Without this a create
        # followed by a report -- which is exactly what the command line does
        # -- would report the empty schema the open found.
        self.stored = VERSIONS[wanted]
        self.compatibility = compatibility(self.stored)
        self.problem = None
        return self.stored

    @property
    def stored_format_version(self) -> int:
        """The schema version recorded in the database this store opened.

        Read at open and remembered, unlike the SQLite backend's, which reads
        a pragma off a file it alone has: this one is a round trip, and the
        number cannot change under an open store because nothing but the
        migration command changes it and that takes the same advisory lock.
        """
        return self._opened().stored.version

    # -- writing -----------------------------------------------------------

    @_logged("store_document")
    def store_document(
        self,
        key: str,
        content: str,
        format: str | None = None,
        *,
        title: str | None = None,
        contents: str | None = None,
        encoding: str | None = None,
        updated_at: str | None = None,
    ) -> str:
        """The document and its supplied metadata, upserted in one transaction.

        The rows go in one ``executemany``, which psycopg sends as a pipeline:
        a document with a title and an index is one round trip, not three.
        Validated first, through the shared check, and then refused if this
        build may not write the store -- the argument is wrong whoever is
        asked, and the store is read only whatever the argument.

        **U+0000 is refused here and nowhere else yet.** A PostgreSQL
        ``text`` value cannot hold it, and escaping it would be a second
        encoding of every document for one character nobody writes on
        purpose. Every field holding one is named at once, so a caller fixes
        them in one pass. The other backends store it; refusing it in the
        shared check instead would close that difference for all of them.
        """
        parsed, content, format, title, contents, updated_at = self._validated(
            key,
            content,
            format,
            title=title,
            contents=contents,
            encoding=encoding,
            updated_at=updated_at,
        )
        holding = [
            name
            for name, value in (("content", content), ("title", title), ("contents", contents))
            if value is not None and _NUL in value
        ]
        if holding:
            raise InvalidArgumentError("postgres-nul-character", key=key, fields=holding)
        self._writable(key, "write")
        stamp = updated_at or _now()

        def meta_rows(target: keys.Key) -> list[tuple[object, ...]]:
            return [
                _row_values(
                    keys.parse(f"{target.key}{keys.DELIMITER}{keys.META_PREFIX}{name}"),
                    value,
                    "markdown",
                    stamp,
                )
                for name, value in (("title", title), ("contents", contents))
                if value is not None
            ]

        def write(cursor: Any) -> str:
            rows = [_row_values(parsed, content, format, stamp), *meta_rows(parsed)]
            cursor.executemany(
                f"INSERT INTO {self._documents} {_COLUMNS} "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
                f"ON CONFLICT (key) DO UPDATE SET {_UPSERTED}",
                rows,
            )
            return parsed.key

        if parsed.has_wildcard:
            return self._writing(
                lambda cursor: self._allocate(cursor, parsed, content, format, stamp, meta_rows),
                key=key,
                action="write",
                serializable=False,
            )
        return self._writing(write, key=key, action="write")

    def _allocate(
        self,
        cursor: Any,
        parsed: keys.Key,
        content: str,
        format: str | None,
        stamp: str,
        meta_rows: Callable[[keys.Key], list[tuple[object, ...]]],
    ) -> str:
        """Write ``parsed`` under the first number free among its parent's children.

        The SQLite backend's rule -- one past the highest number in use, over
        implicit children too, over the same level walk :meth:`list_keys`
        takes -- made safe for several devices by **locking the number rather
        than the parent**:

        1. The walk finds the candidate and tries its lock, in one statement.
        2. Holding the lock, the document is inserted only if **nothing is
           under that number yet** -- a second statement, so its snapshot is
           taken after the lock was. The metadata rides in the same
           statement, and is written only if the document was.
        3. A lock somebody holds, or a number somebody took, moves the
           candidate on by one and tries again, without waiting.

        Correct because a holder keeps its number's lock until it commits: any
        other allocator either finds the lock held, or -- in a statement
        begun after the release -- sees the committed row. The walk's own
        snapshot may be older, which only makes the first candidate one that
        step 2 turns down. ``c/?/doc`` and ``c/?/task`` are kept apart because
        what is checked is everything under ``c/5``, not the key; a plain
        ``ON CONFLICT`` on the key would let both have 5.

        ``ON CONFLICT DO NOTHING`` stays on as well, for a write naming the
        same key outright that has not committed yet: the insert waits for it
        and then passes the number over, rather than writing over it.

        A number whose holder rolls back is left unused, which the one
        allocator at a time the SQLite backend allows never does.
        """
        parent = parsed.wildcard_parent
        assert parent is not None
        space = _allocation_space(self.schema, parent)
        cut = 1 if parent == keys.ROOT else len(parent) + 2
        walk, params = self._walk(parent)
        cursor.execute(
            f"{walk}, candidate AS ("
            "SELECT coalesce(max(substr(child, %s)::numeric), 0) + 1 AS n FROM level "
            f"WHERE substr(child, %s) ~ {_NUMERIC_SQL}"
            f") SELECT n::text, {_TRY_NUMBER.format(number='n')} FROM candidate",
            [*params, cut, cut, space],
        )
        number, held = cursor.fetchone()
        while True:
            if held:
                numbered = keys.with_prefix(parent, number)
                target = keys.parse(keys.substitute_wildcard(parsed.key, number))
                below, bounds = _below("key", numbered)
                rows = [_row_values(target, content, format, stamp), *meta_rows(target)]
                claimed = (
                    f"WITH claimed AS (INSERT INTO {self._documents} {_COLUMNS} "
                    "SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s "
                    f"WHERE NOT EXISTS (SELECT 1 FROM {self._documents} "
                    f"WHERE key = %s OR {_native(below)}) "
                    "ON CONFLICT (key) DO NOTHING RETURNING key)"
                )
                values: list[object] = [*rows[0], numbered, *bounds]
                if len(rows) > 1:
                    claimed += (
                        f", meta AS (INSERT INTO {self._documents} {_COLUMNS} "
                        "SELECT * FROM (VALUES "
                        + ", ".join(["(%s, %s, %s, %s, %s, %s, %s, %s, %s)"] * (len(rows) - 1))
                        + ") AS row WHERE EXISTS (SELECT 1 FROM claimed) "
                        f"ON CONFLICT (key) DO UPDATE SET {_UPSERTED})"
                    )
                    values += [value for row in rows[1:] for value in row]
                cursor.execute(f"{claimed} SELECT key FROM claimed", values)
                if cursor.fetchone() is not None:
                    return target.key
            number = str(int(number) + 1)
            cursor.execute(f"SELECT {_TRY_NUMBER.format(number='%s')}", (space, number))
            (held,) = cursor.fetchone()

    @_logged("delete")
    def delete(
        self,
        key: str,
        recursive: bool = False,
        *,
        key_range: KeyRange = UNBOUNDED,
        unchanged_since: str | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        """One statement: ``DELETE ... RETURNING key``, or the ``SELECT`` it would run.

        The SQLite backend selects first and deletes by key, because its
        ``DELETE`` cannot say what it removed. Here it can, so the selection
        and the delete are the same predicate in one statement, and a dry run
        is that predicate read rather than acted on. The key's own row and its
        metadata unit are one unit whatever the key is, and ``recursive`` adds
        everything else below -- the SQLite backend's rule, from the same
        functions. Every row it takes is archived by the trigger.

        **``unchanged_since`` is checked inside the delete's transaction**, so
        on this backend it is atomic: the check reads through the same
        connection, and a write that lands between the check and the delete
        makes the serializable transaction fail and start again, check and
        all. A dry run checks it the ordinary way.
        """
        self._writable(key, "delete")

        def check() -> None:
            check_unchanged(
                self,
                key,
                unchanged_since,
                action="delete",
                subtree=recursive,
                key_range=key_range,
            )

        parsed = keys.parse(key)
        lo, hi = keys.meta_range(parsed.key)
        taken = ["key = %s", "(key >= %s AND key < %s)"]
        params: list[object] = [parsed.key, lo, hi]
        if recursive:
            below, bounds = _below("key", parsed.key)
            taken.append(_native(below))
            params += bounds
        clauses, bounds = _range_clauses(key_range)
        within = "".join(f" AND {_native(clause)}" for clause in clauses)
        where = f"({' OR '.join(taken)}){within}"

        if dry_run:
            check()
            rows = self._all(f"SELECT key FROM {self._documents} WHERE {where}", [*params, *bounds])
        else:

            def take(cursor: Any) -> list[tuple[Any, ...]]:
                check()
                cursor.execute(
                    f"DELETE FROM {self._documents} WHERE {where} RETURNING key",
                    [*params, *bounds],
                )
                return cursor.fetchall()

            rows = self._writing(take, key=key, action="delete")
        return sorted((row[0] for row in rows), key=keys.sort_form)

    def _writable(self, key: str, action: str) -> None:
        """Refuse a write to a store this build may read and not write.

        :class:`~outrage.store.ReadOnlyStoreError` rather than the mount's
        refusal, and the distinction is the usual one: no flag makes this call
        succeed. What makes it succeed is a newer outrage, which the sentence
        names.
        """
        decided = self._opened()
        if decided.writable:
            return
        raise ReadOnlyStoreError(
            "postgres-below-write-floor",
            key=key,
            action=action,
            version=decided.stored.version,
            write_floor=decided.stored.write_floor,
            build=SCHEMA_VERSION,
        )

    # -- aggregates ----------------------------------------------------------

    @_logged("descendant_count")
    def descendant_count(
        self, key: str, *, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False
    ) -> int:
        """A ``count(*)`` over the subtree, less the metadata unit a plain delete takes."""
        where, params = _below_unit(key, key_range, whole_subtree)
        row = self._one(f"SELECT count(*) FROM {self._documents} WHERE {where}", params)
        assert row is not None  # noqa: S101 - an aggregate always returns a row
        return int(row[0])

    @_logged("subtree_totals")
    def subtree_totals(
        self, key: str, *, key_range: KeyRange = UNBOUNDED, chars: bool = False
    ) -> SubtreeTotals:
        """Rows, documents and optionally characters below ``key``, in one aggregate.

        The characters are the stored ``chars`` column, so a sum reads no
        document -- but it stays behind the flag all the same, because a
        surface that is opt in on one backend and always on in another is two
        contracts wearing one name.
        """
        below, bounds = _below("key", keys.parse(key).key)
        clauses, params = _range_clauses(key_range)
        within = "".join(f" AND {_native(clause)}" for clause in clauses)
        row = self._one(
            "SELECT count(*), count(*) FILTER (WHERE meta_name IS NULL), "
            f"coalesce(sum(chars), 0) FROM {self._documents} WHERE {_native(below)}{within}",
            [*bounds, *params],
        )
        assert row is not None  # noqa: S101 - an aggregate always returns a row
        return SubtreeTotals(
            keys=int(row[0]), documents=int(row[1]), chars=int(row[2]) if chars else None
        )

    @_logged("latest_change")
    def latest_change(
        self, key: str, *, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False
    ) -> str | None:
        """The newest ``updated_at`` over exactly the rows :meth:`descendant_count` counts.

        A text ``max`` under ``COLLATE "C"``, which is what makes it the newest:
        every stamp is one spelling of UTC to the second, so bytewise order is
        time order, and a locale collation is under no obligation to agree.
        """
        where, params = _below_unit(key, key_range, whole_subtree)
        row = self._one(f"SELECT max(updated_at) FROM {self._documents} WHERE {where}", params)
        return None if row is None else row[0]

    def exists(self, key: str) -> bool:
        """One primary key lookup, selecting no content."""
        return (
            self._one(f"SELECT 1 FROM {self._documents} WHERE key = %s", [keys.parse(key).key])
            is not None
        )

    # -- reading by key ------------------------------------------------------

    def level_entry(self, key: str) -> Entry | None:
        """The key's own row if it has one, else whether anything lies below: one statement.

        The SQLite backend asks the two questions in turn. Here each is a
        round trip, and the second is an ``EXISTS`` on a range of the primary
        key, so it rides along with the first rather than following it.
        """
        parsed = keys.parse(key)
        if parsed.key == keys.ROOT:
            raise ValueError("the root is not a child of anything, so it has no listing entry")
        lo, hi = keys.subtree_range(parsed.key)
        row = self._one(
            "SELECT own.key, own.format, own.updated_at, own.chars, "
            f"EXISTS (SELECT 1 FROM {self._documents} WHERE key >= %s AND key < %s) "
            f"FROM (SELECT 1) AS one LEFT JOIN {self._documents} AS own ON own.key = %s",
            [lo, hi, parsed.key],
        )
        assert row is not None  # noqa: S101 - one row joined to at most one
        stored, format, updated_at, chars, beneath = row
        if stored is not None:
            return _entry(stored, format, updated_at, chars)
        return _implicit(parsed.key) if beneath else None

    @_logged("retrieve_document")
    def retrieve_document(
        self,
        key: str,
        *,
        offset: int = 0,
        byte_offset: int | None = None,
        line: int | None = None,
        lines: int | None = None,
        length: int | None = None,
        pattern: str | None = None,
        occurrence: int = 0,
        max_chars: int = DEFAULT_MAX_CHARS,
    ) -> Excerpt:
        """One lookup on the primary key, sliced by the shared slicing.

        A character read fetches the document, as the SQLite backend does:
        a character offset cannot be turned into a position in the stored
        text without counting up to it, and the whole value is detoasted on
        the server either way. A **byte** or **line** read does not -- see
        :meth:`_byte_read`.
        """
        parsed = keys.parse(key)
        if byte_offset is not None or line is not None:
            for _ in range(_REREADS):
                try:
                    return self._byte_read(
                        parsed.key,
                        key,
                        offset,
                        byte_offset,
                        line,
                        lines,
                        pattern,
                        occurrence,
                        length,
                        max_chars,
                    )
                except _Rewritten:
                    continue
            raise BackendError("postgres-document-unsettled", key=key, attempts=_REREADS)

        row = self._one(
            f"SELECT key, content, format, updated_at FROM {self._documents} WHERE key = %s",
            [parsed.key],
        )
        if row is None:
            self._not_found(key)
        check_read_position(
            key,
            offset=offset,
            byte_offset=byte_offset,
            line=line,
            lines=lines,
            pattern=pattern,
            occurrence=occurrence,
        )
        stored, content, format, updated_at = row
        start = offset
        if pattern is not None:
            start = _find_occurrence(content, pattern, occurrence, offset)
            if start is None:
                raise PatternNotFoundError(
                    "pattern-not-found",
                    key=key,
                    pattern=pattern,
                    occurrence=occurrence,
                    offset=offset,
                )
        return _excerpt(stored, content, format, updated_at, start, length, max_chars)

    def _not_found(self, key: str) -> None:
        """Raise the refusal for a key with no row: a container, or nothing at all.

        A key with descendants but no content of its own is a container rather
        than a mistake, and saying so turns a dead end into the next call.
        """
        beneath = self.descendant_count(key)
        if beneath:
            raise KeyNotFoundError("key-is-a-container", key=key, beneath=beneath)
        raise KeyNotFoundError("key-not-found", key=key)

    def _byte_read(
        self,
        stored_key: str,
        key: str,
        offset: int,
        byte_offset: int | None,
        line: int | None,
        lines: int | None,
        pattern: str | None,
        occurrence: int,
        length: int | None,
        max_chars: int,
    ) -> Excerpt:
        """The byte- and line-addressed half of :meth:`retrieve_document`, sliced on the server.

        There is no blob seek over a connection, so the window is cut out of
        ``convert_to(content, 'UTF8')`` by the server and only it crosses the
        network. The first statement finds the row, its lengths and its first
        :data:`READAHEAD` bytes from where the read starts; the shared slicing
        then reads through :class:`_ServerBytes`, which serves each window out
        of what it holds and fetches only what it does not. A pattern is a
        scan, so it fetches the rest of the document -- the one read here
        whose cost is the document's rather than the window's.

        **Each further window is checked to be of the same row version**, by
        its ``xmin``, and a document rewritten between two of them starts the
        read again rather than splicing two versions into one excerpt. A read
        served by its first statement never meets that: it is one snapshot.
        """
        start = 0 if byte_offset is None else max(0, byte_offset - 3)
        row = self._one(
            "SELECT key, format, updated_at, chars, bytes, xmin::text, "
            "substring(convert_to(content, 'UTF8') FROM %s FOR %s) "
            f"FROM {self._documents} WHERE key = %s",
            [start + 1, READAHEAD, stored_key],
        )
        if row is None:
            self._not_found(key)
        check_read_position(
            key,
            offset=offset,
            byte_offset=byte_offset,
            line=line,
            lines=lines,
            pattern=pattern,
            occurrence=occurrence,
        )
        stored, format, updated_at, chars, total_bytes, version, window = row
        read = _ServerBytes(self, stored, version, total_bytes, start, bytes(window))

        first = (
            byte_offset if byte_offset is not None else _line_byte_offset(read, total_bytes, line)
        )
        actual_line = line
        if pattern is not None:
            found = _find_byte_occurrence(read, total_bytes, pattern, occurrence, first)
            if found is None:
                raise PatternNotFoundError(
                    "pattern-not-found",
                    key=key,
                    pattern=pattern,
                    occurrence=occurrence,
                    offset=0,
                    byte_offset=byte_offset,
                    line=line,
                )
            if line is not None:
                actual_line = _line_at_byte(read, first, line, found)
            first = found

        if line is not None:
            return _line_excerpt(
                stored,
                format,
                updated_at,
                first,
                actual_line,
                lines,
                length,
                max_chars,
                read=read,
                total_bytes=total_bytes,
                total=chars,
            )
        return _byte_excerpt(
            stored,
            format,
            updated_at,
            first,
            length,
            max_chars,
            read=read,
            total_bytes=total_bytes,
            total=chars,
        )

    # -- reading a level -----------------------------------------------------

    @_logged("list_keys")
    def list_keys(
        self,
        key: str | None = None,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        descendant_counts: bool = False,
        descendant_chars: bool = False,
    ) -> Page[Entry]:
        """One level, its totals and one page of it, in a single statement.

        The SQLite backend's walk is a loop of short queries, each seeking past
        the child it has just named, and at a fraction of a millisecond a query
        that is the right trade. Across a network each is a round trip, so the
        walk is written as a recursive query instead -- :meth:`_walk` -- and
        the server takes every seek. The level it names is then counted, its
        characters summed from ``parent``, and the page cut past the cursor
        and joined to each stored child's row, all in the same statement.

        **The totals are over the whole level and unaffected by the cursor**,
        as everywhere: 20 keys of 22 is a listing and 20 of 40000 is a sample.
        The descendant flags stay opt in and cost one aggregate per child on
        the page, through :meth:`subtree_totals`.
        """
        parent = keys.parse(_scope(key)).key
        walk, params = self._walk(parent)
        bound = _cursor_bound(cursor)
        past = "" if bound is None else " WHERE position > %s"
        cap = "" if limit is None else " LIMIT %s"
        rows = self._all(
            f"{walk} SELECT counted.total, counted.chars, page.child, page.stored, "
            "own.format, own.updated_at, own.chars "
            "FROM (SELECT count(*) AS total, "
            f"(SELECT coalesce(sum(chars), 0) FROM {self._documents} "
            "WHERE parent = %s AND key <> %s) AS chars FROM level) AS counted "
            "LEFT JOIN LATERAL (SELECT child, position, stored FROM level"
            f"{past} ORDER BY position{cap}) AS page ON true "
            f"LEFT JOIN {self._documents} AS own ON page.stored AND own.key = page.child "
            "ORDER BY page.position",
            [
                *params,
                parent,
                parent,
                *([] if bound is None else [bound]),
                *([] if limit is None else [limit + 1]),
            ],
        )
        total, total_chars = int(rows[0][0]), int(rows[0][1])
        children = [row[2:] for row in rows if row[2] is not None]
        # One past the page is all it takes to know there is a next one.
        more = limit is not None and len(children) > limit
        page = children if limit is None else children[:limit]
        items = [
            _entry(child, format, updated_at, chars) if stored else _implicit(child)
            for child, stored, format, updated_at, chars in page
        ]
        items = _with_descendants(self, items, counts=descendant_counts, chars=descendant_chars)
        return Page(
            items=items,
            returned=len(items),
            total=total,
            total_chars=total_chars,
            next_cursor=items[-1].key if more and items else None,
        )

    def _walk(self, parent: str) -> tuple[str, list[object]]:
        """A ``WITH`` clause naming ``level``: each child of ``parent``, in order.

        ``level`` has a row per child -- its key as ``child``, its sort form
        as ``position``, and ``stored``, whether the child has a row of its
        own -- in no particular order; a reader orders by ``position``.

        **A loose index scan**, the standard way to make Postgres skip: the
        recursive half finds the first row past everything the previous child
        holds -- ``sort_subtree_end`` of it, computed in SQL from its sort
        form -- with one probe of the ``sort_key`` index each. So the walk
        costs one probe per child whatever lies beneath them, which is the
        property the SQLite backend's seek walk has, taken over by the server.

        The child is cut out of the first row of its subtree at the next
        delimiter, in the key and in its sort form alike: a segment holds
        neither delimiter, so both cuts land on the same segment. A child
        whose first row *is* the child is stored -- a key's own row sorts
        first in its subtree -- and one whose first row lies below it is
        implicit, which is the SQLite walk's test read off the same order.
        """
        start = keys.sort_form(parent)
        end = None if parent == keys.ROOT else keys.sort_subtree_end(parent)
        sort_cut = 0 if parent == keys.ROOT else len(start) + 1
        key_cut = 0 if parent == keys.ROOT else len(parent) + 1
        upper = "" if end is None else " AND sort_key < %s"
        uppers: list[object] = [] if end is None else [end]
        after = _chr(keys.sort_subtree_end("x")[-1])
        return (
            "WITH RECURSIVE walk (key, sort_key) AS ("
            f"(SELECT key, sort_key FROM {self._documents} WHERE sort_key > %s{upper} "
            "ORDER BY sort_key LIMIT 1) "
            "UNION ALL "
            "(SELECT step.key, step.sort_key FROM walk, LATERAL ("
            f"SELECT key, sort_key FROM {self._documents} "
            f"WHERE sort_key >= {_cut('walk.sort_key', sort_cut, _chr(_SORT_DELIMITER))} "
            f"|| {after}{upper} ORDER BY sort_key LIMIT 1) AS step)"
            "), level AS ("
            f"SELECT {_cut('key', key_cut, repr(keys.DELIMITER))} AS child, "
            f"{_cut('sort_key', sort_cut, _chr(_SORT_DELIMITER))} AS position, "
            f"key = {_cut('key', key_cut, repr(keys.DELIMITER))} AS stored FROM walk"
            ")"
        ), [start, *uppers, *uppers]

    # -- reading a selection -------------------------------------------------

    @_logged("get_documents")
    def get_documents(
        self,
        subtree: BoundedSubtree = EVERYTHING,
        *,
        key_range: KeyRange = UNBOUNDED,
        cursor: str | None = None,
        meta_name: str | Sequence[str] | None = None,
        max_chars: int = DEFAULT_BULK_MAX_CHARS,
        limit: int | None = None,
        max_total_chars: int | None = None,
    ) -> Page[Excerpt]:
        """The selection's totals from one aggregate, and a page read in batches.

        **Each document is cut to ``max_chars`` on the server**, so a page of
        long documents sends what the page returns rather than every document
        whole. What an excerpt reports beyond its text -- the totals and where
        to resume -- comes from the stored lengths; see :func:`_bulk_excerpt`.

        The page is read a batch at a time past the cursor, as the DuckDB
        backend reads one, so that ``limit`` and ``max_total_chars`` decide
        how much is fetched: a caller naming a limit gets one statement of
        ``limit + 1`` rows, which is exactly enough to know whether another
        page follows.
        """
        where, params = self._selection(subtree, key_range, meta_name=meta_name)
        total, total_chars = self._totals(where, params)

        items: list[Excerpt] = []
        spent = 0
        more = False
        rows = self._rows(
            "key, left(content, %s), format, updated_at, chars, bytes",
            [max_chars],
            where,
            params,
            after=_cursor_bound(cursor),
            batch=BATCH if limit is None else limit + 1,
        )
        for key, prefix, format, updated_at, chars, size in rows:
            if limit is not None and len(items) >= limit:
                more = True
                break
            expected = min(chars, max_chars)
            if items and max_total_chars is not None and spent + expected > max_total_chars:
                # Never on the first document, or a budget smaller than one
                # document returns an empty page with a cursor that does not
                # move, and the caller loops forever making no progress.
                more = True
                break
            excerpt = _bulk_excerpt(key, prefix, format, updated_at, chars, size, max_chars)
            items.append(excerpt)
            spent += excerpt.returned
        return Page(
            items=items,
            returned=len(items),
            total=total,
            total_chars=total_chars,
            next_cursor=items[-1].key if more and items else None,
        )

    @_logged("missing_meta_stats")
    def missing_meta_stats(
        self,
        subtree: BoundedSubtree = EVERYTHING,
        *,
        key_range: KeyRange = UNBOUNDED,
        window: KeyRange = UNBOUNDED,
        meta_name: str | Sequence[str] = "title",
        sample: int = 0,
        coverage: bool = False,
    ) -> MissingMeta:
        """Documents carrying none of ``meta_name``, over one survey window.

        The window is measured at the position the document's metadata
        *would* have taken, synthesised in SQL exactly as the SQLite backend
        does it -- see :meth:`outrage.store_sqlite.SqliteStore.missing_meta_stats`
        for why it is that position and not the document's own.
        """
        names = _names(meta_name)
        where, params = self._missing(subtree, key_range, names)
        suffix = min(keys.meta_sort_suffix(name) for name in names)
        root = min(keys.sort_form(keys.META_PREFIX + name) for name in names)
        position = "(CASE WHEN sort_key = '' THEN ? ELSE sort_key || ? END)"
        clauses, bounds = _range_clauses(window, position, [root, suffix])
        where += "".join(f" AND {_native(clause)}" for clause in clauses)
        params += bounds

        total, total_chars = self._totals(where, params)
        documents, carried = (
            self._selection_coverage(subtree, key_range, names) if coverage else (None, None)
        )
        found: list[str] = []
        if sample > 0 and total:
            found = [
                row[0]
                for row in self._all(
                    f"SELECT key FROM {self._documents} AS documents WHERE {where} "
                    "ORDER BY sort_key LIMIT %s",
                    [*params, sample],
                )
            ]
        return MissingMeta(
            total=total,
            total_chars=total_chars,
            sample=found,
            selection_documents=documents,
            selection_carried=carried,
        )

    @_logged("keys_missing_meta")
    def keys_missing_meta(
        self,
        subtree: BoundedSubtree = EVERYTHING,
        *,
        key_range: KeyRange = UNBOUNDED,
        cursor: str | None = None,
        meta_name: str | Sequence[str] = "title",
        limit: int | None = None,
    ) -> Page[str]:
        """The selection :meth:`missing_meta_stats` counts, a page at a time.

        Keys only, so a page is one statement of ``limit + 1`` rows beside the
        totals, as the SQLite backend reads it.
        """
        where, params = self._missing(subtree, key_range, _names(meta_name))
        total, total_chars = self._totals(where, params)
        page_params = list(params)
        statement = f"SELECT key FROM {self._documents} AS documents WHERE {where}"
        if cursor is not None:
            statement += " AND sort_key > %s"
            page_params.append(_cursor_bound(cursor))
        statement += " ORDER BY sort_key"
        if limit is not None:
            statement += " LIMIT %s"
            page_params.append(limit + 1)
        found = [row[0] for row in self._all(statement, page_params)]
        items = found if limit is None else found[:limit]
        more = limit is not None and len(found) > limit
        return Page(
            items=items,
            returned=len(items),
            total=total,
            total_chars=total_chars,
            next_cursor=items[-1] if more and items else None,
        )

    # -- selecting -----------------------------------------------------------

    def _selection(
        self,
        subtree: BoundedSubtree,
        key_range: KeyRange,
        *,
        meta_name: str | Sequence[str] | None,
    ) -> tuple[str, list[object]]:
        """The WHERE clause a subtree read is about, from the SQLite backend's own functions.

        The same three independent conditions -- inside ``subtree``, carrying
        the metadata asked for, inside ``key_range`` -- because what they
        compile to is dialect-neutral SQL but for the substring search, which
        :func:`~outrage.store_sqlite._meta_clauses` takes as ``strpos`` here.
        Two spellings of one selection are two chances to disagree.
        """
        where, params = _subtree_clauses(subtree)
        clauses, bounds = _meta_clauses(keys.parse(_scope(subtree.key)), meta_name, find="strpos")
        where += clauses
        params += bounds
        clauses, bounds = _range_clauses(key_range)
        where += clauses
        params += bounds
        return " AND ".join(_native(clause) for clause in where) if where else "true", params

    def _missing(
        self, subtree: BoundedSubtree, key_range: KeyRange, names: list[str]
    ) -> tuple[str, list[object]]:
        """The documents in the selection carrying none of ``names``.

        The SQLite backend's predicate: a ``NOT EXISTS`` correlated on the
        exact key a value would sit at, which is a primary key probe and the
        one form that stays right at every scope. The root spells its metadata
        without the leading delimiter, which is what the ``CASE`` is for.
        Statements using this name the outer table ``documents``.
        """
        where, params = self._selection(subtree, key_range, meta_name=None)
        at = ", ".join(
            "CASE WHEN documents.key = '' THEN %s ELSE documents.key || %s END" for _ in names
        )
        where += (
            f" AND NOT EXISTS (SELECT 1 FROM {self._documents} AS meta WHERE meta.key IN ({at}))"
        )
        suffixes = [
            value
            for name in names
            for value in (keys.META_PREFIX + name, keys.DELIMITER + keys.META_PREFIX + name)
        ]
        return where, params + suffixes

    def _selection_coverage(
        self, subtree: BoundedSubtree, key_range: KeyRange, names: list[str]
    ) -> tuple[int, dict[str, int]]:
        """Documents in the selection, and how many carry each name.

        Over the selection and never the window, and each name as the
        documents less those missing it, through :meth:`_missing` -- the
        SQLite backend's method and its reasons, which it gives in full.
        """
        where, params = self._selection(subtree, key_range, meta_name=None)
        documents, _ = self._totals(where, params)
        carried = {}
        for name in names:
            missing, bound = self._missing(subtree, key_range, [name])
            lacking, _ = self._totals(missing, bound)
            carried[name] = documents - lacking
        return documents, carried

    def _totals(self, where: str, params: Sequence[object]) -> tuple[int, int]:
        """How many rows the selection holds and how many characters, from the stored lengths."""
        row = self._one(
            f"SELECT count(*), coalesce(sum(chars), 0) FROM {self._documents} AS documents "
            f"WHERE {where}",
            params,
        )
        assert row is not None  # noqa: S101 - an aggregate always returns a row
        return int(row[0]), int(row[1])

    def _rows(
        self,
        columns: str,
        column_params: Sequence[object],
        where: str,
        params: Sequence[object],
        *,
        after: str | None,
        batch: int,
    ) -> Iterator[tuple[Any, ...]]:
        """The selection's rows in the store's order, read a batch at a time.

        Past ``after``, a cursor's sort position, and then past the last row
        of the previous batch. Each batch is its own statement, fetched whole,
        so nothing is held open between them and a caller that stops reading
        leaves nothing behind on the connection. ``sort_key`` is unique, so
        resuming past one is exact.
        """
        position = after
        while True:
            clause, bound = where, list(params)
            if position is not None:
                clause += " AND sort_key > %s"
                bound.append(position)
            fetched = self._all(
                f"SELECT {columns}, sort_key FROM {self._documents} AS documents "
                f"WHERE {clause} ORDER BY sort_key LIMIT %s",
                [*column_params, *bound, batch],
            )
            yield from (row[:-1] for row in fetched)
            if len(fetched) < batch:
                return
            position = fetched[-1][-1]
            batch = min(batch * 2, BATCH_CEILING)

    # -- maintenance ---------------------------------------------------------

    def audit_rows(self) -> Iterator[AuditRow]:
        """Every row, as written, a chunk at a time in key order.

        A chunk per statement rather than a server-side cursor, which would
        hold a transaction open for as long as the caller took to walk it --
        and a caller walking this may ask the store something else between two
        rows.
        """
        last: str | None = None
        while True:
            after = "" if last is None else " WHERE key > %s"
            rows = self._all(
                f"SELECT key, doc_key, meta_name, parent, chars FROM {self._documents}"
                f"{after} ORDER BY key LIMIT %s",
                [*([] if last is None else [last]), AUDIT_CHUNK],
            )
            for key, doc_key, meta_name, parent, chars in rows:
                yield AuditRow(
                    key=key, doc_key=doc_key, meta_name=meta_name, parent=parent, chars=chars
                )
            if len(rows) < AUDIT_CHUNK:
                return
            last = rows[-1][0]

    def check_file(self, report: Report) -> None:
        raise _unbuilt("check_file")

    def repair(self) -> list[Repaired]:
        raise _unbuilt("repair")


class _Rewritten(Exception):
    """A byte read found the document rewritten between two of its windows."""


class _ServerBytes:
    """The ``read(offset, size)`` the shared byte slicing takes, over a document on the server.

    Holds one window of the document's UTF-8 and serves every read inside it.
    A read outside it fetches :data:`READAHEAD` bytes from there, or what was
    asked if that is more -- and only from the row version the read began on,
    which the ``xmin`` it was handed names. Postgres writes a new row version
    for every update, so a different ``xmin`` is a different document, and the
    read starts again rather than returning an excerpt made of two.
    """

    def __init__(
        self,
        store: PostgresStore,
        key: str,
        version: str,
        total_bytes: int,
        start: int,
        window: bytes,
    ) -> None:
        self._store = store
        self._key = key
        self._version = version
        self._total = total_bytes
        self._start = start
        self._window = window

    def __call__(self, offset: int, size: int) -> bytes:
        end = min(offset + size, self._total)
        held = self._start + len(self._window)
        if not (self._start <= offset and end <= held):
            self._fetch(offset, max(size, READAHEAD))
        return self._window[offset - self._start : end - self._start]

    def _fetch(self, offset: int, size: int) -> None:
        row = self._store._one(
            "SELECT substring(convert_to(content, 'UTF8') FROM %s FOR %s) "
            f"FROM {self._store._documents} WHERE key = %s AND xmin::text = %s",
            [offset + 1, size, self._key, self._version],
        )
        if row is None:
            raise _Rewritten
        self._start, self._window = offset, bytes(row[0])


def _native(clause: str) -> str:
    """A clause written for SQLite's ``?`` placeholders, in psycopg's ``%s``.

    The clauses shared with the SQLite backend are this package's own SQL and
    carry no ``%`` and no literal ``?`` -- every key reaches them as a
    parameter -- so the swap is total. Asserted rather than assumed, because a
    literal of either would be silently rewritten into a placeholder.
    """
    assert "%" not in clause  # noqa: S101 - a guard on this module's own SQL
    return clause.replace("?", "%s")


def _below_unit(key: str, key_range: KeyRange, whole_subtree: bool) -> tuple[str, list[object]]:
    """The rows strictly below ``key``, less its metadata unit unless ``whole_subtree``.

    What :meth:`~PostgresStore.descendant_count` and
    :meth:`~PostgresStore.latest_change` both select, in one place so the two
    answer about the same rows.
    """
    parsed = keys.parse(key)
    below, bounds = _below("key", parsed.key)
    params: list[object] = list(bounds)
    where = _native(below)
    if not whole_subtree:
        lo, hi = keys.meta_range(parsed.key)
        where += " AND NOT (key >= %s AND key < %s)"
        params += [lo, hi]
    clauses, extra = _range_clauses(key_range)
    where += "".join(f" AND {_native(clause)}" for clause in clauses)
    return where, params + extra


#: The delimiter the sort form joins segments with. Read off the sort form
#: itself rather than named from :mod:`outrage.keys`' private constant, so
#: the walk cuts where the encoding actually puts it.
_SORT_DELIMITER = keys.sort_form("a/b")[2]
assert keys.sort_form("a/b") == keys.sort_form("a") + _SORT_DELIMITER + keys.sort_form("b")


def _chr(character: str) -> str:
    """A one-character SQL expression for ``character``, which may be a control character."""
    return f"chr({ord(character)})"


def _cut(column: str, prefix: int, delimiter: str) -> str:
    """SQL for ``column`` cut at the first ``delimiter`` after its first ``prefix`` characters.

    The whole value where there is none. Character positions on both sides:
    ``substr`` and ``strpos`` count characters in Postgres, as ``len`` does
    here, and the prefix is a length measured in Python.
    """
    rest = f"substr({column}, {prefix + 1})"
    return (
        f"(CASE WHEN strpos({rest}, {delimiter}) > 0 "
        f"THEN left({column}, {prefix} + strpos({rest}, {delimiter}) - 1) ELSE {column} END)"
    )


def _names(meta_name: str | Sequence[str]) -> list[str]:
    """One metadata name or several, as a list, refusing none."""
    names = [meta_name] if isinstance(meta_name, str) else list(meta_name)
    if not names:
        raise ValueError("meta_name must not be an empty sequence")
    return names


def _bulk_excerpt(
    key: str,
    prefix: str,
    format: str | None,
    updated_at: str,
    chars: int,
    size: int,
    max_chars: int,
) -> Excerpt:
    """A bulk read's excerpt from the document's first ``max_chars`` and its stored lengths.

    The shared :func:`~outrage.store._excerpt` over the prefix, which is the
    whole document whenever the document fits -- and then the excerpt *is*
    the one a full read gives. Where it does not fit, the prefix is exactly
    what the cap returns, and the four numbers that describe the rest are
    corrected from the stored lengths: the totals, and where to resume, which
    is the end of the prefix in either unit.
    """
    excerpt = _excerpt(key, prefix, format, updated_at, 0, None, max_chars)
    if chars <= max_chars:
        return excerpt
    return replace(
        excerpt,
        total=chars,
        total_bytes=size,
        next_offset=excerpt.returned,
        next_byte_offset=excerpt.total_bytes,
    )


def _entry(key: str, format: str | None, updated_at: str, chars: int) -> Entry:
    """A stored row as a listing entry."""
    return Entry(key=key, kind=entry_kind(key), size=chars, format=format, updated_at=updated_at)


def _implicit(key: str) -> Entry:
    """A key that holds nothing and has something beneath it, as a listing entry."""
    return Entry(key=key, kind="implicit", size=None, format=None, updated_at=None)


def _unbuilt(operation: str) -> NotImplementedError:
    """The placeholder every unported operation raises.

    ``NotImplementedError`` rather than an :class:`~outrage.errors.OutrageError`
    deliberately: this is not a failure a caller asked for and can act on, it
    is a call that should not have been reachable. The backend is out of
    ``_BACKENDS`` until the operations are there, so reaching one of these is a
    bug in outrage and a traceback is the right output for a bug.
    """
    return NotImplementedError(
        f"PostgresStore.{operation} is not built yet; the backend is left out "
        f"of the registry until every operation is, so nothing should reach this"
    )


def _sql(statement: str, *, schema: str) -> Any:
    """``statement`` with its table names qualified by ``schema``.

    The table names are this module's own constants and the schema is read
    from the server, so nothing a caller typed reaches here -- but it is
    composed through psycopg's own identifier quoting all the same, because a
    schema name is an identifier and quoting one by hand is how the next
    person to add a table gets it wrong.
    """
    psycopg = _psycopg()
    return psycopg.sql.SQL(statement).format(
        documents=psycopg.sql.Identifier(schema, "documents"),
        archive=psycopg.sql.Identifier(schema, ARCHIVE_TABLE),
        versions=psycopg.sql.Identifier(schema, SCHEMA_TABLE),
        archive_function=psycopg.sql.Identifier(schema, "outrage_archive"),
        write_floor_function=psycopg.sql.Identifier(schema, "outrage_write_floor"),
        client_version=psycopg.sql.Literal(CLIENT_VERSION_SETTING),
        versioning=psycopg.sql.Literal(VERSIONING_SETTING),
        off=psycopg.sql.Literal(VERSIONING_OFF),
        sqlstate=psycopg.sql.Literal(WRITE_FLOOR_SQLSTATE),
    )


def _first_schema(search_path: str, *, user: str) -> str | None:
    """The schema a connection asked for, from its search path.

    What a first open creates when nothing on the path exists yet. ``$user``
    is expanded the way Postgres expands it; an entry quoted by the server is
    unquoted, since ``SHOW search_path`` renders one that way and a schema
    called ``"$user"`` is not what anybody means by it.
    """
    for entry in search_path.split(","):
        name = entry.strip()
        if name.startswith('"') and name.endswith('"') and len(name) > 1:
            name = name[1:-1].replace('""', '"')
        if not name:
            continue
        return user if name == _USER_SCHEMA else name
    return None


__all__ = [
    "ARCHIVE_TABLE",
    "AUDIT_CHUNK",
    "BATCH",
    "BATCH_CEILING",
    "CLIENT_VERSION_SETTING",
    "DEFAULT_SERVICE_FILE",
    "MIGRATIONS",
    "MIN_SCHEMA_VERSION",
    "READAHEAD",
    "RETRY_PAUSE",
    "SCHEMA_TABLE",
    "SCHEMA_VERSION",
    "VERSIONING_OFF",
    "VERSIONING_SETTING",
    "VERSIONS",
    "WRITE_ATTEMPTS",
    "WRITE_FLOOR_SQLSTATE",
    "Compatibility",
    "PostgresStore",
    "ServiceUnusable",
    "compatibility",
]
