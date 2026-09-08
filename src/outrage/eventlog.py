"""An append-only record of what was asked for and what was touched.

Not diagnostic logging. The name avoids two collisions that would suggest it
was: the standard library's :mod:`logging`, and SQLite's journal, which
``store.py`` runs in WAL mode and which the design notes discuss at length.

This exists because of a failure that keeps recurring here: a success that
cannot be told from a real one. Unknown arguments dropped in silence,
truncation past ``next_offset`` that nothing downstream can detect, scaffolding
appended to a summary that reads correctly to its last sentence - each was
found by hand, afterwards, from evidence that no longer existed. A log turns
those from arguments into observations.

It is off unless asked for, because it records document content. When it is on
it must never be able to break a call: every failure disables the log, says so
once on stderr, and is otherwise swallowed. A logging system that can take down
the store is worse than no logging system.

Nothing here knows about MCP or about the store's own types, so both front ends
and the store can share it.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sys
import threading
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

#: Environment variable naming the log file. Consulted after ``--log`` and
#: before giving up: there is no default location, because the default is not
#: to log at all.
ENV_LOG = "OUTRAGE_LOG"

#: Filename used when ``--log`` is given without a path, alongside the database
#: in the store directory. That directory exists so things can live beside the
#: database, and it is already excluded from version control.
DEFAULT_LOG_NAME = "log.jsonl"

#: How much of a document's text reaches the log. 'excerpt' is the default: see
#: ``content_field`` for why it keeps both ends.
CONTENT_POLICIES = ("none", "excerpt", "full")

#: How much of a document the ``excerpt`` policy keeps, split between its two
#: ends. Enough to recognise what was written without the log becoming a second
#: copy of the store.
DEFAULT_EXCERPT_CHARS = 200

#: Argument names whose string values are document text rather than metadata
#: about it, and so are subject to the content policy. Shared by the store and
#: the request middleware so that ``--log-content=none`` means the same thing at
#: both layers; scrubbing only one of them would leave the documents in the log
#: anyway. Boolean ``title`` and ``contents`` values are generation controls,
#: not document text, and :meth:`EventLog.arguments` retains them as booleans.
CONTENT_ARGS = frozenset({"content", "title", "contents"})


class _BesideTheStore:
    """Sentinel for ``--log`` given without a path.

    An object rather than a string, so that it cannot collide with a path a
    caller actually meant. The store directory is not known when the arguments
    are parsed, so the decision has to survive until it is.
    """

    def __repr__(self) -> str:
        return "<beside the store>"


#: ``--log`` given with no path: log beside the store, once the store
#: directory is known. Pass it where a path would go.
DEFAULT = _BesideTheStore()

#: The request currently being served, so that store accesses can be attributed
#: to the call that caused them. A context variable rather than an argument
#: threaded through every store method: the store would otherwise have to carry
#: a parameter that only exists because of a front end it knows nothing about.
current_call: ContextVar[int | None] = ContextVar("outrage_current_call", default=None)


class EventLog:
    """A JSONL sink. ``path`` of ``None`` is a log that does nothing."""

    def __init__(
        self,
        path: str | os.PathLike[str] | None = None,
        *,
        content: str = "excerpt",
        excerpt_chars: int = DEFAULT_EXCERPT_CHARS,
        session: str | None = None,
    ) -> None:
        if content not in CONTENT_POLICIES:
            raise ValueError(f"content must be one of {CONTENT_POLICIES}, got {content!r}")
        if excerpt_chars <= 0:
            raise ValueError("excerpt_chars must be positive")

        self.path = Path(path) if path is not None else None
        self.content = content
        self.excerpt_chars = excerpt_chars
        # Random rather than the pid, which is reused, and short enough to read.
        self.session = session or secrets.token_hex(3)

        self._lock = threading.Lock()
        self._seq = 0
        self._fd: int | None = None
        self._disabled = self.path is None
        if self.path is not None:
            self._open()

    @property
    def enabled(self) -> bool:
        return not self._disabled

    def _open(self) -> None:
        assert self.path is not None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Append-only, and 0600 because the file holds document text. The
            # database beside it is created under the umask, but a log is read
            # by people rather than by SQLite and is easier to leak.
            self._fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        except OSError as exc:
            # Deliberately not fatal. The user asked for logging, so the failure
            # is loud on stderr, but a store that will not open because its log
            # will not open is a worse trade than a store running unlogged.
            self._fail(f"cannot open {self.path}: {exc}")

    # -- emitting --------------------------------------------------------

    def emit(self, event: str, **fields: Any) -> None:
        """Append one event. Never raises."""
        if self._disabled:
            return
        try:
            # The lock spans the numbering and the write, so the order of the
            # lines and the order of `seq` cannot disagree. A reader that finds
            # them disagreeing is reading a file two processes wrote.
            with self._lock:
                self._seq += 1
                record: dict[str, Any] = {
                    "ts": _now(),
                    "seq": self._seq,
                    "session": self.session,
                    "event": event,
                }
                call = current_call.get()
                if call is not None:
                    record["call"] = call
                record.update(fields)
                # `default=str` so that an argument nobody anticipated is
                # rendered rather than raising, which would cost the whole log.
                line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
                os.write(_require(self._fd), line.encode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - see the module docstring
            self._fail(f"{type(exc).__name__}: {exc}")

    def start(self, **fields: Any) -> None:
        """Record what this process is, which is what dates every line after it."""
        self.emit("start", pid=os.getpid(), content=self.content, **fields)

    def stop(self, **fields: Any) -> None:
        """Record that this process is finishing, and leave the log open.

        A line, not a lifecycle step: it dates the end of a session's events
        the way ``start`` dates their beginning. Writing continues to work
        afterwards, which is deliberate -- a shutdown that still has something
        to record is exactly when the log matters.
        """
        self.emit("stop", **fields)

    def close(self) -> None:
        """Release the file descriptor and refuse to write again.

        The lifecycle step, and the opposite half of the pair: nothing is
        recorded, and every later ``emit`` is silently dropped rather than
        raising, because a log that fails a call it was only observing has
        broken the thing it exists to watch. Idempotent.
        """
        with self._lock:
            if self._fd is not None:
                os.close(self._fd)
                self._fd = None
            self._disabled = True

    def _fail(self, message: str) -> None:
        """Disable the log and say so, once.

        Once, because the alternative is a failure per call on a stream the
        client shows to the user. Never on stdout, which carries the MCP
        protocol and would be corrupted by anything written to it.
        """
        if not self._disabled:
            self._disabled = True
            print(f"outrage: event log disabled: {message}", file=sys.stderr, flush=True)

    # -- content ---------------------------------------------------------

    def content_field(self, text: Any) -> dict[str, Any]:
        """Render document text under the content policy.

        Always the length and a hash of the whole, so two log entries can be
        compared even when neither carries the text.

        Under 'excerpt' a long document keeps both ends. The tail is not
        symmetry: the failure that prompted this was tool-call scaffolding
        appended *after* a summary that read correctly to its last sentence, so
        a head-only excerpt would have missed the exact bug it was built to
        catch. Text short enough to fit in both ends is stored whole instead,
        which is also why the presence of `head` and `tail` rather than `text`
        is itself the signal that something was cut.
        """
        if not isinstance(text, str):
            return {"type": type(text).__name__}

        field: dict[str, Any] = {
            "len": len(text),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }
        if self.content == "none":
            return field
        if self.content == "full" or len(text) <= 2 * self.excerpt_chars:
            field["text"] = text
            return field
        field["head"] = text[: self.excerpt_chars]
        field["tail"] = text[-self.excerpt_chars :]
        return field

    def arguments(self, values: dict[str, Any]) -> dict[str, Any]:
        """Apply the content policy to string arguments carrying document text."""
        return {
            name: (
                self.content_field(value)
                if name in CONTENT_ARGS
                and not (name in {"title", "contents"} and isinstance(value, bool))
                else value
            )
            for name, value in values.items()
        }


#: The log a store has when nobody gave it one, so that callers never branch on
#: whether logging is on.
NULL = EventLog(None)


def resolve_path(
    explicit: str | os.PathLike[str] | _BesideTheStore | None,
    directory: str | os.PathLike[str],
) -> Path | None:
    """Locate the log file: ``--log``, then OUTRAGE_LOG, then off.

    The same order ``store.resolve_directory`` uses, minus the fallback: there
    is no default location, because the default is not to log at all.
    """
    if explicit is DEFAULT:
        return Path(directory) / DEFAULT_LOG_NAME
    if explicit is not None:
        return Path(explicit).expanduser()
    from_env = os.environ.get(ENV_LOG)
    if from_env:
        return Path(from_env).expanduser()
    return None


def _now() -> str:
    """Millisecond precision, unlike the store's own timestamps.

    ``store._now`` is second-granularity, which is right for a document's
    ``updated_at`` and too coarse to order the calls made within one turn.
    """
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _require(fd: int | None) -> int:
    if fd is None:
        raise RuntimeError("the event log has no open file")
    return fd


__all__ = [
    "CONTENT_ARGS",
    "CONTENT_POLICIES",
    "DEFAULT",
    "DEFAULT_EXCERPT_CHARS",
    "DEFAULT_LOG_NAME",
    "ENV_LOG",
    "NULL",
    "EventLog",
    "current_call",
    "resolve_path",
]
