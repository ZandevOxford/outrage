# outrage.eventlog

An append-only record of what was asked for and what was touched.

Not diagnostic logging. The name avoids two collisions that would suggest it
was: the standard library's [`logging`](https://docs.python.org/3/library/logging.html#module-logging), and SQLite's journal, which
`store.py` runs in WAL mode and which the design notes discuss at length.

This exists because of a failure that keeps recurring here: a success that
cannot be told from a real one. Unknown arguments dropped in silence,
truncation past `next_offset` that nothing downstream can detect, scaffolding
appended to a summary that reads correctly to its last sentence - each was
found by hand, afterwards, from evidence that no longer existed. A log turns
those from arguments into observations.

It is off unless asked for, because it records document content. When it is on
it must never be able to break a call: every failure disables the log, says so
once on stderr, and is otherwise swallowed. A logging system that can take down
the store is worse than no logging system.

Nothing here knows about MCP or about the store's own types, so both front ends
and the store can share it.

### outrage.eventlog.CONTENT_ARGS *= frozenset({'content', 'title'})*

Argument names whose string values are document text rather than metadata
about it, and so are subject to the content policy. Shared by the store and
the request middleware so that `--log-content=none` means the same thing at
both layers; scrubbing only one of them would leave the documents in the log
anyway. A boolean `title` is a generation control, not title content, and
[`EventLog.arguments()`](#outrage.eventlog.EventLog.arguments) retains it as a boolean.

### outrage.eventlog.CONTENT_POLICIES *= ('none', 'excerpt', 'full')*

How much of a document's text reaches the log. 'excerpt' is the default: see
`content_field` for why it keeps both ends.

### outrage.eventlog.DEFAULT *= <beside the store>*

`--log` given with no path: log beside the store, once the store
directory is known. Pass it where a path would go.

### outrage.eventlog.DEFAULT_EXCERPT_CHARS *= 200*

How much of a document the `excerpt` policy keeps, split between its two
ends. Enough to recognise what was written without the log becoming a second
copy of the store.

### outrage.eventlog.DEFAULT_LOG_NAME *= 'log.jsonl'*

Filename used when `--log` is given without a path, alongside the database
in the store directory. That directory exists so things can live beside the
database, and it is already excluded from version control.

### outrage.eventlog.ENV_LOG *= 'OUTRAGE_LOG'*

Environment variable naming the log file. Consulted after `--log` and
before giving up: there is no default location, because the default is not
to log at all.

### outrage.eventlog.NULL *= <outrage.eventlog.EventLog object>*

The log a store has when nobody gave it one, so that callers never branch on
whether logging is on.

### *class* outrage.eventlog.EventLog(path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, content: [str](https://docs.python.org/3/library/stdtypes.html#str) = 'excerpt', excerpt_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_EXCERPT_CHARS, session: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

A JSONL sink. `path` of `None` is a log that does nothing.

#### *property* enabled *: [bool](https://docs.python.org/3/library/functions.html#bool)*

#### emit(event: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*fields: [Any](https://docs.python.org/3/library/typing.html#typing.Any)) → [None](https://docs.python.org/3/library/constants.html#None)

Append one event. Never raises.

#### start(\*\*fields: [Any](https://docs.python.org/3/library/typing.html#typing.Any)) → [None](https://docs.python.org/3/library/constants.html#None)

Record what this process is, which is what dates every line after it.

#### stop(\*\*fields: [Any](https://docs.python.org/3/library/typing.html#typing.Any)) → [None](https://docs.python.org/3/library/constants.html#None)

Record that this process is finishing, and leave the log open.

A line, not a lifecycle step: it dates the end of a session's events
the way `start` dates their beginning. Writing continues to work
afterwards, which is deliberate -- a shutdown that still has something
to record is exactly when the log matters.

#### close() → [None](https://docs.python.org/3/library/constants.html#None)

Release the file descriptor and refuse to write again.

The lifecycle step, and the opposite half of the pair: nothing is
recorded, and every later `emit` is silently dropped rather than
raising, because a log that fails a call it was only observing has
broken the thing it exists to watch. Idempotent.

#### content_field(text: [Any](https://docs.python.org/3/library/typing.html#typing.Any)) → [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]

Render document text under the content policy.

Always the length and a hash of the whole, so two log entries can be
compared even when neither carries the text.

Under 'excerpt' a long document keeps both ends. The tail is not
symmetry: the failure that prompted this was tool-call scaffolding
appended *after* a summary that read correctly to its last sentence, so
a head-only excerpt would have missed the exact bug it was built to
catch. Text short enough to fit in both ends is stored whole instead,
which is also why the presence of head and tail rather than text
is itself the signal that something was cut.

#### arguments(values: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]) → [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]

Apply the content policy to string arguments carrying document text.

### outrage.eventlog.current_call *: [ContextVar](https://docs.python.org/3/library/contextvars.html#contextvars.ContextVar)* *= <ContextVar name='outrage_current_call' default=None>*

The request currently being served, so that store accesses can be attributed
to the call that caused them. A context variable rather than an argument
threaded through every store method: the store would otherwise have to carry
a parameter that only exists because of a front end it knows nothing about.

### outrage.eventlog.resolve_path(explicit: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | \_BesideTheStore | [None](https://docs.python.org/3/library/constants.html#None), directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/library/constants.html#None)

Locate the log file: `--log`, then OUTRAGE_LOG, then off.

The same order `store.resolve_directory` uses, minus the fallback: there
is no default location, because the default is not to log at all.
