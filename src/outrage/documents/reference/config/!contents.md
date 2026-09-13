# outrage.config
0 0

## Codex reads TOML, and its entry carries a marker
850 850

### outrage.config.CLI_SCRIPT_NAME *= 'outrage'*
2272 2272

### outrage.config.CODEX_CONFIG_NAME *= PosixPath('.codex/config.toml')*
2618 2618

### outrage.config.CODEX_SERVERS_FIELD *= 'mcp_servers'*
2761 2761

### outrage.config.MARKER *= 'outrage-managed:mcp-server'*
2855 2855

### outrage.config.MARKER_MATCH *= '-managed:mcp-server'*
3027 3027

### outrage.config.PROJECT_CONFIG_NAME *= '.mcp.json'*
3380 3380

### outrage.config.SCOPES *= ('project', 'user')*
3537 3537

### outrage.config.SCRIPT_NAME *= 'outrage-server'*
3704 3704

### outrage.config.SERVERS_FIELD *= 'mcpServers'*
3969 3969

### outrage.config.SERVER_MARKER *= 'outrage-managed:mcp-server:v1'*
4159 4159

### outrage.config.SERVER_NAME *= 'outrage'*
4288 4288

### outrage.config.USER_CONFIG_NAME *= '.claude.json'*
4475 4475

### *class* outrage.config.Change(path: Path, scope: str, name: str, action: str, entry: dict[str, Any], previous: dict[str, Any] | None)
4682 4682

#### path *: Path*
5574 5574

#### scope *: str*
5657 5657

#### name *: str*
5732 5732

#### action *: str*
5806 5806

#### entry *: dict[str, Any]*
5920 5920

#### previous *: dict[str, Any] | None*
6122 6122

#### *property* writes *: bool*
6438 6438

### *exception* outrage.config.ConfigError(code: str, \*\*details: Any)
6528 6528

### outrage.config.codex_config_path(project_dir: str | PathLike[str] | None = None) → Path
6924 6924

### outrage.config.config_path(scope: str, project_dir: str | PathLike[str] | None = None) → Path
7377 7379

### outrage.config.default_store_dir(project_dir: str | PathLike[str] | None = None) → Path
7862 7866

### outrage.config.is_server_marker(value: Any) → bool
8294 8300

### outrage.config.launch_command(executable: str | PathLike[str] | None = None) → list[str]
8537 8545

### outrage.config.merge_entry(previous: dict[str, Any] | None, entry: dict[str, Any]) → dict[str, Any]
9337 9347

### outrage.config.mounts_in(args: Sequence[str]) → list[str]
11376 11388

### outrage.config.plan(path: Path, scope: str, entry: dict[str, Any], name: str = SERVER_NAME) → tuple[Change, dict[str, Any], str | None]
12072 12086

### outrage.config.plan_codex(path: Path, entry: dict[str, Any], name: str = SERVER_NAME) → tuple[Change, TOMLDocument, str | None]
13128 13144

### outrage.config.read_config(path: Path) → tuple[dict[str, Any], str | None]
14425 14443

### outrage.config.read_toml(path: Path) → tuple[TOMLDocument, str | None]
15239 15259

### outrage.config.script_command(script: str, executable: str | PathLike[str] | None = None) → list[str] | None
15798 15820

### outrage.config.server_entry(directory: str | PathLike[str], command: list[str] | None = None, \*, log: Any = None, log_content: str | None = None, no_info: bool = False, no_remount: bool = False, no_versioning: bool = False, marked: bool = False) → dict[str, Any]
16910 16934

### outrage.config.split_args(args: Sequence[str]) → list[tuple[str, list[str]]]
20714 20740

### outrage.config.write_config(path: Path, config: dict[str, Any], original: str | None = None) → None
21719 21747

### outrage.config.write_toml(path: Path, document: TOMLDocument, original: str | None = None) → None
22629 22659
