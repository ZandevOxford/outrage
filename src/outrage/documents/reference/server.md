# outrage.server

MCP server exposing the document store.

A thin wrapper: argument shaping and result shaping only. All behaviour lives
in [`outrage.store`](store.md#module-outrage.store), so it can be exercised without a protocol harness.

**Including the mount table.** More than one store behind one key namespace is
not this module's work -- not the routing, the segment list a subtree is read
as, the merge of a level with the mounts standing in it, nor the cursor
recomputed at every boundary. All of it is
[`MountedStore`](mounts.md#outrage.mounts.MountedStore), which *is* a
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

### outrage.server.DEFAULT_SEARCH_SCAN_LIMIT *= 20*

Candidate documents one search call examines before returning a cursor.

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

### outrage.server.NO_README *= 'This store has no \`readme\` document. Try reading \`outrage/readme\` instead for instructions.'*

What is said when the store has no readme. The empty store is exactly where
naming the convention is worth most, since the session that goes on to learn
the layout is the one that can write it down.

### outrage.server.PROTECTED_CHARS *= 863*

What is delivered ahead of the tail, and so everything that has to survive
the client's cut: the readme line and the essentials. Measured from the real
strings rather than estimated, so editing either moves it, and
`test_the_delivered_text_fits_the_budget` fails when it passes
`DELIVERY_BUDGET`. It no longer varies with the store: what the readme
costs here is the length of the sentence naming it.

### outrage.server.READ_README *= 'This store has a \`readme\` document covering project conventions. Read it before starting.'*

What is said about the readme instead of carrying it: that there is one, and
to read it before anything else. A fixed cost, where the document itself cost
whatever that project's conventions happened to run to.

### outrage.server.README_KEY *= 'readme'*

The key whose document introduces the store. One name, so that a session
arriving at a store nobody described to it has somewhere to look, and a
session that learns how one is organised has somewhere to write it.

### outrage.server.SKILLS *= 'skills'*

Where the delivered text is kept, below the shipped documentation's root.
Prose in a document rather than a string literal here: it is diffable,
carries a title, and is readable with read_document like anything else
-- including by a session that was cut off mid-instructions and wants the
rest of them. The document at outrage/skills says which file is which.

### outrage.server.TOOLS *= 'tools'*

Where the MCP tools' descriptions are kept, below the shipped documentation
root. Like [`SKILLS`](#outrage.server.SKILLS), these are documents rather than string literals:
they are diffable, readable through the mounted manual, and shipped in the
same package as the code that registers them.

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

### outrage.server.build_server(store: [Store](store.md#outrage.store.Store), log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None, directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, all_tools: [bool](https://docs.python.org/3/library/functions.html#bool) = False, info_tool: [bool](https://docs.python.org/3/library/functions.html#bool) = True, mount_config: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = ()) → MCPServer

Build a server exposing `store`, which may be one store or a mount table.

A lone `Store` is wrapped in a table of one rather than served by a
second path through this module. There is then no routing that only runs
when something is mounted, and the single store case exercises the same
code every call takes.

`directory` is the store directory, and it has to be passed in: what is
served is a [`MountedStore`](mounts.md#outrage.mounts.MountedStore), which is a `Store` and
not a [`FileStore`](store.md#outrage.store.FileStore), so it cannot be asked where it is.
[`main()`](#outrage.server.main) has already resolved it for the event log, which is what still
wants it.

`document_edit` does not need it. It writes to
[`export_root()`](bulk.md#outrage.bulk.export_root), a per-user directory below the system
temporary directory, which always exists -- so the tool is registered
unconditionally rather than only where there is a store directory to write
under.

`ingest_document` is the one tool that is not. It needs the optional
`documents` extra, and a client offered a tool whose every call refuses
has been told the store can do something it cannot; the tools a session
lists should be the tools it can use.

`all_tools` registers it anyway, for `tools/render_tools.py`. The
shipped tool documentation describes the server rather than one
installation of it, so it must not gain or lose a tool according to what
happened to be installed where it was generated. It is the only caller that
wants this: a real server passes nothing and offers what it can do.

`info_tool` is the other tool that may be absent, and it is absent
because somebody said so rather than because anything is missing. What it
reports is a list of absolute paths into the machine the server runs on,
which is worth having by default and worth being able to withhold; the
server's `--no-info` is how it is withheld. `all_tools` overrides this
too, for the same reason.

`mount_config` is the one thing that tool needs and this server cannot
work out: the configuration files the mount table was read from, which
[`outrage.mountfile.sources()`](mountfile.md#outrage.mountfile.sources) knows and which are flattened away by the
time there is a table.

### outrage.server.instructions(store: [Store](store.md#outrage.store.Store)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

A line naming the root store's readme, then the essentials, then the tail.

The readme is **named, not carried**. The argument for inlining it holds as
far as it goes: a line telling a session to go and read a key is a line that
can be read past, and this project has watched exactly that happen twice.

What settled it the other way is that the length of a store's entry point
is the project's business, not this server's. Carrying it means capping it,
and the cap was `DELIVERY_BUDGET` minus whatever the static text happened
to cost -- 667 characters when this changed. No conventions worth writing
down fit that reliably, and different projects' will not fit the same
number at all: this store's own readme went to 1898 characters the moment
it listed its namespaces, and the readme shipped as the default is 2560.
Over the cap nothing was inlined and the length was reported instead, which
is a failure mode that arrives *silently* at the one document meant to
prevent silent failure -- it looks like delivery until somebody starts a
fresh session and reads what actually came.

So the cost is fixed and small, the readme can be whatever the project needs,
and what makes the line hard to read past is that it is first and the
session has not yet done anything. Two things carry the risk that it is
read past anyway: the tail document says what a readme is for, and a
host that loads project instructions of its own can say it a second time.

The order still decides what survives. A client cuts this text at some
length it does not announce, so what is written first is what a session
gets, and the tail document is last because it is the recoverable half.
`PROTECTED_CHARS` is what everything ahead of it costs.

The **root** store's readme, when there is a mount table. A mounted store's
own is not named either: a session that has not yet read the root's cannot
act on a second, and a mount announces itself in a listing instead, where
it costs nothing until somebody looks.

### outrage.server.main(argv: [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [int](https://docs.python.org/3/library/functions.html#int)

Open the configured stores and serve them over stdio until the client
stops.

The console script `outrage-server`, and the entry point an MCP client
launches. It resolves the store directory once -- the event log defaults to
a file beside it -- opens the mount table, warns on stderr about any mount that
shadows keys already held, and hands the table to [`build_server()`](#outrage.server.build_server).

Returns rather than exits, for the same reason [`outrage.cli.main()`](cli.md#outrage.cli.main) does.

### outrage.server.parse_args(argv: [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Namespace](https://docs.python.org/3/library/argparse.html#argparse.Namespace)

The server's command line: which stores to serve, and what to record.

Four groups of arguments, and the first two are the interesting pair.
`--dir` says which *directory* holds the stores, `--root-mount` and the
repeatable `--mount`/`--mount-ro` say which *files* inside it are
mounted where. `--log` and
`--log-content` say what is recorded about the calls that arrive, and
`--no-info` withholds the one tool that describes any of it.

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

### outrage.server.tool_description(name: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

The description of one MCP tool, read from the installed documents.

The same contract as [`skill()`](#outrage.server.skill): the installed file is read once per
process, before the tool is registered, and a build that dropped it fails
loudly instead of exposing a tool with an empty or stale description.
Keeping the description in the documentation tree also makes the bytes a
session receives available at `outrage/tools/<name>`.
