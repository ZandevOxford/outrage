# outrage.config
0 0 1

## Codex reads TOML, and its entry carries a marker
850 850 17

## Cursor reads the same JSON somewhere else
2272 2272 41

### outrage.config.CLI_SCRIPT_NAME *= 'outrage'*
3683 3683 65

### outrage.config.CODEX_CONFIG_NAME *= PosixPath('.codex/config.toml')*
4029 4029 72

### outrage.config.CODEX_SERVERS_FIELD *= 'mcp_servers'*
4172 4172 76

### outrage.config.CURSOR_CONFIG_NAME *= PosixPath('.cursor/mcp.json')*
4266 4266 80

### outrage.config.CURSOR_SCOPE *= 'project'*
4561 4561 86

### outrage.config.CURSOR_SERVER_TYPE *= 'stdio'*
4865 4865 93

### outrage.config.MARKER *= 'outrage-managed:mcp-server'*
5055 5055 98

### outrage.config.MARKER_MATCH *= '-managed:mcp-server'*
5227 5227 103

### outrage.config.PROJECT_CONFIG_NAME *= '.mcp.json'*
5580 5580 110

### outrage.config.SCOPES *= ('project', 'user')*
5737 5737 115

### outrage.config.SCRIPT_NAME *= 'outrage-server'*
5904 5904 120

### outrage.config.SERVERS_FIELD *= 'mcpServers'*
6169 6169 126

### outrage.config.SERVER_MARKER *= 'outrage-managed:mcp-server:v1'*
6359 6359 131

### outrage.config.SERVER_NAME *= 'outrage'*
6488 6488 135

### outrage.config.USER_CONFIG_NAME *= '.claude.json'*
6675 6675 140

### *class* outrage.config.Change(path: Path, scope: str, name: str, action: str, entry: dict[str, Any], previous: dict[str, Any] | None, refusals: tuple[Refusal, ...] = ())
6882 6882 145

#### path *: Path*
7913 7913 151

#### scope *: str*
7996 7996 153

#### name *: str*
8072 8072 155

#### action *: str*
8147 8147 157

#### entry *: dict[str, Any]*
8391 8391 163

#### previous *: dict[str, Any] | None*
8595 8595 165

#### refusals *: tuple[Refusal, ...]*
8925 8925 169

#### *property* writes *: bool*
9421 9421 178

### *exception* outrage.config.ConfigError(code: str, \*\*details: Any)
9799 9799 187

### outrage.config.WRITING_ACTIONS *= frozenset({'created', 'removed', 'updated'})*
10197 10197 193

### outrage.config.codex_config_path(project_dir: str | PathLike[str] | None = None) → Path
10409 10409 198

### outrage.config.config_path(scope: str, project_dir: str | PathLike[str] | None = None) → Path
10865 10867 202

### outrage.config.cursor_config_path(project_dir: str | PathLike[str] | None = None) → Path
11354 11358 206

### outrage.config.cursor_entry(entry: dict[str, Any]) → dict[str, Any]
12031 12037 214

### outrage.config.default_store_dir(project_dir: str | PathLike[str] | None = None) → Path
12940 12948 224

### outrage.config.entry_refusals(entry: Mapping[str, Any]) → list[Refusal]
13375 13385 228

### outrage.config.is_server_marker(value: Any) → bool
14280 14292 241

### outrage.config.known_fields() → frozenset[str]
14524 14538 245

### outrage.config.known_options() → frozenset[str]
14971 14987 253

### outrage.config.launch_command(executable: str | PathLike[str] | None = None) → list[str]
15800 15818 268

### outrage.config.merge_entry(previous: dict[str, Any] | None, entry: dict[str, Any]) → dict[str, Any]
16605 16625 278

### outrage.config.mounts_in(args: Sequence[str]) → list[str]
19517 19539 321

### outrage.config.plan(path: Path, scope: str, entry: dict[str, Any], name: str = SERVER_NAME) → tuple[Change, dict[str, Any], str | None]
20216 20240 331

### outrage.config.plan_codex(path: Path, entry: dict[str, Any], name: str = SERVER_NAME) → tuple[Change, TOMLDocument, str | None]
21281 21307 338

### outrage.config.plan_codex_removal(path: Path, name: str = SERVER_NAME) → tuple[Change, TOMLDocument | None, str | None]
22584 22612 353

### outrage.config.plan_removal(path: Path, scope: str, name: str = SERVER_NAME) → tuple[Change, dict[str, Any] | None, str | None]
23851 23881 370

### outrage.config.read_config(path: Path) → tuple[dict[str, Any], str | None]
25824 25856 395

### outrage.config.read_toml(path: Path) → tuple[TOMLDocument, str | None]
26643 26677 404

### outrage.config.script_command(script: str, executable: str | PathLike[str] | None = None) → list[str] | None
27205 27241 411

### outrage.config.server_entry(directory: str | PathLike[str], command: list[str] | None = None, \*, log: Any = None, log_content: str | None = None, no_info: bool = False, no_remount: bool = False, no_versioning: bool = False, marked: bool = False) → dict[str, Any]
28324 28362 425

### outrage.config.split_args(args: Sequence[str]) → list[tuple[str, list[str]]]
32141 32181 473

### outrage.config.write_config(path: Path, config: dict[str, Any], original: str | None = None) → None
33152 33194 484

### outrage.config.write_toml(path: Path, document: TOMLDocument, original: str | None = None) → None
34067 34111 494
