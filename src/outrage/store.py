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

:class:`Store` itself is abstract, and there are two implementations. The
operations carry the contract both answer:
:class:`outrage.store_sqlite.SqliteStore` is a read-write database accumulated a
document at a time, and :class:`outrage.store_parquet.ParquetStore` is one
columnar file written whole and read many times, for a reference base of tens
of thousands of documents. They share none of the storage and every word of
the vocabulary below, which is the point of the split.

:func:`_backend_for` is the one place in the package that chooses between
them, and it chooses by the store file's extension. So nothing above here --
not the server, not the command line, not the mount table -- names a backend
to open one.

Independent of MCP: everything here is callable and testable on its own. Read
:mod:`outrage.keys` first for what a key is, which everything below is written in
terms of; the key namespace and the tool semantics are argued in ``design.md``
**at the root of the repository**, which is not part of this reference.
"""

from __future__ import annotations

import functools
import importlib
import inspect
import json
import os
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Self, TypeVar

from . import eventlog, keys
from .errors import RageError
from .eventlog import EventLog

if TYPE_CHECKING:
    # Only in the signatures of the maintenance methods below. A runtime
    # import would be a cycle: outrage.maintenance is written in terms of Store,
    # and each backend imports the vocabulary from it to fill a report in.
    from .maintenance import Repaired, Report

#: Default directory name, relative to the working directory, when neither
#: --dir nor RAGE_DIR is given.
DEFAULT_DIR_NAME = ".rage"

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
ENV_DIR = "RAGE_DIR"

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
FORMATS = ("markdown", "json", "text", "html")

#: Encodings a caller may use for the content and title it passes in. These
#: describe the argument in transit, not the stored document, which is always
#: decoded back to plain text before it is written. See ``_decode``.
ENCODINGS = ("json-string",)


class StoreFileError(RageError, ValueError):
    """A store file that does not name a file inside its directory.

    A store file is always relative to the directory holding it -- that is what
    lets one directory hold several stores, and what keeps a configuration file
    free of absolute paths that stop being true when a project moves. An
    absolute path, or one climbing out with ``..``, is refused here rather than
    quietly opening a database somewhere nobody was looking.
    """


class KeyNotFoundError(RageError, LookupError):
    """Raised when a key holds no content."""


class PatternNotFoundError(RageError, LookupError):
    """Raised when a search pattern does not occur in a document."""


class BackupError(RageError, RuntimeError):
    """Raised when a backup cannot be taken, or cannot be shown to be good."""


class ReadOnlyStoreError(RageError, PermissionError):
    """Raised when a store is asked to write and its backend cannot.

    Distinct from :class:`outrage.mounts.ReadOnlyMountError`, which is about a
    *configuration*: a store that could be written was mounted with
    ``--mount-ro``, and starting the server without that flag would let the
    write through. This one is about the storage. A parquet file is not
    updated in place, so no flag exists that would make the same call succeed,
    and telling a caller to drop one would be advice that does not work.
    """


class BackendError(RageError, RuntimeError):
    """Raised when a backend cannot be used: absent, or asked for a file it
    did not write."""


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
        """Whether part of the document was left unread.

        The same fact as ``next_offset is not None``, named so that a caller
        deciding whether to read on does not have to know that. Reading on
        means passing ``next_offset`` back as ``offset``.
        """
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

    >>> store_file("/srv/project/.rage").name
    'store.sqlite'
    >>> store_file("/srv/project/.rage", "ref.sqlite").name
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


class Store(ABC):
    """A document store: the operations, without saying how they are kept.

    Abstract, and deliberately narrow. Everything below is expressed in keys,
    ranges, subtrees, pages and excerpts -- the vocabulary of the namespace --
    so that a backend is free to answer them however its storage is shaped.
    What a subclass adds is how a key becomes a stored thing and back; what it
    may not add is a second way of saying which keys a call is about.

    Two things are settled here rather than per backend, because they are the
    same question whatever the storage is: **where the file lives**, which
    :func:`store_file` decides from a directory and a name relative to it, and
    **that a store is a file inside a directory** rather than a directory of
    its own, so that several stores can share one -- see
    ``project/reference/planned/mounts``.

    :func:`default_store` is what a caller uses to get one of these without
    naming a backend.
    """

    #: What this backend calls its store file when a caller names none. Set by
    #: every concrete backend, and the only thing about the file a backend
    #: decides: that it *is* a file inside a directory is settled above, by
    #: :func:`store_file`. :func:`default_store_file` is how the rest of the
    #: package asks for it without naming a backend to ask.
    default_filename: ClassVar[str]

    #: Whether this backend can be written at all. False says the *storage*
    #: refuses, which is not the same as a store that was mounted read-only:
    #: a mount's refusal comes off with a flag and this one does not. A caller
    #: deciding whether to offer a write reads this; a caller that writes
    #: anyway gets :class:`ReadOnlyStoreError` from the backend, since a class
    #: var nobody consulted must not be the only thing standing between a
    #: corpus and a half-written file.
    writable: ClassVar[bool] = True

    #: What this backend is called where a report or a refusal has to name it.
    #: A short lowercase word, matching the store file's extension, so that a
    #: sentence about a store and the name of its file agree.
    backend_name: ClassVar[str]

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
    ) -> None:
        # A null log rather than None, so nothing below has to ask whether
        # logging is on before recording anything.
        self._log = log if log is not None else eventlog.NULL
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
        encoding: str | None = None,
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

        Every refusal above is :meth:`_validated`'s, which an implementation
        calls before it writes anything.
        """

    @classmethod
    def _validated(
        cls,
        key: str,
        content: str,
        format: str | None,
        *,
        title: str | None,
        encoding: str | None,
    ) -> tuple[keys.Key, str, str, str | None]:
        """What :meth:`store_document` accepts, and what it turns into.

        Returns the parsed key, the decoded content, the resolved format and
        the decoded title — the arguments as they are actually written, with
        every refusal already made. A ``?`` in the key survives this: which
        number it becomes is read from the store, inside the transaction that
        writes it, and is the one part of the call that is not decidable here.

        A classmethod rather than a template method calling down into the
        backend. It leaves every implementation's control flow exactly where it
        is, while making it impossible for a backend to validate differently
        without visibly not calling this — two stores that disagreed about what
        a key or a format is would be two namespaces, which is the thing the
        split of :mod:`outrage.store` from a backend exists to prevent.

        **Call it inside the logged method.** ``_logged`` binds the caller's
        arguments before the body runs, so validation lifted out in front of
        the decorated call would leave the log recording the normalised
        arguments rather than the ones that arrived — and what the caller
        actually passed is the one thing that log is for.

        The order is guarded, not incidental: the key parses first, then the
        content is a string, then the encoding decodes it, then the format is
        detected from what the decode produced, and the title is checked last.
        Detecting a format before decoding would read the JSON *literal* rather
        than the document inside it. ``tests/test_store.py`` has a case per
        refusal.
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
        return parsed, content, format, title

    @abstractmethod
    def delete(
        self, key: str, recursive: bool = False, *, key_range: KeyRange = UNBOUNDED
    ) -> list[str]:
        """Delete ``key``, returning the keys actually removed.

        A document key takes its metadata with it. Descendants are removed only
        when ``recursive`` is set, so a mistyped key cannot silently discard a
        whole subtree. Note that storing an empty document is not a deletion.

        ``key_range`` bounds which keys are in scope, exactly as it does for a
        read: a delete that steps over a mounted store's stretch of the order
        needs to say so in the same vocabulary a traversal does, or it removes
        keys the mount has made unreachable and reports them as deleted. Those
        keys read back fine from the mount on the very next call, which is the
        defect this argument exists for -- see
        ``project/reference/planned/mounts/crossing``.

        It bounds *both* halves. The key itself and its metadata are as capable
        of lying inside a shadowed stretch as any descendant is.
        """

    @abstractmethod
    def descendant_count(self, key: str, *, key_range: KeyRange = UNBOUNDED) -> int:
        """How many stored keys lie strictly below ``key``.

        Metadata counts: it is stored, and a caller deciding whether a subtree
        is empty is asking about everything that would have to go.

        Exists so a caller can report what a non-recursive delete left behind:
        without it, deleting a key that holds nothing itself is indistinguishable
        from deleting a key that does not exist.

        ``key_range`` bounds it for the reason it bounds ``delete``: a count
        that includes keys a mount has made unreachable tells a caller to pass
        ``recursive`` to remove keys that are not there to remove.
        """

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

    # -- maintenance -----------------------------------------------------

    @abstractmethod
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
        """

    def backup_path(self, destination: str | os.PathLike[str] | None, *, overwrite: bool) -> Path:
        """Settle where the copy goes, and refuse the destinations that destroy.

        Public so that a caller can report the destination, and hit the same
        refusals, without writing anything — which is what ``--dry-run`` needs.

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


#: The extension each backend claims, and the class behind it. The **single
#: place** the package decides which storage a store file is kept in.
#:
#: A registry rather than a ``backend=`` argument threaded through the server,
#: the command line and the mount table, because a store is already addressed
#: as a *file* and a backend already names its own -- so if a backend names its
#: file, the file can name the backend, and ``--mount-ro ref=python.parquet``
#: needs no new grammar to say what it obviously means.
#:
#: Named by module and class rather than holding the classes, because each
#: backend is written in terms of this module and importing one at module scope
#: would be a cycle. :func:`_backend_for` resolves an entry on use.
_BACKENDS: dict[str, tuple[str, str]] = {
    ".sqlite": (".store_sqlite", "SqliteStore"),
    ".parquet": (".store_parquet", "ParquetStore"),
}

#: The extension a store file has when nobody says otherwise, and so the
#: backend an unrecognised name falls back to. See :func:`_backend_for` for why
#: the fallback is a fallback rather than a refusal.
DEFAULT_BACKEND = ".sqlite"


def _backend() -> type[Store]:
    """The backend class this build uses when nobody names one."""
    return _backend_for(None)


def _backend_for(filename: str | os.PathLike[str] | None) -> type[Store]:
    """Which backend keeps a store file called ``filename``.

    ``None`` means the default. Everything else is read from the extension:
    ``ref.parquet`` is a parquet store and ``ref.sqlite`` is a SQLite one.

    **An unrecognised extension is the default backend, not an error.** A store
    file has always been free to be called anything -- ``ref.db`` and
    ``monday.sqlite`` alike -- and turning every unclaimed name into a refusal
    would break configurations that named a file before any backend claimed an
    extension. So the registry recognises the names a backend has claimed; it
    does not decide which names are allowed. A name that means to be parquet
    and is spelled ``ref.parq`` opens as SQLite, which is the cost of that, and
    the store it opens is empty rather than wrong.

    The import failing is not a bug here: pyarrow is an optional extra, so a
    ``.parquet`` mount on an install without it has to say so in a sentence
    rather than raise ``ModuleNotFoundError`` at whoever is watching.
    """
    extension = DEFAULT_BACKEND if filename is None else Path(filename).suffix
    module_name, class_name = _BACKENDS.get(extension, _BACKENDS[DEFAULT_BACKEND])
    try:
        module = importlib.import_module(module_name, __package__)
    except ImportError as exc:
        raise BackendError(
            "backend-unavailable",
            filename=str(filename),
            backend=class_name,
            reason=str(exc),
        ) from exc
    backend: type[Store] = getattr(module, class_name)
    return backend


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
    log: EventLog | None = None,
) -> Store:
    """A store of the backend this build opens when nobody names one.

    ``filename`` of None means whatever that backend calls its store file.
    Any other name picks the backend that claims its extension, so a caller
    holding a mount's file name opens the right storage without naming one --
    see :func:`_backend_for`.
    """
    return _backend_for(filename)(directory, filename=filename, log=log)


@contextmanager
def open_store(
    directory: str | os.PathLike[str] | None = None,
    *,
    filename: str | os.PathLike[str] | None = None,
    log: EventLog | None = None,
) -> Iterator[Store]:
    """Open a store, closing it on exit."""
    store = default_store(directory, filename=filename, log=log)
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

    return Excerpt(
        key=key,
        content=excerpt,
        format=format,
        updated_at=updated_at,
        offset=start,
        returned=len(excerpt),
        total=total,
        next_offset=end if end < total else None,
    )


__all__ = [
    "BACKUP_DIR_NAME",
    "BACKUP_STAMP",
    "DEFAULT_BACKEND",
    "DEFAULT_BULK_MAX_CHARS",
    "DEFAULT_DIR_NAME",
    "DEFAULT_MAX_CHARS",
    "ENCODINGS",
    "ENV_DIR",
    "EVERYTHING",
    "FORMATS",
    "UNBOUNDED",
    "AuditRow",
    "Backup",
    "BackendError",
    "BackupError",
    "BoundedSubtree",
    "Entry",
    "Excerpt",
    "KeyNotFoundError",
    "KeyRange",
    "MissingMeta",
    "Page",
    "PatternNotFoundError",
    "ReadOnlyStoreError",
    "Store",
    "StoreFileError",
    "default_store",
    "default_store_file",
    "open_store",
    "read_all",
    "resolve_directory",
    "store_file",
]
