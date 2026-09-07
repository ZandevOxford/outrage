# outrage.install
0 0

## Three harnesses, one hook each
873 873

## The matcher outrage does not know the vocabulary of
2580 2580

## Why the marker exists
3246 3246

## The bridge this is
5746 5748

### outrage.install.ASSET_DIRS *= ('skills', 'agents')*
6533 6535

### outrage.install.CLAUDE_DIR *= '.claude'*
6815 6817

### outrage.install.CODEX_DIR *= '.codex'*
7076 7078

### outrage.install.GITHUB_DIR *= '.github'*
7271 7273

### outrage.install.CLAUDE_HOOK *= HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={})*
7395 7397

### outrage.install.CODEX_HOOK *= HookTarget(name='Codex', template=PosixPath('codex.json'), relative=PosixPath('.codex/hooks.json'), event='SessionStart', base={})*
7632 7634

### outrage.install.COPILOT_HOOK *= HookTarget(name='Copilot CLI', template=PosixPath('copilot.json'), relative=PosixPath('.github/hooks/outrage.json'), event='sessionStart', base={'version': 1})*
8100 8102

### outrage.install.HOOKS_FIELD *= 'hooks'*
8482 8484

### outrage.install.HOOK_TARGETS *= (HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}), HookTarget(name='Copilot CLI', template=PosixPath('copilot.json'), relative=PosixPath('.github/hooks/outrage.json'), event='sessionStart', base={'version': 1}), HookTarget(name='Codex', template=PosixPath('codex.json'), relative=PosixPath('.codex/hooks.json'), event='SessionStart', base={}))*
8652 8654

### outrage.install.MARKER *= 'outrage-managed:session-start'*
9194 9196

### outrage.install.MARKER_MATCH *= '-managed:session-start'*
9394 9396

### outrage.install.SESSIONSTART_MARKER *= 'outrage-managed:session-start:v3'*
9689 9691

### outrage.install.SETTINGS_NAME *= 'settings.json'*
9934 9936

### *class* outrage.install.FileChange(path: Path, source: Path, action: str)
10089 10091

#### path *: Path*
10478 10480

#### source *: Path*
10561 10563

#### action *: str*
10646 10648

#### *property* writes *: bool*
10770 10772

#### describe() → str
10860 10862

### *class* outrage.install.HookChange(path: Path, action: str, entry: dict[str, Any], previous: dict[str, Any] | None, duplicates: int = 0, target: HookTarget = HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}))
10938 10942

#### path *: Path*
11970 11974

#### action *: str*
12053 12057

#### entry *: dict[str, Any]*
12167 12171

#### previous *: dict[str, Any] | None*
12369 12373

#### duplicates *: int*
12685 12689

#### target *: HookTarget*
12839 12843

#### *property* writes *: bool*
12969 12973

#### describe() → str
13059 13063

### *class* outrage.install.HookTarget(name: str, template: Path, relative: Path, event: str, base: dict[str, ~typing.Any]=<factory>)
13137 13143

#### name *: str*
13946 13952

#### template *: Path*
14067 14073

#### relative *: Path*
14769 14775

#### event *: str*
14908 14914

#### base *: dict[str, Any]*
15043 15049

#### *property* fragment *: Path*
15528 15534

#### path(project_dir: str | Path) → Path
15824 15830

### *exception* outrage.install.InstallError(code: str, \*\*details: Any)
16119 16127

### *class* outrage.install.Installation(project_dir: Path, server: Change, hooks: tuple[HookChange, ...], assets: tuple[FileChange, ...], codex_assets: tuple[FileChange, ...], copilot_assets: tuple[FileChange, ...], table: Starter)
16412 16420

#### project_dir *: Path*
17273 17281

#### server *: Change*
17363 17371

#### hooks *: tuple[HookChange, ...]*
17422 17430

#### assets *: tuple[FileChange, ...]*
17622 17630

#### codex_assets *: tuple[FileChange, ...]*
17782 17790

#### copilot_assets *: tuple[FileChange, ...]*
17931 17939

#### table *: Starter*
18088 18096

#### *property* writes *: bool*
18227 18235

### outrage.install.asset_sources() → list[tuple[Path, Path]]
18317 18325

### outrage.install.codex_asset_sources() → list[tuple[Path, Path]]
18692 18702

### outrage.install.copilot_asset_sources() → list[tuple[Path, Path]]
19066 19078

### outrage.install.init(project_dir: str | Path, directory: str | Path | None = None, \*, log: Any = None, log_content: str | None = None, no_info: bool = False, no_remount: bool = False, root_mount: str | None = None, mounts: Sequence[str] = (), read_only_mounts: Sequence[str] = (), dry_run: bool = False) → Installation
19445 19459

### outrage.install.install(project_dir: str | Path, dry_run: bool = False, \*, target: HookTarget = CLAUDE_HOOK) → HookChange
22096 22112

### outrage.install.is_ours(entry: Any) → bool
22658 22676

### outrage.install.plan(path: Path, entry: dict[str, Any] | None = None, \*, target: HookTarget = CLAUDE_HOOK) → tuple[HookChange, dict[str, Any], str | None]
23442 23462

### outrage.install.plan_assets(project_dir: str | Path) → list[FileChange]
24590 24612

### outrage.install.plan_codex_assets(project_dir: str | Path) → list[FileChange]
24949 24973

### outrage.install.plan_copilot_assets(project_dir: str | Path) → list[FileChange]
25312 25338

### outrage.install.settings_path(project_dir: str | Path) → Path
25679 25707

### outrage.install.sessionstart_command(executable: str | PathLike[str] | None = None, \*, copilot: bool = False) → str
25993 26023

### outrage.install.sessionstart_payload(\*, copilot: bool = False) → dict[str, Any]
27050 27082

### outrage.install.template_entry(target: HookTarget = CLAUDE_HOOK) → dict[str, Any]
27432 27466

### outrage.install.write_assets(changes: list[FileChange]) → None
28092 28128
