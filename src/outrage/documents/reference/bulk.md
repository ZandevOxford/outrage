# outrage.bulk

Whole subtrees, in and out: the streaming walkers, and the file mapping.

The store's own reads are pages, and every one of them is bounded on purpose.
This module holds the callers that legitimately want all of it - a listing of a
level, an export of a subtree, an import of a directory - and gets there the
only way that stays bounded: page internally, yield as each page arrives, and
never hold the collection.

Behaviour rather than argument shaping, so that it can be tested without going
through argparse. `cli` prints what these yield and decides nothing.

The file mapping is one rule: **a key segment is a path component, and a
document gets an extension naming its format**. a/b stored as markdown is
a/b.md, and anything below a/b is in the directory a/b/, which is why the
extension exists at all - a key is both a document and a container, and a path
cannot be both a file and a directory. Metadata is a segment like any other, so
a/b/!title is the file a/b/!title.md. Nothing is escaped and nothing is
transformed, which is the arrangement the key grammar was widened for: the
characters a filename can hold are the characters a segment can hold.

A tree is written from the root of the key namespace, not from the key that was
exported, so outrage export out context/10 writes out/context/10/... and
re-imports to where it came from. Grafting it somewhere else is what the
import's key prefix is for.

What this is not is a backup. updated_at does not survive the round trip and
neither does anything else the database holds about a document; `FileStore.backup`
is the copy that keeps all of it.

### outrage.bulk.Document

One document as [`outrage.store_parquet.ParquetStore.build()`](store_parquet.md#outrage.store_parquet.ParquetStore.build) takes it:
key, content, the format or None to detect it, and the timestamp or None
for now. A tuple rather than a class because it is what a build consumes
and nothing holds one for longer than that.

alias of [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`str`](https://docs.python.org/3/library/stdtypes.html#str), [`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None), [`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)]

### outrage.bulk.EXTENSION_BY_FORMAT *= {'html': '.html', 'json': '.json', 'markdown': '.md', 'text': '.txt'}*

The extension a document is written with, by stored format. Named for the
direction it maps in, because the inverse is right below it and a reader
reaching for one of the two should not have to check which is which. One
entry per member of [`outrage.store.FORMATS`](store.md#outrage.store.FORMATS), so nothing can be stored
that an export cannot name.

### *class* outrage.bulk.Exported(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), excerpt: [Excerpt](store.md#outrage.store.Excerpt), replaced: [bool](https://docs.python.org/3/library/functions.html#bool))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

What exporting one document did: where it went, and what stood there.

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

The file written.

#### excerpt *: [Excerpt](store.md#outrage.store.Excerpt)*

The document written to it, whole.

#### replaced *: [bool](https://docs.python.org/3/library/functions.html#bool)*

Whether a file was already at that path. A fact, not a refusal:
overwriting on re-export is the point of a deterministic name, and the case
it costs is an edit that had not been imported back yet. See
`context/66/decisions`, call 1.

### outrage.bulk.FALLBACK_PREFIX *= 'document-'*

What a key with no path of its own is named instead. Not
[`TEMP_PREFIX`](#outrage.bulk.TEMP_PREFIX), which marks a file that is half written and that a
reader must skip: this one is the export, and it is finished.

### outrage.bulk.FORMAT_BY_EXTENSION *= {'.html': 'html', '.json': 'json', '.md': 'markdown', '.txt': 'text'}*

The format a file name declares. Deliberately the inverse of
[`EXTENSION_BY_FORMAT`](#outrage.bulk.EXTENSION_BY_FORMAT) and nothing more: the extensions an export
writes are the extensions an import strips, so a file named myfile.py
keeps its name and becomes the key myfile.py rather than losing a suffix
nothing here put there. That is why there is no .htm and no .text, close
as they are -- an export never writes one, so an import reads it as part of
the name. Not to be confused with [`outrage.store.FORMATS`](store.md#outrage.store.FORMATS), which is what
a document may be *stored* as; this is what a file name says it is.

### *class* outrage.bulk.Imported(key: [str](https://docs.python.org/3/library/stdtypes.html#str), stored: [int](https://docs.python.org/3/library/functions.html#int), previous: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

What importing one file did: where it went, and what it displaced.

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The key written, as it was asked for.

#### stored *: [int](https://docs.python.org/3/library/functions.html#int)*

Characters written.

#### previous *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*

Characters the key held before, or None if it held nothing. The
distinction is kept because an empty document and no document are different
things to have overwritten.

### outrage.bulk.PAGE *= 200*

How much of a collection one internal query asks for. The command line reads
to the end regardless, so this only decides how many round trips that takes
and how much is held at once: large enough to be one query for an ordinary
level, small enough that a huge one is never held whole.

### outrage.bulk.Packable

What a pack's source yields: the report of one document, and the document
itself -- or None where there is nothing to pack, which is a symlink or a
file that would not read. Paired so a caller can print the walk as it
happens while the rows accumulate for a file that is written at the end.

alias of [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`Transfer`](store.md#outrage.store.Transfer), [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`str`](https://docs.python.org/3/library/stdtypes.html#str), [`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None), [`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)] | [`None`](https://docs.python.org/3/library/constants.html#None)]

### outrage.bulk.TEMP_PREFIX *= '.outrage-'*

What a half-written file is called while it is being written. Named rather
than spelled inline because a store that *reads* a tree has to skip one:
`_write_file()` finishes with `os.replace`, so the temporary is only
ever seen by a reader looking at the same directory at the same moment, and
a reader that took it for a document would report a key nothing wrote.

### outrage.bulk.TRAVERSAL *= ('.', '..')*

Segments that are legal keys and impossible file names. . and .. became
legal segments when the grammar widened to mirror a filesystem; a path
component of .. does not mirror anything, it climbs out of the directory
the caller named.

### outrage.bulk.UNNAMEABLE *= ('key-segment-is-traversal', 'key-escapes-tree')*

The mapping failures a single-document export answers with a random name
instead of a refusal, and exactly those: a key that cannot be a path is
still a key somebody wants to edit, and there is nowhere else for it to go.
Anything else [`path_for_key()`](#outrage.bulk.path_for_key) or [`contained_path()`](#outrage.bulk.contained_path) raises is a
refusal, and stays one.

### *exception* outrage.bulk.FileMissingError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`FileNotFoundError`](https://docs.python.org/3/library/exceptions.html#FileNotFoundError)

Raised when the file to import one document from is not there.

### *exception* outrage.bulk.OverlappingCopyError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)

Raised when a copy would write into the subtree it is still reading.

### *exception* outrage.bulk.SourceMissingError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`FileNotFoundError`](https://docs.python.org/3/library/exceptions.html#FileNotFoundError)

Raised when the directory to import from is not there.

### *exception* outrage.bulk.UnmappableError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)

Raised when a key has no file it can be written to, or a file no key.

### outrage.bulk.contained_file(root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

`path` as a file inside `root`, refused unless it stays inside it.

The absolute-path end of [`contained_path()`](#outrage.bulk.contained_path), which takes a path
*relative* to the root because that is what a key maps to. An import
arrives with the absolute path an export handed back, so it is relativised
and then checked by the one rule - rather than by a second containment
strategy that could disagree with the first.

### outrage.bulk.contained_path(root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], relative: [PurePosixPath](https://docs.python.org/3/library/pathlib.html#pathlib.PurePosixPath), key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

`root / relative`, refused unless it stays inside `root`.

**The guard on the join, rather than on the segments.** A segment of ..
is refused by [`path_for_key()`](#outrage.bulk.path_for_key) and gives a good sentence when it is,
but it was never the whole of the question: the traversal that is
reachable today is in the *target tree* rather than in the namespace, a
symlinked directory anywhere along the path being enough to write through
it. Resolving the joined path and requiring containment catches that, and
the two Windows cases beside it -- a segment holding a backslash, which
re-parses into components off a Windows path, and one holding a colon,
which becomes a drive and drops the target from the path entirely --
without enumerating what a component may look like on any platform.

[`os.path.realpath()`](https://docs.python.org/3/library/os.path.html#os.path.realpath) rather than `Path.resolve()`, for the strict
reading of a path that does not exist yet: the file being written is
usually the part that is missing, and it is the *directories* above it that
a link can redirect.

See `project/reference/planned/export-traversal`, which is the whole
analysis and says which of these are reachable where.

### outrage.bulk.copied(source: [Store](store.md#outrage.store.Store), target: [Store](store.md#outrage.store.Store), subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = store.EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = store.UNBOUNDED, prefix: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, reroot: [bool](https://docs.python.org/3/library/functions.html#bool) = False, on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str) = SKIP, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Generator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Generator)[[Transfer](store.md#outrage.store.Transfer), [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]

Every document `subtree` names, from one store into another.

What [`outrage.store.Store.copy_from()`](store.md#outrage.store.Store.copy_from) does unless a backend has a
better way, and it is called through that rather than directly: a caller
naming both ends in one breath cannot be overridden by the end that knows
how it is written. Here because the walk is here -- a store's own reads
are pages and this is the caller that legitimately wants all of them.

Read with [`outrage.store.read_all()`](store.md#outrage.store.read_all) rather than through
`get_documents`, for the reason `context/11/decisions` settled: a
subtree read selects documents *or* named metadata, so there is no "all of
it, metadata included" read, and a copy missing every `!title` leaves a
store nothing can be surveyed by. One read per document is what
completeness costs.

A collision is decided on the key at the far end, by asking the target,
which is the only thing that knows -- and the answer a *tree* gives is
about the key rather than about one spelling of its file, so a document
already there as `a.md` collides with one arriving as json.

`reroot` decides which of the two spellings `prefix` means, and the
difference is what a caller moving a subtree needs: grafted, every key
keeps its own name beneath the prefix, so `a/b` copied to `tmp` lands
at `tmp/a/b`; re-rooted, the subtree's own key is stripped first and it
lands *at* `tmp`. Both are wanted -- an archive keeps the whole key on
purpose -- but only the second can say "these documents now live at
another key", and without it no copy can express a move at all. See
[`overlapping()`](#outrage.bulk.overlapping), which is why the safe pairs differ between them.

`limit` and `cursor` are how a copy too large for one call is taken in
pieces, and they are the pair a *front end* needs rather than a person at a
terminal: the command line reads to the end and prints as it goes. At most
`limit` documents cross, and the generator **returns** the source key of
the last one -- the resume cursor, None when the selection ran out and
there is nothing left to resume from. Returned rather than yielded because
it is a fact about the run and not a transfer, and because it is a *source*
key: a `Transfer` carries the key written, which under a prefix or a
reroot is not the key to come back with.

The stop is decided before the write, not after it, so a run stopped by
`limit` has copied exactly that many documents and the next call starts
where this one stopped rather than a document past it. `cursor` is what
it costs: the walk is filtered rather than sought, as every bound here is,
so resuming re-lists the keys already crossed. It does not re-read them,
which is where the expense in a copy is.

### outrage.bulk.documents_from_store(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Transfer](store.md#outrage.store.Transfer), [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)] | [None](https://docs.python.org/3/library/constants.html#None)]]

Every document at and below `key` in `opened`, beside the report.

The other half of a pack, and the one a reference base is usually made
with: accumulate into a writable store, then compact. Built on the same
walk an export uses, so metadata comes across as the rows it is -- a
`!title` is a key like any other here, and a packed store surveys exactly
as the one it came from did. An export that left every title behind would
make the survey worthless, and so would a pack.

Timestamps come across too, which is what makes this a compaction rather
than a copy that quietly restamps the corpus.

### outrage.bulk.documents_from_tree(source: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, hidden: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Transfer](store.md#outrage.store.Transfer), [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)] | [None](https://docs.python.org/3/library/constants.html#None)]]

Every file below `source` as a document, beside the report of it.

The same walk, mapping and refusals [`import_tree()`](#outrage.bulk.import_tree) makes -- one path
to a key, symlinks named and not followed, a file that is not text reported
rather than mangled -- so a tree packs to exactly the keys importing it
would have produced. Shared by walking the same helpers rather than by
calling `import_tree`, which needs a store to write to and this does not.

Yields the `Transfer` first so a caller can report as it reads, and the
row second, or None when there is nothing to pack. `updated_at` is None:
a file's modification time is not the store's timestamp for the document,
and inventing one at build time is the honest answer -- see
[`outrage.store_parquet.ParquetStore.build()`](store_parquet.md#outrage.store_parquet.ParquetStore.build).

### outrage.bulk.export_document(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [Exported](#outrage.bulk.Exported)

Write the document at `key` to its file under `root`, whole.

The whole document rather than a slice, which is the only readable size: a
slice edited and imported back is a silent truncation of everything the
read stopped short of.

### outrage.bulk.export_tree(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), target: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str) = SKIP, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Transfer](store.md#outrage.store.Transfer)]

Write every document at and below `key` into `target`, one per file.

A copy into a directory of files, which is what an export always was: the
mapping it is written by is [`FilesystemStore`](store_files.md#outrage.store_files.FilesystemStore)'s
now, so this is where the target directory becomes a store and nothing
more. Yields a `Transfer` per document as it goes.

Nothing already in `target` is replaced unless `on_conflict` says so,
because the directory belongs to the caller rather than to the store: an
export into a working directory is otherwise a way to lose work that was
never in the store to begin with. What is already there is decided **by
key** rather than by one spelling of its file, so a document held as
`a.md` collides with one arriving as json.

`FilesystemStore` is imported here rather than at the top of the module
because it is written in terms of this one -- the mapping lives here and
the store is expressed in it, not the other way round.

### outrage.bulk.file_for_key(root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], key: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), [bool](https://docs.python.org/3/library/functions.html#bool)]

The file under `root` that `key` is exported to, and whether it is the
key's own.

The key's own mapped path, so exporting a key twice reuses one file:
nothing accumulates, and a stale copy of an earlier export cannot be picked
up by mistake. The cost is taken deliberately - a second export overwrites
an edit that had not been imported back yet.

**A key with no path gets a random name here instead**, for the two cases
in [`UNNAMEABLE`](#outrage.bulk.UNNAMEABLE). It still carries the format's extension, because
with the key and the path free to disagree the path is the only thing left
that says what the content is.

The root key is not one of those cases: it maps to the extension alone at
the top of `root`, which is hidden and valid.

The flag says which of the two happened, because the answers differ in what
a caller may say about the file: a mapped path may already hold an earlier
export, and a fallback never does.

### outrage.bulk.import_document(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [Imported](#outrage.bulk.Imported)

Store the content of `path` at `key`, and say what it displaced.

`path` must be inside `root`, which is the whole of the check: a tool
that stored any file the caller named would read anything the server can
read. See `project/reference/planned/export-traversal`.

**A relative \`\`path\`\` is relative to \`\`root\`\`**, not to the working
directory: it is relativised before it is checked, so the containment rule
is asked once. `tmp/1.md` is a good way to name an export; the same file
named `.outrage/export/tmp/1.md` from the repository root is not.

**The key and the path do not have to agree.** The content is stored where
the caller says, whatever file it came from, which is what makes an export,
an edit and an import to a second key a way of copying content around the
store.

An empty file is stored rather than refused - emptying a document is a
thing a person may legitimately mean. What guards the accident is the
report: both sizes come back, so an edit script that truncated is visible
to whoever asked. See `context/66/decisions`, call 3.

### outrage.bulk.import_tree(opened: [Store](store.md#outrage.store.Store), source: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str) = SKIP, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, hidden: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Transfer](store.md#outrage.store.Transfer)]

Store every file below `source`, keyed by its path under `key`.

The inverse of [`export_tree()`](#outrage.bulk.export_tree) and the same operation: a copy *out of*
a directory of files into a store. Yields a `Transfer` per file as it
goes.

`hidden` is whether a dotfile is a document. False by default, which is
the policy for a **foreign** tree -- one this package did not write, where
a `.git` or a `.DS_Store` is not a document and importing it as one is
a surprise. The root document is exempt either way, since it is named by
its extension alone.

What the tree does not hold as a document does not cross and is not
reported: a symlink, a half-written file, a name that is not a key, and the
second file claiming a key two of them claim. `outrage check` over the
tree is what names those, because deciding what a directory holds is the
store's question rather than the transfer's.

`on_conflict` decides what happens to a key that already holds something,
one key at a time: `stop` is the strictest available and stops at the
first, having kept what it already wrote. There is deliberately no mode
that refuses the whole import unless every key is free - a directory could
be walked twice to promise that, but a source that is a stream cannot be,
and a guarantee that quietly weakens when the source changes is worse than
one never offered. `--dry-run` is what answers the question that mode was
reaching for.

### outrage.bulk.pack(target: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], documents: [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Transfer](store.md#outrage.store.Transfer), [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)] | [None](https://docs.python.org/3/library/constants.html#None)]], \*, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Transfer](store.md#outrage.store.Transfer)]

Report each document as it is read, then write them all as one file.

**The write is at the end, and that is the shape of the format rather than
a choice.** A parquet store is sorted by key on the way in and its
statistics describe the whole of it, so there is no point at which half a
file is a usable store. So this reports `read` per document, not
`wrote`: an interrupted pack has written nothing, and a report claiming
otherwise would be the kind of half-truth `import_tree` streams
specifically to avoid.

Nothing is skipped for collisions the way an import is. There is nothing to
collide with -- the target is a new file, refused outright if it is already
there unless `overwrite` -- and two source documents claiming one key is
resolved by the last one, which is what overwriting means everywhere else.

### outrage.bulk.key_for_path(relative: [PurePosixPath](https://docs.python.org/3/library/pathlib.html#pathlib.PurePosixPath) | [str](https://docs.python.org/3/library/stdtypes.html#str), prefix: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]

The key a file at `relative` imports to, and the format it declares.

The inverse of `path_for_key` for anything an export wrote, and the
obvious reading of anything else: a name carrying neither extension keeps
it whole and has its format detected from the content instead.

```pycon
>>> key_for_path("a/b.md")
('a/b', 'markdown')
>>> key_for_path("b.json", "a")
('a/b', 'json')
>>> key_for_path("notes.txt"), key_for_path("page.html")
(('notes', 'text'), ('page', 'html'))
>>> key_for_path("src/myfile.py")
('src/myfile.py', None)
```

### outrage.bulk.levels(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Entry](store.md#outrage.store.Entry)]

One level, a page at a time, to the end.

The store pages and the command line does not: a person listing a key wants
the level, and a listing that stops at an internal page size is the silent
partial answer this project keeps finding. Streaming is what makes it both
complete and bounded in memory - and it fails better, since a long listing
interrupted has already shown its first thousand lines rather than nothing.

### outrage.bulk.overlapping(source: [str](https://docs.python.org/3/library/stdtypes.html#str), target: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, reroot: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [None](https://docs.python.org/3/library/constants.html#None)

Refuse a source and target pair a copy cannot safely stream between.

[`copied()`](#outrage.bulk.copied) walks the source live rather than snapshotting it, so a
document landing inside the selection can be found by the walk that is
still running and copied a second time. Which landings those are depends
on the spelling, and the two are not symmetrical:

* **grafted**, every key lands beneath `target` *and* its own source key,
  so the landing zone is inside the selection exactly when `target` is at
  or below `source`. The other direction is safe and shipped:
  `copy a/b a` writes `a/a/b/...`, which the walk of `a/b` never
  reaches. `context/68/decisions` 1 is the decision not to widen the rule
  to cover it.
* **re-rooted**, the source key is stripped, so every key lands beneath
  `target` alone and the two subtrees have to be disjoint. `a/b`
  re-rooted onto `a` sends `a/b/b/x` to `a/b/x` -- back inside the
  walk it came from, and later in the order than the key being read.

Called by a front end before the copy starts, so that the refusal is a
refusal rather than an exception raised out of a generator half way
through. Both front ends call this one, because the command line and the
server disagreeing about which copies are allowed is exactly the split
`mounts.toml` was made to avoid.

### outrage.bulk.path_for_key(key: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [PurePosixPath](https://docs.python.org/3/library/pathlib.html#pathlib.PurePosixPath)

The relative path `key` is written to, extension included.

```pycon
>>> path_for_key("a/b", "markdown"), path_for_key("a/b", "json")
(PurePosixPath('a/b.md'), PurePosixPath('a/b.json'))
>>> path_for_key("a/b", "text"), path_for_key("a/b", "html")
(PurePosixPath('a/b.txt'), PurePosixPath('a/b.html'))
>>> path_for_key("a/b/!title")
PurePosixPath('a/b/!title.md')
```

### outrage.bulk.walk(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Entry](store.md#outrage.store.Entry)]

Every key below `key`, depth first.

Built from repeated `list_keys` rather than from `get_documents`,
because only `list_keys` reports the containers - a key holding nothing
itself but with documents beneath it does not appear in a subtree read at
all, and leaving it out of a listing is how its children look parentless.
It is also the only walk that reports metadata beside the documents, which
is what an export needs: a survey by title is worth nothing if the export it
came from left every title behind.

**It descends into a metadata entry too**, because a `!` segment opens a
namespace and there may be documents inside it. It used to stop at one, on
the reading that metadata was a leaf; an export then dropped `a/!x/y`
without saying so. The shape on disk is the ordinary
document-with-children one -- `!x.md` beside the directory `!x/` --
which is what `FilesystemStore` already writes.
