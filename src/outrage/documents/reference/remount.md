# outrage.remount

The mount table a running server serves, and how it is changed.

[`outrage.mounts`](mounts.md#module-outrage.mounts) deliberately has none of what is here: a table is
immutable, knows no directory, opens no file and holds no lock. This is where
a table becomes something a *process* has -- one reference, swapped under a
lock, with the stores that fall out of it closed when nothing serves them any
more.

**The safety argument, in one paragraph.** A change never edits a table. It
builds a new one with [`remounted()`](mounts.md#outrage.mounts.MountedStore.remounted) and swaps
the reference, and every server call reads that reference once, at entry, and
uses the table it got for its whole duration. So a traversal spanning several
stores -- a sequence of per-store segments, with a cursor recomputed at each
boundary -- can never see two tables, which is the failure that kept mounts to
start-time configuration until now. What it cannot promise is a *page taken
before a change and continued after it*: a cursor is a key in the outer
namespace, and which store answers for it is exactly what changed. That is the
same class of thing as a document written between two pages, and it is written
down rather than guarded.

**Sharing rather than reopening.** A surviving mount keeps the very same
[`Store`](store.md#outrage.store.Store) object, because
`mount_point` is the only thing a store knows about
its own mounting and a surviving mount keeps its prefix. So an in-flight call
holding the old table goes on reading a store that is also in the new one, and
nothing is opened twice for a mount that did not move. A mount at a *new*
prefix always opens a new store.

**Closing is safe for the same reason it looks unsafe.**
[`close()`](store_sqlite.md#outrage.store_sqlite.SqliteStore.close) closes only the calling
thread's connection, by design, so a store dropped by a change cannot be closed
out from under a call running on another thread; the rest of its connections go
when the store is collected or the thread ends.

Notes are derived here rather than in [`outrage.server`](server.md#module-outrage.server), per the note
layer: this is the layer that knows what the change did, and it carries facts
rather than sentences. What the tools say about them is
[`outrage.messages.MCP`](messages.md#outrage.messages.MCP).

### outrage.remount.SHIPPED *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [Store](store.md#outrage.store.Store)]]* *= mappingproxy({'outrage': <function open_documents>})*

The stores outrage ships, by the mount point each answers for, as the
openers that produce them. This is what lets a mount be spelled without a
file: the shipped tree lives in `site-packages`, is not relative to
`--dir` and so has no `KEY=FILE` spelling at all, which is the whole
reason unmounting the manual would otherwise be a one-way door.

A mapping rather than a special case for `outrage`, because the shape is
the point: a second shipped store would be an entry here and nothing else.

### *class* outrage.remount.Changed(table: [MountedStore](mounts.md#outrage.mounts.MountedStore), notes: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Note](notes.md#outrage.notes.Note), ...] = ())

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

A change, as the table it produced and what is worth remarking on.

The table is returned rather than left to be read back off
[`Live.table`](#outrage.remount.Live.table), because between the two another thread may have changed
it again -- and an answer describing a table that is no longer there is the
one thing a report of a change must not be.

#### table *: [MountedStore](mounts.md#outrage.mounts.MountedStore)*

#### notes *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Note](notes.md#outrage.notes.Note), ...]*

### *class* outrage.remount.Live(table: [MountedStore](mounts.md#outrage.mounts.MountedStore), \*, directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

The table this process is serving, and the only thing that may replace it.

Read [`table`](#outrage.remount.Live.table) once per call and use what you got. The read is a plain
attribute load, which is atomic, so readers take no lock at all; only a
change does, and it holds the lock across opening, cloning and swapping so
that two changes cannot each clone the table the other is about to replace.

`directory` is where a mounted file is looked for, under the same rule
every mount follows -- relative to the store directory, which is what makes
a mount configuration relocatable. `log` is given to any store opened
here, so a dynamically mounted store records what it is asked exactly as
one named on the command line does.

Used as a context manager by [`outrage.server.main()`](server.md#outrage.server.main), in place of the
`with open_mounts(...) as table:` it would otherwise use: that would close
the table it opened, which after a change is no longer the one being
served, and would close stores the live table still shares.

#### *property* table *: [MountedStore](mounts.md#outrage.mounts.MountedStore)*

The table as it is now. Read it once, at the start of a call.

#### *property* directory *: [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*

The store directory a mounted file is named relative to.

#### mount(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, file: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, type: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, read_only: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Changed](#outrage.remount.Changed)

Open a store and mount it at `key`, replacing whatever is there.

`file` is relative to the store directory, as every mount's file is.
Omitting it mounts the store **outrage ships** for that key -- today the
documentation at `outrage` and nothing else -- which is the only way
back for a caller that unmounted the manual, since a tree in
`site-packages` has no spelling as a mount file. A shipped store is
always mounted read-only: the next upgrade replaces it, so anything
written there would be lost, and the table the call returns says so.

A read-only mount must already exist, the same refusal
[`open_mounts()`](mounts.md#outrage.mounts.open_mounts) makes and for the same reason: a
mistyped name would be *created*, mount as an empty store, and read as
though the reference base were simply empty, while the flag that was
supposed to protect it made that impossible to notice by writing.

#### unmount(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Changed](#outrage.remount.Changed)

Drop the mount at `key`, and close its store once nothing serves it.

What the store beneath was holding there comes back into view, which is
the one consequence a caller is unlikely to have in mind: a mount
*shadows*, so keys the outer store holds at the mount point have been
unreachable for as long as it was mounted.

#### close() → [None](https://docs.python.org/3/library/constants.html#None)

Close every store the live table holds.

### outrage.remount.notes_for_mount(after: [MountedStore](mounts.md#outrage.mounts.MountedStore), prefix: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, replaced: [bool](https://docs.python.org/3/library/functions.html#bool)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]

What a mount is worth remarking on, as codes and facts.

Two of them are about what the caller can no longer see. A mount
**shadows**: the store that would otherwise own those keys is never
consulted for them, so a document sitting at the mount point becomes
unreachable rather than merged -- which the server has warned about on
stderr at startup since mounts existed, where a tool caller could not read
it. And a mount at a point something already held has *replaced* it, which
is the rule a tool call makes unambiguous in a way two configuration
sources do not.

### outrage.remount.notes_for_unmount(after: [MountedStore](mounts.md#outrage.mounts.MountedStore), prefix: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]

What an unmount is worth remarking on.

Asked of the table *after* the change, which is what makes it true: whether
anything is there now is a question about the store that answers for the
key now, and the old table's mount is exactly what stopped that store being
consulted.
