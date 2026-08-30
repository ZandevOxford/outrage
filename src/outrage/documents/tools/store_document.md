Store a document or a metadata value at a key, overwriting whatever is there.
Content is markdown, JSON, plain text or HTML. A whole segment given as `?` is
replaced by a number the store allocates, so `tmp/?` writes to `tmp/1` in an
empty store; the returned `key` is the one actually written, and is what to use
for related keys afterwards. Pass `title` whenever you store a document: it is
what later sessions survey the store by, and a document stored without one is
hard to find again.
