"""Inspecting and repairing a store from outside an agent session.

The server has no reason to offer any of this. A session asks the store
questions about documents; these are questions about the *store* - whether the
rows still satisfy the invariants they were written under, whether the format
version is one this build understands, and whether the storage underneath them
is sound.

That last one is the only part a backend has to answer for itself, and the
split is the point of this module. Five of the questions a check asks are
about **rows and keys**: how many there are, whether any key is deeper than
:data:`outrage.keys.MAX_SEGMENTS`, whether each row's stored ``parent`` still
agrees with the key it was derived from, whether any metadata has no document,
and whether the file was written by a newer outrage than this. None of those is
SQLite's, and a backend keeping its rows some other way has the same
invariants to break. They are asked here, once, over
:meth:`~outrage.store.FileStore.audit_rows`.

What is left really is the backend's, and is asked through
:meth:`~outrage.store.FileStore.check_file`: SQLite's own integrity check and the
size of its write-ahead log, a parquet file's sort order. Neither has any
meaning for the other, which is why neither is here.

The write-ahead log is worth naming because it is the same trap ``backup``
exists for, seen from the other end. A SQLite store in WAL mode can hold
almost nothing in ``store.sqlite`` and megabytes in ``store.sqlite-wal``, and
it opens and reads perfectly that way - so nothing in normal use reveals it,
and anything copying the file alone gets a store missing its recent history.
``check`` reports the split; ``--repair`` folds it back.

Nothing here is destructive. A repair moves bytes about and never changes a
document; one that could lose content would need a backup taken first, and no
backend offers such a repair.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import keys
from .errors import OutrageError
from .store import FileStore, entry_kind, store_file


class CheckError(OutrageError, RuntimeError):
    """Raised when a store cannot be checked at all."""


@dataclass(frozen=True)
class Problem:
    """Something wrong, or worth knowing, about the store rather than a document.

    ``severity`` is 'error' for a store that is damaged or unreadable by this
    build, 'warning' for something that will cause a wrong answer later, and
    'note' for a fact worth reporting that is not itself a fault.

    ``repairable`` is set by whoever raises the problem, because that is the
    only place the answer is known: a backend appending this from
    :meth:`~outrage.store.FileStore.check_file` knows whether its own
    :meth:`~outrage.store.FileStore.repair` acts on it, and nothing above can. It
    defaults to False so that a problem nobody thought about cannot claim to
    be fixable.
    """

    severity: str
    summary: str
    detail: str = ""
    repairable: bool = False


@dataclass
class Report:
    """What a check found. Empty ``problems`` is a sound store."""

    path: Path
    backend: str = ""
    """What kept the file: 'sqlite', 'parquet'. Named because the rest of the
    report reads differently depending on the answer, and because a report that
    did not say would look identical for a store nothing could check."""
    format_version: int = 0
    documents: int = 0
    metadata: int = 0
    characters: int = 0
    details: dict[str, str] = field(default_factory=dict)
    """What this backend says about its own storage, label to value, in the
    order it is worth printing. Filled by
    :meth:`~outrage.store.FileStore.check_file`. A mapping rather than fields, so
    that the numbers SQLite has and parquet does not are absent rather than
    zero -- a report reading ``0 bytes in the log`` for a store that has no log
    is a wrong answer delivered as a clean bill of health."""
    problems: list[Problem] = field(default_factory=list)

    @property
    def sound(self) -> bool:
        """No errors and no warnings. Notes do not make a store unsound."""
        return not any(problem.severity in ("error", "warning") for problem in self.problems)

    @property
    def repairable(self) -> list[Problem]:
        """The problems ``--repair`` would actually act on, in the order found.

        A subset of :attr:`problems`, and usually a strict one. A damaged file
        or a schema from a newer build is reported and left alone, because the
        repairs move where the bytes live and nothing else. An empty list is
        what stops ``outrage check`` offering ``--repair``.
        """
        return [problem for problem in self.problems if problem.repairable]


@dataclass(frozen=True)
class Repaired:
    """What a repair actually did, in bytes rather than in claims."""

    action: str
    before: int
    after: int


def check(store: FileStore) -> Report:
    """Ask whether the store is what it should be.

    Read-only, and answerable for any backend. It runs against an open store
    rather than a path because the invariants being checked are the ones the
    backend writes rows under, and opening through it is also what proves the
    file opens at all.
    """
    report = Report(
        path=store.path,
        backend=type(store).backend_name,
        format_version=store.stored_format_version,
    )
    _check_format_version(store, report)
    _check_rows(store, report)
    store.check_file(report)
    return report


def repair(store: FileStore) -> list[Repaired]:
    """Fix what a check found and the backend can act on.

    A thin pair for :func:`check`, and here rather than left as a method so
    that a caller doing maintenance reaches for one vocabulary throughout.
    Returns what was done, which is an empty list for a backend whose storage
    cannot get into a repairable state -- see
    :meth:`~outrage.store.FileStore.repair`.
    """
    return store.repair()


def _check_format_version(store: FileStore, report: Report) -> None:
    """Compare the version in the file with the one this build writes.

    Written once rather than per backend: each records the number somewhere
    different, and :attr:`~outrage.store.FileStore.stored_format_version` is the name
    that difference does not reach. "Written by something newer than this" is
    the same fault whatever wrote it.

    A backend may refuse an unreadable version on the way in rather than
    reporting it here -- parquet does, so a check of one never sees the error
    branch, because the open that preceded it would have failed. That is not a
    contradiction: this is the answer for a backend that can open a file it
    only partly understands.
    """
    writes = type(store).format_version
    if report.format_version > writes:
        report.problems.append(
            Problem(
                "error",
                "the store was written by a newer version of outrage",
                f"format {report.format_version}, this build understands {writes}",
            )
        )
    elif report.format_version < writes:
        # Not a fault: a writable backend migrates when it opens. Worth saying
        # because it means the file on disk is not the shape the code assumes
        # until then.
        report.problems.append(
            Problem(
                "note",
                "the store predates this build's format",
                f"format {report.format_version}, this build writes {writes}",
            )
        )


def _check_rows(store: FileStore, report: Report) -> None:
    """Every question a check can ask about rows and keys, in one pass.

    One pass rather than a query per question, because they want the same rows
    for different purposes and a store worth checking is large enough for a
    second walk to be felt. The SQLite backend used to pay for two, and said
    so in a comment explaining why a third was not worth it.
    """
    over_deep: list[str] = []
    wrong_parent: list[str] = []
    documents: set[str] = set()
    attached: dict[str, None] = {}

    for row in store.audit_rows():
        # By the last segment, not by ``meta_name``: a metadata namespace holds
        # documents of its own, and ``a/!changelog/22`` is one of them. The
        # census counts what each row *is*; ``meta_name`` says where its key
        # first turns to metadata, which is a different question.
        if entry_kind(row.key) == "document":
            report.documents += 1
            documents.add(row.key)
        else:
            report.metadata += 1
            # Against ``doc_key``, so the whole metadata subtree hangs from the
            # document it describes. That is what keeps an implicit metadata
            # key with content below it -- ``a/!changelog`` holding notes --
            # from being reported as an orphan of its own.
            attached.setdefault(row.doc_key)
        report.characters += row.chars

        # The root may hold content, and has no segments to count.
        if row.key and row.key.count(keys.DELIMITER) + 1 > keys.MAX_SEGMENTS:
            over_deep.append(row.key)

        try:
            expected = keys.parse(row.key).parent
        except keys.InvalidKeyError:
            wrong_parent.append(f"{row.key} is not a valid key")
        else:
            if row.parent != expected:
                wrong_parent.append(f"{row.key} claims parent {row.parent!r}, implies {expected!r}")

    _report_depth(over_deep, report)
    _report_parents(wrong_parent, report)
    _report_orphans([key for key in attached if key not in documents], report)


def _report_depth(over_deep: list[str], report: Report) -> None:
    """Keys with more segments than a store may now hold.

    ``keys.MAX_SEGMENTS`` is 64 so that a mount point and a key inside a store
    - each bounded by it - always join into a valid key in the namespace a mount
    table presents. Nothing writes a deeper key; a store written by an earlier
    outrage can still hold one.

    It is only a fault if the store is ever *mounted*, where the key would have
    no name from outside - so this is a warning naming the keys, not an error.
    Reported here because this is the only place that looks before something
    tries: ``Mount.outer`` raises when it meets one, which is correct and late.
    """
    if not over_deep:
        return
    report.problems.append(
        Problem(
            "warning",
            f"some keys have more than {keys.MAX_SEGMENTS} segments",
            f"{_listed(over_deep)}; they predate that bound, and this store cannot be "
            f"mounted until they are moved",
        )
    )


def _report_parents(wrong: list[str], report: Report) -> None:
    """Every row's stored ``parent`` must be the one its key implies.

    The column is denormalised - it exists so that listing a level is an index
    lookup rather than a scan - which means it can disagree with the key it was
    derived from, and nothing in normal reading would notice. A disagreement
    makes a document unlistable while it is still perfectly readable by key,
    which is a document that has effectively vanished from every survey.

    Not SQLite's, although only SQLite could get it wrong until recently: the
    parquet backend denormalises the same value into the same column, for the
    same reason, and can be handed a file where it disagrees just as easily.
    """
    if not wrong:
        return
    report.problems.append(
        Problem(
            "warning",
            "some rows disagree with the key they are stored under",
            _listed(wrong, separator="; "),
        )
    )


def _report_orphans(orphans: list[str], report: Report) -> None:
    """Metadata whose document does not exist.

    Legal, and reachable by writing ``a/b/!title`` without ever writing ``a/b``.
    Reported as a note rather than a fault because it is a real state a caller
    can want - but it is also how a survey comes to list a title for something
    that cannot be read, so it is worth naming.
    """
    if not orphans:
        return
    report.problems.append(
        Problem(
            "note",
            "some metadata has no document",
            # Spelled rather than printed raw: the root can carry a title
            # without a document beneath it, and a blank name in this list
            # would read as no name at all.
            _listed([keys.displayed(key) for key in orphans]),
        )
    )


def _listed(names: list[str], shown: int = 5, separator: str = ", ") -> str:
    """Name a few and count the rest, so a long list stays one line.

    The separator is an argument because one of the callers lists phrases that
    contain commas of their own, and a list of those joined by another comma
    is not readable as a list at all.
    """
    rest = len(names) - shown
    return separator.join(names[:shown]) + (f"{separator}and {rest} more" if rest > 0 else "")


def require_store(directory: Path, filename: str | None = None) -> Path:
    """Refuse a store file that is not there, rather than creating one.

    ``FileStore.__init__`` creates what is missing, so every command that means to
    act on an existing store has to ask first - otherwise checking a mistyped
    path reports a perfectly healthy empty store, which is the wrong answer
    delivered as a clean bill of health.

    Names the file, not just the directory: since a directory holds several
    stores, "no store in .outrage" would be the wrong sentence as often as it was
    the right one.
    """
    if not store_file(directory, filename).exists():
        raise CheckError("check-no-store", path=str(store_file(directory, filename)))
    return directory


__all__ = [
    "CheckError",
    "Problem",
    "Repaired",
    "Report",
    "check",
    "repair",
    "require_store",
]
