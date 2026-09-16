# outrage.errorlog

Why a server would not start, kept where a client's stderr is not.

The companion to [`outrage.eventlog`](eventlog.md#module-outrage.eventlog) and deliberately not part of it. That
log is off unless `--log` asks for it, because it records document content;
this one is always on, because an error record is a code, a mount point, a path
and the sentence already going to stderr. That asymmetry is the whole argument
for a second file rather than a second field: "by default, errors are logged
somewhere" cannot be a field on a line that is not written by default.

**The reader is an operator, afterwards.** An MCP client launches
`outrage-server` and discards its stderr, so a refused mount table leaves
nothing behind but a `start` and a `stop` a second apart in a log that may
not be on either. What this file exists to answer is "it did not come up, why" -
asked once, later, by somebody who can change the configuration.

Nothing here can break a startup. Every failure to write says so once on stderr
and is otherwise swallowed, the rule [`outrage.eventlog`](eventlog.md#module-outrage.eventlog) follows and for the
same reason: a server that will not serve because its error log will not open is
a worse trade than a server whose failure went unrecorded.

### outrage.errorlog.DEFAULT_CAP_BYTES *= 1048576*

How large the file may get before the oldest records are dropped. Startup
failures are rare, so this is never reached in ordinary use -- it is here so
that a server failing in a loop cannot do what the event log did, which is
reach 34 MB in this checkout without anybody deciding it should.

A ceiling on what is *already there*, checked before a record is appended, so
the file can finish one record over it. That is deliberate rather than
tolerated: trimming after the write would mean the newest record could be the
one dropped, which is the opposite of what a reader wants. Zero or less turns
trimming off.

### outrage.errorlog.DEFAULT_ERROR_LOG_NAME *= 'errors.jsonl'*

Filename in the store directory, beside the database and the event log.
That directory already exists for things that live beside the database, and
is already excluded from version control.

### outrage.errorlog.TRIM_TIMEOUT_SECONDS *= 2.0*

How long to wait for another process trimming the same file. Short, because
the alternative to waiting is skipping the trim, which costs nothing: the
file is over its cap for one more startup.

### outrage.errorlog.path_for(directory: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

Where the error log for `directory` lives.

A function rather than a constant joined at each call site, so that the
answer is in one place if it ever grows an environment variable the way
[`outrage.eventlog.resolve_path()`](eventlog.md#outrage.eventlog.resolve_path) has one. It deliberately has none
today: a file nobody asked for should not also be a file nobody can find.

### outrage.errorlog.record(directory: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)], event: [str](https://docs.python.org/3/builtins/stdtypes.html#str), error: [BaseException](https://docs.python.org/3/builtins/exceptions.html#BaseException) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, \*, cap: [int](https://docs.python.org/3/builtins/functions.html#int) = DEFAULT_CAP_BYTES, \*\*fields: [Any](https://docs.python.org/3/library/typing.html#typing.Any)) → [None](https://docs.python.org/3/builtins/constants.html#None)

Append one record saying that `event` failed, and never raise.

`error` supplies the rest: an [`OutrageError`](errors.md#outrage.errors.OutrageError)
contributes its `code`, and anything else contributes its traceback in
full. The traceback is whole on purpose -- the one-line rendering is what
stderr already had, and the reason this file exists is that the one-line
rendering was not enough to work from.

`message` is not derived here. Rendering an error into a sentence is
[`outrage.messages`](messages.md#module-outrage.messages)' job and it needs to know which front end is asking,
so the caller passes the text it already printed rather than this module
composing a second, differently worded copy of it.
