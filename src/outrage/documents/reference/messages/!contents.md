# outrage.messages
0 0 1

### outrage.messages.MCP *= <outrage.messages.NoteTable object>*
4612 4612 80

### outrage.messages.Namer
5153 5153 90

### *class* outrage.messages.NoteTable(audience: str)
5483 5483 96

#### audience
6750 6750 118

#### template(code: str) → Callable[[Callable[[...], str]], Callable[[...], str]]
6957 6957 124

#### silent(code: str, reason: str) → None
7727 7729 132

#### render(note: Note, name: Callable[[str], str] | None = None) → str | None
8207 8211 140

#### sentences() → Mapping[str, Callable[[...], str]]
9118 9124 150

#### silences() → Mapping[str, str]
9522 9530 154

### outrage.messages.Speller
10124 10134 163

### outrage.messages.codes() → Mapping[str, Callable[[...], str]]
11010 11020 179

### outrage.messages.flag(argument: str, value: Any = None) → str
11425 11437 183

### outrage.messages.keyword(argument: str, value: Any = None) → str
12701 12715 204

### outrage.messages.render(error: OutrageError, name: Callable[[str], str] | None = None, \*, spell: Callable[[...], str] | None = None) → str
13260 13276 213

### outrage.messages.template(code: str) → Callable[[Callable[[...], str]], Callable[[...], str]]
14492 14510 226
