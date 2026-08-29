A store for notes, designs and task context that outlives a single session.

Keys are hierarchical, slash delimited strings such as `context/<id>/design`,
and `/` is the only separator there is. A segment beginning with `!` opens a
metadata namespace on the key above it, such as `context/<id>/design/!title`.
Intermediate keys exist implicitly; nothing needs creating before writing
beneath one.

When storing, a `?` in place of a whole segment asks the store to allocate a
number for it, at any depth: `context/?/design` writes to `context/1/design` in
an empty store. The result reports the key actually written, which is what to
use for anything else belonging with it, such as `context/1/task`.

Store a document under a descriptive key and pass a `title`, so that later
sessions can survey what is here with `get_documents(meta_name=["title"])`
before reading anything in full.

Every listing is a page, not the whole store. Each one reports `returned`
beside `total`, and a `next_cursor` when more remains: pass it back as `after`
to continue from exactly where the page stopped. Read `total` before treating a
result as everything there is - 20 of 22 is a listing, 20 of 40000 is a sample.
