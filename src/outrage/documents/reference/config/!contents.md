# outrage.config
0 0 1

## Codex reads TOML, and its entry carries a marker
1005 1005 19

## Cursor reads the same JSON somewhere else
2427 2427 43

### outrage.config.CLI_SCRIPT_NAME *= 'outrage'*
3838 3838 67

### outrage.config.CODEX_CONFIG_NAME *= PosixPath('.codex/config.toml')*
4184 4184 74

### outrage.config.CODEX_SERVERS_FIELD *= 'mcp_servers'*
4327 4327 78

### outrage.config.CURSOR_CONFIG_NAME *= PosixPath('.cursor/mcp.json')*
4421 4421 82

### outrage.config.CURSOR_SCOPE *= 'project'*
4716 4716 88

### outrage.config.CURSOR_SERVER_TYPE *= 'stdio'*
5020 5020 95

### outrage.config.MARKER *= 'outrage-managed:mcp-server'*
5210 5210 100

### outrage.config.MARKER_MATCH *= '-managed:mcp-server'*
5382 5382 105

### outrage.config.PROJECT_CONFIG_NAME *= '.mcp.json'*
5735 5735 112

### outrage.config.SCOPES *= ('project', 'user')*
5892 5892 117

### outrage.config.SCRIPT_NAME *= 'outrage-server'*
6059 6059 122

### outrage.config.SERVERS_FIELD *= 'mcpServers'*
6324 6324 128

### outrage.config.SERVER_MARKER *= 'outrage-managed:mcp-server:v1'*
6514 6514 133

### outrage.config.SERVER_NAME *= 'outrage'*
6643 6643 137

### outrage.config.USER_CONFIG_NAME *= '.claude.json'*
6830 6830 142

### *class* outrage.config.Change(path: Path, scope: str, name: str, action: str, entry: dict[str, Any], previous: dict[str, Any] | None, refusals: tuple[Refusal, ...] = ())
7037 7037 147

#### path *: Path*
8068 8068 153

#### scope *: str*
8151 8151 155

#### name *: str*
8227 8227 157

#### action *: str*
8302 8302 159

#### entry *: dict[str, Any]*
8546 8546 165

#### previous *: dict[str, Any] | None*
8750 8750 167

#### refusals *: tuple[Refusal, ...]*
9080 9080 171

#### *property* writes *: bool*
9576 9576 180

### *exception* outrage.config.ConfigError(code: str, \*\*details: Any)
9954 9954 189

### outrage.config.WRITING_ACTIONS *= frozenset({'created', 'removed', 'updated'})*
10352 10352 195

### outrage.config.codex_config_path(project_dir: str | PathLike[str] | None = None) → Path
10564 10564 200

### outrage.config.config_path(scope: str, project_dir: str | PathLike[str] | None = None) → Path
11020 11022 204

### outrage.config.cursor_config_path(project_dir: str | PathLike[str] | None = None) → Path
11509 11513 208

### outrage.config.cursor_entry(entry: dict[str, Any]) → dict[str, Any]
12186 12192 216

### outrage.config.default_store_dir(project_dir: str | PathLike[str] | None = None) → Path
13095 13103 226

### outrage.config.entry_refusals(entry: Mapping[str, Any]) → list[Refusal]
13530 13540 230

### outrage.config.is_server_marker(value: Any) → bool
14435 14447 243

### outrage.config.known_fields() → frozenset[str]
14679 14693 247

### outrage.config.known_options() → frozenset[str]
15126 15142 255

### outrage.config.launch_command(executable: str | PathLike[str] | None = None) → list[str]
15955 15973 270

### outrage.config.merge_entry(previous: dict[str, Any] | None, entry: dict[str, Any]) → dict[str, Any]
16760 16780 280

### outrage.config.mounts_in(args: Sequence[str]) → list[str]
19672 19694 323

### outrage.config.plan(path: Path, scope: str, entry: dict[str, Any], name: str = SERVER_NAME) → tuple[Change, dict[str, Any], str | None]
20371 20395 333

### outrage.config.plan_codex(path: Path, entry: dict[str, Any], name: str = SERVER_NAME) → tuple[Change, TOMLDocument, str | None]
21436 21462 340

### outrage.config.plan_codex_removal(path: Path, name: str = SERVER_NAME) → tuple[Change, TOMLDocument | None, str | None]
22739 22767 355

### outrage.config.plan_removal(path: Path, scope: str, name: str = SERVER_NAME) → tuple[Change, dict[str, Any] | None, str | None]
24006 24036 372

### outrage.config.read_config(path: Path) → tuple[dict[str, Any], str | None]
25979 26011 397

### outrage.config.read_toml(path: Path) → tuple[TOMLDocument, str | None]
26798 26832 406

### outrage.config.script_command(script: str, executable: str | PathLike[str] | None = None) → list[str] | None
27360 27396 413

### outrage.config.server_entry(directory: str | PathLike[str], command: list[str] | None = None, \*, log: Any = None, log_content: str | None = None, no_info: bool = False, no_remount: bool = False, no_versioning: bool = False, smart_search: bool = False, marked: bool = False) → dict[str, Any]
28479 28517 427

### outrage.config.split_args(args: Sequence[str]) → list[tuple[str, list[str]]]
32634 32674 480

### outrage.config.write_config(path: Path, config: dict[str, Any], original: str | None = None) → None
33645 33687 491

### outrage.config.write_toml(path: Path, document: TOMLDocument, original: str | None = None) → None
34560 34604 501
