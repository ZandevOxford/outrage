A RAG store to use as a memory and reference.

Keys are hierarchical strings, with path segments delimited with `/`.
Segments which start with `!` indicate metadata of the parent, for
example `document/!title` is the `document` title. Keys above in the
hierarchy exist implicitly and do not need creating.

When storing a document, a segment `?` assigns an auto-incremented id.
For example `context/?/design` may create `context/1/design`. This key name
is reported. These always sort in order of creation.

Most tools are paged. Pass `next_cursor` as `after` for the next page.
Statistics including `total` are reported to allow paging decisions.

Where appropriate, store title metadata, which can be surveyed with
`get_documents(meta_name=["title"])`.

For a large store, first use `list_keys` with `descendant_counts` to find the
large branches, then narrow the survey. Metadata `coverage` scans the whole
selection, so ask for it only when needed and only once while paging.

All unicode characters are valid in a segment except control characters
below \x09, so most file paths can be mirrored. Segments starting with
`?` are reserved.

Projects will have their own conventions, so read the `readme` key
first.

Key depth is a count of path segments, except that a metadata segment
and below does not count, so metadata is selected along with the document.

For all tools `?last` in place of a whole segment names the key that sorts
last there, so `context/?last/state` reads the newest context.

The empty key is a valid root document.
