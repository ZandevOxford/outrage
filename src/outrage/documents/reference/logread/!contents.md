# outrage.logread
0 0 1

### outrage.logread.MESSAGE_CHARS *= 110*
1196 1196 24

### *class* outrage.logread.Event(line: int, record: dict[str, Any])
1451 1451 30

#### line *: int*
2220 2220 42

#### record *: dict[str, Any]*
2296 2296 44

#### *property* event *: str*
2501 2501 46

#### *property* session *: str*
2588 2588 48

#### *property* seq *: int*
2677 2677 50

#### *property* call *: int | None*
2763 2763 52

#### *property* ts *: str*
2915 2915 54

#### *property* ms *: float | None*
2999 2999 56

#### *property* op *: str | None*
3153 3153 58

#### *property* method *: str | None*
3343 3343 62

#### *property* tool *: str | None*
3544 3544 66

#### *property* args *: dict[str, Any]*
3738 3738 70

#### *property* key *: str | None*
4267 4267 79

#### *property* result *: dict[str, Any] | None*
4417 4417 81

#### *property* error *: dict[str, Any] | None*
4698 4698 83

#### *property* content *: dict[str, Any] | None*
5312 5312 93

#### *property* next_offset *: int | None*
5659 5659 97

### *class* outrage.logread.Filter(session: str | None = None, call: int | None = None, op: str | None = None, method: str | None = None, event: str | None = None, key: str | None = None, errors: bool = False)
5889 5889 101

#### session *: str | None* *= None*
6996 6996 107

#### call *: int | None* *= None*
7148 7148 109

#### op *: str | None* *= None*
7298 7298 111

#### method *: str | None* *= None*
7445 7445 113

#### event *: str | None* *= None*
7596 7596 115

#### key *: str | None* *= None*
7746 7746 117

#### errors *: bool* *= False*
7894 7894 119

#### matches(event: Event) → bool
7984 7984 121

#### select(events: Iterable[Event]) → list[Event]
8387 8389 130

### *class* outrage.logread.Log(path: Path, events: list[Event] = <factory>, malformed: list[int] = <factory>)
8907 8911 138

#### path *: Path*
9412 9416 144

#### events *: list[Event]*
9495 9499 146

#### malformed *: list[int]*
9607 9611 148

#### *property* sessions *: list[Session]*
9751 9755 150

### *exception* outrage.logread.LogError(code: str, \*\*details: Any)
9880 9884 152

### *class* outrage.logread.Session(id: str, events: list[Event] = <factory>)
10207 10211 158

#### id *: str*
10573 10577 164

#### events *: list[Event]*
10646 10650 166

#### *property* start *: Event | None*
10758 10762 168

#### *property* pid *: int | None*
10950 10954 172

#### *property* version *: str | None*
11101 11105 174

#### *property* first_ts *: str*
11255 11259 176

#### *property* last_ts *: str*
11345 11349 178

#### *property* calls *: list[int]*
11434 11438 180

#### *property* tool_calls *: int*
11619 11623 184

#### *property* store_accesses *: int*
11712 11716 186

#### *property* is_discovery *: bool*
11809 11813 188

### *class* outrage.logread.Summary(path: Path, lines: int = 0, malformed: int = 0, sessions: list[Session] = <factory>, calls: int = 0, store_accesses: int = 0, accesses_per_call: Counter[tuple[str, int]]=<factory>, ops: Counter[str] = <factory>, methods: Counter[str] = <factory>, tools: Counter[str] = <factory>, errors: Counter[str] = <factory>, refused: int = 0, reads: int = 0, truncated: list[TruncatedRead] = <factory>, documents_truncated: int = 0)
12441 12445 201

#### path *: Path*
14209 14213 207

#### lines *: int* *= 0*
14292 14296 209

#### malformed *: int* *= 0*
14375 14379 211

#### sessions *: list[Session]*
14462 14466 213

#### calls *: int* *= 0*
14580 14584 215

#### store_accesses *: int* *= 0*
14663 14667 217

#### accesses_per_call *: Counter[tuple[str, int]]*
14755 14759 219

#### ops *: Counter[str]*
15284 15288 226

#### methods *: Counter[str]*
15441 15445 228

#### tools *: Counter[str]*
15602 15606 230

#### errors *: Counter[str]*
15761 15765 232

#### refused *: int* *= 0*
15921 15925 234

#### reads *: int* *= 0*
16006 16010 236

#### truncated *: list[TruncatedRead]*
16089 16093 238

#### documents_truncated *: int* *= 0*
16220 16224 240

#### *property* busiest_call *: tuple[int, str, int] | None*
16317 16321 242

#### *property* mean_accesses *: float*
16868 16876 249

#### *property* followed_up *: int*
17235 17243 258

### *class* outrage.logread.TruncatedRead(read: Event, resumed_by: Event | None)
17577 17585 266

#### read *: Event*
17918 17926 272

#### resumed_by *: Event | None*
17965 17973 274

#### *property* followed_up *: bool*
18083 18091 276

### outrage.logread.format_event(event: Event, \*, content: bool = False) → Iterator[str]
18456 18464 285

### outrage.logread.format_session(session: Session) → str
19046 19056 293

### outrage.logread.format_summary(summary: Summary) → Iterator[str]
19261 19273 297

### outrage.logread.read_log(path: str | PathLike[str]) → Log
19566 19580 301

### outrage.logread.sessions(events: Iterable[Event]) → list[Session]
20169 20185 310

### outrage.logread.summarise(log: Log, events: Iterable[Event] | None = None) → Summary
20732 20750 318

### outrage.logread.truncated_reads(session: Session) → list[TruncatedRead]
21262 21282 325
