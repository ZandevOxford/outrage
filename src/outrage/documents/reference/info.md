# outrage.info

What the process answering is: its environment, its stores, and its log.

A caller reaching a store through the MCP server can see everything in it and
nothing about the server holding it. That is a real gap rather than a cosmetic
one, because the answers are not guessable from outside: which Python
environment this build runs in, which files the mounts are kept in, and which
configuration file a mount would be edited in.

**The environment is the one worth stating.** An installation is normally
editable, so the working tree *is* the build, and a caller that wants to run
the command line has to run the one beside *this* interpreter rather than
whatever `outrage` resolves to on their PATH. [`describe()`](#outrage.info.describe) reports the
interpreter, its prefix and the console script's absolute path so that it can.

Facts only, in the dataclasses below, and no sentence anywhere: both front ends
call [`describe()`](#outrage.info.describe) and each says what it says. The report is about the
process that answers it -- a command line run has no event log of its own and
reports none, which is not a claim about what the server for the same store
does.

### *class* outrage.info.Info(version: [str](https://docs.python.org/3/library/stdtypes.html#str), python: [str](https://docs.python.org/3/library/stdtypes.html#str), prefix: [str](https://docs.python.org/3/library/stdtypes.html#str), command: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...] = (), directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, mount_config: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...] = (), log: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, log_content: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, mounts: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[MountInfo](#outrage.info.MountInfo), ...] = ())

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

What one running front end can say about itself.

#### version *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### python *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The running interpreter, as [`sys.executable`](https://docs.python.org/3/library/sys.html#sys.executable) gives it.

**Not resolved through its symlinks**, unlike every path below. A virtual
environment's interpreter is a link to the one it was made from, so
resolving it would name the environment the caller must *not* use.

#### prefix *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The environment the interpreter belongs to, [`sys.prefix`](https://docs.python.org/3/library/sys.html#sys.prefix).

#### command *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...]*

The command line entry point in that environment, empty when this
installation has no console script -- see
[`outrage.config.script_command()`](config.md#outrage.config.script_command).

#### directory *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

The store directory, or None when the caller had none to give. None
rather than the default guess: a report that names the wrong directory
confidently is worse than one that says it does not know.

#### mount_config *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...]*

The mount configuration files read, in the order they were read.

#### log *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

Where this process is recording what it does, or None when it is not.

#### log_content *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

How much document text that log keeps, or None when there is no log.

#### mounts *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[MountInfo](#outrage.info.MountInfo), ...]*

The stores behind the namespace, as they were opened.

### *class* outrage.info.MountInfo(mount: [str](https://docs.python.org/3/library/stdtypes.html#str), path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), kind: [str](https://docs.python.org/3/library/stdtypes.html#str), read_only: [bool](https://docs.python.org/3/library/functions.html#bool))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One mount, as a report names it.

#### mount *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The mount point written for a person to read; the root is `/`.

#### path *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

Absolute path of the file this store is kept in, or None for a store
that keeps none. Absolute because the point of reporting it is that
somebody elsewhere can act on it.

#### kind *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

[`ROOT_KIND`](mounts.md#outrage.mounts.ROOT_KIND), [`MOUNT_KIND`](mounts.md#outrage.mounts.MOUNT_KIND) or
[`READ_ONLY_MOUNT_KIND`](mounts.md#outrage.mounts.READ_ONLY_MOUNT_KIND).

#### read_only *: [bool](https://docs.python.org/3/library/functions.html#bool)*

Whether this process refuses writes routed here.

### outrage.info.describe(opened: [Store](store.md#outrage.store.Store), \*, directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, mount_config: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Info](#outrage.info.Info)

Describe this process and the stores it has open.

`opened` is reported as it **is**, not as it was asked for: the mounts
come from the live table, so a mount that was overridden, or one that
arrived without being named on any command line, is in the answer once and
where it really is. A lone store that is not a table is the root of a
namespace of one, which is what it answers as.

`mount_config` and `directory` are the two things the stores cannot be
asked -- [`outrage.mountfile.sources()`](mountfile.md#outrage.mountfile.sources) and
[`outrage.store.resolve_directory()`](store.md#outrage.store.resolve_directory) know them, and by the time there is
a table both have been flattened away.
