# outrage.mounts

Routing one key namespace across more than one backing store.

A mount table maps a key prefix to a [`Store`](store.md#outrage.store.Store). The longest
prefix matching a key owns it, exactly the way a filesystem mount table works,
and the root mount owns everything no other mount claims -- so every key
resolves, and the single store case is just a table with one entry.

Two translations happen at the boundary and nothing else does:

* **inward**, a key loses the prefix of the mount that owns it, so the mounted
  store is asked about a key in its own namespace and never learns where it was
  mounted. That is what makes a store relocatable: the same database answers
  the same way at `ref` as at `lib/ref`.
* **outward**, every key a mounted store returns regains that prefix, so a
  caller only ever sees the one namespace.

The mount point itself is the inner store's **root**, which is why the root had
to become a valid key first. Without it a store mounted at `ref` would have
no way to answer for the
document or the title *at* `ref`, and a survey could not say what the mount
is.

A mount may be **read-only**, which is where the whole feature was pointed: a
shared read-mostly reference base beside a local read-write store. The refusal
lives here, in the routing, and is checked before the store is called at all --
`Store` knows nothing about it, and the database file is not opened any
differently. So this refuses writes *through this server*; it does not make the
file read-only to anything else.

A table is **immutable**: it has no mutable state after `__init__`, and a
change is a *new* table built by [`MountedStore.remounted()`](#outrage.mounts.MountedStore.remounted) rather than an
edit to this one. That is what makes a mount table changeable on a running
server at all -- a call holds the table it started with for its whole duration,
so no traversal can see two -- and everything about serving one, swapping it and
owning the stores that fall out of it lives in [`outrage.remount`](remount.md#module-outrage.remount), not here.
Some questions are deliberately still open, chief among them where a write to a
new key goes.

### outrage.mounts.EXTENSIONS_OPTION *= 'extensions'*

The option that says how a tree's file names line up with keys, for the one
backend that keeps its store as a directory. The value is a mode from
[`outrage.bulk.EXTENSION_MODES`](bulk.md#outrage.bulk.EXTENSION_MODES) -- `strip`, which is the mapping this
package writes, or `keep`, which makes a file name and a key segment the
same string.

**Why a mount says it rather than the tree.** How to read a corpus is a
property of the corpus and there is nowhere in a plain directory to record
one: a marker file would be a file in the tree that is not a document, in
the one backend whose contents somebody else is expected to be editing. So
it is said where the store is named, beside the `type` that had to be said
for the same kind of reason.

A backend that keeps its store in a file has no such question, and refuses
this rather than ignoring it -- [`outrage.store.FileStore.in_directory()`](store.md#outrage.store.FileStore.in_directory).

### outrage.mounts.MOUNT_KIND *= 'mount'*

The `kind` a listing reports for a key that is a mount point. A fourth
kind beside 'document', 'metadata' and 'implicit', because a mount point is
none of the three: it may hold content, and it always has a store behind it.
A caller that does not know the word still learns that the key exists, which
is the part that matters for navigating to it.

### outrage.mounts.OPTIONS *= ('type', 'extensions')*

Every option a spec may carry. Anything else is refused rather than ignored,
which is the rule `mounts.toml` already follows for a field it does not
know: a mount that quietly did something other than what it says is the
failure a mount configuration is least able to notice.

### outrage.mounts.OPTION_ASSIGNMENT *= '='*

Separates an option's name from its value, and the same character the mount
point uses for the same reason. `type=files` is one option and there is
currently one option; the grammar is what is general, not the list.

### outrage.mounts.OPTION_DELIMITER *= ','*

Separates the store file from an option, and one option from the next:
`KEY=FILE,NAME=VALUE`. `mount(8)`'s own `-o` vocabulary, and chosen
for what it does to *precedence*: an option written inside the value keeps
one mount one option occurrence, so a later `--mount` at that point
replaces the entry and everything said about it, and
`outrage.mountfile._overridden` needs no sentence about half-overridden
mounts. A second flag keyed by mount point would have needed one.

The price is a comma, which a store file may no longer hold: it is refused
by [`parse_options()`](#outrage.mounts.parse_options) on the way in and by [`unparse()`](#outrage.mounts.unparse) on the way
out, rather than being quietly the first option's name.

### outrage.mounts.READ_ONLY_MOUNT_KIND *= 'read-only mount'*

The `kind` for a mount point whose store refuses writes. A separate kind
rather than a `read_only` field on [`Entry`](store.md#outrage.store.Entry), because a
field would appear on *every* entry in every listing as a null, and a
result grows a field only when there is something to say. The kind is
already the field that says what
a key is, only one key in a listing is a mount at all, and the words carry
their own meaning to a caller who has never read any of this.

This is also the only place the fact is announced. The instructions do not
mention mounts -- see `instructions` on why a mounted store's readme is
not carried -- so, exactly like the existence of a mount, being read-only
costs nothing until somebody looks at the listing.

### outrage.mounts.ROOT_KIND *= 'root'*

What a report calls the mount that answers for every key no other mount
claims. Not a `kind` any listing uses -- the root is never an entry in one,
since it is the level everything else is listed *below* -- so it is spelled
here rather than on [`Mount.kind`](#outrage.mounts.Mount.kind), and used by the reports that put the
root in a table beside the mounts.

### outrage.mounts.SPEC_DELIMITER *= '='*

Separates a mount point from its store file in a `--mount` argument.
`=` rather than `:` because a Windows path holds a colon and no key can
hold an `=` any less than it can hold anything else -- but a key with one
in it is vanishingly rare, and a drive letter is not.

### outrage.mounts.TYPE_OPTION *= 'type'*

The option that says which backend keeps this store, overriding what the
file name implies. The value is a backend's own name --
`outrage.store.FileStore.backend_name`, the word a report already uses
-- so `type=files` names [`outrage.store_files.FilesystemStore`](store_files.md#outrage.store_files.FilesystemStore) and
is not a second vocabulary for the same three classes.

**Why the option exists at all.** Which backend keeps a store follows from
the store file's extension, and a directory of files has no extension to
read: without a way to say so, a tree is not mountable and a mount table
cannot describe one. See `outrage.store._BY_EXTENSION`.

### *class* outrage.mounts.Mount(prefix: [str](https://docs.python.org/3/library/stdtypes.html#str), store: [Store](store.md#outrage.store.Store), read_only: [bool](https://docs.python.org/3/library/functions.html#bool) = False)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One store, and the prefix it answers for.

#### prefix *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The key this store is mounted at, normalised. The root mount's is `""`.

#### store *: [Store](store.md#outrage.store.Store)*

#### read_only *: [bool](https://docs.python.org/3/library/functions.html#bool)*

Whether this server refuses writes routed here.

Defaults to False so that every existing construction of a `Mount` means
what it meant before, and so the single store case cannot become read-only
by accident.

#### *property* kind *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

What a listing calls this mount point.

#### *property* name *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The mount point as written for a person to read; the root is `/`.

#### *property* is_root *: [bool](https://docs.python.org/3/library/functions.html#bool)*

#### inner(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)

`key` as this store names it, or None if this mount does not hold it.

#### outer(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

`key` as the whole namespace names it. Total, by construction.

A mount point and a key inside a store are each bounded at
`keys.MAX_SEGMENTS`, and the joined namespace allows twice that, so
the sum always parses. That bound is what abolishes the case rather than
reporting it: without it a listing needs a path for dropping the keys
that will not fit.

The check stays as an assertion, because what it guards is an
arithmetic relationship between two constants and a store's contents,
and a store written by an earlier outrage can still hold a key too deep
for it. Raising names the mount and the key; returning a
string that will not parse would fail one layer away, which is the
failure this project keeps finding. `outrage check` reports such keys
before anything mounts the store.

### *exception* outrage.mounts.MountError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)

Raised when a mount table cannot be built as described.

### *class* outrage.mounts.MountedStore(stores: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Store](store.md#outrage.store.Store)], \*, read_only: [Collection](https://docs.python.org/3/library/collections.abc.html#collections.abc.Collection)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = ())

Bases: [`Store`](store.md#outrage.store.Store)

Several stores behind one key namespace, presented as one store.

A mount table *is* a [`Store`](store.md#outrage.store.Store): it answers every call in
the same vocabulary, over keys spelled the way a caller spells them, and
routes, steps over, crosses and merges underneath. That is what lets one
live in front of the MCP server, the command line, or another table, with
none of them holding routing code of their own -- and it is the reason
`Store` was written as a vocabulary rather than as a database.

What it is **not** is a file. It has no path, no format version of its own,
nothing to back up and nothing to repair, and it says so rather than
answering for its root mount: a check of a three-store table that silently
reported one store would be worse than a refusal.

#### writable *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[bool](https://docs.python.org/3/library/functions.html#bool)]* *= True*

A table can be written when its root mount can, which
`__init__()` requires of every table -- so this is always true, and
stated rather than inherited because a backend that forgets to say
inherits `True` and would be reporting it by accident.

#### backend_name *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[str](https://docs.python.org/3/library/stdtypes.html#str)]* *= 'mounts'*

What a refusal calls this when it has to name what it is talking to.
Not an extension, because no file is kept here; see the class docstring.

#### *classmethod* single(store: [Store](store.md#outrage.store.Store)) → [MountedStore](#outrage.mounts.MountedStore)

A table holding only `store`, at the root.

The single store case stated as a mount table rather than as a separate
path through the server, so there is one set of behaviour to test and
no second code path that only runs when nothing is mounted.

#### remounted(\*, mount: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Store](store.md#outrage.store.Store)] = MappingProxyType({}), read_only: [Collection](https://docs.python.org/3/library/collections.abc.html#collections.abc.Collection)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), unmount: [Collection](https://docs.python.org/3/library/collections.abc.html#collections.abc.Collection)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = ()) → [MountedStore](#outrage.mounts.MountedStore)

This table with mounts removed and added, as a new table.

Pure table algebra: no file is opened, no directory is consulted, and
nothing here knows where a store came from. The caller opens what it
wants mounted and passes the open stores in `mount`, keyed by the
prefix each is to answer for; `unmount` names prefixes to drop, and
removals are applied before additions, so one call can move a store.
A prefix in `mount` that something already holds **replaces** it.

Every surviving mount is copied whole, so **a shared store keeps its
prefix by construction** -- which is the whole of why sharing is safe,
since `mount_point` is the only thing a
store knows about its own mounting. A mount at a *new* prefix takes a
newly opened store, and this cannot silently do otherwise: the stores
it mounts are the ones it was handed.

A surviving mount keeps its read-only flag; a replaced one does not,
since a replacement states what it is. The result goes through
`__init__()`, so every invariant a table has is re-checked here
rather than restated -- a metadata mount point, a duplicate, a root
that must exist and be writable, a read-only flag matching nothing.

The root is refused in both arguments. It owns every key no mount
claims, so a table without one has nowhere to put anything, and
`server.instructions()` is built once from its `readme` -- a root
that cannot change is what keeps a connection's delivered instructions
honest for as long as it lasts.

This says nothing about *when* a table is swapped, or who then owns the
stores that fell out of it. That is [`outrage.remount`](remount.md#module-outrage.remount), which is
where the mutable state and the lock live.

#### *property* root *: [Mount](#outrage.mounts.Mount)*

The mount at the empty prefix, which every table is required to have.

The store a key falls to when nothing longer claims it, and so the only
one whose `readme` is delivered and the only one a caller can reach
without naming a mount. Its prefix being empty is what makes
[`resolve()`](#outrage.mounts.MountedStore.resolve) total: there is always a longest match.

#### *property* read_only *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Mount](#outrage.mounts.Mount)]*

The mounts that refuse writes, in key order.

#### *property* multiple *: [bool](https://docs.python.org/3/library/functions.html#bool)*

Whether anything is mounted besides the root.

#### resolve(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), \*, allow_wildcard: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Resolved](#outrage.mounts.Resolved)

The store owning `key`, and the name it knows it by.

Longest prefix wins, and the root always matches, so this cannot fail
to find a mount for a key that parses. A mount **shadows** whatever the
store behind it holds at the same keys: the outer store is never
consulted for a key a mount claims, so a document left behind at a key
that later became a mount point is unreachable rather than merged. That
is the mount table rule, and the alternative -- merging two stores that
disagree about one key -- has no answer that is not arbitrary.

`allow_wildcard` is passed straight through to the parse and needs
no handling of its own: a mount prefix is literal text, so a `?`
segment can never match one, and a key allocating a segment routes by
the segments around it exactly as the finished key will.

#### below(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Mount](#outrage.mounts.Mount)]

The mounts strictly beneath `key`, in key order.

Every mount below `key`, nested ones included, which is what makes
this the wrong list to traverse with: use `directly_below`, or
`segments`, which is built on it. This one answers "which stores does
this subtree touch", for a caller reporting rather than reading.

#### directly_below(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Mount](#outrage.mounts.Mount)]

The mounts beneath `key` that no other mount beneath it contains.

The ones a traversal of `key` meets *first*, in key order. A mount
nested inside another is left out because it is not reached from here:
it is reached from the mount containing it, one level further down, and
that is what makes nesting fall out of recursion rather than needing a
case of its own.

Taking them in search order is what makes the test local. An ancestor
sorts immediately before its descendants, so a mount is nested exactly
when the last one kept is a prefix of it, and nothing further back can
contain it.

#### segments(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), depth: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Segment](#outrage.mounts.Segment)]

`key`'s subtree as the stretches of each store that make it up.

In key order, disjoint, and covering every key at or below `key` that
any store answers for -- so a traversal that reads each in turn reads
the subtree, mounts included, and one that reads only the first behaves
as it did before mounts existed.

The store answering for `key` contributes the stretches *between* the
mounts below it, named from both sides: `before` ends the stretch in
front of a mount point and `after_subtree` starts the one behind it.
That is not only an optimisation. The outer store still holds every row
a mount shadows, so a traversal that did not step over them would
report documents that reading by key refuses -- a survey offering keys
a read denies, of which this is the general form.

A mount past the depth budget is stepped over but not descended into:
its stretch is still cut out of the store above, since those rows are
unreachable whether or not anything asked for them.

#### children(parent: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Entry](store.md#outrage.store.Entry)]

The keys immediately below `parent` that exist because a mount does.

A mount at `lib/ref` puts `lib` into the root listing and `ref`
into `lib`'s, neither of which any store knows about: the outer store
has no rows there and the inner one cannot see where it was mounted.
Without this a mounted store is invisible to anyone who does not
already know its prefix, which is the same failure as a document with
no title.

#### last_child(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)

The final segment of the last key immediately below `key`.

[`outrage.store.Store.last_child()`](store.md#outrage.store.Store.last_child) asked of the whole namespace, so
that `?last` resolves to what a listing of that level would actually
end with -- a mount point included. Without the second half, `?last`
at a level a mount stands in would name a key the caller can see and
skip the one they are looking at.

The two halves compare as bare segments and need no translation between
namespaces: routing changes what lies *above* a level, never the name
of a key within it, so the answering store's last child is spelled the
same from outside as from in.

#### shadowing() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Mount](#outrage.mounts.Mount)]

The mounts whose mount point the store beneath them already holds.

A mount shadows: the store that would otherwise own those keys is never
consulted for them, so a document left at a key that later became a
mount point becomes unreachable rather than merged. That is quiet
enough to be worth saying out loud once, at startup, while somebody can
still move the document or the mount.

The check is the key and its subtree, which misses one corner: a mount
point the outer store holds *only* metadata for. Metadata sits at the
key rather than below it, so neither question finds it. Worth naming
rather than chasing -- both are misconfigurations, and this catches the
ones anybody actually creates.

#### read_only_below(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

The mounts below `key` that refuse a write, in key order.

Not part of what a store is, and deliberately not folded into
[`delete()`](#outrage.mounts.MountedStore.delete)'s answer: that returns the keys that went, and a mount
that refused is not a key. This is what a front end needs in order to
say *which* part of a subtree a delete will never reach -- which is a
sentence, and a sentence is the front end's business.

#### read_only_at_or_below(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

The mounts that refuse a write anywhere at or below `key`, in key order.

[`read_only_below()`](#outrage.mounts.MountedStore.read_only_below) and, in front of it, the mount that owns `key`
itself when that one refuses. The difference is the whole question for a
caller writing *into* a subtree rather than clearing one out: a delete
names the top of what it is removing, so every mount that can refuse it
is underneath, while a copy names where documents will land, and the
mount that refuses them is as often the one they are landing inside.

Asked by [`outrage.server.build_server()`](server.md#outrage.server.build_server)'s copy, which reported
twenty failures and named no mount at all while it asked the other
question -- each failure carrying the whole read-only refusal, so the
one fact arrived five times as a sample and never once as a sentence.

#### store_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), content: [str](https://docs.python.org/3/library/stdtypes.html#str), format: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, title: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, encoding: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, updated_at: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)

Store `content` at `key`, overwriting anything already there.

A `?` segment in `key` is replaced by a number unused among the
children of the key enclosing it, so `tmp/?` writes to `tmp/1` in
an empty store. Returns the key actually written, which is the only way
the caller learns an allocated number.

`format` is one of `FORMATS`. Left out, it defaults to 'json'
when the content parses as a JSON object or array, 'html' when it opens
with a doctype or an `<html>` element, and 'markdown' otherwise --
'text' is never detected and has to be asked for.

`title` writes the `!title` metadata alongside the document in the
same transaction. It saves a second call, but it exists mainly because
the title is what makes a document discoverable later, and a separate
call is one that can simply be forgotten. It may be given for a
metadata key too, and becomes that key's own `!title`: metadata is a
namespace and a namespace can be described, so `a/!changelog` may say
what its changelog is for at `a/!changelog/!title`.

`encoding` describes how `content` and `title` arrived, not what
is stored: 'json-string' means each is a JSON string literal, quotes
and all, which is decoded before it is written. The stored document is
plain text either way, so readers are unaffected. Its purpose is to
make damage in transit loud - see `_decode`.

`updated_at` is when the document was last written, and left out it
is now - which is what an ordinary write means by it. It is here for
the write that is a *copy* of a document that already exists: a
transfer between two stores carries the timestamp across, or the copy
says every document was written the moment it was copied and the store
loses the one fact about a document that nothing can reconstruct. An
ISO 8601 timestamp, normalised to UTC at second precision, which is
what `_now()` writes and so what every stored value already looks
like; a naive one is read as UTC.

Deliberately **not** offered by the MCP tool or by `outrage set`. A
client writing a document is writing it now, and a stamp it could
choose is one it could get wrong about its own work; the callers that
legitimately restamp are copying something that was already stamped.

Every refusal above is `_validated()`'s, which an implementation
calls before it writes anything.

#### retrieve_document(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, offset: [int](https://docs.python.org/3/library/functions.html#int) = 0, byte_offset: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, length: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, pattern: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, occurrence: [int](https://docs.python.org/3/library/functions.html#int) = 0, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_MAX_CHARS) → [Excerpt](store.md#outrage.store.Excerpt)

Read the content stored at `key`.

`pattern` is a literal substring, not a regular expression; when
given, the read starts at its `occurrence`-th appearance at or after
the offset. The result is capped at `length` or `max_chars`,
whichever is smaller, and carries a continuation offset.

`offset` counts characters and `byte_offset` counts UTF-8 bytes of
the same document. Both are positions, so giving both is refused; a
byte offset landing inside a character reads from that character's
first byte, and the excerpt says where it actually began.

**Every backend accepts a byte offset and returns identical content
for it.** Only the cost differs -- one that can seek does, one that
cannot converts and slices -- and that contract is what makes a byte
offset something a caller can carry between stores, and out of the
store altogether to a file [`bulk()`](bulk.md#module-outrage.bulk) exported.

#### exists(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [bool](https://docs.python.org/3/library/functions.html#bool)

Whether `key` itself holds a document.

Not the same question as whether anything is below it: a bulk import
asks this per file to decide about one key, and a container that holds
nothing itself is free for a document to be written to.

Deliberately cheaper than a read, since the answer is wanted for every
file in an import and the content is not.

#### level_entry(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Entry](store.md#outrage.store.Entry) | [None](https://docs.python.org/3/library/constants.html#None)

As [`level_entry()`](store.md#outrage.store.Store.level_entry), mount points included.

A mount point is a key no store knows about, so asking the store behind
it would answer about whatever the mount shadows -- which is exactly the
row a listing has just declined to show. Answered here instead, from the
inner store's root, the same way [`children()`](#outrage.mounts.MountedStore.children) describes one.

#### descendant_count(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [int](https://docs.python.org/3/library/functions.html#int)

How many stored keys lie strictly below `key`.

Metadata counts: it is stored, and a caller deciding whether a subtree
is empty is asking about everything that would have to go.

**A metadata key has a real subtree of its own**, and this counts it.
`a/!changelog` holding twenty notes reports twenty, exactly as a
document holding twenty children does, which is what makes the delete
below refuse it without `recursive`.

Exists so a caller can report what a non-recursive delete left behind:
without it, deleting a key that holds nothing itself is indistinguishable
from deleting a key that does not exist.

What it leaves out is `key`'s **own** metadata unit, because a plain
delete takes that with the key -- so the default answers *what would a
plain delete keep*. **\`\`whole_subtree\`\` asks the other question**:
everything strictly below `key`, that unit included, which is what a
*recursive* delete takes and what [`outrage.bulk.walk()`](bulk.md#outrage.bulk.walk) reports.
A caller previewing a recursive delete needs the second, and answering
it with the first prints a remainder short by the unit -- negative,
once the preview reaches past the ordinary children.
See [`outrage.keys.meta_range()`](keys.md#outrage.keys.meta_range).

`key_range` bounds it for the reason it bounds `delete`: a count
that includes keys a mount has made unreachable tells a caller to pass
`recursive` to remove keys that are not there to remove.

#### latest_change(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, whole_subtree: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)

The newest change any mount the range touches holds below `key`.

The maximum over the segments, where a count is the sum over them: the
merge differs by the aggregate and the segments are the same ones. Each
store answers about its own stretch, and a store mounted further down
contributes its root row too, because everything it holds is below the
key -- the asymmetry `_kept_below()` exists for, in the shape a
maximum needs.

None when no mount the range touches holds anything, which is what
every empty selection answers here.

#### delete(key: [str](https://docs.python.org/3/library/stdtypes.html#str), recursive: [bool](https://docs.python.org/3/library/functions.html#bool) = False, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, unchanged_since: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, dry_run: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

As [`delete()`](store.md#outrage.store.Store.delete), and it **crosses**.

Deliberate, and the one place crossing makes the system more dangerous
rather than less: a delete that stopped at a boundary while every other
call crossed one would leave a caller to learn the rule from what
survived.

A read-only mount below the key is **skipped rather than fatal**, since
one such mount deep in a subtree should not veto a delete that is legal
everywhere else in it. What it kept back is not returned here -- this
answers with the keys that went -- and a front end that has to say so
asks [`read_only_below()`](#outrage.mounts.MountedStore.read_only_below).

`unchanged_since` is checked **here, over the whole table**, and is
not passed inward. A recursive delete is one store's call at a time, so
a watermark handed to each of them in turn would let the third mount
refuse a run the first two had already carried out -- which is the half
finished outcome the precondition exists to prevent. Asked of the table
it is one aggregate per mount and the refusal comes before any of them
is asked to delete anything.

`dry_run` is passed inward, to every segment: a preview of a crossing
delete has to name what each store would take, and a table that
previewed only its own stretch would report a fraction of the answer as
though it were all of it. A read-only mount is skipped in a preview
exactly as it is skipped in the delete, which is what makes the two
lists the same list.

#### list_keys(key: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[Entry](store.md#outrage.store.Entry)]

As [`list_keys()`](store.md#outrage.store.Store.list_keys), with the mounts spliced in.

A mount point is a key no store knows about: the store beneath it has no
row there, and the store above it cannot see where it was mounted. Put
in here or a mounted store is invisible to anyone who does not already
know its prefix.

#### get_documents(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, max_chars: [int](https://docs.python.org/3/library/functions.html#int) = DEFAULT_BULK_MAX_CHARS, limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None, max_total_chars: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[Excerpt](store.md#outrage.store.Excerpt)]

Read everything `subtree` names, in key order.

With `meta_name` the result holds those metadata entries instead of
documents, which is how the titles of every document under a key are
listed in one call.

`key_range` narrows the subtree to a stretch of the order inside it,
and the two hold together: a key is returned when it is in the subtree
*and* in the range. It bounds the selection, so `total` and
`total_chars` describe that stretch, and a caller reading one subtree
as several ranges can add the answers up.

`cursor` is not one of the bounds. It is where the last page stopped,
it moves within the range as a caller pages, and it deliberately does
not reach the totals: what a caller cannot work out from a page is how
much of the whole they are holding.

Two axes bound the answer and both are needed. `max_chars` caps each
document, `limit` and `cursor` page the collection, and
`max_total_chars` caps the page as a whole -- without that last one
the two axes multiply, and a hundred documents at two thousand
characters each honours both stated bounds while returning two hundred
thousand characters.

#### keys_missing_meta(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, cursor: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', limit: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Page](store.md#outrage.store.Page)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

Document keys in `subtree` carrying none of `meta_name`.

A survey by `!title` only sees documents that have one, so on its own
it silently under-reports the store. This names what the survey missed.

`key_range` narrows the subtree exactly as it narrows a survey, and
for the same reason: the two have to be askable over one stretch of the
store, and to agree about what was in range, or they stop describing
the same one.

#### missing_meta_stats(subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree) = EVERYTHING, \*, key_range: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, window: [KeyRange](store.md#outrage.store.KeyRange) = UNBOUNDED, meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = 'title', sample: [int](https://docs.python.org/3/library/functions.html#int) = 0) → [MissingMeta](store.md#outrage.store.MissingMeta)

What a metadata survey could not see, summed across the boundary.

The counts add for the same reason the pages concatenate: the segments
are disjoint and tile the subtree, and each store counts only its own
stretch. `window` crosses like any other range -- a segment it
excludes is not asked at all, which is what makes a caller's windows
tile as they page.

#### close() → [None](https://docs.python.org/3/library/constants.html#None)

Close this thread's connection to every mounted store.

### *exception* outrage.mounts.ReadOnlyMountError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`PermissionError`](https://docs.python.org/3/library/exceptions.html#PermissionError)

Raised when a write is routed to a mount that was mounted read-only.

Separate from [`MountError`](#outrage.mounts.MountError), which is about a table that cannot be
*built*: this one is about a request, and the table it names is working as
configured.

`PermissionError` is the builtin it keeps, following the rule in
`errors.py` that each subclass keeps the builtin it already inherited --
a caller that catches `OSError` around a write goes on working.

### *class* outrage.mounts.Resolved(mount: [Mount](#outrage.mounts.Mount), key: [str](https://docs.python.org/3/library/stdtypes.html#str), outer: [str](https://docs.python.org/3/library/stdtypes.html#str))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Which store owns a key, and what that store calls it.

#### mount *: [Mount](#outrage.mounts.Mount)*

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The key inside the mounted store.

#### outer *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The key as it was asked for, normalised.

#### *property* store *: [Store](store.md#outrage.store.Store)*

The store that owns the key: the longest mount prefix matching it.

Not "the root store unless something is mounted" -- the root is itself
a mount, so a lone store is a table of one and takes the same path. Ask
this store for [`key`](#outrage.mounts.Resolved.key), which is the inner spelling; asking it for
the key the caller passed would be asking for a key it has never heard
of.

#### *property* read_only *: [bool](https://docs.python.org/3/library/functions.html#bool)*

Whether the mount that owns the key refuses writes.

#### writable(action: [str](https://docs.python.org/3/library/stdtypes.html#str) = 'write') → [Resolved](#outrage.mounts.Resolved)

This, or raise if the mount that owns the key refuses writes.

Returns itself so a caller reads as one expression and cannot resolve a
key, forget to check it, and write anyway -- the failure this guards is
precisely a refusal that arrives too late to matter, so the shape that
makes forgetting awkward is worth the small strangeness of a method
that returns its own receiver.

`action` is the verb for the message, because "cannot write" reads
wrongly for a delete and a caller reading a refusal should not have to
translate it back into what they asked for.

The message names the mount rather than only the key, because the key
looks perfectly ordinary and the reason it was refused is somewhere the
caller cannot see: the command line the server was started with.

**Which of the two refusals this is matters, and the store is what
knows.** A mount refuses because of how it was started, and the message
says so and tells the caller which flag to drop. A *backend* refuses
because a parquet file is not updated in place, and no flag would make
the same call succeed -- so the mount's advice would be wrong, and
wrong in the way that costs someone a restart to find out. The two are
both real and they compose: a SQLite store is read-write or read-only
according to how it was mounted, and a parquet store is read-only
either way. Found by mounting one and writing to it, which is what a
live test is for.

### *class* outrage.mounts.Segment(mount: [Mount](#outrage.mounts.Mount), subtree: [BoundedSubtree](store.md#outrage.store.BoundedSubtree), key_range: [KeyRange](store.md#outrage.store.KeyRange))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

One stretch of one store, as part of reading across a mount boundary.

A subtree spanning mounts is not one query and cannot be: the rows live in
different databases. It is a *sequence* of these, in key order, each naming
the store to ask, which part of that store's hierarchy is in scope, and
which stretch of its order. Concatenate their answers and the totals add,
which is what lets a traversal answer as though the subtree were one thing.

`subtree` and `key_range` are both in the mounted store's **own**
namespace: a mounted store never learns where it was mounted, so the
translation happens here and the results are put back by `mount.outer`.

#### mount *: [Mount](#outrage.mounts.Mount)*

#### subtree *: [BoundedSubtree](store.md#outrage.store.BoundedSubtree)*

#### key_range *: [KeyRange](store.md#outrage.store.KeyRange)*

#### *property* store *: [Store](store.md#outrage.store.Store)*

The store to ask for this segment, which is not necessarily the one
the caller's key named.

A segment is a stretch of *one* store, and a traversal crossing a mount
boundary produces several. `subtree` and `key_range` beside it are
in this store's own namespace, never the outer one.

#### resume_from(after: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), [bool](https://docs.python.org/3/library/functions.html#bool)]

This segment's own cursor, and whether the page already passed it.

A cursor names a key in the one namespace, so it means something
different to each store a traversal crosses, and recomputing it at
every boundary is the only way it keeps meaning the same *place*.
Three answers, and all three are needed:

* a key **inside this segment's store** -- the cursor falls here, so
  the store resumes from it;
* `None` with `False` -- the cursor lies before this segment, which
  therefore starts at its own beginning;
* `None` with `True` -- this segment lies entirely **behind** the
  cursor, so an earlier page has already returned it.

The last is what a single store never needed: within one store a
cursor and a range are ANDed and a stretch before the cursor comes back
empty on its own. Across stores the cursor cannot even be spelled in
the namespace of a store it does not name, so being behind it has to be
an answer rather than an empty result. Such a segment is still
*counted* -- totals describe the whole collection and have never
depended on where the reader had got to.

### *class* outrage.mounts.Spec(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), type: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

A store as an argument names it: which file, and how to open it.

The value half of `--mount KEY=FILE,type=NAME`, and the whole of
`--root-mount FILE,type=NAME`, which is why it is a thing of its own
rather than a pair returned beside a mount point: the root takes the same
grammar and has no mount point to be returned beside.

`path` is relative to the store directory, as every store file is;
`store_file` applies that when the store is opened rather than here, so
this stays a parse of the argument and touches nothing.

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

#### type *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

The backend, when the argument named one, else None for the file to say.

#### extensions *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

How file names line up with keys, when the argument said; else the
backend's own default. Only a tree has an answer -- see
[`EXTENSIONS_OPTION`](#outrage.mounts.EXTENSIONS_OPTION).

#### opened(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None, mount_point: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [FileStore](store.md#outrage.store.FileStore)

The store this spec names, opened in `directory`.

**The one place a spec becomes a store**, and a method rather than a
line repeated wherever one is opened. Every field here is something an
argument said about *how to open it*, so a caller taking them apart by
hand has to be revisited each time the grammar grows one -- and the
failure when it is not is silent in the worst way: the option parses,
the mount succeeds, and the store opens under something nobody asked
for. Nothing raises and no suite goes red, so the only thing that finds
it is somebody reading the keys.

### outrage.mounts.mount_point(prefix: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, spec: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [str](https://docs.python.org/3/library/stdtypes.html#str)

Validate a mount point, however it was written down.

Split out of [`parse_spec()`](#outrage.mounts.parse_spec) so that a mount table read from a file
reaches exactly these refusals rather than growing a second set: a config
file that had its own idea of what a key is would be a second grammar over
the same namespace, and the project has one. `spec` is what the reader
wrote, when there is a spec to quote back at them; a file quotes the key it
used as its own field name.

### outrage.mounts.open_mounts(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None), specs: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), read_only_specs: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), \*, root_mount: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [Spec](#outrage.mounts.Spec) | [None](https://docs.python.org/3/library/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None, attached: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Store](store.md#outrage.store.Store)] = MappingProxyType({})) → [MountedStore](#outrage.mounts.MountedStore)

Open every store in `directory`, as one table.

**One directory, several files.** `directory` holds them all: the root
mount, named by `root_mount`, and one file per `KEY=FILE` spec. That is
what makes a mount configuration relocatable -- only the directory is an
absolute path, and the stores in it are named relative to it -- and it is
the shape a backend other than SQLite would slot into, since what varies
between backends is the file, not the directory around it.

`specs` are mounted read-write and `read_only_specs` read-only; the two
share one namespace, so mounting the same key in both is the same collision
as mounting it twice in either. Two mounts naming the same *file* is not a
collision this checks: they would be two stores over one database, which
SQLite handles and which no configuration has a reason to ask for.

Every spec is parsed before any store is opened, so a table that cannot be
described is refused without half of it existing. A failure part way
through the opening closes what was already open, since a process that
exits without doing so leaves a WAL behind.

A read-only mount must already exist. `Store` creates its file and
migrates a database on the way in, so without this check a mistyped name
would be *created*, mount as an empty store, and read as though the
reference base were simply empty -- while the flag that was supposed to
protect it made it impossible to notice by writing. That is the same
argument `parse_spec` makes for validating a mount point early, one step
further along.

`attached` is the one way in for a store this call did not open: already
open, mounted read-only at the key it is given, and **not** subject to the
relative-to-`directory` rule above, which it could not obey. That rule is
load bearing rather than incidental -- it is what makes a table relocatable
-- so the exception is a separate argument rather than an absolute path
quietly admitted into a spec. What needs it is a store shipped inside the
installed package, which lives in `site-packages` and is not expressible
as a `KEY=FILE` at all: [`outrage.shipped`](shipped.md#module-outrage.shipped). It is mounted read-only
because the caller is lending a store rather than handing one over, and
everything else about it -- precedence, shadowing, how it lists -- is an
ordinary mount's. Duplicates are refused across all three sources together;
which of two claims at one point survives is settled before this, in
`outrage.mountfile._overridden()`.

A store passed here is closed with the table, like every other, so a caller
hands one over and does not close it twice -- and a failure part way
through closes it as well.

### outrage.mounts.parse_options(value: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, spec: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Spec](#outrage.mounts.Spec)

Split `FILE[,NAME=VALUE]...`, or say why it is not one.

The value half of a mount spec, and a `--root-mount` whole. `spec` is
what the reader actually wrote, when there is a longer argument to quote
back at them.

**An unknown option name is refused**, and so is a repeat of a known one.
The first is the rule `mounts.toml` already follows for a field it does
not recognise, for the reason a mount configuration exists: it is read
later, by somebody who is not watching, and an option that silently did
nothing is the failure least likely to be noticed -- a mount that is not
the store it says is a store that reads as simply empty. The second is the
same refusal a duplicate mount point earns, one level down.

The *value* of an option is not checked here. `type=nonsense` is a
backend that does not exist, which `outrage.store._backend_for()`
refuses in its own words when the store is opened; a second list of
backend names kept here to refuse it a moment earlier is exactly the
duplicate vocabulary this grammar is written to avoid.

### outrage.mounts.parse_spec(spec: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Spec](#outrage.mounts.Spec)]

Split a `KEY=FILE[,NAME=VALUE]...` mount argument, or say why it is
not one.

`FILE` is a store file **relative to the store directory**, not a
directory of its own: every mount a server holds lives in the one directory
`--dir` names, as a file beside the root mount. `store_file` is the
rule, and it is applied when the store is opened rather than here, so that
this stays a parse of the argument and touches nothing.

The key is validated here rather than when the store is opened, so a
misspelled mount point is refused before a database is created for it --
`Store` makes its file on the way in, and a typo would otherwise leave an
empty store behind as evidence of a server that never started.

The options after the file are [`parse_options()`](#outrage.mounts.parse_options)'s, and everything a
mount can say beyond *where* it is goes there. One flag remains one mount,
which is what keeps overriding an entry from a mount configuration a matter
of replacing it whole -- see [`OPTION_DELIMITER`](#outrage.mounts.OPTION_DELIMITER).

### outrage.mounts.unparse(spec: [Spec](#outrage.mounts.Spec)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

`spec` as the argument it was read from: the inverse of
[`parse_options()`](#outrage.mounts.parse_options).

What a mount table renders into when it is spliced into a command line,
which is the whole mechanism by which a file has any effect at all -- so
the two functions are here together, where they can be read as one grammar
and tested as a round trip.

A store file holding the option delimiter is refused *here* as well as on
the way in, because this is the direction a file reaches: an entry written
as `{ path = "a,b" }` in TOML never passed through a spec, and rendering
it would produce an argument that parses back as something else.
