# outrage.logread
0 0

### outrage.logread.MESSAGE_CHARS *= 110*
1196 1196

### *class* outrage.logread.Event(line: [int](https://docs.python.org/3/library/functions.html#int), record: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)])
1451 1451

#### line *: [int](https://docs.python.org/3/library/functions.html#int)*
2216 2216

#### record *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*
2291 2291

#### *property* event *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
2494 2494

#### *property* session *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
2580 2580

#### *property* seq *: [int](https://docs.python.org/3/library/functions.html#int)*
2668 2668

#### *property* call *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*
2753 2753

#### *property* ts *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
2903 2903

#### *property* ms *: [float](https://docs.python.org/3/library/functions.html#float) | [None](https://docs.python.org/3/library/constants.html#None)*
2986 2986

#### *property* op *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
3138 3138

#### *property* method *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
3326 3326

#### *property* tool *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
3525 3525

#### *property* args *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*
3717 3717

#### *property* key *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
4244 4244

#### *property* result *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None)*
4392 4392

#### *property* error *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None)*
4670 4670

#### *property* content *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None)*
5281 5281

#### *property* next_offset *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*
5625 5625

### *class* outrage.logread.Filter(session: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, call: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, op: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, method: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, event: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, errors: [bool](https://docs.python.org/3/library/functions.html#bool) = False)
5853 5853

#### session *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*
6946 6946

#### call *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*
7096 7096

#### op *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*
7244 7244

#### method *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*
7389 7389

#### event *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*
7538 7538

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*
7686 7686

#### errors *: [bool](https://docs.python.org/3/library/functions.html#bool)* *= False*
7832 7832

#### matches(event: [Event](#outrage.logread.Event)) → [bool](https://docs.python.org/3/library/functions.html#bool)
7921 7921

#### select(events: [Iterable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterable)[[Event](#outrage.logread.Event)]) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Event](#outrage.logread.Event)]
8323 8325

### *class* outrage.logread.Log(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), events: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Event](#outrage.logread.Event)] = <factory>, malformed: [list](https://docs.python.org/3/library/stdtypes.html#list)[[int](https://docs.python.org/3/library/functions.html#int)] = <factory>)
8842 8846

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
9343 9347

#### events *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Event](#outrage.logread.Event)]*
9426 9430

#### malformed *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[int](https://docs.python.org/3/library/functions.html#int)]*
9537 9541

#### *property* sessions *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Session](#outrage.logread.Session)]*
9679 9683

### *exception* outrage.logread.LogError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
9807 9811

### *class* outrage.logread.Session(id: [str](https://docs.python.org/3/library/stdtypes.html#str), events: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Event](#outrage.logread.Event)] = <factory>)
10133 10137

#### id *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
10496 10500

#### events *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Event](#outrage.logread.Event)]*
10568 10572

#### *property* start *: [Event](#outrage.logread.Event) | [None](https://docs.python.org/3/library/constants.html#None)*
10679 10683

#### *property* pid *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*
10870 10874

#### *property* version *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
11019 11023

#### *property* first_ts *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
11171 11175

#### *property* last_ts *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
11260 11264

#### *property* calls *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[int](https://docs.python.org/3/library/functions.html#int)]*
11348 11352

#### *property* tool_calls *: [int](https://docs.python.org/3/library/functions.html#int)*
11531 11535

#### *property* store_accesses *: [int](https://docs.python.org/3/library/functions.html#int)*
11623 11627

#### *property* is_discovery *: [bool](https://docs.python.org/3/library/functions.html#bool)*
11719 11723

### *class* outrage.logread.Summary(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), lines: [int](https://docs.python.org/3/library/functions.html#int) = 0, malformed: [int](https://docs.python.org/3/library/functions.html#int) = 0, sessions: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Session](#outrage.logread.Session)] = <factory>, calls: [int](https://docs.python.org/3/library/functions.html#int) = 0, store_accesses: [int](https://docs.python.org/3/library/functions.html#int) = 0, accesses_per_call: Counter[tuple[str, int]]=<factory>, ops: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = <factory>, methods: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = <factory>, tools: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = <factory>, errors: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = <factory>, refused: [int](https://docs.python.org/3/library/functions.html#int) = 0, reads: [int](https://docs.python.org/3/library/functions.html#int) = 0, truncated: [list](https://docs.python.org/3/library/stdtypes.html#list)[[TruncatedRead](#outrage.logread.TruncatedRead)] = <factory>, documents_truncated: [int](https://docs.python.org/3/library/functions.html#int) = 0)
12350 12354

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
14104 14108

#### lines *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
14187 14191

#### malformed *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
14269 14273

#### sessions *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Session](#outrage.logread.Session)]*
14355 14359

#### calls *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
14472 14476

#### store_accesses *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
14554 14558

#### accesses_per_call *: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [int](https://docs.python.org/3/library/functions.html#int)]]*
14645 14649

#### ops *: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*
15171 15175

#### methods *: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*
15327 15331

#### tools *: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*
15487 15491

#### errors *: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*
15645 15649

#### refused *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
15804 15808

#### reads *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
15888 15892

#### truncated *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[TruncatedRead](#outrage.logread.TruncatedRead)]*
15970 15974

#### documents_truncated *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
16100 16104

#### *property* busiest_call *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[int](https://docs.python.org/3/library/functions.html#int), [str](https://docs.python.org/3/library/stdtypes.html#str), [int](https://docs.python.org/3/library/functions.html#int)] | [None](https://docs.python.org/3/library/constants.html#None)*
16196 16200

#### *property* mean_accesses *: [float](https://docs.python.org/3/library/functions.html#float)*
16742 16750

#### *property* followed_up *: [int](https://docs.python.org/3/library/functions.html#int)*
17108 17116

### *class* outrage.logread.TruncatedRead(read: [Event](#outrage.logread.Event), resumed_by: [Event](#outrage.logread.Event) | [None](https://docs.python.org/3/library/constants.html#None))
17449 17457

#### read *: [Event](#outrage.logread.Event)*
17788 17796

#### resumed_by *: [Event](#outrage.logread.Event) | [None](https://docs.python.org/3/library/constants.html#None)*
17835 17843

#### *property* followed_up *: [bool](https://docs.python.org/3/library/functions.html#bool)*
17952 17960

### outrage.logread.format_event(event: [Event](#outrage.logread.Event), \*, content: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
18324 18332

### outrage.logread.format_session(session: [Session](#outrage.logread.Session)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
18912 18922

### outrage.logread.format_summary(summary: [Summary](#outrage.logread.Summary)) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
19126 19138

### outrage.logread.read_log(path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [Log](#outrage.logread.Log)
19430 19444

### outrage.logread.sessions(events: [Iterable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterable)[[Event](#outrage.logread.Event)]) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Session](#outrage.logread.Session)]
20031 20047

### outrage.logread.summarise(log: [Log](#outrage.logread.Log), events: [Iterable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterable)[[Event](#outrage.logread.Event)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Summary](#outrage.logread.Summary)
20593 20611

### outrage.logread.truncated_reads(session: [Session](#outrage.logread.Session)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[TruncatedRead](#outrage.logread.TruncatedRead)]
21122 21142
