Move one document between the store and a file, so a long document can be
edited by shell tools without its unchanged text passing through the
context.

**Omit `path` to export**: the whole document at `key` is
written to a file and the path returned, ready to be edited in place with
e.g. `sed`. Every export gets a file of its own, so a second session
exporting the same key cannot overwrite an edit you have not stored back.

**Pass `path` to import**: that file's content is stored at `key`, and the
answer reports both the size written and the size that was there before, so
an edit that truncated is visible. The path must be one this tool exported,
but the keys do not need to match, so this can copy data.

**A document written by somebody else since you exported it refuses the
import** rather than losing their work: export it again and redo the edit, or
pass `overwrite` if you have looked and mean to replace it. Only a file
exported from the key being written can be checked this way.
