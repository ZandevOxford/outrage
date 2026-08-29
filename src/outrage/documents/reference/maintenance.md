# outrage.maintenance

Inspecting and repairing a store from outside an agent session.

The server has no reason to offer any of this. A session asks the store
questions about documents; these are questions about the *store* - whether the
rows still satisfy the invariants they were written under, whether the format
version is one this build understands, and whether the storage underneath them
is sound.

That last one is the only part a backend has to answer for itself, and the
split is the point of this module. Five of the questions a check asks are
about **rows and keys**: how many there are, whether any key is deeper than
[`outrage.keys.MAX_SEGMENTS`](keys.md#outrage.keys.MAX_SEGMENTS), whether each row's stored `parent` still
agrees with the key it was derived from, whether any metadata has no document,
and whether the file was written by a newer outrage than this. None of those is
SQLite's, and a backend keeping its rows some other way has the same
invariants to break. They are asked here, once, over
[`audit_rows()`](store.md#outrage.store.FileStore.audit_rows).

What is left really is the backend's, and is asked through
[`check_file()`](store.md#outrage.store.FileStore.check_file): SQLite's own integrity check and the
size of its write-ahead log, a parquet file's sort order. Neither has any
meaning for the other, which is why neither is here.

The write-ahead log is worth naming because it is the same trap `backup`
exists for, seen from the other end. A SQLite store in WAL mode can hold
almost nothing in `store.sqlite` and megabytes in `store.sqlite-wal`, and
it opens and reads perfectly that way - so nothing in normal use reveals it,
and anything copying the file alone gets a store missing its recent history.
`check` reports the split; `--repair` folds it back.

Nothing here is destructive. A repair moves bytes about and never changes a
document; one that could lose content would need a backup taken first, and no
backend offers such a repair.

### *exception* outrage.maintenance.CheckError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`RuntimeError`](https://docs.python.org/3/library/exceptions.html#RuntimeError)

Raised when a store cannot be checked at all.

### *class* outrage.maintenance.Problem(severity: [str](https://docs.python.org/3/library/stdtypes.html#str), summary: [str](https://docs.python.org/3/library/stdtypes.html#str), detail: [str](https://docs.python.org/3/library/stdtypes.html#str) = '', repairable: [bool](https://docs.python.org/3/library/functions.html#bool) = False)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Something wrong, or worth knowing, about the store rather than a document.

`severity` is 'error' for a store that is damaged or unreadable by this
build, 'warning' for something that will cause a wrong answer later, and
'note' for a fact worth reporting that is not itself a fault.

`repairable` is set by whoever raises the problem, because that is the
only place the answer is known: a backend appending this from
[`check_file()`](store.md#outrage.store.FileStore.check_file) knows whether its own
[`repair()`](store.md#outrage.store.FileStore.repair) acts on it, and nothing above can. It
defaults to False so that a problem nobody thought about cannot claim to
be fixable.

#### severity *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### summary *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### detail *: [str](https://docs.python.org/3/library/stdtypes.html#str)* *= ''*

#### repairable *: [bool](https://docs.python.org/3/library/functions.html#bool)* *= False*

### *class* outrage.maintenance.Repaired(action: [str](https://docs.python.org/3/library/stdtypes.html#str), before: [int](https://docs.python.org/3/library/functions.html#int), after: [int](https://docs.python.org/3/library/functions.html#int))

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

What a repair actually did, in bytes rather than in claims.

#### action *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### before *: [int](https://docs.python.org/3/library/functions.html#int)*

#### after *: [int](https://docs.python.org/3/library/functions.html#int)*

### *class* outrage.maintenance.Report(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), backend: [str](https://docs.python.org/3/library/stdtypes.html#str) = '', format_version: [int](https://docs.python.org/3/library/functions.html#int) = 0, documents: [int](https://docs.python.org/3/library/functions.html#int) = 0, metadata: [int](https://docs.python.org/3/library/functions.html#int) = 0, characters: [int](https://docs.python.org/3/library/functions.html#int) = 0, details: dict[str, str]=<factory>, problems: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Problem](#outrage.maintenance.Problem)] = <factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

What a check found. Empty `problems` is a sound store.

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

#### backend *: [str](https://docs.python.org/3/library/stdtypes.html#str)* *= ''*

What kept the file: 'sqlite', 'parquet'. Named because the rest of the
report reads differently depending on the answer, and because a report that
did not say would look identical for a store nothing could check.

#### format_version *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*

#### documents *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*

#### metadata *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*

#### characters *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*

#### details *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)]*

What this backend says about its own storage, label to value, in the
order it is worth printing. Filled by
[`check_file()`](store.md#outrage.store.FileStore.check_file). A mapping rather than fields, so
that the numbers SQLite has and parquet does not are absent rather than
zero -- a report reading `0 bytes in the log` for a store that has no log
is a wrong answer delivered as a clean bill of health.

#### problems *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Problem](#outrage.maintenance.Problem)]*

#### *property* sound *: [bool](https://docs.python.org/3/library/functions.html#bool)*

No errors and no warnings. Notes do not make a store unsound.

#### *property* repairable *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Problem](#outrage.maintenance.Problem)]*

The problems `--repair` would actually act on, in the order found.

A subset of [`problems`](#outrage.maintenance.Report.problems), and usually a strict one. A damaged file
or a schema from a newer build is reported and left alone, because the
repairs move where the bytes live and nothing else. An empty list is
what stops `outrage check` offering `--repair`.

### outrage.maintenance.check(store: [FileStore](store.md#outrage.store.FileStore)) → [Report](#outrage.maintenance.Report)

Ask whether the store is what it should be.

Read-only, and answerable for any backend. It runs against an open store
rather than a path because the invariants being checked are the ones the
backend writes rows under, and opening through it is also what proves the
file opens at all.

### outrage.maintenance.repair(store: [FileStore](store.md#outrage.store.FileStore)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Repaired](#outrage.maintenance.Repaired)]

Fix what a check found and the backend can act on.

A thin pair for [`check()`](#outrage.maintenance.check), and here rather than left as a method so
that a caller doing maintenance reaches for one vocabulary throughout.
Returns what was done, which is an empty list for a backend whose storage
cannot get into a repairable state -- see
[`repair()`](store.md#outrage.store.FileStore.repair).

### outrage.maintenance.require_store(directory: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), filename: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

Refuse a store file that is not there, rather than creating one.

`FileStore.__init__` creates what is missing, so every command that means to
act on an existing store has to ask first - otherwise checking a mistyped
path reports a perfectly healthy empty store, which is the wrong answer
delivered as a clean bill of health.

Names the file, not just the directory: since a directory holds several
stores, "no store in .outrage" would be the wrong sentence as often as it was
the right one.
