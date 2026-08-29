# outrage.shipped

The documentation store that ships inside the package, and where it is.

A read-only store of documents *about outrage* -- what a key is, what the tools
do, the conventions worth following -- mounted at `outrage` so that a session
can read them the same way it reads anything else. No second retrieval path, no
second vocabulary: the manual is documents in the namespace.

**Two halves, and only one of them is written by hand.** The documents at the
top of the tree, `skills/` among them, are prose, edited in place like any
other file in the repository. `reference/` is the API documentation, rendered from the
docstrings in `src/outrage` by `make markdown` in `docs/` and copied in --
one page per module, reached as `outrage/reference/<module>`. Editing a page
there is editing build output: the change is lost at the next render, and the
source is the docstring. `context/71` in the outrage store is the design and
the three ways the render is silently wrong if it is done by hand.

Nothing in this module knows the difference, and that is on purpose. A
generated page is a file in a directory of files, so it mounts, lists, reads
and is surveyed exactly as the hand-written ones are, and neither
[`open_documents()`](#outrage.shipped.open_documents) nor the mount has a case for it.

**Why this is its own module.** The tree lives in `site-packages` once
installed, and every mount a table opens is a file *relative to* `--dir` --
[`outrage.store.store_file()`](store.md#outrage.store.store_file), which refuses an absolute path on purpose,
since that rule is what makes a mount configuration relocatable. So this mount
cannot be written as a `KEY=FILE` spec at all. It is opened here, by absolute
path, and handed to [`outrage.mounts.open_mounts()`](mounts.md#outrage.mounts.open_mounts) as an already-opened
store -- see its `attached` argument, which is the whole of the mount-system
change this needed. `project/reference/planned/mounts/default-store` in the
outrage store is the argument for all of it.

**The one behaviour to expect.** The mount is ordinary once it is there: it
shadows, it is listed, it takes precedence exactly as any mount at `outrage`
would, and a mount table naming `outrage` overrides it silently by the
ordinary rule that a later source wins. The only thing special about it is that
the server mounts it without being asked and the command line does not --
`--mount-docs`.

**One directory here is delivered, and it is not the readme.** `skills/`
holds the static text [`outrage.server.instructions()`](server.md#outrage.server.instructions) sends when a client
connects, as the two documents it is delivered in -- so editing a file there
edits what every session is told, and the budget arithmetic in
[`outrage.server`](server.md#module-outrage.server) is what bounds it. The server reads those files directly
rather than through this mount: it needs them at import, and a mount table
naming `outrage` would otherwise decide what the server says about itself.

Nothing else here is delivered, the readme included. Only the *root* store's
readme is, on the delivery-budget argument in
[`outrage.server.instructions()`](server.md#outrage.server.instructions); this store announces itself as a mount in
a listing and is read on demand. That is deliberate and belongs to the session
bootstrap rather than here.

### outrage.shipped.MOUNT_POINT *= 'outrage'*

Where the shipped documentation is mounted. A single segment, and the
project's own name, because the question it answers is "what does outrage
itself say about this" -- the same word somebody would type to ask.

### outrage.shipped.TREE_NAME *= 'documents'*

The directory inside the installed package holding the tree. A directory of
files rather than a database, so it is diffable in the repository and
shipped by the same wheel rule that already carries `src/outrage/skills/`
-- the packaged agent skill, a different thing from the `skills/`
directory *inside* this tree -- and `codex/`. Editable without a tool as
well -- but of the hand-written half only, and the module docstring says
which that is.

### *exception* outrage.shipped.DocumentsError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`FileNotFoundError`](https://docs.python.org/3/library/exceptions.html#FileNotFoundError)

Raised when the shipped documentation is not in the installation.

### outrage.shipped.attached(\*, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [FilesystemStore](store_files.md#outrage.store_files.FilesystemStore)]

The documentation as the `attached` argument `open_mounts` takes.

One call rather than two lines repeated in each front end, and the mount
point is spelled once.

### outrage.shipped.available() → [bool](https://docs.python.org/3/library/functions.html#bool)

Whether this installation actually carries the tree.

A build that dropped it is the failure this exists to notice: 0.1.0 shipped
without `src/outrage/skills/` and nothing said so. `test_packaging.py`
is where that is guarded; this is what a front end asks before mounting
something it was not explicitly told to mount.

### outrage.shipped.open_documents(\*, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [FilesystemStore](store_files.md#outrage.store_files.FilesystemStore)

Open the shipped tree, read-only, refusing if it is not there.

`create=False`, so this never writes into an installation: a missing tree
is reported rather than made, which is the same argument
[`outrage.mounts.open_mounts()`](mounts.md#outrage.mounts.open_mounts) makes for a read-only mount that names
nothing. Read-only is enforced by the *mount*, since
[`FilesystemStore`](store_files.md#outrage.store_files.FilesystemStore) is a writable backend and the
file permissions of a `site-packages` directory are not something to rely
on.

`hidden` is left at its default: this is a tree outrage wrote, so a
dotfile in it is a document rather than somebody's `.DS_Store`.

### outrage.shipped.tree() → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

The directory the documents are in, whether or not it is there.

`__file__`-relative rather than [`importlib.resources`](https://docs.python.org/3/library/importlib.resources.html#module-importlib.resources), and for a
reason worth stating: the store reads and stats real paths, so a resource
that had to be materialised out of a zip would be a copy with a different
lifetime. Every supported installation -- an editable checkout, a wheel
unpacked by pip -- puts the tree on the filesystem beside this module.
