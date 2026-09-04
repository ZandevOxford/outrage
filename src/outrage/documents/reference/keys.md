# outrage.keys

Parsing and validation for the Outrage key namespace.

A key is zero or more segments joined by `/`, and `/` is the only separator
there is. A segment may hold almost any text: the intent is that a key can
mirror a filesystem path without transforming the names it carries, so the only
exclusions are `/` itself, the control characters below `\t`, and a leading
`?` -- which is reserved, since a segment beginning with one names something
for the store to *do* rather than a key to store under.

The key with no segments is the **root**, spelled by the empty string. It is a
key like any other: it holds a document, carries metadata as `!title`, and is
the parent of every top level key. A `None` key arriving at a front end means
the root, so that nothing below the boundary carries two spellings of
"everywhere".

A segment beginning with `!` opens a **metadata namespace** on the key above
it, so `context/5/state/!title` is the title of `context/5/state`. Inside
that namespace everything is an ordinary namespace again -- documents, `?`,
`?last` and their own metadata -- so `a/!changelog/22` is a document kept
inside the `changelog` metadata on `a`, and `a/!changelog/22/!title` is
that document's title. The metadata *name* is therefore one segment: `a`
carries `changelog`, not `changelog/22`.

**Metadata changes exactly one thing, which is depth**: `!` and everything
after it adds none, so `a`, `a/!changelog` and `a/!changelog/22/!title`
are all at depth 1. Levels and depth are decoupled -- reaching that document
from `a` is two level walks and no depth -- and that is what keeps depth
across a mount boundary a constant offset.

A key being written may use `?` as a whole segment to ask the store to
allocate a number for it, and any key may use `?last` as a whole segment to
name the key that sorts last at that point -- resolved by a front end, against
a store, before the key is parsed for anything else.

A segment that is purely numeric is normalised by stripping its leading zeros,
so `context/01` and `context/1` are the same key, and is sorted as though
zero padded, so `context/2` comes before `context/10`.

The reasoning behind the grammar, the sort form and the schema is in
`design.md`, which ships beside these pages and is read as `outrage/design`.
It is not part of this *reference* -- these pages are generated from the
docstrings and contain nothing else.

### outrage.keys.DELIMITER *= '/'*

Separates the segments of a key, and the only separator in the namespace.

### outrage.keys.LAST *= '?last'*

Stands in for the last key at that point, so `notes/?last` names whatever
sorts last immediately below `notes`. Legal only as a whole segment, and
only where a front end has resolved it against a store first -- which is why
[`parse()`](#outrage.keys.parse) refuses it by default, exactly as it refuses [`WILDCARD`](#outrage.keys.WILDCARD).
The two are spelled alike because they are the same idea from either end:
one names a key that does not exist yet, the other the newest that does.

### outrage.keys.LEGACY_META *= ':'*

The metadata suffix this namespace used until schema 4, kept only so the
schema 2 to 3 migration can read keys written in it. No longer rejected by
`parse`: `:` is an ordinary segment character now, like any other.

### outrage.keys.MAX_JOINED_SEGMENTS *= 128*

The most segments a key may have in the namespace a mount table presents,
which is the only place the two halves are ever seen joined. Derived rather
than chosen, so that halving one cannot be done without the other following.

### outrage.keys.MAX_SEGMENTS *= 64*

The most segments a key may have **within one store**, and the most a mount
point may have. Two bounds in one number, deliberately: a key in the joined
namespace is a mount prefix followed by a key inside the store mounted
there, so bounding each half at half the total makes every joined key valid
*by construction*. Nothing has to check the sum, and no key can exist in a
mounted store that the namespace above it cannot name.

This was 128 until 2026-08-20, when it was halved to buy that property.
128 was overkill - a key is typically a handful of segments - and the
alternative was carrying a drop path through every listing for keys that
had no name from outside. See `project/reference/planned/mounts/cursors`.

### outrage.keys.MAX_SEGMENT_CHARS *= 1024*

Bounds on a key, generous enough that only a generated key will meet them.
Both are guidelines made checkable rather than limits anyone should design
against: a segment is usually well under 20 characters and a key well under
half a dozen segments.

### outrage.keys.META_PREFIX *= '!'*

Opens a metadata namespace on the key above it, inside which everything is
an ordinary namespace again. Nothing rests on where `!` sorts any more --
the sort form discriminates metadata explicitly -- so this is a spelling
convention rather than a mechanism, and it may repeat at any level.

### outrage.keys.MIN_SEGMENT_CHAR *= '\\t'*

The lowest character a segment may contain. Excluding everything below tab
costs nothing worth mirroring -- no filesystem name addresses that range --
and it is what lets the sort form below discriminate segments without
escaping, since no legal segment character can collide with its markers.

### outrage.keys.NUMERIC_RE *= re.compile('\\\\A[0-9]+\\\\Z')*

A segment that names nothing but a number. Deliberately not str.isdigit,
which accepts superscripts and other digits that int() then rejects.

### outrage.keys.RESERVED_PREFIX *= '?'*

Begins a segment the store interprets rather than stores. [`WILDCARD`](#outrage.keys.WILDCARD)
and [`LAST`](#outrage.keys.LAST) are the whole of it today; every other spelling is refused,
which is what reserves the space for the filters and logical operations a
key will grow -- a subtree filter, a range, a choice between two keys.

Reserved **before** anything needs it, deliberately and at a known cost:
`a/?x` was a legal key until 2026-08-23 and is not one now. The
alternative is adding each operator to a namespace that already allows it as
ordinary text, where every one of them silently changes what an existing key
means. One refusal now, or an unbounded number of migrations later.

Only the *first* character is reserved, so a key can still mirror a name
holding a question mark: `notes/where?.md` is fine.

### outrage.keys.RESERVED_SEGMENTS *= frozenset({'?', '?last'})*

Every reserved segment that means something today. A third one is a constant
and a line here, and needs no change to the grammar: that is what reserving
the prefix bought.

### outrage.keys.ROOT *= ''*

The root: the key with no segments, and the parent of every top level key.
It is its own parent, the way POSIX makes `/..` be `/`. That is what
lets an ancestor walk terminate without a second value meaning "nowhere",
and it is why every query listing a level has to exclude the root from its
own listing -- which `store` does in one place.

### outrage.keys.WILDCARD *= '?'*

Stands in for a segment the store should allocate. Legal only when writing,
and only as a whole segment: past the first character it is ordinary text,
so `notes/where?.md` is a perfectly good key. A segment that *begins* with
one is reserved -- see [`RESERVED_PREFIX`](#outrage.keys.RESERVED_PREFIX).

### *exception* outrage.keys.InvalidKeyError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)

Raised when a key does not match the grammar.

A `OutrageError` because a malformed key is *about the request*, so a front
end should render it as one line rather than a traceback. Still a
`ValueError` as well, so existing callers catching that go on working.

### *class* outrage.keys.Key(key: [str](https://docs.python.org/3/library/stdtypes.html#str), doc_key: [str](https://docs.python.org/3/library/stdtypes.html#str), meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), meta_path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), parent: [str](https://docs.python.org/3/library/stdtypes.html#str), wildcard_parent: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

A parsed key, with the columns derived from it.

#### key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The full key, normalised, including any metadata segments. Delimiters
are tidied and numeric segments have lost their leading zeros, so this may
differ from the string that was parsed.

#### doc_key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The key up to but excluding its first metadata segment.

#### meta_name *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

The first metadata segment, without the leading `!`, or None if the
key names a document. **One segment.** A metadata name is a name, so
`a/!changelog/22` says that `a` carries `changelog`; the `22` is a
document kept inside that namespace and belongs to [`meta_path`](#outrage.keys.Key.meta_path).

#### meta_path *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

What follows the first metadata segment, or None when nothing does.
`a/!changelog/22/!title` has a `meta_name` of `changelog` and a
`meta_path` of `22/!title`.

Inside a metadata namespace everything is an ordinary namespace again, so
this may hold documents, their own metadata and whole subtrees. It is what
tells the metadata *value* from something kept inside it, which is the
distinction [`is_meta_value`](#outrage.keys.Key.is_meta_value) names.

#### parent *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The enclosing key: this key without its last segment. A document's
metadata therefore has that document as its parent, and lists alongside its
subkeys. The root is its own parent, which is what makes an ancestor walk
terminate and what every listing of a level has to allow for.

#### wildcard_parent *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*

The key enclosing the `?` segment, or None if there is no wildcard.
ROOT when the wildcard is the first segment. This is the key whose children
the allocated segment has to be unique among.

#### *property* is_metadata *: [bool](https://docs.python.org/3/library/functions.html#bool)*

#### *property* is_meta_value *: [bool](https://docs.python.org/3/library/functions.html#bool)*

Whether this key is a metadata value, not something kept inside one.

The predicate every survey needs, and the one [`meta_name`](#outrage.keys.Key.meta_name) alone
used to supply: when everything below a `!` was folded into the name
there was nothing to tell `a/!title` from `a/!changelog/22`, and
the surveys that asked `meta_name is not None` were asking this.

#### *property* has_wildcard *: [bool](https://docs.python.org/3/library/functions.html#bool)*

#### *property* has_last *: [bool](https://docs.python.org/3/library/functions.html#bool)*

Whether any segment is `?last` and still waiting to be resolved.

Derived rather than stored, and there is no `last_parent` beside
`wildcard_parent`, because a key may hold several: each one is
resolved against the key the ones before it produced, so the parent
only exists part way through [`resolve_last()`](#outrage.keys.resolve_last).

### outrage.keys.LastChild

What [`resolve_last()`](#outrage.keys.resolve_last) asks a store for: the final segment of the last
key immediately below the one it is given, or None when nothing is below it.
A *segment*, not a key, because the caller already knows the part above it
and joining the two here is what keeps a mounted store's answer -- which is
named from inside that store -- usable in the namespace it was asked in.

alias of [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`str`](https://docs.python.org/3/library/stdtypes.html#str)], [`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)]

### outrage.keys.ancestors(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]

The enclosing keys of `key`, outermost first.

These are the keys that exist implicitly. A metadata key's ancestors
include the document it is attached to.

The root is not among them, though it encloses everything. It is not
brought into being by what sits below it the way the others are -- it is
always there -- so counting it as implicit would say something untrue about
every key in the store.

```pycon
>>> ancestors("context/a1b2/design/!title")
['context', 'context/a1b2', 'context/a1b2/design']
>>> ancestors("a"), ancestors("")
([], [])
```

### outrage.keys.depth(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [int](https://docs.python.org/3/library/functions.html#int)

The number of segments in the document part of `key`.

Metadata segments do not add depth; `a/b` and `a/b/!title` are both at
depth 2. The root is depth 0, and so is metadata on it: neither has a
segment to count.

```pycon
>>> depth("a/b"), depth("a/b/!title"), depth(""), depth("!title")
(2, 2, 0, 0)
```

### outrage.keys.displayed(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

How a key is written for a person to read. The root is spelled `/`.

The empty string is invisible in a report: it reads as a missing name, or
as stray indentation, and a reader cannot tell which. `/` is a legal
spelling of the root and normalises straight back to it, so what is printed
is also what can be typed in again.

```pycon
>>> displayed("a/b"), displayed(ROOT)
('a/b', '/')
```

### outrage.keys.fits(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [bool](https://docs.python.org/3/library/functions.html#bool)

Whether `key` is a valid key in the joined namespace a mount table shows.

`MAX_SEGMENTS` bounds each half and this bounds the pair, so a prefix and
an inner key that each parsed can always be joined: **this cannot return
False for a key built that way**. It is kept as the statement of that
property, to be asserted at the join rather than assumed, since the
alternative is a silently unnameable key -- which is what the bounds were
halved to abolish.

```pycon
>>> fits("a/b"), fits("a/" * MAX_JOINED_SEGMENTS + "b")
(True, False)
>>> fits("a/" * MAX_SEGMENTS + "b")  # two full halves still join
True
```

### outrage.keys.is_valid(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, allow_wildcard: [bool](https://docs.python.org/3/library/functions.html#bool) = False, allow_last: [bool](https://docs.python.org/3/library/functions.html#bool) = False, max_segments: [int](https://docs.python.org/3/library/functions.html#int) = MAX_SEGMENTS) → [bool](https://docs.python.org/3/library/functions.html#bool)

Whether `key` matches the grammar.

### outrage.keys.meta_range(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)]

Half open bounds on `key`'s own metadata subtree.

A key and its whole metadata subtree are one unit -- written together,
taken together by a plain delete, and contiguous in the order -- and this
is the stretch that unit occupies *below* the key itself. Every key in it
begins `key/!` and no other key does: a segment may begin with any
character from [`MIN_SEGMENT_CHAR`](#outrage.keys.MIN_SEGMENT_CHAR) up, so the ones below `!` sort
beneath the low bound and the ones above it at or past the high one.

Subtracting this from [`subtree_range()`](#outrage.keys.subtree_range) leaves exactly what a plain
delete would keep, which is what `descendant_count` reports.

Unlike [`subtree_range()`](#outrage.keys.subtree_range) **the root has bounds here.** Its metadata is
spelled with no leading delimiter -- `!title`, not `/!title` -- and is
an ordinary contiguous stretch of the order like anyone else's.

```pycon
>>> meta_range("a"), meta_range(ROOT)
(('a/!', 'a/"'), ('!', '"'))
```

### outrage.keys.meta_sort_suffix(meta_name: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

What to append to `sort_form(doc)` to get `sort_form(doc/!meta_name)`.

A caller that has a document's stored `sort_key` and wants to know where
its metadata *would* have sorted can append this rather than reparsing the
key. Exposed because the alternative is composing it by hand out of
`DELIMITER`, which silently stopped being the sort delimiter in schema 5
and put every synthesised position in the wrong place.

**One segment in, one segment out.** That is the contract, and a metadata
name is now one segment by construction, so there is no longer a name this
can be handed that it would mark and pad as though it were single. It was
silently wrong for the multi-segment names the old grammar allowed.

```pycon
>>> sort_form("a") + meta_sort_suffix("title") == sort_form("a/!title")
True
```

### outrage.keys.migrate_legacy(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

The current spelling of a key written with the pre-schema-4 `:` suffix.

Only for reading a store old enough to hold that spelling. `:` is an
ordinary segment character now, so this must not be applied to a key a
caller supplied -- it would rewrite one they meant literally.

```pycon
>>> migrate_legacy("context/5/state:title")
'context/5/state/!title'
```

### outrage.keys.normalise_key(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

`key` with its delimiters tidied: no leading, trailing or repeated `/`.

Runs before validation, so a key is judged in the form it will be stored
in. `"/"` and `"///"` reduce to the empty string, which is the root:
they are spellings of it rather than errors, which is what a key mirroring
a filesystem path ought to do.

```pycon
>>> normalise_key("/a//b/"), normalise_key("a/b"), normalise_key("///")
('a/b', 'a/b', '')
```

### outrage.keys.normalise_segment(segment: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

A numeric segment without its leading zeros; anything else unchanged.

This makes `01` and `1` the same segment rather than two, which is what
keeps a padded key from naming a second document alongside the one it was
meant to name, and what keeps the sort form injective.

```pycon
>>> normalise_segment("007"), normalise_segment("000"), normalise_segment("x0")
('7', '0', 'x0')
```

### outrage.keys.parse(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, allow_wildcard: [bool](https://docs.python.org/3/library/functions.html#bool) = False, allow_last: [bool](https://docs.python.org/3/library/functions.html#bool) = False, max_segments: [int](https://docs.python.org/3/library/functions.html#int) = MAX_SEGMENTS) → [Key](#outrage.keys.Key)

Parse and validate `key`.

With `allow_wildcard` a single segment of the document key may be `?`,
which the store replaces with a number it allocates. Reads and deletes
parse without it, so a wildcard cannot be mistaken for a search.

With `allow_last` a segment may be `?last`, which [`resolve_last()`](#outrage.keys.resolve_last)
replaces with the key that sorts last at that point. Only that function
passes it: refused by default, an unresolved `?last` reaching a store is
a loud failure rather than a document quietly written to a key spelled
`?last`, which is what it was before this segment meant anything. Several
are allowed, unlike `?`, because each is resolved against the key the one
before it produced and there is nothing to be ambiguous about.

`max_segments` defaults to the bound on a key **within one store**, which
is what almost every caller wants. Only a front end resolving a key across
a mount table passes `MAX_JOINED_SEGMENTS`, and it has to ask: defaulting
to the wider bound would let a store quietly accept a key too deep to be
named from a namespace it was mounted into, and that key would then be
invisible rather than refused. The tighter default fails in the safe
direction.

Raises InvalidKeyError if it does not match the grammar.

### outrage.keys.relative(key: [str](https://docs.python.org/3/library/stdtypes.html#str), scope: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Key](#outrage.keys.Key)

`key` parsed as it is named from inside `scope`.

The same operation a mounted store performs on every key that reaches it,
and the answer to every question a read has to ask *relative to what it was
scoped at*. [`parse()`](#outrage.keys.parse) splits a key at its **first** metadata segment,
which is the split seen from the root; a read scoped inside a metadata
namespace sees a different one, and this is it.

Three predicates come off the result, and between them they are what a
survey, a count and a delete each need:

* `meta_name is None` -- this key is a **document** at this scope. From
  `a` that excludes `a/!changelog/22`, which is why a survey descends
  into a metadata namespace only when it is scoped inside one.
* [`Key.is_meta_value`](#outrage.keys.Key.is_meta_value) -- this key is a metadata **value** at this
  scope, rather than something kept inside one.
* `doc_key != ROOT` -- a plain, non recursive delete of `scope` would
  **keep** this key. What it takes is the scope's own metadata subtree,
  and that is exactly the keys whose relative document part is empty.

`key` must be at or below `scope`; a key outside it has no reading
from there and raises.

From a scope holding no `!` this agrees with [`parse()`](#outrage.keys.parse) about the
metadata split, since the first metadata segment below such a scope is the
first one in the key. That is what lets a backend keep using its stored
columns for every ordinary scope and reach for this only when the scope is
itself metadata.

```pycon
>>> relative("a/b/!title", "a").doc_key
'b'
>>> relative("a/!changelog/22/!title", "a/!changelog").meta_name
'title'
>>> relative("a/!changelog/22", "a/!changelog").is_metadata
False
```

### outrage.keys.remaining_depth(budget: [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None), key: [str](https://docs.python.org/3/library/stdtypes.html#str), below: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None)

What is left of a depth budget measured from `key` once it reaches `below`.

A depth is counted in segments from the key a read was *asked* about, so a
traversal that descends into a store mounted further down has to hand that
store the part of the budget the descent did not spend -- and hand it as a
number measured from the mounted store's own root, which is where its keys
begin. Computed here, once, rather than at each traversal: the same
arithmetic written twice is how the root came to be depth 1 in SQL and
depth 0 in Python, which cost two silent defects
(`project/reference/planned/root-key/impact`).

Unlimited stays unlimited. A **negative** result means `below` already
lies past the budget, so nothing there is in scope -- not even its own row.
Zero is in scope and means only that row is.

```pycon
>>> remaining_depth(2, "", "ref"), remaining_depth(2, "a", "a/b/c")
(1, 0)
>>> remaining_depth(None, "", "ref"), remaining_depth(0, "", "ref")
(None, -1)
```

### outrage.keys.resolve_last(key: [str](https://docs.python.org/3/library/stdtypes.html#str), last_child: [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[str](https://docs.python.org/3/library/stdtypes.html#str)], [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)], \*, max_segments: [int](https://docs.python.org/3/library/functions.html#int) = MAX_SEGMENTS) → [str](https://docs.python.org/3/library/stdtypes.html#str)

`key` with every `?last` segment replaced by the last key at that point.

`notes/?last/state` becomes `notes/9/state` where 9 is the last key
below `notes`, in the order a listing walks -- so a numeric level gives
the highest number rather than the highest spelling, which is the whole
reason [`sort_form()`](#outrage.keys.sort_form) pads. It resolves against what *exists*, including
a key that holds nothing itself and is only there because something lies
beneath it: `context/?last` is the newest context whether or not anybody
wrote a document at it.

**Left to right, and one store call per \`\`?last\`\`.** An inner one cannot be
asked until the key above it is known, so `a/?last/?last` is two lookups
and the second depends on the first.

Keys with no `?last` are returned normalised and no lookup is made, so
every front end can call this on every key it is given.

`last_child` is the store's [`outrage.store.Store.last_child()`](store.md#outrage.store.Store.last_child), or a
mount table's, which is the same question asked of a whole namespace. It is
a parameter because this module knows nothing about stores and is not going
to start: what a key *is* has to stay decidable without opening one.

Raises InvalidKeyError when a `?last` has nothing below it to name. That
is a failed *read*, not a malformed key, but it is raised as one anyway:
the caller asked for a key and there is no key to give it, and inventing
one -- or resolving to the parent -- would silently answer a different
question.

```pycon
>>> resolve_last("a/?last/b", {"a": "9"}.get)
'a/9/b'
>>> resolve_last("a/b", {}.get)
'a/b'
```

### outrage.keys.sort_form(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

`key` encoded for ordering only, never stored in place of the key.

Three things happen at once, and each removes an ordering defect:

* numeric segments are zero padded, so `a/2` sorts before `a/10`.
  Plain text ordering gives the reverse, which is untidy in a listing and
  unsafe under a cursor: a reader resuming after `a/9` never sees
  `a/10`, because the new key sorts *behind* the one it was written after.
* every segment is marked as metadata or document, so a document's metadata
  sorts ahead of its subkeys.
* segments are joined by a delimiter below every character they may
  contain, so a subtree sorts immediately after its parent.
* the root sorts as the empty string rather than as one empty segment, so
  it comes before its own metadata and before every top level key. Marked
  as a segment it would sort *after* `!title`, the metadata marker being
  the lower of the two: the one place the marking would invert rather than
  order. Nothing can collide with it, since every other sort form begins
  with a marker.

The marking is a prefix rather than a property of the segment text, so two
different keys cannot share a sort form. That matters more than it looks:
pagination resumes with `sort_key > ?` over a non-unique index, so two
rows sharing a sort key would mean resuming past one silently skipped the
other.

```pycon
>>> sorted(["a/10", "a/2"]), sorted(["a/10", "a/2"], key=sort_form)
(['a/10', 'a/2'], ['a/2', 'a/10'])
>>> sort_form("a/!title") < sort_form("a/b/!title")
True
>>> sort_form("a/!title") < sort_form("a-x/!title")
True
>>> sort_form("") < sort_form("!title") < sort_form("a")
True
```

### outrage.keys.sort_subtree_end(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

The sort form immediately past everything at and below `key`.

[`subtree_range()`](#outrage.keys.subtree_range) bounds a subtree on `doc_key` and excludes the key
itself; this bounds it on `sort_key` and includes it, so
`sort_form(k) <= sort_key < sort_subtree_end(k)` is exactly `k`, its
metadata and its descendants -- one contiguous stretch of the order a
listing walks. That is what lets a caller name a range *around* a subtree
without naming a key that does not exist.

Every descendant continues `sort_form(k)` with `_SORT_DELIMITER`, and
every key that sorts after `k` without being one of its descendants has
to differ by then with a real segment character, which is higher still.
`_AFTER_SORT_DELIMITER` sits in the gap between the two.

**The root has no such bound**, for the reason [`subtree_range()`](#outrage.keys.subtree_range) gives:
everything is beneath it, and its sort form is the empty string rather than
a marked segment, so nothing can be appended to it that a descendant would
sort below. This raises rather than returning a bound that quietly matches
nothing.

```pycon
>>> sort_form("a") < sort_form("a/b") < sort_subtree_end("a")
True
>>> sort_subtree_end("a") < sort_form("a-x")
True
```

### outrage.keys.strip_prefix(prefix: [str](https://docs.python.org/3/library/stdtypes.html#str), key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)

`key` as named from inside `prefix`, or None if it is not below it.

The mount point itself maps to the root, which is the whole reason the root
had to become a key: a store mounted at `ref` has to be able to answer
for the document *at* `ref`, and that position is its own empty key.

Matching is by segment, not by character: `ref` does not contain
`reference`, however much the two strings look alike. That is the same
trap [`subtree_range()`](#outrage.keys.subtree_range) exists to avoid, and getting it wrong here would
route a key to a store that has never heard of it.

```pycon
>>> strip_prefix("ref", "ref/a"), strip_prefix("ref", "ref")
('a', '')
>>> strip_prefix("ref", "reference/a"), strip_prefix(ROOT, "a")
(None, 'a')
```

### outrage.keys.substitute_wildcard(key: [str](https://docs.python.org/3/library/stdtypes.html#str), segment: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

Return `key` with its `?` segment replaced by `segment`.

```pycon
>>> substitute_wildcard("context/?/design", "7")
'context/7/design'
```

### outrage.keys.subtree_range(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)]

Half open bounds on the document keys strictly beneath `key`.

Everything under `a` starts with `a/`, so `lo <= doc_key < hi`
selects exactly the subtree, as an index range scan rather than a prefix
match. This is what keeps `a/b` from picking up `a/beta`.

**The root has no such bounds.** Everything is beneath it, and no string
bounds every key from above. This raises rather than returning something
that looks usable, because the bounds the formula gives for it -- `"/"`
to `"0"` -- match nothing at all: a caller that forgot to check would get
a confident zero from a store full of documents. Select with no range
predicate instead, which is what `store` does.

### outrage.keys.with_prefix(prefix: [str](https://docs.python.org/3/library/stdtypes.html#str), key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [str](https://docs.python.org/3/library/stdtypes.html#str)

`key`, as seen from a namespace that holds it under `prefix`.

The inverse of [`strip_prefix()`](#outrage.keys.strip_prefix). Joining by hand is what this exists to
stop: the inner root is the empty string, so `prefix + "/" + key` spells
the mount point itself as `ref/`, which normalises back to `ref` only
if somebody remembers to normalise it.

```pycon
>>> with_prefix("ref", "a/b"), with_prefix("ref", ROOT), with_prefix(ROOT, "a")
('ref/a/b', 'ref', 'a')
```
