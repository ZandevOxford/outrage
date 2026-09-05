# outrage.messages

Turning what the library carries into a sentence for a person.

Two kinds of thing reach a reader as prose, and both arrive here as a code and
its facts rather than as words. A **failure** is an
[`OutrageError`](errors.md#outrage.errors.OutrageError), raised by the layer that hit it. A
**note** is a [`Note`](notes.md#outrage.notes.Note) on an answer that *worked* -- the
document shrank, the write went past a check nobody could make -- carried on
the result object, because a success path has nothing to raise. Neither is
worded where it was found.

**Why the naming is a parameter.** There are two front ends and the right name
for a key differs between them. The command line opens one store directory and
knows nothing about a mount table, so a key it failed on is called exactly what
the store calls it. The MCP server presents one namespace across several
stores, so the same key has a longer name there -- `python/nope` inside the
store mounted at `ref` is `ref/python/nope` to any caller. A sentence built
where the failure happened is wrong for one of them and there is no third
answer. That was a live defect, not a hypothetical one.

So `name` is a function from the key the raising layer used to the key the
reader should see. It defaults to [`outrage.keys.displayed()`](keys.md#outrage.keys.displayed), which is the
right answer for a single store and spells the root `/` rather than as the
empty string that reads like a missing value.

An **error's** wording is shared rather than written per front end. Two copies
of the same sentence drift, and the drift is invisible until somebody compares
them.

A **note's** wording is not shared, and the difference is deliberate. Each
audience gets a table of its own -- [`MCP`](#outrage.messages.MCP) below is the tools' -- because
two front ends should remark on *different* situations and one of them should
often say nothing at all. A front end wanting its own selection brings its own
table rather than a branch inside a template here. So this file is the one
place an error's wording lives, and one of the places a note's does.

The next reader will want to unify the two mechanisms. The reason not to:

> An error **must always be reported**. Whoever catches it has to say
> something, so silence is not an option and only the spelling varies --
> hence one table, and [`Speller`](#outrage.messages.Speller) for the words that differ between
> readers. A note is **optional by nature**, so *which* notes are said is
> the primary question and the wording is secondary -- hence a table per
> audience, and no speller, because the table already is the audience: a
> command line's note writes `--unchanged-since` itself.

Different problems, different shapes. What makes the note side safe is the
guard in `tests/test_notes.py` that the error side does not need: **silence
must be deliberate.** A code an audience has no sentence for is a failure
unless that audience has said, with a reason, that it means to be quiet about
it -- otherwise "this front end is quiet for now" decays into permanent
silence by neglect and nothing ever notices.

### outrage.messages.MCP *= <outrage.messages.NoteTable object>*

What the MCP tools say about a note. The tools' spelling for an argument is
the library's own -- see [`keyword()`](#outrage.messages.keyword) -- so this table sits beside the
error wording both front ends share rather than in a module of its own.

Its entries are the sentences `server.py` composed by hand until the notes
on one document write moved here; the wording is theirs, and the naming is
no longer fixed to one store, since a table renders for whoever is reading.

### outrage.messages.Namer

How a key is named when nobody says otherwise: as one store sees it.

alias of [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`str`](https://docs.python.org/3/library/stdtypes.html#str)], [`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### *class* outrage.messages.NoteTable(audience: [str](https://docs.python.org/3/library/stdtypes.html#str))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

What one audience is told about a [`Note`](notes.md#outrage.notes.Note), if anything.

A table per audience rather than one table spelled two ways, for the reason
the module docstring gives: selection is the note side's primary question,
and a template that branched on who is reading would be one function with
two meanings -- the shape every message defect this project has had came
out of, two readings agreeing the day they are written and drifting after.

Two ways in, and a code must take exactly one of them. [`template()`](#outrage.messages.template)
says how this audience puts the situation; [`silent()`](#outrage.messages.NoteTable.silent) says that this
audience means not to mention it, and why. A code with neither is the
failure the guard exists for, because a table that may legitimately be
quiet cannot otherwise tell a decision from an omission.

The audience is the whole of the reader's identity here, so there is no
speller: a table belonging to the command line writes `--unchanged-since`
into its own sentence, and nothing has to be parameterised for it.

#### audience

Who this table words notes for, as a sentence would name them. It
is only ever read by a failure -- here or in the guards -- so it is
a phrase that can be read out in one, not an identifier.

#### template(code: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]], [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]]

Register how this audience says `code`.

The function takes the namer **positionally** and the note's details by
keyword, exactly as [`template()`](#outrage.messages.template) does above and for the same
reason: a detail may be called `name` without colliding with it.

#### silent(code: [str](https://docs.python.org/3/library/stdtypes.html#str), reason: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [None](https://docs.python.org/3/library/constants.html#None)

Declare that this audience says nothing about `code`, and why.

The reason is required and is the point of the call. "Not written yet"
is a legitimate one; what is not legitimate is the empty set entry that
reads the same whether somebody decided or nobody looked.

#### render(note: [Note](notes.md#outrage.notes.Note), name: [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[str](https://docs.python.org/3/library/stdtypes.html#str)], [str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)

`note` as one line for this audience, or `None` where it is silent.

`None` is a real answer -- this reader is not told -- and a caller
drops it. A code this table has never heard of is not that: it raises,
the way [`render()`](#outrage.messages.render) does for an error, because a note quietly lost
for want of an entry is indistinguishable from one deliberately not
said, which is the distinction the whole table exists to keep.

#### sentences() → [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]]

The codes this audience has words for, for the guards that check them.

#### silences() → [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)]

The codes it means not to mention, and why, for the same.

Kept apart from [`sentences()`](#outrage.messages.NoteTable.sentences) rather than merged into one table of
codes, because the guards ask different questions of the two: a code
nobody has words for anywhere is unreachable, while a code nobody has
*decided* about is the neglect this design is guarding against.

### outrage.messages.Speller

How an *argument* is spelled where the message will be read, and the second
half of the same rule [`Namer`](#outrage.messages.Namer) is the first half of. A key is called
something different behind a mount; an argument is called something
different at each front end -- `unchanged_since` to a tool call and
`--unchanged-since` to a shell -- and a sentence naming one of them in the
other's spelling tells its reader to type something that does not exist.
Live testing found exactly that: a command line user told to "Pass
on_conflict='overwrite-unchanged'", which is not a flag.

Called with the argument's name, and its value where naming the value is
what the sentence is about.

alias of [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### outrage.messages.codes() → [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]]

The whole table, for the test that checks it against the raise sites.

### outrage.messages.keyword(argument: [str](https://docs.python.org/3/library/stdtypes.html#str), value: [Any](https://docs.python.org/3/library/typing.html#typing.Any) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)

An argument as a keyword call writes it: what an MCP tool is passed.

The default, because it is the spelling a library's own argument already
has -- a sentence naming `unchanged_since` is right for anything calling
Python or the tools, and only a front end whose arguments are spelled some
other way has to say so.

### outrage.messages.render(error: [OutrageError](errors.md#outrage.errors.OutrageError), name: [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[str](https://docs.python.org/3/library/stdtypes.html#str)], [str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, spell: [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)

`error` as one line, named the way `name` and `spell` say.

Front ends call this; nothing else should. A code with no template is a
programming error and raises rather than falling back on something
plausible -- a message that silently degrades is how a caller ends up
reading a sentence that is not about their problem.

`spell` reaches a template as a keyword, so only the templates that name
an argument declare it and the rest go on absorbing it in `**_`. That is
why no error detail may be called `spell`, which `test_messages` pins.

### outrage.messages.template(code: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]], [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]]

Register the sentence for `code`.
