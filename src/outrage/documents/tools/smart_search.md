Find which documents under a key are about a query, without reading them
yourself. A small classification model judges each document in the slice on
its `!title`, then `!keywords`, `!summary`, `!contents` and finally its body,
and carries a document to the next level only while the evidence so far leaves
it unsure. The result is every document not ruled out, best first, with the
combined probability and what each level said.

**Document text leaves this machine**: it is sent to the configured System One
service (TypeSafe's Jev by default) to be judged. Do not search content that
must stay local.

The slice is a page of the subtree's documents, `limit` of them, as
`get_documents` would page it; pass `next_cursor` as `after` for the next
slice. A result cannot itself be paged, so `limit` is what bounds it. A
document without some metadata goes on to the next level unchanged, and a title
or keywords can count for a document but never rule it out. `levels` narrows or
reorders the cascade, for example `["title", "summary"]` to screen on metadata
alone.

It is slower than the other tools, seconds to a minute for a slice of a
hundred, and bodies take most of that. Documents whose requests failed are
listed in `unjudged` with the reason, not dropped. The probabilities rank
documents; treat them as a ranking rather than as calibrated.
