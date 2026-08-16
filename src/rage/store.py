"""SQLite backed document store.

Independent of MCP: everything here is callable and testable on its own. See
design.md for the key namespace, the tool semantics and the schema.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from . import keys
from .keys import Key

#: Default directory name, relative to the working directory, when neither
#: --dir nor RAGE_DIR is given.
DEFAULT_DIR_NAME = ".rage"

DB_FILENAME = "store.sqlite"

ENV_DIR = "RAGE_DIR"

#: Cap on a single retrieve, so one oversized document cannot flood an agent's
#: context window. The caller pages with the returned next_offset.
DEFAULT_MAX_CHARS = 8000

#: Per document cap when several are returned at once, which is usually a
#: listing rather than a read.
DEFAULT_BULK_MAX_CHARS = 2000

FORMATS = ("markdown", "json")

SCHEMA_VERSION = 2

#: A key segment that names a number, for the benefit of wildcard allocation.
#: Deliberately not str.isdigit, which accepts superscripts and other digits
#: that int() then rejects.
_NUMBER_RE = re.compile(r"\A[0-9]+\Z")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
  key        TEXT PRIMARY KEY,
  doc_key    TEXT NOT NULL,
  meta_name  TEXT,
  parent     TEXT NOT NULL,
  content    TEXT NOT NULL,
  format     TEXT,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_documents_parent ON documents(parent);
CREATE INDEX IF NOT EXISTS idx_documents_meta   ON documents(meta_name, doc_key);
"""


class KeyNotFoundError(LookupError):
    """Raised when a key holds no content."""


class PatternNotFoundError(LookupError):
    """Raised when a search pattern does not occur in a document."""


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


class Store:
    """A document store held in a single SQLite database."""

    def __init__(self, directory: str | os.PathLike[str] | None = None) -> None:
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
            elif version < 2:
                self._migrate_delimiter_to_slash()
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

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- writing ---------------------------------------------------------

    def store_document(self, key: str, content: str, format: str | None = None) -> str:
        """Store ``content`` at ``key``, overwriting anything already there.

        A ``?`` segment in ``key`` is replaced by a number unused among the
        children of the key enclosing it, so ``tmp/?`` writes to ``tmp/1`` in
        an empty store. Returns the key actually written, which is the only way
        the caller learns an allocated number.

        ``format`` defaults to 'json' when the content parses as a JSON object
        or array, and 'markdown' otherwise.
        """
        parsed = keys.parse(key, allow_wildcard=True)
        if not isinstance(content, str):
            raise TypeError(f"content must be a string, got {type(content).__name__}")
        if format is None:
            format = _detect_format(content)
        elif format not in FORMATS:
            raise ValueError(f"format must be one of {FORMATS}, got {format!r}")

        # Allocating reads before it writes, so the whole thing has to be one
        # transaction that excludes other writers: a deferred transaction would
        # let two callers pick the same number.
        with self._transaction(immediate=parsed.has_wildcard):
            if parsed.has_wildcard:
                allocated = self._next_number(parsed.wildcard_parent)
                parsed = keys.parse(keys.substitute_wildcard(parsed.key, allocated))
            self._conn.execute(
                """
                INSERT INTO documents (key, doc_key, meta_name, parent, content, format,
                                       updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
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
                ),
            )
        return parsed.key

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
        used = [int(name) for name in self._child_names(parent) if _NUMBER_RE.match(name)]
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
        return sorted(targets)

    # -- reading ---------------------------------------------------------

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
            raise KeyNotFoundError(f"no content stored at {key!r}")

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

    def list_keys(self, key: str | None = None) -> list[Entry]:
        """List the keys immediately below ``key``, or below the root.

        Includes subkeys and metadata, and keys that exist only implicitly
        because something beneath them has content.
        """
        parent = keys.parse(key).doc_key if key is not None else keys.ROOT

        entries: dict[str, Entry] = {}
        for row in self._conn.execute(
            "SELECT * FROM documents WHERE parent = ? ORDER BY key", (parent,)
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

        return [entries[k] for k in sorted(entries)]

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
        sql += " ORDER BY key"

        rows = self._conn.execute(sql, params).fetchall()

        if depth is not None:
            if depth < 0:
                raise ValueError("depth must not be negative")
            base = keys.depth(key) if key is not None else 0
            rows = [row for row in rows if keys.depth(row["doc_key"]) - base <= depth]

        return [_excerpt(row, 0, None, max_chars) for row in rows]


@contextmanager
def open_store(directory: str | os.PathLike[str] | None = None) -> Iterator[Store]:
    """Open a store, closing it on exit."""
    store = Store(directory)
    try:
        yield store
    finally:
        store.close()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


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
    "resolve_directory",
]
