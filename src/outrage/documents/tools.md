# The tools, and which one answers which question

* `retrieve_document` - read one key, in full or from an offset or a pattern.
* `store_document` - write one key, with an optional title.
* `list_keys` - what is immediately below a key, subkeys and metadata alike.
* `get_documents` - read a whole subtree, or, with `meta_name`, survey it.
* `keys_missing_meta` - which keys in a subtree lack a piece of metadata.
* `delete_keys` - remove a key, or a subtree.
* `document_file` - put one document on disk and take it back, so the shell can
  edit it without the content passing through the context window.
* `copy_tree` - copy a subtree to another key, merging into whatever is there.
  `reroot` is what lands it *at* the new key rather than beneath its own source
  key, which is what moving a subtree means.

Every listing is a page rather than the whole store: each reports `returned`
beside `total`, and a `next_cursor` when more remains.

Each tool's full description is the document at its own key below this one.
Those documents are also the source the MCP server reads when it registers the
tools: editing one changes what a client is told the next time the server
starts. Argument descriptions remain on the tool schema itself.
