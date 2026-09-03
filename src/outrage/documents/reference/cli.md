# outrage.cli

Command line tool over the store library.

A thin wrapper, like the server: argument shaping and printing only. Anything
with behaviour belongs in [`outrage.store`](store.md#module-outrage.store) or [`outrage.config`](config.md#module-outrage.config), so that it
can be tested without going through argparse and used by whichever of the two
front ends needs it.

What this module *offers* is [`argument_parser()`](#outrage.cli.argument_parser), [`parse_args()`](#outrage.cli.parse_args),
[`main()`](#outrage.cli.main), and [`ConflictingSourceError`](#outrage.cli.ConflictingSourceError) as something to catch. The
subcommand handlers are argparse wiring reached through `handler`, one per
subcommand and never from outside, so they are private -- which also keeps this
page from being a list of twelve near-identical `(args, out) -> int` entries
in place of an orientation. The interface people actually use here is the
command line, and `outrage --help` is what states it.

### outrage.cli.MOUNTED *= ('get', 'set', 'ingest', 'ls', 'dump', 'copy', 'rm', 'export', 'import', 'mounts')*

The subcommands that act across a whole mount table rather than on one
store file. Everything that reads or writes documents is here; `check` and
`backup` are not, and by nature: both are about a *file* -- its integrity,
its bytes -- and both already say which one they mean with `--store`.
`pack` is not either, for the same reason its target is one file.

`mounts` is here for the options and the splice rather than for opening
anything: it reports the table a command line would open, which is a
question only worth asking of the same list every other one of these gets.

Read by [`parse_args()`](#outrage.cli.parse_args) to decide whether a mount configuration file is
spliced in, and by the loop that adds the options, so the two cannot drift.

### *exception* outrage.cli.ConflictingSourceError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError)

Raised when the content to store cannot be determined from the arguments.

### outrage.cli.argument_parser() → [ArgumentParser](https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser)

Build the whole command-line interface.

Every subcommand sets `handler`, so [`main()`](#outrage.cli.main) dispatches without a
branch per command and this function is the one place the shape of the
command line is written down. It returns a new parser on every call, making
the interface available to documentation and other introspection without
parsing `sys.argv` or reading a mount configuration.

### outrage.cli.main(argv: [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, out: [TextIO](https://docs.python.org/3/library/typing.html#typing.TextIO) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [int](https://docs.python.org/3/library/functions.html#int)

Run one command and return its exit status.

The console script `outrage`, and the whole of what this front end does:
parse, dispatch, and turn a [`OutrageError`](errors.md#outrage.errors.OutrageError) into a sentence
on stderr. `out` is where a command's own output goes, and defaults to
stdout; a test passes its own and reads what a person would have seen.

Returns rather than exits, so that a caller in the same process -- which is
every test of this module -- gets the status without the interpreter
stopping.

### outrage.cli.parse_args(argv: [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Namespace](https://docs.python.org/3/library/argparse.html#argparse.Namespace)

Parse an argument list and attach the selected command's handler.

Separate from [`main()`](#outrage.cli.main) so that a test can ask what an argument list
parses to without running anything.

The subcommands in [`MOUNTED`](#outrage.cli.MOUNTED) have their mount options spliced in
from a configuration file first -- see [`outrage.mountfile`](mountfile.md#module-outrage.mountfile). Only
those, because a subcommand that does not take the options would be handed
ones it has never heard of; and the subcommand is read off the front of the
argument list rather than parsed, since parsing is what has not happened
yet. That is safe here for one reason worth keeping true: **no option on
the top level parser takes a value**, so the first token that is not a flag
is the subcommand.
