# outrage.logread

Reading back what [`outrage.eventlog`](eventlog.md#module-outrage.eventlog) wrote.

The writer half exists because evidence was not being kept. This half is what
turns the file it produces into answers, and the questions are already known -
they are the ones that were open long enough to motivate the log:

* Which arguments did a call actually carry? Not how many calls were made, and
  not what the caller says it did, but the arguments as they arrived.
* Was a read truncated, and did anyone come back for the rest of it?
* Is the document that was written the document that was sent?

**Group by \`\`session\`\` before trusting \`\`seq\`\`.** One file holds more than one
process: a client may run a short-lived process for discovery before the
serving one, and both append to the same path. `seq` counts within one
`EventLog` instance, so it restarts partway down the file, and sorting the
whole file by it interleaves two processes into an order neither of them ran
in. Every function here that orders events does so within a session.

Nothing here writes. A reader that could modify the log would be able to
destroy the only copy of the evidence it exists to present.

### outrage.logread.MESSAGE_CHARS *= 110*

How much of a failure message goes on its line. Long enough for the sentence
that names the cause, short enough that a screen of errors stays a column.
The whole message is in the record, which `--json` prints.

### *class* outrage.logread.Event(line: [int](https://docs.python.org/3/library/functions.html#int), record: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)])

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One line of the log, with the accessors the filters and summary ask in.

The record is kept whole rather than unpacked into fields. The writer adds
fields as it learns what is worth recording, and a reader that mapped each
one into a slot of its own would silently drop whatever it was not updated
for - which is the failure mode the log exists to catch, rebuilt in the
thing that reads it.

#### line *: [int](https://docs.python.org/3/library/functions.html#int)*

#### record *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*

#### *property* event *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### *property* session *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### *property* seq *: [int](https://docs.python.org/3/library/functions.html#int)*

#### *property* call *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*

#### *property* ts *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### *property* ms *: [float](https://docs.python.org/3/library/functions.html#float) | [None](https://docs.python.org/3/library/constants.html#None)*

#### *property* op *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

The store operation, for a store event.

#### *property* method *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

The MCP method, for a request or notify event.

#### *property* tool *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

The tool named by a `tools/call` request.

#### *property* args *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*

The arguments as they were recorded, from either layer.

A store event holds them under `args`; a request holds them nested in
the tool call's `params`. Both answer the same question, so both are
reachable the same way - that question ("which `meta_name` did that
search screen on") is what the log settled first.

#### *property* key *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

#### *property* result *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None)*

#### *property* error *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None)*

The failure, from either layer.

The store records a raised exception under `error`. The request layer
records a *refused* call as a result with `ok` false, because a tool
that returns an error result never raises - reading only `error`
would report every rejected call as a success, which is a bug this
reader has already had once.

#### *property* content *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None)*

The document text field, whichever side of the call carried it.

#### *property* next_offset *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*

Where the rest of a truncated read begins, or `None` if it was whole.

### *class* outrage.logread.Filter(session: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, call: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, op: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, method: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, event: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, errors: [bool](https://docs.python.org/3/library/functions.html#bool) = False)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Which events to show. Every field given must match; omitted fields ignore.

#### session *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

#### call *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

#### op *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

#### method *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

#### event *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

#### errors *: [bool](https://docs.python.org/3/library/functions.html#bool)* *= False*

#### matches(event: [Event](#outrage.logread.Event)) → [bool](https://docs.python.org/3/library/functions.html#bool)

Whether one event satisfies every field that is set.

Fields combine with AND, and an unset field constrains nothing, so an
empty filter matches everything. `session` matches on a prefix and
`key` on a substring, because both are typed by hand at a command
line; the rest are exact.

#### select(events: [Iterable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterable)[[Event](#outrage.logread.Event)]) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Event](#outrage.logread.Event)]

The events that [`matches()`](#outrage.logread.Filter.matches) accepts, in the order they arrived.

The many-at-once form of the same question, which is what every caller
actually wants; `matches` is public because a caller streaming a
large log asks it one event at a time.

### *class* outrage.logread.Log(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), events: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Event](#outrage.logread.Event)] = <factory>, malformed: [list](https://docs.python.org/3/library/stdtypes.html#list)[[int](https://docs.python.org/3/library/functions.html#int)] = <factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

A parsed log file, and what could not be parsed in it.

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

#### events *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Event](#outrage.logread.Event)]*

#### malformed *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[int](https://docs.python.org/3/library/functions.html#int)]*

#### *property* sessions *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Session](#outrage.logread.Session)]*

### *exception* outrage.logread.LogError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError)

A log that cannot be read at all, as opposed to one with a bad line in it.

### *class* outrage.logread.Session(id: [str](https://docs.python.org/3/library/stdtypes.html#str), events: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Event](#outrage.logread.Event)] = <factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

The events of one server process, in the order that process ran them.

#### id *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### events *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Event](#outrage.logread.Event)]*

#### *property* start *: [Event](#outrage.logread.Event) | [None](https://docs.python.org/3/library/constants.html#None)*

The `start` event, which is what dates and identifies the process.

#### *property* pid *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*

#### *property* version *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

#### *property* first_ts *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### *property* last_ts *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### *property* calls *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[int](https://docs.python.org/3/library/functions.html#int)]*

The call numbers seen, in order.

#### *property* tool_calls *: [int](https://docs.python.org/3/library/functions.html#int)*

#### *property* store_accesses *: [int](https://docs.python.org/3/library/functions.html#int)*

#### *property* is_discovery *: [bool](https://docs.python.org/3/library/functions.html#bool)*

Whether this looks like the short-lived process a client runs first.

It starts, answers a handful of catalogue methods and exits, so it
appears in the file as a session that did nothing - and a search that
mistakes it for the serving one finds an empty log.

All three conditions are needed because a filtered view is also a
session that did nothing: requiring the `start` event and at least
one request means the annotation only appears where the evidence for it
is actually present, rather than wherever a filter removed the work.

### *class* outrage.logread.Summary(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), lines: [int](https://docs.python.org/3/library/functions.html#int) = 0, malformed: [int](https://docs.python.org/3/library/functions.html#int) = 0, sessions: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Session](#outrage.logread.Session)] = <factory>, calls: [int](https://docs.python.org/3/library/functions.html#int) = 0, store_accesses: [int](https://docs.python.org/3/library/functions.html#int) = 0, accesses_per_call: Counter[tuple[str, int]]=<factory>, ops: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = <factory>, methods: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = <factory>, tools: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = <factory>, errors: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = <factory>, refused: [int](https://docs.python.org/3/library/functions.html#int) = 0, reads: [int](https://docs.python.org/3/library/functions.html#int) = 0, truncated: [list](https://docs.python.org/3/library/stdtypes.html#list)[[TruncatedRead](#outrage.logread.TruncatedRead)] = <factory>, documents_truncated: [int](https://docs.python.org/3/library/functions.html#int) = 0)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

The numbers a log is read for, over whatever set of events was selected.

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

#### lines *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*

#### malformed *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*

#### sessions *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Session](#outrage.logread.Session)]*

#### calls *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*

#### store_accesses *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*

#### accesses_per_call *: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [int](https://docs.python.org/3/library/functions.html#int)]]*

Keyed by `(session, call)`. Call numbers restart with the process that
issues them, so two sessions' call 5 are two different calls and adding
them together invents a call that touched the store twice as much as any
real one did.

#### ops *: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*

#### methods *: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*

#### tools *: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*

#### errors *: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*

#### refused *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*

#### reads *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*

#### truncated *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[TruncatedRead](#outrage.logread.TruncatedRead)]*

#### documents_truncated *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*

#### *property* busiest_call *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[int](https://docs.python.org/3/library/functions.html#int), [str](https://docs.python.org/3/library/stdtypes.html#str), [int](https://docs.python.org/3/library/functions.html#int)] | [None](https://docs.python.org/3/library/constants.html#None)*

The call that touched the store most, as `(accesses, session, call)`.

Named rather than just counted, so that the number is somewhere to go:
`outrage log --session … --call …` shows what it was doing.

#### *property* mean_accesses *: [float](https://docs.python.org/3/library/functions.html#float)*

Store accesses per tool call, averaged over the calls seen.

Per *call*, not per session or per event: it says how much work one
tool call costs the store, which is what a change to a tool's
implementation moves. Zero when nothing was called, rather than
undefined.

#### *property* followed_up *: [int](https://docs.python.org/3/library/functions.html#int)*

How many of the truncated reads were resumed in the same session.

Against `len(self.truncated)` for the share that was not. Same
session deliberately: a resume in a later one is a new reader arriving
at the document, not this reader coming back.

### *class* outrage.logread.TruncatedRead(read: [Event](#outrage.logread.Event), resumed_by: [Event](#outrage.logread.Event) | [None](https://docs.python.org/3/library/constants.html#None))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

A read that returned part of a document, and the read that resumed it.

#### read *: [Event](#outrage.logread.Event)*

#### resumed_by *: [Event](#outrage.logread.Event) | [None](https://docs.python.org/3/library/constants.html#None)*

#### *property* followed_up *: [bool](https://docs.python.org/3/library/functions.html#bool)*

Whether the caller ever came back for the rest of the document.

The question the pairing exists to answer. False is the interesting
answer: it means an agent was handed part of a document and acted on
it. How often that happens was guesswork until it could be measured
here.

### outrage.logread.format_event(event: [Event](#outrage.logread.Event), \*, content: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

Render one event as a line, plus the document text when asked for.

The excerpt is off by default and available on request because it is the
only way to answer the question it was kept for - whether what was written
is what was sent - and much too long to put on every line.

### outrage.logread.format_session(session: [Session](#outrage.logread.Session)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

Identify one process: which it was, when it ran, and how much it did.

### outrage.logread.format_summary(summary: [Summary](#outrage.logread.Summary)) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

Render the standing numbers, in the order the questions get asked.

### outrage.logread.read_log(path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [Log](#outrage.logread.Log)

Parse a log file, tolerating lines that are not events.

A line that will not parse is counted and skipped rather than fatal. The
writer appends under a lock, but it appends from more than one process and
can be killed mid-line, so a torn last line is an expected state of a live
log - not a reason to refuse to show the 300 good lines above it.

### outrage.logread.sessions(events: [Iterable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterable)[[Event](#outrage.logread.Event)]) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Session](#outrage.logread.Session)]

Group events by the process that wrote them, ordered within each by `seq`.

Sessions come back in the order they first appear in the file, which is the
order the processes started. Between two sessions only the timestamps
compare; `seq` does not, and this is the whole reason the grouping exists.

### outrage.logread.summarise(log: [Log](#outrage.logread.Log), events: [Iterable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterable)[[Event](#outrage.logread.Event)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Summary](#outrage.logread.Summary)

Compute the standing numbers over `events`, defaulting to the whole log.

Taking the events separately is what lets a summary describe a filtered
slice - "how did *this* session behave" - rather than only ever the file.

### outrage.logread.truncated_reads(session: [Session](#outrage.logread.Session)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[TruncatedRead](#outrage.logread.TruncatedRead)]

Find the truncated reads in one session and pair each with its follow-up.

A follow-up is a later read of the same key starting at exactly the offset
the truncated one handed back. Matching the offset rather than just the key
is the point: a caller that reads the same document again from the top has
not collected the rest of it, and counting that as a follow-up would answer
the question backwards.

Within one session only. Two processes reading the same key are two
callers, and one of them resuming the other's read is not a thing that
happens.
