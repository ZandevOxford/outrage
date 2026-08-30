Move one document between the store and a file, so a long document can be
edited by shell tools without its unchanged text passing through the
context.

**Omit `path` to export**: the whole document at `key` is
written to a file and the path returned, ready to be edited in place with
e.g. `sed`.

**Pass `path` to import**: that file's content is stored at `key`, and the
answer reports both the size written and the size that was there before, so
an edit that truncated is visible. The path must be one this tool exported,
but the keys do not need to match, so this can copy data.
