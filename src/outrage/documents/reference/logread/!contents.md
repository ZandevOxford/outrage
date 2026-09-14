# outrage.logread
0 0

### outrage.logread.MESSAGE_CHARS *= 110*
1196 1196

### *class* outrage.logread.Event(line: int, record: dict[str, Any])
1451 1451

#### line *: int*
2220 2220

#### record *: dict[str, Any]*
2296 2296

#### *property* event *: str*
2501 2501

#### *property* session *: str*
2588 2588

#### *property* seq *: int*
2677 2677

#### *property* call *: int | None*
2763 2763

#### *property* ts *: str*
2915 2915

#### *property* ms *: float | None*
2999 2999

#### *property* op *: str | None*
3153 3153

#### *property* method *: str | None*
3343 3343

#### *property* tool *: str | None*
3544 3544

#### *property* args *: dict[str, Any]*
3738 3738

#### *property* key *: str | None*
4267 4267

#### *property* result *: dict[str, Any] | None*
4417 4417

#### *property* error *: dict[str, Any] | None*
4698 4698

#### *property* content *: dict[str, Any] | None*
5312 5312

#### *property* next_offset *: int | None*
5659 5659

### *class* outrage.logread.Filter(session: str | None = None, call: int | None = None, op: str | None = None, method: str | None = None, event: str | None = None, key: str | None = None, errors: bool = False)
5889 5889

#### session *: str | None* *= None*
6996 6996

#### call *: int | None* *= None*
7148 7148

#### op *: str | None* *= None*
7298 7298

#### method *: str | None* *= None*
7445 7445

#### event *: str | None* *= None*
7596 7596

#### key *: str | None* *= None*
7746 7746

#### errors *: bool* *= False*
7894 7894

#### matches(event: Event) → bool
7984 7984

#### select(events: Iterable[Event]) → list[Event]
8387 8389

### *class* outrage.logread.Log(path: Path, events: list[Event] = <factory>, malformed: list[int] = <factory>)
8907 8911

#### path *: Path*
9412 9416

#### events *: list[Event]*
9495 9499

#### malformed *: list[int]*
9607 9611

#### *property* sessions *: list[Session]*
9751 9755

### *exception* outrage.logread.LogError(code: str, \*\*details: Any)
9880 9884

### *class* outrage.logread.Session(id: str, events: list[Event] = <factory>)
10207 10211

#### id *: str*
10573 10577

#### events *: list[Event]*
10646 10650

#### *property* start *: Event | None*
10758 10762

#### *property* pid *: int | None*
10950 10954

#### *property* version *: str | None*
11101 11105

#### *property* first_ts *: str*
11255 11259

#### *property* last_ts *: str*
11345 11349

#### *property* calls *: list[int]*
11434 11438

#### *property* tool_calls *: int*
11619 11623

#### *property* store_accesses *: int*
11712 11716

#### *property* is_discovery *: bool*
11809 11813

### *class* outrage.logread.Summary(path: Path, lines: int = 0, malformed: int = 0, sessions: list[Session] = <factory>, calls: int = 0, store_accesses: int = 0, accesses_per_call: Counter[tuple[str, int]]=<factory>, ops: Counter[str] = <factory>, methods: Counter[str] = <factory>, tools: Counter[str] = <factory>, errors: Counter[str] = <factory>, refused: int = 0, reads: int = 0, truncated: list[TruncatedRead] = <factory>, documents_truncated: int = 0)
12441 12445

#### path *: Path*
14209 14213

#### lines *: int* *= 0*
14292 14296

#### malformed *: int* *= 0*
14375 14379

#### sessions *: list[Session]*
14462 14466

#### calls *: int* *= 0*
14580 14584

#### store_accesses *: int* *= 0*
14663 14667

#### accesses_per_call *: Counter[tuple[str, int]]*
14755 14759

#### ops *: Counter[str]*
15284 15288

#### methods *: Counter[str]*
15441 15445

#### tools *: Counter[str]*
15602 15606

#### errors *: Counter[str]*
15761 15765

#### refused *: int* *= 0*
15921 15925

#### reads *: int* *= 0*
16006 16010

#### truncated *: list[TruncatedRead]*
16089 16093

#### documents_truncated *: int* *= 0*
16220 16224

#### *property* busiest_call *: tuple[int, str, int] | None*
16317 16321

#### *property* mean_accesses *: float*
16868 16876

#### *property* followed_up *: int*
17235 17243

### *class* outrage.logread.TruncatedRead(read: Event, resumed_by: Event | None)
17577 17585

#### read *: Event*
17918 17926

#### resumed_by *: Event | None*
17965 17973

#### *property* followed_up *: bool*
18083 18091

### outrage.logread.format_event(event: Event, \*, content: bool = False) → Iterator[str]
18456 18464

### outrage.logread.format_session(session: Session) → str
19046 19056

### outrage.logread.format_summary(summary: Summary) → Iterator[str]
19261 19273

### outrage.logread.read_log(path: str | PathLike[str]) → Log
19566 19580

### outrage.logread.sessions(events: Iterable[Event]) → list[Session]
20169 20185

### outrage.logread.summarise(log: Log, events: Iterable[Event] | None = None) → Summary
20732 20750

### outrage.logread.truncated_reads(session: Session) → list[TruncatedRead]
21262 21282
