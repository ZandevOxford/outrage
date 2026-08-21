"""Inspecting and repairing a store from outside an agent session.

The server has no reason to offer any of this. A session asks the store
questions about documents; these are questions about the *file* — whether
SQLite still considers it sound, whether the schema is one this build
understands, whether the rows still satisfy the invariants the store writes
them under, and whether all the recent writes are sitting in a sidecar rather
than in the database.

That last one is the same trap ``backup`` exists for, seen from the other end.
A store in WAL mode can hold almost nothing in ``store.sqlite`` and megabytes
in ``store.sqlite-wal``, and it opens and reads perfectly that way — so nothing
in normal use ever reveals it, and anything that copies the file alone gets a
store missing its recent history. ``check`` reports the split; ``--repair``
folds it back.

Nothing here is destructive. The two repairs are a WAL checkpoint and a
VACUUM: both rewrite where the bytes live and neither changes a document. A
repair that could lose content would need a backup first, and this module
deliberately has no such repair to offer.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from . import keys
from .errors import RageError
from .store import DB_FILENAME, SCHEMA_VERSION, Store, store_file


class CheckError(RageError, RuntimeError):
    """Raised when a store cannot be checked at all."""


@dataclass(frozen=True)
class Problem:
    """Something wrong, or worth knowing, about the file rather than a document.

    ``severity`` is 'error' for a store that is damaged or unreadable by this
    build, 'warning' for something that will cause a wrong answer later, and
    'note' for a fact worth reporting that is not itself a fault.
    """

    severity: str
    summary: str
    detail: str = ""

    @property
    def repairable(self) -> bool:
        """Whether ``repair`` can fix this one, as opposed to only reporting it."""
        return self.summary in _REPAIRS


@dataclass
class Report:
    """What a check found. Empty ``problems`` is a sound store."""

    path: Path
    schema: int = 0
    integrity: str = ""
    documents: int = 0
    metadata: int = 0
    characters: int = 0
    main_bytes: int = 0
    wal_bytes: int = 0
    problems: list[Problem] = field(default_factory=list)

    @property
    def sound(self) -> bool:
        """No errors and no warnings. Notes do not make a store unsound."""
        return not any(problem.severity in ("error", "warning") for problem in self.problems)

    @property
    def repairable(self) -> list[Problem]:
        return [problem for problem in self.problems if problem.repairable]


#: Problems ``repair`` knows how to act on, by their summary. Keyed on the
#: summary so that a check reporting something no repair addresses cannot
#: quietly claim to be fixable.
_WAL_UNCHECKPOINTED = "most of the store is in the write-ahead log"
_REPAIRS = frozenset({_WAL_UNCHECKPOINTED})

#: When the sidecar is worth reporting. A WAL always holds something between
#: checkpoints; it is only interesting once it holds more than the database it
#: belongs to, which is the state that makes a file copy lose real content.
WAL_RATIO = 1.0


def check(store: Store) -> Report:
    """Ask SQLite and the schema whether the store is what it should be.

    Read-only. It runs against an open store rather than a path because the
    invariants being checked are the ones ``Store`` writes rows under, and
    opening through ``Store`` is also what proves the file opens at all.
    """
    connection = store.connection
    report = Report(path=store.path)

    try:
        report.integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        report.schema = int(connection.execute("PRAGMA user_version").fetchone()[0])
    except sqlite3.DatabaseError as exc:
        raise CheckError("check-unreadable", path=str(store.path), reason=str(exc)) from exc

    if report.integrity != "ok":
        report.problems.append(
            Problem("error", "SQLite reports the database as damaged", report.integrity)
        )
    if report.schema > SCHEMA_VERSION:
        report.problems.append(
            Problem(
                "error",
                "the store was written by a newer version of rage",
                f"schema {report.schema}, this build understands {SCHEMA_VERSION}",
            )
        )
    elif report.schema < SCHEMA_VERSION:
        # Not a fault: opening through Store migrates. Worth saying because it
        # means the file on disk is not the shape the code assumes until then.
        report.problems.append(
            Problem(
                "note",
                "the store predates this build's schema",
                f"schema {report.schema}, this build writes {SCHEMA_VERSION}",
            )
        )

    _count(connection, report)
    _check_depth(connection, report)
    _check_parents(connection, report)
    _check_orphan_metadata(connection, report)
    _check_wal(store, report)
    return report


def _count(connection: sqlite3.Connection, report: Report) -> None:
    row = connection.execute(
        "SELECT "
        "  SUM(meta_name IS NULL) AS documents, "
        "  SUM(meta_name IS NOT NULL) AS metadata, "
        "  SUM(LENGTH(content)) AS characters "
        "FROM documents"
    ).fetchone()
    report.documents = row["documents"] or 0
    report.metadata = row["metadata"] or 0
    report.characters = row["characters"] or 0


def _check_depth(connection: sqlite3.Connection, report: Report) -> None:
    """Keys with more segments than a store may now hold.

    ``keys.MAX_SEGMENTS`` was halved to 64 on 2026-08-20, so that a mount point
    and a key inside a store — each bounded by it — always join into a valid
    key in the namespace a mount table presents. Nothing writes such a key any
    more; a store written by an earlier rage can still hold one.

    It is only a fault if the store is ever *mounted*, where the key would have
    no name from outside — so this is a warning naming the keys, not an error.
    Reported here because this is the only place that looks before something
    tries: `Mount.outer` raises when it meets one, which is correct and late.

    Counted in SQL rather than by parsing every key in Python, since
    ``_check_parents`` already pays for one full parse of the table and a
    second would double the cost of a check to ask a much narrower question.
    """
    over = [
        row["key"]
        for row in connection.execute(
            "SELECT key FROM documents "
            "WHERE key <> '' "
            "AND length(key) - length(replace(key, ?, '')) + 1 > ?",
            (keys.DELIMITER, keys.MAX_SEGMENTS),
        )
    ]
    if over:
        report.problems.append(
            Problem(
                "warning",
                f"some keys have more than {keys.MAX_SEGMENTS} segments",
                f"{_listed(over)}; they predate that bound, and this store cannot be "
                f"mounted until they are moved",
            )
        )


def _check_parents(connection: sqlite3.Connection, report: Report) -> None:
    """Every row's stored ``parent`` must be the one its key implies.

    The column is denormalised — it exists so that listing a level is an index
    lookup rather than a scan — which means it can disagree with the key it was
    derived from, and nothing in normal reading would notice. A disagreement
    makes a document unlistable while it is still perfectly readable by key,
    which is a document that has effectively vanished from every survey.
    """
    wrong = []
    for row in connection.execute("SELECT key, parent FROM documents"):
        try:
            expected = keys.parse(row["key"]).parent
        except keys.InvalidKeyError:
            wrong.append(f"{row['key']} is not a valid key")
            continue
        if row["parent"] != expected:
            wrong.append(f"{row['key']} claims parent {row['parent']!r}, implies {expected!r}")

    if wrong:
        report.problems.append(
            Problem(
                "warning",
                "some rows disagree with the key they are stored under",
                "; ".join(wrong[:5]) + (f"; and {len(wrong) - 5} more" if len(wrong) > 5 else ""),
            )
        )


def _check_orphan_metadata(connection: sqlite3.Connection, report: Report) -> None:
    """Metadata whose document does not exist.

    Legal, and reachable by writing ``a/b/!title`` without ever writing ``a/b``.
    Reported as a note rather than a fault because it is a real state a caller
    can want — but it is also how a survey comes to list a title for something
    that cannot be read, so it is worth naming.
    """
    orphans = [
        # Spelled rather than printed raw: the root can carry a title without
        # a document beneath it, and a blank name in this list would read as
        # no name at all.
        keys.displayed(row["doc_key"])
        for row in connection.execute(
            "SELECT DISTINCT doc_key FROM documents WHERE meta_name IS NOT NULL "
            "AND doc_key NOT IN (SELECT key FROM documents WHERE meta_name IS NULL)"
        )
    ]
    if orphans:
        report.problems.append(
            Problem(
                "note",
                "some metadata has no document",
                _listed(orphans),
            )
        )


def _listed(names: list[str], shown: int = 5) -> str:
    """Name a few and count the rest, so a long list stays one line."""
    rest = len(names) - shown
    return ", ".join(names[:shown]) + (f", and {rest} more" if rest > 0 else "")


def _check_wal(store: Store, report: Report) -> None:
    """Compare the database with its write-ahead log."""
    report.main_bytes = store.path.stat().st_size if store.path.exists() else 0
    wal = store.path.with_name(store.path.name + "-wal")
    report.wal_bytes = wal.stat().st_size if wal.exists() else 0

    if report.main_bytes and report.wal_bytes > report.main_bytes * WAL_RATIO:
        report.problems.append(
            Problem(
                "warning",
                _WAL_UNCHECKPOINTED,
                f"{report.wal_bytes} bytes in {wal.name} against {report.main_bytes} in "
                f"{store.path.name}. The store reads correctly, but anything copying the "
                f"database file alone gets one missing those writes.",
            )
        )


@dataclass(frozen=True)
class Repaired:
    """What a repair actually did, in bytes rather than in claims."""

    action: str
    before: int
    after: int


def repair(store: Store) -> list[Repaired]:
    """Fold the write-ahead log back and compact the database.

    Both steps are safe to run on a healthy store and safe to run twice. Sizes
    are measured either side rather than reported from the action's own return
    value, because the question being asked is what the file looks like now.
    """
    done = []

    before = _sizes(store)
    store.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    after = _sizes(store)
    done.append(Repaired("checkpoint the write-ahead log", before[1], after[1]))

    # VACUUM cannot run inside a transaction, and sqlite3 opens one implicitly
    # for anything it thinks is a write. Committing first is what lets it run.
    store.connection.commit()
    store.connection.execute("VACUUM")
    # VACUUM rewrites the whole database, and in WAL mode it writes through the
    # log like anything else. Without this second checkpoint the repair ends
    # holding a log the size of the file it just compacted, and the check that
    # runs afterwards reports the same warning it was called to clear -- a
    # repair that worked, reporting itself as a failure.
    store.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    done.append(Repaired("compact the database", after[0], _sizes(store)[0]))
    return done


def _sizes(store: Store) -> tuple[int, int]:
    """Bytes in the database and in its write-ahead log, in that order."""
    wal = store.path.with_name(store.path.name + "-wal")
    return (
        store.path.stat().st_size if store.path.exists() else 0,
        wal.stat().st_size if wal.exists() else 0,
    )


def require_store(directory: Path, filename: str = DB_FILENAME) -> Path:
    """Refuse a store file that is not there, rather than creating one.

    ``Store.__init__`` creates what is missing, so every command that means to
    act on an existing store has to ask first — otherwise checking a mistyped
    path reports a perfectly healthy empty store, which is the wrong answer
    delivered as a clean bill of health.

    Names the file, not just the directory: since a directory holds several
    stores, "no store in .rage" would be the wrong sentence as often as it was
    the right one.
    """
    if not store_file(directory, filename).exists():
        raise CheckError("check-no-store", path=str(store_file(directory, filename)))
    return directory


__all__ = [
    "WAL_RATIO",
    "CheckError",
    "Problem",
    "Repaired",
    "Report",
    "check",
    "repair",
    "require_store",
]
