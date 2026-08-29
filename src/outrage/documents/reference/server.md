# outrage.server

MCP server exposing the document store.

A thin wrapper: argument shaping and result shaping only. All behaviour lives
in [`outrage.store`](store.md#module-outrage.store), so it can be exercised without a protocol harness.

**Including the mount table.** More than one store behind one key namespace
used to be this module's work -- the routing, the segment list a subtree is read
as, the merge of a level with the mounts standing in it, the cursor recomputed
at every boundary. All of it is
[`MountedStore`](mounts.md#outrage.mounts.MountedStore) now, which *is* a
[`Store`](store.md#outrage.store.Store), so every handler here calls one store method and
shapes the answer. What is left that knows about mounts is configuration
(`--mount` at startup) and the two sentences a result carries about what a
delete would not reach -- because those are sentences, and a sentence is a front
end's business.

Two things a front end still does before anything routes. `?last` is resolved
against the whole namespace, since a `?last` naming a mount decides which store
answers; and an error is rendered, by [`outrage.messages`](messages.md#module-outrage.messages), from the code and
facts it carries.

### outrage.server.COPY_FAILURE_SAMPLE *= 5*

Failed transfers named in a copy's result before it stops listing and only
counts. A copy reports statistics because it may cross more keys than a
result can hold, and a bare failed: 12 is a number nobody can act on: the
sample is what says *what* went wrong, at a size that cannot grow with the
store.

### outrage.server.DEFAULT_COPY_LIMIT *= 500*

How many documents one copy_tree call carries before it stops and hands
back a cursor. Larger than a page limit on purpose: this bounds a *run*
rather than a result, since the caller is told counts however many crossed
and pays nothing per document for the ones that did. What it protects is the
length of one call, against a subtree nobody has counted.

### outrage.server.DEFAULT_ITEM_LIMIT *= 100*

What one tool call may return. The store offers pagination and takes no view;
this is the view. A tool answers into a context window, so an unwitting call
must not be able to fill one, and every capped result says what it was part
of.

Two caps rather than one tuned number, because the two failures are
different sizes. Characters are what fill a context window, so that is the
cap that binds a read of real documents: twenty thousand is ten documents at
the bulk cap. The item count is what keeps a page comprehensible when the
items are tiny -- a hundred titles is a survey a model can hold, and it is
the whole store for the session-scale case these defaults are mostly serving.

### outrage.server.DEFAULT_PAGE_CHARS *= 20000*

The character half of that pair: what one page may total before it stops,
whatever the item count still allows.

### outrage.server.DELIVERED *= ('essentials', 'tail')*

The documents delivered, in the order they are sent. The split is a delivery
order and not a subject: a client cuts these instructions at a length it does
not announce, so essentials is what has to survive the cut -- the grammar of
a key, how one is allocated, and that a listing is a page -- and tail is
chosen so that every part of it is recoverable somewhere a session reaches
anyway: a tool description, the packaged agent skill, or a failure that
explains itself. That test is the whole of what decides which document a
sentence belongs in, and outrage/skills is where it is written down for
whoever edits them.

### outrage.server.DELIVERY_BUDGET *= 2048*

What a client is assumed to deliver of a server's instructions before it
cuts them. An observation of one client, not a protocol guarantee: Claude
Code truncates at 2048 characters, measured on 2026-08-19 across this
project's own transcripts and again the day after. Whether the number is
fixed, shared between servers, or really a token count is unestablished -
2047 characters landing on a power of two is the argument for characters.
Everything ordered before this point survives on that client; everything
after it may not, and nothing may be *only* said after it.

### outrage.server.NO_README *= 'This store has no \`readme\` document. If you work out how it is organised, or what a later session should read first, store that there.'*

What is said when the store has no readme. The empty store is exactly where
naming the convention is worth most, since the session that goes on to learn
the layout is the one that can write it down.

### outrage.server.README_FLOOR_CHARS *= 600*

The smallest readme worth having a mechanism for: enough to name what a
store holds and point at two or three keys. `test_the_essentials_leave_room`
fails if the static text grows back over the cut, which is the failure that
produced all of this.

### outrage.server.README_HEADING *= "--- \`readme\`: this store's own introduction, so you start with it ---"*

How the readme is introduced, and the one thing about it a session cannot
work out for itself. Both are paid for out of the same budget as the readme
they wrap, so both say the least that is still true: the heading carries why
the document is here, the note carries when it was read. Everything else
about the convention is in the tail document, where it can afford to be.

### outrage.server.README_KEY *= 'readme'*

The key whose document introduces the store. One name, so that a session
arriving at a store nobody described to it has somewhere to look, and a
session that learns how one is organised has somewhere to write it.

### outrage.server.README_MAX_CHARS *= 667*

How much of the readme is carried, computed rather than chosen: whatever the
budget has left once the scaffolding is paid for. The old constant bounded
the wrong thing - it asked how long a routing document ought to be, when the
question the client actually answers is how much room is left before the
cut. That number was negative, so no readme of any length was ever
delivered. See project/reference/planned/instructions-budget.

### outrage.server.README_NOTE *= 'Read once, when the server started - a \`readme\` changed during a session reaches the next one, not this one.'*

The second half of that pair: when the readme was read, which is the one
thing about it a session cannot work out from the text itself.

### outrage.server.SCAFFOLDING_CHARS *= 1381*

What the readme's own block costs before a word of it is written: the
heading, the note below it, the blank lines between, and the essentials that
follow. Measured from the real strings, so editing any of them moves the cap.

### outrage.server.SKILLS *= 'skills'*

Where the delivered text is kept, below the shipped documentation's root.
Prose in a document rather than a string literal here: it is diffable,
carries a title, and is readable with retrieve_document like anything else
-- including by a session that was cut off mid-instructions and wants the
rest of them. The document at outrage/skills says which file is which.

### outrage.server.WITHOUT_META_SAMPLE *= 10*

Keys named in without_meta before it stops listing and only counts. Its
job is to warn that a survey under-reports the store, and a count does that
at any size; at reference scale the list would *be* the corpus.

### *class* outrage.server.RequestLog(log: [EventLog](eventlog.md#outrage.eventlog.EventLog))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Record every inbound message, from the layer that can still see the failures.

Wrapping the five tool functions instead would be simpler and would miss
the calls that matter most. An argument the server does not know is refused
by the tool's own argument model - see `_forbid_unknown_arguments` - and
that refusal becomes a `CallToolResult` carrying `is_error` without the
tool function ever being entered. A log wired inside those functions is
structurally blind to it, which would leave the one failure this server
goes out of its way to catch as the one failure it cannot record.

From here the raw parameters are visible before validation, `initialize`
is visible along with the client that sent it, and a refusal is visible
either as a raised error or as an error result. Both are recorded.

`MCPServer.middleware` is documented as provisional and expected to
change before v2 is final, so this depends on something that may move. The
risk is accepted on the same terms as `extra="forbid"`: what a change
would cost is logging silently ceasing to happen, and
`test_the_middleware_is_reached` fails loudly rather than letting it.

### outrage.server.build_server(store: [Store](store.md#outrage.store.Store), log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None, directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → MCPServer

Build a server exposing `store`, which may be one store or a mount table.

A lone `Store` is wrapped in a table of one rather than served by a
second path through this module. There is then no routing that only runs
when something is mounted, and the single store case exercises the same
code every call takes.

`directory` is the store directory, and it has to be passed in: what is
served is a [`MountedStore`](mounts.md#outrage.mounts.MountedStore), which is a `Store` and
not a [`FileStore`](store.md#outrage.store.FileStore), so it cannot be asked where it is.
[`main()`](#outrage.server.main) has already resolved it for the event log. Given one,
`document_file` is registered and writes under
[`EXPORT_DIR_NAME`](store.md#outrage.store.EXPORT_DIR_NAME) inside it; without one there is
nowhere to put a file, and the tool is not offered rather than offered and
always failing.

### outrage.server.instructions(store: [Store](store.md#outrage.store.Store)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

The root store's own readme, then the essentials, then the tail.

Delivered rather than requested. A line telling a session to go and read a
key is a line that can be read past, and this project has two records of
exactly that happening -- see planned/agents on trap 2, and
project/reference/agents on the search cascade. The readme costs no tool
call and cannot be skipped, which is the same argument that puts title in
the tool signature: reachable at the moment it applies, rather than
depending on somebody remembering it then.

The order is the whole point. A client cuts this text at some length it
does not announce -- `DELIVERY_BUDGET` records the one measurement there
is -- so what is written first is what survives, and the readme was last
for long enough that it never arrived once. What is at risk now is
the tail document, which is chosen to be the recoverable half.

Over `README_MAX_CHARS` nothing is inlined and the length is reported
instead. A silently shortened entry point would be the project's own
recurring failure at the one document meant to prevent it, and a reader
told the size can decide to go and read the rest.

The **root** store's readme, when there is a mount table. A mounted
store's own readme is not carried: the budget is spent to within a few
dozen characters -- see project/reference/planned/instructions-budget
for what the margin is today -- and a second readme is hundreds, so it
would push the first over the client's cut, which is the exact failure
that ordering exists to prevent. A mount announces itself in a listing
instead, where it costs nothing until somebody looks.

### outrage.server.main(argv: [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [int](https://docs.python.org/3/library/functions.html#int)

Open the configured stores and serve them over stdio until the client
stops.

The console script `outrage-server`, and the entry point an MCP client
launches. It resolves the store directory once -- the event log defaults to
a file beside it, and `document_file` writes under it, so both need the
same answer -- opens the mount table, warns on stderr about any mount that
shadows keys already held, and hands the table to [`build_server()`](#outrage.server.build_server).

Returns rather than exits, for the same reason [`outrage.cli.main()`](cli.md#outrage.cli.main) does.

### outrage.server.parse_args(argv: [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Namespace](https://docs.python.org/3/library/argparse.html#argparse.Namespace)

The server's command line: which stores to serve, and what to record.

Three groups of arguments, and the first two are the interesting pair.
`--dir` says which *directory* holds the stores, `--root-mount` and the
repeatable `--mount`/`--mount-ro` say which *files* inside it are
mounted where -- see `project/reference/planned/mounts`. `--log` and
`--log-content` say what is recorded about the calls that arrive.

The mount options may also be written in a file rather than typed --
[`outrage.mountfile`](mountfile.md#module-outrage.mountfile), and the whole point of it here: with a table in
the store directory, the `args` a client's JSON has to carry come down to
`--dir`. The file is spliced into `argv` before the parser sees it, so
everything below describes both.

Separate from [`main()`](#outrage.server.main) so that a test can ask what an argument list
parses to without opening a store or starting a server.

### outrage.server.skill(name: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

The text of one delivered document, read from the installed files.

The files rather than the mount, for two reasons. This is needed at import,
to size the readme against `DELIVERY_BUDGET`, which is before any store
is opened; and a mount table naming `outrage` overrides the shipped
documentation silently, which would otherwise let a project's own store
decide what this server says about itself.
[`outrage.shipped.tree()`](shipped.md#outrage.shipped.tree) is the same directory the mount reads, so the
two never disagree about what the text is.

Read once per process, which is what the text itself promises a session:
instructions are sent when a client connects, so a file edited afterwards
reaches the next server rather than this one.

A missing file is the build failure [`outrage.shipped.available()`](shipped.md#outrage.shipped.available)
exists to notice, and is raised rather than served as instructions with a
hole in them.

### outrage.server.static_instructions() → [str](https://docs.python.org/3/library/stdtypes.html#str)

Every delivered document, in order: what a client that does not truncate gets.

A function rather than a constant, and not only because the text is read
from files now. A module constant holding it is rendered *by value* into
the API reference, which put the whole of both documents back into the
generated page they had just been taken out of.
