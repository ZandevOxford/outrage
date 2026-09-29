# outrage.server
0 0 1

### outrage.server.COPY_FAILURE_SAMPLE *= 5*
1402 1402 26

### outrage.server.DEFAULT_COPY_LIMIT *= 500*
1752 1752 34

### outrage.server.DEFAULT_ITEM_LIMIT *= 100*
2154 2154 42

### outrage.server.DEFAULT_PAGE_CHARS *= 20000*
2885 2885 56

### outrage.server.DEFAULT_SEARCH_SCAN_LIMIT *= 20*
3047 3047 61

### outrage.server.DELIVERY_BUDGET *= 2048*
3173 3173 65

### outrage.server.INCOMPLETE_MOUNTS *= "Warning: one or more non-root stores could not be opened, so this server's namespace is incomplete; call \`info\` to inspect its live mounts and configuration files."*
3989 3989 79

### outrage.server.INSTRUCTIONS *= ('instructions', 'instructions')*
4526 4526 87

### outrage.server.NO_README *= 'This store has no \`readme\` document. Try reading \`outrage/readme\` instead for instructions.'*
5012 5012 96

### outrage.server.READ_README *= 'This store has a \`readme\` document covering project conventions. Read it before starting.'*
5344 5344 102

### outrage.server.README_KEY *= 'readme'*
5686 5686 108

### outrage.server.TOOLS *= 'tools'*
5944 5944 114

### outrage.server.WITHOUT_META_SAMPLE *= 10*
6288 6288 121

### *class* outrage.server.RequestLog(log: EventLog)
6548 6548 127

### outrage.server.build_server(store: Store | Live, log: EventLog | None = None, directory: str | PathLike[str] | None = None, \*, all_tools: bool = False, info_tool: bool = True, remount_tool: bool = True, mount_config: Sequence[str] = (), incomplete_mounts: bool = False, smart_search: Callable[[], AbstractContextManager[Judge]] | None = None) → MCPServer
7855 7855 151

### outrage.server.delivered_text() → str
12923 12925 218

### outrage.server.instructions(store: Store, \*, incomplete_mounts: bool = False) → str
13509 13513 230

### outrage.server.main(argv: list[str] | None = None) → int
15733 15739 267

### outrage.server.parse_args(argv: list[str] | None = None) → Namespace
16615 16623 280

### outrage.server.tool_description(name: str) → str
17946 17956 301
