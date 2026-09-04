Search document bodies or their direct metadata values with one to five
criteria. Each criterion targets `document` or `metadata` and uses
case-sensitive `contains`, whole-`line`, or Python `regex` matching. Use
`meta_name` to restrict a metadata criterion to selected names. A `regex` is
your expression exactly as written, so in a document holding CRLF a `$` sits
after the carriage return and matches nothing; `line` strips every ending
before comparing.

`combine='any'` selects a document satisfying at least one criterion;
`combine='all'` requires every criterion. Results contain the selected document
and one first-match witness for each satisfied criterion.

Each call examines at most 20 candidate documents by default. `next_cursor`
names the last candidate examined, so a page can have no matches and still need
continuing. Pass it as `after` until `next_cursor` is null.
