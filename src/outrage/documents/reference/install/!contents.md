# outrage.install
0 0 1

## Four harnesses, one hook each
995 995 20

## The matcher outrage does not know the vocabulary of
3978 3978 70

## Why the marker exists
4644 4644 82

## The bridge this is
7443 7445 133

## The packaged files have no identity, so there is a receipt
8343 8345 149

### outrage.install.ASSET_DIRS *= ('skills', 'agents')*
10350 10352 182

### outrage.install.CLAUDE_DIR *= '.claude'*
10632 10634 188

### outrage.install.CODEX_DIR *= '.codex'*
10893 10895 194

### outrage.install.CURSOR_DIR *= '.cursor'*
11088 11090 199

### outrage.install.GITHUB_DIR *= '.github'*
11316 11318 204

### outrage.install.CLAUDE_HOOK *= HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}, context_field=None, payload_flag=None)*
11440 11442 208

### outrage.install.CODEX_HOOK *= HookTarget(name='Codex', template=PosixPath('codex.json'), relative=PosixPath('.codex/hooks.json'), event='SessionStart', base={}, context_field=None, payload_flag=None)*
11716 11718 212

### outrage.install.COPILOT_HOOK *= HookTarget(name='Copilot CLI', template=PosixPath('copilot.json'), relative=PosixPath('.github/hooks/outrage.json'), event='sessionStart', base={'version': 1}, context_field='additionalContext', payload_flag='--copilot')*
12223 12225 220

### outrage.install.CURSOR_HOOK *= HookTarget(name='Cursor', template=PosixPath('cursor.json'), relative=PosixPath('.cursor/hooks.json'), event='sessionStart', base={'version': 1}, context_field='additional_context', payload_flag='--cursor')*
12666 12668 226

### outrage.install.HOOKS_FIELD *= 'hooks'*
13216 13218 234

### outrage.install.HOOK_TARGETS *= (HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}, context_field=None, payload_flag=None), HookTarget(name='Copilot CLI', template=PosixPath('copilot.json'), relative=PosixPath('.github/hooks/outrage.json'), event='sessionStart', base={'version': 1}, context_field='additionalContext', payload_flag='--copilot'), HookTarget(name='Codex', template=PosixPath('codex.json'), relative=PosixPath('.codex/hooks.json'), event='SessionStart', base={}, context_field=None, payload_flag=None), HookTarget(name='Cursor', template=PosixPath('cursor.json'), relative=PosixPath('.cursor/hooks.json'), event='sessionStart', base={'version': 1}, context_field='additional_context', payload_flag='--cursor'))*
13386 13388 239

### outrage.install.MARKER *= 'outrage-managed:session-start'*
14275 14277 243

### outrage.install.MARKER_MATCH *= '-managed:session-start'*
14475 14477 248

### outrage.install.SESSIONSTART_MARKER *= 'outrage-managed:session-start:v3'*
14770 14772 254

### outrage.install.SETTINGS_NAME *= 'settings.json'*
15015 15017 259

### *class* outrage.install.Edit(path: Path, document: Any | None = None, original: str | None = None, toml: bool = False, delete: bool = False)
15170 15172 263

#### path *: Path*
16023 16025 272

#### document *: Any | None*
16106 16108 274

#### original *: str | None*
16325 16327 278

#### toml *: bool*
16534 16536 282

#### delete *: bool*
16612 16614 284

### *class* outrage.install.FileChange(path: Path, source: Path, action: str, relative: str = '')
16692 16694 286

#### path *: Path*
17171 17173 292

#### source *: Path*
17254 17256 294

#### action *: str*
17339 17341 296

#### relative *: str*
18149 18151 323

#### *property* writes *: bool*
18328 18330 328

#### *property* refuses *: bool*
18473 18475 332

#### describe() → str
18616 18618 336

### *class* outrage.install.HookChange(path: Path, action: str, entry: dict[str, Any], previous: dict[str, Any] | None, duplicates: int = 0, target: HookTarget = HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}, context_field=None, payload_flag=None), refusals: tuple[Refusal, ...] = ())
18695 18699 338

#### path *: Path*
19916 19920 344

#### action *: str*
19999 20003 346

#### entry *: dict[str, Any]*
20212 20216 352

#### previous *: dict[str, Any] | None*
20416 20420 354

#### duplicates *: int*
20746 20750 358

#### target *: HookTarget*
20901 20905 362

#### refusals *: tuple[Refusal, ...]*
21031 21035 366

#### *property* writes *: bool*
21504 21508 375

#### describe() → str
21595 21599 377

### *class* outrage.install.HookTarget(name: str, template: Path, relative: Path, event: str, base: dict[str, ~typing.Any]=<factory>, context_field: str | None = None, payload_flag: str | None = None)
21674 21680 379

#### name *: str*
22781 22787 390

#### template *: Path*
22903 22909 394

#### relative *: Path*
23605 23611 406

#### event *: str*
23744 23750 410

#### base *: dict[str, Any]*
23880 23886 414

#### context_field *: str | None*
24382 24388 423

#### payload_flag *: str | None*
24935 24941 433

#### *property* fragment *: Path*
25478 25484 442

#### path(project_dir: str | Path) → Path
25774 25780 449

### *exception* outrage.install.InstallError(code: str, \*\*details: Any)
26070 26078 453

### *class* outrage.install.InstallRecord(files: dict[str, str], version: int = 1)
26364 26372 459

#### files *: dict[str, str]*
27073 27081 469

#### version *: int*
27490 27498 475

#### *static* path_for(root: str | Path) → Path
27569 27577 477

#### *classmethod* read(root: str | Path) → InstallRecord | None
27856 27866 481

#### *classmethod* of(changes: Sequence[FileChange]) → InstallRecord
28454 28466 490

#### matches(relative: str, content: bytes) → bool
28996 29010 499

#### write(root: str | Path) → bool
29273 29289 503

### *class* outrage.install.Installation(project_dir: Path, server: Change, codex_server: Change, cursor_server: Change, hooks: tuple[HookChange, ...], assets: tuple[FileChange, ...], codex_assets: tuple[FileChange, ...], copilot_assets: tuple[FileChange, ...], table: Starter, refusals: tuple[Refusal, ...] = ())
29683 29701 510

#### project_dir *: Path*
30794 30812 516

#### server *: Change*
30884 30902 518

#### codex_server *: Change*
30943 30961 520

#### cursor_server *: Change*
31081 31099 524

#### hooks *: tuple[HookChange, ...]*
31322 31340 529

#### assets *: tuple[FileChange, ...]*
31523 31541 533

#### codex_assets *: tuple[FileChange, ...]*
31684 31702 537

#### copilot_assets *: tuple[FileChange, ...]*
31834 31852 541

#### table *: Starter*
31992 32010 545

#### refusals *: tuple[Refusal, ...]*
32131 32149 549

#### *property* writes *: bool*
32563 32581 558

### outrage.install.RECORD_NAME *= '.outrage.json'*
32654 32672 560

### outrage.install.RECORD_VERSION *= 1*
32926 32944 566

### *class* outrage.install.Uninstallation(project_dir: Path, forced: bool, server: Change, codex_server: Change, cursor_server: Change, hooks: tuple[HookChange, ...], assets: tuple[FileChange, ...], codex_assets: tuple[FileChange, ...], copilot_assets: tuple[FileChange, ...], receipts: tuple[Path, ...], file_refusals: tuple[Refusal, ...] = (), edits: tuple[Edit, ...] = ())
33115 33133 571

#### project_dir *: Path*
34647 34665 580

#### forced *: bool*
34737 34755 582

#### server *: Change*
34817 34835 584

#### codex_server *: Change*
34876 34894 586

#### cursor_server *: Change*
34941 34959 588

#### hooks *: tuple[HookChange, ...]*
35007 35025 590

#### assets *: tuple[FileChange, ...]*
35135 35153 592

#### codex_assets *: tuple[FileChange, ...]*
35264 35282 594

#### copilot_assets *: tuple[FileChange, ...]*
35399 35417 596

#### receipts *: tuple[Path, ...]*
35536 35554 598

#### file_refusals *: tuple[Refusal, ...]*
35832 35850 603

#### edits *: tuple[Edit, ...]*
35970 35988 605

#### *property* refusals *: tuple[Refusal, ...]*
36086 36104 607

#### *property* blocking *: tuple[Refusal, ...]*
36298 36316 611

#### *property* writes *: bool*
36518 36536 615

### outrage.install.apply_uninit(plan: Uninstallation) → None
36609 36627 617

### outrage.install.asset_refusals(changes: Sequence[FileChange]) → list[Refusal]
37326 37346 630

### outrage.install.asset_sources() → list[tuple[Path, Path]]
37754 37776 636

### outrage.install.codex_asset_sources() → list[tuple[Path, Path]]
38131 38155 640

### outrage.install.copilot_asset_sources() → list[tuple[Path, Path]]
38507 38533 644

### outrage.install.init(project_dir: str | Path, directory: str | Path | None = None, \*, log: Any = None, log_content: str | None = None, no_info: bool = False, no_remount: bool = False, no_versioning: bool = False, root_mount: str | None = None, mounts: Sequence[str] = (), read_only_mounts: Sequence[str] = (), dry_run: bool = False, force: bool = False) → Installation
38888 38916 648

### outrage.install.install(project_dir: str | Path, dry_run: bool = False, \*, target: HookTarget = CLAUDE_HOOK) → HookChange
42758 42788 686

### outrage.install.is_ours(entry: Any) → bool
43322 43354 693

### outrage.install.plan(path: Path, entry: dict[str, Any] | None = None, \*, target: HookTarget = CLAUDE_HOOK) → tuple[HookChange, dict[str, Any], str | None]
44107 44141 707

### outrage.install.plan_assets(project_dir: str | Path) → list[FileChange]
45263 45299 716

### outrage.install.plan_hook_removal(path: Path, \*, target: HookTarget = CLAUDE_HOOK) → tuple[HookChange, dict[str, Any] | None, str | None]
45624 45662 720

### outrage.install.plan_codex_assets(project_dir: str | Path) → list[FileChange]
47034 47074 738

### outrage.install.plan_copilot_assets(project_dir: str | Path) → list[FileChange]
47399 47441 742

### outrage.install.plan_uninit(project_dir: str | Path, \*, force: bool = False) → Uninstallation
47768 47812 746

### outrage.install.removal_action(change: FileChange, \*, forced: bool = False) → str
48732 48778 761

### outrage.install.removal_refusals(changes: Sequence[FileChange]) → list[Refusal]
49286 49334 770

### outrage.install.settings_path(project_dir: str | Path) → Path
50000 50050 780

### outrage.install.uninit(project_dir: str | Path, \*, dry_run: bool = False, force: bool = False) → Uninstallation
50315 50367 784

### outrage.install.sessionstart_command(executable: str | PathLike[str] | None = None, \*, target: HookTarget = CLAUDE_HOOK) → str
51670 51724 803

### outrage.install.sessionstart_payload(\*, target: HookTarget = CLAUDE_HOOK) → dict[str, Any]
52868 52924 819

### outrage.install.template_entry(target: HookTarget = CLAUDE_HOOK) → dict[str, Any]
53529 53587 828

### outrage.install.write_assets(changes: list[FileChange], \*, force: bool = False) → None
54211 54271 838
