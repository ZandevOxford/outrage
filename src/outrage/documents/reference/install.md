# outrage.install

Setting a project up: the MCP entry, hooks, and harness-specific skills.

`init` is the whole of `outrage init` and the three parts are separable: the
server entry is [`outrage.config`](config.md#module-outrage.config)'s and is called rather than repeated, the
session-start hooks are written here, and packaged assets are copied into the
directories their harness reads. Most of what follows is about the hooks,
because they are the part with something to say.

A config file belongs to the user, not to outrage. It holds their model, their
permissions and their own hooks, so this writes the one entry it owns and
leaves everything else exactly as it found it - the rule [`outrage.config`](config.md#module-outrage.config)
already follows for `.mcp.json`, and the reason its `read_config` and
`write_config` are reused here rather than reimplemented.

## Three harnesses, one hook each

[`HOOK_TARGETS`](#outrage.install.HOOK_TARGETS) is the list, and everything below takes one of them rather
than assuming Claude Code. Adding the second one is what turned the constants
into a [`HookTarget`](#outrage.install.HookTarget), on the rule that nothing is generalised before
there is a second real case to generalise *to*, and Copilot CLI was it. Codex,
added third, cost a template and a constant and no change to any function here
- which is the shape working.

They differ in more than spelling:

* **Claude Code** merges into `.claude/settings.json`, a file the user owns
  outright and which this project does not commit.
* **Copilot CLI** takes a file per purpose under `.github/hooks/`, so
  `.github/hooks/outrage.json` is outrage's own, and repository agents under
  `.github/agents/`. `.github` is usually **committed**, so a re-run's diff
  lands in somebody's version control where the Claude one does not.
* Copilot's entry carries the command twice, as `bash` and `powershell`,
  and the file needs `"version": 1` at its top. Hence
  [`HookTarget.base`](#outrage.install.HookTarget.base): what to start from when the file does not exist.
* **Codex** reads `.codex/hooks.json`, its own file like Copilot's, but the
  entry inside is Claude Code's shape down to the `hookSpecificOutput`
  payload - so the two templates differ only in the `matcher` below.
  `.codex` is not committed here, so it behaves like the Claude file rather
  than the Copilot one.

All three are written by default. A project that uses one harness carries a
small inert file for the other two, which is cheaper than an installer that has
to be told what the user is running.

## The matcher outrage does not know the vocabulary of

Codex's documented `SessionStart` example carries `"matcher":
"startup|resume"`, and the template ships exactly that. Whether the field is
required, and what else it could match, is **not** established: the
documentation gives no list of sources. Both readings fail the same silent way
this project keeps being caught by - omit a required matcher and the hook never
fires; ship a narrow one and it stops firing on whatever source is not named -
so this ships what was documented and does not improve on it. If a Codex
session is ever seen starting a way this does not match, that is the evidence
to widen it.

## Why the marker exists

`mcpServers` is an object, so [`outrage.config`](config.md#module-outrage.config) can key on a name and
replace one entry. `hooks.SessionStart` is a **list**, and nothing in it says
who wrote what. An installer that cannot recognise its own entry has only bad
options: append every run and accumulate duplicates, or replace the lot and
destroy hooks it did not write.

All three harnesses carry the marker as the final argument to the managed
command:

```default
<python> -m outrage sessionstart outrage-managed:session-start:v3
```

The CLI accepts that one private argument and does not print it, so the marker
is independent of shell comment syntax and remains absent from stdout.

Copilot's command also carries a hidden `--copilot` flag so the CLI emits its
flat `additionalContext` payload rather than Claude and Codex's nested one.
Older Copilot entries carried the marker in a `comment` field, and older
Claude Code and Codex entries carried it in a trailing shell comment;
[`is_ours()`](#outrage.install.is_ours) looks for the marker anywhere in the entry, so every generation
is recognised and replaced without a migration.

An unknown JSON key on the entry - `{"_outrageManaged": …}` - was tested and
works: the client tolerates it and the hook still fires. It was rejected
anyway. It depends on that tolerance continuing, which is undocumented, and if
it ever stops the hook is rejected and delivers nothing *silently*. An ordinary
argument belongs to the command contract and needs no undocumented JSON
tolerance. Both client behaviours this project has been burnt by were
undocumented ones.

**Match on the stable part, never the whole marker.** `:vN` is
informational, and so is the product name in front of it. A matcher that
includes either stops recognising the entry it exists to replace the moment
that part changes, which is how one hook becomes two.

That is not hypothetical: the rename to `outrage` moved the name, an upgrade
stopped recognising what the previous release had written, and `init`
appended a second session-start hook instead of replacing the first. So
[`MARKER`](#outrage.install.MARKER) is what gets *written* and [`MARKER_MATCH`](#outrage.install.MARKER_MATCH) is what gets
*compared*, and the second is the part a rename does not touch. The cost is a
slightly wider namespace claim - any entry carrying `-managed:session-start`
is treated as ours - which is the same bet the previous matcher already made
one word further along.

## The bridge this is

All three hooks now run `<python> -m outrage sessionstart`.
The interpreter is the absolute [`sys.executable`](https://docs.python.org/3/library/sys.html#sys.executable) of the environment that
ran `outrage init`, for the same reason the MCP entry names that environment:
a hook does not inherit an activated environment. The managed marker is an
ordinary final argument rather than a shell comment, so neither it nor the
command depends on `#` meaning the same thing on every platform.

Copilot CLI remains different only at the boundary: its hook contract provides
separate `bash` and `powershell` commands and its output is the documented
flat payload. The same command reads the same shipped prompt at invocation time
and selects that shape with `--copilot`.

### outrage.install.ASSET_DIRS *= ('skills', 'agents')*

Packaged directories that install into `.claude/`, copied whole. Markdown
a client reads directly: nothing here is executed, so nothing here needs an
interpreter or an absolute path, and a copy of it is complete on its own.

### outrage.install.CLAUDE_DIR *= '.claude'*

Where a project's skills, agents and settings live, relative to its root.
Declared above its three users rather than beside the assets, because the
settings path is one of them and used to spell the directory out.

### outrage.install.CODEX_DIR *= '.codex'*

Where Codex reads project-scoped skills and hooks, relative to the project
root. Both live below it, so the hook target spells out only the filename.

### outrage.install.GITHUB_DIR *= '.github'*

Where Copilot CLI reads its repository hook and preferred agent definitions.

### outrage.install.CLAUDE_HOOK *= HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={})*

Claude Code: merged into the user's own settings file.

### outrage.install.CODEX_HOOK *= HookTarget(name='Codex', template=PosixPath('codex.json'), relative=PosixPath('.codex/hooks.json'), event='SessionStart', base={})*

Codex: its own file, like Copilot CLI, but the entry is Claude Code's shape
- `SessionStart`, a nested `hooks` list, and the same
`hookSpecificOutput` payload. The one thing neither of the others has is
the `matcher`; see the module docstring on why it is written as documented
rather than left out.

### outrage.install.COPILOT_HOOK *= HookTarget(name='Copilot CLI', template=PosixPath('copilot.json'), relative=PosixPath('.github/hooks/outrage.json'), event='sessionStart', base={'version': 1})*

Copilot CLI: a file per purpose, so this one is outrage's own. Named for the
package rather than the event, so a second outrage hook joins it here rather
than claiming a second file.

### outrage.install.HOOKS_FIELD *= 'hooks'*

The key below which that merge happens. Everything else in the file is
somebody else's and is written back as it was found.

### outrage.install.HOOK_TARGETS *= (HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}), HookTarget(name='Copilot CLI', template=PosixPath('copilot.json'), relative=PosixPath('.github/hooks/outrage.json'), event='sessionStart', base={'version': 1}), HookTarget(name='Codex', template=PosixPath('codex.json'), relative=PosixPath('.codex/hooks.json'), event='SessionStart', base={}))*

Every hook `outrage init` writes, in the order it reports them.

### outrage.install.MARKER *= 'outrage-managed:session-start'*

What gets written into the entry, minus the `:vN` the template adds. One
marker for both harnesses: it names the hook, not the client.

### outrage.install.MARKER_MATCH *= '-managed:session-start'*

What a matcher compares against: [`MARKER`](#outrage.install.MARKER) without the product name, so
that an entry written under a former name is still recognised as ours and
replaced rather than duplicated. See the module docstring.

### outrage.install.SESSIONSTART_MARKER *= 'outrage-managed:session-start:v3'*

The complete marker written as the final CLI argument. The stable part is
still [`MARKER_MATCH`](#outrage.install.MARKER_MATCH); the version remains informational.

### outrage.install.SETTINGS_NAME *= 'settings.json'*

The settings file the fragment is merged into, inside [`CLAUDE_DIR`](#outrage.install.CLAUDE_DIR).

### *class* outrage.install.FileChange(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), source: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), action: [str](https://docs.python.org/3/library/stdtypes.html#str))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

What installing one packaged file would do, or did.

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

#### source *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

#### action *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

'created', 'updated', 'unchanged' or 'linked'.

#### *property* writes *: [bool](https://docs.python.org/3/library/functions.html#bool)*

#### describe() → [str](https://docs.python.org/3/library/stdtypes.html#str)

### *class* outrage.install.HookChange(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), action: [str](https://docs.python.org/3/library/stdtypes.html#str), entry: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)], previous: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None), duplicates: [int](https://docs.python.org/3/library/functions.html#int) = 0, target: [HookTarget](#outrage.install.HookTarget) = HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

What installing the hook would do, or did.

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

#### action *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

'created', 'updated' or 'unchanged'.

#### entry *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*

#### previous *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None)*

The entry being replaced, when there was one.

#### duplicates *: [int](https://docs.python.org/3/library/functions.html#int)*

Extra entries of ours removed, from a run that could not identify them.

#### target *: [HookTarget](#outrage.install.HookTarget)*

Which harness's hook this is, so a report over several can name them.

#### *property* writes *: [bool](https://docs.python.org/3/library/functions.html#bool)*

#### describe() → [str](https://docs.python.org/3/library/stdtypes.html#str)

### *class* outrage.install.HookTarget(name: [str](https://docs.python.org/3/library/stdtypes.html#str), template: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), relative: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), event: [str](https://docs.python.org/3/library/stdtypes.html#str), base: dict[str, ~typing.Any]=<factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One harness's session-start hook: where it goes and what shape it is.

Everything harness-specific about the hook is one of these fields, so
supporting a third client is a fourth instance rather than a branch in the
code below. What is *not* here is deliberate: the merge rule, the marker
and the refusal to touch what it did not write are the same everywhere.

#### name *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

What `outrage init` calls this in its output.

#### template *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

The packaged fragment, **relative to the hooks directory**, holding the
entry exactly as it is installed. [`fragment`](#outrage.install.HookTarget.fragment) is where it actually is.

Relative for the same reason [`relative`](#outrage.install.HookTarget.relative) is: a field that is the whole
installation's absolute path is different on every machine, and this
dataclass's `repr` is *rendered into the shipped API reference*. An
absolute path here commits the build machine's checkout to
`documents/reference/install.md`, and `test_the_reference_is_not_stale`
then fails for anyone whose clone is somewhere else.

#### relative *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

Where the file goes, relative to the project root.

#### event *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The key below `hooks` this harness fires at session start.

#### base *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*

What a newly created file starts from, before the entry is merged in.

Empty for Claude Code. Copilot CLI requires `{"version": 1}`, and a file
without it is not read - which is the sort of thing that fails by the hook
simply never firing, so it is carried here rather than assumed.

#### *property* fragment *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

Where [`template`](#outrage.install.HookTarget.template) actually is, inside this installation.

A property rather than a field, so it stays out of the `repr` that
the generated reference renders.

#### path(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

Where this hook's file is in a project, whether or not it exists yet.

### *exception* outrage.install.InstallError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`ConfigError`](config.md#outrage.config.ConfigError)

Settings that cannot safely be updated.

### *class* outrage.install.Installation(project_dir: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), server: [Change](config.md#outrage.config.Change), hooks: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[HookChange](#outrage.install.HookChange), ...], assets: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...], codex_assets: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...], copilot_assets: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...], table: [Starter](mountfile.md#outrage.mountfile.Starter))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Everything `outrage init` does to a project, or would do.

#### project_dir *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

#### server *: [Change](config.md#outrage.config.Change)*

#### hooks *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[HookChange](#outrage.install.HookChange), ...]*

One per [`HOOK_TARGETS`](#outrage.install.HOOK_TARGETS), in that order.

#### assets *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...]*

Claude Code skills and agents.

#### codex_assets *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...]*

Codex skills.

#### copilot_assets *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...]*

Copilot CLI agents.

#### table *: [Starter](mountfile.md#outrage.mountfile.Starter)*

The project's mount table: written when there is none, never rewritten.

#### *property* writes *: [bool](https://docs.python.org/3/library/functions.html#bool)*

### outrage.install.asset_sources() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]]

Every packaged file to install, as a source and a path below `.claude`.

### outrage.install.codex_asset_sources() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]]

Every packaged Codex skill, as a source and path below `.codex`.

### outrage.install.copilot_asset_sources() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]]

Every packaged Copilot agent, as a source and path below `.github`.

### outrage.install.init(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, log: [Any](https://docs.python.org/3/library/typing.html#typing.Any) = None, log_content: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, no_info: [bool](https://docs.python.org/3/library/functions.html#bool) = False, no_remount: [bool](https://docs.python.org/3/library/functions.html#bool) = False, root_mount: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, mounts: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), read_only_mounts: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Installation](#outrage.install.Installation)

Set a project up: the MCP server entry, hooks, and packaged skills.

The whole of it is planned before any of it is written, so a refusal - a
settings file that does not parse, a `.mcp.json` that does not - stops
the run rather than leaving a project half arranged. The dry run stops
after the same planning the real run does, so it cannot preview something a
write would disagree with.

`outrage config` writes the server entry alone and this calls it rather than
repeating it, which is also why `log`, `log_content`, `no_info` and
`no_remount` are passed through. `root_mount` and the two mount lists no
longer reach the entry at all: a mount table lives in `mounts.toml`, and
they seed it - see [`outrage.mountfile.plan_starter()`](mountfile.md#outrage.mountfile.plan_starter), and note that a
table already there is reported and left alone rather than rewritten.

Passing them through was never enough on its own, and a real project lost
three mounts and its `--log` to a re-run of `outrage init` that was only
meant to install a hook: the flags default to nothing, so the entry was
rebuilt with nothing. [`outrage.config.merge_entry()`](config.md#outrage.config.merge_entry) is the actual fix
and it sits in `plan`, where both this and `outrage config` reach it.

### outrage.install.install(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, \*, target: [HookTarget](#outrage.install.HookTarget) = CLAUDE_HOOK) → [HookChange](#outrage.install.HookChange)

Install one packaged hook into a project, or say what would change.

The dry run calls the same `plan` the real run does, so it cannot preview
something different from what a write would produce.

### outrage.install.is_ours(entry: [Any](https://docs.python.org/3/library/typing.html#typing.Any)) → [bool](https://docs.python.org/3/library/functions.html#bool)

Whether this session-start entry is one outrage wrote.

The marker anywhere in the entry, because the harnesses put the command in
different places - `hooks[].command` for Claude Code and Codex, `bash`
and `powershell` for Copilot CLI - and a matcher that knows those shapes
has to be taught the next one. Codex arrived and needed nothing here, which
is the argument. Nothing but our own entry carries a string in this
namespace.

Compares [`MARKER_MATCH`](#outrage.install.MARKER_MATCH), not [`MARKER`](#outrage.install.MARKER). See the module docstring
on why neither the version nor the product name is part of it.

### outrage.install.plan(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), entry: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, target: [HookTarget](#outrage.install.HookTarget) = CLAUDE_HOOK) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[HookChange](#outrage.install.HookChange), [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)], [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]

Work out what installing would change, without writing.

Returns the change, the merged settings and the file's original text, so a
caller can preview and then write without reading twice - and so a dry run
goes through this same function rather than a second one that could
disagree with it.

### outrage.install.plan_assets(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[FileChange](#outrage.install.FileChange)]

Work out which packaged files a project is missing or has an older copy of.

### outrage.install.plan_codex_assets(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[FileChange](#outrage.install.FileChange)]

Work out which Codex skills a project is missing or has an older copy of.

### outrage.install.plan_copilot_assets(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[FileChange](#outrage.install.FileChange)]

Work out which Copilot agents a project is missing or has an older copy of.

### outrage.install.settings_path(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

Where a project's Claude Code settings file is, existing or not.

### outrage.install.sessionstart_command(executable: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, copilot: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [str](https://docs.python.org/3/library/stdtypes.html#str)

Build the shell command installed for the shared SessionStart payload.

The absolute interpreter is the one running `outrage init`. `shlex`
quotes it for POSIX shells and `list2cmdline` for Windows; neither has to
quote JSON because [`sessionstart_payload()`](#outrage.install.sessionstart_payload) creates that at runtime.
Windows paths use forward slashes, which Windows accepts and JSON can carry
without another layer of backslash escaping.
The marker is a real argument understood by the private CLI wiring, not a
shell comment, so it survives either command language without reaching
stdout.

### outrage.install.sessionstart_payload(\*, copilot: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]

Read the shipped prompt and wrap it in one harness's hook payload.

### outrage.install.template_entry(target: [HookTarget](#outrage.install.HookTarget) = CLAUDE_HOOK) → [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]

The entry to install, read from the packaged template.

Every harness carries a placeholder rendered with the absolute interpreter
and managed marker at init time. Copilot receives the same command with a
flag selecting its flat payload. The marker is present before the entry is
accepted, so a broken template cannot silently become one a later run
fails to recognise.

### outrage.install.write_assets(changes: [list](https://docs.python.org/3/library/stdtypes.html#list)[[FileChange](#outrage.install.FileChange)]) → [None](https://docs.python.org/3/library/constants.html#None)

Copy across the files that differ, atomically and one at a time.
