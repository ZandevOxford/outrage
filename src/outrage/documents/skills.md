# The instructions the server delivers

The documents below this key are not *about* the MCP server's instructions.
They **are** them: `outrage.server` reads these files out of the installation
at import and sends them, unchanged, as the text a client is given when it
connects. Edit one and you have edited what every session is told.

Kept here rather than inline in `server.py` for the ordinary reason - prose
belongs in a document, where it is diffable, readable and reachable by the same
`retrieve_document` as anything else - and for one particular to this store: a
session that was cut off mid-instructions can read the rest at
`outrage/skills/tail` instead of guessing at what it did not get.

## The two halves, and why there are two

A client cuts a server's instructions at a length it does not announce. The
split is a delivery order, not a subject:

* `outrage/skills/essentials` - the key grammar, `?` allocation, `title`, and
  that every listing is a page. Sent first, after the root store's own
  `readme`, because a session that gets this and nothing else can still read
  and write correctly.
* `outrage/skills/tail` - metadata namespaces, `?last`, containers, the root
  key, `without_meta`, and what a `readme` is for. Sent last, because every
  part of it is recoverable somewhere a session reaches anyway: a tool
  description, the packaged skill, or a failure that explains itself.

That test - *is this recoverable elsewhere?* - is the whole of what decides
which file a sentence goes in.

## Before editing either

Both are paid for out of one budget, and the readme carried above them is paid
for out of what is left. Growing `essentials` shrinks the store's own entry
point, which is the failure this ordering exists to prevent, so
`tests/test_server.py` holds a floor for the readme and fails when the static
text grows back over it. `outrage/reference/server` has the constants and the
arithmetic.
