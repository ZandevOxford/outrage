Mount a store at `key`, for as long as this server runs.

The store answers for `key` and everything below it from the moment this
returns. A mount **shadows**: whatever the store beneath held at those keys is
never consulted while this is mounted, so it becomes unreachable rather than
merged, and the result says so when it happens.

`file` is a store file **relative to the store directory** — the same rule
every mount follows, and what makes a mount configuration relocatable. `info`
reports that directory. `type` names the backend where the file name cannot say
it: a directory of files has no extension to read.

Omit `file` to mount the store **outrage ships** for that key. Today that is
the `outrage` manual and nothing else. It is the way back after unmounting the
manual, which otherwise has no spelling here at all: it lives inside the
installed package rather than in the store directory. A shipped store is always
mounted read-only.

`read_only` refuses every write routed here, before the store is asked. It
refuses writes *through this server* and does nothing to the file, which stays
writable to anything else. A read-only mount must already exist: a mistyped
name would otherwise be created and read as though the reference base were
simply empty.

A mount at a point something already holds **replaces** it. The root cannot be
mounted over: it owns every key no mount claims, and the instructions this
connection was given were built from its readme.

Returns the whole table, not the one mount, because what shadows what is not
visible in an answer about a single mount. The change lasts as long as this
server; write it into the mount configuration file to keep it.
