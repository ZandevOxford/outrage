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

### *class* outrage.eventlog.EventLog(path: str | PathLike[str] | None = None, \*, content: str = 'excerpt', excerpt_chars: int = DEFAULT_EXCERPT_CHARS, session: str | None = None)
2781 2781

#### *property* enabled *: bool*
3546 3546

#### emit(event: str, \*\*fields: Any) → None
3637 3637

#### start(\*\*fields: Any) → None
3889 3891

#### stop(\*\*fields: Any) → None
4113 4117

#### close() → None
4578 4584

#### content_field(text: Any) → dict[str, Any]
4960 4968

#### arguments(values: dict[str, Any]) → dict[str, Any]
5855 5865

### outrage.eventlog.current_call *: ContextVar* *= <ContextVar name='outrage_current_call' default=None>*
6324 6336

### outrage.eventlog.resolve_path(explicit: str | PathLike[str] | \_BesideTheStore | None, directory: str | PathLike[str]) → Path | None
6813 6825
