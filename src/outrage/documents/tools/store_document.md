Store (overwrite) a document or metadata value at a key.

Content is markdown, JSON, plain text or HTML.

When appropriate, supply `title` which will be stored in the `/!title` key
below.

Use the `?` auto-increment path segment to add documents with incrementing
ids. This is safe to use across parallel agents.

**Pass `against` when you are storing back a document you read out with
`document_edit`** and edited here rather than on disk. It is that exported
file's path; only its record is read, never its content, and the write is
refused if somebody else has written the document since it came out. Without
it this call overwrites whatever is there.
