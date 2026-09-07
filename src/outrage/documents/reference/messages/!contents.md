# outrage.messages
0 0

### outrage.messages.MCP *= <outrage.messages.NoteTable object>*
4612 4612

### outrage.messages.Namer
5153 5153

### *class* outrage.messages.NoteTable(audience: str)
5481 5481

#### audience
6746 6746

#### template(code: str) → Callable[[Callable[[...], str]], Callable[[...], str]]
6953 6953

#### silent(code: str, reason: str) → None
7720 7722

#### render(note: Note, name: Callable[[str], str] | None = None) → str | None
8197 8201

#### sentences() → Mapping[str, Callable[[...], str]]
9103 9109

#### silences() → Mapping[str, str]
9505 9513

### outrage.messages.Speller
10105 10115

### outrage.messages.codes() → Mapping[str, Callable[[...], str]]
10990 11000

### outrage.messages.flag(argument: str, value: Any = None) → str
11403 11415

### outrage.messages.keyword(argument: str, value: Any = None) → str
12677 12691

### outrage.messages.render(error: OutrageError, name: Callable[[str], str] | None = None, \*, spell: Callable[[...], str] | None = None) → str
13234 13250

### outrage.messages.template(code: str) → Callable[[Callable[[...], str]], Callable[[...], str]]
14460 14478
