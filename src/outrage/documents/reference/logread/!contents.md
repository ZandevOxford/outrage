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
5300 5300

#### *property* next_offset *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*
5644 5644

### *class* outrage.logread.Filter(session: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, call: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, op: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, method: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, event: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, errors: [bool](https://docs.python.org/3/library/functions.html#bool) = False)
5872 5872

#### session *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*
6965 6965

#### call *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*
7115 7115

#### op *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*
7263 7263

#### method *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*
7408 7408

#### event *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*
7557 7557

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*
7705 7705

#### errors *: [bool](https://docs.python.org/3/library/functions.html#bool)* *= False*
7851 7851

#### matches(event: [Event](#outrage.logread.Event)) → [bool](https://docs.python.org/3/library/functions.html#bool)
7940 7940

#### select(events: [Iterable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterable)[[Event](#outrage.logread.Event)]) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Event](#outrage.logread.Event)]
8342 8344

### *class* outrage.logread.Log(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), events: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Event](#outrage.logread.Event)] = <factory>, malformed: [list](https://docs.python.org/3/library/stdtypes.html#list)[[int](https://docs.python.org/3/library/functions.html#int)] = <factory>)
8861 8865

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
9362 9366

#### events *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Event](#outrage.logread.Event)]*
9445 9449

#### malformed *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[int](https://docs.python.org/3/library/functions.html#int)]*
9556 9560

#### *property* sessions *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Session](#outrage.logread.Session)]*
9698 9702

### *exception* outrage.logread.LogError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
9826 9830

### *class* outrage.logread.Session(id: [str](https://docs.python.org/3/library/stdtypes.html#str), events: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Event](#outrage.logread.Event)] = <factory>)
10152 10156

#### id *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
10515 10519

#### events *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Event](#outrage.logread.Event)]*
10587 10591

#### *property* start *: [Event](#outrage.logread.Event) | [None](https://docs.python.org/3/library/constants.html#None)*
10698 10702

#### *property* pid *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*
10889 10893

#### *property* version *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
11038 11042

#### *property* first_ts *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
11190 11194

#### *property* last_ts *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
11279 11283

#### *property* calls *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[int](https://docs.python.org/3/library/functions.html#int)]*
11367 11371

#### *property* tool_calls *: [int](https://docs.python.org/3/library/functions.html#int)*
11550 11554

#### *property* store_accesses *: [int](https://docs.python.org/3/library/functions.html#int)*
11642 11646

#### *property* is_discovery *: [bool](https://docs.python.org/3/library/functions.html#bool)*
11738 11742

### *class* outrage.logread.Summary(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), lines: [int](https://docs.python.org/3/library/functions.html#int) = 0, malformed: [int](https://docs.python.org/3/library/functions.html#int) = 0, sessions: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Session](#outrage.logread.Session)] = <factory>, calls: [int](https://docs.python.org/3/library/functions.html#int) = 0, store_accesses: [int](https://docs.python.org/3/library/functions.html#int) = 0, accesses_per_call: Counter[tuple[str, int]]=<factory>, ops: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = <factory>, methods: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = <factory>, tools: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = <factory>, errors: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = <factory>, refused: [int](https://docs.python.org/3/library/functions.html#int) = 0, reads: [int](https://docs.python.org/3/library/functions.html#int) = 0, truncated: [list](https://docs.python.org/3/library/stdtypes.html#list)[[TruncatedRead](#outrage.logread.TruncatedRead)] = <factory>, documents_truncated: [int](https://docs.python.org/3/library/functions.html#int) = 0)
12369 12373

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
14123 14127

#### lines *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
14206 14210

#### malformed *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
14288 14292

#### sessions *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Session](#outrage.logread.Session)]*
14374 14378

#### calls *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
14491 14495

#### store_accesses *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
14573 14577

#### accesses_per_call *: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [int](https://docs.python.org/3/library/functions.html#int)]]*
14664 14668

#### ops *: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*
15190 15194

#### methods *: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*
15346 15350

#### tools *: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*
15506 15510

#### errors *: [Counter](https://docs.python.org/3/library/collections.html#collections.Counter)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*
15664 15668

#### refused *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
15823 15827

#### reads *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
15907 15911

#### truncated *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[TruncatedRead](#outrage.logread.TruncatedRead)]*
15989 15993

#### documents_truncated *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
16119 16123

#### *property* busiest_call *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[int](https://docs.python.org/3/library/functions.html#int), [str](https://docs.python.org/3/library/stdtypes.html#str), [int](https://docs.python.org/3/library/functions.html#int)] | [None](https://docs.python.org/3/library/constants.html#None)*
16215 16219

#### *property* mean_accesses *: [float](https://docs.python.org/3/library/functions.html#float)*
16761 16769

#### *property* followed_up *: [int](https://docs.python.org/3/library/functions.html#int)*
17127 17135

### *class* outrage.logread.TruncatedRead(read: [Event](#outrage.logread.Event), resumed_by: [Event](#outrage.logread.Event) | [None](https://docs.python.org/3/library/constants.html#None))
17468 17476

#### read *: [Event](#outrage.logread.Event)*
17807 17815

#### resumed_by *: [Event](#outrage.logread.Event) | [None](https://docs.python.org/3/library/constants.html#None)*
17854 17862

#### *property* followed_up *: [bool](https://docs.python.org/3/library/functions.html#bool)*
17971 17979

### outrage.logread.format_event(event: [Event](#outrage.logread.Event), \*, content: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
18372 18380

### outrage.logread.format_session(session: [Session](#outrage.logread.Session)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
18960 18970

### outrage.logread.format_summary(summary: [Summary](#outrage.logread.Summary)) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
19174 19186

### outrage.logread.read_log(path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [Log](#outrage.logread.Log)
19478 19492

### outrage.logread.sessions(events: [Iterable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterable)[[Event](#outrage.logread.Event)]) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Session](#outrage.logread.Session)]
20079 20095

### outrage.logread.summarise(log: [Log](#outrage.logread.Log), events: [Iterable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterable)[[Event](#outrage.logread.Event)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Summary](#outrage.logread.Summary)
20641 20659

### outrage.logread.truncated_reads(session: [Session](#outrage.logread.Session)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[TruncatedRead](#outrage.logread.TruncatedRead)]
21170 21190
