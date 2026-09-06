# outrage.mountfile

A mount table kept in a file, and the fiction that makes it one.

A mount table used to be *only* an argument list. For the server that meant it
lived inside a client's `.mcp.json`, in the `args` array, as a flat run of
`--mount ref=reference.sqlite` strings that could only be changed by editing
JSON belonging to somebody else; for the command line it meant there was no
table at all. This is the file it lives in instead.

**The one rule to know.** A file behaves as if the equivalent options had been
inserted into the command line at the point where the file is named. The
default file in the store directory is spelled at the very front, so everything
actually typed comes after it and wins; an explicit `--mount-config FILE`
splices that file's options in where the flag appears, so a flag before it
loses and a flag after it wins.

That rule is worth its weight because it needs no second vocabulary:
precedence, repetition and the interaction of the two are already whatever
argparse does, and there is no separate notion of a merge to specify. It has
one mechanical caveat, and it is unavoidable: `--dir` is what *finds* the
default file, so it cannot be resolved by the same pass that consumes it.
Reading is two passes -- [`directory_in()`](#outrage.mountfile.directory_in) settles `--dir` from the real
argument list, then [`spliced()`](#outrage.mountfile.spliced) builds the list argparse actually parses.

**One exception to the fiction, and it is the point of having a file.** A
duplicate mount point is refused within one source and the later one wins
across sources. `MountedStore` refuses two mounts at one key because that is
somebody typing a mount point twice on one line; that reason does not carry
across two sources, where replacing one entry of a committed table for a single
maintenance run is the whole intent. So [`spliced()`](#outrage.mountfile.spliced) drops an earlier mount
point only when a *later* source claims it, and leaves a repeat within one
source exactly where it was, for `open_mounts` to refuse as it always did.

**TOML, and read only.** A config file is the one place people want comments,
which JSON has none of, and YAML would have cost a second required runtime
dependency where `mcp` is the only one today. `tomllib` has been in the
standard library since 3.11 and this package requires 3.12. It reads and does
not write, which is less of a problem than it looks: a file whose reason for
existing is comments should not be machine-rewritten, because a rewrite is
exactly what loses them.

### outrage.mountfile.BUILTIN_SOURCE *= 'built in'*

What the built-in default is called in the same column.

### outrage.mountfile.CONFIG_FLAG *= '--mount-config'*

Names a file explicitly, and splices it in where the flag appears. Spelled
`--mount-config` rather than `--config`, which would read as being about
the `outrage config` subcommand -- that writes an MCP client's JSON, which
is a different file for a different reader.

### outrage.mountfile.DEFAULT_NAME *= 'mounts.toml'*

The file read from inside `--dir` when nobody names one. The table is a
property of the store directory it describes, which is also what makes every
FILE in it relative to the same place the flags are relative to.

### outrage.mountfile.DIR_FLAG *= '--dir'*

The option that says which *directory* the stores are in, and so the one
option a file cannot hold: it is what finds the default file.

### outrage.mountfile.DOCS_FLAG *= '--mount-docs'*

The documentation shipped inside the package, mounted read-only at
[`outrage.shipped.MOUNT_POINT`](shipped.md#outrage.shipped.MOUNT_POINT). It takes no value: there is no file to
name, because the tree is in `site-packages` rather than in `--dir` and
so is not expressible as a `KEY=FILE` at all -- which is why it is a flag
of its own rather than a spelling of `--mount-ro`.

The **enable** half only. The server carries it by default and the command
line does not, and turning it off is `--unmount outrage`: an override
cannot remove a mount, but that is the flag that already does, and a second
spelling of it would be two ways to say one thing.

### outrage.mountfile.DOCS_MOUNT *= 'outrage'*

The mount point [`DOCS_FLAG`](#outrage.mountfile.DOCS_FLAG) claims. Named through
[`outrage.shipped`](shipped.md#module-outrage.shipped), which owns the answer, so that the splice and the
store agree without either holding a second copy of the word.

### outrage.mountfile.FIELDS *= ('root-mount', 'mount', 'mount-ro')*

Every field a mount configuration may hold. Anything else in one is refused
rather than ignored -- `--log` and the rest would splice in for free, and
whether the file grows that far is a call to make on purpose.

### outrage.mountfile.MOUNT_FIELD *= 'mount'*

The `[mount]` table: one `KEY = "FILE"` entry per read-write mount.

### outrage.mountfile.PATH_FIELD *= 'path'*

The field naming the store file in an entry's table form, and the one field
that is not an option: `{ path = "docs", type = "files" }` is a store and
how to open it. Spelled `path` rather than `file` because that is what a
mount option would have called it, and the other fields *are* options.

### outrage.mountfile.MOUNT_FLAG *= '--mount'*

Another store, under a mount point.

### outrage.mountfile.NO_CONFIG_FLAG *= '--no-mount-config'*

Ignores the default file for one run, so that only what is typed is
mounted. Narrow on purpose: it suppresses the file nobody named, and an
explicit `--mount-config` is something the caller can simply not type.
Needed
rather than tidy -- a mount table requires a writable root, so without it a
project holding a table could not read a packed store at all.

### outrage.mountfile.READ_ONLY_FIELD *= 'mount-ro'*

The `[mount-ro]` table: the same, read-only.

### outrage.mountfile.READ_ONLY_FLAG *= '--mount-ro'*

The same, with every write routed there refused before it reaches the store.

### outrage.mountfile.ROOT_FIELD *= 'root-mount'*

The file's fields are named after the options they stand for, so that
nothing here is a new word for anything: a table entry is `KEY = "FILE"`,
which is the `KEY=FILE` of a spec with the delimiter turned into TOML's
own. This one holds the root mount.

### outrage.mountfile.ROOT_FLAG *= '--root-mount'*

The store answering for every key no mount claims. The command line spells
it `--store` as well, which is an alias for this and not a second option.

### outrage.mountfile.TYPED_SOURCE *= 'the command line'*

What a source that is not a file is called, when one is named to a reader.

### outrage.mountfile.UNMOUNT_FLAG *= '--unmount'*

Removes a mount some earlier source declared, which is the one thing an
override cannot do: it can replace an entry or add one, and only this takes
one away. Command line only -- a file has nothing before it to remove.

### *exception* outrage.mountfile.MountFileError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)

Raised when a mount configuration file cannot be read as a mount table.

### *class* outrage.mountfile.MountTable(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), root: [Spec](mounts.md#outrage.mounts.Spec) | [None](https://docs.python.org/3/library/constants.html#None), mounts: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Spec](mounts.md#outrage.mounts.Spec)], ...], read_only: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Spec](mounts.md#outrage.mounts.Spec)], ...])

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

What one file says, parsed, with every mount point already validated.

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

#### root *: [Spec](mounts.md#outrage.mounts.Spec) | [None](https://docs.python.org/3/library/constants.html#None)*

`--root-mount`: the store answering for every key no mount claims.

#### mounts *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Spec](mounts.md#outrage.mounts.Spec)], ...]*

`(mount point, store)` pairs, mounted read-write.

#### read_only *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Spec](mounts.md#outrage.mounts.Spec)], ...]*

The same, mounted read-only.

#### options() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

This table as the command line it stands for.

### *class* outrage.mountfile.Origin(mount: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), flag: [str](https://docs.python.org/3/library/stdtypes.html#str), value: [str](https://docs.python.org/3/library/stdtypes.html#str), source: [str](https://docs.python.org/3/library/stdtypes.html#str))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One mount in a spliced argument list, and where it came from.

What `outrage mounts` reports and nothing else needs. The table a command
ends up with is a merge of the default file, each `--mount-config`, and
what was typed - so "which of them won" became a question the moment there
was more than one, and the argument list argparse is handed has the answer
beaten out of it.

#### mount *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

The mount point, or None for the root.

#### flag *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### value *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### source *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The file it was read from, or [`TYPED_SOURCE`](#outrage.mountfile.TYPED_SOURCE).

#### *property* read_only *: [bool](https://docs.python.org/3/library/functions.html#bool)*

#### *property* file *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The store this names, whichever of the three options it is.

The value half of the argument, options and all -- what a mount *says*,
rather than only where it points, so that two entries differing in
`type` are not reported as the same mount written twice.
[`store`](#outrage.mountfile.Origin.store) is the same thing parsed.

#### *property* store *: [Spec](mounts.md#outrage.mounts.Spec)*

The store this names, parsed: its file and its options.

### *class* outrage.mountfile.Starter(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), action: [str](https://docs.python.org/3/library/stdtypes.html#str), text: [str](https://docs.python.org/3/library/stdtypes.html#str), missing: [str](https://docs.python.org/3/library/stdtypes.html#str))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

What writing a project's mount table would do, or did.

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

#### action *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

'created' or 'unchanged'.

#### text *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The file's content: what a write made, or what is already there.

#### missing *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The TOML a run named that the file does not already say, or `""`.

Only ever set beside 'unchanged', and it is how the command stays useful
when it declines to write: the lines are the ones to paste in.

#### *property* writes *: [bool](https://docs.python.org/3/library/functions.html#bool)*

### outrage.mountfile.directory_in(argv: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)

`--dir` as the argument list gives it, or None.

The first of the two passes. It cannot be argparse's, because the parser
that would answer this is the one being handed a list that does not exist
until the answer is known.

### outrage.mountfile.origins(argv: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, front: [int](https://docs.python.org/3/library/functions.html#int) = 0, builtin: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Origin](#outrage.mountfile.Origin)]

The mounts `argv` ends up with, each named with where it came from.

The same pass [`spliced()`](#outrage.mountfile.spliced) makes, reported rather than rendered. An
entry a later source replaced is not here, because it is not in the table
either - this is what the command would open, not what it read on the way.

### outrage.mountfile.plan_starter(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, root_mount: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, mounts: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), read_only_mounts: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = ()) → [Starter](#outrage.mountfile.Starter)

Work out what writing this table into `directory` would do.

**Written once, by hand thereafter.** A file whose reason for existing is
comments must not be machine-rewritten, because a rewrite is exactly what
loses them - so a table that is already there is never touched, and a run
naming a mount it does not hold is told which lines to add rather than
having them written underneath the comments somebody wrote.

Nothing at all happens when no mount is named. outrage config and
outrage init exist to register a server and repair a project, and
creating a store directory to drop an empty file into it is not something
either was asked to do.

Every spec goes through [`outrage.mounts.parse_spec()`](mounts.md#outrage.mounts.parse_spec), so a misspelled
mount point is refused while somebody is looking at the command that wrote
it rather than at a server that silently failed to start.

### outrage.mountfile.read(path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [MountTable](#outrage.mountfile.MountTable)

Read one mount configuration file.

Every refusal a mount point can earn is reached through
[`outrage.mounts.mount_point()`](mounts.md#outrage.mounts.mount_point), which is the same parse `--mount`
goes through, rather than being written a second time here. A file that
grew its own idea of what a key is would be a second grammar, and the
project has one.

### outrage.mountfile.sources(argv: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, front: [int](https://docs.python.org/3/library/functions.html#int) = 0, builtin: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

The configuration files a splice read, in the order it read them.

The default file in the store directory first, when there is one and
nothing suppressed it, then each [`CONFIG_FLAG`](#outrage.mountfile.CONFIG_FLAG) as it was written.
The same pass [`spliced()`](#outrage.mountfile.spliced) and [`origins()`](#outrage.mountfile.origins) make, answering the third
question the splice created: *which files does this run read*, as against
which mounts came out of them.

What wants it is a front end reporting itself, since a file that was read
is where a mount is edited -- and a table flattened into one argument list
can no longer say which files it came from, which is exactly what the
splice is for.

A file named twice appears once: these are sources, and the second naming
of one is the same source read again.

### outrage.mountfile.spliced(argv: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, front: [int](https://docs.python.org/3/library/functions.html#int) = 0, builtin: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

`argv` with every mount configuration file's options written into it.

The list argparse is then given. `directory` is the store directory to
look for the default file in; omitted, it is whatever `--dir` in `argv`
says, then the environment, then the working directory -- the same answer
the command itself will resolve.

`front` is how many leading tokens the default file's options go *after*,
and is the one place the fiction needs a number. "The very front" is where
they belong, so that everything typed comes after them and wins -- but a
command line with subcommands has no such position at the front: an option
belonging to `outrage ls` written before the word `ls` is an option on
the wrong parser. So the front of the line is the front of the subcommand,
and a front-end that has one says where it is.

An explicit file *stacks* on the default one rather than replacing it,
because that is what the splice rule says when read literally: naming a
file inserts its options, and inserting them says nothing about the ones
already there. [`NO_CONFIG_FLAG`](#outrage.mountfile.NO_CONFIG_FLAG) is the escape from the default file,
and is the only way to be rid of it.

`builtin` is whether this front end carries the shipped documentation
without being asked -- the server does, the command line does not. It is
spliced in as [`DOCS_FLAG`](#outrage.mountfile.DOCS_FLAG) at the very front, ahead of the default
file, so that it is an ordinary mount for every question that follows:
`mounts.toml` naming that point overrides it, `--unmount` there removes
it, and both by the rules already written rather than by a case for it.
Handled here rather than by the front end passing a pre-opened store,
because override is settled over this list -- a second claim reaching
`open_mounts` is a hard duplicate refusal, which is the opposite of what
overriding a default should do.

### outrage.mountfile.starter_text(table: [MountTable](#outrage.mountfile.MountTable)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

A commented mount configuration holding `table`.

The comments are the point of the file being TOML at all, and they are why
nothing rewrites it afterwards. What is not asked for is shown commented
out, so the shape of every field is on the page whether or not this project
uses it.

### outrage.mountfile.write_starter(starter: [Starter](#outrage.mountfile.Starter)) → [None](https://docs.python.org/3/library/constants.html#None)

Create the file `starter` planned, and only if it is still not there.

Opened exclusively rather than checked and then written: "only when there
is none" is the whole promise, and it is the one thing a plan made a moment
earlier cannot still guarantee.
