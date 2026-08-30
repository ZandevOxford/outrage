Read every document at and below a key.

Pass `meta_name` to get that metadata across the subtree instead, for example
`get_documents(key='context', meta_name=['title'])` lists the titles of
everything under `context`.

Pages hold at most 100 documents and 20000 characters. Pass `next_cursor` as
`after` for the next page.

Documents may also be truncated. If this is reported and you need the
whole document, use `read_document` on that document.
