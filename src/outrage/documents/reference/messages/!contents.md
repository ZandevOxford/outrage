# outrage.messages
0 0

### outrage.messages.MCP *= <outrage.messages.NoteTable object>*
3126 3126

### outrage.messages.Namer
3653 3653

### *class* outrage.messages.NoteTable(audience: [str](https://docs.python.org/3/library/stdtypes.html#str))
3981 3981

#### audience
5246 5246

#### template(code: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]], [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]]
5453 5453

#### silent(code: [str](https://docs.python.org/3/library/stdtypes.html#str), reason: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [None](https://docs.python.org/3/library/constants.html#None)
6220 6222

#### render(note: [Note](notes.md#outrage.notes.Note), name: [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[str](https://docs.python.org/3/library/stdtypes.html#str)], [str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
6697 6701

#### sentences() → [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]]
7603 7609

#### silences() → [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)]
8005 8013

### outrage.messages.Speller
8605 8615

### outrage.messages.codes() → [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]]
9490 9500

### outrage.messages.keyword(argument: [str](https://docs.python.org/3/library/stdtypes.html#str), value: [Any](https://docs.python.org/3/library/typing.html#typing.Any) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)
9903 9915

### outrage.messages.render(error: [OutrageError](errors.md#outrage.errors.OutrageError), name: [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[str](https://docs.python.org/3/library/stdtypes.html#str)], [str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, spell: [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)
10460 10474

### outrage.messages.template(code: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]], [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]]
11686 11702
