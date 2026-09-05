# outrage.messages

Turning a [`OutrageError`](errors.md#outrage.errors.OutrageError) into a sentence for a person.

The one place wording lives. The layers that *raise* carry facts and a code
(see [`outrage.errors`](errors.md#module-outrage.errors)); this renders them, and the front end says how a key
should be named.

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

Wording is shared rather than written per front end. Two copies of the same
sentence drift, and the drift is invisible until somebody compares them.

### outrage.messages.Namer

How a key is named when nobody says otherwise: as one store sees it.

alias of [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`str`](https://docs.python.org/3/library/stdtypes.html#str)], [`str`](https://docs.python.org/3/library/stdtypes.html#str)]

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
