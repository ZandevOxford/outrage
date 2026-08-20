"""SQLite backed document store.

Independent of MCP: everything here is callable and testable on its own. See
design.md for the key namespace, the tool semantics and the schema.
"""

from __future__ import annotations

import functools
import inspect
import json
import os
import sqlite3
import threading
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

from . import eventlog, keys
from .errors import RageError
from .eventlog import EventLog
from .keys import Key

#: Default directory name, relative to the working directory, when neither
#: --dir nor RAGE_DIR is given.
DEFAULT_DIR_NAME = ".rage"

DB_FILENAME = "store.sqlite"

#: How long a writer waits for another writer to finish before giving up, in
#: milliseconds. SQLite's own default is zero -- a busy database fails on the
#: spot rather than waiting -- which is invisible with one connection and the
#: usual cause of spurious "database is locked" with several. Generous, because
#: every write here is small and the alternative to waiting is an error.
BUSY_TIMEOUT_MS = 5000

#: Where backups go when no destination is given, relative to the store
#: directory, and how they are named within it.
BACKUP_DIR_NAME = "backups"
BACKUP_STAMP = "%Y%m%d-%H%M%S"

ENV_DIR = "RAGE_DIR"

#: Cap on a single retrieve, so one oversized document cannot flood an agent's
#: context window. The caller pages with the returned next_offset.
DEFAULT_MAX_CHARS = 8000

#: Per document cap when several are returned at once, which is usually a
#: listing rather than a read.
DEFAULT_BULK_MAX_CHARS = 2000

FORMATS = ("markdown", "json")

#: Encodings a caller may use for the content and title it passes in. These
#: describe the argument in transit, not the stored document, which is always
#: decoded back to plain text before it is written. See ``_decode``.
ENCODINGS = ("json-string",)

SCHEMA_VERSION = 5

_TABLE = """
CREATE TABLE IF NOT EXISTS {name} (
  key        TEXT PRIMARY KEY,
  doc_key    TEXT NOT NULL,
  meta_name  TEXT,
  parent     TEXT NOT NULL,
  content    TEXT NOT NULL,
  format     TEXT,
  updated_at TEXT NOT NULL,
  sort_key   TEXT NOT NULL
);
"""

_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_documents_parent ON documents(parent);
CREATE INDEX IF NOT EXISTS idx_documents_meta   ON documents(meta_name, doc_key);
CREATE INDEX IF NOT EXISTS idx_documents_sort   ON documents(sort_key);
"""

_SCHEMA = _TABLE.format(name="documents") + _INDEXES


class KeyNotFoundError(RageError, LookupError):
    """Raised when a key holds no content."""


class PatternNotFoundError(RageError, LookupError):
    """Raised when a search pattern does not occur in a document."""


class BackupError(RageError, RuntimeError):
    """Raised when a backup cannot be taken, or cannot be shown to be good."""


@dataclass(frozen=True, slots=True)
class Excerpt:
    """Some or all of one document's content."""

    key: str
    content: str
    format: str | None
    updated_at: str
    offset: int
    """Character offset within the document at which content starts."""
    returned: int
    """Number of characters returned."""
    total: int
    """Total length of the document."""
    next_offset: int | None
    """Where to resume, or None if this excerpt reached the end."""

    @property
    def truncated(self) -> bool:
        return self.next_offset is not None


@dataclass(frozen=True, slots=True)
class MissingMeta:
    """Documents one page of a metadata survey could not show, over its window.

    Stats about a window rather than a page of one, so there is no cursor:
    the window is already bounded at both ends by the page it describes, and a
    cursor here would name a position in a collection no argument resumes.
    """

    total: int
    """Documents in the window carrying none of the names asked for."""
    total_chars: int
    """Characters stored across those documents, which is the other half of
    what a caller needs to decide whether to go and look."""
    sample: list[str]
    """Up to a requested number of their keys. The count is exact; this is not."""


@dataclass(frozen=True, slots=True)
class Page[T]:
    """Some or all of a collection, and the size of the whole it came from.

    The collection axis member of the same family as ``Excerpt``, named to
    match it rather than inventing a second vocabulary. A partial answer that
    does not state the size of the whole is not actionable: 20 keys of 22 is a
    listing, 20 keys of 40000 is a sample, and a caller that cannot tell them
    apart treats them the same.
    """

    items: list[T]
    returned: int
    """Items in this page."""
    total: int
    """Items in the whole collection, which is what this page is part of."""
    total_chars: int
    """Characters stored across that whole collection. Named apart from
    ``total`` deliberately: 12000 documents beneath a key is a different
    prospect from 40 MB beneath it, and no caller should be able to read one
    number as the other."""
    next_cursor: str | None
    """Key to resume after, or None when the page reached the end."""

    @property
    def truncated(self) -> bool:
        return self.next_cursor is not None


@dataclass(frozen=True, slots=True)
class Backup:
    """A copy of the database, and the evidence that it is a real one."""

    path: Path
    bytes: int
    documents: int
    """Rows copied, checked against the source rather than assumed."""
    integrity: str
    """What SQLite's own integrity_check said. 'ok' when sound."""


@dataclass(frozen=True, slots=True)
class Entry:
    """One key immediately below some other key."""

    key: str
    kind: str
    """'document', 'metadata', or 'implicit' for a key that exists only because
    something beneath it does."""
    size: int | None
    format: str | None
    updated_at: str | None


@dataclass(frozen=True, slots=True)
class KeyRange:
    """A stretch of the key order, named by keys rather than by positions.

    Six one-sided bounds, all optional, all combined with AND, so any window
    the order supports can be described by one of these and nothing outside it
    describes a range at all. Three cut from below and three from above, and
    the three of each are the three places a cut can fall relative to a key:
    in front of its row, behind its row, and behind its whole subtree.

    ==================== ==========================================
    ``after_inclusive``  at that key or after it
    ``after``            strictly after that key, its subtree included
    ``after_subtree``    strictly after that key **and** everything below it
    ``before``           strictly before that key, and so before its subtree
    ``before_inclusive`` at that key or before it
    ``final_subtree``    no later than the end of that key's subtree
    ==================== ==========================================

    The distinction between ``after`` and ``after_subtree`` is the one worth
    holding on to. ``after`` is what a cursor means -- exclusive of the key it
    names and *inclusive of that key's children*, because the row after the
    last one emitted may well be its child. ``after_subtree`` is what stepping
    over a subtree means, and nothing else can say it. Together with ``before``
    it names a subtree from both sides, which is how a range excludes one:
    ``before=k`` ends the stretch in front of ``k`` and ``after_subtree=k``
    begins the stretch behind it, and neither has to name a key that exists.
    There is no key spelling "just past the last thing under ``k``".

    A range bounds the **selection**, so a count taken over one counts that
    range. That is what makes the ranges either side of an excluded subtree add
    up, and it is why a page cursor is a separate argument rather than an
    ``after`` set here: a page's totals have never depended on where the reader
    had got to.

    Nothing set means no bound at all, so ``KeyRange()`` is every key.
    """

    after: str | None = None
    after_inclusive: str | None = None
    after_subtree: str | None = None
    before: str | None = None
    before_inclusive: str | None = None
    final_subtree: str | None = None

    def clauses(
        self, column: str = "sort_key", column_params: Sequence[object] = ()
    ) -> tuple[list[str], list[object]]:
        """These bounds as SQL predicates on ``column``, with their parameters.

        ``column`` is an expression, not only a column name, and
        ``column_params`` are whatever it binds -- which is what lets a caller
        measure a range against something other than a row's own position.
        ``missing_meta_stats`` measures one against where a document's metadata
        *would* have sorted, and that expression carries two parameters of its
        own; they are repeated ahead of each bound, in clause order, so a
        caller can concatenate both lists and keep them aligned.
        """
        clauses: list[str] = []
        params: list[object] = []
        for key, operator, position in (
            (self.after_inclusive, ">=", _position),
            (self.after, ">", _position),
            (self.after_subtree, ">=", keys.sort_subtree_end),
            (self.before, "<", _position),
            (self.before_inclusive, "<=", _position),
            (self.final_subtree, "<", keys.sort_subtree_end),
        ):
            if key is None:
                continue
            clauses.append(f"{column} {operator} ?")
            params += [*column_params, position(key)]
        return clauses, params


@dataclass(frozen=True, slots=True)
class BoundedSubtree:
    """A key and how far below it to descend: what a subtree read is *about*.

    Deliberately not a :class:`KeyRange`, though a subtree is one. A range says
    where in the order to look and a subtree says which part of the hierarchy
    to read, and a caller gives **both** -- a key must be at or below ``key``,
    within ``depth`` of it, *and* inside whatever range was asked for. Folding
    the two together would make the pair inexpressible, and it is the pair that
    a traversal stepping over a mounted store needs.

    ``key`` of None is the root, which is every key. ``depth`` is counted in
    segments from ``key``, and None is unlimited.
    """

    key: str | None = None
    depth: int | None = None

    def __post_init__(self) -> None:
        if self.depth is not None and self.depth < 0:
            raise ValueError("depth must not be negative")

    def clauses(self) -> tuple[list[str], list[object]]:
        """This subtree as SQL predicates on ``doc_key``, with their parameters.

        On ``doc_key`` rather than on ``sort_key``, which is where a
        :class:`KeyRange` is measured: metadata shares its document's
        ``doc_key``, so one range predicate takes a document and its metadata
        together, and the depth of a metadata key is the depth of the document
        it belongs to.
        """
        clauses: list[str] = []
        params: list[object] = []

        # The root needs no predicate at all: everything is at or below it.
        # A clause that said so would still be evaluated per row, and against
        # `doc_key`, which carries no index of its own.
        parsed = keys.parse(_scope(self.key))
        if parsed.doc_key != keys.ROOT:
            below, bounds = _below("doc_key", parsed.doc_key)
            clauses.append(f"(doc_key = ? OR {below})")
            params += [parsed.doc_key, *bounds]

        if self.depth is not None:
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
            params += [keys.depth(_scope(self.key)), self.depth]

        return clauses, params


#: Every key, and every key at and below the root: the defaults for a call that
#: puts no bound of its own on what it reads.
EVERYTHING = BoundedSubtree()
UNBOUNDED = KeyRange()


def resolve_directory(explicit: str | os.PathLike[str] | None = None) -> Path:
    """Locate the store directory: explicit path, then RAGE_DIR, then ./.rage.

    A directory rather than a file, so that other files can live beside the
    database later.
    """
    if explicit is not None:
        return Path(explicit).expanduser()
    from_env = os.environ.get(ENV_DIR)
    if from_env:
        return Path(from_env).expanduser()
    return Path.cwd() / DEFAULT_DIR_NAME


_Method = TypeVar("_Method", bound=Callable[..., Any])


def _logged(op: str) -> Callable[[_Method], _Method]:
    """Record one event per call to the decorated method.

    A decorator rather than a block inside each method, for two reasons. The
    method bodies stay exactly as they were, so the diff that added logging
    cannot have changed behaviour; and the recording stays visibly separable
    from a store that is meant to be usable without it.

    The signature is read once, at decoration, so the only per-call cost when
    logging is on is binding the arguments — and none at all when it is off.
    """

    def decorate(method: _Method) -> _Method:
        signature = inspect.signature(method)

        @functools.wraps(method)
        def wrapper(self: Store, *args: Any, **kwargs: Any) -> Any:
            log = self._log
            if not log.enabled:
                return method(self, *args, **kwargs)

            bound = signature.bind(self, *args, **kwargs)
            bound.apply_defaults()
            # Everything but `self`, so the record names the arguments the
            # caller actually passed, defaults included.
            fields = log.arguments(dict(list(bound.arguments.items())[1:]))
            started = time.monotonic_ns()
            try:
                result = method(self, *args, **kwargs)
            except Exception as exc:
                log.emit(
                    "store",
                    op=op,
                    args=fields,
                    ms=_ms(started),
                    error={"type": type(exc).__name__, "message": str(exc)},
                )
                raise
            log.emit("store", op=op, args=fields, ms=_ms(started), result=_summarise(log, result))
            return result

        return wrapper  # type: ignore[return-value]

    return decorate


class Store:
    """A document store held in a single SQLite database."""

    def __init__(
        self,
        directory: str | os.PathLike[str] | None = None,
        *,
        log: EventLog | None = None,
    ) -> None:
        # A null log rather than None, so nothing below has to ask whether
        # logging is on before recording anything.
        self._log = log if log is not None else eventlog.NULL
        self.directory = resolve_directory(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / DB_FILENAME
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
                    f"{self.path} was written by a newer version of rage "
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
        than half merged — there is no way to tell which content was meant to
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
            rebuilt.append(
                (
                    parsed.key,
                    parsed.doc_key,
                    parsed.meta_name,
                    parsed.parent,
                    row["content"],
                    row["format"],
                    row["updated_at"],
                    keys.sort_form(parsed.key),
                )
            )

        # Statement by statement rather than executescript, which commits any
        # pending transaction before it runs. The rebuild drops the live table,
        # so it has to roll back as one thing if anything goes wrong.
        self._conn.execute(_TABLE.format(name="documents_rebuilt"))
        self._conn.executemany(
            "INSERT INTO documents_rebuilt (key, doc_key, meta_name, parent, content, "
            "format, updated_at, sort_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
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

        Exposed for :mod:`rage.maintenance`, which checks integrity, the schema
        version and the row invariants — none of which are questions about
        documents, so none of them belong on this class. Reaching through it to
        read or write documents defeats every guarantee the methods above make.
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

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

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
    ) -> str:
        """Store ``content`` at ``key``, overwriting anything already there.

        A ``?`` segment in ``key`` is replaced by a number unused among the
        children of the key enclosing it, so ``tmp/?`` writes to ``tmp/1`` in
        an empty store. Returns the key actually written, which is the only way
        the caller learns an allocated number.

        ``format`` defaults to 'json' when the content parses as a JSON object
        or array, and 'markdown' otherwise.

        ``title`` writes the ``!title`` metadata alongside the document in the
        same transaction. It saves a second call, but it exists mainly because
        the title is what makes a document discoverable later, and a separate
        call is one that can simply be forgotten. It may not be combined with a
        ``key`` that is itself metadata, since metadata does not nest.

        ``encoding`` describes how ``content`` and ``title`` arrived, not what
        is stored: 'json-string' means each is a JSON string literal, quotes
        and all, which is decoded before it is written. The stored document is
        plain text either way, so readers are unaffected. Its purpose is to
        make damage in transit loud — see ``_decode``.
        """
        parsed = keys.parse(key, allow_wildcard=True)
        if not isinstance(content, str):
            raise TypeError(f"content must be a string, got {type(content).__name__}")
        if encoding is not None:
            if encoding not in ENCODINGS:
                raise ValueError(f"encoding must be one of {ENCODINGS}, got {encoding!r}")
            content = _decode(content, encoding, "content")
            if title is not None:
                if not isinstance(title, str):
                    raise TypeError(f"title must be a string, got {type(title).__name__}")
                title = _decode(title, encoding, "title")
        if format is None:
            format = _detect_format(content)
        elif format not in FORMATS:
            raise ValueError(f"format must be one of {FORMATS}, got {format!r}")
        if title is not None:
            if parsed.is_metadata:
                raise ValueError(f"cannot attach a title to metadata key {key!r}")
            if not isinstance(title, str):
                raise TypeError(f"title must be a string, got {type(title).__name__}")

        # Allocating reads before it writes, so the whole thing has to be one
        # transaction that excludes other writers: a deferred transaction would
        # let two callers pick the same number.
        with self._transaction(immediate=parsed.has_wildcard):
            if parsed.has_wildcard:
                allocated = self._next_number(parsed.wildcard_parent)
                parsed = keys.parse(keys.substitute_wildcard(parsed.key, allocated))
            self._write(parsed, content, format)
            if title is not None:
                title_key = f"{parsed.key}{keys.DELIMITER}{keys.META_PREFIX}title"
                self._write(keys.parse(title_key), title, "markdown")
        return parsed.key

    def _write(self, parsed: keys.Key, content: str, format: str) -> None:
        """Insert or replace one row. Caller holds the transaction."""
        self._conn.execute(
            """
            INSERT INTO documents (key, doc_key, meta_name, parent, content, format,
                                   updated_at, sort_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                content = excluded.content,
                format = excluded.format,
                updated_at = excluded.updated_at
            """,
            (
                parsed.key,
                parsed.doc_key,
                parsed.meta_name,
                parsed.parent,
                content,
                format,
                _now(),
                keys.sort_form(parsed.key),
            ),
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
        names = {
            row["doc_key"][prefix_len:]
            for row in self._conn.execute(
                f"SELECT DISTINCT doc_key FROM documents "
                f"WHERE {_children_clause()} AND meta_name IS NULL",
                (parent, parent),
            )
        }
        names.update(
            entry.key[prefix_len:]
            for entry in self._implicit_children(parent, bound=None, limit=None)
        )
        return names

    @_logged("delete")
    def delete(self, key: str, recursive: bool = False) -> list[str]:
        """Delete ``key``, returning the keys actually removed.

        A document key takes its metadata with it. Descendants are removed only
        when ``recursive`` is set, so a mistyped key cannot silently discard a
        whole subtree. Note that storing an empty document is not a deletion.
        """
        parsed = keys.parse(key)
        if parsed.is_metadata:
            targets = [parsed.key]
        else:
            targets = [
                row["key"]
                for row in self._conn.execute(
                    "SELECT key FROM documents WHERE doc_key = ?", (parsed.doc_key,)
                )
            ]
            if recursive:
                below, bounds = _below("doc_key", parsed.doc_key)
                targets += [
                    row["key"]
                    for row in self._conn.execute(
                        f"SELECT key FROM documents WHERE {below}", bounds
                    )
                ]

        with self._conn:
            self._conn.executemany("DELETE FROM documents WHERE key = ?", [(k,) for k in targets])
        return sorted(targets, key=keys.sort_form)

    @_logged("descendant_count")
    def descendant_count(self, key: str) -> int:
        """How many stored rows lie strictly below ``key``.

        Exists so a caller can report what a non-recursive delete left behind:
        without it, deleting a key that holds nothing itself is indistinguishable
        from deleting a key that does not exist.
        """
        below, bounds = _below("doc_key", keys.parse(key).doc_key)
        row = self._conn.execute(
            f"SELECT count(*) AS n FROM documents WHERE {below}", bounds
        ).fetchone()
        return row["n"]

    def exists(self, key: str) -> bool:
        """Whether ``key`` itself holds a document.

        Not the same question as whether anything is below it: a bulk import
        asks this per file to decide about one key, and a container that holds
        nothing itself is free for a document to be written to.

        Deliberately cheaper than a read, since the answer is wanted for every
        file in an import and the content is not.
        """
        row = self._conn.execute(
            "SELECT 1 FROM documents WHERE key = ?", (keys.parse(key).key,)
        ).fetchone()
        return row is not None

    # -- reading ---------------------------------------------------------

    def level_entry(self, key: str) -> Entry | None:
        """How ``key`` appears in its parent's listing, or None if it does not.

        The same three answers :meth:`list_keys` gives about one key without
        listing the level to find it: a stored row, an implicit key that exists
        only because something lies beneath it, or nothing at all.

        Asked by a caller that has to reconcile this store's level with keys
        from somewhere else and must not count the same position twice. A
        cheaper pair of questions -- does the key exist, does it have
        descendants -- gets one corner wrong: metadata sits *at* a key rather
        than below it, so a key holding only metadata has no document and no
        descendants and still appears in the listing. This tests the ``key``
        column, which metadata is part of, rather than ``doc_key``, which it
        is not.
        """
        parsed = keys.parse(key)
        if parsed.key == keys.ROOT:
            raise ValueError("the root is not a child of anything, so it has no listing entry")

        row = self._conn.execute(
            "SELECT * FROM documents WHERE key = ?", (parsed.key,)
        ).fetchone()
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
        """Read the content stored at ``key``.

        ``pattern`` is a literal substring, not a regular expression; when
        given, the read starts at its ``occurrence``-th appearance at or after
        ``offset``. The result is capped at ``length`` or ``max_chars``,
        whichever is smaller, and carries a continuation offset.
        """
        row = self._conn.execute(
            "SELECT * FROM documents WHERE key = ?", (keys.parse(key).key,)
        ).fetchone()
        if row is None:
            # A key with descendants but no content of its own is a container,
            # not a mistake. Saying so turns a dead end into the next call.
            parsed = keys.parse(key)
            beneath = 0 if parsed.is_metadata else self.descendant_count(key)
            if beneath:
                raise KeyNotFoundError(
                    f"no content stored at {key!r}, but {beneath} key(s) lie beneath it; "
                    f"use list_keys or get_documents to see them"
                )
            raise KeyNotFoundError(f"nothing is stored at or below {key!r}")

        content = row["content"]
        if offset < 0:
            raise ValueError("offset must not be negative")

        start = offset
        if pattern is not None:
            if not pattern:
                raise ValueError("pattern must not be empty")
            if occurrence < 0:
                raise ValueError("occurrence must not be negative")
            start = _find_occurrence(content, pattern, occurrence, offset)
            if start is None:
                raise PatternNotFoundError(
                    f"{pattern!r} does not occur {occurrence + 1} time(s) in {key!r} "
                    f"at or after offset {offset}"
                )

        return _excerpt(row, start, length, max_chars)

    @_logged("list_keys")
    def list_keys(
        self,
        key: str | None = None,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> Page[Entry]:
        """List the keys immediately below ``key``, or below the root.

        Includes subkeys and metadata, and keys that exist only implicitly
        because something beneath them has content.

        ``limit`` and ``cursor`` page the level. Neither has a default: this
        layer offers pagination and holds no opinion about how much a caller
        can take, which is the tools' and the command line's question and they
        answer it differently.

        No :class:`KeyRange` here, deliberately. This reads one *level*, not a
        stretch of the order, and the cursor is the only bound a level has ever
        needed; a range would have to be threaded through three separate
        queries for no caller that exists.
        """
        parent = keys.parse(_scope(key)).doc_key
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
        where, params = subtree.clauses()

        if meta_name is None:
            where.append("meta_name IS NULL")
        else:
            names = [meta_name] if isinstance(meta_name, str) else list(meta_name)
            if not names:
                raise ValueError("meta_name must not be an empty sequence")
            where.append(f"meta_name IN ({', '.join('?' * len(names))})")
            params += names

        clauses, bounds = key_range.clauses()
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
        """Read everything ``subtree`` names, in key order.

        With ``meta_name`` the result holds those metadata entries instead of
        documents, which is how the titles of every document under a key are
        listed in one call.

        ``key_range`` narrows the subtree to a stretch of the order inside it,
        and the two hold together: a row is returned when it is in the subtree
        *and* in the range. It bounds the selection, so ``total`` and
        ``total_chars`` describe that stretch, and a caller reading one subtree
        as several ranges can add the answers up.

        ``cursor`` is not one of the bounds. It is where the last page stopped,
        it moves within the range as a caller pages, and it deliberately does
        not reach the totals: what a caller cannot work out from a page is how
        much of the whole they are holding.

        Two axes bound the answer and both are needed. ``max_chars`` caps each
        document, ``limit`` and ``cursor`` page the collection, and
        ``max_total_chars`` caps the page as a whole -- without that last one
        the two axes multiply, and a hundred documents at two thousand
        characters each honours both stated bounds while returning two hundred
        thousand characters.
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
            excerpt = _excerpt(row, 0, None, max_chars)
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
        """
        names = [meta_name] if isinstance(meta_name, str) else list(meta_name)
        if not names:
            raise ValueError("meta_name must not be an empty sequence")

        where, params = self._selection(subtree, key_range, meta_name=None)
        where += (
            f" AND NOT EXISTS (SELECT 1 FROM documents AS meta "
            f"WHERE meta.doc_key = documents.doc_key "
            f"AND meta.meta_name IN ({', '.join('?' * len(names))}))"
        )
        return where, params + list(names), names

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
        """What a metadata survey could not see, over exactly one page's window.

        **Two ranges, measured against two different things**, and a document
        has to satisfy both. ``key_range`` is measured against a document's own
        position, as everywhere else in the store. ``window`` is measured
        against the position its metadata *would* have taken, which is the
        order the survey walks, so this is where a survey's own cursors go --
        ``KeyRange(after=page_start, before_inclusive=page_end)`` is a page,
        exclusive below and inclusive above, each end left unset when the page
        ran to that end of the collection.

        The split is not a technicality. A document is inside a subtree that
        was stepped over because of where the *document* is, and is inside a
        page because of where its *title* would have sorted, and a survey
        reading one subtree in several ranges needs to say both at once.

        A document carrying none of the names has no row in the ordering the
        survey walks, so it has no position in it either. One is synthesised:
        where its row *would* have sorted had it carried the name, which is
        exactly ``sort_form(doc/!name)``.

        Since schema 5 the two orderings genuinely agree: the sort form marks
        every segment and joins with a delimiter below every legal segment
        character, so ``sort_form(d + "/!name")`` is ``sort_form(d)`` plus a
        fixed suffix and the map from document to metadata order preserves it.
        A survey's window therefore *is* an interval of document keys now,
        which schema 4 could not say -- ``a-x/!title`` used to sort before
        ``a/!title`` while ``a`` sorted before ``a-x``.

        **That does not make it safe to bound this by document key**, and this
        still measures at the synthesised position deliberately. Exactly that
        simplification was made once before, on exactly this reasoning, and
        reintroduced a double count that review did not catch; see
        ``context/8`` and ``context/9`` in the rage store.
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

        clauses, bounds = window.clauses(position, [root, suffix])
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
        """Document keys in ``subtree`` carrying none of ``meta_name``.

        A survey by ``!title`` only sees documents that have one, so on its own
        it silently under-reports the store. This names what the survey missed.

        One query with a NOT EXISTS, over the same range predicate the survey
        itself uses, so the two agree about what was in range. It used to read
        every document in the subtree through ``get_documents`` and throw the
        content away.

        ``key_range`` narrows the subtree exactly as it narrows a survey, and
        for the same reason: the two have to be askable over one stretch of the
        store or they stop describing the same one.
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
        """Copy the database to ``destination``, through SQLite, and verify it.

        Here rather than in a caller because taking a correct copy needs to know
        that this is a live WAL-mode database, which is this class's business
        and nobody else's. Almost everything written since the last checkpoint
        is in the ``-wal`` sidecar rather than the ``.sqlite`` file — 4 KB of
        database against 2 MB of WAL, observed on 2026-08-17 — so copying the
        file yields a near-empty database that opens cleanly and passes an
        integrity check. That is a failure indistinguishable from success, which
        is the one kind worth paying for in the library.

        ``destination`` may name a file or a directory, and defaults to a
        timestamped name under ``backups/`` in the store directory. Missing
        parents are created. An existing file is refused unless ``overwrite``.
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
            raise BackupError(f"could not write {target}: {exc}") from exc
        copy.close()

        return self._verify_backup(target)

    def backup_path(self, destination: str | os.PathLike[str] | None, *, overwrite: bool) -> Path:
        """Settle where the copy goes, and refuse the destinations that destroy.

        Public so that a caller can report the destination, and hit the same
        refusals, without writing anything — which is what ``--dry-run`` needs.
        """
        default_name = f"store-{time.strftime(BACKUP_STAMP)}.sqlite"
        if destination is None:
            target = self.directory / BACKUP_DIR_NAME / default_name
        else:
            target = Path(destination).expanduser()
            if target.is_dir():
                target = target / default_name

        target = target.resolve()
        if target == self.path.resolve():
            raise BackupError(f"{target} is the store itself, not a backup of it")
        if target.exists() and not overwrite:
            raise BackupError(f"{target} already exists; pass overwrite to replace it")
        return target

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
            raise BackupError(f"{target} failed its integrity check: {integrity}")
        if version != SCHEMA_VERSION:
            raise BackupError(
                f"{target} came out at schema {version}, but the store is at {SCHEMA_VERSION}"
            )
        if documents != expected:
            raise BackupError(
                f"{target} holds {documents} documents but the store holds {expected}; "
                "a concurrent write can cause this, so try again before suspecting the copy"
            )
        return Backup(
            path=target,
            bytes=target.stat().st_size,
            documents=documents,
            integrity=integrity,
        )


@contextmanager
def open_store(
    directory: str | os.PathLike[str] | None = None,
    *,
    log: EventLog | None = None,
) -> Iterator[Store]:
    """Open a store, closing it on exit."""
    store = Store(directory, log=log)
    try:
        yield store
    finally:
        store.close()


def read_all(store: Store, key: str, **kwargs: Any) -> Excerpt:
    """Read a whole document, following ``next_offset`` until there is no more.

    A function beside the store rather than a method on it, deliberately.
    Whether the *library* should stop handing out silent partial documents is
    an open design question — the options are weighed in
    ``project/reference/planned/agents`` and none has been chosen. This settles
    only what the command line does, which is a narrower question with an
    obvious answer: a person redirecting a document to a file wants the
    document, and a slice is available by asking for one.

    Asked for the whole document, the result reports it with ``next_offset`` of
    ``None``, so a caller cannot tell it apart from a document that fitted.
    That is the point. Asked for a ``length``, the result stops there and
    carries a continuation offset, exactly as a single capped read does.
    """
    first = store.retrieve_document(key, **kwargs)
    if first.next_offset is None:
        return first

    max_chars = kwargs.get("max_chars", DEFAULT_MAX_CHARS)
    wanted = kwargs.get("length")
    parts = [first.content]
    taken = first.returned
    offset = first.next_offset
    while offset is not None and (wanted is None or taken < wanted):
        # A pattern is spent by the first read: it seeks, and seeking again
        # from the new start would find the next occurrence instead of
        # continuing. A length is not spent, because it bounds the whole read
        # rather than each slice -- re-applying it per slice returns more than
        # was asked for, and dropping it returns the entire document.
        cap = max_chars if wanted is None else min(max_chars, wanted - taken)
        following = store.retrieve_document(key, offset=offset, max_chars=cap)
        parts.append(following.content)
        taken += following.returned
        offset = following.next_offset

    content = "".join(parts)
    return replace(first, content=content, returned=len(content), next_offset=offset)


def _entry(row: sqlite3.Row) -> Entry:
    """A stored row as a listing entry."""
    return Entry(
        key=row["key"],
        kind="metadata" if row["meta_name"] is not None else "document",
        size=len(row["content"]),
        format=row["format"],
        updated_at=row["updated_at"],
    )


def _scope(key: str | None) -> str:
    """The key a scope argument names, with ``None`` meaning the root.

    Omitting the argument, passing None and passing "" all name the whole
    store. Applied once on the way in, so nothing below here carries a second
    spelling of "everywhere": that duality is what the root key exists to
    remove, and left in place every new call taking a subtree would have to
    re-decide which spelling it accepted.
    """
    return keys.ROOT if key is None else key


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


def _position(key: str) -> str:
    """Where ``key`` sits in the order: the padded sort form of the parsed key.

    Every bound in the store compares against one of these, so a key is parsed
    and normalised on the way into a comparison exactly once and in one place.
    """
    return keys.sort_form(keys.parse(key).key)


def _cursor_bound(cursor: str | None) -> str | None:
    """What a cursor compares against, or None when there is no cursor.

    A cursor names a key, never a position. The store is written to while it is
    being read, so under a positional cursor anything landing before it shifts
    every later page and a page silently repeats or skips. A key does not move.
    """
    return None if cursor is None else _position(cursor)



def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _ms(started: int) -> float:
    """Elapsed milliseconds, from the monotonic clock a time change cannot move."""
    return round((time.monotonic_ns() - started) / 1_000_000, 3)


#: Cap on the keys named in one logged result. A log line has to stay small
#: enough to be written in a single call, or two processes appending can
#: interleave; a survey of a large subtree would otherwise be unbounded.
_MAX_LOGGED_KEYS = 50


def _summarise(log: EventLog, result: object) -> dict[str, object]:
    """Describe a return value in the terms an investigation later asks in.

    Not the value itself. The point of a summary is that the questions being
    asked are about shape — how much was returned, whether it was cut short,
    which keys were touched — and a log holding whole results is a second copy
    of the store rather than a record of what happened to it.
    """
    match result:
        case Excerpt():
            # `next_offset` is the truncation evidence: it is what says a
            # caller was handed part of a document, and following the log
            # forward is what says whether they ever came back for the rest.
            return {
                "total": result.total,
                "returned": result.returned,
                "next_offset": result.next_offset,
                "content": log.content_field(result.content),
            }
        case Backup():
            return {
                "path": str(result.path),
                "bytes": result.bytes,
                "documents": result.documents,
            }
        case str():
            return {"key": result}
        case int():
            return {"count": result}
        case Page():
            # The size of the whole, not just of the page: a log of pages that
            # never says what they were part of cannot answer whether a caller
            # who stopped had finished or given up.
            summary: dict[str, object] = {
                "count": result.returned,
                "total": result.total,
                "total_chars": result.total_chars,
                "next_cursor": result.next_cursor,
            }
            if result.items and isinstance(result.items[0], Excerpt):
                summary["truncated"] = sum(1 for item in result.items if item.truncated)
            elif (
                result.items
                and isinstance(result.items[0], str)
                and result.returned <= _MAX_LOGGED_KEYS
            ):
                summary["keys"] = result.items
            return summary
        case []:
            return {"count": 0}
        case [Excerpt(), *_]:
            return {
                "count": len(result),
                "truncated": sum(1 for excerpt in result if excerpt.truncated),
            }
        case [Entry(), *_]:
            return {"count": len(result)}
        case [str(), *_]:
            listed: dict[str, object] = {"count": len(result)}
            if len(result) <= _MAX_LOGGED_KEYS:
                listed["keys"] = result
            return listed
        case _:
            return {"type": type(result).__name__}


def _decode(value: str, encoding: str, what: str) -> str:
    """Decode one argument that arrived under ``encoding``.

    Only 'json-string' exists: ``value`` is a JSON string literal, and what is
    stored is the string it denotes. The point is not the encoding but the
    check it makes possible. A tool call is generated as text before it is
    parsed into arguments, and a model can emit its own closing scaffolding
    into the middle of a value; that damage is invisible in a bare string,
    which has no shape to violate. A JSON string literal has one, and every
    form of the damage seen so far breaks it: trailing scaffolding is extra
    data past the closing quote, and scaffolding pushed inside the quote
    carries raw newlines, which JSON forbids in a string.

    So this refuses rather than repairs. A value that arrives damaged is one
    the caller can send again; a value that is silently trimmed is one nobody
    ever learns was wrong.
    """
    try:
        decoded = json.loads(value)
    except ValueError as exc:
        raise ValueError(
            f"{what} is not a valid JSON string literal under encoding "
            f"{encoding!r}: {exc}. Send it as a JSON string, quotes included, "
            f"with nothing after the closing quote."
        ) from exc
    if not isinstance(decoded, str):
        raise ValueError(
            f"{what} decoded to {type(decoded).__name__} under encoding "
            f"{encoding!r}, not a string. Send a JSON string literal, not an "
            f"object or an array."
        )
    return decoded


def _detect_format(content: str) -> str:
    stripped = content.lstrip()
    if stripped[:1] in ("{", "["):
        try:
            json.loads(content)
        except ValueError:
            return "markdown"
        return "json"
    return "markdown"


def _find_occurrence(content: str, pattern: str, occurrence: int, offset: int) -> int | None:
    position = offset - 1
    for _ in range(occurrence + 1):
        position = content.find(pattern, position + 1)
        if position == -1:
            return None
    return position


def _excerpt(row: sqlite3.Row, start: int, length: int | None, max_chars: int) -> Excerpt:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if length is not None and length < 0:
        raise ValueError("length must not be negative")

    content = row["content"]
    total = len(content)
    start = min(start, total)
    take = max_chars if length is None else min(length, max_chars)
    excerpt = content[start : start + take]
    end = start + len(excerpt)

    return Excerpt(
        key=row["key"],
        content=excerpt,
        format=row["format"],
        updated_at=row["updated_at"],
        offset=start,
        returned=len(excerpt),
        total=total,
        next_offset=end if end < total else None,
    )


__all__ = [
    "DEFAULT_BULK_MAX_CHARS",
    "DEFAULT_MAX_CHARS",
    "Entry",
    "Excerpt",
    "Key",
    "KeyNotFoundError",
    "Page",
    "PatternNotFoundError",
    "Store",
    "open_store",
    "read_all",
    "resolve_directory",
]
