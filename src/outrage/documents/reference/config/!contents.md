# outrage.config
0 0

### outrage.config.CLI_SCRIPT_NAME *= 'outrage'*
850 850

### outrage.config.PROJECT_CONFIG_NAME *= '.mcp.json'*
1196 1196

### outrage.config.SCOPES *= ('project', 'user')*
1353 1353

### outrage.config.SCRIPT_NAME *= 'outrage-server'*
1520 1520

### outrage.config.SERVERS_FIELD *= 'mcpServers'*
1785 1785

### outrage.config.SERVER_NAME *= 'outrage'*
1975 1975

### outrage.config.USER_CONFIG_NAME *= '.claude.json'*
2162 2162

### *class* outrage.config.Change(path: Path, scope: str, name: str, action: str, entry: dict[str, Any], previous: dict[str, Any] | None)
2369 2369

#### path *: Path*
3261 3261

#### scope *: str*
3344 3344

#### name *: str*
3419 3419

#### action *: str*
3493 3493

#### entry *: dict[str, Any]*
3607 3607

#### previous *: dict[str, Any] | None*
3809 3809

#### *property* writes *: bool*
4125 4125

### *exception* outrage.config.ConfigError(code: str, \*\*details: Any)
4215 4215

### outrage.config.config_path(scope: str, project_dir: str | PathLike[str] | None = None) → Path
4611 4611

### outrage.config.default_store_dir(project_dir: str | PathLike[str] | None = None) → Path
5096 5098

### outrage.config.launch_command(executable: str | PathLike[str] | None = None) → list[str]
5528 5532

### outrage.config.merge_entry(previous: dict[str, Any] | None, entry: dict[str, Any]) → dict[str, Any]
6328 6334

### outrage.config.mounts_in(args: Sequence[str]) → list[str]
8367 8375

### outrage.config.plan(path: Path, scope: str, entry: dict[str, Any], name: str = SERVER_NAME) → tuple[Change, dict[str, Any], str | None]
9063 9073

### outrage.config.read_config(path: Path) → tuple[dict[str, Any], str | None]
10119 10131

### outrage.config.script_command(script: str, executable: str | PathLike[str] | None = None) → list[str] | None
10933 10947

### outrage.config.server_entry(directory: str | PathLike[str], command: list[str] | None = None, \*, log: Any = None, log_content: str | None = None, no_info: bool = False, no_remount: bool = False) → dict[str, Any]
12045 12061

### outrage.config.split_args(args: Sequence[str]) → list[tuple[str, list[str]]]
15174 15192

### outrage.config.write_config(path: Path, config: dict[str, Any], original: str | None = None) → None
16179 16199
