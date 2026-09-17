# outrage.install

Setting a project up: the MCP entries, hooks, and harness-specific skills.

`init` is the whole of `outrage init` and the three parts are separable: the
server entries - `.mcp.json`, `.codex/config.toml` for Codex and
`.cursor/mcp.json` for Cursor, neither of which reads the first - are
[`outrage.config`](config.md#module-outrage.config)'s and are called rather
than repeated, the
session-start hooks are written here, and packaged assets are copied into the
directories their harness reads. Most of what follows is about the hooks,
because they are the part with something to say.

A config file belongs to the user, not to outrage. It holds their model, their
permissions and their own hooks, so this writes the one entry it owns and
leaves everything else exactly as it found it - the rule [`outrage.config`](config.md#module-outrage.config)
already follows for `.mcp.json`, and the reason its `read_config` and
`write_config` are reused here rather than reimplemented.

## Four harnesses, one hook each

[`HOOK_TARGETS`](#outrage.install.HOOK_TARGETS) is the list, and everything below takes one of them rather
than assuming Claude Code. Adding the second one is what turned the constants
into a [`HookTarget`](#outrage.install.HookTarget), on the rule that nothing is generalised before
there is a second real case to generalise *to*, and Copilot CLI was it. Codex,
added third, cost a template and a constant and no change to any function here
- which is the shape working.

Cursor, added fourth, cost one more field. Its file is `.cursor/hooks.json`,
Copilot's shape down to the `"version": 1` stamp and the lower-case
`sessionStart`, and its entry is a single `command` string like Codex's.
What it does not share with either is the **payload**, and that is the field:
Cursor reads back `additional_context` where Copilot reads
`additionalContext`, the same word in a different case convention. One
character of difference that delivers nothing at all if it is wrong, which is
why [`HookTarget.context_field`](#outrage.install.HookTarget.context_field) spells it out per harness rather than
letting a boolean mean "the flat one".

Cursor's packaged *assets* are still nothing: its project instructions are
`.cursor/rules` and `.cursor/commands`, and there is no packaged equivalent
of either here, so [`write_assets()`](#outrage.install.write_assets) has nothing to copy there.

Cursor's `matcher` is documented as optional for every event, so unlike the
Codex one it is left out. That is the same rule as Codex's, not a departure
from it: ship what the documentation establishes. For Codex requiredness was
*not* established and the example carried one, so the example won.

They differ in more than spelling:

* **Claude Code** merges into `.claude/settings.json`, a file the user owns
  outright and which this project does not commit.
* **Copilot CLI** takes a file per purpose under `.github/hooks/`, so
  `.github/hooks/outrage.json` is outrage's own, and repository agents under
  `.github/agents/`. `.github` is usually **committed**, so a re-run's diff
  lands in somebody's version control where the Claude one does not.
* Copilot's packaged template carries both `bash` and `powershell` forms,
  but the installed entry keeps only the form for the current platform. The
  file also needs `"version": 1` at its top. Hence [`HookTarget.base`](#outrage.install.HookTarget.base):
  what to start from when the file does not exist.
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
flat `additionalContext` payload rather than Claude and Codex's nested one,
and Cursor's carries `--cursor` for its `additional_context`. Both flags
stay accepted for as long as an entry written by an older release might still
be installed: the hook file is only rewritten by `outrage init`, so upgrading
the package does not upgrade the command line already recorded in it.
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

All four hooks now run `<python> -m outrage sessionstart`.
The interpreter is the absolute [`sys.executable`](https://docs.python.org/3/library/sys.html#sys.executable) of the environment that
ran `outrage init`, for the same reason the MCP entry names that environment:
a hook does not inherit an activated environment. The managed marker is an
ordinary final argument rather than a shell comment, so neither it nor the
command depends on `#` meaning the same thing on every platform.

Copilot CLI remains different only at the boundary: its hook contract selects
one of `bash` and `powershell` according to the platform, and its output is
the documented flat payload. The command reads the same shipped prompt at
invocation time and selects that shape with `--copilot`. Cursor takes one
command string for every platform, as Codex does, and differs only in the
payload key.

## The packaged files have no identity, so there is a receipt

A hook entry and a server table can be recognised: one carries a marker, the
other a name. A copied markdown file carries nothing at all, so the only
evidence about it is its bytes -- and bytes cannot answer the question that
matters, which is whether a file differing from the packaged copy was *edited*
or is simply an **older release's** copy that nobody has touched. The second is
the common one: it happens to every project on any upgrade that changed a
shipped file.

That was affordable while the answer was "overwrite it anyway". It stops being
affordable once a difference refuses, because then every upgrade refuses.

[`InstallRecord`](#outrage.install.InstallRecord) is what separates the two. `init` writes one manifest
per harness directory, holding a hash of each file as it wrote it, and a later
run compares three things rather than two: what is on disk, what this release
packages, and what outrage recorded putting there. A file that matches the
record but not the package is an upgrade and is replaced in silence; one that
matches neither was edited, and both `init` and `uninit` refuse over it.

The rules are [`outrage.bulk.ExportRecord`](bulk.md#outrage.bulk.ExportRecord)'s, which answers the same
question about an exported document: a file rather than a name or a table in a
process, unknown fields ignored on read so a later writer can record more, and
**a missing record degrades to not making the check** rather than to making it
wrongly. The last is what makes the first run after an upgrade possible at all:
no project in existence has a manifest, so `init` adopts -- it does what it
did before, and records what it wrote, so the check begins one run later.

There is deliberately no timestamp and no version string in it. One harness
directory is usually committed, so a field that changes on every run is a diff
in somebody's history for nothing; what is worth recording is what changes only
when the files do.

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

### outrage.install.CURSOR_DIR *= '.cursor'*

Where Cursor reads its project hook. The server entry lives here too, as
`mcp.json`; [`outrage.config.CURSOR_CONFIG_NAME`](config.md#outrage.config.CURSOR_CONFIG_NAME) is that one.

### outrage.install.GITHUB_DIR *= '.github'*

Where Copilot CLI reads its repository hook and preferred agent definitions.

### outrage.install.CLAUDE_HOOK *= HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}, context_field=None, payload_flag=None)*

Claude Code: merged into the user's own settings file.

### outrage.install.CODEX_HOOK *= HookTarget(name='Codex', template=PosixPath('codex.json'), relative=PosixPath('.codex/hooks.json'), event='SessionStart', base={}, context_field=None, payload_flag=None)*

Codex: its own file, like Copilot CLI, but the entry is Claude Code's shape
- `SessionStart`, a nested `hooks` list, and the same
`hookSpecificOutput` payload. The one thing neither of the others has is
the `matcher`; see the module docstring on why it is written as documented
rather than left out.

### outrage.install.COPILOT_HOOK *= HookTarget(name='Copilot CLI', template=PosixPath('copilot.json'), relative=PosixPath('.github/hooks/outrage.json'), event='sessionStart', base={'version': 1}, context_field='additionalContext', payload_flag='--copilot')*

Copilot CLI: a file per purpose, so this one is outrage's own. Named for the
package rather than the event, so a second outrage hook joins it here rather
than claiming a second file.

### outrage.install.CURSOR_HOOK *= HookTarget(name='Cursor', template=PosixPath('cursor.json'), relative=PosixPath('.cursor/hooks.json'), event='sessionStart', base={'version': 1}, context_field='additional_context', payload_flag='--cursor')*

Cursor: its own file again, Copilot's `"version": 1` stamp and lower-case
`sessionStart`, and Codex's single `command` string. The one thing it
shares with neither is the payload key. `matcher` is documented as
optional here, so it is left out; see the module docstring on why Codex's is
written even so.

### outrage.install.HOOKS_FIELD *= 'hooks'*

The key below which that merge happens. Everything else in the file is
somebody else's and is written back as it was found.

### outrage.install.HOOK_TARGETS *= (HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}, context_field=None, payload_flag=None), HookTarget(name='Copilot CLI', template=PosixPath('copilot.json'), relative=PosixPath('.github/hooks/outrage.json'), event='sessionStart', base={'version': 1}, context_field='additionalContext', payload_flag='--copilot'), HookTarget(name='Codex', template=PosixPath('codex.json'), relative=PosixPath('.codex/hooks.json'), event='SessionStart', base={}, context_field=None, payload_flag=None), HookTarget(name='Cursor', template=PosixPath('cursor.json'), relative=PosixPath('.cursor/hooks.json'), event='sessionStart', base={'version': 1}, context_field='additional_context', payload_flag='--cursor'))*

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

### *class* outrage.install.Edit(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), document: [Any](https://docs.python.org/3/library/typing.html#typing.Any) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, original: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, toml: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False, delete: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One file a removal will write or delete, decided and ready to apply.

The plan carries these so that applying it needs nothing but the plan --
see [`apply_uninit()`](#outrage.install.apply_uninit) on why that matters.

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

#### document *: [Any](https://docs.python.org/3/library/typing.html#typing.Any) | [None](https://docs.python.org/3/builtins/constants.html#None)*

The whole file as it will be left, or None where it is being deleted.

#### original *: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)*

The file's text as it was read, so its layout can be preserved.

#### toml *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

#### delete *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

### *class* outrage.install.FileChange(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), source: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), action: [str](https://docs.python.org/3/builtins/stdtypes.html#str), relative: [str](https://docs.python.org/3/builtins/stdtypes.html#str) = '')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

What installing or removing one packaged file would do, or did.

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

#### source *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

#### action *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

What comparing the file with the packaged copy found, which each command
reads for itself:

`created`
: Not there. `init` writes it; a removal has nothing to do.

`unchanged`
: Byte for byte the packaged copy.

`updated`
: Different, and the receipt says outrage wrote what is there -- so an
  **earlier release's** copy, which nobody has touched.

`edited`
: Different, and the receipt says outrage wrote something else. Somebody
  edited it, and both commands refuse rather than destroy it.

`unrecorded`
: Different, with no receipt covering it, so which of the two it is
  cannot be told. `init` does what it did before receipts existed;
  a removal refuses.

`linked`
: Reached through a symlink, and left alone by everything.

#### relative *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

Where the file is below its harness directory, in POSIX spelling, which
is how a receipt names it.

#### *property* writes *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

Whether `init` writes this one without being forced.

#### *property* refuses *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

Whether this one stops a run that was not forced.

#### describe() → [str](https://docs.python.org/3/builtins/stdtypes.html#str)

### *class* outrage.install.HookChange(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), action: [str](https://docs.python.org/3/builtins/stdtypes.html#str), entry: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)], previous: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/builtins/constants.html#None), duplicates: [int](https://docs.python.org/3/builtins/functions.html#int) = 0, target: [HookTarget](#outrage.install.HookTarget) = HookTarget(name='Claude Code', template=PosixPath('settings.json'), relative=PosixPath('.claude/settings.json'), event='SessionStart', base={}, context_field=None, payload_flag=None), refusals: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Refusal](errors.md#outrage.errors.Refusal), ...] = ())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

What installing or removing the hook would do, or did.

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

#### action *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

`created`, `updated` or `unchanged` when the entry is being
written, and `removed`, `absent` or `refused` when it is being taken
away.

#### entry *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*

#### previous *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/builtins/constants.html#None)*

The entry being replaced or removed, when there was one.

#### duplicates *: [int](https://docs.python.org/3/builtins/functions.html#int)*

Extra entries of ours removed, from a run that could not identify them.

#### target *: [HookTarget](#outrage.install.HookTarget)*

Which harness's hook this is, so a report over several can name them.

#### refusals *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Refusal](errors.md#outrage.errors.Refusal), ...]*

Why this hook will not be touched, when something stopped it.

**Never about the entry's content.** An installer replaces its own hook
entry whole, so nothing a person writes inside one survives the next
`init` anyway and a removal destroys nothing that was not already
forfeit. What does land here is a settings file that cannot be read.

#### *property* writes *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

#### describe() → [str](https://docs.python.org/3/builtins/stdtypes.html#str)

### *class* outrage.install.HookTarget(name: [str](https://docs.python.org/3/builtins/stdtypes.html#str), template: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), relative: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), event: [str](https://docs.python.org/3/builtins/stdtypes.html#str), base: dict[str, ~typing.Any]=<factory>, context_field: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, payload_flag: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One harness's session-start hook: where it goes and what shape it is.

Everything harness-specific about the hook is one of these fields, so
supporting a third client is a fourth instance rather than a branch in the
code below. What is *not* here is deliberate: the merge rule, the marker
and the refusal to touch what it did not write are the same everywhere.

#### name *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

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

#### event *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

The key below `hooks` this harness fires at session start.

#### base *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*

What a newly created file starts from, before the entry is merged in.

Empty for Claude Code. Copilot CLI and Cursor both require
`{"version": 1}`, and a file without it is not read - which is the sort of
thing that fails by the hook simply never firing, so it is carried here
rather than assumed.

#### context_field *: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)*

The key this harness reads the prompt back under, or None for the nested
Claude Code shape that Codex shares.

A string rather than a flag because the two flat harnesses do not agree:
Copilot CLI reads `additionalContext` and Cursor `additional_context`.
Nothing reports a payload under the wrong key - the session simply starts
without the context - so the exact spelling is worth stating per harness.

#### payload_flag *: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)*

The private `outrage sessionstart` flag that selects [`context_field`](#outrage.install.HookTarget.context_field).

None where the nested shape is the default and no flag is needed. It is
part of the installed command, so a flag here can be **added** but not
renamed or removed: an entry written by an older release keeps running the
command it recorded until `outrage init` rewrites the file.

#### *property* fragment *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

Where [`template`](#outrage.install.HookTarget.template) actually is, inside this installation.

A property rather than a field, so it stays out of the `repr` that
the generated reference renders.

#### path(project_dir: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

Where this hook's file is in a project, whether or not it exists yet.

### *exception* outrage.install.InstallError(code: [str](https://docs.python.org/3/builtins/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`ConfigError`](config.md#outrage.config.ConfigError)

Settings that cannot safely be updated.

### *class* outrage.install.InstallRecord(files: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)], version: [int](https://docs.python.org/3/builtins/functions.html#int) = 1)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

What `init` last wrote into one harness directory, as it recorded it.

The only evidence that separates a packaged file somebody edited from one
an earlier release wrote. See the module docstring for why bytes alone
cannot, and [`outrage.bulk.ExportRecord`](bulk.md#outrage.bulk.ExportRecord) for the shape this follows.

#### files *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)]*

Each installed file, by its path below the harness directory in POSIX
spelling, to the hash of what was written there. POSIX because one of these
directories is committed and read on whatever platform checks it out.

#### version *: [int](https://docs.python.org/3/builtins/functions.html#int)*

#### *static* path_for(root: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

Where the receipt for the directory at `root` is kept.

#### *classmethod* read(root: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [InstallRecord](#outrage.install.InstallRecord) | [None](https://docs.python.org/3/builtins/constants.html#None)

The receipt in `root`, or None if there is not a readable one.

None for every way it can be absent -- not there, not JSON, not an
object, holding no usable file table -- because the caller's fallback
is to make no claim about what it finds, which is exactly right for a
directory outrage has never recorded writing to.

#### *classmethod* of(changes: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[FileChange](#outrage.install.FileChange)]) → [InstallRecord](#outrage.install.InstallRecord)

The receipt for a directory these changes have just been applied to.

The packaged bytes, because that is what is on disk once every change
that writes has been written and every change that did not write was
already equal to them. A symlinked path is left out: its content is not
outrage's to claim, and nothing wrote it.

#### matches(relative: [str](https://docs.python.org/3/builtins/stdtypes.html#str), content: [bytes](store.md#outrage.store.Backup.bytes)) → [bool](https://docs.python.org/3/builtins/functions.html#bool)

Whether `content` is what this receipt says was written at `relative`.

#### write(root: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [bool](https://docs.python.org/3/builtins/functions.html#bool)

Write this receipt into `root`, and say whether anything changed.

False when the directory already holds exactly this, so a re-run leaves
no diff behind in a harness directory somebody commits.

### *class* outrage.install.Installation(project_dir: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), server: [Change](config.md#outrage.config.Change), codex_server: [Change](config.md#outrage.config.Change), cursor_server: [Change](config.md#outrage.config.Change), hooks: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[HookChange](#outrage.install.HookChange), ...], assets: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...], codex_assets: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...], copilot_assets: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...], table: [Starter](mountfile.md#outrage.mountfile.Starter), refusals: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Refusal](errors.md#outrage.errors.Refusal), ...] = ())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Everything `outrage init` does to a project, or would do.

#### project_dir *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

#### server *: [Change](config.md#outrage.config.Change)*

#### codex_server *: [Change](config.md#outrage.config.Change)*

The same server in `.codex/config.toml`, which is where Codex reads it.

#### cursor_server *: [Change](config.md#outrage.config.Change)*

The same server again in `.cursor/mcp.json`, for Cursor. Its hook is in
[`hooks`](#outrage.install.Installation.hooks) with the rest; what it has none of is packaged assets.

#### hooks *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[HookChange](#outrage.install.HookChange), ...]*

One per [`HOOK_TARGETS`](#outrage.install.HOOK_TARGETS), in that order.

#### assets *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...]*

Claude Code skills and agents.

#### codex_assets *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...]*

Codex skills.

#### copilot_assets *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...]*

Copilot CLI agents.

#### table *: [Starter](mountfile.md#outrage.mountfile.Starter)*

The project's mount table: written when there is none, never rewritten.

#### refusals *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Refusal](errors.md#outrage.errors.Refusal), ...]*

Every reason this installation will not proceed, not merely the first.

Empty on an ordinary run. What lands here is a packaged file somebody
edited, which is the one thing `init` declines to overwrite -- and every
one of them, so a person is told the whole of what is in the way and
decides once.

#### *property* writes *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

### outrage.install.RECORD_NAME *= '.outrage.json'*

What `init` writes beside the files it copied, in each harness directory,
recording what it put there. Named for the suffix the export record already
uses, because it is the same mechanism answering the same question.

### outrage.install.RECORD_VERSION *= 1*

The manifest format. Bumped only by a change an older reader cannot survive;
an added field is not one, since unknown fields are ignored on read.

### *class* outrage.install.Uninstallation(project_dir: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), forced: [bool](https://docs.python.org/3/builtins/functions.html#bool), server: [Change](config.md#outrage.config.Change), codex_server: [Change](config.md#outrage.config.Change), cursor_server: [Change](config.md#outrage.config.Change), hooks: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[HookChange](#outrage.install.HookChange), ...], assets: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...], codex_assets: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...], copilot_assets: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...], receipts: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), ...], file_refusals: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Refusal](errors.md#outrage.errors.Refusal), ...] = (), edits: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Edit](#outrage.install.Edit), ...] = ())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Everything `outrage uninit` would take out of a project, and why not.

Produced whole before anything is written, and applied from itself, so
nothing can be done that the report did not describe.

#### project_dir *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

#### forced *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

#### server *: [Change](config.md#outrage.config.Change)*

#### codex_server *: [Change](config.md#outrage.config.Change)*

#### cursor_server *: [Change](config.md#outrage.config.Change)*

#### hooks *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[HookChange](#outrage.install.HookChange), ...]*

#### assets *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...]*

#### codex_assets *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...]*

#### copilot_assets *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[FileChange](#outrage.install.FileChange), ...]*

#### receipts *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), ...]*

The install receipts to delete. Outrage's own bookkeeping rather than
configuration, and one left behind would claim files that are gone.

#### file_refusals *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Refusal](errors.md#outrage.errors.Refusal), ...]*

#### edits *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Edit](#outrage.install.Edit), ...]*

#### *property* refusals *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Refusal](errors.md#outrage.errors.Refusal), ...]*

Every reason found, over the whole project, in the order reported.

#### *property* blocking *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Refusal](errors.md#outrage.errors.Refusal), ...]*

The refusals that still stand, which under force is those no flag reaches.

#### *property* writes *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

### outrage.install.apply_uninit(plan: [Uninstallation](#outrage.install.Uninstallation)) → [None](https://docs.python.org/3/builtins/constants.html#None)

Carry out a plan [`plan_uninit()`](#outrage.install.plan_uninit) produced.

**Takes the plan, not the project.** Nothing here looks at the project
again, so there is no second derivation that could reach a different answer
from the one already reported -- which is what makes the two passes a
property of the code rather than a convention that holds until somebody
adds a third caller.

Applying a plan that still has [`Uninstallation.blocking`](#outrage.install.Uninstallation.blocking) refusals is
the caller's mistake to avoid; this does what it was given.

### outrage.install.asset_refusals(changes: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[FileChange](#outrage.install.FileChange)]) → [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[Refusal](errors.md#outrage.errors.Refusal)]

Every packaged file somebody edited, as refusals, one per file.

Overridable: the content is real and a caller may knowingly discard it.

### outrage.install.asset_sources() → [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]]

Every packaged file to install, as a source and a path below `.claude`.

### outrage.install.codex_asset_sources() → [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]]

Every packaged Codex skill, as a source and path below `.codex`.

### outrage.install.copilot_asset_sources() → [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]]

Every packaged Copilot agent, as a source and path below `.github`.

### outrage.install.init(project_dir: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), directory: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, \*, log: [Any](https://docs.python.org/3/library/typing.html#typing.Any) = None, log_content: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, no_info: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False, no_remount: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False, no_versioning: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False, root_mount: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, mounts: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] = (), read_only_mounts: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] = (), dry_run: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False, force: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False) → [Installation](#outrage.install.Installation)

Set a project up: the MCP server entries, hooks, and packaged skills.

The server entry is written three times, to `.mcp.json`, to Codex's
`.codex/config.toml` and to Cursor's `.cursor/mcp.json`, from the same
options; the Codex one carries a marker, [`outrage.config.plan_codex()`](config.md#outrage.config.plan_codex)
says why, and the Cursor one carries a `type`,
[`outrage.config.cursor_entry()`](config.md#outrage.config.cursor_entry) says why. The hooks are one per
[`HOOK_TARGETS`](#outrage.install.HOOK_TARGETS), which is all four harnesses.

The whole of it is planned before any of it is written, so a refusal - a
settings file that does not parse, a `.mcp.json` that does not - stops
the run rather than leaving a project half arranged. The dry run stops
after the same planning the real run does, so it cannot preview something a
write would disagree with.

`outrage config` writes the server entry alone and this calls it rather than
repeating it, which is also why `log`, `log_content`, `no_info`,
`no_remount` and `no_versioning` are passed through. `root_mount` and
the two mount lists no longer reach the entry at all: a mount table lives in
`mounts.toml`, and they seed it - see [`outrage.mountfile.plan_starter()`](mountfile.md#outrage.mountfile.plan_starter), and note that a
table already there is reported and left alone rather than rewritten.

Passing them through was never enough on its own, and a real project lost
three mounts and its `--log` to a re-run of `outrage init` that was only
meant to install a hook: the flags default to nothing, so the entry was
rebuilt with nothing. [`outrage.config.merge_entry()`](config.md#outrage.config.merge_entry) is the actual fix
and it sits in `plan`, where both this and `outrage config` reach it.

**A packaged file somebody edited stops the run**, and `force` is what
replaces it anyway. Every such file is reported, not the first, which is
why they are collected as [`outrage.errors.Refusal`](errors.md#outrage.errors.Refusal) values rather
than raised: the whole of what is in the way should reach a person in one
go. Refusing is only affordable because a receipt can tell an edit from an
older release's copy -- [`InstallRecord`](#outrage.install.InstallRecord), and the module docstring on
what happens where there is no receipt yet.

### outrage.install.install(project_dir: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), dry_run: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False, \*, target: [HookTarget](#outrage.install.HookTarget) = CLAUDE_HOOK) → [HookChange](#outrage.install.HookChange)

Install one packaged hook into a project, or say what would change.

The dry run calls the same `plan` the real run does, so it cannot preview
something different from what a write would produce.

### outrage.install.is_ours(entry: [Any](https://docs.python.org/3/library/typing.html#typing.Any)) → [bool](https://docs.python.org/3/builtins/functions.html#bool)

Whether this session-start entry is one outrage wrote.

The marker anywhere in the entry, because the harnesses put the command in
different places - `hooks[].command` for Claude Code and Codex, `bash`
and `powershell` for Copilot CLI - and a matcher that knows those shapes
has to be taught the next one. Codex arrived and needed nothing here, which
is the argument. Nothing but our own entry carries a string in this
namespace.

Compares [`MARKER_MATCH`](#outrage.install.MARKER_MATCH), not [`MARKER`](#outrage.install.MARKER). See the module docstring
on why neither the version nor the product name is part of it.

### outrage.install.plan(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), entry: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, \*, target: [HookTarget](#outrage.install.HookTarget) = CLAUDE_HOOK) → [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[HookChange](#outrage.install.HookChange), [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)], [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)]

Work out what installing would change, without writing.

Returns the change, the merged settings and the file's original text, so a
caller can preview and then write without reading twice - and so a dry run
goes through this same function rather than a second one that could
disagree with it.

### outrage.install.plan_assets(project_dir: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[FileChange](#outrage.install.FileChange)]

Work out which packaged files a project is missing or has an older copy of.

### outrage.install.plan_hook_removal(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), \*, target: [HookTarget](#outrage.install.HookTarget) = CLAUDE_HOOK) → [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[HookChange](#outrage.install.HookChange), [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/builtins/constants.html#None), [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)]

Work out what taking our session-start entry out of `path` would change.

Returns what [`plan()`](#outrage.install.plan) returns, with `None` in place of the settings
when there is nothing to write.

**Every entry the marker matches goes**, not merely the first: a run that
once failed to recognise its own entry can have left more than one, and
leaving the extras behind would leave the hook firing.

Nothing here raises. A settings file that will not parse is recorded as a
refusal instead, so a caller taking four hooks out at once reports all four
answers rather than the first failure.

The event's list is left in place when the last entry leaves it. An empty
list fires nothing, and the file belongs to whoever else writes in it.

### outrage.install.plan_codex_assets(project_dir: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[FileChange](#outrage.install.FileChange)]

Work out which Codex skills a project is missing or has an older copy of.

### outrage.install.plan_copilot_assets(project_dir: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[FileChange](#outrage.install.FileChange)]

Work out which Copilot agents a project is missing or has an older copy of.

### outrage.install.plan_uninit(project_dir: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), \*, force: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False) → [Uninstallation](#outrage.install.Uninstallation)

Work out everything removing outrage from a project would do.

**Never writes and never raises.** A file that cannot be read becomes a
refusal like any other, because the point of planning the whole project
first is to report every reason at once: a caller who fixes one thing,
runs again and meets the next has been sent round a loop this could have
spared them.

`force` is applied here, to the plan, rather than at the moment of
writing. A refusal every reason for which is overridable becomes an
ordinary removal and the reasons stay on it, so the report can say what was
overridden; one that no flag reaches stays refused whatever was asked for.

### outrage.install.removal_action(change: [FileChange](#outrage.install.FileChange), \*, forced: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False) → [str](https://docs.python.org/3/builtins/stdtypes.html#str)

What removing one packaged file does, read off the shared comparison.

The comparison is `_plan_files()`' and says what the file *is*; this
says what a removal makes of that, which is not the same reading the
installer takes. An earlier release's copy is still outrage's to delete;
a file nobody can account for is not.

### outrage.install.removal_refusals(changes: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[FileChange](#outrage.install.FileChange)]) → [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[Refusal](errors.md#outrage.errors.Refusal)]

The same, for a removal, which refuses over one more case.

A file with no receipt covering it might be an earlier release's copy or
might be somebody's work, and deleting it is not reversible either way.
`init` overwrites such a file because that is what it has always done and
a refusal there would block the very upgrade that starts recording them;
deleting one on the same evidence would be a different bet entirely.

### outrage.install.settings_path(project_dir: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

Where a project's Claude Code settings file is, existing or not.

### outrage.install.uninit(project_dir: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), \*, dry_run: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False, force: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False) → [Uninstallation](#outrage.install.Uninstallation)

Remove outrage's integration from a project, or say what removing it would do.

Takes out the server entries, the session-start hooks, the packaged skills
and agents, and the receipts recording them. **Leaves every file and
directory standing**: an empty servers object and an empty hook list
trigger nothing, and pruning a container risks removing a key the harness
needs. The store directory is not touched at all -- this removes an
integration, not anybody's documents.

**Nothing at all is written when anything still refuses**, force or no
force, which is the same all-or-nothing the installer has and for the same
reason: a project left half arranged is a worse state than one left alone,
and here it would be one where some of outrage still starts. A refusal no
flag reaches -- a file that cannot be read -- therefore stops the whole
removal, and the remedy is to repair or delete that file and run again.
See [`plan_uninit()`](#outrage.install.plan_uninit).

### outrage.install.sessionstart_command(executable: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, \*, target: [HookTarget](#outrage.install.HookTarget) = CLAUDE_HOOK) → [str](https://docs.python.org/3/builtins/stdtypes.html#str)

Build the shell command installed for `target`'s SessionStart payload.

The absolute interpreter is the one running `outrage init`. `shlex`
quotes it for POSIX shells and `list2cmdline` for Windows; neither has to
quote JSON because [`sessionstart_payload()`](#outrage.install.sessionstart_payload) creates that at runtime.
Windows paths use forward slashes, which Windows accepts and JSON can carry
without another layer of backslash escaping.
The marker is a real argument understood by the private CLI wiring, not a
shell comment, so it survives either command language without reaching
stdout.

The only thing `target` changes is whether a payload flag is appended,
which is [`HookTarget.payload_flag`](#outrage.install.HookTarget.payload_flag).

### outrage.install.sessionstart_payload(\*, target: [HookTarget](#outrage.install.HookTarget) = CLAUDE_HOOK) → [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]

Read the shipped prompt and wrap it in `target`'s hook payload.

Two shapes, and which one is not a property of this function: a harness
with a [`HookTarget.context_field`](#outrage.install.HookTarget.context_field) reads the prompt back under that
key alone, and one without it takes Claude Code's nested envelope, which
Codex shares down to the event name.

### outrage.install.template_entry(target: [HookTarget](#outrage.install.HookTarget) = CLAUDE_HOOK) → [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]

The entry to install, read from the packaged template.

Every harness carries a placeholder rendered with the absolute interpreter
and managed marker at init time. Copilot and Cursor receive the same
command with a flag selecting their own flat payload key. The marker is
present before the entry is accepted, so a broken template cannot silently
become one a later run fails to recognise.

### outrage.install.write_assets(changes: [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[FileChange](#outrage.install.FileChange)], \*, force: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False) → [None](https://docs.python.org/3/builtins/constants.html#None)

Copy across the files that differ, atomically and one at a time.

`force` also replaces a file somebody edited, which is otherwise the one
thing this declines to do.
