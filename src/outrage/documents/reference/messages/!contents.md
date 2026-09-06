# outrage.messages
0 0

### outrage.messages.MCP *= <outrage.messages.NoteTable object>*
4612 4612

### outrage.messages.Namer
5153 5153

### *class* outrage.messages.NoteTable(audience: [str](https://docs.python.org/3/library/stdtypes.html#str))
5481 5481

#### audience
6746 6746

#### template(code: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]], [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]]
6953 6953

#### silent(code: [str](https://docs.python.org/3/library/stdtypes.html#str), reason: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [None](https://docs.python.org/3/library/constants.html#None)
7720 7722

#### render(note: [Note](notes.md#outrage.notes.Note), name: [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[str](https://docs.python.org/3/library/stdtypes.html#str)], [str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
8197 8201

#### sentences() → [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]]
9103 9109

#### silences() → [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)]
9505 9513

### outrage.messages.Speller
10105 10115

### outrage.messages.codes() → [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]]
10990 11000

### outrage.messages.flag(argument: [str](https://docs.python.org/3/library/stdtypes.html#str), value: [Any](https://docs.python.org/3/library/typing.html#typing.Any) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)
11403 11415

### outrage.messages.keyword(argument: [str](https://docs.python.org/3/library/stdtypes.html#str), value: [Any](https://docs.python.org/3/library/typing.html#typing.Any) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)
12677 12691

### outrage.messages.render(error: [OutrageError](errors.md#outrage.errors.OutrageError), name: [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[str](https://docs.python.org/3/library/stdtypes.html#str)], [str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, spell: [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)
13234 13250

### outrage.messages.template(code: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]], [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [str](https://docs.python.org/3/library/stdtypes.html#str)]]
14460 14478
