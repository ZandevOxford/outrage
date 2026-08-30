Read every document at and below a key. Pass `meta_name` to get that metadata
across the subtree instead, which is the cheap way to survey what is stored:
`get_documents(key='context', meta_name=['title'])` lists the titles of
everything under `context`. Each document is truncated to `max_chars`; use
retrieve_document to read one in full. The page holds at most 100 documents
and 20000 characters in total, whichever comes first, so a survey of short
metadata usually arrives whole while a read of real documents does not:
compare `returned` with `total`, and pass `next_cursor` back as `after` to
continue from where it stopped. With `meta_name`, `without_meta` counts the
documents in this same page's window that carry none of it - what the survey
structurally cannot show. It is always present, and describes exactly the
stretch this page covers, so paging the survey tiles those windows without gap
or overlap. Use keys_missing_meta to list them.
