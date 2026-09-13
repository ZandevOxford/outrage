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
10651 10653

#### source *: Path*
10734 10736

#### action *: str*
10819 10821

#### *property* writes *: bool*
10943 10945

#### describe() → str
11033 11035

### *class* outrage.install.HookChange(path: Path, action: str, entry: dict[str, Any], previous: dict[str, Any] | None, duplicates: int = 0, target: HookTarget = HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}))
11111 11115

#### path *: Path*
12143 12147

#### action *: str*
12226 12230

#### entry *: dict[str, Any]*
12340 12344

#### previous *: dict[str, Any] | None*
12542 12546

#### duplicates *: int*
12858 12862

#### target *: HookTarget*
13012 13016

#### *property* writes *: bool*
13142 13146

#### describe() → str
13232 13236

### *class* outrage.install.HookTarget(name: str, template: Path, relative: Path, event: str, base: dict[str, ~typing.Any]=<factory>)
13310 13316

#### name *: str*
14119 14125

#### template *: Path*
14240 14246

#### relative *: Path*
14942 14948

#### event *: str*
15081 15087

#### base *: dict[str, Any]*
15216 15222

#### *property* fragment *: Path*
15701 15707

#### path(project_dir: str | Path) → Path
15997 16003

### *exception* outrage.install.InstallError(code: str, \*\*details: Any)
16292 16300

### *class* outrage.install.Installation(project_dir: Path, server: Change, codex_server: Change, hooks: tuple[HookChange, ...], assets: tuple[FileChange, ...], codex_assets: tuple[FileChange, ...], copilot_assets: tuple[FileChange, ...], table: Starter)
16585 16593

#### project_dir *: Path*
17503 17511

#### server *: Change*
17593 17601

#### codex_server *: Change*
17652 17660

#### hooks *: tuple[HookChange, ...]*
17790 17798

#### assets *: tuple[FileChange, ...]*
17990 17998

#### codex_assets *: tuple[FileChange, ...]*
18150 18158

#### copilot_assets *: tuple[FileChange, ...]*
18299 18307

#### table *: Starter*
18456 18464

#### *property* writes *: bool*
18595 18603

### outrage.install.asset_sources() → list[tuple[Path, Path]]
18685 18693

### outrage.install.codex_asset_sources() → list[tuple[Path, Path]]
19060 19070

### outrage.install.copilot_asset_sources() → list[tuple[Path, Path]]
19434 19446

### outrage.install.init(project_dir: str | Path, directory: str | Path | None = None, \*, log: Any = None, log_content: str | None = None, no_info: bool = False, no_remount: bool = False, no_versioning: bool = False, root_mount: str | None = None, mounts: Sequence[str] = (), read_only_mounts: Sequence[str] = (), dry_run: bool = False) → Installation
19813 19827

### outrage.install.install(project_dir: str | Path, dry_run: bool = False, \*, target: HookTarget = CLAUDE_HOOK) → HookChange
22791 22807

### outrage.install.is_ours(entry: Any) → bool
23353 23371

### outrage.install.plan(path: Path, entry: dict[str, Any] | None = None, \*, target: HookTarget = CLAUDE_HOOK) → tuple[HookChange, dict[str, Any], str | None]
24137 24157

### outrage.install.plan_assets(project_dir: str | Path) → list[FileChange]
25285 25307

### outrage.install.plan_codex_assets(project_dir: str | Path) → list[FileChange]
25644 25668

### outrage.install.plan_copilot_assets(project_dir: str | Path) → list[FileChange]
26007 26033

### outrage.install.settings_path(project_dir: str | Path) → Path
26374 26402

### outrage.install.sessionstart_command(executable: str | PathLike[str] | None = None, \*, copilot: bool = False) → str
26688 26718

### outrage.install.sessionstart_payload(\*, copilot: bool = False) → dict[str, Any]
27745 27777

### outrage.install.template_entry(target: HookTarget = CLAUDE_HOOK) → dict[str, Any]
28127 28161

### outrage.install.write_assets(changes: list[FileChange]) → None
28787 28823
