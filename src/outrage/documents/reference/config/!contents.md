# outrage.config
0 0

## Codex reads TOML, and its entry carries a marker
850 850

## Cursor reads the same JSON somewhere else
2272 2272

### outrage.config.CLI_SCRIPT_NAME *= 'outrage'*
3683 3683

### outrage.config.CODEX_CONFIG_NAME *= PosixPath('.codex/config.toml')*
4029 4029

### outrage.config.CODEX_SERVERS_FIELD *= 'mcp_servers'*
4172 4172

### outrage.config.CURSOR_CONFIG_NAME *= PosixPath('.cursor/mcp.json')*
4266 4266

### outrage.config.CURSOR_SCOPE *= 'project'*
4561 4561

### outrage.config.CURSOR_SERVER_TYPE *= 'stdio'*
4865 4865

### outrage.config.MARKER *= 'outrage-managed:mcp-server'*
5055 5055

### outrage.config.MARKER_MATCH *= '-managed:mcp-server'*
5227 5227

### outrage.config.PROJECT_CONFIG_NAME *= '.mcp.json'*
5580 5580

### outrage.config.SCOPES *= ('project', 'user')*
5737 5737

### outrage.config.SCRIPT_NAME *= 'outrage-server'*
5904 5904

### outrage.config.SERVERS_FIELD *= 'mcpServers'*
6169 6169

### outrage.config.SERVER_MARKER *= 'outrage-managed:mcp-server:v1'*
6359 6359

### outrage.config.SERVER_NAME *= 'outrage'*
6488 6488

### outrage.config.USER_CONFIG_NAME *= '.claude.json'*
6675 6675

### *class* outrage.config.Change(path: Path, scope: str, name: str, action: str, entry: dict[str, Any], previous: dict[str, Any] | None)
6882 6882

#### path *: Path*
7783 7783

#### scope *: str*
7866 7866

#### name *: str*
7942 7942

#### action *: str*
8017 8017

#### entry *: dict[str, Any]*
8132 8132

#### previous *: dict[str, Any] | None*
8336 8336

#### *property* writes *: bool*
8655 8655

### *exception* outrage.config.ConfigError(code: str, \*\*details: Any)
8746 8746

### outrage.config.codex_config_path(project_dir: str | PathLike[str] | None = None) → Path
9144 9144

### outrage.config.config_path(scope: str, project_dir: str | PathLike[str] | None = None) → Path
9600 9602

### outrage.config.cursor_config_path(project_dir: str | PathLike[str] | None = None) → Path
10089 10093

### outrage.config.cursor_entry(entry: dict[str, Any]) → dict[str, Any]
10766 10772

### outrage.config.default_store_dir(project_dir: str | PathLike[str] | None = None) → Path
11675 11683

### outrage.config.is_server_marker(value: Any) → bool
12110 12120

### outrage.config.launch_command(executable: str | PathLike[str] | None = None) → list[str]
12354 12366

### outrage.config.merge_entry(previous: dict[str, Any] | None, entry: dict[str, Any]) → dict[str, Any]
13159 13173

### outrage.config.mounts_in(args: Sequence[str]) → list[str]
16071 16087

### outrage.config.plan(path: Path, scope: str, entry: dict[str, Any], name: str = SERVER_NAME) → tuple[Change, dict[str, Any], str | None]
16770 16788

### outrage.config.plan_codex(path: Path, entry: dict[str, Any], name: str = SERVER_NAME) → tuple[Change, TOMLDocument, str | None]
17835 17855

### outrage.config.read_config(path: Path) → tuple[dict[str, Any], str | None]
19138 19160

### outrage.config.read_toml(path: Path) → tuple[TOMLDocument, str | None]
19957 19981

### outrage.config.script_command(script: str, executable: str | PathLike[str] | None = None) → list[str] | None
20519 20545

### outrage.config.server_entry(directory: str | PathLike[str], command: list[str] | None = None, \*, log: Any = None, log_content: str | None = None, no_info: bool = False, no_remount: bool = False, no_versioning: bool = False, marked: bool = False) → dict[str, Any]
21638 21666

### outrage.config.split_args(args: Sequence[str]) → list[tuple[str, list[str]]]
25455 25485

### outrage.config.write_config(path: Path, config: dict[str, Any], original: str | None = None) → None
26466 26498

### outrage.config.write_toml(path: Path, document: TOMLDocument, original: str | None = None) → None
27381 27415
