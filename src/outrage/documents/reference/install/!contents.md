# outrage.install
0 0

## Four harnesses, one hook each
995 995

## The matcher outrage does not know the vocabulary of
3978 3978

## Why the marker exists
4644 4644

## The bridge this is
7443 7445

### outrage.install.ASSET_DIRS *= ('skills', 'agents')*
8343 8345

### outrage.install.CLAUDE_DIR *= '.claude'*
8625 8627

### outrage.install.CODEX_DIR *= '.codex'*
8886 8888

### outrage.install.CURSOR_DIR *= '.cursor'*
9081 9083

### outrage.install.GITHUB_DIR *= '.github'*
9309 9311

### outrage.install.CLAUDE_HOOK *= HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}, context_field=None, payload_flag=None)*
9433 9435

### outrage.install.CODEX_HOOK *= HookTarget(name='Codex', template=PosixPath('codex.json'), relative=PosixPath('.codex/hooks.json'), event='SessionStart', base={}, context_field=None, payload_flag=None)*
9709 9711

### outrage.install.COPILOT_HOOK *= HookTarget(name='Copilot CLI', template=PosixPath('copilot.json'), relative=PosixPath('.github/hooks/outrage.json'), event='sessionStart', base={'version': 1}, context_field='additionalContext', payload_flag='--copilot')*
10216 10218

### outrage.install.CURSOR_HOOK *= HookTarget(name='Cursor', template=PosixPath('cursor.json'), relative=PosixPath('.cursor/hooks.json'), event='sessionStart', base={'version': 1}, context_field='additional_context', payload_flag='--cursor')*
10659 10661

### outrage.install.HOOKS_FIELD *= 'hooks'*
11209 11211

### outrage.install.HOOK_TARGETS *= (HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}, context_field=None, payload_flag=None), HookTarget(name='Copilot CLI', template=PosixPath('copilot.json'), relative=PosixPath('.github/hooks/outrage.json'), event='sessionStart', base={'version': 1}, context_field='additionalContext', payload_flag='--copilot'), HookTarget(name='Codex', template=PosixPath('codex.json'), relative=PosixPath('.codex/hooks.json'), event='SessionStart', base={}, context_field=None, payload_flag=None), HookTarget(name='Cursor', template=PosixPath('cursor.json'), relative=PosixPath('.cursor/hooks.json'), event='sessionStart', base={'version': 1}, context_field='additional_context', payload_flag='--cursor'))*
11379 11381

### outrage.install.MARKER *= 'outrage-managed:session-start'*
12268 12270

### outrage.install.MARKER_MATCH *= '-managed:session-start'*
12468 12470

### outrage.install.SESSIONSTART_MARKER *= 'outrage-managed:session-start:v3'*
12763 12765

### outrage.install.SETTINGS_NAME *= 'settings.json'*
13008 13010

### *class* outrage.install.FileChange(path: Path, source: Path, action: str)
13163 13165

#### path *: Path*
13554 13556

#### source *: Path*
13637 13639

#### action *: str*
13722 13724

#### *property* writes *: bool*
13847 13849

#### describe() → str
13938 13940

### *class* outrage.install.HookChange(path: Path, action: str, entry: dict[str, Any], previous: dict[str, Any] | None, duplicates: int = 0, target: HookTarget = HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}, context_field=None, payload_flag=None))
14017 14021

#### path *: Path*
15096 15100

#### action *: str*
15179 15183

#### entry *: dict[str, Any]*
15294 15298

#### previous *: dict[str, Any] | None*
15498 15502

#### duplicates *: int*
15817 15821

#### target *: HookTarget*
15972 15976

#### *property* writes *: bool*
16102 16106

#### describe() → str
16193 16197

### *class* outrage.install.HookTarget(name: str, template: Path, relative: Path, event: str, base: dict[str, ~typing.Any]=<factory>, context_field: str | None = None, payload_flag: str | None = None)
16272 16278

#### name *: str*
17379 17385

#### template *: Path*
17501 17507

#### relative *: Path*
18203 18209

#### event *: str*
18342 18348

#### base *: dict[str, Any]*
18478 18484

#### context_field *: str | None*
18980 18986

#### payload_flag *: str | None*
19533 19539

#### *property* fragment *: Path*
20076 20082

#### path(project_dir: str | Path) → Path
20372 20378

### *exception* outrage.install.InstallError(code: str, \*\*details: Any)
20668 20676

### *class* outrage.install.Installation(project_dir: Path, server: Change, codex_server: Change, cursor_server: Change, hooks: tuple[HookChange, ...], assets: tuple[FileChange, ...], codex_assets: tuple[FileChange, ...], copilot_assets: tuple[FileChange, ...], table: Starter)
20962 20970

#### project_dir *: Path*
21943 21951

#### server *: Change*
22033 22041

#### codex_server *: Change*
22092 22100

#### cursor_server *: Change*
22230 22238

#### hooks *: tuple[HookChange, ...]*
22471 22479

#### assets *: tuple[FileChange, ...]*
22672 22680

#### codex_assets *: tuple[FileChange, ...]*
22833 22841

#### copilot_assets *: tuple[FileChange, ...]*
22983 22991

#### table *: Starter*
23141 23149

#### *property* writes *: bool*
23280 23288

### outrage.install.asset_sources() → list[tuple[Path, Path]]
23371 23379

### outrage.install.codex_asset_sources() → list[tuple[Path, Path]]
23748 23758

### outrage.install.copilot_asset_sources() → list[tuple[Path, Path]]
24124 24136

### outrage.install.init(project_dir: str | Path, directory: str | Path | None = None, \*, log: Any = None, log_content: str | None = None, no_info: bool = False, no_remount: bool = False, no_versioning: bool = False, root_mount: str | None = None, mounts: Sequence[str] = (), read_only_mounts: Sequence[str] = (), dry_run: bool = False) → Installation
24505 24519

### outrage.install.install(project_dir: str | Path, dry_run: bool = False, \*, target: HookTarget = CLAUDE_HOOK) → HookChange
27754 27770

### outrage.install.is_ours(entry: Any) → bool
28318 28336

### outrage.install.plan(path: Path, entry: dict[str, Any] | None = None, \*, target: HookTarget = CLAUDE_HOOK) → tuple[HookChange, dict[str, Any], str | None]
29103 29123

### outrage.install.plan_assets(project_dir: str | Path) → list[FileChange]
30259 30281

### outrage.install.plan_codex_assets(project_dir: str | Path) → list[FileChange]
30620 30644

### outrage.install.plan_copilot_assets(project_dir: str | Path) → list[FileChange]
30985 31011

### outrage.install.settings_path(project_dir: str | Path) → Path
31354 31382

### outrage.install.sessionstart_command(executable: str | PathLike[str] | None = None, \*, target: HookTarget = CLAUDE_HOOK) → str
31669 31699

### outrage.install.sessionstart_payload(\*, target: HookTarget = CLAUDE_HOOK) → dict[str, Any]
32867 32899

### outrage.install.template_entry(target: HookTarget = CLAUDE_HOOK) → dict[str, Any]
33528 33562

### outrage.install.write_assets(changes: list[FileChange]) → None
34210 34246
