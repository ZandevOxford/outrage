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

### outrage.maintenance.DATABASE_DAMAGED *= 'database-damaged'*

The storage itself reports the file as damaged.

### outrage.maintenance.FILES_NOT_KEYS *= 'files-not-keys'*

Files in a directory store whose names do not map to a key.

### outrage.maintenance.FILES_NOT_TEXT *= 'files-not-text'*

Files in a directory store that are not UTF-8 text.

### outrage.maintenance.FORMAT_OLDER *= 'format-older'*

A store older than this build's format, which a writable backend migrates
when it opens it. Not a fault.

### outrage.maintenance.FORMAT_TOO_NEW *= 'format-too-new'*

A store written by a build newer than this one, which cannot read it safely.

### outrage.maintenance.KEYS_DOUBLED *= 'keys-doubled'*

One key held by more than one file, where only the first can be read.

### outrage.maintenance.KEYS_TOO_DEEP *= 'keys-too-deep'*

Keys with more segments than [`outrage.keys.MAX_SEGMENTS`](keys.md#outrage.keys.MAX_SEGMENTS) allows.

### outrage.maintenance.LENGTH_CACHE_STALE *= 'length-cache-stale'*

Cached document lengths describing documents that have since changed.

### outrage.maintenance.METADATA_WITHOUT_DOCUMENT *= 'metadata-without-document'*

Metadata whose document does not exist. Legal, and worth naming.

### outrage.maintenance.PROBLEM_CODES *= ('format-too-new', 'format-older', 'keys-too-deep', 'rows-under-wrong-key', 'metadata-without-document', 'database-damaged', 'length-cache-stale', 'wal-uncheckpointed', 'files-not-keys', 'keys-doubled', 'files-not-text', 'rows-out-of-order')*

Every code above. For a caller deciding what it can act on, and for the
guard in `tests/test_maintenance.py` that keeps the list complete: a code
constant this does not name is one nothing has agreed to.

### outrage.maintenance.ROWS_OUT_OF_ORDER *= 'rows-out-of-order'*

Rows not in sort order, which every read bisects and so answers wrongly.

### outrage.maintenance.ROWS_UNDER_WRONG_KEY *= 'rows-under-wrong-key'*

Rows whose stored `parent` disagrees with the key they are stored under.

### outrage.maintenance.WAL_UNCHECKPOINTED *= 'wal-uncheckpointed'*

More of the store is in the write-ahead log than in the database file, so
anything copying that file alone gets a store missing recent writes. The one
problem `repair` acts on.

### *exception* outrage.maintenance.CheckError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`RuntimeError`](https://docs.python.org/3/library/exceptions.html#RuntimeError)

Raised when a store cannot be checked at all.

### *class* outrage.maintenance.Problem(code: [str](https://docs.python.org/3/library/stdtypes.html#str), severity: [str](https://docs.python.org/3/library/stdtypes.html#str), summary: [str](https://docs.python.org/3/library/stdtypes.html#str), detail: [str](https://docs.python.org/3/library/stdtypes.html#str) = '', repairable: [bool](https://docs.python.org/3/library/functions.html#bool) = False)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Something wrong, or worth knowing, about the store rather than a document.

`code` names *which* problem this is, one of [`PROBLEM_CODES`](#outrage.maintenance.PROBLEM_CODES), and
is what a caller with something to do about a particular fault selects on.
First, as it is on [`OutrageError`](errors.md#outrage.errors.OutrageError) and
[`Note`](notes.md#outrage.notes.Note), and for the same reason: what a thing is
comes before how it reads.

`summary` and `detail` are that same problem as prose, and they are the
report -- `outrage check` prints them and nothing else consumes them.
They stay where the fault is found rather than moving to a wording table,
because there is one reader of them; a second one would change that answer.
Nothing should match on them.

`severity` is 'error' for a store that is damaged or unreadable by this
build, 'warning' for something that will cause a wrong answer later, and
'note' for a fact worth reporting that is not itself a fault.

`repairable` is set by whoever raises the problem, because that is the
only place the answer is known: a backend appending this from
[`check_file()`](store.md#outrage.store.FileStore.check_file) knows whether its own
[`repair()`](store.md#outrage.store.FileStore.repair) acts on it, and nothing above can. It
defaults to False so that a problem nobody thought about cannot claim to
be fixable.

#### code *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### severity *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### summary *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### detail *: [str](https://docs.python.org/3/library/stdtypes.html#str)* *= ''*

#### repairable *: [bool](https://docs.python.org/3/library/functions.html#bool)* *= False*

### *class* outrage.maintenance.Repaired(action: [str](https://docs.python.org/3/library/stdtypes.html#str), before: [int](https://docs.python.org/3/library/functions.html#int), after: [int](https://docs.python.org/3/library/functions.html#int), unit: [str](https://docs.python.org/3/library/stdtypes.html#str) = 'bytes')

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

What a repair actually did, measured rather than claimed.

`unit` is what `before` and `after` are counted in. It exists because
the vocabulary started out assuming every repair moves bytes about inside a
file, which was true while the only repairs were a checkpoint and a
compaction, and stopped being true for one that drops rows: a count of
three rows printed as "3 bytes" is a sentence that reads correctly and
says something false.

#### action *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

#### before *: [int](https://docs.python.org/3/library/functions.html#int)*

#### after *: [int](https://docs.python.org/3/library/functions.html#int)*

#### unit *: [str](https://docs.python.org/3/library/stdtypes.html#str)* *= 'bytes'*

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
