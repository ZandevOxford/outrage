"""What a document store is, in terms every backend has to answer in.

A store maps a key to a document. This module says what that means -- the
constants a caller configures it with, the value types every answer comes back
as, the two ways a call bounds what it is asking about, and the abstract
:class:`Store` that names the operations themselves. It says none of it in
terms of how the documents are kept.

The vocabulary is the interesting part, and it is worth reading in this order:

* :class:`KeyRange` is a stretch of the key *order*, and
  :class:`BoundedSubtree` is a part of the *hierarchy*. A subtree read gives
  both, plus a page cursor, and the three bound different things -- which is
  the distinction :class:`KeyRange` exists to keep.
* :class:`Excerpt` is part of one document and :class:`Page` is part of a
  collection, and each states the size of the whole it came from. A partial
  answer that does not is not actionable.
* :class:`Entry` is how one key appears in its parent's listing, which is the
  only place the difference between a stored key and an implicit one shows.

:class:`Store` itself is abstract, and it says only what a store *does*.
:class:`FileStore` is the half of that which needs a file to answer -- where it
lives, what version wrote it, how it is copied and checked -- and the three
backends are its implementations:
:class:`outrage.store_sqlite.SqliteStore` is a read-write database accumulated a
document at a time, :class:`outrage.store_parquet.ParquetStore` is one
columnar file written whole and read many times, for a reference base of tens
of thousands of documents, and
:class:`outrage.store_files.FilesystemStore` is a directory of files, whose
"file" is that directory. They share none of the storage and every word of
the vocabulary below, which is the point of the split.
:class:`outrage.mounts.MountedStore` is a :class:`Store` and not a
:class:`FileStore`: it keeps nothing of its own and routes to the stores behind
it, and that is what the two classes are for.

:func:`_backend_for` is the one place in the package that chooses between
them, and it chooses by the store file's extension. So nothing above here --
not the server, not the command line, not the mount table -- names a backend
to open one.

Independent of MCP: everything here is callable and testable on its own. Read
:mod:`outrage.keys` first for what a key is, which everything below is written in
terms of; the key namespace and the tool semantics are argued in ``design.md``,
which ships beside these pages as ``outrage/design`` and is not part of this
generated reference.
"""

from __future__ import annotations

import codecs
import functools
import importlib
import inspect
import json
import os
import re
import shutil
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Generator, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Self, TypeVar, get_args

from . import eventlog, keys
from .errors import OutrageError
from .eventlog import EventLog

if TYPE_CHECKING:
    # Only in the signatures of the maintenance methods below. A runtime
    # import would be a cycle: outrage.maintenance is written in terms of Store,
    # and each backend imports the vocabulary from it to fill a report in.
    from .maintenance import Repaired, Report

#: Default directory name, relative to the working directory, when neither
#: --dir nor OUTRAGE_DIR is given.
DEFAULT_DIR_NAME = ".outrage"

#: Where backups go when no destination is given, relative to the store
#: directory.
BACKUP_DIR_NAME = "backups"

#: How a backup is named within that directory. Sortable, so a listing is in
#: age order without parsing anything, and to the second, because two backups
#: in one minute is a thing that happens while working on the store itself.
BACKUP_STAMP = "%Y%m%d-%H%M%S"

#: Environment variable naming the store directory, consulted when no ``--dir``
#: is given. See :func:`resolve_directory` for the order the three sources
#: are tried in.
ENV_DIR = "OUTRAGE_DIR"

#: Cap on a single retrieve, so one oversized document cannot flood an agent's
#: context window. The caller pages with the returned next_offset.
DEFAULT_MAX_CHARS = 8000

#: Per document cap when several are returned at once, which is usually a
#: listing rather than a read.
DEFAULT_BULK_MAX_CHARS = 2000

#: What a document may be stored as, and the only thing the store knows about
#: a document's text. Detected from the content when a caller names none, but
#: only two of the four can be: JSON and HTML each open with something no other
#: format plausibly opens with, while 'text' and 'markdown' are the same
#: characters and only the caller knows which was meant. So plain text is asked
#: for, never inferred. See :func:`_detect_format`.
Format = Literal["markdown", "json", "text", "html"]

#: How one search criterion compares its pattern with a stored value.
MatchMode = Literal["contains", "line", "regex"]

#: Which part of a document one search criterion examines.
SearchTarget = Literal["document", "metadata"]

#: Whether any criterion or every criterion selects a document.
SearchCombination = Literal["any", "all"]

#: The same four as a tuple, for membership tests and for argparse ``choices``.
#: Derived from :data:`Format` rather than written twice: a front end validates
#: against the type and this is what lists it, and the two drifting apart is a
#: schema that advertises a format the store then refuses.
FORMATS: tuple[str, ...] = get_args(Format)

#: Encodings a caller may use for the content, title and contents it passes in.
#: These describe the argument in transit, not the stored document, which is
#: always decoded back to plain text before it is written. See ``_decode``.
Encoding = Literal["json-string"]

#: The same, as a tuple. See :data:`FORMATS` for why it is derived.
ENCODINGS: tuple[str, ...] = get_args(Encoding)


class StoreFileError(OutrageError, ValueError):
    """A store file that does not name a file inside its directory.

    A store file is always relative to the directory holding it -- that is what
    lets one directory hold several stores, and what keeps a configuration file
    free of absolute paths that stop being true when a project moves. An
    absolute path, or one climbing out with ``..``, is refused here rather than
    quietly opening a database somewhere nobody was looking.
    """


class InvalidArgumentError(OutrageError, ValueError):
    """Raised when an argument's *value* is one the caller can correct.

    The distinction :mod:`outrage.errors` draws, applied to arguments. Most of
    the value checks in this package guard against a caller that cannot fix
    anything -- a negative ``offset`` reaching a backend means the front end
    let it through, and a bare ``ValueError`` and its traceback are the right
    output for that. These are the other kind: a person or a model sent
    something they can send again differently, and they need a sentence saying
    so.

    Reaching for this one is a claim about **reachability**. A check a front
    end already makes -- argparse ``choices``, a schema constraint -- cannot be
    reached by a caller and stays a bare ``ValueError``; only what no front end
    can express in its own argument layer belongs here.

    Kept a ``ValueError`` too, so ``except ValueError`` around a store call
    goes on working. That matters more here than elsewhere, because the mcp
    SDK's own boundary catches on the class.
    """


class KeyNotFoundError(OutrageError, LookupError):
    """Raised when a key holds no content."""


class PatternNotFoundError(OutrageError, LookupError):
    """Raised when a search pattern does not occur in a document."""


class BackupError(OutrageError, RuntimeError):
    """Raised when a backup cannot be taken, or cannot be shown to be good."""


class ReadOnlyStoreError(OutrageError, PermissionError):
    """Raised when a store is asked to write and its backend cannot.

    Distinct from :class:`outrage.mounts.ReadOnlyMountError`, which is about a
    *configuration*: a store that could be written was mounted with
    ``--mount-ro``, and starting the server without that flag would let the
    write through. This one is about the storage. A parquet file is not
    updated in place, so no flag exists that would make the same call succeed,
    and telling a caller to drop one would be advice that does not work.
    """


class BackendError(OutrageError, RuntimeError):
    """Raised when a backend cannot be used: absent, or asked for a file it
    did not write."""


class ChangedSinceError(OutrageError, ValueError):
    """Raised when what a write was about to land on moved since the caller looked.

    The precondition ``unchanged_since`` asks for, refused **before anything is
    written** rather than half way through: a copy or a delete that stopped in
    the middle would leave the caller reasoning about what had already gone.
    See :func:`check_unchanged`, which is the one place this is raised from.

    It does not make the operation atomic. The comparison sits between a read
    and a write, so a writer racing it still wins; what it does is shrink the
    window from the length of the run to the gap between the check and the
    write. And it sees **edits, not deletions** -- a key removed since the
    watermark leaves no row to carry a timestamp.
    """


@dataclass(frozen=True, slots=True)
class Excerpt:
    """Some or all of one document's content."""

    key: str
    content: str
    format: str | None
    updated_at: str
    offset: int | None
    """Character offset within the document at which content starts, or None
    when the read was addressed in bytes. A caller gets the unit they asked
    in: converting back means decoding the prefix, which is the cost a byte
    offset exists to avoid, so it is reported unknown rather than paid for
    unasked. Both numbers for one position come from ``!contents``, where they
    are already a pair."""
    returned: int
    """Number of characters returned."""
    total: int | None
    """Total length of the document in characters, or None when the read was
    addressed in bytes and the backend would have to scan the whole document
    to count them. ``total_bytes`` is the size such a read reports."""
    next_offset: int | None
    """Where to resume in characters, or None if this excerpt reached the end
    -- and None throughout a byte-addressed read, which resumes at
    ``next_byte_offset``."""
    byte_offset: int
    """Byte offset within the document's UTF-8 at which content starts, always
    known. Where the read *actually* began: a byte offset landing inside a
    character is snapped back to that character's first byte, so this differing
    from what was asked for is normal and is not an error."""
    total_bytes: int
    """Total length of the document in UTF-8 bytes."""
    next_byte_offset: int | None
    """Where to resume in bytes, or None if this excerpt reached the end.
    Always on a character boundary, so paging by it reassembles the document
    exactly."""

    @property
    def truncated(self) -> bool:
        """Whether part of the document was left unread.

        The same fact as *either continuation is set*, named so that a caller
        deciding whether to read on does not have to know that. Reading on
        means passing back whichever continuation the read's own unit uses.

        Deliberately not ``next_offset is not None``, which it was while
        characters were the only unit: a byte-addressed read leaves that None
        while the document plainly continues, so the old definition reported
        every one of them as complete.
        """
        return self.next_offset is not None or self.next_byte_offset is not None


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
        """Whether the collection continues past this page.

        Deliberately not ``returned < total``: ``total`` describes the whole
        selection and ``returned`` only this page, so that comparison is true
        of every page but the last *and* of a page that ended exactly at the
        end. The cursor is the one that knows.
        """
        return self.next_cursor is not None


@dataclass(frozen=True, slots=True)
class Backup:
    """A copy of a store, and the evidence that it is a real one."""

    path: Path
    bytes: int
    documents: int
    """Rows copied, checked against the source rather than assumed."""
    integrity: str
    """What SQLite's own integrity_check said. 'ok' when sound."""


@dataclass(frozen=True, slots=True)
class AuditRow:
    """One stored row as its backend actually holds it, bookkeeping included.

    The reading surface deliberately does not expose ``parent``: it is a
    denormalisation, kept so that listing a level is a lookup rather than a
    scan, and a caller reading documents has no business knowing a store keeps
    one. :func:`outrage.maintenance.check` does, because a denormalisation that
    can disagree with what it was derived from is exactly what a check is for.

    So this is the audit surface and not a second way to read. It yields every
    row, metadata included, in one pass and in no promised order, and it is the
    only place a backend's own bookkeeping is named outside the backend.
    """

    key: str
    doc_key: str
    """The document this row belongs to: itself, or the document its metadata
    is attached to."""
    meta_name: str | None
    """None for a document, the metadata name otherwise."""
    parent: str
    """The parent this row is *stored* under, which is the value being checked
    and not the one :func:`outrage.keys.parse` would derive."""
    chars: int


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
class SearchCriterion:
    """One targeted condition in a document search."""

    pattern: str
    match: MatchMode
    target: SearchTarget
    meta_name: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class MatchWitness:
    """The first stored span satisfying one search criterion."""

    criterion: int
    source_key: str
    source: SearchTarget
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class DocumentMatch:
    """A selected document and the bounded evidence that selected it."""

    document: Entry
    witnesses: tuple[MatchWitness, ...]


@dataclass(frozen=True, slots=True)
class SearchPage:
    """Matches from one bounded candidate window.

    Unlike :class:`Page`, the totals describe the candidate selection rather
    than the filtered matches. Discovering a global match total would require
    searching the whole selection and defeat the scan bound.
    """

    matches: tuple[DocumentMatch, ...]
    matched: int
    matched_chars: int
    scanned: int
    total_candidates: int
    total_candidate_chars: int
    next_cursor: str | None


#: Leave what is already there and carry on. The default, because a transfer
#: that overwrites by accident cannot be undone from here.
SKIP = "skip"

#: Replace what is already there.
OVERWRITE = "overwrite"

#: Replace what is already there, unless it has changed since the caller
#: looked. :data:`OVERWRITE` narrowed by a watermark: one word covers both
#: "replace the stale copy I mean to replace" and "replace the edit somebody
#: made while I was deciding", and this is the narrower spelling of the first.
#: Needs ``unchanged_since``, which is the watermark it is measured against.
OVERWRITE_UNCHANGED = "overwrite-unchanged"

#: Stop the whole transfer at the first collision, having written what came
#: before it. What a caller wants when a collision means the wrong target.
STOP = "stop"

#: What to do about something already there, at the far end.
CONFLICTS = (SKIP, OVERWRITE, OVERWRITE_UNCHANGED, STOP)

#: The outcome recorded on a :class:`Transfer`: it crossed.
WROTE = "wrote"

#: Something was already there and :data:`SKIP` was asked for.
SKIPPED = "skipped"

#: This one could not cross, and the rest were still tried. ``reason`` says why.
FAILED = "failed"

#: Read and held for a store that is not written yet. A store written whole
#: cannot report a document as written while it goes -- nothing is written
#: until all of it is -- and calling it ``wrote`` in the meantime would be a
#: report an interrupted run made untrue. See :attr:`Store.writes_deferred`.
READ = "read"

#: The collision that ended the run, under :data:`STOP`. Reported rather than
#: swallowed, so a caller can see where the transfer stopped and why; nothing
#: after it is yielded at all.
STOPPED = "stopped"

#: Left alone under :data:`OVERWRITE_UNCHANGED` **because it changed since**
#: the watermark. Its own action rather than a :data:`SKIPPED` with a different
#: reason: a caller who gets an empty list learns the copy was clean, and one
#: who gets three keys learns exactly which three to go and look at.
CHANGED = "changed"


@dataclass(frozen=True, slots=True)
class Transfer:
    """One document crossing from one store to another, or not, and why not.

    Yielded per document rather than collected, so that a front end can print
    a transfer as it happens and an interrupted one has reported exactly what
    it did. ``action`` is what happened at the far end, and it says nothing
    about a dry run: a caller that wrote nothing knows it, and it is the only
    one that can render the difference honestly.

    ``key`` is the key **written**, which is the source's own key unless the
    copy grafted it somewhere else. ``path`` is the file behind it where
    either end keeps its documents in files, which is what makes an export
    report readable; None where neither does, and the report is key to key.

    **Why a refusal is carried and not written down.** ``reason`` is prose, and
    the walk that produces a transfer is a library: it does not know whether
    the reader spells an argument ``overwrite`` or ``--overwrite``, nor which
    of a mount table's names a key should be given. So a store's own refusal
    travels as ``error``, unrendered, and each front end turns it into the
    sentence its reader gets -- the rule ``plans/error-naming`` settled for
    every other error and that this one was still outside. ``reason`` stays for
    what has no error behind it: a symlink skipped, a key already stored, a
    document written again since the caller looked, and what the operating
    system said about a file, which has no code to carry. Exactly one of the
    two is set.
    """

    action: str
    key: str | None
    path: Path | None
    reason: str | None = None
    characters: int = 0
    error: OutrageError | None = None


def _said(transfer: Transfer) -> str | None:
    """A transfer's refusal as a sentence, for a message built inside the library.

    The one place that legitimately renders one here rather than leaving it to
    a front end: :meth:`FileStore.backup` nests the reason inside a
    ``BackupError`` of its own, and by then it is a detail of another error
    rather than something a caller can be handed unrendered.

    The defaults are the right answer and not merely the available one. A
    backup is a :class:`FileStore` copied to a file of its own, never a mount
    table, so the key a store used *is* the key to print; and every refusal
    reachable from a store-to-store copy names no argument, so there is nothing
    for a speller to spell.

    Imported where it is used, like :meth:`Store.copy_from`'s walk and for the
    same reason: :mod:`outrage.messages` is written in terms of this module.
    """
    if transfer.error is None:
        return transfer.reason
    from . import messages

    return messages.render(transfer.error)


@dataclass(frozen=True, slots=True)
class KeyRange:
    """A stretch of the key order, named by keys rather than by positions.

    Six one-sided bounds, all optional, all combined with AND, so any window
    the order supports can be described by one of these and nothing outside it
    describes a range at all. Three cut from below and three from above, and
    the three of each are the three places a cut can fall relative to a key:
    in front of the key, behind the key, and behind its whole subtree.

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
    names and *inclusive of that key's children*, because the key after the
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


#: Every key at and below the root: the default selection for a call that puts
#: no bound of its own on which part of the hierarchy it reads.
EVERYTHING = BoundedSubtree()

#: The whole of the order, bounded at neither end: the default for a call that
#: names no stretch. Distinct from :data:`EVERYTHING` on purpose -- one bounds
#: the hierarchy and the other the order, and a subtree read needs both.
UNBOUNDED = KeyRange()


def store_file(
    directory: str | os.PathLike[str],
    filename: str | os.PathLike[str] | None = None,
) -> Path:
    """The file a store keeps, from a name relative to its directory.

    One rule, in one place, for every store this process opens: the root mount
    and each ``--mount`` alike. The directory is shared infrastructure -- the
    event log and the backups sit in it -- and the file is which store within
    it, which is what lets several stores live in one directory and what a
    backend other than SQLite would vary.

    Relative, and only relative. An absolute path would make the directory a
    lie and a configuration file unmovable; ``..`` would reach outside the
    directory an operator named. Both are refused rather than resolved.

    ``filename`` of None is whatever the default backend calls its store file
    -- see :func:`default_store_file`. A store that already knows its backend
    passes that backend's name instead, so a store is never opened under a
    name a different backend chose.

    >>> store_file("/srv/project/.outrage").name
    'store.sqlite'
    >>> store_file("/srv/project/.outrage", "ref.sqlite").name
    'ref.sqlite'
    """
    relative = Path(default_store_file() if filename is None else filename)
    if not str(relative) or relative == Path("."):
        raise StoreFileError("store-file-unnamed")
    if relative.is_absolute():
        raise StoreFileError("store-file-absolute", filename=str(relative))
    if ".." in relative.parts:
        raise StoreFileError("store-file-escapes", filename=str(relative))
    return Path(directory) / relative


def resolve_directory(explicit: str | os.PathLike[str] | None = None) -> Path:
    """Locate the store directory: explicit path, then OUTRAGE_DIR, then ./.outrage.

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
    logging is on is binding the arguments - and none at all when it is off.
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
            fields = log.arguments(
                {
                    name: self._log_argument(name, value)
                    for name, value in list(bound.arguments.items())[1:]
                }
            )
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
            log.emit(
                "store",
                op=op,
                args=fields,
                ms=_ms(started),
                result=_summarise(log, result, mount_point=self.mount_point),
            )
            return result

        return wrapper  # type: ignore[return-value]

    return decorate


class Store(ABC):
    """A document store: the operations, without saying how they are kept.

    Abstract, and deliberately narrow. Everything below is expressed in keys,
    ranges, subtrees, pages and excerpts -- the vocabulary of the namespace --
    so that a backend is free to answer them however its storage is shaped.
    What a subclass adds is how a key becomes a stored thing and back; what it
    may not add is a second way of saying which keys a call is about.

    **A store is not necessarily kept in a file.** Everything about one that
    is -- where it lives, which version of its format wrote it, how it is
    copied and checked -- is :class:`FileStore` below.
    :class:`~outrage.mounts.MountedStore` is a store and not a file store: it
    keeps nothing of its own and routes to the stores behind it. The split is
    what says so, in place of the eight members it used to carry to refuse
    them.

    :func:`default_store` is what a caller uses to get one of these without
    naming a backend.
    """

    #: Whether this backend can be written at all. False says the *storage*
    #: refuses, which is not the same as a store that was mounted read-only:
    #: a mount's refusal comes off with a flag and this one does not. A caller
    #: deciding whether to offer a write reads this; a caller that writes
    #: anyway gets :class:`ReadOnlyStoreError` from the backend, since a class
    #: var nobody consulted must not be the only thing standing between a
    #: corpus and a half-written file.
    writable: ClassVar[bool] = True

    #: Whether a write here is only visible once the whole store is written.
    #: True for a store built in one pass, where nothing exists until all of it
    #: does -- so a transfer into one reports :data:`READ` rather than
    #: :data:`WROTE`, because an interrupted run wrote nothing and a report
    #: saying otherwise would be one the interruption made untrue.
    writes_deferred: ClassVar[bool] = False

    #: What this backend is called where a report or a refusal has to name it.
    #: A short lowercase word, matching the store file's extension, so that a
    #: sentence about a store and the name of its file agree.
    backend_name: ClassVar[str]

    def __init__(
        self,
        *,
        log: EventLog | None = None,
        mount_point: str | None = None,
    ) -> None:
        # The one thing every store has, file or no file. A null log rather
        # than None, so nothing below has to ask whether logging is on before
        # recording anything.
        self._log = log if log is not None else eventlog.NULL
        # A backend speaks in keys relative to itself. The mount point is only
        # how those keys are rendered in the event log; storage, routing and
        # every value returned to the caller remain unchanged.
        #
        # This being the *only* thing a store knows about its own mounting is
        # what lets a live table share a store with the table that replaces it,
        # rather than reopening the file: `MountedStore.remounted` copies a
        # surviving mount whole, so a shared store is always at the same prefix
        # and the log it writes goes on naming the keys that are there. A mount
        # at a new prefix has to take a newly opened store for the same reason.
        self.mount_point = keys.parse(_scope(mount_point)).key

    def _log_key(self, key: str | None) -> str | None:
        """A backend-local key as seen from this store's mounted namespace."""
        if not self.mount_point:
            return key
        return keys.with_prefix(self.mount_point, _scope(key))

    def _log_argument(self, name: str, value: object) -> object:
        """Translate key-bearing arguments without changing the call itself."""
        if name == "key" and isinstance(value, str | None):
            return self._log_key(value)
        if name == "cursor" and isinstance(value, str):
            return self._log_key(value)
        if isinstance(value, BoundedSubtree):
            return replace(value, key=self._log_key(value.key))
        if isinstance(value, KeyRange):
            return replace(
                value,
                **{
                    name: (
                        self._log_key(bound)
                        if (bound := getattr(value, name)) is not None
                        else None
                    )
                    for name, *_ in _BOUNDS
                },
            )
        return value

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @abstractmethod
    def close(self) -> None:
        """Release whatever this store holds open.

        Called by ``__exit__``, and safe to call more than once. What is
        released is the backend's business -- a store that holds nothing open
        has nothing to do here -- but a caller is entitled to say it is
        finished, and to have that mean something.
        """

    # -- writing ---------------------------------------------------------

    @abstractmethod
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
        """Store ``content`` at ``key``, overwriting anything already there.

        A ``?`` segment in ``key`` is replaced by a number unused among the
        children of the key enclosing it, so ``tmp/?`` writes to ``tmp/1`` in
        an empty store. Returns the key actually written, which is the only way
        the caller learns an allocated number.

        ``format`` is one of :data:`FORMATS`. Left out, it defaults to 'json'
        when the content parses as a JSON object or array, 'html' when it opens
        with a doctype or an ``<html>`` element, and 'markdown' otherwise --
        'text' is never detected and has to be asked for.

        ``title`` and ``contents`` write the ``!title`` and ``!contents``
        metadata alongside the document, in the same transaction where
        possible. They save a second call, but exist mainly because metadata
        written separately can simply be forgotten. Either may be given for a
        metadata key too, and becomes that key's own metadata: metadata is a
        namespace and a namespace can be described, so ``a/!changelog`` may
        say what its changelog is for at ``a/!changelog/!title``.

        ``encoding`` describes how ``content``, ``title`` and ``contents``
        arrived, not what is stored: 'json-string' means each is a JSON string
        literal, quotes and all, which is decoded before it is written. The
        stored documents are plain text either way, so readers are unaffected.
        Its purpose is to make damage in transit loud - see ``_decode``.

        ``updated_at`` is when the document was last written, and left out it
        is now - which is what an ordinary write means by it. It is here for
        the write that is a *copy* of a document that already exists: a
        transfer between two stores carries the timestamp across, or the copy
        says every document was written the moment it was copied and the store
        loses the one fact about a document that nothing can reconstruct. An
        ISO 8601 timestamp, normalised to UTC at second precision, which is
        what :func:`_now` writes and so what every stored value already looks
        like; a naive one is read as UTC.

        Deliberately **not** offered by the MCP tool or by ``outrage set``. A
        client writing a document is writing it now, and a stamp it could
        choose is one it could get wrong about its own work; the callers that
        legitimately restamp are copying something that was already stamped.

        Every refusal above is :meth:`_validated`'s, which an implementation
        calls before it writes anything.
        """

    def _check_writable(self, key: str) -> None:
        """Raise for a structural refusal knowable before a document is written.

        Empty for an ordinary store: a backend may need the content or the
        filesystem operation itself before it can know a write will fail. A
        mounted namespace overrides this because read-only routing is already
        settled by the key, so a dry-run transfer can report the same refusal
        as the real write instead of promising an operation that cannot land.
        """
        return None

    @classmethod
    def _validated(
        cls,
        key: str,
        content: str,
        format: str | None,
        *,
        title: str | None,
        contents: str | None,
        encoding: str | None,
        updated_at: str | None = None,
    ) -> tuple[keys.Key, str, str, str | None, str | None, str | None]:
        """What :meth:`store_document` accepts, and what it turns into.

        Returns the parsed key, the decoded content, the resolved format, the
        decoded title and contents, and the normalised timestamp - the
        arguments as they are actually written, with every refusal already
        made. A ``?`` in the key survives this: which number it becomes is read
        from the store, inside the transaction that writes it, and is the one
        part of the call that is not decidable here. So does a timestamp of
        None, because what "now" means is the storage's own answer: a row gets
        :func:`_now` and a file gets the mtime the write already gave it.

        A classmethod rather than a template method calling down into the
        backend. It leaves every implementation's control flow exactly where it
        is, while making it impossible for a backend to validate differently
        without visibly not calling this - two stores that disagreed about what
        a key or a format is would be two namespaces, which is the thing the
        split of :mod:`outrage.store` from a backend exists to prevent.

        **Call it inside the logged method.** ``_logged`` binds the caller's
        arguments before the body runs, so validation lifted out in front of
        the decorated call would leave the log recording the normalised
        arguments rather than the ones that arrived - and what the caller
        actually passed is the one thing that log is for.

        The order is guarded, not incidental: the key parses first, then the
        content is a string, then the encoding decodes it, then the format is
        detected from what the decode produced, and the metadata is checked
        last.
        A metadata key used to be refused a title here, on the grounds that
        metadata does not nest; it nests now, so every key in a metadata
        namespace takes a title like any other.
        Detecting a format before decoding would read the JSON *literal* rather
        than the document inside it. The timestamp is checked last, since it is
        about the document rather than about what it says.
        ``tests/test_store.py`` has a case per refusal.
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
            if contents is not None:
                if not isinstance(contents, str):
                    raise TypeError(f"contents must be a string, got {type(contents).__name__}")
                contents = _decode(contents, encoding, "contents")
        if format is None:
            format = _detect_format(content)
        elif format not in FORMATS:
            raise ValueError(f"format must be one of {FORMATS}, got {format!r}")
        if title is not None:
            if not isinstance(title, str):
                raise TypeError(f"title must be a string, got {type(title).__name__}")
        if contents is not None:
            if not isinstance(contents, str):
                raise TypeError(f"contents must be a string, got {type(contents).__name__}")
        return parsed, content, format, title, contents, _timestamp(updated_at)

    def copy_from(
        self,
        source: Store,
        subtree: BoundedSubtree = EVERYTHING,
        *,
        key_range: KeyRange = UNBOUNDED,
        prefix: str | None = None,
        reroot: bool = False,
        on_conflict: str = SKIP,
        unchanged_since: str | None = None,
        dry_run: bool = False,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> Generator[Transfer, None, str | None]:
        """Write every document ``source`` holds in ``subtree`` into this store.

        The one bulk operation, and it is a method on the **target** rather
        than a function over a pair, because the target is what knows how it
        is written: a database takes a document at a time, and a file written
        whole takes all of them and writes once. A caller asks for the same
        transfer either way and each store answers it appropriately, which is
        what an export, an import, a repack and a backup all turn out to be.

        ``source`` is any :class:`Store` -- a database, a directory of files,
        or a mount table presenting several of them as one namespace, which is
        what makes a copy *out of* a table possible at all. ``subtree`` and
        ``key_range`` bound what crosses exactly as they bound a read, so a
        copy of part of a store is the same selection as a listing of it.
        ``prefix`` grafts what crosses under a key here, and left out, each
        document keeps the key it had. ``reroot`` changes what the graft keeps:
        the subtree's own key is stripped first, so ``a/b`` copied to ``tmp``
        lands at ``tmp`` rather than at ``tmp/a/b`` and everything below it
        keeps its position below that. Grafting the whole key is right for an
        archive and is the default; re-rooting is the only spelling that says
        "these documents now live at another key", which is what a caller
        moving a subtree needs. Which pairs of keys are safe to stream between
        differs between the two -- :func:`outrage.bulk.overlapping` is the rule,
        and the front ends apply it.

        Metadata crosses as the keys it is: a copy that left every ``!title``
        behind would produce a store nothing can be surveyed by. So does each
        document's ``updated_at``, which is what makes this a copy rather than
        a restamping -- see :meth:`store_document`.

        ``limit`` bounds how many documents cross, and the generator returns
        the source key of the last one so that ``cursor`` can pick the copy up
        there. That pair is what a front end returning one value needs -- a
        tool result cannot stream, and a copy of a large subtree cannot be one
        answer -- and the cursor is a *source* key, which is why it is returned
        rather than read off the last transfer. See :func:`outrage.bulk.copied`.

        Yields a :class:`Transfer` per document as it goes, so that a front end
        can report the transfer while it happens and an interrupted one has
        reported exactly what it did. ``on_conflict`` decides what happens to a
        key already here, one key at a time: :data:`SKIP` leaves it,
        :data:`OVERWRITE` replaces it, :data:`OVERWRITE_UNCHANGED` replaces
        what has not moved since ``unchanged_since`` and reports the rest as
        :data:`CHANGED`, and :data:`STOP` ends the run at the first collision
        having kept what it already wrote.

        ``unchanged_since`` is a watermark -- when the caller looked -- and it
        buys two things. Before anything crosses, the keys this copy is about
        to land on are asked whether any of them moved since; if one did the
        run is refused having written nothing (:func:`check_unchanged`). Then
        under :data:`OVERWRITE_UNCHANGED` each collision is measured against it
        again, which is what catches a write made between the check and the
        copy reaching that key. A copy left unwatermarked behaves exactly as it
        always has.

        The default implementation reads each document and writes it here,
        which is every store's answer until it has a better one. A backend
        with a bulk way in overrides this; what it may not do is change what
        the transfer *means*, which is why the report is the same either way.

        The walk itself is :mod:`outrage.bulk`'s, imported where it is used
        rather than at the top of this module: a store's own reads are pages,
        deliberately, and the caller that legitimately wants all of it lives
        there. A copy is that caller.
        """
        from . import bulk

        return (
            yield from bulk.copied(
                source,
                self,
                subtree,
                key_range=key_range,
                prefix=prefix,
                reroot=reroot,
                on_conflict=on_conflict,
                unchanged_since=unchanged_since,
                dry_run=dry_run,
                cursor=cursor,
                limit=limit,
            )
        )

    def located(self, key: str, format: str | None = None) -> Path | None:
        """The file this store keeps ``key`` in, when there is one to name.

        None by default, and that is not an omission: a row in a database has
        no file of its own, and a store answering with the file the *whole*
        corpus is in would be naming something a caller cannot open expecting
        one document.

        For reporting rather than for reading -- nothing here opens what it
        returns. A copy into a directory of files is worth reading as key to
        path, and the store on the far end is the only thing that knows which
        path, so :class:`Transfer` carries it and this is where it comes from.
        """
        return None

    @abstractmethod
    def delete(
        self,
        key: str,
        recursive: bool = False,
        *,
        key_range: KeyRange = UNBOUNDED,
        unchanged_since: str | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        """Delete ``key``, returning the keys actually removed.

        ``dry_run`` reports that same list without removing any of it. It
        belongs here rather than in a front end because every backend already
        selects the keys before it takes them: a preview computed anywhere else
        is a second spelling of the selection, and the way that fails is a
        preview which quietly disagrees with the delete it previews. The
        watermark is checked either way, so a preview of a delete that would be
        refused is refused rather than listing keys it would never take.

        A document key takes its metadata with it -- the whole metadata
        subtree, since a document and its metadata are one unit and contiguous
        in the order. Descendants are removed only when ``recursive`` is set,
        so a mistyped key cannot silently discard a whole subtree. Note that
        storing an empty document is not a deletion.

        **A metadata key is a container like any other.** Deleting one takes
        what is inside it, so ``a/!changelog`` with notes below refuses without
        ``recursive`` rather than quietly discarding them. It is only a
        document's *own* delete that carries metadata away unasked, and that is
        because the metadata has no meaning once the document is gone.

        ``key_range`` bounds which keys are in scope, exactly as it does for a
        read: a delete that steps over a mounted store's stretch of the order
        needs to say so in the same vocabulary a traversal does, or it removes
        keys the mount has made unreachable and reports them as deleted. Those
        keys read back fine from the mount on the very next call, which is the
        defect this argument exists for.

        It bounds *both* halves. The key itself and its metadata are as capable
        of lying inside a shadowed stretch as any descendant is.

        ``unchanged_since`` is a precondition rather than a bound: the keys
        this delete would take are asked whether any of them moved since the
        caller looked, and the whole delete is refused if one did. **Refused
        rather than narrowed**, because a delete is one call and a partial
        subtree is the outcome nobody asked for -- a caller told which key
        moved can look at it and run the delete again, and a caller handed half
        a subtree cannot put it back. See :func:`check_unchanged`, and note
        that what it cannot see is a key somebody else *deleted* since.
        """

    @abstractmethod
    def descendant_count(
        self, key: str, *, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False
    ) -> int:
        """How many stored keys lie strictly below ``key``.

        Metadata counts: it is stored, and a caller deciding whether a subtree
        is empty is asking about everything that would have to go.

        **A metadata key has a real subtree of its own**, and this counts it.
        ``a/!changelog`` holding twenty notes reports twenty, exactly as a
        document holding twenty children does, which is what makes the delete
        below refuse it without ``recursive``.

        Exists so a caller can report what a non-recursive delete left behind:
        without it, deleting a key that holds nothing itself is indistinguishable
        from deleting a key that does not exist.

        What it leaves out is ``key``'s **own** metadata unit, because a plain
        delete takes that with the key -- so the default answers *what would a
        plain delete keep*. **``whole_subtree`` asks the other question**:
        everything strictly below ``key``, that unit included, which is what a
        *recursive* delete takes and what :func:`outrage.bulk.walk` reports.
        A caller previewing a recursive delete needs the second, and answering
        it with the first prints a remainder short by the unit -- negative,
        once the preview reaches past the ordinary children.
        See :func:`outrage.keys.meta_range`.

        ``key_range`` bounds it for the reason it bounds ``delete``: a count
        that includes keys a mount has made unreachable tells a caller to pass
        ``recursive`` to remove keys that are not there to remove.
        """

    @_logged("latest_change")
    def latest_change(
        self, key: str, *, key_range: KeyRange = UNBOUNDED, whole_subtree: bool = False
    ) -> str | None:
        """The newest ``updated_at`` below ``key``, or None where nothing is.

        The aggregate a write precondition asks: one value whatever the size of
        the subtree, so "has anything here moved since I looked" costs a query
        rather than a walk. The selection is :meth:`descendant_count`'s exactly
        -- strictly below ``key``, less the metadata unit a plain delete takes
        with it, and ``whole_subtree`` keeps that unit -- so the two answer
        about the same set of keys and a caller can hold one meaning for both.

        **Metadata counts**, as it does there and for the same reason: a
        ``!title`` written since the watermark is a change to the subtree, and
        an aggregate with a second unstated meaning costs more than it saves.

        **What it cannot see is a deletion.** The row that would carry the
        timestamp is the row that has gone, so the newest change in a range
        says nothing about what was *removed* from it. A guard built on this
        covers edits and no more; when an archive exists, asking it the same
        question over the same range is what answers the other half.

        Timestamps are normalised to seconds (:meth:`store_document`), so a
        write inside the same second as a watermark is invisible to a
        comparison against one. That is the weakness ``content_sha256`` exists
        to avoid elsewhere, inherited here deliberately: a watermark over a
        whole subtree has no single content to hash.

        The default implementation walks the subtree and takes the maximum,
        which is every store's answer until it has a better one: a database
        has ``max()``, a sorted file has a row range, and a directory of files
        has the walk this does.
        """
        from . import bulk

        scope = keys.parse(key).key
        lo, hi = keys.meta_range(scope)
        inside = _within(key_range)
        newest: str | None = None
        for entry in bulk.walk(self, scope):
            # An implicit container holds no document and so carries no
            # timestamp; it is a position in the order rather than a change to
            # anything, and the key beneath it that *is* stored is walked too.
            if entry.updated_at is None:
                continue
            if not whole_subtree and lo <= entry.key < hi:
                continue
            if not inside(keys.sort_form(entry.key)):
                continue
            if newest is None or entry.updated_at > newest:
                newest = entry.updated_at
        return newest

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Whether ``key`` itself holds a document.

        Not the same question as whether anything is below it: a bulk import
        asks this per file to decide about one key, and a container that holds
        nothing itself is free for a document to be written to.

        Deliberately cheaper than a read, since the answer is wanted for every
        file in an import and the content is not.
        """

    # -- reading ---------------------------------------------------------

    @abstractmethod
    def level_entry(self, key: str) -> Entry | None:
        """How ``key`` appears in its parent's listing, or None if it does not.

        The same three answers :meth:`list_keys` gives about one key without
        listing the level to find it: a stored document, an implicit key that
        exists only because something lies beneath it, or nothing at all.

        Asked by a caller that has to reconcile this store's level with keys
        from somewhere else and must not count the same position twice. A
        cheaper pair of questions -- does the key exist, does it have
        descendants -- gets one corner wrong: metadata sits *at* a key rather
        than below it, so a key holding only metadata has no document and no
        descendants and still appears in the listing.
        """

    @abstractmethod
    def retrieve_document(
        self,
        key: str,
        *,
        offset: int = 0,
        byte_offset: int | None = None,
        length: int | None = None,
        pattern: str | None = None,
        occurrence: int = 0,
        max_chars: int = DEFAULT_MAX_CHARS,
    ) -> Excerpt:
        """Read the content stored at ``key``.

        ``pattern`` is a literal substring, not a regular expression; when
        given, the read starts at its ``occurrence``-th appearance at or after
        the offset. The result is capped at ``length`` or ``max_chars``,
        whichever is smaller, and carries a continuation offset.

        ``offset`` counts characters and ``byte_offset`` counts UTF-8 bytes of
        the same document. Both are positions, so giving both is refused; a
        byte offset landing inside a character reads from that character's
        first byte, and the excerpt says where it actually began.

        **Every backend accepts a byte offset and returns identical content
        for it.** Only the cost differs -- one that can seek does, one that
        cannot converts and slices -- and that contract is what makes a byte
        offset something a caller can carry between stores, and out of the
        store altogether to a file :func:`~outrage.bulk` exported.
        """

    @abstractmethod
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
        needed; a range would have to be honoured by every part of a level's
        answer, for no caller that exists.
        """

    def last_child(self, key: str) -> str | None:
        """The final segment of the last key immediately below ``key``.

        What ``?last`` resolves to, and the store half of
        :func:`outrage.keys.resolve_last` -- so ``notes/?last`` names whatever
        this returns for ``notes``. None when nothing is below ``key``, which
        is what the caller turns into a refusal.

        **Last in the order a listing walks**, which is :func:`sort_form`'s,
        so a level of numbers gives the highest number and not the highest
        spelling. Implicit keys count: a container holding only descendants is
        as much the last key at that level as a document is, and ``?last``
        exists to name the newest thread of work whether or not somebody
        wrote a document at the top of it.

        Metadata does not count, **at whatever level this stands**. ``?last``
        stands where an ordinary segment goes -- it can no more resolve to
        ``!title`` than ``?`` can allocate one -- so a level holding a document
        and its title has one child here. Inside a metadata namespace the same
        rule applies to that level: ``a/!changelog/?last`` is the newest note
        kept in the changelog and never the changelog's own ``!title``.

        Concrete rather than abstract, on :meth:`list_keys`, because it asks
        nothing a backend answers differently. **It reads the whole level to
        take its last row**, which is one round trip at the sizes a level
        actually reaches and the wrong shape if one ever holds thousands: the
        fix then is an override selecting one row in descending order, not a
        second definition of what "last" means.
        """
        level = self.list_keys(key)
        names = [
            name
            for entry in level.items
            if not (name := entry.key.rpartition(keys.DELIMITER)[2]).startswith(keys.META_PREFIX)
        ]
        return names[-1] if names else None

    @abstractmethod
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
        and the two hold together: a key is returned when it is in the subtree
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

    def find_documents(
        self,
        subtree: BoundedSubtree = EVERYTHING,
        *,
        criteria: Sequence[SearchCriterion],
        combine: SearchCombination = "any",
        key_range: KeyRange = UNBOUNDED,
        cursor: str | None = None,
        scan_limit: int | None = None,
    ) -> SearchPage:
        """Search one bounded window of documents and their direct metadata.

        The returned cursor is the last candidate examined, not the last
        match. A page can therefore contain no matches and still carry a
        cursor; callers continue until it is ``None``.

        Concrete here, in terms of the ordinary read contract, so every
        backend and :class:`~outrage.mounts.MountedStore` shares one baseline
        implementation. A backend override is only an optimization and can be
        checked against this method as its oracle.
        """
        prepared = _search_matchers(criteria, combine, scan_limit)
        candidates = self.get_documents(
            subtree,
            key_range=key_range,
            cursor=cursor,
            max_chars=1,
            limit=scan_limit,
        )
        wants_documents = any(criterion.target == "document" for criterion, _ in prepared)
        wants_metadata = any(criterion.target == "metadata" for criterion, _ in prepared)
        matches: list[DocumentMatch] = []

        for candidate in candidates.items:
            body = read_all(self, candidate.key).content if wants_documents else None
            metadata = _search_metadata(self, candidate.key, prepared) if wants_metadata else {}
            witnesses: list[MatchWitness] = []

            for index, (criterion, matcher) in enumerate(prepared):
                witness = None
                if criterion.target == "document":
                    span = matcher(body or "")
                    if span is not None:
                        witness = MatchWitness(index, candidate.key, "document", *span)
                else:
                    for source_key, content in metadata.items():
                        name = source_key.rpartition(keys.DELIMITER)[2][len(keys.META_PREFIX) :]
                        if criterion.meta_name is not None and name not in criterion.meta_name:
                            continue
                        span = matcher(content)
                        if span is not None:
                            witness = MatchWitness(index, source_key, "metadata", *span)
                            break
                if witness is not None:
                    witnesses.append(witness)

            selected = bool(witnesses) if combine == "any" else len(witnesses) == len(prepared)
            if selected:
                matches.append(
                    DocumentMatch(
                        document=Entry(
                            key=candidate.key,
                            kind="document",
                            size=candidate.total,
                            format=candidate.format,
                            updated_at=candidate.updated_at,
                        ),
                        witnesses=tuple(witnesses),
                    )
                )

        return SearchPage(
            matches=tuple(matches),
            matched=len(matches),
            matched_chars=sum(match.document.size or 0 for match in matches),
            scanned=candidates.returned,
            total_candidates=candidates.total,
            total_candidate_chars=candidates.total_chars,
            next_cursor=candidates.next_cursor,
        )

    @abstractmethod
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

        A document carrying none of the names appears nowhere in the ordering
        the survey walks, so it has no position in it either. One is synthesised:
        where it *would* have sorted had it carried the name, which is exactly
        the position of ``doc/!name``. That is part of the contract rather than
        an implementation detail -- it is what decides which window a document
        is counted in, and so what makes a caller's windows tile.
        """

    @abstractmethod
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

        ``key_range`` narrows the subtree exactly as it narrows a survey, and
        for the same reason: the two have to be askable over one stretch of the
        store, and to agree about what was in range, or they stop describing
        the same one.
        """


class FileStore(Store):
    """A store kept in a file of its own, and everything that follows from it.

    The half of a store that needs somewhere on disk to answer from: where it
    lives, which version of its format wrote it, how it is copied, and what a
    check can say about the storage rather than about the keys. Every backend
    is one of these. :class:`~outrage.mounts.MountedStore` is not, and that is
    the whole reason the two are separate classes -- a table that keeps nothing
    cannot answer any of it, and saying so by *not having* the members is
    better than having eight that exist to refuse.

    Two things are settled here rather than per backend, because they are the
    same question whatever the storage is: **where the file lives**, which
    :func:`store_file` decides from a directory and a name relative to it, and
    **that a store is a file inside a directory** rather than a directory of
    its own, so that several stores can share one.

    A backend whose "file" is a *directory* is still one of these:
    :class:`~outrage.store_files.FilesystemStore` sets :attr:`path` to the tree
    and :attr:`directory` to its parent, so a backup of it lands beside the
    corpus rather than inside it. The name means the same thing -- the one
    place on disk this store *is* -- and only its kind differs.
    """

    #: What this backend calls its store file when a caller names none. Set by
    #: every concrete backend, and the only thing about the file a backend
    #: decides: that it *is* a file inside a directory is settled above, by
    #: :func:`store_file`. :func:`default_store_file` is how the rest of the
    #: package asks for it without naming a backend to ask.
    default_filename: ClassVar[str]

    #: The version of its own on-disk format this build writes. Compared
    #: against :attr:`stored_format_version` by :func:`outrage.maintenance.check`,
    #: which is why the comparison is written once rather than per backend --
    #: "written by a newer outrage than this" is the same fault whatever wrote it,
    #: even though each backend records the number somewhere different.
    format_version: ClassVar[int]

    def __init__(
        self,
        directory: str | os.PathLike[str] | None = None,
        *,
        filename: str | os.PathLike[str] | None = None,
        log: EventLog | None = None,
        mount_point: str | None = None,
    ) -> None:
        super().__init__(log=log, mount_point=mount_point)
        # The directory holding this store, and the shared infrastructure
        # beside it -- the event log and the backups.
        self.directory = resolve_directory(directory)
        # The file this store keeps its documents in, inside that directory.
        # Settled before the directory is made, so a store file that will be
        # refused leaves nothing behind to explain. A caller who named no file
        # gets *this* backend's default rather than the package's, so a store
        # constructed directly is never opened under another backend's name.
        self.path = store_file(
            self.directory,
            type(self).default_filename if filename is None else filename,
        )
        self.directory.mkdir(parents=True, exist_ok=True)
        # A store file may name a subdirectory, and nothing else creates it.
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def in_directory(
        cls,
        directory: str | os.PathLike[str] | None = None,
        *,
        filename: str | os.PathLike[str] | None = None,
        extensions: str | None = None,
        log: EventLog | None = None,
        mount_point: str | None = None,
    ) -> Self:
        """This backend's store, named as a file inside a store directory.

        The constructor, for every backend whose store *is* a file: the
        signature above is already the directory-plus-name one. It is a
        classmethod of its own so that a backend whose store is a **directory**
        has somewhere to spell the same thing --
        :class:`~outrage.store_files.FilesystemStore` takes the tree itself,
        because an export target is a path a person typed, and a mount is not:
        a mount is a name inside ``--dir`` like every other store, and
        :func:`store_file` is the rule for both.

        :func:`default_store` opens every store through here, so which of the
        two shapes a backend has stays the backend's business rather than
        something a mount table has to know.

        ``extensions`` is one backend's option reaching the one place every
        backend is opened through. It says how a file name and a key segment
        line up, which is a question only a store kept as a *tree* has --
        :class:`~outrage.store_files.FilesystemStore` overrides this and takes
        it, and every other backend arrives here and **refuses** it. Refused
        rather than ignored, because that is the rule the option grammar it
        comes from already follows: an option that silently did nothing is the
        failure a mount configuration is least able to notice, and a caller who
        wrote ``extensions=keep`` on a database meant something by it.
        """
        if extensions is not None:
            raise BackendError(
                "backend-takes-no-extensions",
                backend=cls.backend_name,
                filename="" if filename is None else str(filename),
                extensions=extensions,
            )
        return cls(directory, filename=filename, log=log, mount_point=mount_point)

    def opened_at(self, path: Path) -> Self:
        """Another store of this class, kept at ``path``.

        The one thing a copy of a store cannot work out for itself. Every
        backend's constructor takes a directory and a name within it, so the
        default splits ``path`` that way; a backend whose "file" is a directory
        overrides this rather than being spelled as a special case here.

        Whatever else distinguishes *this* store from a bare one travels across
        in the override, because only the backend knows what that is -- and a
        copy opened under a different policy from the store it was copied from
        would compare short against it for a reason that is not a fault.
        """
        return type(self)(path.parent, filename=path.name)

    # -- maintenance -----------------------------------------------------

    def backup(
        self,
        destination: str | os.PathLike[str] | None = None,
        *,
        overwrite: bool = False,
    ) -> Backup:
        """Copy the store to ``destination``, and verify the copy.

        Both halves, and both here rather than in a caller: only the backend
        knows what a complete copy of itself is, and a copy that opens cleanly
        is not evidence of one. The result carries what the check found, so a
        caller can report a backup it did not have to trust.

        ``destination`` may name a file or a directory, and defaults to a
        timestamped name under ``backups/`` in the store directory, taking the
        store file's own extension. Missing parents are created. An existing
        file is refused unless ``overwrite``.

        **This is the copy every store can make of itself**: open a fresh one
        of the same class at the target and :meth:`~Store.copy_from` this one
        into it, which carries every document, its format, its metadata and its
        ``updated_at``. A backend with a native copy of its file overrides
        this and should -- :class:`~outrage.store_sqlite.SqliteStore` must,
        because the file alone is not the store there, and
        :class:`~outrage.store_parquet.ParquetStore` does because a byte copy
        is faster and exact. What a backend may not do is skip the verifying.

        The copy is written through a store that is then closed, and reopened
        to check it: what a still-open handle says about a file is what it
        believes it wrote, which is the thing in question.
        """
        target = self.backup_path(destination, overwrite=overwrite)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Removed rather than written over: what is there need not be the same
        # shape as what is going there, and a copy that landed *inside* a
        # directory left behind would be a backup nothing could open.
        _clear(target)

        try:
            with self.opened_at(target) as copy:
                for transfer in copy.copy_from(self, on_conflict=OVERWRITE):
                    if transfer.action in (FAILED, STOPPED):
                        raise BackupError(
                            "backup-unwritable",
                            target=str(target),
                            reason=f"{transfer.key}: {_said(transfer)}",
                        )
        except OSError as exc:
            _clear(target)
            raise BackupError("backup-unwritable", target=str(target), reason=str(exc)) from exc

        return self.verified_backup(target)

    def verified_backup(self, target: Path) -> Backup:
        """Read the copy at ``target`` back, and prove it holds what this does.

        Every key, compared, rather than a count of them: a copy that lost one
        document and gained another counts the same and is not a backup.
        :meth:`~FileStore.audit_rows` is what both ends are asked, because it is
        the one read that yields *every* row a store holds, metadata included,
        and a backup missing every ``!title`` would open cleanly and be
        useless.

        Public because a backend with its own copy still owes the same
        evidence, and the two that have one answer it their own way -- from
        row counts and a version their storage records natively, which is
        cheaper and says more. This is the answer for a backend with nothing
        better to ask.

        ``integrity`` is ``"ok"``: the keys agreeing *is* the check here, and
        there is no second opinion to report. A backend whose storage has one
        says what it said.
        """
        mine = sorted(row.key for row in self.audit_rows())
        with self.opened_at(target) as copy:
            theirs = sorted(row.key for row in copy.audit_rows())
        if mine != theirs:
            lost = set(mine) - set(theirs)
            gained = set(theirs) - set(mine)
            raise BackupError(
                "backup-incomplete",
                target=str(target),
                differs=f"{len(lost)} keys missing, {len(gained)} unexpected",
            )
        return Backup(
            path=target,
            bytes=_stored_bytes(target),
            documents=len(theirs),
            integrity="ok",
        )

    def backup_path(self, destination: str | os.PathLike[str] | None, *, overwrite: bool) -> Path:
        """Settle where the copy goes, and refuse the destinations that destroy.

        Public so that a caller can report the destination, and hit the same
        refusals, without writing anything - which is what ``--dry-run`` needs.

        The default name takes the store file's own extension rather than a
        fixed one, so a backup of a store is recognisably the same kind of
        thing as the store. Here rather than on a backend because the two
        refusals are the point of it, and neither is about storage: a
        destination that is the store itself destroys what it was copying, and
        one that already exists destroys whatever was there.
        """
        default_name = f"store-{time.strftime(BACKUP_STAMP)}{self.path.suffix}"
        if destination is None:
            target = self.directory / BACKUP_DIR_NAME / default_name
        else:
            target = Path(destination).expanduser()
            if target.is_dir():
                target = target / default_name

        target = target.resolve()
        if target == self.path.resolve():
            raise BackupError("backup-is-the-store", target=str(target))
        if target.exists() and not overwrite:
            raise BackupError("backup-exists", target=str(target))
        return target

    @property
    @abstractmethod
    def stored_format_version(self) -> int:
        """The format version recorded *in the file this store opened*.

        Not :attr:`format_version`, which is what this build writes. The two
        differing is the whole question: below, and the file predates this
        build; above, and something newer wrote it. Each backend records the
        number its own way -- SQLite in ``PRAGMA user_version``, parquet in the
        file's key-value metadata -- and this is the one name the difference
        does not reach.
        """

    @abstractmethod
    def audit_rows(self) -> Iterator[AuditRow]:
        """Every row this store holds, bookkeeping included, in one pass.

        For :func:`outrage.maintenance.check` and nothing else -- see
        :class:`AuditRow` for why the reading surface does not offer this. One
        pass rather than a query per check, because the checks that use it want
        the same rows for different questions and a store large enough to be
        worth checking is large enough for a second pass to be felt.

        Order is not promised. Nothing auditing rows one at a time depends on
        it, and a backend held in key order should not have to pay to prove it.
        """

    @abstractmethod
    def check_file(self, report: Report) -> None:
        """Add what only this backend can say about its own file.

        Called by :func:`outrage.maintenance.check` once the checks that any
        backend can answer have run. Those are about rows and keys; this is
        about *storage* -- whether SQLite still considers the database sound,
        how much of it is sitting in the write-ahead log, whether a parquet
        file is still in the sort order every read of it bisects.

        Fills in :attr:`~outrage.maintenance.Report.details` with the numbers
        worth printing whether or not anything is wrong, and appends to
        ``problems`` for anything that is.
        """

    @abstractmethod
    def repair(self) -> list[Repaired]:
        """Fix what :meth:`check_file` found and this backend can act on.

        Returns what was actually done, which may be nothing: a backend whose
        storage cannot get into a repairable state returns an empty list, and
        that is an honest answer rather than a silence. It is not the same
        answer as :meth:`check_file` finding nothing -- one says there is
        nothing that *could* need repairing, the other that nothing does.

        Nothing here may lose a document. A repair moves bytes about; one that
        could discard content would need a backup taken first, and no backend
        offers such a repair.
        """


#: Every backend, by the name it answers to, and the class behind it. The
#: **single place** the package decides which storage a store is kept in.
#:
#: A registry rather than a ``backend=`` argument threaded through the server,
#: the command line and the mount table, because a store is already addressed
#: as a *file* and a backend already names its own -- so if a backend names its
#: file, the file can name the backend, and ``--mount-ro ref=python.parquet``
#: needs no new grammar to say what it obviously means. The name is
#: :attr:`FileStore.backend_name`, which is what a report or a refusal already
#: calls it, so ``type=files`` in a mount spec is not a second word for
#: anything.
#:
#: Named by module and class rather than holding the classes, because each
#: backend is written in terms of this module and importing one at module scope
#: would be a cycle. :func:`_backend_for` resolves an entry on use.
_BACKENDS: dict[str, tuple[str, str]] = {
    "sqlite": (".store_sqlite", "SqliteStore"),
    "parquet": (".store_parquet", "ParquetStore"),
    "files": (".store_files", "FilesystemStore"),
}

#: The extension each backend claims, as the name it resolves to. A store file
#: names its own backend, which is what keeps a mount spec free of one.
#:
#: **Not every backend is here, and that is the point of a mount option.** A
#: directory of files has no extension to read, so ``files`` is nameable and
#: not inferable -- see :func:`_backend_for` and
#: ``outrage.mounts.parse_spec``.
_BY_EXTENSION: dict[str, str] = {
    ".sqlite": "sqlite",
    ".parquet": "parquet",
}

#: The backend a store is kept in when nobody says otherwise, and so the one an
#: unrecognised extension falls back to. See :func:`_backend_for` for why the
#: fallback is a fallback rather than a refusal.
DEFAULT_BACKEND = "sqlite"


def _backend() -> type[FileStore]:
    """The backend class this build uses when nobody names one."""
    return _backend_for(None)


def _backend_for(
    filename: str | os.PathLike[str] | None,
    backend: str | None = None,
) -> type[FileStore]:
    """Which backend keeps a store called ``filename``.

    ``backend`` names one outright, as a mount option does; ``None`` reads it
    from the file. ``filename`` of None with no ``backend`` is the default.
    Everything else is read from the extension: ``ref.parquet`` is a parquet
    store and ``ref.sqlite`` is a SQLite one.

    **An unrecognised extension is the default backend, not an error.** A store
    file has always been free to be called anything -- ``ref.db`` and
    ``monday.sqlite`` alike -- and turning every unclaimed name into a refusal
    would break configurations that named a file before any backend claimed an
    extension. So the registry recognises the names a backend has claimed; it
    does not decide which names are allowed. A name that means to be parquet
    and is spelled ``ref.parq`` opens as SQLite, which is the cost of that, and
    the store it opens is empty rather than wrong.

    **A name that was asked for is refused, and for the same reason.** An
    extension is a guess at what somebody meant and a ``type=`` is what they
    said, so a misspelling of one falls back and a misspelling of the other
    cannot: a mount that silently opened under a backend nobody named would
    read as a store that is simply empty.

    The import failing is not a bug here: pyarrow is an optional extra, so a
    ``.parquet`` mount on an install without it has to say so in a sentence
    rather than raise ``ModuleNotFoundError`` at whoever is watching.
    """
    if backend is not None:
        if backend not in _BACKENDS:
            raise BackendError(
                "backend-unknown",
                backend=backend,
                filename="" if filename is None else str(filename),
                known=sorted(_BACKENDS),
            )
        name = backend
    elif filename is None:
        name = DEFAULT_BACKEND
    else:
        name = _BY_EXTENSION.get(Path(filename).suffix, DEFAULT_BACKEND)
    module_name, class_name = _BACKENDS[name]
    try:
        module = importlib.import_module(module_name, __package__)
    except ImportError as exc:
        raise BackendError(
            "backend-unavailable",
            filename=str(filename),
            backend=class_name,
            reason=str(exc),
        ) from exc
    resolved: type[FileStore] = getattr(module, class_name)
    return resolved


def backend_names() -> tuple[str, ...]:
    """Every backend a store may be opened as, by name.

    What a ``type=`` option may say, for the front ends that document it and
    the refusal that lists it -- one answer from the registry rather than a
    list retyped in each place that needs to name them.
    """
    return tuple(sorted(_BACKENDS))


def default_store_file() -> str:
    """What the default backend calls its store file.

    A store is addressed as a *file* within a directory rather than as a
    directory of its own, so that one directory can hold several stores side by
    side and so that a backend which is not SQLite can be named by the file it
    keeps. That rule is this module's and does not vary; *which* name is the
    backend's, and asking for it through here is what keeps the front ends from
    having to name one to print a default.

    It is the root mount when ``--root-mount`` names nothing else, and the file
    a bare ``--dir`` opens.
    """
    return _backend().default_filename


def default_store(
    directory: str | os.PathLike[str] | None = None,
    *,
    filename: str | os.PathLike[str] | None = None,
    backend: str | None = None,
    extensions: str | None = None,
    log: EventLog | None = None,
    mount_point: str | None = None,
) -> FileStore:
    """A store of the backend this build opens when nobody names one.

    ``filename`` of None means whatever that backend calls its store file.
    Any other name picks the backend that claims its extension, so a caller
    holding a mount's file name opens the right storage without naming one --
    see :func:`_backend_for`.

    ``backend`` names one instead of reading it from the file, which is what a
    mount's ``type=`` option and ``--store FILE,type=NAME`` reach: a directory
    of files has no extension for the rule above to read, so the only way to
    say ``files`` is to say it. Opening goes through
    :meth:`FileStore.in_directory` rather than the constructor, because that is
    the one thing a backend whose store is a directory spells differently.

    ``extensions`` is the mount option of the same name, and is carried here
    for the same reason ``backend`` is: it is what an argument said, and the
    backend it reaches either takes it or refuses it --
    :meth:`FileStore.in_directory` is where that happens.
    """
    return _backend_for(filename, backend).in_directory(
        directory,
        filename=filename,
        extensions=extensions,
        log=log,
        mount_point=mount_point,
    )


@contextmanager
def open_store(
    directory: str | os.PathLike[str] | None = None,
    *,
    filename: str | os.PathLike[str] | None = None,
    backend: str | None = None,
    extensions: str | None = None,
    log: EventLog | None = None,
    mount_point: str | None = None,
) -> Iterator[FileStore]:
    """Open a store, closing it on exit."""
    store = default_store(
        directory,
        filename=filename,
        backend=backend,
        extensions=extensions,
        log=log,
        mount_point=mount_point,
    )
    try:
        yield store
    finally:
        store.close()


def read_all(store: Store, key: str, **kwargs: Any) -> Excerpt:
    """Read a whole document, following ``next_offset`` until there is no more.

    A function beside the store rather than a method on it, deliberately.
    Whether the *library* should stop handing out silent partial documents is
    an open design question, and no answer has been chosen. This settles
    only what the command line does, which is a narrower question with an
    obvious answer: a person redirecting a document to a file wants the
    document, and a slice is available by asking for one.

    Asked for the whole document, the result reports it with ``next_offset`` of
    ``None``, so a caller cannot tell it apart from a document that fitted.
    That is the point. Asked for a ``length``, the result stops there and
    carries a continuation offset, exactly as a single capped read does.
    """
    first = store.retrieve_document(key, **kwargs)
    if not first.truncated:
        return first

    max_chars = kwargs.get("max_chars", DEFAULT_MAX_CHARS)
    wanted = kwargs.get("length")
    # Resumed in the unit the caller addressed it in, which is the unit that
    # has a continuation: a byte-addressed read carries no character offset to
    # page by, and paging it by one would start the second slice somewhere
    # else entirely.
    in_bytes = first.offset is None
    resume: Callable[[Excerpt], int | None] = (
        (lambda part: part.next_byte_offset) if in_bytes else (lambda part: part.next_offset)
    )

    parts = [first.content]
    taken = first.returned
    last = first
    position = resume(first)
    while position is not None and (wanted is None or taken < wanted):
        # A pattern is spent by the first read: it seeks, and seeking again
        # from the new start would find the next occurrence instead of
        # continuing. A length is not spent, because it bounds the whole read
        # rather than each slice -- re-applying it per slice returns more than
        # was asked for, and dropping it returns the entire document.
        cap = max_chars if wanted is None else min(max_chars, wanted - taken)
        where = {"byte_offset": position} if in_bytes else {"offset": position}
        last = store.retrieve_document(key, max_chars=cap, **where)
        parts.append(last.content)
        taken += last.returned
        position = resume(last)

    content = "".join(parts)
    return replace(
        first,
        content=content,
        returned=len(content),
        next_offset=last.next_offset,
        next_byte_offset=last.next_byte_offset,
    )


def check_unchanged(
    opened: Store,
    key: str,
    unchanged_since: str | None,
    *,
    action: str = "write over",
    subtree: bool = True,
    key_range: KeyRange = UNBOUNDED,
) -> None:
    """Refuse, before anything is written, if ``key`` moved since the watermark.

    The pre-pass every ``unchanged_since`` gets: one question to the range a
    run is about to write over or delete, asked while nothing has happened yet.
    That converts "half done, then refused" into "refused having written
    nothing", which is the difference the argument exists for. It does not make
    the operation atomic -- see :class:`ChangedSinceError` -- and it costs one
    aggregate per store rather than a walk, which is what
    :meth:`Store.latest_change` is for.

    ``action`` is what the caller was about to do, as the verb the refusal is
    built on -- ``delete`` for one, and the default for a copy. A fact rather
    than a sentence, exactly as :class:`ReadOnlyStoreError` carries one: a
    delete refused with "this would land on work done since" is the copy's
    sentence read out at the wrong operation.

    ``subtree`` is what a recursive run asks and a single-key one does not: a
    plain delete takes ``key`` and its metadata unit, so a child changing since
    the watermark is not a change to what it is about to remove, and refusing
    on it would be a guard about the wrong keys.

    Does nothing at all when ``unchanged_since`` is None. An absent watermark
    is an unchecked run, which is what every caller that has not asked for this
    gets and why nothing that worked before behaves differently.
    """
    if unchanged_since is None:
        return
    watermark = _watermark(unchanged_since)
    newest = _document_change(opened, key, key_range)
    if subtree:
        newest = _later(newest, opened.latest_change(key, key_range=key_range, whole_subtree=True))
    else:
        newest = _later(newest, _metadata_change(opened, key, key_range))
    if newest is not None and newest > watermark:
        raise ChangedSinceError(
            "changed-since",
            key=key,
            action=action,
            subtree=subtree,
            unchanged_since=watermark,
            changed_at=newest,
        )


def _watermark(unchanged_since: str) -> str:
    """``unchanged_since`` in the one spelling stored timestamps are written in.

    Normalised rather than compared as it arrives, because the comparison is a
    string comparison: a caller writing ``2026-09-03T11:15:00+01:00`` and a
    store holding ``2026-09-03T10:15:00+00:00`` are naming the same moment, and
    an unnormalised comparison would read the offset as an hour of difference
    in the wrong direction.

    An :class:`InvalidArgumentError` rather than the ``ValueError``
    :func:`_timestamp` raises, because this one reaches a person: no front end
    can check a timestamp in its own argument layer, so a mistyped watermark
    arrives here and deserves a sentence.
    """
    try:
        moment = _timestamp(unchanged_since)
    except ValueError as exc:
        raise InvalidArgumentError(
            "unchanged-since-unreadable", unchanged_since=unchanged_since
        ) from exc
    assert moment is not None  # noqa: S101 - None in is None out, and it is not None here
    return moment


def _document_change(opened: Store, key: str, key_range: KeyRange) -> str | None:
    """When the document at ``key`` was last written, if it holds one.

    A one-character read, because the timestamp is metadata about the document
    rather than part of it, and because the root has no listing entry to ask
    instead. Tested against the range here rather than by the store, for the
    reason :func:`outrage.mounts._rows_at` does the same: this named the key,
    so it can say whether the range keeps it.
    """
    try:
        moment = opened.retrieve_document(key, max_chars=1).updated_at
    except KeyNotFoundError:
        return None
    if moment is None or not _within(key_range)(keys.sort_form(keys.parse(key).key)):
        return None
    return moment


def _metadata_change(opened: Store, key: str, key_range: KeyRange) -> str | None:
    """The newest change inside ``key``'s own metadata unit.

    What a *plain* delete takes with the key, which
    :meth:`Store.latest_change` leaves out by default and reports as part of
    the subtree under ``whole_subtree``: neither answers this on its own, so a
    caller guarding one key asks for it here.

    Recursive, because a metadata namespace has a subtree: ``a/!changelog`` may
    hold notes, and a note written since the watermark is a change to the unit.
    By the segment rather than by ``kind``, exactly as
    :func:`outrage.mounts._rows_at` is, since a namespace holding only what is
    below it appears as an implicit entry and is no less part of the unit.
    """
    inside = _within(key_range)
    newest: str | None = None
    for entry in opened.list_keys(key).items:
        if entry_kind(entry.key) != "metadata":
            continue
        if entry.updated_at is not None and inside(keys.sort_form(entry.key)):
            newest = _later(newest, entry.updated_at)
        newest = _later(
            newest, opened.latest_change(entry.key, key_range=key_range, whole_subtree=True)
        )
    return newest


def _later(one: str | None, other: str | None) -> str | None:
    """The newer of two timestamps, either of which may be absent."""
    if one is None:
        return other
    if other is None:
        return one
    return max(one, other)


_MATCH_MODES = ("contains", "line", "regex")
_SEARCH_TARGETS = ("document", "metadata")
_SEARCH_COMBINATIONS = ("any", "all")
_SEARCH_METADATA_PAGE = 100


def _search_matchers(
    criteria: Sequence[SearchCriterion], combine: str, scan_limit: int | None
) -> list[tuple[SearchCriterion, Callable[[str], tuple[int, int] | None]]]:
    """Validate and compile one search request at the Store boundary."""
    if not 1 <= len(criteria) <= 5:
        raise InvalidArgumentError("search-criteria-count", count=len(criteria))
    if combine not in _SEARCH_COMBINATIONS:
        raise InvalidArgumentError("search-combination", combine=combine)
    if scan_limit is not None and scan_limit <= 0:
        raise InvalidArgumentError("search-scan-limit", scan_limit=scan_limit)

    prepared = []
    for index, criterion in enumerate(criteria):
        if criterion.match not in _MATCH_MODES:
            raise InvalidArgumentError("search-match-mode", index=index, match=criterion.match)
        if criterion.target not in _SEARCH_TARGETS:
            raise InvalidArgumentError("search-target", index=index, target=criterion.target)
        if not criterion.pattern:
            raise InvalidArgumentError("search-pattern-empty", index=index)
        if criterion.target == "document" and criterion.meta_name is not None:
            raise InvalidArgumentError("search-document-meta-name", index=index)
        if criterion.target == "metadata" and criterion.meta_name is not None:
            if not criterion.meta_name or any(not name for name in criterion.meta_name):
                raise InvalidArgumentError("search-meta-name-empty", index=index)
        prepared.append((criterion, _search_matcher(criterion, index)))
    return prepared


def _search_matcher(
    criterion: SearchCriterion, index: int
) -> Callable[[str], tuple[int, int] | None]:
    if criterion.match == "contains":

        def contains(content: str) -> tuple[int, int] | None:
            start = content.find(criterion.pattern)
            return None if start < 0 else (start, start + len(criterion.pattern))

        return contains
    if criterion.match == "line":

        def line(content: str) -> tuple[int, int] | None:
            offset = 0
            endings = (
                "\r\n",
                "\n",
                "\r",
                "\v",
                "\f",
                "\x1c",
                "\x1d",
                "\x1e",
                "\x85",
                "\u2028",
                "\u2029",
            )
            for held in content.splitlines(keepends=True):
                body = held
                for ending in endings:
                    if body.endswith(ending):
                        body = body[: -len(ending)]
                        break
                if body == criterion.pattern:
                    return offset, offset + len(body)
                offset += len(held)
            return None

        return line
    try:
        expression = re.compile(criterion.pattern)
    except re.error as exc:
        raise InvalidArgumentError(
            "search-regex-invalid", index=index, pattern=criterion.pattern, reason=str(exc)
        ) from exc

    def regex(content: str) -> tuple[int, int] | None:
        found = expression.search(content)
        return None if found is None else found.span()

    return regex


def _search_metadata(
    store: Store,
    document_key: str,
    prepared: Sequence[tuple[SearchCriterion, Callable[[str], tuple[int, int] | None]]],
) -> dict[str, str]:
    """Read each direct metadata value relevant to the request once."""
    requested: set[str] | None = set()
    for criterion, _ in prepared:
        if criterion.target != "metadata":
            continue
        if criterion.meta_name is None:
            requested = None
            break
        requested.update(criterion.meta_name)

    found: dict[str, str] = {}
    cursor = None
    while True:
        page = store.list_keys(document_key, limit=_SEARCH_METADATA_PAGE, cursor=cursor)
        for entry in page.items:
            if entry.kind != "metadata" or entry.size is None:
                continue
            name = entry.key.rpartition(keys.DELIMITER)[2][len(keys.META_PREFIX) :]
            if requested is None or name in requested:
                found[entry.key] = read_all(store, entry.key).content
        if page.next_cursor is None:
            return found
        cursor = page.next_cursor


# -- shared by every backend -------------------------------------------------
#
# Below here is what a backend needs and should not re-decide: how a scope
# argument names the root, where a key sits in the order, what a timestamp
# looks like, how one argument is decoded and one document is sliced, and how
# a call is recorded. None of it touches storage, and a second backend that
# writes its own version of any of it is a second answer to a settled
# question.


def _scope(key: str | None) -> str:
    """The key a scope argument names, with ``None`` meaning the root.

    Omitting the argument, passing None and passing "" all name the whole
    store. Applied once on the way in, so nothing below here carries a second
    spelling of "everywhere": that duality is what the root key exists to
    remove, and left in place every new call taking a subtree would have to
    re-decide which spelling it accepted.
    """
    return keys.ROOT if key is None else key


#: What :func:`meta_reader` returns: a row's key and its stored metadata split,
#: in; the split as the scope sees it, out.
MetaReader = Callable[[str, str | None, str | None], tuple[str | None, str | None]]


def meta_reader(scope: str) -> MetaReader:
    """How to read a row's metadata split from inside ``scope``.

    "Is this a document" and "is this the value of a name" are asked *relative
    to the key a read was scoped at*, and the stored ``meta_name`` and
    ``meta_path`` answer them only when that scope holds no ``!``. They record
    where the **key** first turns to metadata, which from inside
    ``a/!changelog`` is a segment above the question: every row there carries
    ``changelog``, so the stored reading would match nothing at all.

    So the stored pair for an ordinary scope -- which is every survey anyone
    runs -- and :func:`outrage.keys.relative` per row for a scope that is
    itself metadata. **This is where the rule that a survey descends into a
    metadata namespace only when scoped inside one lives** for the backends
    that hold their rows in memory; ``store_sqlite._meta_clauses`` is the same
    rule as SQL.
    """
    at = keys.parse(scope)
    if not at.is_metadata:
        return lambda key, meta_name, meta_path: (meta_name, meta_path)

    def seen_from(
        key: str, meta_name: str | None, meta_path: str | None
    ) -> tuple[str | None, str | None]:
        seen = keys.relative(key, at.key)
        return seen.meta_name, seen.meta_path

    return seen_from


def entry_kind(key: str) -> str:
    """Whether ``key`` lists as ``"metadata"`` or as ``"document"``.

    Decided by the **last segment**, because a listing shows one level and a
    ``!`` opens a namespace at whatever level it stands: ``a/!changelog`` lists
    inside ``a`` as metadata, and the ``22`` inside it lists as the ordinary
    document it is. The stored ``meta_name`` says where the whole key first
    turns to metadata, which is a different question and the wrong one here.

    Shared by all three backends, so a listing cannot mean one thing in SQL and
    another on a filesystem.
    """
    return (
        "metadata" if key.rpartition(keys.DELIMITER)[2].startswith(keys.META_PREFIX) else "document"
    )


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


#: A sort position past every key there is. :func:`outrage.keys.sort_subtree_end`
#: refuses the root, because everything is beneath it and nothing can be
#: appended to the empty sort form that a descendant would sort below -- but a
#: bound naming the root still has to be *compared* against something, so the
#: comparison gets the position the refusal denies it. Above every sort form by
#: construction, since a sort form is built from segment characters and the
#: three low markers.
_PAST_EVERYTHING = "\uffff"

#: Each bound of a :class:`KeyRange`, as the three things a comparison needs:
#: which side of the order it cuts from, whether the cut keeps the key it
#: names, and where in the order the cut falls. Every bound is a cut in one
#: ordering, so what differs between them is only this.
#:
#: Written down once, here with the range itself, because three things now ask
#: it: a table deciding whether a bound reaches a mounted store, a bisect over
#: rows already in order, and a filter over a stream that is in order but
#: cannot be bisected. The table is the same six rows as
#: ``store_parquet._span`` and ``store_sqlite._range_clauses``, and the three
#: are meant to be read against each other.
_BOUNDS: tuple[tuple[str, bool, bool, Callable[[str], str]], ...] = (
    ("after_inclusive", True, True, keys.sort_form),
    ("after", True, False, keys.sort_form),
    ("after_subtree", True, True, keys.sort_subtree_end),
    ("before", False, False, keys.sort_form),
    ("before_inclusive", False, True, keys.sort_form),
    ("final_subtree", False, False, keys.sort_subtree_end),
)


def _parsed(key: str) -> str:
    """``key`` normalised, allowing the segments a mount table's namespace has.

    A bound may name a key spanning several stores, which is longer than one
    store's own limit and still a key -- see :data:`outrage.keys.MAX_JOINED_SEGMENTS`.
    """
    return keys.parse(key, max_segments=keys.MAX_JOINED_SEGMENTS).key


def _cut(key: str, at: Callable[[str], str]) -> str:
    """Where a bound naming ``key`` falls in the order."""
    if at is keys.sort_subtree_end:
        parsed = keys.parse(key, max_segments=keys.MAX_JOINED_SEGMENTS)
        if parsed.key == keys.ROOT:
            return _PAST_EVERYTHING
    return at(key)


def _within(key_range: KeyRange) -> Callable[[str], bool]:
    """``key_range`` as a test on a sort position.

    The predicate form of the same six bounds a backend holding its rows in
    order bisects. A store that reads its rows as a stream cannot bisect -- it
    has no list to seek within -- and yet the range means exactly what it means
    everywhere else, so it is answered here from :data:`_BOUNDS` rather than
    re-derived per backend.

    Built once per call and applied per row, so a key is parsed and a cut
    taken once for the whole read rather than once for every row it looks at.

    **A subtree bound naming the root is refused here**, by
    :func:`outrage.keys.sort_subtree_end` rather than by anything written down
    twice: everything is beneath the root, so there is no bound to draw around
    it, and the alternative is a bound that quietly matches nothing. That is
    the contract every backend keeps, and it is why this takes the cut
    directly rather than through :func:`_cut`, which answers a different
    question -- where a bound falls *relative to a stretch of the order*, for a
    table deciding whether it reaches a store at all.
    """
    cuts = [
        (is_lower, inclusive, at(_parsed(named)))
        for name, is_lower, inclusive, at in _BOUNDS
        if (named := getattr(key_range, name)) is not None
    ]
    if not cuts:
        return lambda position: True

    def inside(position: str) -> bool:
        for is_lower, inclusive, cut in cuts:
            if is_lower and (position < cut or (not inclusive and position == cut)):
                return False
            if not is_lower and (position > cut or (not inclusive and position == cut)):
                return False
        return True

    return inside


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _timestamp(updated_at: str | None) -> str | None:
    """One spelling for a caller's ``updated_at``, or None left as it is.

    Normalised rather than taken as given, so that a timestamp a copy carried
    in is the same shape as one :func:`_now` wrote: every stored value is then
    comparable as a string, which is how a listing sorts them and how a check
    reads them. UTC at second precision for the same reason - the corpus has
    never held anything else, and a store where half the rows carry an offset
    is one where a string comparison quietly stops meaning what it says.

    A naive timestamp is read as UTC. It is the only reading that agrees with
    the rest of the package: :func:`_now` is UTC, and so is the mtime the
    filesystem backend reads back.
    """
    if updated_at is None:
        return None
    if not isinstance(updated_at, str):
        raise TypeError(f"updated_at must be a string, got {type(updated_at).__name__}")
    try:
        moment = datetime.fromisoformat(updated_at)
    except ValueError as exc:
        raise ValueError(f"updated_at must be an ISO 8601 timestamp, got {updated_at!r}") from exc
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).isoformat(timespec="seconds")


def _ms(started: int) -> float:
    """Elapsed milliseconds, from the monotonic clock a time change cannot move."""
    return round((time.monotonic_ns() - started) / 1_000_000, 3)


def _clear(target: Path) -> None:
    """Remove whatever is at ``target``, file or directory, if anything is.

    A backup writes to a path :meth:`FileStore.backup_path` has already agreed
    to, so anything still there was asked to be overwritten. Removed rather
    than written over, because the two shapes are not interchangeable: writing
    a store file over a directory fails, and writing a tree into one that is
    already there leaves whatever was in it beside what was copied.
    """
    if target.is_dir() and not target.is_symlink():
        shutil.rmtree(target)
    else:
        target.unlink(missing_ok=True)


def _stored_bytes(target: Path) -> int:
    """How much disk a store takes, whether it is a file or a tree of them.

    A directory's own size says nothing about what is in it, so a tree is the
    sum of its files. Reported rather than checked: it is what a caller prints
    beside a backup, and a number that means the same for both kinds is worth
    more here than one that is exact about blocks.
    """
    if target.is_dir():
        return sum(path.stat().st_size for path in target.rglob("*") if path.is_file())
    return target.stat().st_size


#: Cap on the keys named in one logged result. A log line has to stay small
#: enough to be written in a single call, or two processes appending can
#: interleave; a survey of a large subtree would otherwise be unbounded.
_MAX_LOGGED_KEYS = 50


def _summarise(
    log: EventLog,
    result: object,
    *,
    mount_point: str = keys.ROOT,
) -> dict[str, object]:
    """Describe a return value in the terms an investigation later asks in.

    Not the value itself. The point of a summary is that the questions being
    asked are about shape - how much was returned, whether it was cut short,
    which keys were touched - and a log holding whole results is a second copy
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
            return {"key": keys.with_prefix(mount_point, result)}
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
                "next_cursor": (
                    keys.with_prefix(mount_point, result.next_cursor)
                    if result.next_cursor is not None
                    else None
                ),
            }
            if result.items and isinstance(result.items[0], Excerpt):
                summary["truncated"] = sum(1 for item in result.items if item.truncated)
            elif (
                result.items
                and isinstance(result.items[0], str)
                and result.returned <= _MAX_LOGGED_KEYS
            ):
                summary["keys"] = [keys.with_prefix(mount_point, key) for key in result.items]
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
                listed["keys"] = [keys.with_prefix(mount_point, key) for key in result]
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
        raise InvalidArgumentError(
            "encoding-not-a-json-string", what=what, encoding=encoding, reason=str(exc)
        ) from exc
    if not isinstance(decoded, str):
        raise InvalidArgumentError(
            "encoding-not-a-string",
            what=what,
            encoding=encoding,
            decoded=type(decoded).__name__,
        )
    return decoded


#: An HTML document announcing itself in its first characters: a doctype, or
#: the root element. Deliberately narrow -- markdown carries inline HTML, so a
#: document opening with `<div>` or `<img>` is still markdown and a looser test
#: would relabel a great deal of ordinary prose.
_HTML_OPENING = re.compile(r"<(?:!doctype\s+html\b|html[\s>])", re.IGNORECASE)


def _detect_format(content: str) -> str:
    """The format ``content`` declares about itself, or markdown.

    Only a declaration at the very start counts, and only one that no markdown
    document plausibly makes: JSON that actually parses, or an HTML doctype or
    root element. Everything else is markdown, which is the honest answer for
    prose and the unavoidable one for plain text -- see :data:`FORMATS`.
    """
    stripped = content.lstrip()
    if stripped[:1] in ("{", "["):
        try:
            json.loads(content)
        except ValueError:
            return "markdown"
        return "json"
    if _HTML_OPENING.match(stripped):
        return "html"
    return "markdown"


def _find_occurrence(content: str, pattern: str, occurrence: int, offset: int) -> int | None:
    position = offset - 1
    for _ in range(occurrence + 1):
        position = content.find(pattern, position + 1)
        if position == -1:
            return None
    return position


def _excerpt(
    key: str,
    content: str,
    format: str | None,
    updated_at: str,
    start: int,
    length: int | None,
    max_chars: int,
) -> Excerpt:
    """One document's stored text as the slice a caller asked for.

    The slicing policy rather than the storage: how ``length`` and
    ``max_chars`` combine, where the slice stops, and when the result carries a
    continuation offset. Takes the four stored fields rather than a row, so a
    backend that does not have rows still slices identically.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if length is not None and length < 0:
        raise ValueError("length must not be negative")

    total = len(content)
    start = min(start, total)
    take = max_chars if length is None else min(length, max_chars)
    excerpt = content[start : start + take]
    end = start + len(excerpt)

    # The byte numbers cost one encode of the document, split at the same two
    # points the slice is -- and nothing at all where every character is one
    # byte, which is most Markdown. `isascii` is a flag CPython already keeps
    # on the string, not a scan.
    if content.isascii():
        byte_start, byte_end, total_bytes = start, end, total
    else:
        byte_start = len(content[:start].encode())
        byte_end = byte_start + len(excerpt.encode())
        total_bytes = byte_end + len(content[end:].encode())

    return Excerpt(
        key=key,
        content=excerpt,
        format=format,
        updated_at=updated_at,
        offset=start,
        returned=len(excerpt),
        total=total,
        next_offset=end if end < total else None,
        byte_offset=byte_start,
        total_bytes=total_bytes,
        next_byte_offset=byte_end if end < total else None,
    )


#: The most bytes UTF-8 spends on one character, and so how far a read must
#: over-read to be sure of filling a cap counted in characters.
_UTF8_MAX_BYTES = 4

#: How many bytes back a snap can have to walk: a character is at most four
#: bytes, so at most three of them are continuations.
_UTF8_MAX_CONTINUATIONS = 3


def _character_start(data: bytes, position: int) -> int:
    """``position`` snapped back to the first byte of the character it is in.

    John's boundary rule, in one function because it is shared: two backends
    that snapped differently would return different documents for the same
    call, which is the reason :func:`_excerpt` is shared in the first place.

    A continuation byte is ``0b10xxxxxx`` and there are never more than three
    of them in a row, so this walks back at most three. Already on a boundary,
    or at the end of the data, it moves nothing -- and every byte offset the
    store itself hands out is on a boundary already, so the snap only ever
    fires on arithmetic a caller invented.
    """
    while 0 < position < len(data) and 0x80 <= data[position] < 0xC0:
        position -= 1
    return position


def _whole_characters(data: bytes) -> str:
    """``data`` decoded, less any character its final bytes only begin.

    The far end of the boundary rule. A slice taken to a byte cap can stop
    inside a character; the incremental decoder holds those bytes back rather
    than raising, so what comes out is exactly the characters the slice
    completed. Data ending at the document's end has nothing to hold back.
    """
    return codecs.getincrementaldecoder("utf-8")().decode(data, final=False)


def _byte_excerpt(
    key: str,
    format: str | None,
    updated_at: str,
    start: int,
    length: int | None,
    max_chars: int,
    *,
    read: Callable[[int, int], bytes],
    total_bytes: int,
    total: int | None = None,
) -> Excerpt:
    """One document's stored text as the slice a *byte* offset asked for.

    The same policy as :func:`_excerpt` in the other unit, and the only thing
    the two do not share is which numbers they can report. ``read(offset,
    size)`` hands back that many bytes of the document's UTF-8 from that byte,
    which a backend that can seek answers without materialising the rest --
    which is the whole point -- and one that cannot answers by slicing bytes
    it already has. Either way the content is identical, and that contract is
    what keeps a byte offset portable between backends.

    ``max_chars`` stays a cap in *characters*, whichever unit addressed the
    read: the budget a caller spends is context, and context is counted in
    characters. So this over-reads by the worst ratio UTF-8 can spend -- 32 KB
    of bytes for 8 000 characters -- decodes, and cuts back.

    ``total`` is the document's length in characters where the backend knows it
    without reading the document -- from a stored length, or because it holds
    the text anyway -- and None where finding out would mean the scan a byte
    offset exists to avoid. So it stays backend-dependent by design, and a
    caller reads ``total_bytes``, which every backend always knows.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if length is not None and length < 0:
        raise ValueError("length must not be negative")

    take = max_chars if length is None else min(length, max_chars)
    start = min(start, total_bytes)

    # Three bytes of run-up, so the snap has the character's own first byte to
    # find without a second read.
    window_start = max(0, start - _UTF8_MAX_CONTINUATIONS)
    window = read(window_start, (start - window_start) + take * _UTF8_MAX_BYTES)
    start = window_start + _character_start(window, start - window_start)

    excerpt = _whole_characters(window[start - window_start :])[:take]
    end = start + len(excerpt.encode())

    return Excerpt(
        key=key,
        content=excerpt,
        format=format,
        updated_at=updated_at,
        offset=None,
        returned=len(excerpt),
        total=total,
        next_offset=None,
        byte_offset=start,
        total_bytes=total_bytes,
        next_byte_offset=end if end < total_bytes else None,
    )


def _sliced(data: bytes) -> Callable[[int, int], bytes]:
    """The reader :func:`_byte_excerpt` takes, over bytes already in hand.

    What a backend with no fast path passes, so that converting and slicing is
    the *same* code as seeking rather than a second implementation of the
    boundary rule beside it.
    """
    return lambda offset, size: data[offset : offset + size]


def _find_byte_occurrence(
    read: Callable[[int, int], bytes],
    total_bytes: int,
    pattern: str,
    occurrence: int,
    byte_offset: int,
) -> int | None:
    """Where a literal pattern occurs at or after ``byte_offset``, in bytes.

    Searching is a scan whatever the unit, so this reads the document rather
    than seeking within it; no backend has a fast path for it and pretending
    otherwise would only hide that. It searches the *encoded* pattern in the
    encoded document, which needs no boundary rule of its own: UTF-8 is
    self-synchronising, so an encoded needle cannot match anywhere but at a
    character boundary.
    """
    data = read(0, total_bytes)
    needle = pattern.encode()
    position = _character_start(data, min(byte_offset, len(data))) - 1
    for _ in range(occurrence + 1):
        position = data.find(needle, position + 1)
        if position == -1:
            return None
    return position


def check_read_position(
    key: str,
    *,
    offset: int,
    byte_offset: int | None,
    pattern: str | None,
    occurrence: int,
) -> None:
    """Refuse a read that names its position twice, or names it impossibly.

    One place, for the same reason the slicing is one place: a backend that
    accepted a pair of offsets its neighbours refused would be answering a
    question the store has no answer to. ``offset=0`` beside a byte offset is
    not that pair -- it cannot be told from silence, and does not need to be,
    since both spell the start of the document.
    """
    if byte_offset is not None and offset:
        raise InvalidArgumentError(
            "offsets-both-given", key=key, offset=offset, byte_offset=byte_offset
        )
    if offset < 0:
        raise ValueError("offset must not be negative")
    if byte_offset is not None and byte_offset < 0:
        raise ValueError("byte_offset must not be negative")
    if pattern is not None:
        if not pattern:
            raise InvalidArgumentError("pattern-empty")
        if occurrence < 0:
            raise ValueError("occurrence must not be negative")


__all__ = [
    "BACKUP_DIR_NAME",
    "BACKUP_STAMP",
    "CHANGED",
    "CONFLICTS",
    "DEFAULT_BACKEND",
    "backend_names",
    "check_read_position",
    "check_unchanged",
    "DEFAULT_BULK_MAX_CHARS",
    "DEFAULT_DIR_NAME",
    "DEFAULT_MAX_CHARS",
    "ENCODINGS",
    "ENV_DIR",
    "EVERYTHING",
    "FAILED",
    "FORMATS",
    "OVERWRITE",
    "OVERWRITE_UNCHANGED",
    "READ",
    "SKIP",
    "SKIPPED",
    "STOP",
    "STOPPED",
    "UNBOUNDED",
    "WROTE",
    "AuditRow",
    "Backup",
    "BackendError",
    "BackupError",
    "BoundedSubtree",
    "ChangedSinceError",
    "DocumentMatch",
    "Encoding",
    "Entry",
    "Excerpt",
    "FileStore",
    "Format",
    "InvalidArgumentError",
    "KeyNotFoundError",
    "KeyRange",
    "MatchMode",
    "MatchWitness",
    "MetaReader",
    "MissingMeta",
    "Page",
    "PatternNotFoundError",
    "ReadOnlyStoreError",
    "SearchCombination",
    "SearchCriterion",
    "SearchPage",
    "SearchTarget",
    "Store",
    "StoreFileError",
    "Transfer",
    "default_store",
    "default_store_file",
    "entry_kind",
    "meta_reader",
    "open_store",
    "read_all",
    "resolve_directory",
    "store_file",
]
