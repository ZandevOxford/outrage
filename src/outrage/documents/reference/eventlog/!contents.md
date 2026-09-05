# outrage.eventlog
0 0

### outrage.eventlog.CONTENT_ARGS *= frozenset({'content', 'title'})*
1178 1178

### outrage.eventlog.CONTENT_POLICIES *= ('none', 'excerpt', 'full')*
1554 1554

### outrage.eventlog.DEFAULT *= <beside the store>*
1747 1747

### outrage.eventlog.DEFAULT_EXCERPT_CHARS *= 200*
1917 1917

### outrage.eventlog.DEFAULT_LOG_NAME *= 'log.jsonl'*
2139 2139

### outrage.eventlog.ENV_LOG *= 'OUTRAGE_LOG'*
2405 2405

### outrage.eventlog.NULL *= <outrage.eventlog.EventLog object>*
2614 2614

### *class* outrage.eventlog.EventLog(path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, content: [str](https://docs.python.org/3/library/stdtypes.html#str) = 'excerpt', excerpt_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_EXCERPT_CHARS, session: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)
2781 2781

#### *property* enabled *: [bool](https://docs.python.org/3/library/functions.html#bool)*
3546 3546

#### emit(event: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*fields: [Any](https://docs.python.org/3/library/typing.html#typing.Any)) → [None](https://docs.python.org/3/library/constants.html#None)
3637 3637

#### start(\*\*fields: [Any](https://docs.python.org/3/library/typing.html#typing.Any)) → [None](https://docs.python.org/3/library/constants.html#None)
3889 3891

#### stop(\*\*fields: [Any](https://docs.python.org/3/library/typing.html#typing.Any)) → [None](https://docs.python.org/3/library/constants.html#None)
4113 4117

#### close() → [None](https://docs.python.org/3/library/constants.html#None)
4578 4584

#### content_field(text: [Any](https://docs.python.org/3/library/typing.html#typing.Any)) → [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]
4960 4968

#### arguments(values: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]) → [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]
5855 5865

### outrage.eventlog.current_call *: [ContextVar](https://docs.python.org/3/library/contextvars.html#contextvars.ContextVar)* *= <ContextVar name='outrage_current_call' default=None>*
6324 6336

### outrage.eventlog.resolve_path(explicit: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | \_BesideTheStore | [None](https://docs.python.org/3/library/constants.html#None), directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/library/constants.html#None)
6813 6825
