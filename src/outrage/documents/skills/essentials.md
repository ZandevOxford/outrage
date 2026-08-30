A RAG store to use as a memory and reference.

Keys are hierarchical strings, with path segments delimited with `/`. Path
segments which start with `!` indicate metadata of the parent key, for
example `document/!title` is the title of `document`. Folders for content
exist implicitly by name and do not need creating.

When storing a document, a path segment `?` assigns an auto-incremented id
for example `context/?/design` may create `context/1/design`. This key name
is reported. These always sort in order of creation.

Most tools are paged. Pass `next_cursor` as `after` for the next slice.
Statistics including `total` are reported to allow paging decisions.

Where appropriate, store title metadata, which can be surveyed with
`get_documents(meta_name=["title"])`.
