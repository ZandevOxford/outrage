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

### *class* outrage.bulk.Check(file: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), record: [ExportRecord](#outrage.bulk.ExportRecord) | [None](https://docs.python.org/3/library/constants.html#None), previous: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None), changed_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, unchecked_code: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, unchecked_from: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, overwritten: [bool](https://docs.python.org/3/library/functions.html#bool) = False)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

What asking an exported file whether the store still holds it found.

Separate from the import that asks it, because a write's *content* and a
write's *check* need not be the same file: an exported path handed to a
write is a claim about what the edit was made against, and that claim is
useful apart from the bytes in the file.

#### file *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

The file whose record was asked, so a caller that got past this can
renew it -- see [`renew()`](#outrage.bulk.renew).

#### record *: [ExportRecord](#outrage.bulk.ExportRecord) | [None](https://docs.python.org/3/library/constants.html#None)*

The record that answered, or None when there was none to ask and
`overwrite` allowed the write regardless. None is what stops
[`renew()`](#outrage.bulk.renew) writing a claim about a key the file did not come from.

#### previous *: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)*

Characters the key held before the write, or None if it held nothing.
An empty document and no document are different things to have replaced.

#### changed_at *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

`updated_at` of what was there, for the sentence `overwrite` owes.

#### unchecked_code *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

Why no comparison was made, as a code, when `overwrite` allowed one to
be skipped. None when the comparison happened.

#### unchecked_from *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

The key the record named, when it named another one.

#### overwritten *: [bool](https://docs.python.org/3/library/functions.html#bool)*

Whether `overwrite` allowed a write the staleness refusal would have
stopped. Separate from `unchecked_code`: this one knows somebody's write
is being lost, and that one does not know anything.

### outrage.bulk.Document

One document as [`outrage.store_parquet.ParquetStore.build()`](store_parquet.md#outrage.store_parquet.ParquetStore.build) takes it:
key, content, the format or None to detect it, and the timestamp or None
for now. A tuple rather than a class because it is what a build consumes
and nothing holds one for longer than that.

alias of [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`str`](https://docs.python.org/3/library/stdtypes.html#str), [`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None), [`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)]

### outrage.bulk.DEFAULT_EXTENSIONS *= 'strip'*

The mode nothing else names, and the one every tree this package wrote is
in. A default rather than an argument each caller passes, because it is the
mapping as it has always been: `keep` is the thing somebody asks for.

### outrage.bulk.EXPORT_DIR_PREFIX *= 'outrage-export'*

The per-user directory exports live in, below [`tempfile.gettempdir()`](https://docs.python.org/3/library/tempfile.html#tempfile.gettempdir).
Not inside the store directory: one file per key there meant two sessions
editing one key shared one file, and the second export overwrote the first's
unimported edit. That is the collision that happens, and a per-user
directory outside the store is what stops it.

The uid is in the name because `gettempdir()` is shared between users on a
POSIX machine. Windows has no uid and its temporary directory is already per
user, so there the prefix is the whole name. That half is reasoned rather
than tested: this suite does not run on Windows.

### outrage.bulk.EXPORT_MAX_AGE *= datetime.timedelta(days=7)*

How long an export and its record are kept. Exports no longer overwrite one
another, so nothing else removes them: a sweep by age is what a name of its
own for every export costs. Seven days is John's call, 2026-09-02 - long
enough that an edit picked up after a weekend still has its record.

### outrage.bulk.CONTAINER_PREFIX *= '.!'*

What a directory holding the keys below a **document** is called under
`keep`, and the one thing in that mapping which is a convention rather
than the identity it otherwise is.

**The problem it solves.** A name in a directory is a file or a directory
and not both. Under `strip` the extension keeps a document and its
container apart -- `a.md` the file beside `a/` the directory -- and
under `keep` there is one name for the two, so a document could not carry
so much as a title. `document.md` keeps its own name and its keys live in
`.!document.md`, John's call of 2026-09-06.

**Which names get one cannot be decided by the name alone**, and that is the
one place this mapping consults the tree. `notes` the document and
`notes/` the bundle directory are the same string, so only what is there
says which: a segment whose *file* exists needs a container, and a segment
that is already a plain directory is a bundle's own structure and is left
alone. [`container_name()`](#outrage.bulk.container_name) is the answer where neither is there, which is
every write into empty space, and
`outrage.store_files.FilesystemStore._dir_for()` is where the tree gets
its say. What that buys is a bundle untouched -- `guide/intro.md` is still
`guide/intro.md`, and an export under `keep` is a tree somebody can
browse -- with no key left unwritable.

**Inside a container it is the ordinary mapping again**, John's call:
metadata keeps the extension its format names, so a title is
`.!document.md/!title.md` and the container's contents are what `strip`
would have written. Apart from the directory's own name the two
representations are the same, which is worth more than the identity would
have been -- an unextended `!title` is a file whose format nothing on disk
declares, and a listing, which does not open what it lists, would have to
answer that it does not know. It also means metadata with children needs no
container of its own: `!changelog.md` the file and `!changelog/` the
directory are two names, exactly as under `strip`.

**The entry type says which half it is.** A directory named `.!notes`
holds the keys below a document in the plain file `notes`; a file named
`.!notes` holds the document whose keys already occupy the plain directory
`notes`. That symmetry means either half can be written first without
moving a bundle's own directory. The leading dot keeps these out of a
bundle's ordinary listing; they are exempt from the dotfile skip for the
reason the root document is, since they are this package's own structure
rather than somebody else's.

### outrage.bulk.EXTENSION_BY_FORMAT *= {'html': '.html', 'json': '.json', 'markdown': '.md', 'text': '.txt'}*

The extension a document is written with, by stored format. Named for the
direction it maps in, because the inverse is right below it and a reader
reaching for one of the two should not have to check which is which. One
entry per member of [`outrage.store.FORMATS`](store.md#outrage.store.FORMATS), so nothing can be stored
that an export cannot name.

### outrage.bulk.EXTENSION_MODES *= ('strip', 'keep')*

How a file name and a key segment line up. `strip` is the mapping this
package writes: a document's format names its extension and an import takes
that extension off again, so `a/b` stored as markdown is the file
`a/b.md`. `keep` is identity -- a file name **is** a key segment,
extension included, so the same file is the key `a/b.md`.

**Why there is a choice.** Stripping is right for a tree this package wrote,
where the extension is its own doing and is how a format survives the round
trip. It is wrong for a documentation bundle somebody else wrote, where the
names are given and the documents *link to them*: strip them and every
relative link in the corpus names a key that is not there.

**What \`\`keep\`\` costs is what the extension was buying.** A key with no
extension is written to a file with none, so a format the key does not spell
does not round-trip -- `notes` stored as text reads back as markdown, which
is what `outrage.store._detect_format()` answers for prose -- and a key
that *does* spell one may not contradict the format being stored. The other
half, a key holding a document *and* the keys below it, is what
[`CONTAINER_PREFIX`](#outrage.bulk.CONTAINER_PREFIX) answers.

### *class* outrage.bulk.ExportRecord(key: [str](https://docs.python.org/3/library/stdtypes.html#str), content_sha256: [str](https://docs.python.org/3/library/stdtypes.html#str), exported_at: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, updated_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, store: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

What an export handed out, as the sidecar beside it records it.

A file rather than the filename or a table in the server process. The
filename caps the record at what fits, truncates the hash and loses the
check silently on a rename; a table dies with the server, and takes
[`export_document()`](#outrage.bulk.export_document) and [`import_document()`](#outrage.bulk.import_document)'s standalone usefulness
with it. A sidecar survives a restart, extends without a format change,
and when it is missing an import degrades to *not getting the check*
rather than to being wrong. John's call 1, 2026-09-02.

The fields are shaped for a precondition that may eventually live inside
`Store.store_document`, not for the comparison
below alone: the token is what a store-level precondition would take, and
it covers the body and nothing else, because that is exactly what a write
covers. **Unknown fields are ignored on read**, so a later writer can
record more without making the files an older reader must still import
unreadable.

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The key that was exported. An import to a *different* key is how content
is copied around the store, not an edit, so the comparison does not apply
to it -- see [`import_document()`](#outrage.bulk.import_document).

#### content_sha256 *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

Hex sha256 of the exported content as UTF-8. The token that decides.
Named for its algorithm rather than `hash` so a second one can be added
beside it rather than replacing it.

#### exported_at *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

When the export happened, UTC.

#### format *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

The document's stored format.

#### updated_at *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

What the document's `updated_at` was. **Recorded for the sentence, not
for the decision**: it is normalised to second precision, so two writes
inside one second are indistinguishable. The hash decides; this is what
makes a refusal readable by a person.

#### store *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

Where the store was, when it could be asked. Recorded and **not
enforced**: a file exported from one store and imported into another is a
copy between stores, which is a thing somebody may mean, and the record is
there so the answer can say it happened.

#### *static* path_for(file: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

Where the record for the export at `file` is kept.

#### write(file: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

Write this record beside the export at `file`.

#### *classmethod* read(file: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [ExportRecord](#outrage.bulk.ExportRecord) | [None](https://docs.python.org/3/library/constants.html#None)

The record beside the export at `file`, or None if there is none to read.

None rather than a raise for every way it can be absent - not there,
not JSON, not an object, missing a field this needs. A hand-written
file dropped into the export directory is still importable, as it was
before there were records at all, and an import that cannot read one
says so and proceeds.

#### followed(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), content: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [ExportRecord](#outrage.bulk.ExportRecord)

This record moved on to `content`, which `key` now holds.

What an import writes back. The record is a claim about *what the edit
was made against*, and an import that succeeds makes the file and the
document agree again -- so the claim is renewed rather than left
pointing at the state before the write.

`key` is the key this record already names: an import to a different
one is a copy, and rewriting the record would silently turn the file
into an edit claim on a key it did not come from.

### *class* outrage.bulk.Exported(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), excerpt: [Excerpt](store.md#outrage.store.Excerpt), record: [ExportRecord](#outrage.bulk.ExportRecord))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

What exporting one document did: where it went, and what was recorded.

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

The file written, a fresh one on every export.

#### excerpt *: [Excerpt](store.md#outrage.store.Excerpt)*

The document written to it, whole.

#### record *: [ExportRecord](#outrage.bulk.ExportRecord)*

What was written to the sidecar beside it.

### outrage.bulk.FALLBACK_PREFIX *= 'document-'*

What every export is named, an id and the format's extension and nothing
else. Not [`TEMP_PREFIX`](#outrage.bulk.TEMP_PREFIX), which marks a file that is half written and
that a reader must skip: this one is the export, and it is finished.

The name carries no slug of the key, deliberately: two sessions editing one
key must not collide on one filename, so the id is the whole of what
distinguishes an export and the sidecar is what makes a listing readable.

### outrage.bulk.FORMAT_BY_EXTENSION *= {'.html': 'html', '.json': 'json', '.md': 'markdown', '.txt': 'text'}*

The format a file name declares. Deliberately the inverse of
[`EXTENSION_BY_FORMAT`](#outrage.bulk.EXTENSION_BY_FORMAT) and nothing more: the extensions an export
writes are the extensions an import strips, so a file named myfile.py
keeps its name and becomes the key myfile.py rather than losing a suffix
nothing here put there. That is why there is no .htm and no .text, close
as they are -- an export never writes one, so an import reads it as part of
the name. Not to be confused with [`outrage.store.FORMATS`](store.md#outrage.store.FORMATS), which is what
a document may be *stored* as; this is what a file name says it is.

### *class* outrage.bulk.Imported(key: [str](https://docs.python.org/3/library/stdtypes.html#str), stored: [int](https://docs.python.org/3/library/functions.html#int), previous: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None), unchecked_code: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, unchecked_from: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, unedited: [bool](https://docs.python.org/3/library/functions.html#bool) = False, copied_from: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, overwritten: [bool](https://docs.python.org/3/library/functions.html#bool) = False, changed_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, contents_key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)

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

#### unchecked_code *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

Why the document was not compared with what was exported, as a code --
[`UNCHECKED_NO_RECORD`](notes.md#outrage.notes.UNCHECKED_NO_RECORD) or
[`UNCHECKED_OTHER_KEY`](notes.md#outrage.notes.UNCHECKED_OTHER_KEY) -- or None when it was compared.
A missing record and a cross-key import both land here: the write happens
either way, and the caller is told the check did not.

A code rather than a sentence, because the layer that noticed does not know
who is reading. A front end words it: see [`outrage.messages`](messages.md#module-outrage.messages).

#### unchecked_from *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

The key the record named when it named another one, which is the fact
[`UNCHECKED_OTHER_KEY`](notes.md#outrage.notes.UNCHECKED_OTHER_KEY)'s sentence needs. About the *checking* file, so
it is not `copied_from`: with `against` the two are different files and
may name different keys.

#### unedited *: [bool](https://docs.python.org/3/library/functions.html#bool)*

Whether the file is byte-identical to what the export handed out, so the
edit matched nothing. Not a refusal - storing an unchanged document is
harmless - but it is a call that looks like a write and stored the document
the store already had, and the record closes that for free.

#### copied_from *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

The key the content file was exported from, when that is not the key
written, and None for a round trip. What it is for is `unedited`: an
unedited file put back where it came from changed nothing, and the same
file imported to another key is a copy, which changes that key however
little the file moved. One flag, two true sentences.

#### overwritten *: [bool](https://docs.python.org/3/library/functions.html#bool)*

Whether `overwrite` allowed a write this check would have refused.

#### changed_at *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

What the displaced document's `updated_at` was, for the sentence that
says what `overwrite` overwrote. None when the key held nothing.

#### contents_key *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

Where an automatically generated contents index was stored, or None
when generation was disabled or did not apply to this key and format.

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

### outrage.bulk.RECORD_SUFFIX *= '.outrage.json'*

What is written beside an export to record what was handed out, read back by
an import. [`ExportRecord`](#outrage.bulk.ExportRecord) is the format, and what it has to answer
is what key the file came from, what was in it, and when.

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

### *exception* outrage.bulk.ExportRootError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError)

Raised when the directory exports would go in is not safely this user's.

### *exception* outrage.bulk.FileMissingError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`FileNotFoundError`](https://docs.python.org/3/library/exceptions.html#FileNotFoundError)

Raised when the file to import one document from is not there.

### *exception* outrage.bulk.OverlappingCopyError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)

Raised when a copy would write into the subtree it is still reading.

### *exception* outrage.bulk.SourceMissingError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`FileNotFoundError`](https://docs.python.org/3/library/exceptions.html#FileNotFoundError)

Raised when the directory to import from is not there.

### *exception* outrage.bulk.StaleImportError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError)

Raised when the document changed after the file being imported came out.

The lost-update problem, refused rather than reported: two agents editing
one key are both doing something reasonable, so a guard aimed at them
cannot be advisory. `overwrite` is what keeps the refusal from being a
hard bound - the caller who has looked and meant it has one word to say so.

### *exception* outrage.bulk.UncheckedWriteError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError)

Raised when there is no record naming this key, so nothing can be checked.

The other way a write can be unsafe, and John's call 2026-09-02: the two
are one rule, because a write nobody could check is the *less* informed of
the pair and must not therefore be the more permissive. A record that names
another key and no readable record at all both land here.

Both refusals lift with the same `overwrite`, which says "I have looked,
write it anyway" once rather than twice. What lifting it costs is different
in each case, so the message says which refusal it was.

### *exception* outrage.bulk.UnmappableError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)

Raised when a key has no file it can be written to, or a file no key.

### outrage.bulk.check_extensions(extensions: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

`extensions` back, or say that it names no mapping.

Here rather than in the store that takes it, because the modes are the
mapping's and this is where the mapping lives. Checked at all for the
reason `outrage.store._backend_for()` refuses a `type` nobody
recognises: a mode is *asked for* rather than guessed at, and one that fell
back to the default would mount a tree whose keys are not the keys the
caller asked for and read as simply the wrong store.

### outrage.bulk.check_write(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, storing: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Check](#outrage.bulk.Check)

Refuse a write to `key` unless `path` says what it was made against.

`path` is an exported file, resolved inside `root` by the one
containment rule [`contained_file()`](#outrage.bulk.contained_file) holds. Its **record** is read and
its content is not: what the write stores comes from somewhere else, and
this answers only *has the document moved since that file came out*.

Two refusals, and `overwrite` lifts either:

* [`UncheckedWriteError`](#outrage.bulk.UncheckedWriteError) when there is no record naming `key` to
  ask -- no readable record beside the file, or one that names the key it
  was exported from rather than the key being written.
* [`StaleImportError`](#outrage.bulk.StaleImportError) when the record answers no: somebody has
  written the document since, and this write would lose their work.

`storing` is the file whose content is being written, when one is, and
exists for the **message** alone: the file that checks a write and the file
that supplies it are no longer the same thing, so a refusal that named one
of them as the other would send a reader to look at the wrong file. Left
out when the content came from the call rather than from any file.

What it is not is a compare-and-swap. The comparison happens here, between
a read and a write, so two writers in the same instant both pass. A real
precondition would have to live inside `Store.store_document`, and does
not yet.

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

### outrage.bulk.container_name(segment: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

What holds the keys below `segment` under `keep`, where nothing is there yet.

The default rather than the rule: a name carrying an extension is a
document in every bundle worth reading, so its keys are given a container
at once; anything else is assumed to be structure and keeps a plain
directory. A tree that already answers the question overrides this -- see
[`CONTAINER_PREFIX`](#outrage.bulk.CONTAINER_PREFIX) and
`outrage.store_files.FilesystemStore._dir_for()`.

Metadata is not special here. It carries the extension its format names, so
`!changelog.md` the file and `!changelog/` the directory are two names
and need no third.

```pycon
>>> container_name("guide.md"), container_name("!changelog.md")
('.!guide.md', '.!!changelog.md')
>>> container_name("guide"), container_name("!changelog"), container_name("22")
('guide', '!changelog', '22')
```

### outrage.bulk.content_hash(content: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

The token a record carries: hex sha256 of `content` as UTF-8.

A hash rather than the length, which is a weak token: a substitution that
keeps the length is exactly the edit a careless script makes. This costs one
read an import already makes.

### outrage.bulk.copied(source: [Store](store.md#outrage.store.Store), target: [Store](store.md#outrage.store.Store), subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = store.EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = store.UNBOUNDED, prefix: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, reroot: [bool](https://docs.python.org/3/library/functions.html#bool) = False, on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str) = SKIP, unchanged_since: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Generator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Generator)[[Transfer](store.md#outrage.store.Transfer), [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]

Every document `subtree` names, from one store into another.

What [`outrage.store.Store.copy_from()`](store.md#outrage.store.Store.copy_from) does unless a backend has a
better way, and it is called through that rather than directly: a caller
naming both ends in one breath cannot be overridden by the end that knows
how it is written. Here because the walk is here -- a store's own reads
are pages and this is the caller that legitimately wants all of them.

Read with [`outrage.store.read_all()`](store.md#outrage.store.read_all) rather than through
`get_documents`, because a
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

`unchanged_since` says when the caller looked at the far end, and it is
what keeps `OVERWRITE` from covering two intentions at once --
replacing the stale copy they meant to replace, and replacing the edit
somebody made while they were deciding. Two layers, and they answer
different questions:

* **Before anything crosses**, the landing zone is asked whether it moved
  since. If it did, the run is refused having written nothing, which is the
  one outcome better than a copy that stops half way through.
* **Then at each collision**, under `OVERWRITE_UNCHANGED`, the key
  itself is measured against the watermark again. What has moved is left
  alone and reported as `CHANGED` rather than folded in with the
  ordinary skips, so an empty list means the copy was clean and three keys
  name three documents to go and look at.

Skipping rather than refusing is deliberate at the second layer, and the
opposite call to the first: a mid-run refusal leaves the copy half done and
the caller reasoning about a cursor, where skipping completes the copy,
loses nothing, and hands the awkward case back.

### outrage.bulk.declared_format(name: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)

The format a file name's extension declares, or None for one that does not.

```pycon
>>> declared_format("a.md"), declared_format("a.py"), declared_format("a")
('markdown', None, None)
```

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

### outrage.bulk.documents_from_tree(source: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, hidden: [bool](https://docs.python.org/3/library/functions.html#bool) = False, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) = DEFAULT_EXTENSIONS) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Transfer](store.md#outrage.store.Transfer), [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)] | [None](https://docs.python.org/3/library/constants.html#None)]]

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

Write the document at `key` to a fresh file under `root`, whole.

The whole document rather than a slice, which is the only readable size: a
slice edited and imported back is a silent truncation of everything the
read stopped short of.

A file of its own every time, with [`ExportRecord`](#outrage.bulk.ExportRecord) beside it saying
what was handed out, so [`import_document()`](#outrage.bulk.import_document) can tell whether the store
still holds what the edit was made against. Nothing is overwritten here:
one file per key would mean a second session's export destroying the
first's unimported edit.

### outrage.bulk.export_root() → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

This user's export directory, created if it is not already there.

A stable directory swept by age rather than a fresh one per server process,
which is John's call 3, 2026-09-02: a restart mid-edit must not strand the
file, because the session that comes back is the one that wanted it. What
it costs is that files accumulate, which [`sweep_exports()`](#outrage.bulk.sweep_exports) answers.

Created `0700` and, when it is already there, **required to be a
directory, ours, and not a symbolic link** - refused rather than written
into otherwise. `gettempdir()` is shared between users on a POSIX
machine, so a directory at a name another user could have pre-created is
the one new risk moving out of the project took on.

### outrage.bulk.export_tree(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), target: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str) = SKIP, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) = DEFAULT_EXTENSIONS) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Transfer](store.md#outrage.store.Transfer)]

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

`extensions` is how a key becomes a file name -- see
[`EXTENSION_MODES`](#outrage.bulk.EXTENSION_MODES). An export under `keep` writes each document's
key as it is spelled, which is what a tree meant to be *linked into* wants:
the cost is that a **document** whose key spells no extension is written to
a file with none, and so comes back as markdown. Metadata is unaffected --
it is written the ordinary way inside [`CONTAINER_PREFIX`](#outrage.bulk.CONTAINER_PREFIX).

`FilesystemStore` is imported here rather than at the top of the module
because it is written in terms of this one -- the mapping lives here and
the store is expressed in it, not the other way round.

### outrage.bulk.file_name(segment: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)

What the file holding `segment`'s own document is called, under `keep`.

The segment itself, which is the whole of the mode -- except for metadata,
which takes the extension its format names because nothing in a bundle
links to it and a format nothing declares is a format lost.

```pycon
>>> file_name("guide.md"), file_name("notes"), file_name("!title")
('guide.md', 'notes', '!title.md')
>>> file_name("!contents", "json")
'!contents.json'
```

### outrage.bulk.import_document(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, against: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False, generate_contents: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Imported](#outrage.bulk.Imported)

Store the content of `path` at `key`, and say what it displaced.

`path` must be inside `root`, which is the whole of the security check:
a tool that stored any file the caller named would read anything the server
can read.

**A relative \`\`path\`\` is relative to \`\`root\`\`**, not to the working
directory: it is relativised before it is checked, so the containment rule
is asked once.

**The key and the path do not have to agree.** The content is stored where
the caller says, whatever file it came from, which is what makes an export,
an edit and an import to a second key a way of copying content around the
store.

**A write that cannot be checked is refused**, and so is one the check
fails - see [`check_write()`](#outrage.bulk.check_write), which is where both refusals and the
`overwrite` that lifts them live. By default the check is asked of
`path`'s own record, which answers only when the file came out of the key
being written.

**\`\`against\`\` is where the check comes from when the content is not.** It
is a second exported file, exported *from* `key`, and only its record is
read. That is what makes export A, edit, import to B safe: the content
comes from A's file and the claim about B comes from B's. Without it the
cross-key route has no claim to make and goes unchecked.

An empty file is stored rather than refused - emptying a document is a
thing a person may legitimately mean. What guards the accident is the
report: both sizes come back, so an edit script that truncated is visible
to whoever asked.

`generate_contents` asks a Markdown or HTML document to carry a fresh
heading index in `!contents` as part of the same store call. Metadata
keys and formats without a heading index are left alone. It defaults off
here because this is a general import API; the editing tool opts in by
default so an edited document cannot silently keep a stale index.

### outrage.bulk.import_tree(opened: [Store](store.md#outrage.store.Store), source: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str) = SKIP, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, hidden: [bool](https://docs.python.org/3/library/functions.html#bool) = False, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) = DEFAULT_EXTENSIONS) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Transfer](store.md#outrage.store.Transfer)]

Store every file below `source`, keyed by its path under `key`.

The inverse of [`export_tree()`](#outrage.bulk.export_tree) and the same operation: a copy *out of*
a directory of files into a store. Yields a `Transfer` per file as it
goes.

`hidden` is whether a dotfile is a document. False by default, which is
the policy for a **foreign** tree -- one this package did not write, where
a `.git` or a `.DS_Store` is not a document and importing it as one is
a surprise. The root document is exempt either way, since it is named by
its extension alone.

`extensions` is the other half of that policy and the same argument --
see [`EXTENSION_MODES`](#outrage.bulk.EXTENSION_MODES). A foreign bundle whose documents link to each
other by file name imports under `keep`, so that a link already in the
corpus names the key that holds it.

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

### outrage.bulk.key_for_path(relative: [PurePosixPath](https://docs.python.org/3/library/pathlib.html#pathlib.PurePosixPath) | [str](https://docs.python.org/3/library/stdtypes.html#str), prefix: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) = DEFAULT_EXTENSIONS) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]

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

Under `extensions="keep"` the name is the key segment, whole. The
**format is still read off the extension** -- what changes is the key, not
what the file says it holds -- and a directory named for
[`CONTAINER_PREFIX`](#outrage.bulk.CONTAINER_PREFIX) gives back the segment it holds the keys below.
Metadata is the exception in both directions: it is written with an
extension and so has one taken off again, which is what makes a container's
contents read exactly as `strip` wrote them.

```pycon
>>> key_for_path("a/b.md", extensions="keep")
('a/b.md', 'markdown')
>>> key_for_path("a/.!b.md/!title.md", extensions="keep")
('a/b.md/!title', 'markdown')
>>> key_for_path("a/.!b.md/chapter", extensions="keep")
('a/b.md/chapter', None)
```

A final *file* named for that prefix is the symmetric collision spelling:
`.!notes` is the document at `notes` when the plain `notes/`
directory already holds its children. In an earlier component the same
spelling is a directory, and therefore the container below that document.

### outrage.bulk.levels(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Entry](store.md#outrage.store.Entry)]

One level, a page at a time, to the end.

The store pages and the command line does not: a person listing a key wants
the level, and a listing that stops at an internal page size is the silent
partial answer this project keeps finding. Streaming is what makes it both
complete and bounded in memory - and it fails better, since a long listing
interrupted has already shown its first thousand lines rather than nothing.

### outrage.bulk.new_export_file(root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

A file under `root` for one export, and for nothing that came before it.

An id and the format's extension, with **no slug of the key in it**: John's
call, 2026-09-02. A name derived from the key stops two *keys* colliding
and does nothing about two *agents* colliding, which is the collision that
happens.

`mkstemp` for the guarantee that the name is free - the mechanism the
unnameable-key fallback already used, promoted from the exception to the
only path. The extension stays because with the key and the path free to
disagree, the path is the only thing left that says what the content is.

What this costs is discoverability, and it is accepted: a person can no
longer work out where a key's export is. The export result carries the
path, and [`ExportRecord`](#outrage.bulk.ExportRecord) is what makes a directory of ids readable
after the fact - every file has one, and it names the key.

### outrage.bulk.notes_for(imported: [Imported](#outrage.bulk.Imported)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]

Every situation [`import_document()`](#outrage.bulk.import_document) reached that is worth remarking on.

One place, front end agnostic, deciding *which* situations arose and never
how to say them: each is a [`Note`](notes.md#outrage.notes.Note), a code and the
facts its sentence will need, and a wording table turns it into words for
whoever is reading.

**Why this is not left to each front end.** It was, and that is where the
worst of these defects came from. The branch below on `unedited` and
`copied_from` lived in the MCP server, so the command line neither had it
nor could have got it right independently -- and when the server had only
`unedited` to go on it called a verbatim cross-key copy an edit that
changed nothing, beside its own `previous` and `stored` saying the
document had grown. One flag, two true sentences: the pair is decided here
once, where a test can point at it, rather than in a conditional that only
one caller has.

The order is the order a reader meets them, and it is not arbitrary. What
a write destroyed comes before what it stored, because the first is the
thing somebody may have to go and recover.

### outrage.bulk.notes_for_checked_write(key: [str](https://docs.python.org/3/library/stdtypes.html#str), check: [Check](#outrage.bulk.Check), stored: [int](https://docs.python.org/3/library/functions.html#int)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]

The same, for a write whose content did not come from a file.

`store_document` takes `against` and gets the staleness refusal without
handing back a file, so what it has afterwards is a [`Check`](#outrage.bulk.Check) and the
size it wrote rather than an [`Imported`](#outrage.bulk.Imported). The situations are the ones
any write past a check reaches; there is no file, so nothing here can be a
copy or a no-op.

`stored` is passed rather than read off the check because the check
happens *before* the write, and on the encoded path what was stored is not
the length of what arrived.

### outrage.bulk.notes_for_copy(landing: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool), on_conflict: [str](https://docs.python.org/3/library/stdtypes.html#str), unchanged_since: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), changed: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)], next_cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), limit: [int](https://docs.python.org/3/library/functions.html#int), failed: [int](https://docs.python.org/3/library/functions.html#int), named: [int](https://docs.python.org/3/library/functions.html#int), stopped: [bool](https://docs.python.org/3/library/functions.html#bool), mounts_kept: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]

The same for a copy, which has more ways to do less than it was asked.

A copy reports counts, and a count cannot say that the run stopped early,
that a page of it was refused, or that the failures beside it are a sample.
Six situations, in the order a reader meets them: what did not happen at
all, then what was left behind, then where to carry on from, then what the
numbers are not telling them.

`landing` is where the documents actually arrive, which under a graft is
not the target key, and it is the key a refusing mount has to be named
against. `named` is how many failures the answer spells out, against
`failed` for how many there were. `on_conflict` decides only whether
the advice can be followed as it stands: a watermark refuses to be handed
to the plain overwrite rule, so a dry run under that rule has to point at
the narrowed one instead.

### outrage.bulk.notes_for_delete(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool), remaining: [int](https://docs.python.org/3/library/functions.html#int), mounts_kept: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]

What a delete has to remark on, which is all about what it left standing.

`deleted` and its count describe what went, and nothing in them describes
what stayed -- so an answer to a call that removed a fraction of what the
caller meant reads exactly like an answer to one that removed all of it.
Each note here names a different way that happens.

The facts are passed rather than taken off a result, because a delete's
answer is the store's and says only what it did: `remaining` is what lies
below `key` after a delete that was not recursive, and `mounts_kept`
names read-only mounted stores below it, which are not keys and so are
counted by nothing. `key` is the caller's own spelling, echoed back so
that the advice to try again names the call they made.

### outrage.bulk.notes_for_export(exported: [Exported](#outrage.bulk.Exported)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]

What handing a document out as a file has to remark on.

One note, and the only one in this module that is not a discovery: an
export always has the same thing to say, because what is worth saying is
what happens *next*, and a file handed over with nothing said about it
reads as the answer rather than as half of a round trip.

It is derived here anyway, with the others, so that emitting a note is one
thing a front end does rather than two -- a table it asks, and a sentence
it may write for itself. The exported document is taken and not read for
the same reason: this is a note about a result, and a caller should not
have to know which of these need the result to decide.

### outrage.bulk.notes_for_write(previous: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None), stored: [int](https://docs.python.org/3/library/functions.html#int)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]

What a write with nothing to check it against has to remark on.

The write a command line makes: no export record, so nothing here can be a
copy, a silent no-op, or a write that went past a check somebody lifted.
What is left is the arithmetic, and on that front end it is the one that
matters most -- `outrage get > file`, edit, `outrage set --file` is the
documented way to change a long document from a shell, and the first use of
it wrote an empty document over a good one.

`previous` is [`size_of()`](#outrage.bulk.size_of)'s answer, so `None` means the store could
not say rather than that there was nothing there.

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
  reaches, and the rule is deliberately not widened to cover it.
* **re-rooted**, the source key is stripped, so every key lands beneath
  `target` alone and the two subtrees have to be disjoint. `a/b`
  re-rooted onto `a` sends `a/b/b/x` to `a/b/x` -- back inside the
  walk it came from, and later in the order than the key being read.

Called by a front end before the copy starts, so that the refusal is a
refusal rather than an exception raised out of a generator half way
through. Both front ends call this one, because the command line and the
server disagreeing about which copies are allowed is exactly the split
`mounts.toml` was made to avoid.

### outrage.bulk.pack(target: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], documents: [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Transfer](store.md#outrage.store.Transfer), [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)] | [None](https://docs.python.org/3/library/constants.html#None)]], \*, overwrite: [bool](https://docs.python.org/3/library/functions.html#bool) = False, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False, byte_lengths: [bool](https://docs.python.org/3/library/functions.html#bool) = True) → [Iterator](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[Transfer](store.md#outrage.store.Transfer)]

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

### outrage.bulk.path_for_key(key: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) = DEFAULT_EXTENSIONS) → [PurePosixPath](https://docs.python.org/3/library/pathlib.html#pathlib.PurePosixPath)

The relative path `key` is written to, extension included.

```pycon
>>> path_for_key("a/b", "markdown"), path_for_key("a/b", "json")
(PurePosixPath('a/b.md'), PurePosixPath('a/b.json'))
>>> path_for_key("a/b", "text"), path_for_key("a/b", "html")
(PurePosixPath('a/b.txt'), PurePosixPath('a/b.html'))
>>> path_for_key("a/b/!title")
PurePosixPath('a/b/!title.md')
```

Under `extensions="keep"` the last segment is the file name, so nothing
is appended and a key already carrying an extension keeps exactly the one
it has -- except metadata, which takes its format's extension because
nothing links to it. Segments above it name directories, by
[`container_name()`](#outrage.bulk.container_name):

```pycon
>>> path_for_key("a/b.md", "markdown", extensions="keep")
PurePosixPath('a/b.md')
>>> path_for_key("a/b", "text", extensions="keep")
PurePosixPath('a/b')
>>> path_for_key("a/b.md/!title", None, extensions="keep")
PurePosixPath('a/.!b.md/!title.md')
>>> path_for_key("a/b.md/!changelog/22", None, extensions="keep")
PurePosixPath('a/.!b.md/!changelog/22')
```

**This is the answer for a tree that says nothing else.** Whether an
extensionless segment holds a document -- and so needs a container rather
than a plain directory -- only the tree can answer, and
`outrage.store_files.FilesystemStore._dir_for()` is what asks it. A
store resolves a path through that and falls back to this.

A key whose extension **contradicts** the format being stored is refused
there, rather than writing a file whose name says one thing and whose
content is another -- which would read back as what the name said.

The root is the exception in both modes, and has to be: it has no segments
to be a path, so its file is named by the extension alone.

### outrage.bulk.renew(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str), check: [Check](#outrage.bulk.Check), content: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [None](https://docs.python.org/3/library/constants.html#None)

Move `check`'s record on to what `key` now holds, after the write.

Without this the tool is one edit per export: the *next* write checked
against the same file is refused against a change this call made, and an
agent that hits that refusal on its own second write learns to pass
`overwrite`, which is the guard being thrown away.

Does nothing when there is no record to renew, which is the unchecked write
`overwrite` allowed through: the file did not come from `key` and must
not start claiming it did.

`content` is what was written, when the caller already has it. Otherwise
the document is read back -- which is what a write that transformed what it
was given needs, since the record hashes what the store holds.

### outrage.bulk.size_of(opened: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)

What `key` holds, in characters, or None when it holds nothing.

The cheap read, for the paths that do not need the content: an empty
document and no document are different things to have overwritten, and the
report distinguishes them. `None` also comes back from a store that
cannot answer without reading the document, so a caller measuring a write
against what was there has to treat it as "not known" rather than as zero.

### outrage.bulk.sweep_exports(root: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], max_age: [timedelta](https://docs.python.org/3/library/datetime.html#datetime.timedelta) = EXPORT_MAX_AGE, now: [datetime](https://docs.python.org/3/library/datetime.html#datetime.datetime) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [int](https://docs.python.org/3/library/functions.html#int)

Remove exports and records under `root` older than `max_age`, and count them.

**An export and its record age together**, by the newer of the two: a file
edited days after it came out is still being worked on, and sweeping the
record out from under it would cost exactly the check it is there for.

Best effort throughout - a file that cannot be stat'd or removed is left
alone rather than raising. This runs on the way to an export, and failing
that export because somebody else's leftovers are unreadable would be a
worse answer than leaving them there.

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
namespace and there may be documents inside it. Stopping at one, on the
reading that metadata is a leaf, drops `a/!x/y` from an export without
saying so. The shape on disk is the ordinary
document-with-children one -- `!x.md` beside the directory `!x/` --
which is what `FilesystemStore` already writes.
