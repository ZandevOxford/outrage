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

## What is *not* here yet

Connecting, the schema, the version table and the compatibility rules are
here. The operations -- reading, writing, listing, the surveys -- are not, and
every one of them raises :class:`NotImplementedError` below rather than being
absent, so that the class can be opened and the parts that are built can be
exercised. The backend is deliberately left **out** of
``outrage.store._BACKENDS`` while that is true, so no mount spec can reach a
half-built store and no configuration can be written against one.
"""

from __future__ import annotations

import hashlib
import os
import threading
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from . import pgservice
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
    KeyRange,
    MissingMeta,
    Page,
    ReadOnlyStoreError,
    SchemaState,
    SchemaVersion,
    Store,
    SubtreeTotals,
    resolve_directory,
    store_file,
)

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
#: trigger rather than two statements, and that is step 6.
ARCHIVE_TABLE = "document_archive"

#: The setting a session declares itself with, read by the archive triggers so
#: that a build below ``write_floor`` is refused at the server rather than
#: trusted to have checked. A two-part name, which is how Postgres spells a
#: setting that is not one of its own.
CLIENT_VERSION_SETTING = "outrage.client_version"

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
    digest = hashlib.blake2b(_LOCK_NAMESPACE + schema.encode("utf-8"), digest_size=8).digest()
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
    #: Stated for the same reason from the other side. The archive table is in
    #: the schema from version 1, and what fills it is step 6.
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

        #: Whether a write keeps what it replaces.
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
        """
        psycopg = _psycopg()
        try:
            conn = psycopg.connect(**dict(self.service.parameters))
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
                # the triggers that read it run in whatever session made the
                # write, and a connection opened later by another thread is a
                # session that would otherwise declare nothing.
                cursor.execute(
                    "SELECT set_config(%s, %s, false)",
                    (CLIENT_VERSION_SETTING, str(SCHEMA_VERSION)),
                )
            conn.commit()
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
    def _transaction(self) -> Iterator[Any]:
        """A cursor inside a transaction, committed on success and rolled back on failure.

        psycopg opens a transaction on the first statement and holds it until
        it is told, so this is the only place either happens.
        """
        conn = self._conn
        try:
            with conn.cursor() as cursor:
                yield cursor
        except BaseException:
            conn.rollback()
            raise
        else:
            conn.commit()

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

    # -- everything below is steps 5 to 7 ---------------------------------

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
        """Refused while the store is below this build's write floor; unbuilt otherwise.

        Validation first, through the shared check, even though nothing here
        writes yet: what a key and a format are is settled for every backend in
        one place, and a backend that reached its own conclusion would be a
        second namespace. See :meth:`outrage.store.Store._validated`.
        """
        self._validated(
            key,
            content,
            format,
            title=title,
            contents=contents,
            encoding=encoding,
            updated_at=updated_at,
        )
        self._writable(key, "write")
        raise _unbuilt("store_document")

    def delete(
        self,
        key: str,
        recursive: bool = False,
        *,
        key_range: KeyRange = UNBOUNDED,
        unchanged_since: str | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        """Refused below the write floor; unbuilt otherwise."""
        self._writable(key, "delete")
        raise _unbuilt("delete")

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

    def descendant_count(self, key: str, *, key_range: KeyRange = UNBOUNDED) -> int:
        raise _unbuilt("descendant_count")

    def subtree_totals(
        self, subtree: BoundedSubtree = EVERYTHING, *, key_range: KeyRange = UNBOUNDED
    ) -> SubtreeTotals:
        raise _unbuilt("subtree_totals")

    def latest_change(
        self, subtree: BoundedSubtree = EVERYTHING, *, key_range: KeyRange = UNBOUNDED
    ) -> str | None:
        raise _unbuilt("latest_change")

    def exists(self, key: str) -> bool:
        raise _unbuilt("exists")

    def level_entry(self, key: str) -> Entry | None:
        raise _unbuilt("level_entry")

    def retrieve_document(
        self,
        key: str,
        *,
        offset: int = 0,
        max_chars: int = DEFAULT_MAX_CHARS,
        **rest: Any,
    ) -> Excerpt:
        raise _unbuilt("retrieve_document")

    def list_keys(self, key: str | None = None, **rest: Any) -> Page:
        raise _unbuilt("list_keys")

    def get_documents(
        self,
        subtree: BoundedSubtree = EVERYTHING,
        *,
        max_chars: int = DEFAULT_BULK_MAX_CHARS,
        **rest: Any,
    ) -> Page:
        raise _unbuilt("get_documents")

    def missing_meta_stats(self, subtree: BoundedSubtree = EVERYTHING, **rest: Any) -> MissingMeta:
        raise _unbuilt("missing_meta_stats")

    def keys_missing_meta(self, subtree: BoundedSubtree = EVERYTHING, **rest: Any) -> Page:
        raise _unbuilt("keys_missing_meta")

    def audit_rows(self) -> Iterator[AuditRow]:
        raise _unbuilt("audit_rows")

    def check_file(self, report: Report) -> None:
        raise _unbuilt("check_file")

    def repair(self) -> list[Repaired]:
        raise _unbuilt("repair")


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
    "CLIENT_VERSION_SETTING",
    "DEFAULT_SERVICE_FILE",
    "MIGRATIONS",
    "MIN_SCHEMA_VERSION",
    "SCHEMA_TABLE",
    "SCHEMA_VERSION",
    "VERSIONS",
    "Compatibility",
    "PostgresStore",
    "ServiceUnusable",
    "compatibility",
]
