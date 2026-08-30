# Search the store

Find documents bearing on a question by judging each at the cheapest level
that can decide it. Inputs are a required query, an optional subtree key, and
metadata levels that default to `title`, then `summary`.

For every document decide `likely`, `unlikely`, or `unclear`. Include likely
documents, exclude unlikely ones, and move only unclear documents to the next
level. If everything is deferred, the cascade has saved nothing.

## Procedure

1. Fetch one metadata name per call, for example:

   ```text
   get_documents(key=<key>, meta_name=["title"], max_chars=4000)
   ```

   Judge the whole returned page, then follow `next_cursor` with `after` until
   it is null. If the whole subtree is not screened, report the exact range
   that was. Never combine metadata names: `without_meta` would then identify
   only documents missing all the names and conceal a document missing one.

2. Treat missing metadata as unclear, never absent. `without_meta` describes
   only its page's window, so account for it on every page. To enumerate the
   missing keys, page through `keys_missing_meta` with one metadata name.
   Metadata keys have the form `<document key>/!<name>`.

3. Fetch the next metadata level only for still-unclear documents, ignoring
   entries for documents already decided. A truncated metadata value cannot
   justify `unlikely`: re-read it or leave that document unclear.

4. Read each document still unclear with:

   ```text
   read_document(key=<document key>, max_chars=20000)
   ```

   Follow `next_offset` to the end. If more than 15 documents remain, read the
   15 most promising and explicitly name the remainder as unread.

## Report

List likely matches best first. Give each key, confidence and deciding level,
plus one line explaining its relevance. Also report the documents in range,
how many were screened out at each level, how many needed a full read, and any
range left unread or unscreened. If nothing matched, say what was searched and
how many documents it covered. Mention widespread missing metadata because a
backfill could make later searches cheaper and more reliable.
