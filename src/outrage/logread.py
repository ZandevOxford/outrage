"""Reading back what :mod:`outrage.eventlog` wrote.

The writer half exists because evidence was not being kept. This half is what
turns the file it produces into answers, and the questions are already known -
they are the ones that were open long enough to motivate the log:

* Which arguments did a call actually carry? Not how many calls were made, and
  not what the caller says it did, but the arguments as they arrived.
* Was a read truncated, and did anyone come back for the rest of it?
* Is the document that was written the document that was sent?

**Group by ``session`` before trusting ``seq``.** One file holds more than one
process: a client may run a short-lived process for discovery before the
serving one, and both append to the same path. ``seq`` counts within one
``EventLog`` instance, so it restarts partway down the file, and sorting the
whole file by it interleaves two processes into an order neither of them ran
in. Every function here that orders events does so within a session.

Nothing here writes. A reader that could modify the log would be able to
destroy the only copy of the evidence it exists to present.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import OutrageError

#: Arguments whose value carries no information on a summary line. ``max_chars``
#: is on every read and is a caller default rather than an intent; the rest are
#: absent-by-default and read as noise when they hold their zero. All of them
#: survive in the record itself, which ``--json`` prints.
_DULL_ARGS = frozenset({"max_chars"})
_DULL_WHEN_ZERO = frozenset({"offset", "occurrence"})

#: How much of a failure message goes on its line. Long enough for the sentence
#: that names the cause, short enough that a screen of errors stays a column.
#: The whole message is in the record, which ``--json`` prints.
MESSAGE_CHARS = 110


class LogError(OutrageError):
    """A log that cannot be read at all, as opposed to one with a bad line in it."""


@dataclass(frozen=True)
class Event:
    """One line of the log, with the accessors the filters and summary ask in.

    The record is kept whole rather than unpacked into fields. The writer adds
    fields as it learns what is worth recording, and a reader that mapped each
    one into a slot of its own would silently drop whatever it was not updated
    for - which is the failure mode the log exists to catch, rebuilt in the
    thing that reads it.
    """

    line: int
    record: dict[str, Any]

    @property
    def event(self) -> str:
        return str(self.record.get("event", ""))

    @property
    def session(self) -> str:
        return str(self.record.get("session", ""))

    @property
    def seq(self) -> int:
        seq = self.record.get("seq")
        return seq if isinstance(seq, int) else 0

    @property
    def call(self) -> int | None:
        call = self.record.get("call")
        return call if isinstance(call, int) else None

    @property
    def ts(self) -> str:
        return str(self.record.get("ts", ""))

    @property
    def ms(self) -> float | None:
        ms = self.record.get("ms")
        return float(ms) if isinstance(ms, int | float) else None

    @property
    def op(self) -> str | None:
        """The store operation, for a store event."""
        op = self.record.get("op")
        return str(op) if isinstance(op, str) else None

    @property
    def method(self) -> str | None:
        """The MCP method, for a request or notify event."""
        method = self.record.get("method")
        return str(method) if isinstance(method, str) else None

    @property
    def tool(self) -> str | None:
        """The tool named by a ``tools/call`` request."""
        params = self.record.get("params")
        if isinstance(params, dict) and isinstance(params.get("name"), str):
            return str(params["name"])
        return None

    @property
    def args(self) -> dict[str, Any]:
        """The arguments as they were recorded, from either layer.

        A store event holds them under ``args``; a request holds them nested in
        the tool call's ``params``. Both answer the same question, so both are
        reachable the same way - that question ("which ``meta_name`` did that
        search screen on") is what the log settled first.
        """
        args = self.record.get("args")
        if isinstance(args, dict):
            return args
        params = self.record.get("params")
        if isinstance(params, dict) and isinstance(params.get("arguments"), dict):
            return dict(params["arguments"])
        return {}

    @property
    def key(self) -> str | None:
        key = self.args.get("key")
        return key if isinstance(key, str) else None

    @property
    def result(self) -> dict[str, Any] | None:
        result = self.record.get("result")
        return result if isinstance(result, dict) else None

    @property
    def error(self) -> dict[str, Any] | None:
        """The failure, from either layer.

        The store records a raised exception under ``error``. The request layer
        records a *refused* call as a result with ``ok`` false, because a tool
        that returns an error result never raises - reading only ``error``
        would report every rejected call as a success, which is the bug that
        the first version of the writer shipped with.
        """
        error = self.record.get("error")
        if isinstance(error, dict):
            return error
        result = self.result
        if result is not None and result.get("ok") is False:
            # Named apart from anything the store raises, because one failing
            # call produces both: the store's exception underneath and the
            # refusal the caller was handed. Counting them under one label
            # would double every failure and make neither number mean anything.
            return {"type": "refused", "message": str(result.get("message", ""))}
        return None

    @property
    def content(self) -> dict[str, Any] | None:
        """The document text field, whichever side of the call carried it."""
        for holder in (self.args.get("content"), (self.result or {}).get("content")):
            if isinstance(holder, dict):
                return holder
        return None

    @property
    def next_offset(self) -> int | None:
        """Where the rest of a truncated read begins, or ``None`` if it was whole."""
        result = self.result
        if result is None:
            return None
        offset = result.get("next_offset")
        return offset if isinstance(offset, int) else None


@dataclass
class Session:
    """The events of one server process, in the order that process ran them."""

    id: str
    events: list[Event] = field(default_factory=list)

    @property
    def start(self) -> Event | None:
        """The ``start`` event, which is what dates and identifies the process."""
        return next((event for event in self.events if event.event == "start"), None)

    @property
    def pid(self) -> int | None:
        start = self.start
        pid = start.record.get("pid") if start else None
        return pid if isinstance(pid, int) else None

    @property
    def version(self) -> str | None:
        start = self.start
        return str(start.record["version"]) if start and "version" in start.record else None

    @property
    def first_ts(self) -> str:
        return self.events[0].ts if self.events else ""

    @property
    def last_ts(self) -> str:
        return self.events[-1].ts if self.events else ""

    @property
    def calls(self) -> list[int]:
        """The call numbers seen, in order."""
        seen = dict.fromkeys(event.call for event in self.events if event.call is not None)
        return list(seen)

    @property
    def tool_calls(self) -> int:
        return sum(1 for event in self.events if event.method == "tools/call")

    @property
    def store_accesses(self) -> int:
        return sum(1 for event in self.events if event.event == "store")

    @property
    def is_discovery(self) -> bool:
        """Whether this looks like the short-lived process a client runs first.

        It starts, answers a handful of catalogue methods and exits, so it
        appears in the file as a session that did nothing - and a search that
        mistakes it for the serving one finds an empty log.

        All three conditions are needed because a filtered view is also a
        session that did nothing: requiring the ``start`` event and at least
        one request means the annotation only appears where the evidence for it
        is actually present, rather than wherever a filter removed the work.
        """
        served = sum(1 for event in self.events if event.method)
        return self.start is not None and served > 0 and self.tool_calls == 0


@dataclass
class Log:
    """A parsed log file, and what could not be parsed in it."""

    path: Path
    events: list[Event] = field(default_factory=list)
    malformed: list[int] = field(default_factory=list)

    @property
    def sessions(self) -> list[Session]:
        return sessions(self.events)


def read_log(path: str | os.PathLike[str]) -> Log:
    """Parse a log file, tolerating lines that are not events.

    A line that will not parse is counted and skipped rather than fatal. The
    writer appends under a lock, but it appends from more than one process and
    can be killed mid-line, so a torn last line is an expected state of a live
    log - not a reason to refuse to show the 300 good lines above it.
    """
    path = Path(path).expanduser()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError as exc:
        raise LogError("log-missing", path=str(path)) from exc
    except OSError as exc:
        raise LogError("log-unreadable", path=str(path), reason=str(exc)) from exc

    log = Log(path=path)
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError:
            log.malformed.append(number)
            continue
        if not isinstance(record, dict):
            log.malformed.append(number)
            continue
        log.events.append(Event(line=number, record=record))
    return log


def sessions(events: Iterable[Event]) -> list[Session]:
    """Group events by the process that wrote them, ordered within each by ``seq``.

    Sessions come back in the order they first appear in the file, which is the
    order the processes started. Between two sessions only the timestamps
    compare; ``seq`` does not, and this is the whole reason the grouping exists.
    """
    grouped: dict[str, Session] = {}
    for event in events:
        grouped.setdefault(event.session, Session(id=event.session)).events.append(event)
    for session in grouped.values():
        session.events.sort(key=lambda event: event.seq)
    return list(grouped.values())


@dataclass(frozen=True)
class Filter:
    """Which events to show. Every field given must match; omitted fields ignore."""

    session: str | None = None
    call: int | None = None
    op: str | None = None
    method: str | None = None
    event: str | None = None
    key: str | None = None
    errors: bool = False

    def matches(self, event: Event) -> bool:
        """Whether one event satisfies every field that is set.

        Fields combine with AND, and an unset field constrains nothing, so an
        empty filter matches everything. ``session`` matches on a prefix and
        ``key`` on a substring, because both are typed by hand at a command
        line; the rest are exact.
        """
        if self.session is not None and not event.session.startswith(self.session):
            return False
        if self.call is not None and event.call != self.call:
            return False
        if self.op is not None and event.op != self.op:
            return False
        if self.method is not None and event.method != self.method:
            return False
        if self.event is not None and event.event != self.event:
            return False
        if self.key is not None and self.key not in (event.key or ""):
            return False
        if self.errors and event.error is None:
            return False
        return True

    def select(self, events: Iterable[Event]) -> list[Event]:
        """The events that :meth:`matches` accepts, in the order they arrived.

        The many-at-once form of the same question, which is what every caller
        actually wants; ``matches`` is public because a caller streaming a
        large log asks it one event at a time.
        """
        return [event for event in events if self.matches(event)]


# -- the standing questions ------------------------------------------------


@dataclass(frozen=True)
class TruncatedRead:
    """A read that returned part of a document, and the read that resumed it."""

    read: Event
    resumed_by: Event | None

    @property
    def followed_up(self) -> bool:
        """Whether the caller ever came back for the rest of the document.

        The question the pairing exists to answer. False is the interesting
        answer: it means an agent was handed part of a document and acted on
        it, which is what ``project/reference/planned/agents`` was guessing
        about before this could be measured.
        """
        return self.resumed_by is not None


def truncated_reads(session: Session) -> list[TruncatedRead]:
    """Find the truncated reads in one session and pair each with its follow-up.

    A follow-up is a later read of the same key starting at exactly the offset
    the truncated one handed back. Matching the offset rather than just the key
    is the point: a caller that reads the same document again from the top has
    not collected the rest of it, and counting that as a follow-up would answer
    the question backwards.

    Within one session only. Two processes reading the same key are two
    callers, and one of them resuming the other's read is not a thing that
    happens.
    """
    found: list[TruncatedRead] = []
    reads = [event for event in session.events if event.op == "retrieve_document"]
    for position, event in enumerate(reads):
        offset = event.next_offset
        if offset is None:
            continue
        resumed = next(
            (
                later
                for later in reads[position + 1 :]
                if later.key == event.key and later.args.get("offset") == offset
            ),
            None,
        )
        found.append(TruncatedRead(read=event, resumed_by=resumed))
    return found


@dataclass
class Summary:
    """The numbers a log is read for, over whatever set of events was selected."""

    path: Path
    lines: int = 0
    malformed: int = 0
    sessions: list[Session] = field(default_factory=list)
    calls: int = 0
    store_accesses: int = 0
    #: Keyed by ``(session, call)``. Call numbers restart with the process that
    #: issues them, so two sessions' call 5 are two different calls and adding
    #: them together invents a call that touched the store twice as much as any
    #: real one did.
    accesses_per_call: Counter[tuple[str, int]] = field(default_factory=Counter)
    ops: Counter[str] = field(default_factory=Counter)
    methods: Counter[str] = field(default_factory=Counter)
    tools: Counter[str] = field(default_factory=Counter)
    errors: Counter[str] = field(default_factory=Counter)
    refused: int = 0
    reads: int = 0
    truncated: list[TruncatedRead] = field(default_factory=list)
    documents_truncated: int = 0

    @property
    def busiest_call(self) -> tuple[int, str, int] | None:
        """The call that touched the store most, as ``(accesses, session, call)``.

        Named rather than just counted, so that the number is somewhere to go:
        ``outrage log --session … --call …`` shows what it was doing.
        """
        if not self.accesses_per_call:
            return None
        (session, call), accesses = self.accesses_per_call.most_common(1)[0]
        return accesses, session, call

    @property
    def mean_accesses(self) -> float:
        """Store accesses per tool call, averaged over the calls seen.

        Per *call*, not per session or per event: it says how much work one
        tool call costs the store, which is what a change to a tool's
        implementation moves. Zero when nothing was called, rather than
        undefined.
        """
        if not self.accesses_per_call:
            return 0.0
        return sum(self.accesses_per_call.values()) / len(self.accesses_per_call)

    @property
    def followed_up(self) -> int:
        """How many of the truncated reads were resumed in the same session.

        Against ``len(self.truncated)`` for the share that was not. Same
        session deliberately: a resume in a later one is a new reader arriving
        at the document, not this reader coming back.
        """
        return sum(1 for read in self.truncated if read.followed_up)


def summarise(log: Log, events: Iterable[Event] | None = None) -> Summary:
    """Compute the standing numbers over ``events``, defaulting to the whole log.

    Taking the events separately is what lets a summary describe a filtered
    slice - "how did *this* session behave" - rather than only ever the file.
    """
    selected = list(log.events if events is None else events)
    summary = Summary(
        path=log.path,
        lines=len(selected),
        malformed=len(log.malformed),
        sessions=sessions(selected),
    )

    for session in summary.sessions:
        for event in session.events:
            if event.event == "store":
                summary.store_accesses += 1
                if event.op:
                    summary.ops[event.op] += 1
                if event.call is not None:
                    summary.accesses_per_call[session.id, event.call] += 1
            elif event.method:
                summary.methods[event.method] += 1
                if event.tool:
                    summary.tools[event.tool] += 1
            if (error := event.error) is not None:
                if error["type"] == "refused":
                    summary.refused += 1
                else:
                    summary.errors[str(error.get("type", "error"))] += 1

        summary.calls += len(session.calls)
        summary.truncated.extend(truncated_reads(session))

    summary.reads = summary.ops.get("retrieve_document", 0)
    summary.documents_truncated = sum(
        count
        for event in selected
        if event.op == "get_documents"
        and isinstance(count := (event.result or {}).get("truncated"), int)
    )
    return summary


# -- rendering -------------------------------------------------------------


def format_event(event: Event, *, content: bool = False) -> Iterator[str]:
    """Render one event as a line, plus the document text when asked for.

    The excerpt is off by default and available on request because it is the
    only way to answer the question it was kept for - whether what was written
    is what was sent - and much too long to put on every line.
    """
    call = f"call {event.call}" if event.call is not None else "-"
    parts = [f"{event.seq:>5}", _clock(event.ts), f"{call:<8}", f"{event.event:<7}"]

    if event.event == "start":
        version = event.record.get("version", "?")
        parts.append(f"outrage {version} pid {event.record.get('pid', '?')}")
    else:
        parts.append(_what(event))
        if arguments := _args_gist(event):
            parts.append(arguments)
        parts.append(_outcome(event))
        if event.ms is not None:
            parts.append(f"{event.ms:.1f}ms")

    yield "  ".join(part for part in parts if part)
    if content and (field := event.content) is not None:
        yield from _content_block(field)


def format_summary(summary: Summary) -> Iterator[str]:
    """Render the standing numbers, in the order the questions get asked."""
    yield f"{summary.path}"
    counted = f"{summary.lines} events, {len(summary.sessions)} sessions"
    if summary.malformed:
        counted += f", {summary.malformed} unparseable lines"
    yield f"  {counted}"

    yield ""
    yield "sessions"
    for session in summary.sessions:
        yield f"  {format_session(session)}"

    yield ""
    yield "calls"
    yield f"  {summary.calls} calls, {summary.store_accesses} store accesses"
    if summary.accesses_per_call:
        line = f"  {summary.mean_accesses:.1f} accesses per call"
        if (busiest := summary.busiest_call) is not None:
            accesses, session_id, call = busiest
            line += f", most in one call {accesses} (session {session_id}, call {call})"
        yield line
    if summary.tools:
        yield f"  tools: {_counts(summary.tools)}"
    if summary.ops:
        yield f"  store: {_counts(summary.ops)}"

    yield ""
    yield "reads"
    if summary.reads:
        share = f" ({len(summary.truncated) * 100 // summary.reads}%)"
        yield f"  {summary.reads} document reads, {len(summary.truncated)} truncated{share}"
        if summary.truncated:
            # The number the second trap in planned/agents was a guess about.
            yield f"  {summary.followed_up} of those resumed at next_offset in the same session"
            for read in summary.truncated:
                if not read.followed_up:
                    yield f"    abandoned: {read.read.key} at {read.read.next_offset}"
    else:
        yield "  no document reads"
    if summary.documents_truncated:
        yield f"  {summary.documents_truncated} documents truncated inside get_documents results"

    if summary.errors or summary.refused:
        yield ""
        yield "errors"
        if summary.errors:
            yield f"  raised by the store: {_counts(summary.errors)}"
        if summary.refused:
            # Usually the same failures seen from the other side. A count here
            # larger than the store's is the interesting case: a call refused
            # before it ever reached the store.
            yield f"  returned to the caller as an error: {summary.refused}"


def format_session(session: Session) -> str:
    """Identify one process: which it was, when it ran, and how much it did."""
    identity = [session.id]
    if session.pid is not None:
        identity.append(f"pid {session.pid}")
    if session.version is not None:
        identity.append(f"outrage {session.version}")
    span = _clock(session.first_ts)
    if session.last_ts != session.first_ts:
        span += f" … {_clock(session.last_ts)}"
    counts = f"{len(session.events)} events, {session.tool_calls} tool calls"
    if session.is_discovery:
        counts += " (discovery only)"
    return f"{'  '.join(identity)}  {span}  {counts}"


def _what(event: Event) -> str:
    """What the event was: the store op, or the method and the tool it called."""
    if event.op:
        return event.op
    if event.method == "tools/call" and event.tool:
        return f"{event.method} {event.tool}"
    return event.method or ""


def _args_gist(event: Event) -> str:
    """The arguments worth putting on one line, in the order they were recorded.

    Dropped: anything unset, a caller default that says nothing about intent,
    and the size caps that are on every read. All of them survive in the record
    and come back under --json, so this trades completeness for a line that can
    be scanned down a column.
    """
    rendered = []
    for name, value in event.args.items():
        if value is None or name in _DULL_ARGS or _is_absent_content(value):
            continue
        if name in _DULL_WHEN_ZERO and value == 0:
            continue
        rendered.append(f"{name}={_value(value)}")
    return " ".join(rendered)


def _is_absent_content(value: Any) -> bool:
    """Whether a content field stands for an argument that was never passed.

    The writer renders a non-string under the content policy as its type alone,
    so an omitted ``title`` arrives here as ``{"type": "NoneType"}``. That is a
    faithful record and a useless column: it is on every write that did not set
    one.
    """
    return isinstance(value, dict) and value.get("type") == "NoneType"


def _value(value: Any) -> str:
    if isinstance(value, dict) and "len" in value:
        # A content field: its length is the part that fits on a line.
        return f"<{value['len']} chars>"
    if isinstance(value, dict) and "type" in value:
        return f"<{value['type']}>"
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


def _outcome(event: Event) -> str:
    if (error := event.error) is not None:
        return f"!! {error.get('type', 'error')}: {_message(error.get('message'))}".rstrip()
    result = event.result
    if result is None:
        return ""
    if "total" in result:
        got = f"-> {result.get('returned')}/{result['total']} chars"
        if (offset := result.get("next_offset")) is not None:
            got += f", more at {offset}"
        return got
    if "count" in result:
        got = f"-> {result['count']}"
        if result.get("truncated"):
            got += f", {result['truncated']} truncated"
        return got
    if "key" in result:
        return f"-> {result['key']}"
    if result.get("ok") is True:
        return "-> ok"
    return f"-> {json.dumps(result, ensure_ascii=False, default=str)}"


def _content_block(field: dict[str, Any]) -> Iterator[str]:
    """Show the document text the log kept, marking where it was cut.

    Head and tail are printed as two blocks with the gap named, never joined:
    the failure this was built to catch was scaffolding appended after a
    summary that read correctly to its last sentence, and a rendering that hid
    the seam would read as one clean document.
    """
    if "text" in field:
        yield from _quoted(str(field["text"]))
        return
    if "head" not in field and "tail" not in field:
        yield f"      <{field.get('len', '?')} chars, not recorded>"
        return
    head, tail = str(field.get("head", "")), str(field.get("tail", ""))
    yield from _quoted(head)
    yield f"      … {int(field.get('len', 0)) - len(head) - len(tail)} chars not recorded …"
    yield from _quoted(tail)


def _quoted(text: str) -> Iterator[str]:
    for line in text.splitlines() or [""]:
        yield f"      {line}"


def _message(message: Any) -> str:
    """The first line of a failure, capped. The rest is in the record."""
    first = str(message or "").splitlines()
    text = first[0] if first else ""
    return text if len(text) <= MESSAGE_CHARS else text[: MESSAGE_CHARS - 1] + "…"


def _counts(counter: Counter[str]) -> str:
    return ", ".join(f"{name} {count}" for name, count in counter.most_common())


def _clock(ts: str) -> str:
    """Just the time of day. The date is on the session line above it."""
    _, _, time_of_day = ts.partition("T")
    return (time_of_day.split("+")[0] or ts)[:12]


__all__ = [
    "MESSAGE_CHARS",
    "Event",
    "Filter",
    "Log",
    "LogError",
    "Session",
    "Summary",
    "TruncatedRead",
    "format_event",
    "format_session",
    "format_summary",
    "read_log",
    "sessions",
    "summarise",
    "truncated_reads",
]
