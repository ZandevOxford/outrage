"""Why a server would not start, kept where a client's stderr is not.

The companion to :mod:`outrage.eventlog` and deliberately not part of it. That
log is off unless ``--log`` asks for it, because it records document content;
this one is always on, because an error record is a code, a mount point, a path
and the sentence already going to stderr. That asymmetry is the whole argument
for a second file rather than a second field: "by default, errors are logged
somewhere" cannot be a field on a line that is not written by default.

**The reader is an operator, afterwards.** An MCP client launches
``outrage-server`` and discards its stderr, so a refused mount table leaves
nothing behind but a ``start`` and a ``stop`` a second apart in a log that may
not be on either. What this file exists to answer is "it did not come up, why" -
asked once, later, by somebody who can change the configuration.

Nothing here can break a startup. Every failure to write says so once on stderr
and is otherwise swallowed, the rule :mod:`outrage.eventlog` follows and for the
same reason: a server that will not serve because its error log will not open is
a worse trade than a server whose failure went unrecorded.
"""

from __future__ import annotations

import json
import os
import sys
import traceback as traceback_module
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout

from .errors import OutrageError

#: Filename in the store directory, beside the database and the event log.
#: That directory already exists for things that live beside the database, and
#: is already excluded from version control.
DEFAULT_ERROR_LOG_NAME = "errors.jsonl"

#: How large the file may get before the oldest records are dropped. Startup
#: failures are rare, so this is never reached in ordinary use -- it is here so
#: that a server failing in a loop cannot do what the event log did, which is
#: reach 34 MB in this checkout without anybody deciding it should.
#:
#: A ceiling on what is *already there*, checked before a record is appended, so
#: the file can finish one record over it. That is deliberate rather than
#: tolerated: trimming after the write would mean the newest record could be the
#: one dropped, which is the opposite of what a reader wants. Zero or less turns
#: trimming off.
DEFAULT_CAP_BYTES = 1 << 20

#: How long to wait for another process trimming the same file. Short, because
#: the alternative to waiting is skipping the trim, which costs nothing: the
#: file is over its cap for one more startup.
TRIM_TIMEOUT_SECONDS = 2.0


def path_for(directory: str | os.PathLike[str]) -> Path:
    """Where the error log for ``directory`` lives.

    A function rather than a constant joined at each call site, so that the
    answer is in one place if it ever grows an environment variable the way
    :func:`outrage.eventlog.resolve_path` has one. It deliberately has none
    today: a file nobody asked for should not also be a file nobody can find.
    """
    return Path(directory) / DEFAULT_ERROR_LOG_NAME


def record(
    directory: str | os.PathLike[str],
    event: str,
    error: BaseException | None = None,
    *,
    cap: int = DEFAULT_CAP_BYTES,
    **fields: Any,
) -> None:
    """Append one record saying that ``event`` failed, and never raise.

    ``error`` supplies the rest: an :class:`~outrage.errors.OutrageError`
    contributes its ``code``, and anything else contributes its traceback in
    full. The traceback is whole on purpose -- the one-line rendering is what
    stderr already had, and the reason this file exists is that the one-line
    rendering was not enough to work from.

    ``message`` is not derived here. Rendering an error into a sentence is
    :mod:`outrage.messages`' job and it needs to know which front end is asking,
    so the caller passes the text it already printed rather than this module
    composing a second, differently worded copy of it.
    """
    entry: dict[str, Any] = {
        "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "pid": os.getpid(),
        "event": event,
    }
    if error is not None:
        entry["error"] = type(error).__name__
        if isinstance(error, OutrageError):
            entry["code"] = error.code
        else:
            entry["traceback"] = "".join(
                traceback_module.format_exception(type(error), error, error.__traceback__)
            )
    entry.update(fields)

    file = path_for(directory)
    try:
        file.parent.mkdir(parents=True, exist_ok=True)
        _trim(file, cap)
        # `default=str` for the same reason the event log gives: a field nobody
        # anticipated is rendered rather than costing the record it is in.
        line = json.dumps(entry, ensure_ascii=False, default=str) + "\n"
        # 0600 because a file read by people is easier to leak than the database
        # beside it, and this one carries absolute paths.
        fd = os.open(file, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)
    except Exception as exc:  # noqa: BLE001 - see the module docstring
        # Never on stdout, which carries the MCP protocol and would be corrupted
        # by anything written to it.
        print(
            f"outrage: warning: could not record the error in {file}: {type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )


def _trim(file: Path, cap: int) -> None:
    """Drop the oldest records until the file is under ``cap``.

    On open rather than per write, because the check costs a ``stat`` and the
    rewrite is rare. Under a lock beside the file, because two servers starting
    at once would otherwise each rewrite what the other had just written and one
    set of records would go missing. Appends need no lock: they are ``O_APPEND``,
    which is what makes the common path free.

    A lock somebody else holds means somebody else is already trimming, so this
    call leaves the file alone rather than waiting for a turn to do work that is
    being done.
    """
    if cap <= 0 or not file.exists() or file.stat().st_size <= cap:
        return
    lock = FileLock(str(file) + ".lock", timeout=TRIM_TIMEOUT_SECONDS)
    try:
        with lock:
            # Re-checked inside the lock: the holder we waited for may have
            # already brought it under the cap, and trimming again would drop
            # records for nothing.
            if not file.exists() or file.stat().st_size <= cap:
                return
            kept = _tail(file.read_bytes(), cap)
            temporary = file.with_suffix(file.suffix + ".trim")
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                os.write(fd, kept)
            finally:
                os.close(fd)
            os.replace(temporary, file)
    except Timeout:
        return


def _tail(data: bytes, cap: int) -> bytes:
    """The whole records at the end of ``data`` that fit in ``cap``.

    Whole records: a file that begins half way through a line is one a reader
    has to guess about, and the guess is the thing this file exists to remove.
    Splitting from the right, so the newest are what survive.
    """
    lines = data.splitlines(keepends=True)
    kept: list[bytes] = []
    size = 0
    for line in reversed(lines):
        size += len(line)
        if size > cap:
            break
        kept.append(line)
    kept.reverse()
    return b"".join(kept)


__all__ = [
    "DEFAULT_CAP_BYTES",
    "DEFAULT_ERROR_LOG_NAME",
    "TRIM_TIMEOUT_SECONDS",
    "path_for",
    "record",
]
