# outrage.config

Writing the MCP server configuration for a project or a user.

Separate from [`outrage.cli`](cli.md#module-outrage.cli) for the same reason the store is separate from
the server: the CLI should shape arguments and print, nothing else. Everything
here is callable and testable without going through argparse.

The problem this solves is that an MCP client launches the server as a
subprocess, so it needs an absolute path to an entry point inside whichever
environment outrage was installed in. That path is only reliably known from
inside that environment - which is where this code runs, and is why writing
the configuration is a command rather than something a user does by hand. The
`.mcp.json` originally written by hand in this repository is the illustration:
it names one machine's conda prefix and is wrong everywhere else.

### outrage.config.CLI_SCRIPT_NAME *= 'outrage'*

Console script for the command line, the other half of the pair. A caller
told which environment this server runs in wants it to run `outrage` there,
and there is no module fallback for this one: `python -m outrage` is the
*server*, so an installation without the script has no second spelling.

### outrage.config.PROJECT_CONFIG_NAME *= '.mcp.json'*

Project scoped configuration, committed with the project and read by clients
from the project root.

### outrage.config.SCOPES *= ('project', 'user')*

Where a configuration may be written, and the order of preference: the
project it is for, or the user who runs it.

### outrage.config.SCRIPT_NAME *= 'outrage-server'*

Console script installed by this package, and the fallback for when it is
absent. `python -m outrage` is equivalent, and works in an environment the
scripts directory of which is not where sys.executable lives.

### outrage.config.SERVERS_FIELD *= 'mcpServers'*

The key holding the servers, in both configuration files. The rest of
either file belongs to somebody else and is written back untouched.

### outrage.config.SERVER_NAME *= 'outrage'*

The name this server is registered under. Also the key that a re-run
replaces, which is what keeps unrelated servers in the file untouched.

### outrage.config.USER_CONFIG_NAME *= '.claude.json'*

User scoped configuration, in the home directory. Holds a great deal besides
MCP servers, which is why nothing here rewrites more of it than one key.

### *class* outrage.config.Change(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), scope: [str](https://docs.python.org/3/library/stdtypes.html#str), name: [str](https://docs.python.org/3/library/stdtypes.html#str), action: [str](https://docs.python.org/3/library/stdtypes.html#str), entry: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)], previous: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

What writing the configuration would do, or did.

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

#### scope *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### name *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### action *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

'created', 'updated' or 'unchanged'.

#### entry *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*

#### previous *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None)*

The entry being replaced, when there was one.

#### *property* writes *: [bool](https://docs.python.org/3/library/functions.html#bool)*

### *exception* outrage.config.ConfigError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`RuntimeError`](https://docs.python.org/3/library/exceptions.html#RuntimeError)

Raised when existing configuration cannot be safely updated.

### outrage.config.config_path(scope: [str](https://docs.python.org/3/library/stdtypes.html#str), project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

Locate the configuration file for `scope`.

### outrage.config.default_store_dir(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

Where the store goes when the caller does not say.

### outrage.config.launch_command(executable: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

Build the absolute command that starts the server.

Prefers the console script beside the running interpreter, because it is
what an install provides and it names the environment unambiguously. Falls
back to `<python> -m outrage`, which is equivalent and cannot be missing: it
needs only the interpreter that is already running and the package that is
already imported.

### outrage.config.merge_entry(previous: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None), entry: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]) → [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]

Fold `entry` onto the entry already in the file, keeping what it omits.

An `outrage init` that is only asked to set a project up should not be
able to switch off logging somebody turned on, or drop the mounts they
configured - and before this it did exactly that, because
[`server_entry()`](#outrage.config.server_entry) builds an argument list from what the caller passed
and nothing else. A re-run with no flags therefore wrote an entry with no
mounts.

It is also what keeps an entry written before the mount table moved into
`mounts.toml` working: `server_entry` no longer builds a `--mount`,
so the ones already in the file are inherited by every re-run rather than
quietly dropped.

So: **an option the new entry does not mention is inherited from the old
one.** Options it does mention replace the old ones outright, all of them
at once, so a re-run naming one `--mount` does not accumulate the
previous three beside it. `command` always comes from the new entry -
the absolute path into this environment is the one thing `outrage config`
exists to correct.

The consequence to know: **an option cannot be removed by leaving it out.**
Dropping a mount is an edit to the file. That is the right way round for a
command a user runs to repair a project rather than to redefine it, and
losing configuration silently is the failure that was actually reported.

### outrage.config.mounts_in(args: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

The mount options an existing server entry still carries, if any.

Nothing migrates these: an entry that names mounts goes on working, and
they win over `mounts.toml` because the command line comes after the
file. But an entry and a file both describing a table, with only one of
them the place anybody thinks to look, is worth a sentence - so this is
what `outrage config` reports.

### outrage.config.plan(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), scope: [str](https://docs.python.org/3/library/stdtypes.html#str), entry: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)], name: [str](https://docs.python.org/3/library/stdtypes.html#str) = SERVER_NAME) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Change](#outrage.config.Change), [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)], [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]

Work out what writing `entry` into `path` would change.

Returns the change, the merged configuration, and the file's original text,
so a caller can report before writing and write without reading twice.

### outrage.config.read_config(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)], [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]

Read a configuration file, returning its content and original text.

A file that exists but does not parse is an error rather than something to
overwrite. The user scoped file in particular holds a great deal of
unrelated state, and replacing it wholesale because one read failed would
do far more damage than declining to write.

### outrage.config.script_command(script: [str](https://docs.python.org/3/library/stdtypes.html#str), executable: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None)

The absolute command running `script` beside the given interpreter, or None.

A console script names the environment unambiguously, which is the whole
reason a path is reported rather than a bare name: a caller elsewhere runs
*this* installation rather than whatever the same word resolves to on their
PATH.

None rather than a guess when it is not there. Which fallback is right is a
property of the script -- the server has one and the command line has none
-- so the caller who knows that decides, and a report that cannot name a
command says so.

### outrage.config.server_entry(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], command: [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, log: [Any](https://docs.python.org/3/library/typing.html#typing.Any) = None, log_content: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, no_info: [bool](https://docs.python.org/3/library/functions.html#bool) = False, no_remount: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]

Build the configuration entry for the stores in `directory`.

**One absolute path in the whole entry**, and it is the directory. A client
cannot be relied on to launch the server in the project working directory,
so a relative `--dir` would resolve against somewhere unpredictable and
quietly produce a second, empty store rather than an error. Everything else
is named relative to it, which is what lets a project be moved or checked
out elsewhere with only that one line to fix.

`log` adds `--log`: a path, or the `eventlog.DEFAULT` sentinel for the
file beside the store. Logging is off unless it is asked for here, and it is
asked for here rather than by hand because an entry edited by hand is the
failure this module exists to prevent.

**The mounts are not here.** A flat run of `--mount ref=reference.sqlite`
strings in this array would make a client's JSON the place a mount table is
maintained, and hand-editing it the supported way to change one. They live
in `mounts.toml` in the store directory instead -
[`outrage.mountfile`](mountfile.md#module-outrage.mountfile) - which is what leaves `--dir` as the only thing
this entry has to carry. **An entry already naming mounts
keeps them**: [`merge_entry()`](#outrage.config.merge_entry) inherits what a new entry does not
mention, and they still win, since the command line comes after the file.
Nothing migrates that automatically, deliberately; `outrage config` says
they are there.

`no_info` adds `--no-info`, withholding the tool that reports the
server's environment and stores. Written here for the same reason `--log`
is: it belongs to the launch, and a client's JSON edited by hand is the
failure this module exists to prevent. Being valueless makes no difference
to [`merge_entry()`](#outrage.config.merge_entry) -- it inherits by flag, so a re-run that does not
mention it keeps it.

`no_remount` adds `--no-remount`, withholding the tools that change the
mounts while the server runs. Same shape, same reason, and it is the one
place the decision can be recorded: those tools are the server's, so there
is no command line run to pass a flag to.

### outrage.config.split_args(args: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]]]

Take an argument list apart into `(flag, values)` pairs, in order.

A flag is any token beginning with `-`; its values are the tokens up to
the next flag. That rule is deliberately about *shape* rather than about a
list of known options: an argument this release has never heard of - added
by hand, or by a newer one - comes apart the same way and can be put back
unchanged. A leading token that is not a flag is paired with the empty
string, so nothing is dropped by a list that does not start with one.

### outrage.config.write_config(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), config: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)], original: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [None](https://docs.python.org/3/library/constants.html#None)

Write `config` to `path`, replacing it atomically.

Written to a temporary file in the same directory and moved into place, so
an interrupted write cannot truncate a file holding configuration this
command did not create. Indentation and permissions follow the existing
file where there is one: the point is to change one key, and a wholesale
reformat or a loosened mode is a change nobody asked for.
