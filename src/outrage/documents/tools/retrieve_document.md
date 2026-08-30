Read the document stored at a key. Long documents are returned in capped
slices: when `next_offset` is set, call again with that `offset` to continue.
To jump to a section, pass `pattern` as a literal substring to start the read
from.
