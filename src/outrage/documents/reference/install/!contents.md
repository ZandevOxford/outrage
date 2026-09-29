# outrage.install
0 0 1

## Four harnesses, one hook each
1152 1152 22

## The matcher outrage does not know the vocabulary of
4135 4135 72

## Why the marker exists
4801 4801 84

## The bridge this is
7600 7602 135

## The packaged files have no identity, so there is a receipt
8500 8502 151

### outrage.install.ASSET_DIRS *= ('skills', 'agents')*
10507 10509 184

### outrage.install.CLAUDE_DIR *= '.claude'*
10789 10791 190

### outrage.install.CODEX_DIR *= '.codex'*
11050 11052 196

### outrage.install.CURSOR_DIR *= '.cursor'*
11245 11247 201

### outrage.install.GITHUB_DIR *= '.github'*
11473 11475 206

### outrage.install.CLAUDE_HOOK *= HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}, context_field=None, payload_flag=None)*
11597 11599 210

### outrage.install.CODEX_HOOK *= HookTarget(name='Codex', template=PosixPath('codex.json'), relative=PosixPath('.codex/hooks.json'), event='SessionStart', base={}, context_field=None, payload_flag=None)*
11873 11875 214

### outrage.install.COPILOT_HOOK *= HookTarget(name='Copilot CLI', template=PosixPath('copilot.json'), relative=PosixPath('.github/hooks/outrage.json'), event='sessionStart', base={'version': 1}, context_field='additionalContext', payload_flag='--copilot')*
12380 12382 222

### outrage.install.CURSOR_HOOK *= HookTarget(name='Cursor', template=PosixPath('cursor.json'), relative=PosixPath('.cursor/hooks.json'), event='sessionStart', base={'version': 1}, context_field='additional_context', payload_flag='--cursor')*
12823 12825 228

### outrage.install.HOOKS_FIELD *= 'hooks'*
13373 13375 236

### outrage.install.HOOK_TARGETS *= (HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}, context_field=None, payload_flag=None), HookTarget(name='Copilot CLI', template=PosixPath('copilot.json'), relative=PosixPath('.github/hooks/outrage.json'), event='sessionStart', base={'version': 1}, context_field='additionalContext', payload_flag='--copilot'), HookTarget(name='Codex', template=PosixPath('codex.json'), relative=PosixPath('.codex/hooks.json'), event='SessionStart', base={}, context_field=None, payload_flag=None), HookTarget(name='Cursor', template=PosixPath('cursor.json'), relative=PosixPath('.cursor/hooks.json'), event='sessionStart', base={'version': 1}, context_field='additional_context', payload_flag='--cursor'))*
13543 13545 241

### outrage.install.MARKER *= 'outrage-managed:session-start'*
14432 14434 245

### outrage.install.MARKER_MATCH *= '-managed:session-start'*
14632 14634 250

### outrage.install.SESSIONSTART_MARKER *= 'outrage-managed:session-start:v3'*
14927 14929 256

### outrage.install.SETTINGS_NAME *= 'settings.json'*
15172 15174 261

### *class* outrage.install.Edit(path: Path, document: Any | None = None, original: str | None = None, toml: bool = False, delete: bool = False)
15327 15329 265

#### path *: Path*
16180 16182 274

#### document *: Any | None*
16263 16265 276

#### original *: str | None*
16482 16484 280

#### toml *: bool*
16691 16693 284

#### delete *: bool*
16769 16771 286

### *class* outrage.install.FileChange(path: Path, source: Path, action: str, relative: str = '')
16849 16851 288

#### path *: Path*
17328 17330 294

#### source *: Path*
17411 17413 296

#### action *: str*
17496 17498 298

#### relative *: str*
18306 18308 325

#### *property* writes *: bool*
18485 18487 330

#### *property* refuses *: bool*
18630 18632 334

#### describe() → str
18773 18775 338

### *class* outrage.install.HookChange(path: Path, action: str, entry: dict[str, Any], previous: dict[str, Any] | None, duplicates: int = 0, target: HookTarget = HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}, context_field=None, payload_flag=None), refusals: tuple[Refusal, ...] = ())
18852 18856 340

#### path *: Path*
20073 20077 346

#### action *: str*
20156 20160 348

#### entry *: dict[str, Any]*
20369 20373 354

#### previous *: dict[str, Any] | None*
20573 20577 356

#### duplicates *: int*
20903 20907 360

#### target *: HookTarget*
21058 21062 364

#### refusals *: tuple[Refusal, ...]*
21188 21192 368

#### *property* writes *: bool*
21661 21665 377

#### describe() → str
21752 21756 379

### *class* outrage.install.HookTarget(name: str, template: Path, relative: Path, event: str, base: dict[str, ~typing.Any]=<factory>, context_field: str | None = None, payload_flag: str | None = None)
21831 21837 381

#### name *: str*
22938 22944 392

#### template *: Path*
23060 23066 396

#### relative *: Path*
23762 23768 408

#### event *: str*
23901 23907 412

#### base *: dict[str, Any]*
24037 24043 416

#### context_field *: str | None*
24539 24545 425

#### payload_flag *: str | None*
25092 25098 435

#### *property* fragment *: Path*
25635 25641 444

#### path(project_dir: str | Path) → Path
25931 25937 451

### *exception* outrage.install.InstallError(code: str, \*\*details: Any)
26227 26235 455

### *class* outrage.install.InstallRecord(files: dict[str, str], version: int = 1)
26521 26529 461

#### files *: dict[str, str]*
27230 27238 471

#### version *: int*
27647 27655 477

#### *static* path_for(root: str | Path) → Path
27726 27734 479

#### *classmethod* read(root: str | Path) → InstallRecord | None
28013 28023 483

#### *classmethod* of(changes: Sequence[FileChange]) → InstallRecord
28611 28623 492

#### matches(relative: str, content: bytes) → bool
29153 29167 501

#### write(root: str | Path) → bool
29430 29446 505

### *class* outrage.install.Installation(project_dir: Path, server: Change, codex_server: Change, cursor_server: Change, hooks: tuple[HookChange, ...], assets: tuple[FileChange, ...], codex_assets: tuple[FileChange, ...], copilot_assets: tuple[FileChange, ...], table: Starter, refusals: tuple[Refusal, ...] = ())
29840 29858 512

#### project_dir *: Path*
30951 30969 518

#### server *: Change*
31041 31059 520

#### codex_server *: Change*
31100 31118 522

#### cursor_server *: Change*
31238 31256 526

#### hooks *: tuple[HookChange, ...]*
31479 31497 531

#### assets *: tuple[FileChange, ...]*
31680 31698 535

#### codex_assets *: tuple[FileChange, ...]*
31841 31859 539

#### copilot_assets *: tuple[FileChange, ...]*
31991 32009 543

#### table *: Starter*
32149 32167 547

#### refusals *: tuple[Refusal, ...]*
32288 32306 551

#### *property* writes *: bool*
32720 32738 560

### outrage.install.RECORD_NAME *= '.outrage.json'*
32811 32829 562

### outrage.install.RECORD_VERSION *= 1*
33083 33101 568

### *class* outrage.install.Uninstallation(project_dir: Path, forced: bool, server: Change, codex_server: Change, cursor_server: Change, hooks: tuple[HookChange, ...], assets: tuple[FileChange, ...], codex_assets: tuple[FileChange, ...], copilot_assets: tuple[FileChange, ...], receipts: tuple[Path, ...], file_refusals: tuple[Refusal, ...] = (), edits: tuple[Edit, ...] = ())
33272 33290 573

#### project_dir *: Path*
34804 34822 582

#### forced *: bool*
34894 34912 584

#### server *: Change*
34974 34992 586

#### codex_server *: Change*
35033 35051 588

#### cursor_server *: Change*
35098 35116 590

#### hooks *: tuple[HookChange, ...]*
35164 35182 592

#### assets *: tuple[FileChange, ...]*
35292 35310 594

#### codex_assets *: tuple[FileChange, ...]*
35421 35439 596

#### copilot_assets *: tuple[FileChange, ...]*
35556 35574 598

#### receipts *: tuple[Path, ...]*
35693 35711 600

#### file_refusals *: tuple[Refusal, ...]*
35989 36007 605

#### edits *: tuple[Edit, ...]*
36127 36145 607

#### *property* refusals *: tuple[Refusal, ...]*
36243 36261 609

#### *property* blocking *: tuple[Refusal, ...]*
36455 36473 613

#### *property* writes *: bool*
36675 36693 617

### outrage.install.apply_uninit(plan: Uninstallation) → None
36766 36784 619

### outrage.install.asset_refusals(changes: Sequence[FileChange]) → list[Refusal]
37483 37503 632

### outrage.install.asset_sources() → list[tuple[Path, Path]]
37911 37933 638

### outrage.install.codex_asset_sources() → list[tuple[Path, Path]]
38288 38312 642

### outrage.install.copilot_asset_sources() → list[tuple[Path, Path]]
38664 38690 646

### outrage.install.init(project_dir: str | Path, directory: str | Path | None = None, \*, log: Any = None, log_content: str | None = None, no_info: bool = False, no_remount: bool = False, no_versioning: bool = False, smart_search: bool = False, root_mount: str | None = None, mounts: Sequence[str] = (), read_only_mounts: Sequence[str] = (), dry_run: bool = False, force: bool = False) → Installation
39045 39073 650

### outrage.install.install(project_dir: str | Path, dry_run: bool = False, \*, target: HookTarget = CLAUDE_HOOK) → HookChange
43017 43047 688

### outrage.install.is_ours(entry: Any) → bool
43581 43613 695

### outrage.install.plan(path: Path, entry: dict[str, Any] | None = None, \*, target: HookTarget = CLAUDE_HOOK) → tuple[HookChange, dict[str, Any], str | None]
44366 44400 709

### outrage.install.plan_assets(project_dir: str | Path) → list[FileChange]
45522 45558 718

### outrage.install.plan_hook_removal(path: Path, \*, target: HookTarget = CLAUDE_HOOK) → tuple[HookChange, dict[str, Any] | None, str | None]
45883 45921 722

### outrage.install.plan_codex_assets(project_dir: str | Path) → list[FileChange]
47293 47333 740

### outrage.install.plan_copilot_assets(project_dir: str | Path) → list[FileChange]
47658 47700 744

### outrage.install.plan_uninit(project_dir: str | Path, \*, force: bool = False) → Uninstallation
48027 48071 748

### outrage.install.removal_action(change: FileChange, \*, forced: bool = False) → str
48991 49037 763

### outrage.install.removal_refusals(changes: Sequence[FileChange]) → list[Refusal]
49545 49593 772

### outrage.install.settings_path(project_dir: str | Path) → Path
50259 50309 782

### outrage.install.uninit(project_dir: str | Path, \*, dry_run: bool = False, force: bool = False) → Uninstallation
50574 50626 786

### outrage.install.sessionstart_command(executable: str | PathLike[str] | None = None, \*, target: HookTarget = CLAUDE_HOOK) → str
51929 51983 805

### outrage.install.sessionstart_payload(\*, target: HookTarget = CLAUDE_HOOK) → dict[str, Any]
53127 53183 821

### outrage.install.template_entry(target: HookTarget = CLAUDE_HOOK) → dict[str, Any]
53788 53846 830

### outrage.install.write_assets(changes: list[FileChange], \*, force: bool = False) → None
54470 54530 840
