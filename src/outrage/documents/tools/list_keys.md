List the keys immediately below a key, including subkeys and metadata. Omit the
key to list the top level. Keys of kind 'implicit' hold no content themselves
but have something beneath them. A key of kind 'mount' is where another store
is mounted, and 'read-only mount' is one that refuses writes; either reads,
lists and is searched like any other key, so nothing has to be asked twice.
Returns at most 100 keys: compare `returned` with `total` to see whether that
was the whole level, and pass `next_cursor` back as `after` to continue.
