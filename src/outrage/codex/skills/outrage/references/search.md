# Search the store

Search by screening each document at the cheapest useful level, starting with
metadata and reading full documents only when needed. Inputs are a required
query, an optional subtree key, and metadata levels that default to `title`,
then `summary`.

For each document, decide `likely`, `unlikely`, or `unclear`. Only unclear
documents continue to the next level.

1. Fetch one metadata name per call, for example
   `get_documents(key=..., meta_name=["title"], max_chars=4000)`. Screen the
   whole returned page, then follow `next_cursor` until it is null. Never ask
   for title and summary in one call: `without_meta` would then omit documents
   carrying one but not the other, and the larger response is likelier to
   truncate.
2. Treat missing metadata as unclear, never absent. `without_meta` applies to
   that page's window, so add it across every page. To enumerate the missing
   keys, use `keys_missing_meta` with one metadata name.
3. Fetch the next metadata level only for documents still unclear. Ignore
   already-decided documents. If returned metadata is truncated, re-read it or
   leave the document unclear; never reject a document based on a truncated
   value.
4. Read each document still unclear with
   `retrieve_document(key=..., max_chars=20000)`, following `next_offset` to
   the end. If more than 15 remain, read the 15 most promising and explicitly
   name the remainder as unread.

Report likely matches, best first, with the key, confidence and deciding level,
and one relevant line. Also report how many documents were screened at each
level, how many needed a full read, and any range left unread or unscreened.
