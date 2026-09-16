# outrage.server
0 0

### outrage.server.COPY_FAILURE_SAMPLE *= 5*
1212 1212

### outrage.server.DEFAULT_COPY_LIMIT *= 500*
1562 1562

### outrage.server.DEFAULT_ITEM_LIMIT *= 100*
1964 1964

### outrage.server.DEFAULT_PAGE_CHARS *= 20000*
2695 2695

### outrage.server.DEFAULT_SEARCH_SCAN_LIMIT *= 20*
2857 2857

### outrage.server.DELIVERY_BUDGET *= 2048*
2983 2983

### outrage.server.INCOMPLETE_MOUNTS *= "Warning: one or more non-root stores could not be opened, so this server's namespace is incomplete; call \`info\` to inspect its live mounts and configuration files."*
3799 3799

### outrage.server.INSTRUCTIONS *= ('instructions', 'instructions')*
4336 4336

### outrage.server.NO_README *= 'This store has no \`readme\` document. Try reading \`outrage/readme\` instead for instructions.'*
4822 4822

### outrage.server.READ_README *= 'This store has a \`readme\` document covering project conventions. Read it before starting.'*
5154 5154

### outrage.server.README_KEY *= 'readme'*
5496 5496

### outrage.server.TOOLS *= 'tools'*
5754 5754

### outrage.server.WITHOUT_META_SAMPLE *= 10*
6098 6098

### *class* outrage.server.RequestLog(log: EventLog)
6358 6358

### outrage.server.build_server(store: Store | Live, log: EventLog | None = None, directory: str | PathLike[str] | None = None, \*, all_tools: bool = False, info_tool: bool = True, remount_tool: bool = True, mount_config: Sequence[str] = (), incomplete_mounts: bool = False) → MCPServer
7665 7665

### outrage.server.delivered_text() → str
11887 11889

### outrage.server.instructions(store: Store, \*, incomplete_mounts: bool = False) → str
12473 12477

### outrage.server.main(argv: list[str] | None = None) → int
14697 14703

### outrage.server.parse_args(argv: list[str] | None = None) → Namespace
15579 15587

### outrage.server.tool_description(name: str) → str
16910 16920
