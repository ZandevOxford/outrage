# outrage.install
0 0

## Three harnesses, one hook each
873 873

## The matcher outrage does not know the vocabulary of
2592 2592

## Why the marker exists
3258 3258

## The bridge this is
5805 5807

### outrage.install.ASSET_DIRS *= ('skills', 'agents')*
6592 6594

### outrage.install.CLAUDE_DIR *= '.claude'*
6874 6876

### outrage.install.CODEX_DIR *= '.codex'*
7135 7137

### outrage.install.GITHUB_DIR *= '.github'*
7330 7332

### outrage.install.CLAUDE_HOOK *= HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={})*
7454 7456

### outrage.install.CODEX_HOOK *= HookTarget(name='Codex', template=PosixPath('codex.json'), relative=PosixPath('.codex/hooks.json'), event='SessionStart', base={})*
7691 7693

### outrage.install.COPILOT_HOOK *= HookTarget(name='Copilot CLI', template=PosixPath('copilot.json'), relative=PosixPath('.github/hooks/outrage.json'), event='sessionStart', base={'version': 1})*
8159 8161

### outrage.install.HOOKS_FIELD *= 'hooks'*
8541 8543

### outrage.install.HOOK_TARGETS *= (HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}), HookTarget(name='Copilot CLI', template=PosixPath('copilot.json'), relative=PosixPath('.github/hooks/outrage.json'), event='sessionStart', base={'version': 1}), HookTarget(name='Codex', template=PosixPath('codex.json'), relative=PosixPath('.codex/hooks.json'), event='SessionStart', base={}))*
8711 8713

### outrage.install.MARKER *= 'outrage-managed:session-start'*
9253 9255

### outrage.install.MARKER_MATCH *= '-managed:session-start'*
9453 9455

### outrage.install.SESSIONSTART_MARKER *= 'outrage-managed:session-start:v3'*
9748 9750

### outrage.install.SETTINGS_NAME *= 'settings.json'*
9993 9995

### *class* outrage.install.FileChange(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), source: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), action: [str](https://docs.python.org/3/library/stdtypes.html#str))
10148 10150

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
10537 10539

#### source *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
10620 10622

#### action *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
10705 10707

#### *property* writes *: [bool](https://docs.python.org/3/library/functions.html#bool)*
10829 10831

#### describe() → [str](https://docs.python.org/3/library/stdtypes.html#str)
10919 10921

### *class* outrage.install.HookChange(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), action: [str](https://docs.python.org/3/library/stdtypes.html#str), entry: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)], previous: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None), duplicates: [int](https://docs.python.org/3/library/functions.html#int) = 0, target: [HookTarget](#outrage.install.HookTarget) = HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}))
10997 11001

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
12029 12033

#### action *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
12112 12116

#### entry *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*
12226 12230

#### previous *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None)*
12428 12432

#### duplicates *: [int](https://docs.python.org/3/library/functions.html#int)*
12744 12748

#### target *: [HookTarget](#outrage.install.HookTarget)*
12898 12902

#### *property* writes *: [bool](https://docs.python.org/3/library/functions.html#bool)*
13028 13032

#### describe() → [str](https://docs.python.org/3/library/stdtypes.html#str)
13118 13122

### *class* outrage.install.HookTarget(name: [str](https://docs.python.org/3/library/stdtypes.html#str), template: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), relative: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), event: [str](https://docs.python.org/3/library/stdtypes.html#str), base: dict[str, ~typing.Any]=<factory>)
13196 13202

#### name *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
14005 14011

#### template *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
14126 14132

#### relative *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
14841 14847

#### event *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
14980 14986

#### base *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*
15115 15121

#### *property* fragment *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
15600 15606

#### path(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
15896 15902

### *exception* outrage.install.InstallError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
16191 16199

### *class* outrage.install.Installation(project_dir: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), server: [Change](config.md#outrage.config.Change), hooks: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[HookChange](#outrage.install.HookChange), ...], assets: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...], codex_assets: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...], copilot_assets: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...], table: [Starter](mountfile.md#outrage.mountfile.Starter))
16484 16492

#### project_dir *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
17345 17353

#### server *: [Change](config.md#outrage.config.Change)*
17435 17443

#### hooks *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[HookChange](#outrage.install.HookChange), ...]*
17494 17502

#### assets *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...]*
17694 17702

#### codex_assets *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...]*
17854 17862

#### copilot_assets *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...]*
18003 18011

#### table *: [Starter](mountfile.md#outrage.mountfile.Starter)*
18160 18168

#### *property* writes *: [bool](https://docs.python.org/3/library/functions.html#bool)*
18299 18307

### outrage.install.asset_sources() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]]
18389 18397

### outrage.install.codex_asset_sources() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]]
18764 18774

### outrage.install.copilot_asset_sources() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]]
19138 19150

### outrage.install.init(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, log: [Any](https://docs.python.org/3/library/typing.html#typing.Any) = None, log_content: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, root_mount: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, mounts: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), read_only_mounts: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Installation](#outrage.install.Installation)
19517 19531

### outrage.install.install(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, \*, target: [HookTarget](#outrage.install.HookTarget) = CLAUDE_HOOK) → [HookChange](#outrage.install.HookChange)
22003 22019

### outrage.install.is_ours(entry: [Any](https://docs.python.org/3/library/typing.html#typing.Any)) → [bool](https://docs.python.org/3/library/functions.html#bool)
22565 22583

### outrage.install.plan(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), entry: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, target: [HookTarget](#outrage.install.HookTarget) = CLAUDE_HOOK) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[HookChange](#outrage.install.HookChange), [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)], [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]
23349 23369

### outrage.install.plan_assets(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[FileChange](#outrage.install.FileChange)]
24497 24519

### outrage.install.plan_codex_assets(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[FileChange](#outrage.install.FileChange)]
24856 24880

### outrage.install.plan_copilot_assets(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[FileChange](#outrage.install.FileChange)]
25219 25245

### outrage.install.settings_path(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
25586 25614

### outrage.install.sessionstart_command(executable: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, copilot: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [str](https://docs.python.org/3/library/stdtypes.html#str)
25900 25930

### outrage.install.sessionstart_payload(\*, copilot: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]
26836 26868

### outrage.install.template_entry(target: [HookTarget](#outrage.install.HookTarget) = CLAUDE_HOOK) → [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]
27218 27252

### outrage.install.write_assets(changes: [list](https://docs.python.org/3/library/stdtypes.html#list)[[FileChange](#outrage.install.FileChange)]) → [None](https://docs.python.org/3/library/constants.html#None)
27878 27914
