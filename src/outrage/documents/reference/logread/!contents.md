# outrage.logread
0 0

### outrage.logread.MESSAGE_CHARS *= 110*
1196 1196

### *class* outrage.logread.Event(line: int, record: dict[str, Any])
1451 1451

#### line *: int*
2216 2216

#### record *: dict[str, Any]*
2291 2291

#### *property* event *: str*
2494 2494

#### *property* session *: str*
2580 2580

#### *property* seq *: int*
2668 2668

#### *property* call *: int | None*
2753 2753

#### *property* ts *: str*
2903 2903

#### *property* ms *: float | None*
2986 2986

#### *property* op *: str | None*
3138 3138

#### *property* method *: str | None*
3326 3326

#### *property* tool *: str | None*
3525 3525

#### *property* args *: dict[str, Any]*
3717 3717

#### *property* key *: str | None*
4244 4244

#### *property* result *: dict[str, Any] | None*
4392 4392

#### *property* error *: dict[str, Any] | None*
4670 4670

#### *property* content *: dict[str, Any] | None*
5281 5281

#### *property* next_offset *: int | None*
5625 5625

### *class* outrage.logread.Filter(session: str | None = None, call: int | None = None, op: str | None = None, method: str | None = None, event: str | None = None, key: str | None = None, errors: bool = False)
5853 5853

#### session *: str | None* *= None*
6946 6946

#### call *: int | None* *= None*
7096 7096

#### op *: str | None* *= None*
7244 7244

#### method *: str | None* *= None*
7389 7389

#### event *: str | None* *= None*
7538 7538

#### key *: str | None* *= None*
7686 7686

#### errors *: bool* *= False*
7832 7832

#### matches(event: Event) → bool
7921 7921

#### select(events: Iterable[Event]) → list[Event]
8323 8325

### *class* outrage.logread.Log(path: Path, events: list[Event] = <factory>, malformed: list[int] = <factory>)
8842 8846

#### path *: Path*
9343 9347

#### events *: list[Event]*
9426 9430

#### malformed *: list[int]*
9537 9541

#### *property* sessions *: list[Session]*
9679 9683

### *exception* outrage.logread.LogError(code: str, \*\*details: Any)
9807 9811

### *class* outrage.logread.Session(id: str, events: list[Event] = <factory>)
10133 10137

#### id *: str*
10496 10500

#### events *: list[Event]*
10568 10572

#### *property* start *: Event | None*
10679 10683

#### *property* pid *: int | None*
10870 10874

#### *property* version *: str | None*
11019 11023

#### *property* first_ts *: str*
11171 11175

#### *property* last_ts *: str*
11260 11264

#### *property* calls *: list[int]*
11348 11352

#### *property* tool_calls *: int*
11531 11535

#### *property* store_accesses *: int*
11623 11627

#### *property* is_discovery *: bool*
11719 11723

### *class* outrage.logread.Summary(path: Path, lines: int = 0, malformed: int = 0, sessions: list[Session] = <factory>, calls: int = 0, store_accesses: int = 0, accesses_per_call: Counter[tuple[str, int]]=<factory>, ops: Counter[str] = <factory>, methods: Counter[str] = <factory>, tools: Counter[str] = <factory>, errors: Counter[str] = <factory>, refused: int = 0, reads: int = 0, truncated: list[TruncatedRead] = <factory>, documents_truncated: int = 0)
12350 12354

#### path *: Path*
14104 14108

#### lines *: int* *= 0*
14187 14191

#### malformed *: int* *= 0*
14269 14273

#### sessions *: list[Session]*
14355 14359

#### calls *: int* *= 0*
14472 14476

#### store_accesses *: int* *= 0*
14554 14558

#### accesses_per_call *: Counter[tuple[str, int]]*
14645 14649

#### ops *: Counter[str]*
15171 15175

#### methods *: Counter[str]*
15327 15331

#### tools *: Counter[str]*
15487 15491

#### errors *: Counter[str]*
15645 15649

#### refused *: int* *= 0*
15804 15808

#### reads *: int* *= 0*
15888 15892

#### truncated *: list[TruncatedRead]*
15970 15974

#### documents_truncated *: int* *= 0*
16100 16104

#### *property* busiest_call *: tuple[int, str, int] | None*
16196 16200

#### *property* mean_accesses *: float*
16742 16750

#### *property* followed_up *: int*
17108 17116

### *class* outrage.logread.TruncatedRead(read: Event, resumed_by: Event | None)
17449 17457

#### read *: Event*
17788 17796

#### resumed_by *: Event | None*
17835 17843

#### *property* followed_up *: bool*
17952 17960

### outrage.logread.format_event(event: Event, \*, content: bool = False) → Iterator[str]
18324 18332

### outrage.logread.format_session(session: Session) → str
18912 18922

### outrage.logread.format_summary(summary: Summary) → Iterator[str]
19126 19138

### outrage.logread.read_log(path: str | PathLike[str]) → Log
19430 19444

### outrage.logread.sessions(events: Iterable[Event]) → list[Session]
20031 20047

### outrage.logread.summarise(log: Log, events: Iterable[Event] | None = None) → Summary
20593 20611

### outrage.logread.truncated_reads(session: Session) → list[TruncatedRead]
21122 21142
