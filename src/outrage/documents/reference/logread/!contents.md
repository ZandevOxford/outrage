# outrage.logread
0 0 1

### outrage.logread.MESSAGE_CHARS *= 110*
1301 1301 26

### *class* outrage.logread.Event(line: int, record: dict[str, Any])
1556 1556 32

#### line *: int*
2325 2325 44

#### record *: dict[str, Any]*
2401 2401 46

#### *property* event *: str*
2606 2606 48

#### *property* session *: str*
2693 2693 50

#### *property* seq *: int*
2782 2782 52

#### *property* call *: int | None*
2868 2868 54

#### *property* ts *: str*
3020 3020 56

#### *property* ms *: float | None*
3104 3104 58

#### *property* op *: str | None*
3258 3258 60

#### *property* method *: str | None*
3448 3448 64

#### *property* tool *: str | None*
3649 3649 68

#### *property* args *: dict[str, Any]*
3843 3843 72

#### *property* key *: str | None*
4372 4372 81

#### *property* result *: dict[str, Any] | None*
4522 4522 83

#### *property* error *: dict[str, Any] | None*
4803 4803 85

#### *property* content *: dict[str, Any] | None*
5417 5417 95

#### *property* next_offset *: int | None*
5764 5764 99

### *class* outrage.logread.Filter(session: str | None = None, call: int | None = None, op: str | None = None, method: str | None = None, event: str | None = None, key: str | None = None, errors: bool = False)
5994 5994 103

#### session *: str | None* *= None*
7101 7101 109

#### call *: int | None* *= None*
7253 7253 111

#### op *: str | None* *= None*
7403 7403 113

#### method *: str | None* *= None*
7550 7550 115

#### event *: str | None* *= None*
7701 7701 117

#### key *: str | None* *= None*
7851 7851 119

#### errors *: bool* *= False*
7999 7999 121

#### matches(event: Event) → bool
8089 8089 123

#### select(events: Iterable[Event]) → list[Event]
8492 8494 132

### *class* outrage.logread.Log(path: Path, events: list[Event] = <factory>, malformed: list[int] = <factory>)
9012 9016 140

#### path *: Path*
9517 9521 146

#### events *: list[Event]*
9600 9604 148

#### malformed *: list[int]*
9712 9716 150

#### *property* sessions *: list[Session]*
9856 9860 152

### *exception* outrage.logread.LogError(code: str, \*\*details: Any)
9985 9989 154

### *class* outrage.logread.Session(id: str, events: list[Event] = <factory>)
10312 10316 160

#### id *: str*
10678 10682 166

#### events *: list[Event]*
10751 10755 168

#### *property* start *: Event | None*
10863 10867 170

#### *property* pid *: int | None*
11055 11059 174

#### *property* version *: str | None*
11206 11210 176

#### *property* first_ts *: str*
11360 11364 178

#### *property* last_ts *: str*
11450 11454 180

#### *property* calls *: list[int]*
11539 11543 182

#### *property* tool_calls *: int*
11724 11728 186

#### *property* store_accesses *: int*
11817 11821 188

#### *property* is_discovery *: bool*
11914 11918 190

### *class* outrage.logread.Summary(path: Path, lines: int = 0, malformed: int = 0, sessions: list[Session] = <factory>, calls: int = 0, store_accesses: int = 0, accesses_per_call: Counter[tuple[str, int]]=<factory>, ops: Counter[str] = <factory>, methods: Counter[str] = <factory>, tools: Counter[str] = <factory>, errors: Counter[str] = <factory>, refused: int = 0, reads: int = 0, truncated: list[TruncatedRead] = <factory>, documents_truncated: int = 0)
12546 12550 203

#### path *: Path*
14314 14318 209

#### lines *: int* *= 0*
14397 14401 211

#### malformed *: int* *= 0*
14480 14484 213

#### sessions *: list[Session]*
14567 14571 215

#### calls *: int* *= 0*
14685 14689 217

#### store_accesses *: int* *= 0*
14768 14772 219

#### accesses_per_call *: Counter[tuple[str, int]]*
14860 14864 221

#### ops *: Counter[str]*
15389 15393 228

#### methods *: Counter[str]*
15546 15550 230

#### tools *: Counter[str]*
15707 15711 232

#### errors *: Counter[str]*
15866 15870 234

#### refused *: int* *= 0*
16026 16030 236

#### reads *: int* *= 0*
16111 16115 238

#### truncated *: list[TruncatedRead]*
16194 16198 240

#### documents_truncated *: int* *= 0*
16325 16329 242

#### *property* busiest_call *: tuple[int, str, int] | None*
16422 16426 244

#### *property* mean_accesses *: float*
16973 16981 251

#### *property* followed_up *: int*
17340 17348 260

### *class* outrage.logread.TruncatedRead(read: Event, resumed_by: Event | None)
17682 17690 268

#### read *: Event*
18023 18031 274

#### resumed_by *: Event | None*
18070 18078 276

#### *property* followed_up *: bool*
18188 18196 278

### outrage.logread.format_event(event: Event, \*, content: bool = False) → Iterator[str]
18561 18569 287

### outrage.logread.format_session(session: Session) → str
19151 19161 295

### outrage.logread.format_summary(summary: Summary) → Iterator[str]
19366 19378 299

### outrage.logread.read_log(path: str | PathLike[str]) → Log
19671 19685 303

### outrage.logread.sessions(events: Iterable[Event]) → list[Session]
20274 20290 312

### outrage.logread.summarise(log: Log, events: Iterable[Event] | None = None) → Summary
20837 20855 320

### outrage.logread.truncated_reads(session: Session) → list[TruncatedRead]
21367 21387 327
