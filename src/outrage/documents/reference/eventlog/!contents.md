# outrage.eventlog
0 0 1

### outrage.eventlog.CONTENT_ARGS *= frozenset({'content', 'contents', 'title'})*
1340 1340 26

### outrage.eventlog.CONTENT_POLICIES *= ('none', 'excerpt', 'full')*
1910 1910 35

### outrage.eventlog.DEFAULT *= <beside the store>*
2103 2103 40

### outrage.eventlog.DEFAULT_EXCERPT_CHARS *= 200*
2273 2273 45

### outrage.eventlog.DEFAULT_LOG_NAME *= 'log.jsonl'*
2495 2495 51

### outrage.eventlog.ENV_LOG *= 'OUTRAGE_LOG'*
2761 2761 57

### outrage.eventlog.NULL *= <outrage.eventlog.EventLog object>*
2970 2970 63

### *class* outrage.eventlog.EventLog(path: str | PathLike[str] | None = None, \*, content: str = 'excerpt', excerpt_chars: int = DEFAULT_EXCERPT_CHARS, session: str | None = None)
3137 3137 68

#### *property* enabled *: bool*
3910 3910 74

#### emit(event: str, \*\*fields: Any) → None
4002 4002 76

#### start(\*\*fields: Any) → None
4256 4258 80

#### stop(\*\*fields: Any) → None
4481 4485 84

#### close() → None
4947 4953 93

#### content_field(text: Any) → dict[str, Any]
5330 5338 102

#### arguments(values: dict[str, Any]) → dict[str, Any]
6227 6237 117

### outrage.eventlog.current_call *: ContextVar* *= <ContextVar name='outrage_current_call' default=None>*
6700 6712 121

### outrage.eventlog.resolve_path(explicit: str | PathLike[str] | \_BesideTheStore | None, directory: str | PathLike[str]) → Path | None
7189 7201 128
