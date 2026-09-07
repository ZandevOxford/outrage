# outrage.eventlog
0 0

### outrage.eventlog.CONTENT_ARGS *= frozenset({'content', 'title'})*
1178 1178

### outrage.eventlog.CONTENT_POLICIES *= ('none', 'excerpt', 'full')*
1715 1715

### outrage.eventlog.DEFAULT *= <beside the store>*
1908 1908

### outrage.eventlog.DEFAULT_EXCERPT_CHARS *= 200*
2078 2078

### outrage.eventlog.DEFAULT_LOG_NAME *= 'log.jsonl'*
2300 2300

### outrage.eventlog.ENV_LOG *= 'OUTRAGE_LOG'*
2566 2566

### outrage.eventlog.NULL *= <outrage.eventlog.EventLog object>*
2775 2775

### *class* outrage.eventlog.EventLog(path: str | PathLike[str] | None = None, \*, content: str = 'excerpt', excerpt_chars: int = DEFAULT_EXCERPT_CHARS, session: str | None = None)
2942 2942

#### *property* enabled *: bool*
3707 3707

#### emit(event: str, \*\*fields: Any) → None
3798 3798

#### start(\*\*fields: Any) → None
4050 4052

#### stop(\*\*fields: Any) → None
4274 4278

#### close() → None
4739 4745

#### content_field(text: Any) → dict[str, Any]
5121 5129

#### arguments(values: dict[str, Any]) → dict[str, Any]
6016 6026

### outrage.eventlog.current_call *: ContextVar* *= <ContextVar name='outrage_current_call' default=None>*
6485 6497

### outrage.eventlog.resolve_path(explicit: str | PathLike[str] | \_BesideTheStore | None, directory: str | PathLike[str]) → Path | None
6974 6986
