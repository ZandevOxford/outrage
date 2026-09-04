# outrage.store_files

A document store that is a directory of files: one key, one file.

The mapping is [`outrage.bulk`](bulk.md#module-outrage.bulk)'s, unchanged and reused rather than
restated -- a segment is a path component, an extension names the format, so
`a/b` stored as markdown is the file `a/b.md` and everything below `a/b`
is in the directory `a/b/`. That mapping already existed as a pair of one-off
tree walkers; this is the same rule expressed as a [`Store`](store.md#outrage.store.Store),
so a directory can answer the reading surface that a database answers and every
bulk operation between the two can become a copy.

**Registered in** `outrage.store._BACKENDS` under `files`, and
**nameable rather than inferable**. Which backend keeps a store otherwise
follows from its file extension, and a tree has no extension to read -- so this
is the backend a mount has to ask for, as `--mount export=tree,type=files` or
the `type` of an entry in `mounts.toml`. That is what the option grammar in
[`outrage.mounts.parse_spec()`](mounts.md#outrage.mounts.parse_spec) exists for.

Two ways in, because there are two kinds of caller.
`__init__()` is overridden to take the tree
itself: an export target is an absolute path somebody typed, and
[`outrage.store.store_file()`](store.md#outrage.store.store_file) refuses those, correctly, for the store file it
is about. [`FilesystemStore.in_directory()`](#outrage.store_files.FilesystemStore.in_directory) is the other, and it is the
base's rule unchanged -- a mount is a name relative to `--dir` like every
other store, and a tree mounted from a table has to obey exactly the refusals
a database mounted beside it obeys.

## What it costs

Every subtree read is a **walk**, per call, with nothing kept between them.
A sorted depth-first descent produces global key order without materialising
the tree, because [`outrage.keys.sort_form()`](keys.md#outrage.keys.sort_form) is per segment and delimiter
joined, so a parent's sort form prefixes every descendant's: at each directory,
emit the key's own document, then its metadata, then its subkeys, children in
segment order. Ranges, subtrees and cursors are filters over that stream.

It is O(n) per read of a subtree, which is the wrong shape for a large corpus
and the right one for what this backend is for -- an export target, a working
copy, a tree under review. The fix, if a tree ever holds enough to want one, is
a resident index like `outrage.store_parquet.ParquetStore._index`, not a
second definition of what the order is. The same paragraph is in
[`outrage.store.Store.last_child()`](store.md#outrage.store.Store.last_child) for the same reason: a cost worth paying
should be written down where it is paid.

**A character count is not a byte count**, so a page's `total_chars` and an
entry's `size` are answered by decoding a file rather than by its size on
disk. A walk that has to report either reads what it walks.

## Where it diverges from the contract, deliberately

Three, each covered by a test that says so:

* **\`\`.\`\` and \`\`..\`\` as whole segments are legal keys and impossible paths.**
  They are refused on write, with [`UnmappableError`](bulk.md#outrage.bulk.UnmappableError), and
  cannot occur on read.
* **A key that would land outside the tree is refused**, which is the same
  refusal one directory up: see [`outrage.bulk.contained_path()`](bulk.md#outrage.bulk.contained_path).
* **A file holding bytes that are not UTF-8 text is not a document.** The walk
  passes over it and [`FilesystemStore.check_file()`](#outrage.store_files.FilesystemStore.check_file) reports it; reading it
  by name says so rather than returning something mangled.

Everything else is the contract as `tests/test_store.py` states it, including
the root document, which is the file named by its extension alone at the top of
the tree -- `.md` -- and closes the export gap `planned/root-key` left.

### outrage.store_files.DEFAULT_TREE_NAME *= 'documents'*

What a tree is called when a caller names a store directory and no tree
inside it, so that `.outrage/documents/` sits beside `.outrage/store.sqlite`
the way two store files would. A name rather than the directory itself: the
store directory holds shared infrastructure -- the event log, the backups --
and a tree that *was* that directory would read them back as documents.

### outrage.store_files.FORMAT_VERSION *= 1*

The version of this layout. The layout **is** the format, so there is no
marker in the tree recording it and [`FilesystemStore.stored_format_version`](#outrage.store_files.FilesystemStore.stored_format_version)
answers with this rather than reading one. See
[`FilesystemStore.stored_format_version()`](#outrage.store_files.FilesystemStore.stored_format_version).

### *class* outrage.store_files.FilesystemStore(root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None, hidden: [bool](https://docs.python.org/3/library/functions.html#bool) = True, create: [bool](https://docs.python.org/3/library/functions.html#bool) = True, mount_point: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)

Bases: [`FileStore`](store.md#outrage.store.FileStore)

A document store kept as a directory of files.

#### default_filename *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[str](https://docs.python.org/3/library/stdtypes.html#str)]* *= 'documents'*

What this backend calls its store file when a caller names none. Set by
every concrete backend, and the only thing about the file a backend
decides: that it *is* a file inside a directory is settled above, by
`store_file()`. `default_store_file()` is how the rest of the
package asks for it without naming a backend to ask.

#### backend_name *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[str](https://docs.python.org/3/library/stdtypes.html#str)]* *= 'files'*

What this backend is called where a report or a refusal has to name it.
A short lowercase word, matching the store file's extension, so that a
sentence about a store and the name of its file agree.

#### format_version *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[int](https://docs.python.org/3/library/functions.html#int)]* *= 1*

The version of its own on-disk format this build writes. Compared
against [`stored_format_version`](#outrage.store_files.FilesystemStore.stored_format_version) by [`outrage.maintenance.check()`](maintenance.md#outrage.maintenance.check),
which is why the comparison is written once rather than per backend --
"written by a newer outrage than this" is the same fault whatever wrote it,
even though each backend records the number somewhere different.

#### writable *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[bool](https://docs.python.org/3/library/functions.html#bool)]* *= True*

Whether this backend can be written at all. False says the *storage*
refuses, which is not the same as a store that was mounted read-only:
a mount's refusal comes off with a flag and this one does not. A caller
deciding whether to offer a write reads this; a caller that writes
anyway gets `ReadOnlyStoreError` from the backend, since a class
var nobody consulted must not be the only thing standing between a
corpus and a half-written file.

#### close() → [None](https://docs.python.org/3/library/constants.html#None)

Nothing to release: a file is opened per read and closed by it.

An honest no-op rather than an omission. A caller is entitled to say it
has finished with a store without knowing which backend it holds.

#### located(key: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/library/constants.html#None)

The file `key` is kept in, which for this backend is the store.

The base answers None, because a row in a database has no file of its
own. Here every key has one and the mapping is public, so a transfer
into a tree reports key to path -- which is what an export has always
printed and the reason [`Transfer`](store.md#outrage.store.Transfer) carries a path
at all.

The path a write *would* take, whether or not anything is there yet: a
report of a copy is about where each document lands. None where that
path would leave the tree, which is `_readable()`'s answer rather
than a refusal, since a report is not the place to raise.

#### store_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), content: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, title: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, encoding: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, updated_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)

One file per key, written whole, with the title written beside it.

No transaction. A filesystem has none to offer, and pretending
otherwise by writing to a staging directory and renaming would buy
atomicity for the *pair* while a concurrent reader of the tree can see
either file at any moment anyway. What is atomic is each file, which is
`outrage.bulk._write_file()`'s `os.replace`: a write interrupted
halfway leaves whole files and no half of one.

#### delete(key: [str](https://docs.python.org/3/library/stdtypes.html#str), recursive: [bool](https://docs.python.org/3/library/functions.html#bool) = False, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, unchanged_since: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

Unlink the files the selection names, then prune what that emptied.

`dry_run` names them and unlinks nothing, from the same selection.

The selection is the other backends' exactly: a metadata key is itself
alone, a document key takes its metadata with it, and descendants come
too only when `recursive` says so. `key_range` bounds both halves.

**A directory left empty is removed**, up to the tree's own root. An
empty directory is not a key -- nothing is below it, so nothing puts it
in a listing -- and leaving one behind would make a delete visible in
the shape of the tree without being visible in the namespace.

The watermark is checked before the first `unlink`, which is the only
place it can be: unlinking is not undoable and there is no transaction
here to abandon.

A tree's timestamps are the filesystem's, so a watermark compared
against one is comparing against an mtime rather than against something
this store wrote. Touching a file is a change here and would not be in
a database -- which is the honest reading for a tree a person edits.

#### exists(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [bool](https://docs.python.org/3/library/functions.html#bool)

Whether a file holds `key`, asked of the path rather than a walk.

The one read that does not decode: a file that is there but is not text
is still a file, and this question is about the key being taken.

#### level_entry(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Entry](store.md#outrage.store.Entry) | [None](https://docs.python.org/3/library/constants.html#None)

The file if there is one, else whether the directory holds anything.

The second half is not "does the directory exist": an empty directory
is not a key, and one is what a hand edited tree or an interrupted run
leaves behind. It descends until it finds a row and stops there.

#### descendant_count(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [int](https://docs.python.org/3/library/functions.html#int)

What a plain delete of `key` would keep, counted over a walk.

Everything below `key`, less the metadata unit a non-recursive delete
takes with it -- which is why a document's own title has never counted
here. `whole_subtree` keeps that unit, which is the walk itself and
no subtraction at all. See [`outrage.keys.meta_range()`](keys.md#outrage.keys.meta_range).

Unmeasured: a count has no use for a document's length, and measuring
would make asking how much is below a key cost reading all of it.

#### retrieve_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, offset: [int](https://docs.python.org/3/library/functions.html#int) = 0, byte_offset: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, length: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, pattern: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, occurrence: [int](https://docs.python.org/3/library/functions.html#int) = 0, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_MAX_CHARS) → [Excerpt](store.md#outrage.store.Excerpt)

One path lookup, one file read, and the shared slicing.

The slicing is `outrage.store._excerpt()`, unchanged: how `length`
and `max_chars` combine is the store's policy rather than this
backend's, and two backends that sliced differently would return
different documents for the same call.

A **byte** offset seeks: a document here is a file, and a file is the
one thing in this project that already knows how to start reading in
the middle. `_byte_read()` is that half.

#### list_keys(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[Entry](store.md#outrage.store.Entry)]

One directory, its files and its subdirectories together.

Real and implicit keys arrive from the same listing rather than from
two halves that have to be merged and cut together, which is the defect
the SQLite shape has to be careful about: a name in this directory is a
child whether a file holds it or a directory does.

The totals are over the level rather than over the page, so a cursor
does not reach them, and they cost a decode per document -- see the
module docstring on what a character count is.

#### get_documents(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_BULK_MAX_CHARS, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, max_total_chars: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[Excerpt](store.md#outrage.store.Excerpt)]

The selection, then the page cut out of it against the two caps.

The totals come from the selection and the page from the cursor into
it, which is the split every backend makes: a cursor moves as a caller
pages and must not reach `total`.

#### missing_meta_stats(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, window: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', sample: [int](https://docs.python.org/3/library/functions.html#int) = 0) → [MissingMeta](store.md#outrage.store.MissingMeta)

Documents carrying none of `meta_name`, over one window.

The window is measured where the document's metadata *would* have
sorted, not where the document itself does -- the contract says so, and
it is what makes a caller's windows tile. Synthesised the same way the
parquet backend synthesises it, from the same two pieces:
[`outrage.keys.meta_sort_suffix()`](keys.md#outrage.keys.meta_sort_suffix) for an ordinary key, and the
metadata's own sort form for the root, which contributes no segment for
a suffix to join onto.

#### keys_missing_meta(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

The same selection [`missing_meta_stats()`](#outrage.store_files.FilesystemStore.missing_meta_stats) counts, listed.

Shared rather than reimplemented, for the reason the other backends
share theirs: the survey, its count and the list of what it could not
see have to agree about what was in range, and two expressions of one
predicate are two chances to disagree.

#### *classmethod* in_directory(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, filename: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None, mount_point: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Self](https://docs.python.org/3/library/typing.html#typing.Self)

The tree `filename` names inside a store directory.

The base's rule, reached the long way round: this constructor takes the
tree itself, so the directory-plus-relative-name one is applied here
with [`store_file()`](store.md#outrage.store.store_file) and the result handed over as a
path. A mount is a name inside `--dir` whatever backend answers it,
and every refusal that rule makes -- an absolute path, a `..` out of
the directory -- is made for a tree as it is for a database.

`filename` of None is [`DEFAULT_TREE_NAME`](#outrage.store_files.DEFAULT_TREE_NAME), so a tree mounted
without a name sits beside the store files rather than being one.

#### opened_at(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [Self](https://docs.python.org/3/library/typing.html#typing.Self)

The tree at `path`, reading dotfiles the way this store does.

The base splits a path into a directory and a name within it, which is
what every other backend's constructor takes; this one's takes the
directory itself. `hidden` travels with it because the root document
*is* a dotfile: a copy opened without it would not see the key the
store it was copied from holds at the root, and would compare short
for a reason that is not a fault.

**A backup of a tree is a copy of its documents, not of its
directory.** Whatever the tree holds that is not a document -- a
symbolic link, a file that is not text, a name no key spells -- is
passed over, the same way every other read of this store passes it
over. [`check_file()`](#outrage.store_files.FilesystemStore.check_file) is what names those, and it is worth running
before trusting a backup of a tree somebody has been editing by hand.

#### *property* stored_format_version *: [int](https://docs.python.org/3/library/functions.html#int)*

This build's own, because the layout is the format.

There is nothing in the tree recording a version and nothing should
be: a marker file would be litter in an exported tree and a key that is
not a document, and it could only ever disagree with the layout the
files are actually in. Answering with [`format_version`](#outrage.store_files.FilesystemStore.format_version) says the
two cannot differ, which is true here and false for a file with a
header -- cf. "'Nothing to repair' and 'nothing to check' are not the
same sentence" in `planned/storage`.

#### audit_rows() → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[AuditRow](store.md#outrage.store.AuditRow)]

Every row the tree holds, in one walk.

`parent` is **derived** rather than read back, because a tree keeps
no denormalisation of it: a file's parent is the directory it is in, by
construction. So the parent check in
[`outrage.maintenance.check()`](maintenance.md#outrage.maintenance.check) cannot fire here, and that is a
property of the storage rather than a check being skipped.

#### check_file(report: [Report](maintenance.md#outrage.maintenance.Report)) → [None](https://docs.python.org/3/library/constants.html#None)

What only a tree can say about itself: the files that are not keys.

A database refuses a bad key at the point of writing, so every row in
one is a key. A directory takes whatever is put in it, and a tree is
meant to be edited by hand -- that is most of what it is for -- so the
faults worth reporting are the ones an editor can create: a name that
no key spells, two files claiming one key, and a file that is not text.

#### repair() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Repaired](maintenance.md#outrage.maintenance.Repaired)]

Nothing, and that is the honest answer rather than a silence.

A repair moves bytes about inside a file the storage owns. What
[`check_file()`](#outrage.store_files.FilesystemStore.check_file) finds here is not that: a file whose name is not a
key is somebody's file, and a store that quietly renamed or removed it
would be losing what it was asked to keep. Reporting it and leaving it
is the only answer that does not.

### *exception* outrage.store_files.NotTextError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)

Raised when a file in the tree does not hold UTF-8 text.

The store holds text. A file that is not text is reported rather than
mangled into it -- the same answer [`outrage.bulk.import_tree()`](bulk.md#outrage.bulk.import_tree) gives
for the same file, one layer up.
