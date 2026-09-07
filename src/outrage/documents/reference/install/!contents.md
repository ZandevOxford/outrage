# outrage.install
0 0

## Three harnesses, one hook each
873 873

## The matcher outrage does not know the vocabulary of
2654 2654

## Why the marker exists
3320 3320

## The bridge this is
5820 5822

### outrage.install.ASSET_DIRS *= ('skills', 'agents')*
6617 6619

### outrage.install.CLAUDE_DIR *= '.claude'*
6899 6901

### outrage.install.CODEX_DIR *= '.codex'*
7160 7162

### outrage.install.GITHUB_DIR *= '.github'*
7355 7357

### outrage.install.CLAUDE_HOOK *= HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={})*
7479 7481

### outrage.install.CODEX_HOOK *= HookTarget(name='Codex', template=PosixPath('codex.json'), relative=PosixPath('.codex/hooks.json'), event='SessionStart', base={})*
7716 7718

### outrage.install.COPILOT_HOOK *= HookTarget(name='Copilot CLI', template=PosixPath('copilot.json'), relative=PosixPath('.github/hooks/outrage.json'), event='sessionStart', base={'version': 1})*
8184 8186

### outrage.install.HOOKS_FIELD *= 'hooks'*
8566 8568

### outrage.install.HOOK_TARGETS *= (HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}), HookTarget(name='Copilot CLI', template=PosixPath('copilot.json'), relative=PosixPath('.github/hooks/outrage.json'), event='sessionStart', base={'version': 1}), HookTarget(name='Codex', template=PosixPath('codex.json'), relative=PosixPath('.codex/hooks.json'), event='SessionStart', base={}))*
8736 8738

### outrage.install.MARKER *= 'outrage-managed:session-start'*
9278 9280

### outrage.install.MARKER_MATCH *= '-managed:session-start'*
9478 9480

### outrage.install.SESSIONSTART_MARKER *= 'outrage-managed:session-start:v3'*
9773 9775

### outrage.install.SETTINGS_NAME *= 'settings.json'*
10018 10020

### *class* outrage.install.FileChange(path: Path, source: Path, action: str)
10173 10175

#### path *: Path*
10562 10564

#### source *: Path*
10645 10647

#### action *: str*
10730 10732

#### *property* writes *: bool*
10854 10856

#### describe() → str
10944 10946

### *class* outrage.install.HookChange(path: Path, action: str, entry: dict[str, Any], previous: dict[str, Any] | None, duplicates: int = 0, target: HookTarget = HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}))
11022 11026

#### path *: Path*
12054 12058

#### action *: str*
12137 12141

#### entry *: dict[str, Any]*
12251 12255

#### previous *: dict[str, Any] | None*
12453 12457

#### duplicates *: int*
12769 12773

#### target *: HookTarget*
12923 12927

#### *property* writes *: bool*
13053 13057

#### describe() → str
13143 13147

### *class* outrage.install.HookTarget(name: str, template: Path, relative: Path, event: str, base: dict[str, ~typing.Any]=<factory>)
13221 13227

#### name *: str*
14030 14036

#### template *: Path*
14151 14157

#### relative *: Path*
14853 14859

#### event *: str*
14992 14998

#### base *: dict[str, Any]*
15127 15133

#### *property* fragment *: Path*
15612 15618

#### path(project_dir: str | Path) → Path
15908 15914

### *exception* outrage.install.InstallError(code: str, \*\*details: Any)
16203 16211

### *class* outrage.install.Installation(project_dir: Path, server: Change, hooks: tuple[HookChange, ...], assets: tuple[FileChange, ...], codex_assets: tuple[FileChange, ...], copilot_assets: tuple[FileChange, ...], table: Starter)
16496 16504

#### project_dir *: Path*
17357 17365

#### server *: Change*
17447 17455

#### hooks *: tuple[HookChange, ...]*
17506 17514

#### assets *: tuple[FileChange, ...]*
17706 17714

#### codex_assets *: tuple[FileChange, ...]*
17866 17874

#### copilot_assets *: tuple[FileChange, ...]*
18015 18023

#### table *: Starter*
18172 18180

#### *property* writes *: bool*
18311 18319

### outrage.install.asset_sources() → list[tuple[Path, Path]]
18401 18409

### outrage.install.codex_asset_sources() → list[tuple[Path, Path]]
18776 18786

### outrage.install.copilot_asset_sources() → list[tuple[Path, Path]]
19150 19162

### outrage.install.init(project_dir: str | Path, directory: str | Path | None = None, \*, log: Any = None, log_content: str | None = None, no_info: bool = False, no_remount: bool = False, root_mount: str | None = None, mounts: Sequence[str] = (), read_only_mounts: Sequence[str] = (), dry_run: bool = False) → Installation
19529 19543

### outrage.install.install(project_dir: str | Path, dry_run: bool = False, \*, target: HookTarget = CLAUDE_HOOK) → HookChange
22180 22196

### outrage.install.is_ours(entry: Any) → bool
22742 22760

### outrage.install.plan(path: Path, entry: dict[str, Any] | None = None, \*, target: HookTarget = CLAUDE_HOOK) → tuple[HookChange, dict[str, Any], str | None]
23526 23546

### outrage.install.plan_assets(project_dir: str | Path) → list[FileChange]
24674 24696

### outrage.install.plan_codex_assets(project_dir: str | Path) → list[FileChange]
25033 25057

### outrage.install.plan_copilot_assets(project_dir: str | Path) → list[FileChange]
25396 25422

### outrage.install.settings_path(project_dir: str | Path) → Path
25763 25791

### outrage.install.sessionstart_command(executable: str | PathLike[str] | None = None, \*, copilot: bool = False) → str
26077 26107

### outrage.install.sessionstart_payload(\*, copilot: bool = False) → dict[str, Any]
27134 27166

### outrage.install.template_entry(target: HookTarget = CLAUDE_HOOK) → dict[str, Any]
27516 27550

### outrage.install.write_assets(changes: list[FileChange]) → None
28176 28212
