"""The SQLite backend: one database file, one row per key.

The read-write implementation of :class:`outrage.store.Store`, and the one a store
is opened as when its file says nothing else. Everything specific to SQLite
lives here -- the schema and its
migrations, the connection handling, and the SQL that every read and write is
expressed as -- so that :mod:`outrage.store` says what a store *is* without saying
how this one is kept.

The split was not speculative tidiness, and :mod:`outrage.store_parquet` is the
evidence: the parts of this module that did not survive a second backend are
exactly the parts that are here -- a row-per-key table with secondary indexes,
``NOT EXISTS`` against a self-join, and a connection per thread -- while every
word of the vocabulary above was inherited unchanged. That vocabulary is keys,
ranges, subtrees, pages and excerpts, and it is backend independent because it
is about the namespace rather than about storage.

Read this one against :mod:`outrage.store_parquet` where the two answer the same
question differently. ``_range_clauses`` compiles a range to a predicate
because a row-per-key table evaluates one; the parquet backend bisects a sorted
file instead, and the two are written to be read side by side.

Nothing here is imported by a caller that only wants to read and write
documents: :func:`outrage.store.default_store` is what chooses this class, and it
is the one place in the package that names a backend.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

from . import keys
from .eventlog import EventLog
from .maintenance import CheckError, Problem, Repaired, Report
from .store import (
    DEFAULT_BULK_MAX_CHARS,
    DEFAULT_MAX_CHARS,
    EVERYTHING,
    UNBOUNDED,
    AuditRow,
    Backup,
    BackupError,
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
    _cursor_bound,
    _excerpt,
    _find_occurrence,
    _logged,
    _now,
    _position,
    _scope,
    check_unchanged,
    entry_kind,
)

#: What a SQLite store's file is called when a caller names none. The name a
#: parquet backend's default sits beside, each in its own module, neither
#: needing a qualifier to say which storage it is for. That a store *is* a file
#: inside a directory is not decided here -- see :func:`outrage.store.store_file`;
#: only what this backend calls one.
DEFAULT_STORE_FILE = "store.sqlite"

#: The schema this code writes, and the version a store is migrated up to when
#: it is opened. Every bump needs a migration that reads the version below it;
#: an older store is upgraded in place, and a newer one is refused rather than
#: read with the wrong shape assumed.
SCHEMA_VERSION = 6

_TABLE = """
CREATE TABLE IF NOT EXISTS {name} (
  key        TEXT PRIMARY KEY,
  doc_key    TEXT NOT NULL,
  meta_name  TEXT,
  meta_path  TEXT,
  parent     TEXT NOT NULL,
  content    TEXT NOT NULL,
  format     TEXT,
  updated_at TEXT NOT NULL,
  sort_key   TEXT NOT NULL
);
"""

_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_documents_parent ON documents(parent);
CREATE INDEX IF NOT EXISTS idx_documents_meta   ON documents(meta_name, meta_path, doc_key);
CREATE INDEX IF NOT EXISTS idx_documents_sort   ON documents(sort_key);
"""

_SCHEMA = _TABLE.format(name="documents") + _INDEXES

#: How long a writer waits for another writer to finish before giving up, in
#: milliseconds. SQLite's own default is zero -- a busy database fails on the
#: spot rather than waiting -- which is invisible with one connection and the
#: usual cause of spurious "database is locked" with several. Generous, because
#: every write here is small and the alternative to waiting is an error.
BUSY_TIMEOUT_MS = 5000

#: When the sidecar is worth reporting. A WAL always holds something between
#: checkpoints; it is only interesting once it holds more than the database it
#: belongs to, which is the state that makes a file copy lose real content.
WAL_RATIO = 1.0

#: The one problem ``repair`` acts on, named so that the test asserting a
#: repaired store stops reporting it does not have to spell it again.
WAL_UNCHECKPOINTED = "most of the store is in the write-ahead log"


class SqliteStore(FileStore):
    """A document store held in a single SQLite database."""

    default_filename = DEFAULT_STORE_FILE
    backend_name = "sqlite"
    format_version = SCHEMA_VERSION
    #: Stated rather than inherited. The default is True, so a backend that
    #: forgets reports itself writable -- which is the wrong way round for a
    #: mistake to fall, and `test_every_backend_states_whether_it_can_be_written`
    #: is why this is here rather than left to the base.
    writable = True

    def __init__(
        self,
        directory: str | os.PathLike[str] | None = None,
        *,
        filename: str | os.PathLike[str] | None = None,
        log: EventLog | None = None,
        mount_point: str | None = None,
    ) -> None:
        # Where the file is, and the directory around it, are the base's
        # business: they are the same question for every backend, and the
        # answer has to be settled before anything is opened.
        super().__init__(
            directory,
            filename=filename,
            log=log,
            mount_point=mount_point,
        )
        # One connection per thread, opened on first use. The server runs its
        # sync tool handlers in a worker pool, so a single shared connection
        # was being used from several threads at once -- which SQLite reported
        # as `bad parameter or other API misuse`, and, about a third of the
        # time, as an empty result set that raised nothing at all. See
        # `project/reference/planned/concurrency`.
        self._local = threading.local()
        # Migrating here, on the constructing thread, is what lets every later
        # connection assume the schema is already current: two threads can
        # never race to apply the same migration, because only this one ever
        # tries.
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        """A new connection, configured exactly like every other one.

        ``check_same_thread`` is left at its default. Turning it off is a
        promise to serialise access by hand, and nothing here does; leaving it
        on means a connection that escapes to another thread fails loudly
        rather than returning quiet nonsense.
        """
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        # WAL lets readers run alongside a writer, but writers still take
        # turns, and without this a second one is refused *immediately*: the
        # default busy timeout is zero. Waiting is what makes a concurrent
        # write look like it merely took a moment.
        conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        # Ordering stays defined in one place. The stored `sort_key` covers
        # every real row, but the implicit children of a level are derived from
        # the `parent` column and have no row of their own, so a query that has
        # to order or bound them needs the same padding SQLite cannot express.
        # Registered per connection, because that is the scope SQLite gives it.
        conn.create_function("sort_form", 1, keys.sort_form, deterministic=True)
        # The metadata split as seen from the key a read was scoped at, which
        # is not the stored one when that scope is itself inside a metadata
        # namespace. Only those reads use these: an ordinary scope sees the
        # same split the columns already hold, and keeps its index.
        conn.create_function("rel_meta_name", 2, _rel_meta_name, deterministic=True)
        conn.create_function("rel_meta_path", 2, _rel_meta_path, deterministic=True)
        return conn

    @property
    def _conn(self) -> sqlite3.Connection:
        """This thread's connection, opened on first use."""
        conn: sqlite3.Connection | None = getattr(self._local, "conn", None)
        if conn is None:
            conn = self._local.conn = self._connect()
        return conn

    def _migrate(self) -> None:
        with self._conn:
            version = self._conn.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise RuntimeError(
                    f"{self.path} was written by a newer version of outrage "
                    f"(schema {version}, this build understands {SCHEMA_VERSION})"
                )
            if version == 0:
                self._conn.executescript(_SCHEMA)
            else:
                if version < 2:
                    self._migrate_delimiter_to_slash()
                if version < 3:
                    self._migrate_add_sort_key()
                if version < 4:
                    self._migrate_meta_segment()
                if version < 5:
                    self._migrate_sort_form()
                if version < 6:
                    self._migrate_meta_namespace()
            if version != SCHEMA_VERSION:
                self._conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    def _migrate_delimiter_to_slash(self) -> None:
        """Schema 1 to 2: keys were period delimited.

        A segment could not contain ``.`` or ``/`` under the old grammar, and a
        metadata name could not contain ``.`` either, so every ``.`` in a
        schema 1 key was a delimiter and the rewrite is unambiguous.
        """
        self._conn.execute(
            """
            UPDATE documents SET
                key     = replace(key, '.', '/'),
                doc_key = replace(doc_key, '.', '/'),
                parent  = replace(parent, '.', '/')
            """
        )

    def _migrate_add_sort_key(self) -> None:
        """Schema 2 to 3: numeric segments gained a normal form and an order.

        Keys are rewritten, not just indexed, because stripping leading zeros
        changed what a key *is*: ``a/01`` and ``a/1`` used to name two
        documents and now name one. A store holding both is refused rather
        than half merged - there is no way to tell which content was meant to
        survive, and quietly keeping one is exactly the kind of success this
        project keeps failing to distinguish from a real one.

        The table is rebuilt rather than altered. ``ALTER TABLE ADD COLUMN``
        cannot add a ``NOT NULL`` column without a default, and that default
        then survives the migration: an older build, still running against the
        migrated file, would insert rows with an empty sort key and no error,
        which sort ahead of everything. Rebuilding leaves a migrated store with
        exactly the schema a fresh one has, so a write that forgets the sort
        key fails in both.
        """
        rows = self._conn.execute(
            "SELECT key, meta_name, content, format, updated_at FROM documents"
        ).fetchall()

        normalised: dict[str, str] = {}
        rebuilt = []
        for row in rows:
            was = row["key"]
            parsed = keys.parse(keys.migrate_legacy(was))
            clash = normalised.get(parsed.key)
            if clash is not None:
                raise RuntimeError(
                    f"{self.path} holds both {clash!r} and {was!r}, which are one key once "
                    f"leading zeros are stripped; remove or rename one, then reopen"
                )
            normalised[parsed.key] = was
            rebuilt.append(_row_values(parsed, row["content"], row["format"], row["updated_at"]))

        self._rebuild_table(rebuilt)

    def _rebuild_table(self, rebuilt: list[tuple[object, ...]]) -> None:
        """Replace ``documents`` with ``rebuilt``, in the schema this build writes.

        Statement by statement rather than executescript, which commits any
        pending transaction before it runs. The rebuild drops the live table,
        so it has to roll back as one thing if anything goes wrong.

        Shared by the two migrations that rebuild, so that a column added to
        ``_TABLE`` cannot reach one of them and not the other.
        """
        self._conn.execute(_TABLE.format(name="documents_rebuilt"))
        self._conn.executemany(
            "INSERT INTO documents_rebuilt (key, doc_key, meta_name, meta_path, parent, "
            "content, format, updated_at, sort_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rebuilt,
        )
        self._conn.execute("DROP TABLE documents")
        self._conn.execute("ALTER TABLE documents_rebuilt RENAME TO documents")
        for statement in filter(str.strip, _INDEXES.split(";")):
            self._conn.execute(statement)

    def _migrate_meta_segment(self) -> None:
        """Schema 3 to 4: metadata stopped being a suffix and became a segment.

        ``a/b:title`` becomes ``a/b/!title``, so ``/`` is the only separator in
        the namespace. Only ``key`` and ``sort_key`` change; ``doc_key``,
        ``meta_name`` and ``parent`` never included the suffix and are already
        right.

        No key can collide with the rewrite, because ``!`` was not a legal
        character before this schema, so nothing already stored can occupy the
        name a metadata row is moving to. Rewritten in place for that reason,
        rather than through the table rebuild schema 3 needed.

        The point of the change is ordering. ``:`` sorts above ``/``, so
        ``a:title`` sorted *after* ``a/x:title`` while ``a`` sorted *before*
        ``a/x`` -- a metadata survey walked its documents in a different order
        from a plain read, for every document that had a subtree. ``!`` sorts
        below every character a segment may begin with, so the two orderings
        are now one.
        """
        rewritten = f"doc_key || '{keys.DELIMITER}{keys.META_PREFIX}' || meta_name"
        self._conn.execute(
            f"UPDATE documents SET key = {rewritten}, sort_key = sort_form({rewritten}) "
            f"WHERE meta_name IS NOT NULL"
        )

    def _migrate_meta_namespace(self) -> None:
        """Schema 5 to 6: a metadata name became one segment, with a path below it.

        ``!`` opens a namespace now rather than swallowing everything after
        it, so ``a/!changelog/22`` is a document called ``22`` kept inside
        ``a``'s ``changelog`` rather than metadata called ``changelog/22``.
        No key changes; what changes is the two columns derived from one.

        Both are recomputed from ``key`` through :func:`outrage.keys.parse`
        rather than assuming ``meta_path`` starts out null everywhere. That is
        true of a store nobody wrote such a key to and is not true of the
        *format*, and a migration that reads its input is the one that stays
        right when it is handed a store that did.

        **The table is rebuilt rather than altered**, for the reason
        :meth:`_migrate_add_sort_key` gives: ``ALTER TABLE ADD COLUMN`` would
        leave the migrated file with a schema a fresh store does not have, and
        an older build writing to it would then insert a wrong ``meta_name``
        with no error at all.
        """
        rebuilt = [
            _row_values(keys.parse(row["key"]), row["content"], row["format"], row["updated_at"])
            for row in self._conn.execute(
                "SELECT key, content, format, updated_at FROM documents"
            ).fetchall()
        ]
        self._rebuild_table(rebuilt)

    def _migrate_sort_form(self) -> None:
        """Schema 4 to 5: the sort form gained segment markers and its own delimiter.

        No key changes -- only how keys order against each other -- so this
        rewrites the derived ``sort_key`` column and nothing else. ``sort_form``
        is registered on the connection, so SQLite can do it in one statement
        without the rows travelling through Python.

        Two orderings were wrong before, with two different causes. Metadata
        sorted among its document's subkeys rather than ahead of them, because
        that rested on ``!`` sorting below every character a segment could
        begin with, which stopped being true once segments could hold almost
        anything. And ``a-x/!title`` sorted before ``a/!title`` while ``a``
        sorted before ``a-x``, because ``-`` and ``.`` sort below the ``/``
        that joined the segments. Marking every segment fixes the first;
        joining with a delimiter below every legal segment character fixes the
        second. A metadata survey and a plain read now walk in one order rather
        than two that nearly agree.

        The markers cannot collide with content: all three sort below
        ``keys.MIN_SEGMENT_CHAR``, so no segment can contain one, and two keys
        therefore cannot share a sort form. That is load bearing -- pagination
        resumes with ``sort_key > ?`` over a non-unique index, so a collision
        would mean resuming past one row silently skipped the other.
        """
        self._conn.execute("UPDATE documents SET sort_key = sort_form(key)")

    @property
    def connection(self) -> sqlite3.Connection:
        """The open database, for asking questions about the file itself.

        **Nothing inside the package reaches through this any more.** It was
        exposed for :mod:`outrage.maintenance`, which asked SQLite about integrity
        and the write-ahead log from outside; those are now answered by
        :meth:`check_file` here, off ``_conn`` directly, because they are
        questions about *this* storage and have no meaning for any other.

        Kept public for a caller outside the package with a question about the
        database that no method answers, and because the tests ask them. It is
        not a way in: reaching through it to read or write documents defeats
        every guarantee the methods above make.
        """
        return self._conn

    def close(self) -> None:
        """Close this thread's connection.

        Only this thread's: SQLite refuses to let one thread touch another's
        connection at all, closing included, which is the same rule that makes
        the per-thread connections safe in the first place. The rest are
        released when their thread ends or the process exits -- the lifetime
        the one shared connection effectively had anyway.
        """
        conn: sqlite3.Connection | None = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

    # -- writing ---------------------------------------------------------

    @_logged("store_document")
    def store_document(
        self,
        key: str,
        content: str,
        format: str | None = None,
        *,
        title: str | None = None,
        encoding: str | None = None,
        updated_at: str | None = None,
    ) -> str:
        """One row per key, upserted, with the title written in the same
        transaction.

        The transaction is ``IMMEDIATE`` only when a ``?`` has to be allocated:
        that path reads the level before it writes, and a deferred transaction
        would let two callers read the same highest number and pick it twice.

        A caller's ``updated_at`` stamps the title row too. The pair is written
        as one thing and read back as one thing, and a title dated later than
        the document it titles would say an edit happened that did not.
        """
        # Inside the logged method, deliberately: `_logged` has already bound
        # the arguments the caller passed, which is what the log is for.
        parsed, content, format, title, updated_at = self._validated(
            key, content, format, title=title, encoding=encoding, updated_at=updated_at
        )

        # Allocating reads before it writes, so the whole thing has to be one
        # transaction that excludes other writers: a deferred transaction would
        # let two callers pick the same number.
        with self._transaction(immediate=parsed.has_wildcard):
            if parsed.has_wildcard:
                allocated = self._next_number(parsed.wildcard_parent)
                parsed = keys.parse(keys.substitute_wildcard(parsed.key, allocated))
            self._write(parsed, content, format, updated_at)
            if title is not None:
                title_key = f"{parsed.key}{keys.DELIMITER}{keys.META_PREFIX}title"
                self._write(keys.parse(title_key), title, "markdown", updated_at)
        return parsed.key

    def _write(
        self, parsed: keys.Key, content: str, format: str, updated_at: str | None = None
    ) -> None:
        """Insert or replace one row. Caller holds the transaction."""
        self._conn.execute(
            """
            INSERT INTO documents (key, doc_key, meta_name, meta_path, parent, content,
                                   format, updated_at, sort_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                content = excluded.content,
                format = excluded.format,
                updated_at = excluded.updated_at
            """,
            _row_values(parsed, content, format, updated_at or _now()),
        )

    @contextmanager
    def _transaction(self, immediate: bool = False) -> Iterator[None]:
        """Commit on success, roll back on failure.

        ``immediate`` takes the write lock up front, so reads made while
        deciding what to write cannot be overtaken by another writer.
        """
        if immediate:
            self._conn.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()

    def _next_number(self, parent: str) -> str:
        """A numeric segment not already in use among the children of ``parent``.

        One past the highest number in use rather than the lowest number free,
        so that deleting a key in the middle does not hand its number to
        something unrelated. Numbers are only unique, not permanently reserved:
        deleting the highest does free it again.
        """
        used = [int(name) for name in self._child_names(parent) if keys.NUMERIC_RE.match(name)]
        return str(max(used) + 1) if used else "1"

    def _child_names(self, parent: str) -> set[str]:
        """The final segments of the keys immediately below ``parent``.

        Covers implicit children too, so a number is not reused just because
        the key holding it has content only further down.
        """
        prefix_len = len(parent) + 1 if parent != keys.ROOT else 0
        # By the segment rather than by ``meta_name``, which says where the
        # *key* first turns to metadata and not whether this child does: every
        # row inside ``a/!changelog`` carries that name, and ``22`` there is an
        # ordinary child a number may be allocated beside.
        names = {
            name
            for row in self._conn.execute(
                f"SELECT key FROM documents WHERE {_children_clause()}",
                (parent, parent),
            )
            if not (name := row["key"][prefix_len:]).startswith(keys.META_PREFIX)
        }
        names.update(
            entry.key[prefix_len:]
            for entry in self._implicit_children(parent, bound=None, limit=None)
        )
        return names

    @_logged("delete")
    def delete(
        self,
        key: str,
        recursive: bool = False,
        *,
        key_range: KeyRange = UNBOUNDED,
        unchanged_since: str | None = None,
    ) -> list[str]:
        """The rows to remove are selected first, then deleted by key.

        Selected rather than deleted in one statement because the return value
        is the keys actually removed, and ``DELETE`` does not report them. The
        range bounds are appended to both halves of the selection -- the key's
        own row and, when recursive, the subtree beneath it.

        The watermark is checked over the same two halves before any of it
        goes, which is one aggregate query rather than a second selection.
        """
        check_unchanged(
            self,
            key,
            unchanged_since,
            action="delete",
            subtree=recursive,
            key_range=key_range,
        )
        parsed = keys.parse(key)
        bounds, params = _range_clauses(key_range)
        within = "".join(f" AND {clause}" for clause in bounds)

        # The key's own row and its whole metadata subtree: one unit, whatever
        # the key is. A document's metadata has no meaning once the document
        # is gone, and the same holds one level down for a metadata namespace's
        # own title. What ``recursive`` adds is everything else below.
        lo, hi = keys.meta_range(parsed.key)
        taken = ["key = ?", "(key >= ? AND key < ?)"]
        taken_params: list[object] = [parsed.key, lo, hi]
        if recursive:
            below, below_params = _below("key", parsed.key)
            taken.append(below)
            taken_params += below_params

        # ORed rather than queried in turn, so the metadata unit and the
        # subtree that contains it cannot report a key twice.
        targets = [
            row["key"]
            for row in self._conn.execute(
                f"SELECT key FROM documents WHERE ({' OR '.join(taken)}){within}",
                [*taken_params, *params],
            )
        ]

        with self._conn:
            self._conn.executemany("DELETE FROM documents WHERE key = ?", [(k,) for k in targets])
        return sorted(targets, key=keys.sort_form)

    @_logged("descendant_count")
    def descendant_count(
        self, key: str, *, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False
    ) -> int:
        """A ``count(*)`` over the subtree, less the metadata unit inside it.

        Two range scans, both on the primary key: everything below ``key``, and
        not the stretch a plain delete would take with it. That difference is
        what this reports, and it is why a document's own title has never
        counted here. See :func:`_below` and :func:`outrage.keys.meta_range`.

        ``whole_subtree`` **drops** the second scan rather than adding a third:
        the question is then the subtree itself, and one range scan is all of
        it.
        """
        parsed = keys.parse(key)
        below, bounds = _below("key", parsed.key)
        clauses, params = _range_clauses(key_range)
        within = "".join(f" AND {clause}" for clause in clauses)
        kept = ""
        unit: list[str] = []
        if not whole_subtree:
            lo, hi = keys.meta_range(parsed.key)
            kept = " AND NOT (key >= ? AND key < ?)"
            unit = [lo, hi]
        row = self._conn.execute(
            f"SELECT count(*) AS n FROM documents WHERE {below}{kept}{within}",
            [*bounds, *unit, *params],
        ).fetchone()
        return row["n"]

    @_logged("latest_change")
    def latest_change(
        self, key: str, *, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False
    ) -> str | None:
        """A ``max(updated_at)`` over the same bounds the count scans.

        :meth:`descendant_count`'s query with the aggregate changed and nothing
        else, deliberately: the two are one selection asked two questions, and
        a guard that measured a different set of keys from the count beside it
        would be answering about a subtree nobody named. ``max()`` over no rows
        is NULL, which is the None a caller reads as "nothing here to change".
        """
        parsed = keys.parse(key)
        below, bounds = _below("key", parsed.key)
        clauses, params = _range_clauses(key_range)
        within = "".join(f" AND {clause}" for clause in clauses)
        kept = ""
        unit: list[str] = []
        if not whole_subtree:
            lo, hi = keys.meta_range(parsed.key)
            kept = " AND NOT (key >= ? AND key < ?)"
            unit = [lo, hi]
        row = self._conn.execute(
            f"SELECT max(updated_at) AS newest FROM documents WHERE {below}{kept}{within}",
            [*bounds, *unit, *params],
        ).fetchone()
        return row["newest"]

    def exists(self, key: str) -> bool:
        """One indexed lookup on the primary key, selecting no content.

        On ``key`` rather than ``doc_key``, so a metadata key answers for
        itself, and returning a literal so a large document is not read to
        find out that it is there.
        """
        row = self._conn.execute(
            "SELECT 1 FROM documents WHERE key = ?", (keys.parse(key).key,)
        ).fetchone()
        return row is not None

    # -- reading ---------------------------------------------------------

    def level_entry(self, key: str) -> Entry | None:
        """One lookup on ``key``, then a range scan for anything below it.

        The lookup is on the ``key`` column, which metadata is part of, rather
        than on ``doc_key``, which it is not: a key holding only metadata has
        no document and no descendants, and still appears in its parent's
        listing.
        """
        parsed = keys.parse(key)
        if parsed.key == keys.ROOT:
            raise ValueError("the root is not a child of anything, so it has no listing entry")

        row = self._conn.execute("SELECT * FROM documents WHERE key = ?", (parsed.key,)).fetchone()
        if row is not None:
            return _entry(row)

        lo, hi = keys.subtree_range(parsed.key)
        beneath = self._conn.execute(
            "SELECT 1 FROM documents WHERE key >= ? AND key < ? LIMIT 1", (lo, hi)
        ).fetchone()
        if beneath is None:
            return None
        return Entry(key=parsed.key, kind="implicit", size=None, format=None, updated_at=None)

    @_logged("retrieve_document")
    def retrieve_document(
        self,
        key: str,
        *,
        offset: int = 0,
        length: int | None = None,
        pattern: str | None = None,
        occurrence: int = 0,
        max_chars: int = DEFAULT_MAX_CHARS,
    ) -> Excerpt:
        """One lookup on the primary key, sliced in Python.

        The whole document is read and then cut, because a row is stored as one
        value and SQLite would have to read it either way; the cost the caps
        exist to avoid is the one on the way out, not the one off the disk.
        """
        row = self._conn.execute(
            "SELECT * FROM documents WHERE key = ?", (keys.parse(key).key,)
        ).fetchone()
        if row is None:
            # A key with descendants but no content of its own is a container,
            # not a mistake. Saying so turns a dead end into the next call.
            beneath = self.descendant_count(key)
            if beneath:
                raise KeyNotFoundError("key-is-a-container", key=key, beneath=beneath)
            raise KeyNotFoundError("key-not-found", key=key)

        content = row["content"]
        if offset < 0:
            raise ValueError("offset must not be negative")

        start = offset
        if pattern is not None:
            if not pattern:
                raise InvalidArgumentError("pattern-empty")
            if occurrence < 0:
                raise ValueError("occurrence must not be negative")
            start = _find_occurrence(content, pattern, occurrence, offset)
            if start is None:
                raise PatternNotFoundError(
                    "pattern-not-found",
                    key=key,
                    pattern=pattern,
                    occurrence=occurrence,
                    offset=offset,
                )

        return _excerpt(*_stored(row), start, length, max_chars)

    @_logged("list_keys")
    def list_keys(
        self,
        key: str | None = None,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> Page[Entry]:
        """Two queries, merged: the rows stored at this level, and the keys
        that exist only because something lies beneath them.

        Both halves are taken past the same cursor and merged before either is
        cut. Cutting them separately is what makes the two disagree about where
        the page ends: whichever half is denser near the cursor pushes the
        other's keys over the edge, and a cursor never looks back.
        """
        # The whole key, not its document part: a metadata namespace is a
        # level like any other and ``list_keys("a/!x")`` lists what is in it.
        parent = keys.parse(_scope(key)).key
        bound = _cursor_bound(cursor)

        # Both halves are taken past the same cursor and merged before either
        # is cut. Cutting them separately is what makes the two disagree about
        # where the page ends: whichever half is denser near the cursor pushes
        # the other's keys over the edge, and a cursor never looks back.
        candidates = self._real_children(parent, bound, limit) + self._implicit_children(
            parent, bound, limit
        )
        candidates.sort(key=lambda entry: keys.sort_form(entry.key))

        items = candidates if limit is None else candidates[:limit]
        more = limit is not None and len(candidates) > limit
        total, total_chars = self._level_totals(parent)
        return Page(
            items=items,
            returned=len(items),
            total=total,
            total_chars=total_chars,
            next_cursor=items[-1].key if more and items else None,
        )

    def _real_children(self, parent: str, bound: str | None, limit: int | None) -> list[Entry]:
        """The rows stored directly under ``parent``, in order, after ``bound``."""
        sql = f"SELECT * FROM documents WHERE {_children_clause()}"
        params: list[object] = [parent, parent]
        if bound is not None:
            sql += " AND sort_key > ?"
            params.append(bound)
        sql += " ORDER BY sort_key"
        if limit is not None:
            # One more than the page: enough to know another page exists,
            # without counting the level a second time to find out.
            sql += " LIMIT ?"
            params.append(limit + 1)

        return [_entry(row) for row in self._conn.execute(sql, params)]

    def _implicit_child_query(self, parent: str) -> tuple[str, dict[str, object]]:
        """A SELECT over the children of ``parent`` that hold no content.

        Every stored row names its own parent, so the distinct parents lying
        within the subtree, truncated back to one level down, are exactly the
        keys that exist implicitly. Keys that are stored in their own right are
        excluded here rather than after the fact, so this half and the real one
        are disjoint and a merge of the two cannot lose a key to a duplicate.
        """
        params: dict[str, object] = {"parent": parent}
        if parent == keys.ROOT:
            # Every row is within the root's subtree, so the only thing to
            # exclude is the top level itself: a row whose parent is the root
            # truncates to the root, which is not a child of anything. The
            # root's own row is excluded by the same test, for the same reason.
            within = "parent <> ''"
            params["plen"] = 0
        else:
            within = "parent >= :lo AND parent < :hi"
            params["lo"], params["hi"] = keys.subtree_range(parent)
            params["plen"] = len(parent) + 1

        children = _children_clause(":parent")
        return (
            f"""
            SELECT DISTINCT CASE
                     WHEN instr(substr(parent, :plen + 1), '/') > 0
                     THEN substr(parent, 1, :plen + instr(substr(parent, :plen + 1), '/') - 1)
                     ELSE parent
                   END AS child
              FROM documents
             WHERE {within}
               AND child NOT IN (SELECT key FROM documents WHERE {children})
            """,
            params,
        )

    def _implicit_children(self, parent: str, bound: str | None, limit: int | None) -> list[Entry]:
        inner, params = self._implicit_child_query(parent)
        sql = f"SELECT child FROM ({inner})"
        if bound is not None:
            sql += " WHERE sort_form(child) > :bound"
            params["bound"] = bound
        sql += " ORDER BY sort_form(child)"
        if limit is not None:
            sql += " LIMIT :limit"
            params["limit"] = limit + 1

        return [
            Entry(key=row["child"], kind="implicit", size=None, format=None, updated_at=None)
            for row in self._conn.execute(sql, params)
        ]

    def _level_totals(self, parent: str) -> tuple[int, int]:
        """How many keys the whole level holds, and how many characters.

        Asked of the level rather than of the page, and so unaffected by the
        cursor: what a caller cannot work out from a page is how much of the
        whole they are holding.
        """
        row = self._conn.execute(
            f"SELECT count(*) AS n, coalesce(sum(length(content)), 0) AS chars "
            f"FROM documents WHERE {_children_clause()}",
            (parent, parent),
        ).fetchone()
        inner, params = self._implicit_child_query(parent)
        implicit = self._conn.execute(f"SELECT count(*) AS n FROM ({inner})", params).fetchone()
        # Implicit keys hold no content of their own, so they add to the count
        # and nothing to the characters.
        return row["n"] + implicit["n"], row["chars"]

    def _selection(
        self,
        subtree: BoundedSubtree,
        key_range: KeyRange,
        *,
        meta_name: str | Sequence[str] | None,
    ) -> tuple[str, list[object]]:
        """The WHERE clause naming a subtree read, shared by every caller of one.

        One predicate, so that a survey, its count, and the list of what the
        survey could not see all agree about what was in range.

        The three parts are independent and are all required to hold: a row is
        in the selection when it is inside ``subtree``, carries the metadata
        asked for, **and** falls inside ``key_range``. A page cursor is not
        part of this, which is what keeps ``total`` describing the selection
        rather than the remainder of it.
        """
        where, params = _subtree_clauses(subtree)

        clauses, bounds = _meta_clauses(keys.parse(_scope(subtree.key)), meta_name)
        where += clauses
        params += bounds

        clauses, bounds = _range_clauses(key_range)
        where += clauses
        params += bounds

        return " AND ".join(where) if where else "1", params

    def _selection_totals(self, where: str, params: list[object]) -> tuple[int, int]:
        row = self._conn.execute(
            f"SELECT count(*) AS n, coalesce(sum(length(content)), 0) AS chars "
            f"FROM documents WHERE {where}",
            params,
        ).fetchone()
        return row["n"], row["chars"]

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
        """One selection, streamed and cut against the caps as it arrives.

        Streamed, not fetched: the caps are what make this answer bounded, and
        a query that materialises the subtree before applying them has already
        done the work the caps exist to avoid. The totals come from a separate
        ``count(*)`` over the same predicate, which is what keeps them
        describing the selection rather than the page.
        """
        where, params = self._selection(subtree, key_range, meta_name=meta_name)
        total, total_chars = self._selection_totals(where, params)

        sql = f"SELECT * FROM documents WHERE {where}"
        page_params = list(params)
        if cursor is not None:
            sql += " AND sort_key > ?"
            page_params.append(_cursor_bound(cursor))
        sql += " ORDER BY sort_key"

        items: list[Excerpt] = []
        spent = 0
        more = False
        # Streamed, not fetched: the caps are what make this answer bounded, and
        # a query that materialises the subtree before applying them has already
        # done the work the caps exist to avoid.
        for row in self._conn.execute(sql, page_params):
            if limit is not None and len(items) >= limit:
                more = True
                break
            expected = min(len(row["content"]), max_chars)
            if items and max_total_chars is not None and spent + expected > max_total_chars:
                # Never on the first document, or a budget smaller than one
                # document returns an empty page with a cursor that does not
                # move, and the caller loops forever making no progress.
                more = True
                break
            excerpt = _excerpt(*_stored(row), 0, None, max_chars)
            items.append(excerpt)
            spent += excerpt.returned

        return Page(
            items=items,
            returned=len(items),
            total=total,
            total_chars=total_chars,
            next_cursor=items[-1].key if more and items else None,
        )

    def _missing_selection(
        self,
        subtree: BoundedSubtree,
        key_range: KeyRange,
        *,
        meta_name: str | Sequence[str],
    ) -> tuple[str, list[object], list[str]]:
        """The WHERE clause naming documents carrying none of ``meta_name``.

        One NOT EXISTS over the same range predicate the survey itself uses, so
        the two agree about what was in range. Shared by the paged listing and
        the per-window stats, which must not be able to disagree either.

        It correlates on the **exact key** a value would sit at, which is the
        document's own key with ``/!name`` appended -- a primary key lookup,
        and the one form that stays right at every scope. Correlating on
        ``doc_key`` and ``meta_name`` would read the split as it is seen from
        the root, and inside a metadata namespace that is not the split the
        question is being asked at. The root spells its metadata without the
        leading delimiter, which is what the CASE is for.
        """
        names = [meta_name] if isinstance(meta_name, str) else list(meta_name)
        if not names:
            raise ValueError("meta_name must not be an empty sequence")

        where, params = self._selection(subtree, key_range, meta_name=None)
        at = ", ".join(
            "CASE WHEN documents.key = '' THEN ? ELSE documents.key || ? END" for _ in names
        )
        where += f" AND NOT EXISTS (SELECT 1 FROM documents AS meta WHERE meta.key IN ({at}))"
        suffixes = [
            value
            for name in names
            for value in (keys.META_PREFIX + name, keys.DELIMITER + keys.META_PREFIX + name)
        ]
        return where, params + suffixes, names

    @_logged("missing_meta_stats")
    def missing_meta_stats(
        self,
        subtree: BoundedSubtree = EVERYTHING,
        *,
        key_range: KeyRange = UNBOUNDED,
        window: KeyRange = UNBOUNDED,
        meta_name: str | Sequence[str] = "title",
        sample: int = 0,
    ) -> MissingMeta:
        """The window is measured at a synthesised ``sort_key``, in SQL.

        A document carrying none of the names has no row in the ordering the
        survey walks, so ``sort_key || suffix`` stands in for where its row
        *would* have sorted. Since schema 5 the two orderings genuinely agree:
        the sort form marks every segment and joins with a delimiter below
        every legal segment character, so ``sort_form(d + "/!name")`` is
        ``sort_form(d)`` plus a fixed suffix, and the map from document to
        metadata order preserves it. A survey's window therefore *is* an
        interval of document keys now, which schema 4 could not say --
        ``a-x/!title`` used to sort before ``a/!title`` while ``a`` sorted
        before ``a-x``.

        **That does not make it safe to bound this by document key**, and this
        still measures at the synthesised position deliberately. Exactly that
        simplification was made once before, on exactly this reasoning, and
        reintroduced a double count that review did not catch; see
        ``context/8`` and ``context/9`` in the outrage store.
        ``tests/test_store.py::test_survey_windows_tile_over_adversarial_keys``
        is the guard, and the synthesised position is correct under any
        ordering, which a document-key bound is not.

        The synthesised position is not sargable, so this scans the selection
        rather than seeking into the sort index. Measured at 20k documents it
        costs about 6% against a plain range, because the query is driven by
        ``idx_documents_meta`` on ``meta_name`` and neither bound could seek
        anyway. The window is one page wide, which is what keeps it affordable.
        """
        where, params, names = self._missing_selection(subtree, key_range, meta_name=meta_name)

        # Where the row would have sorted had the document carried the name.
        # Asked for several, a document would first have appeared at the
        # earliest of them.
        suffix = min(keys.meta_sort_suffix(n) for n in names)
        # The root is the one document whose metadata is not its sort form plus
        # a suffix: it contributes no segment, so `!title` is a *first* segment
        # rather than one joined onto a previous. Concatenating anyway would
        # still tile -- the map stays monotone, so nothing is double counted --
        # but it would file the root under a later window than the one its
        # title would really have sorted in.
        root = min(keys.sort_form(keys.META_PREFIX + n) for n in names)
        position = "(CASE WHEN sort_key = '' THEN ? ELSE sort_key || ? END)"

        clauses, bounds = _range_clauses(window, position, [root, suffix])
        for clause in clauses:
            where += f" AND {clause}"
        params += bounds

        total, total_chars = self._selection_totals(where, params)

        found: list[str] = []
        if sample > 0 and total:
            rows = self._conn.execute(
                f"SELECT key FROM documents WHERE {where} ORDER BY sort_key LIMIT ?",
                [*params, sample],
            )
            found = [row["key"] for row in rows]

        return MissingMeta(total=total, total_chars=total_chars, sample=found)

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
        """One query with a ``NOT EXISTS`` against the metadata rows.

        Over the same range predicate the survey itself uses, so the two agree
        about what was in range. It used to read every document in the subtree
        through :meth:`get_documents` and throw the content away.
        """
        where, params, _ = self._missing_selection(subtree, key_range, meta_name=meta_name)

        total, total_chars = self._selection_totals(where, params)

        sql = f"SELECT key FROM documents WHERE {where}"
        page_params = list(params)
        if cursor is not None:
            sql += " AND sort_key > ?"
            page_params.append(_cursor_bound(cursor))
        sql += " ORDER BY sort_key"
        if limit is not None:
            sql += " LIMIT ?"
            page_params.append(limit + 1)

        found = [row["key"] for row in self._conn.execute(sql, page_params)]
        items = found if limit is None else found[:limit]
        more = limit is not None and len(found) > limit
        return Page(
            items=items,
            returned=len(items),
            total=total,
            total_chars=total_chars,
            next_cursor=items[-1] if more and items else None,
        )

    # -- maintenance -----------------------------------------------------

    @_logged("backup")
    def backup(
        self,
        destination: str | os.PathLike[str] | None = None,
        *,
        overwrite: bool = False,
    ) -> Backup:
        """Through SQLite's own backup API, because the file alone is not the
        store.

        Almost everything written since the last checkpoint is in the ``-wal``
        sidecar rather than the ``.sqlite`` file - 4 KB of database against
        2 MB of WAL, observed on 2026-08-17 - so copying the file yields a
        near-empty database that opens cleanly and passes an integrity check.
        That is a failure indistinguishable from success, which is the one kind
        worth paying for in the library, and it is why this is the backend's
        job rather than a caller's.
        """
        target = self.backup_path(destination, overwrite=overwrite)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Remove rather than write over: whatever is there need not be a
        # database at all, and SQLite refuses to open what it did not write.
        target.unlink(missing_ok=True)

        copy = sqlite3.connect(target)
        try:
            with copy:
                self._conn.backup(copy)
        except sqlite3.Error as exc:
            copy.close()
            target.unlink(missing_ok=True)
            raise BackupError("backup-unwritable", target=str(target), reason=str(exc)) from exc
        copy.close()

        return self._verify_backup(target)

    def _verify_backup(self, target: Path) -> Backup:
        """Check the copy is sound and complete, since a bad one still opens.

        The row count is compared after the copy rather than before it, so a
        concurrent write from another process can make a good backup look
        short. That is deliberate: this fails loudly and is cheap to re-run,
        whereas the alternative is trusting a count nobody checked.
        """
        expected = self._conn.execute("SELECT count(*) FROM documents").fetchone()[0]
        copy = sqlite3.connect(f"file:{target}?mode=ro", uri=True)
        try:
            integrity = copy.execute("PRAGMA integrity_check").fetchone()[0]
            documents = copy.execute("SELECT count(*) FROM documents").fetchone()[0]
            version = copy.execute("PRAGMA user_version").fetchone()[0]
        finally:
            copy.close()

        if integrity != "ok":
            raise BackupError("backup-corrupt", target=str(target), integrity=str(integrity))
        if version != SCHEMA_VERSION:
            raise BackupError(
                "backup-schema-mismatch",
                target=str(target),
                found=version,
                expected=SCHEMA_VERSION,
            )
        if documents != expected:
            raise BackupError(
                "backup-short", target=str(target), found=documents, expected=expected
            )
        return Backup(
            path=target,
            bytes=target.stat().st_size,
            documents=documents,
            integrity=integrity,
        )

    @property
    def stored_format_version(self) -> int:
        """SQLite keeps it in the header, as ``PRAGMA user_version``."""
        return int(self._conn.execute("PRAGMA user_version").fetchone()[0])

    def audit_rows(self) -> Iterator[AuditRow]:
        """Every row, in one query, streamed rather than fetched whole.

        ``LENGTH(content)`` rather than the content itself: a check counts
        characters and never reads a document, and a store worth checking is
        one it would be foolish to pull into memory to count.
        """
        for row in self._conn.execute(
            "SELECT key, doc_key, meta_name, parent, LENGTH(content) AS chars FROM documents"
        ):
            yield AuditRow(
                key=row["key"],
                doc_key=row["doc_key"],
                meta_name=row["meta_name"],
                parent=row["parent"],
                chars=row["chars"] or 0,
            )

    def check_file(self, report: Report) -> None:
        """What SQLite knows about the database and its sidecar.

        Both questions here are the stooutrage's and have no meaning above it:
        whether SQLite still considers its own pages sound, and how much of the
        store is in the write-ahead log rather than the database.
        """
        try:
            integrity = str(self._conn.execute("PRAGMA integrity_check").fetchone()[0])
        except sqlite3.DatabaseError as exc:
            raise CheckError("check-unreadable", path=str(self.path), reason=str(exc)) from exc

        report.details["integrity"] = integrity
        if integrity != "ok":
            report.problems.append(
                Problem("error", "SQLite reports the database as damaged", integrity)
            )

        self._check_wal(report)

    def _check_wal(self, report: Report) -> None:
        """Compare the database with its write-ahead log."""
        main_bytes, wal_bytes = self._sizes()
        report.details["database"] = f"{main_bytes} bytes"
        report.details["log"] = f"{wal_bytes} bytes"

        if main_bytes and wal_bytes > main_bytes * WAL_RATIO:
            wal = self._wal_path()
            report.problems.append(
                Problem(
                    "warning",
                    WAL_UNCHECKPOINTED,
                    f"{wal_bytes} bytes in {wal.name} against {main_bytes} in "
                    f"{self.path.name}. The store reads correctly, but anything copying the "
                    f"database file alone gets one missing those writes.",
                    repairable=True,
                )
            )

    def repair(self) -> list[Repaired]:
        """Fold the write-ahead log back and compact the database.

        Both steps are safe to run on a healthy store and safe to run twice.
        Sizes are measured either side rather than reported from the action's
        own return value, because the question being asked is what the file
        looks like now.
        """
        done = []

        before = self._sizes()
        self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        after = self._sizes()
        done.append(Repaired("checkpoint the write-ahead log", before[1], after[1]))

        # VACUUM cannot run inside a transaction, and sqlite3 opens one
        # implicitly for anything it thinks is a write. Committing first is
        # what lets it run.
        self._conn.commit()
        self._conn.execute("VACUUM")
        # VACUUM rewrites the whole database, and in WAL mode it writes through
        # the log like anything else. Without this second checkpoint the repair
        # ends holding a log the size of the file it just compacted, and the
        # check that runs afterwards reports the same warning it was called to
        # clear -- a repair that worked, reporting itself as a failure.
        self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        done.append(Repaired("compact the database", after[0], self._sizes()[0]))
        return done

    def _wal_path(self) -> Path:
        return self.path.with_name(self.path.name + "-wal")

    def _sizes(self) -> tuple[int, int]:
        """Bytes in the database and in its write-ahead log, in that order."""
        wal = self._wal_path()
        return (
            self.path.stat().st_size if self.path.exists() else 0,
            wal.stat().st_size if wal.exists() else 0,
        )


# -- turning the store's vocabulary into SQL --------------------------------
#
# A :class:`~outrage.store.KeyRange` and a :class:`~outrage.store.BoundedSubtree` say
# which stretch of the order and which part of the hierarchy a call is about.
# What they mean is the namespace's business and lives with them; what they
# compile to is this backend's, and lives here. A backend that answers a range
# by seeking row-group statistics rather than by evaluating a predicate has the
# same two types to read and nothing here to reuse.


def _range_clauses(
    key_range: KeyRange, column: str = "sort_key", column_params: Sequence[object] = ()
) -> tuple[list[str], list[object]]:
    """``key_range``'s bounds as SQL predicates on ``column``, with parameters.

    ``column`` is an expression, not only a column name, and ``column_params``
    are whatever it binds -- which is what lets a caller measure a range
    against something other than a row's own position.
    :meth:`SqliteStore.missing_meta_stats` measures one against where a
    document's metadata *would* have sorted, and that expression carries two
    parameters of its own; they are repeated ahead of each bound, in clause
    order, so a caller can concatenate both lists and keep them aligned.
    """
    clauses: list[str] = []
    params: list[object] = []
    for key, operator, position in (
        (key_range.after_inclusive, ">=", _position),
        (key_range.after, ">", _position),
        (key_range.after_subtree, ">=", keys.sort_subtree_end),
        (key_range.before, "<", _position),
        (key_range.before_inclusive, "<=", _position),
        (key_range.final_subtree, "<", keys.sort_subtree_end),
    ):
        if key is None:
            continue
        clauses.append(f"{column} {operator} ?")
        params += [*column_params, position(key)]
    return clauses, params


def _subtree_clauses(subtree: BoundedSubtree) -> tuple[list[str], list[object]]:
    """``subtree`` as SQL predicates on ``key`` and depth, with their parameters.

    On ``key`` rather than on ``sort_key``, which is where a
    :class:`~outrage.store.KeyRange` is measured: a key's metadata continues
    its own key, so one range predicate takes a key and its metadata subtree
    together, and it is the primary key besides.

    On ``key`` rather than on ``doc_key``, which it used to be, because a scope
    may now be a metadata namespace: every row inside ``a/!changelog`` has a
    ``doc_key`` of ``a``, so a range over that column cannot name the namespace
    at all. For a scope holding no ``!`` the two select exactly the same rows.

    **Depth stays measured on ``doc_key``**, because that is what depth counts:
    metadata adds none. So a depth filter reaches a key's whole metadata
    subtree, which is the cost ``planned/metadata`` accepted, and inside a
    metadata namespace it excludes nothing -- levels and depth are decoupled
    there, and a level walk is what descends.
    """
    clauses: list[str] = []
    params: list[object] = []

    # The root needs no predicate at all: everything is at or below it.
    # A clause that said so would still be evaluated per row.
    parsed = keys.parse(_scope(subtree.key))
    if parsed.key != keys.ROOT:
        below, bounds = _below("key", parsed.key)
        clauses.append(f"(key = ? OR {below})")
        params += [parsed.key, *bounds]

    if subtree.depth is not None:
        # A segment count SQLite can compute per row: the delimiters plus
        # one. In SQL rather than over the results, because a depth filter
        # applied afterwards has already paid to fetch what it discards.
        # The root has no segments and so breaks the formula -- delimiters
        # plus one makes it depth 1, and `depth=0` from the root would then
        # exclude the very document it names.
        clauses.append(
            "(CASE WHEN doc_key = '' THEN 0 ELSE "
            "length(doc_key) - length(replace(doc_key, '/', '')) + 1 END) - ? <= ?"
        )
        params += [keys.depth(_scope(subtree.key)), subtree.depth]

    return clauses, params


def _rel_meta_name(key: str, scope: str) -> str | None:
    """``key``'s metadata name as seen from ``scope``, for SQL to call per row.

    Registered on the connection rather than written out as an expression:
    what the split *is* belongs to ``keys``, and a second spelling of it in SQL
    is a second definition to keep right. Only a read scoped inside a metadata
    namespace reaches these, so the per row call is not on the common path.
    """
    return keys.relative(key, scope).meta_name


def _rel_meta_path(key: str, scope: str) -> str | None:
    """``key``'s metadata path as seen from ``scope``. See :func:`_rel_meta_name`."""
    return keys.relative(key, scope).meta_path


def _row_values(
    parsed: keys.Key, content: str, format: str | None, updated_at: str
) -> tuple[object, ...]:
    """One row's columns, in the order ``_TABLE`` declares them.

    One place, so that a write and the migrations that rebuild the table
    cannot disagree about what a column holds -- which is how ``meta_path``
    could have been added to the schema and left null by one of them.
    """
    return (
        parsed.key,
        parsed.doc_key,
        parsed.meta_name,
        parsed.meta_path,
        parsed.parent,
        content,
        format,
        updated_at,
        keys.sort_form(parsed.key),
    )


def _meta_clauses(
    scope: keys.Key, meta_name: str | Sequence[str] | None
) -> tuple[list[str], list[object]]:
    """ "Is this a document" and "is this the value of a name", at ``scope``.

    Both questions are asked *relative to the key the read was scoped at*, and
    the stored ``meta_name`` and ``meta_path`` answer them only when that scope
    holds no ``!``: they record where the **key** first turns to metadata,
    which from inside ``a/!changelog`` is a segment above the scope and not
    part of the question. Every row there carries ``changelog``, so the stored
    predicate would return nothing at all.

    So: the columns for an ordinary scope, which is every survey anyone runs
    and the one that keeps ``idx_documents_meta``; and the relative split,
    per row, for a scope that is itself metadata. **This is where the rule that
    a survey descends into a metadata namespace only when scoped inside one is
    implemented** -- from ``a``, ``a/!changelog/22`` carries a name and a path
    and so is neither a document nor a value.
    """
    names: list[str] | None = None
    if meta_name is not None:
        names = [meta_name] if isinstance(meta_name, str) else list(meta_name)
        if not names:
            raise ValueError("meta_name must not be an empty sequence")

    if not scope.is_metadata:
        if names is None:
            return ["meta_name IS NULL"], []
        return [
            f"meta_name IN ({', '.join('?' * len(names))})",
            "meta_path IS NULL",
        ], list(names)

    if names is None:
        return ["rel_meta_name(key, ?) IS NULL"], [scope.key]
    return [
        f"rel_meta_name(key, ?) IN ({', '.join('?' * len(names))})",
        "rel_meta_path(key, ?) IS NULL",
    ], [scope.key, *names, scope.key]


def _stored(row: sqlite3.Row) -> tuple[str, str, str | None, str]:
    """The four stored fields :func:`~outrage.store._excerpt` slices, from a row.

    Named apart from the slicing itself so that the policy stays above, shared,
    and only the shape of a row is this backend's business.
    """
    return row["key"], row["content"], row["format"], row["updated_at"]


def _entry(row: sqlite3.Row) -> Entry:
    """A stored row as a listing entry."""
    return Entry(
        key=row["key"],
        kind=entry_kind(row["key"]),
        size=len(row["content"]),
        format=row["format"],
        updated_at=row["updated_at"],
    )


def _children_clause(parent: str = "?") -> str:
    """SQL selecting the rows immediately below the key bound to ``parent``.

    ``key <> parent`` is what keeps the root out of its own listing. The root
    is its own parent -- as POSIX makes ``/..`` be ``/`` -- so a plain
    ``parent = ?`` would hand it back as a child of itself, and count it into
    the level's totals besides. For every other key the second test excludes
    nothing, since no other key is its own parent.

    One function because four queries ask this question, and four hand written
    clauses that must all remember the same exception is exactly the drift
    ``_check_parents`` exists to catch after the fact.
    """
    return f"parent = {parent} AND key <> {parent}"


def _below(column: str, doc_key: str) -> tuple[str, list[object]]:
    """SQL selecting the rows strictly beneath ``doc_key``, by ``column``.

    A range scan for an ordinary key, since everything under ``a`` starts with
    ``a/``. For the root it is a test against the root itself: everything else
    is beneath it, and no string bounds every key from above, so there is no
    range to scan. ``keys.subtree_range`` refuses to invent one rather than
    returning bounds that quietly match nothing.

    No predicate at all would be cheaper still, and ``_selection`` does that
    where it can. Here the clause has to exclude the root's own row, which a
    range does for free and an unbounded selection does not.
    """
    if doc_key == keys.ROOT:
        return f"{column} <> ?", [keys.ROOT]
    lo, hi = keys.subtree_range(doc_key)
    return f"({column} >= ? AND {column} < ?)", [lo, hi]


__all__ = [
    "BUSY_TIMEOUT_MS",
    "DEFAULT_STORE_FILE",
    "SCHEMA_VERSION",
    "WAL_RATIO",
    "WAL_UNCHECKPOINTED",
    "SqliteStore",
]
