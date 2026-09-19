# outrage.eventlog
0 0 1

### outrage.eventlog.CONTENT_ARGS *= frozenset({'content', 'contents', 'title'})*
1178 1178 24

### outrage.eventlog.CONTENT_POLICIES *= ('none', 'excerpt', 'full')*
1748 1748 33

### outrage.eventlog.DEFAULT *= <beside the store>*
1941 1941 38

### outrage.eventlog.DEFAULT_EXCERPT_CHARS *= 200*
2111 2111 43

### outrage.eventlog.DEFAULT_LOG_NAME *= 'log.jsonl'*
2333 2333 49

### outrage.eventlog.ENV_LOG *= 'OUTRAGE_LOG'*
2599 2599 55

### outrage.eventlog.NULL *= <outrage.eventlog.EventLog object>*
2808 2808 61

### *class* outrage.eventlog.EventLog(path: str | PathLike[str] | None = None, \*, content: str = 'excerpt', excerpt_chars: int = DEFAULT_EXCERPT_CHARS, session: str | None = None)
2975 2975 66

#### *property* enabled *: bool*
3748 3748 72

#### emit(event: str, \*\*fields: Any) → None
3840 3840 74

#### start(\*\*fields: Any) → None
4094 4096 78

#### stop(\*\*fields: Any) → None
4319 4323 82

#### close() → None
4785 4791 91

#### content_field(text: Any) → dict[str, Any]
5168 5176 100

#### arguments(values: dict[str, Any]) → dict[str, Any]
6065 6075 115

### outrage.eventlog.current_call *: ContextVar* *= <ContextVar name='outrage_current_call' default=None>*
6538 6550 119

### outrage.eventlog.resolve_path(explicit: str | PathLike[str] | \_BesideTheStore | None, directory: str | PathLike[str]) → Path | None
7027 7039 126
