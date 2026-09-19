Read the document or metadata stored at a key.

Long documents are returned in slices. Continue with the matching value the
result supplies: `next_offset`, `next_byte_offset`, or `next_line`. A line read
that must stop part way through its first line has no `next_line`; continue it
with `next_byte_offset`.

To jump to a section, pass `pattern` as a literal substring to start the read
from, or use a character offset, UTF-8 byte offset, or 1-based line number from
the document's `!contents` metadata.
