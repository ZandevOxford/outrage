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
5583 5583

#### scope *: str*
5666 5666

#### name *: str*
5742 5742

#### action *: str*
5817 5817

#### entry *: dict[str, Any]*
5932 5932

#### previous *: dict[str, Any] | None*
6136 6136

#### *property* writes *: bool*
6455 6455

### *exception* outrage.config.ConfigError(code: str, \*\*details: Any)
6546 6546

### outrage.config.codex_config_path(project_dir: str | PathLike[str] | None = None) → Path
6944 6944

### outrage.config.config_path(scope: str, project_dir: str | PathLike[str] | None = None) → Path
7400 7402

### outrage.config.default_store_dir(project_dir: str | PathLike[str] | None = None) → Path
7889 7893

### outrage.config.is_server_marker(value: Any) → bool
8324 8330

### outrage.config.launch_command(executable: str | PathLike[str] | None = None) → list[str]
8568 8576

### outrage.config.merge_entry(previous: dict[str, Any] | None, entry: dict[str, Any]) → dict[str, Any]
9373 9383

### outrage.config.mounts_in(args: Sequence[str]) → list[str]
11419 11431

### outrage.config.plan(path: Path, scope: str, entry: dict[str, Any], name: str = SERVER_NAME) → tuple[Change, dict[str, Any], str | None]
12118 12132

### outrage.config.plan_codex(path: Path, entry: dict[str, Any], name: str = SERVER_NAME) → tuple[Change, TOMLDocument, str | None]
13183 13199

### outrage.config.read_config(path: Path) → tuple[dict[str, Any], str | None]
14486 14504

### outrage.config.read_toml(path: Path) → tuple[TOMLDocument, str | None]
15305 15325

### outrage.config.script_command(script: str, executable: str | PathLike[str] | None = None) → list[str] | None
15867 15889

### outrage.config.server_entry(directory: str | PathLike[str], command: list[str] | None = None, \*, log: Any = None, log_content: str | None = None, no_info: bool = False, no_remount: bool = False, no_versioning: bool = False, marked: bool = False) → dict[str, Any]
16986 17010

### outrage.config.split_args(args: Sequence[str]) → list[tuple[str, list[str]]]
20803 20829

### outrage.config.write_config(path: Path, config: dict[str, Any], original: str | None = None) → None
21814 21842

### outrage.config.write_toml(path: Path, document: TOMLDocument, original: str | None = None) → None
22729 22759
