# outrage.eventlog
0 0

### outrage.eventlog.CONTENT_ARGS *= frozenset({'content', 'contents', 'title'})*
1178 1178

### outrage.eventlog.CONTENT_POLICIES *= ('none', 'excerpt', 'full')*
1748 1748

### outrage.eventlog.DEFAULT *= <beside the store>*
1941 1941

### outrage.eventlog.DEFAULT_EXCERPT_CHARS *= 200*
2111 2111

### outrage.eventlog.DEFAULT_LOG_NAME *= 'log.jsonl'*
2333 2333

### outrage.eventlog.ENV_LOG *= 'OUTRAGE_LOG'*
2599 2599

### outrage.eventlog.NULL *= <outrage.eventlog.EventLog object>*
2808 2808

### *class* outrage.eventlog.EventLog(path: str | PathLike[str] | None = None, \*, content: str = 'excerpt', excerpt_chars: int = DEFAULT_EXCERPT_CHARS, session: str | None = None)
2975 2975

#### *property* enabled *: bool*
3740 3740

#### emit(event: str, \*\*fields: Any) → None
3831 3831

#### start(\*\*fields: Any) → None
4083 4085

#### stop(\*\*fields: Any) → None
4307 4311

#### close() → None
4772 4778

#### content_field(text: Any) → dict[str, Any]
5154 5162

#### arguments(values: dict[str, Any]) → dict[str, Any]
6049 6059

### outrage.eventlog.current_call *: ContextVar* *= <ContextVar name='outrage_current_call' default=None>*
6518 6530

### outrage.eventlog.resolve_path(explicit: str | PathLike[str] | \_BesideTheStore | None, directory: str | PathLike[str]) → Path | None
7007 7019
