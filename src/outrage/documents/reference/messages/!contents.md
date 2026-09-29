# outrage.messages
0 0 1

### outrage.messages.MCP *= <outrage.messages.NoteTable object>*
4763 4763 82

### outrage.messages.Namer
5304 5304 92

### *class* outrage.messages.NoteTable(audience: str)
5634 5634 98

#### audience
6901 6901 120

#### template(code: str) → Callable[[Callable[[...], str]], Callable[[...], str]]
7108 7108 126

#### silent(code: str, reason: str) → None
7878 7880 134

#### render(note: Note, name: Callable[[str], str] | None = None) → str | None
8358 8362 142

#### sentences() → Mapping[str, Callable[[...], str]]
9269 9275 152

#### silences() → Mapping[str, str]
9673 9681 156

### outrage.messages.Speller
10275 10285 165

### outrage.messages.codes() → Mapping[str, Callable[[...], str]]
11161 11171 181

### outrage.messages.flag(argument: str, value: Any = None) → str
11576 11588 185

### outrage.messages.keyword(argument: str, value: Any = None) → str
12852 12866 206

### outrage.messages.not_opened(mount_point: str, error: OutrageError) → str
13411 13427 215

### outrage.messages.render(error: OutrageError, name: Callable[[str], str] | None = None, \*, spell: Callable[[...], str] | None = None) → str
13910 13928 223

### outrage.messages.template(code: str) → Callable[[Callable[[...], str]], Callable[[...], str]]
15142 15162 236
