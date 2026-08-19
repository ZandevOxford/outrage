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

SCHEMA_VERSION = 3

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
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._migrate()

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
            parsed = keys.parse(was)
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
        self._conn.close()

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

        ``title`` writes the ``:title`` metadata alongside the document in the
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
                self._write(keys.parse(f"{parsed.key}{keys.META}title"), title, "markdown")
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
                "SELECT DISTINCT doc_key FROM documents WHERE parent = ? AND meta_name IS NULL",
                (parent,),
            )
        }
        names.update(child[prefix_len:] for child in self._implicit_children(parent))
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
                lo, hi = keys.subtree_range(parsed.doc_key)
                targets += [
                    row["key"]
                    for row in self._conn.execute(
                        "SELECT key FROM documents WHERE doc_key >= ? AND doc_key < ?",
                        (lo, hi),
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
        lo, hi = keys.subtree_range(keys.parse(key).doc_key)
        row = self._conn.execute(
            "SELECT count(*) AS n FROM documents WHERE doc_key >= ? AND doc_key < ?",
            (lo, hi),
        ).fetchone()
        return row["n"]

    # -- reading ---------------------------------------------------------

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
    def list_keys(self, key: str | None = None) -> list[Entry]:
        """List the keys immediately below ``key``, or below the root.

        Includes subkeys and metadata, and keys that exist only implicitly
        because something beneath them has content.
        """
        parent = keys.parse(key).doc_key if key is not None else keys.ROOT

        entries: dict[str, Entry] = {}
        for row in self._conn.execute(
            "SELECT * FROM documents WHERE parent = ? ORDER BY sort_key", (parent,)
        ):
            entries[row["key"]] = Entry(
                key=row["key"],
                kind="metadata" if row["meta_name"] is not None else "document",
                size=len(row["content"]),
                format=row["format"],
                updated_at=row["updated_at"],
            )

        for implicit in self._implicit_children(parent):
            entries.setdefault(
                implicit,
                Entry(key=implicit, kind="implicit", size=None, format=None, updated_at=None),
            )

        return [entries[k] for k in sorted(entries, key=keys.sort_form)]

    def _implicit_children(self, parent: str) -> Iterator[str]:
        """Children of ``parent`` that hold no content themselves.

        Every stored row names its own parent, so the distinct parents lying
        within the subtree, truncated back to one level down, are exactly the
        keys that exist implicitly.
        """
        if parent == keys.ROOT:
            rows = self._conn.execute("SELECT DISTINCT parent FROM documents")
            prefix_len = 0
        else:
            lo, hi = keys.subtree_range(parent)
            rows = self._conn.execute(
                "SELECT DISTINCT parent FROM documents WHERE parent >= ? AND parent < ?",
                (lo, hi),
            )
            prefix_len = len(parent) + 1

        seen: set[str] = set()
        for row in rows:
            value = row["parent"]
            if not value:
                continue
            head, _, _ = value[prefix_len:].partition(keys.DELIMITER)
            child = value[:prefix_len] + head
            if child not in seen:
                seen.add(child)
                yield child

    @_logged("get_documents")
    def get_documents(
        self,
        key: str | None = None,
        *,
        meta_name: str | Sequence[str] | None = None,
        depth: int | None = None,
        max_chars: int = DEFAULT_BULK_MAX_CHARS,
    ) -> list[Excerpt]:
        """Read everything at and below ``key``, newest key order.

        With ``meta_name`` the result holds those metadata entries instead of
        documents, which is how the titles of every document under a key are
        listed in one call. ``depth`` limits how far below ``key`` to descend,
        counted in segments; the default is unlimited.
        """
        where = []
        params: list[object] = []

        if key is not None:
            parsed = keys.parse(key)
            lo, hi = keys.subtree_range(parsed.doc_key)
            where.append("(doc_key = ? OR (doc_key >= ? AND doc_key < ?))")
            params += [parsed.doc_key, lo, hi]

        if meta_name is None:
            where.append("meta_name IS NULL")
        else:
            names = [meta_name] if isinstance(meta_name, str) else list(meta_name)
            if not names:
                raise ValueError("meta_name must not be an empty sequence")
            where.append(f"meta_name IN ({', '.join('?' * len(names))})")
            params += names

        sql = "SELECT * FROM documents"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY sort_key"

        rows = self._conn.execute(sql, params).fetchall()

        if depth is not None:
            if depth < 0:
                raise ValueError("depth must not be negative")
            base = keys.depth(key) if key is not None else 0
            rows = [row for row in rows if keys.depth(row["doc_key"]) - base <= depth]

        return [_excerpt(row, 0, None, max_chars) for row in rows]

    @_logged("keys_missing_meta")
    def keys_missing_meta(
        self,
        key: str | None = None,
        *,
        meta_name: str | Sequence[str] = "title",
        depth: int | None = None,
    ) -> list[str]:
        """Document keys at and below ``key`` carrying none of ``meta_name``.

        A survey by ``:title`` only sees documents that have one, so on its own
        it silently under-reports the store. This names what the survey missed.
        """
        names = [meta_name] if isinstance(meta_name, str) else list(meta_name)
        if not names:
            raise ValueError("meta_name must not be an empty sequence")

        # Deliberately the same call the survey makes, so the two lists agree on
        # what was in range; only the content is thrown away.
        documents = self.get_documents(key, depth=depth, max_chars=1)
        having = {
            row["doc_key"]
            for row in self._conn.execute(
                f"SELECT DISTINCT doc_key FROM documents "
                f"WHERE meta_name IN ({', '.join('?' * len(names))})",
                names,
            )
        }
        return [excerpt.key for excerpt in documents if excerpt.key not in having]

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
            summary: dict[str, object] = {"count": len(result)}
            if len(result) <= _MAX_LOGGED_KEYS:
                summary["keys"] = result
            return summary
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
    "PatternNotFoundError",
    "Store",
    "open_store",
    "read_all",
    "resolve_directory",
]
