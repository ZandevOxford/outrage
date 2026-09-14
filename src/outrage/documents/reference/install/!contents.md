# outrage.install
0 0

## Three harnesses, one hook each
962 962

## The matcher outrage does not know the vocabulary of
2743 2743

## Why the marker exists
3409 3409

## The bridge this is
5909 5911

### outrage.install.ASSET_DIRS *= ('skills', 'agents')*
6706 6708

### outrage.install.CLAUDE_DIR *= '.claude'*
6988 6990

### outrage.install.CODEX_DIR *= '.codex'*
7249 7251

### outrage.install.GITHUB_DIR *= '.github'*
7444 7446

### outrage.install.CLAUDE_HOOK *= HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={})*
7568 7570

### outrage.install.CODEX_HOOK *= HookTarget(name='Codex', template=PosixPath('codex.json'), relative=PosixPath('.codex/hooks.json'), event='SessionStart', base={})*
7805 7807

### outrage.install.COPILOT_HOOK *= HookTarget(name='Copilot CLI', template=PosixPath('copilot.json'), relative=PosixPath('.github/hooks/outrage.json'), event='sessionStart', base={'version': 1})*
8273 8275

### outrage.install.HOOKS_FIELD *= 'hooks'*
8655 8657

### outrage.install.HOOK_TARGETS *= (HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}), HookTarget(name='Copilot CLI', template=PosixPath('copilot.json'), relative=PosixPath('.github/hooks/outrage.json'), event='sessionStart', base={'version': 1}), HookTarget(name='Codex', template=PosixPath('codex.json'), relative=PosixPath('.codex/hooks.json'), event='SessionStart', base={}))*
8825 8827

### outrage.install.MARKER *= 'outrage-managed:session-start'*
9367 9369

### outrage.install.MARKER_MATCH *= '-managed:session-start'*
9567 9569

### outrage.install.SESSIONSTART_MARKER *= 'outrage-managed:session-start:v3'*
9862 9864

### outrage.install.SETTINGS_NAME *= 'settings.json'*
10107 10109

### *class* outrage.install.FileChange(path: Path, source: Path, action: str)
10262 10264

#### path *: Path*
10653 10655

#### source *: Path*
10736 10738

#### action *: str*
10821 10823

#### *property* writes *: bool*
10946 10948

#### describe() → str
11037 11039

### *class* outrage.install.HookChange(path: Path, action: str, entry: dict[str, Any], previous: dict[str, Any] | None, duplicates: int = 0, target: HookTarget = HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}))
11116 11120

#### path *: Path*
12156 12160

#### action *: str*
12239 12243

#### entry *: dict[str, Any]*
12354 12358

#### previous *: dict[str, Any] | None*
12558 12562

#### duplicates *: int*
12877 12881

#### target *: HookTarget*
13032 13036

#### *property* writes *: bool*
13162 13166

#### describe() → str
13253 13257

### *class* outrage.install.HookTarget(name: str, template: Path, relative: Path, event: str, base: dict[str, ~typing.Any]=<factory>)
13332 13338

#### name *: str*
14144 14150

#### template *: Path*
14266 14272

#### relative *: Path*
14968 14974

#### event *: str*
15107 15113

#### base *: dict[str, Any]*
15243 15249

#### *property* fragment *: Path*
15730 15736

#### path(project_dir: str | Path) → Path
16026 16032

### *exception* outrage.install.InstallError(code: str, \*\*details: Any)
16322 16330

### *class* outrage.install.Installation(project_dir: Path, server: Change, codex_server: Change, hooks: tuple[HookChange, ...], assets: tuple[FileChange, ...], codex_assets: tuple[FileChange, ...], copilot_assets: tuple[FileChange, ...], table: Starter)
16616 16624

#### project_dir *: Path*
17539 17547

#### server *: Change*
17629 17637

#### codex_server *: Change*
17688 17696

#### hooks *: tuple[HookChange, ...]*
17826 17834

#### assets *: tuple[FileChange, ...]*
18027 18035

#### codex_assets *: tuple[FileChange, ...]*
18188 18196

#### copilot_assets *: tuple[FileChange, ...]*
18338 18346

#### table *: Starter*
18496 18504

#### *property* writes *: bool*
18635 18643

### outrage.install.asset_sources() → list[tuple[Path, Path]]
18726 18734

### outrage.install.codex_asset_sources() → list[tuple[Path, Path]]
19103 19113

### outrage.install.copilot_asset_sources() → list[tuple[Path, Path]]
19479 19491

### outrage.install.init(project_dir: str | Path, directory: str | Path | None = None, \*, log: Any = None, log_content: str | None = None, no_info: bool = False, no_remount: bool = False, no_versioning: bool = False, root_mount: str | None = None, mounts: Sequence[str] = (), read_only_mounts: Sequence[str] = (), dry_run: bool = False) → Installation
19860 19874

### outrage.install.install(project_dir: str | Path, dry_run: bool = False, \*, target: HookTarget = CLAUDE_HOOK) → HookChange
22851 22867

### outrage.install.is_ours(entry: Any) → bool
23415 23433

### outrage.install.plan(path: Path, entry: dict[str, Any] | None = None, \*, target: HookTarget = CLAUDE_HOOK) → tuple[HookChange, dict[str, Any], str | None]
24200 24220

### outrage.install.plan_assets(project_dir: str | Path) → list[FileChange]
25356 25378

### outrage.install.plan_codex_assets(project_dir: str | Path) → list[FileChange]
25717 25741

### outrage.install.plan_copilot_assets(project_dir: str | Path) → list[FileChange]
26082 26108

### outrage.install.settings_path(project_dir: str | Path) → Path
26451 26479

### outrage.install.sessionstart_command(executable: str | PathLike[str] | None = None, \*, copilot: bool = False) → str
26766 26796

### outrage.install.sessionstart_payload(\*, copilot: bool = False) → dict[str, Any]
27828 27860

### outrage.install.template_entry(target: HookTarget = CLAUDE_HOOK) → dict[str, Any]
28213 28247

### outrage.install.write_assets(changes: list[FileChange]) → None
28875 28911
