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
answer, which is the defect recorded in
`project/reference/planned/error-naming`.

So `name` is a function from the key the raising layer used to the key the
reader should see. It defaults to [`outrage.keys.displayed()`](keys.md#outrage.keys.displayed), which is the
right answer for a single store and spells the root `/` rather than as the
empty string that reads like a missing value.

Wording is shared rather than written per front end. Two copies of the same
sentence drift, and the drift is invisible until somebody compares them.

### outrage.messages.Namer

How a key is named when nobody says otherwise: as one store sees it.

alias of [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`str`](https://docs.python.org/3/library/stdtypes.html#str)], [`str`](https://docs.python.org/3/library/stdtypes.html#str)]

### outrage.messages.codes() → [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]]

The whole table, for the test that checks it against the raise sites.

### outrage.messages.render(error: [OutrageError](errors.md#outrage.errors.OutrageError), name: [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[str](https://docs.python.org/3/library/stdtypes.html#str)], [str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)

`error` as one line, with keys named the way `name` says.

Front ends call this; nothing else should. A code with no template is a
programming error and raises rather than falling back on something
plausible -- a message that silently degrades is how a caller ends up
reading a sentence that is not about their problem.

### outrage.messages.template(code: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]], [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]]

Register the sentence for `code`.
