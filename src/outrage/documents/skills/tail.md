A segment may hold almost any text - the exclusions are `/`, the control
characters below tab, and a leading `?`, which is reserved for `?` and `?last`
and for the filters a key will grow - so a key can mirror a real name without
transforming it. Keys are not file paths, but they read like them: notes about a file can
live at `notes/src/myfile.py`. Inside a metadata namespace everything is an
ordinary namespace again - documents, `?`, `?last` and their own metadata - so
`a/!changelog/22` is a document kept in `a`'s changelog, and `a` carries
`changelog`, not `changelog/22`. Only the segments before the first `!` count
towards depth, so a survey reaches a namespace's contents by being scoped
inside it rather than by asking for more depth.

A survey also reports the untitled documents under `without_meta`, as a count
and a few examples covering the same stretch of the store as the page itself.
It is stats, not a listing, so it carries no cursor: page the survey and the
windows tile; to enumerate what it counts, call `keys_missing_meta`.

Prefer several small documents to one large one. A document should answer one
question and be readable in a single call, and a key can hold content *and*
have keys beneath it, so a general document can stay where it is with the
detail below it. When there is more to add, add a document rather than growing
one - `?` allocates the key, so this costs no naming decision.

A key that holds nothing itself but has keys beneath it is a container: reading
it fails, listing it does not.

`?last` in place of a whole segment names the key that sorts last there, so
`context/?last/state` reads the newest context without looking the number up
first. It works on any key a tool takes, counts containers, and the result says
which key it resolved to.

The empty key is the root, and omitting a key means the same thing. It holds a
document like any other key and carries metadata as `!title`, so a store can
title itself. Nothing else about it is special, and by convention nothing much
is kept there.

The document at `readme` is a store's entry point: what that particular store
holds, and what to read before anything else. It is carried at the top of these
instructions when there is one, so a session starts with it rather than having
to know to ask. If you work out how a store is organised, or what a later
session should read first, `readme` is where that belongs.
