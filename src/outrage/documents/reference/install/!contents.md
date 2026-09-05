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

### *class* outrage.install.FileChange(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), source: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), action: [str](https://docs.python.org/3/library/stdtypes.html#str))
10089 10091

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
10478 10480

#### source *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
10561 10563

#### action *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
10646 10648

#### *property* writes *: [bool](https://docs.python.org/3/library/functions.html#bool)*
10770 10772

#### describe() → [str](https://docs.python.org/3/library/stdtypes.html#str)
10860 10862

### *class* outrage.install.HookChange(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), action: [str](https://docs.python.org/3/library/stdtypes.html#str), entry: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)], previous: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None), duplicates: [int](https://docs.python.org/3/library/functions.html#int) = 0, target: [HookTarget](#outrage.install.HookTarget) = HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}))
10938 10942

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
11970 11974

#### action *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
12053 12057

#### entry *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*
12167 12171

#### previous *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None)*
12369 12373

#### duplicates *: [int](https://docs.python.org/3/library/functions.html#int)*
12685 12689

#### target *: [HookTarget](#outrage.install.HookTarget)*
12839 12843

#### *property* writes *: [bool](https://docs.python.org/3/library/functions.html#bool)*
12969 12973

#### describe() → [str](https://docs.python.org/3/library/stdtypes.html#str)
13059 13063

### *class* outrage.install.HookTarget(name: [str](https://docs.python.org/3/library/stdtypes.html#str), template: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), relative: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), event: [str](https://docs.python.org/3/library/stdtypes.html#str), base: dict[str, ~typing.Any]=<factory>)
13137 13143

#### name *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
13946 13952

#### template *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
14067 14073

#### relative *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
14769 14775

#### event *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
14908 14914

#### base *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*
15043 15049

#### *property* fragment *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
15528 15534

#### path(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
15824 15830

### *exception* outrage.install.InstallError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
16119 16127

### *class* outrage.install.Installation(project_dir: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), server: [Change](config.md#outrage.config.Change), hooks: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[HookChange](#outrage.install.HookChange), ...], assets: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...], codex_assets: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...], copilot_assets: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...], table: [Starter](mountfile.md#outrage.mountfile.Starter))
16412 16420

#### project_dir *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
17273 17281

#### server *: [Change](config.md#outrage.config.Change)*
17363 17371

#### hooks *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[HookChange](#outrage.install.HookChange), ...]*
17422 17430

#### assets *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...]*
17622 17630

#### codex_assets *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...]*
17782 17790

#### copilot_assets *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...]*
17931 17939

#### table *: [Starter](mountfile.md#outrage.mountfile.Starter)*
18088 18096

#### *property* writes *: [bool](https://docs.python.org/3/library/functions.html#bool)*
18227 18235

### outrage.install.asset_sources() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]]
18317 18325

### outrage.install.codex_asset_sources() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]]
18692 18702

### outrage.install.copilot_asset_sources() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]]
19066 19078

### outrage.install.init(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, log: [Any](https://docs.python.org/3/library/typing.html#typing.Any) = None, log_content: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, root_mount: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, mounts: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), read_only_mounts: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Installation](#outrage.install.Installation)
19445 19459

### outrage.install.install(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, \*, target: [HookTarget](#outrage.install.HookTarget) = CLAUDE_HOOK) → [HookChange](#outrage.install.HookChange)
21931 21947

### outrage.install.is_ours(entry: [Any](https://docs.python.org/3/library/typing.html#typing.Any)) → [bool](https://docs.python.org/3/library/functions.html#bool)
22493 22511

### outrage.install.plan(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), entry: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, target: [HookTarget](#outrage.install.HookTarget) = CLAUDE_HOOK) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[HookChange](#outrage.install.HookChange), [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)], [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]
23277 23297

### outrage.install.plan_assets(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[FileChange](#outrage.install.FileChange)]
24425 24447

### outrage.install.plan_codex_assets(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[FileChange](#outrage.install.FileChange)]
24784 24808

### outrage.install.plan_copilot_assets(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[FileChange](#outrage.install.FileChange)]
25147 25173

### outrage.install.settings_path(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
25514 25542

### outrage.install.sessionstart_command(executable: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, copilot: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [str](https://docs.python.org/3/library/stdtypes.html#str)
25828 25858

### outrage.install.sessionstart_payload(\*, copilot: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]
26764 26796

### outrage.install.template_entry(target: [HookTarget](#outrage.install.HookTarget) = CLAUDE_HOOK) → [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]
27146 27180

### outrage.install.write_assets(changes: [list](https://docs.python.org/3/library/stdtypes.html#list)[[FileChange](#outrage.install.FileChange)]) → [None](https://docs.python.org/3/library/constants.html#None)
27806 27842
