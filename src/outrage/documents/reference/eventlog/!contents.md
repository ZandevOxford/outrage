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
3748 3748

#### emit(event: str, \*\*fields: Any) → None
3840 3840

#### start(\*\*fields: Any) → None
4094 4096

#### stop(\*\*fields: Any) → None
4319 4323

#### close() → None
4785 4791

#### content_field(text: Any) → dict[str, Any]
5168 5176

#### arguments(values: dict[str, Any]) → dict[str, Any]
6065 6075

### outrage.eventlog.current_call *: ContextVar* *= <ContextVar name='outrage_current_call' default=None>*
6538 6550

### outrage.eventlog.resolve_path(explicit: str | PathLike[str] | \_BesideTheStore | None, directory: str | PathLike[str]) → Path | None
7027 7039
