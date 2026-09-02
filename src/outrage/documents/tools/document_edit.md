Take one document out for editing and put it back, so a long document can be
changed by shell tools without its unchanged text passing through the
context. A file is how the edit is carried, and a path handed back here is a
claim about what was edited rather than just a source of bytes.

**Omit `path` to export**: the whole document at `key` is
written to a file and the path returned, ready to be edited in place with
e.g. `sed`. Every export gets a file of its own, so a second session
exporting the same key cannot overwrite an edit you have not stored back.

**Pass `path` to import**: that file's content is stored at `key`, and the
answer reports both the size written and the size that was there before, so
an edit that truncated is visible. The path must be one this tool exported.

**A write that cannot be checked is refused**, as is one the check fails.
The check is the export record beside the file: it says what the document
held when it came out, so an import can tell whether somebody else has
written it since and refuse rather than lose their work. Export it again and
redo the edit, or pass `overwrite` if you have looked and mean to replace it.

**Importing to a different key is how content is copied around the store**,
and a file exported from one key says nothing about another. So either
export the target too and pass that file as `against` - the content then
comes from `path` and the check comes from `against`, and the copy is as
safe as saving back - or pass `overwrite` to write it unchecked.
