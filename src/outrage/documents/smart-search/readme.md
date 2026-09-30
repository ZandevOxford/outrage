# Smart search tuning

`tuning.json`, beside this document, holds everything about smart search that
is a number or a sentence rather than a rule: which metadata the cascade reads
and in what order, the question put to the model at each level, the constants
that turn answers into a decision, and how much is read and sent at once. It is
served here as `outrage/smart-search/tuning`, so it can be read like the rest
of the manual.

**What the search uses is the file in the installed package**, read when smart
search starts rather than through this mount. A mount table naming `outrage`
therefore changes what you read here but not how search behaves. To change the
tuning, edit `src/outrage/documents/smart-search/tuning.json` in a checkout
and restart whatever runs the search.

The rules themselves stay in code: how the per-level answers are combined,
that the best chunk of a body stands for the whole body, that missing metadata
leaves a document unsure, and that partial evidence cannot count against a
document. The file chooses among them by name and supplies their numbers. It
cannot define a new rule.

## How the cascade uses it

Every document in a slice is judged at the first level. The answers so far are
combined into one probability. At or above `yes` a document is a match and
stops. At or below `no` it is ruled out. Anything between goes on to the next
level. What comes back is every document not ruled out, best first, with the
evidence from each level it reached.

## The file

Any object may carry a `note` string, which the loader ignores. Use it for the
short reason beside a number, and leave the longer account to this document.
Any other name the loader does not know is refused rather than ignored, so a
misspelt `weigth` is reported instead of silently doing nothing.

### `format`

The layout version, `1`. A file naming another is refused.

### `question`

The default question, used at every level that does not override it.

* `kind` — `score` asks the model to place the document on the ordered
  `criteria` and answers a probability for each. `noul` asks for a single
  probability of yes and ignores `criteria`. Switching between them is this one
  field.
* `criteria` — for `score`, what each tier means, lowest first, two to ten of
  them. A score answer becomes a probability as its expected tier scaled to 0–1,
  so a document the model splits between two tiers sits between them.
* `questions` — the text asked in the `questions` shape, where the query is the
  state and the document is in the question's instructions. It may name
  `{level}`, the level's name, which is also the name the value is sent under,
  and `{what}`, the level's description. It must not name `{query}`, since the
  query is already the state.
* `state` — the text asked in the `state` shape, where the document's value is
  the state. It may name `{level}` and `{what}`, and must name `{query}`, where
  the search query goes.

Write a literal brace as `{{` or `}}`.

### `levels`

The cascade, in order. Each level is an object with the following fields:

* `name` — what the level is called in a result and in a request's `levels`.
  It must be a valid metadata name, and no two levels may share one.
* `kind` — what the level reads, which is behaviour the file can choose but not
  define:
  * `value` reads one metadata value, `!<meta>`. A value longer than
    `value_chars` is judged on its first part and marked partial.
  * `contents` reads `!contents` and judges its headings alone, the offset lines
    being meaningless to a model. The offsets are kept to cut the body into
    chunks on section boundaries. At most one level has this kind.
  * `body` reads the document itself, in chunks, and the best chunk is the
    evidence. At most one level has this kind, and it must use the `state`
    shape, since a body is too long to sit in a question.
* `meta` — the metadata name a `value` or `contents` level reads, without its
  `!`. Defaults to `name`, so adding `!tags` as a level is a new entry here and
  no code. A `body` level has none.
* `what` — how the question describes what is being judged, filling `{what}`.
* `shape` — `questions` puts the query in the state and one document in each
  question, so one request judges up to `batch_size` documents. `state` puts
  the document in the state and the query in its one question, which is one
  request per document.
* `weight` — how much the level's answer counts, zero or more (see
  `scoring`).
* `supporting` — `true` if the level's answer can count for a document and
  never against it. Defaults to `false`.
* `question` — optional, and any of the default `question`'s fields, which
  override the default for this level alone. For example, a body could be given
  its own `criteria`.

### `scoring`

* `rule` — how the levels' answers are combined. `log-odds-sum` is the only
  rule. Each level adds `weight × logit(p)`, scaled by the answer's confidence
  where it has one, and the probability is the sigmoid of the total. A
  `supporting` level's contribution, or a partial one's, is floored at zero.
  Two near misses therefore add up to more than either alone. Weights below
  one damp the overlap between levels, since a title and a summary written
  together say much the same thing.
* `yes` — at or above this, a document is a match and stops cascading.
* `no` — at or below this, a document is ruled out. It must be below `yes`.
* `clamp` — how close to 0 or 1 an answer is taken to be, so that a certain
  answer adds a large but finite amount. Between 0 and 0.5.

### `requests`

Every size is a whole number, one or more.

* `limit` — documents in one slice, the default when a caller names none. The
  server keeps no state, so a slice's result cannot itself be paged; the caller
  asks for the next slice instead.
* `batch_size` — documents judged in one `questions` request. Each question
  is evaluated on its own, so this bounds the request rather than what the
  model weighs together.
* `value_chars` — the longest metadata value read for judging.
* `chunk_chars` — characters of body in one request.
* `max_chunks` — body chunks judged per document before the rest is left
  unread. A document cut short this way is partial, so it can be kept but not
  ruled out.
* `min_chunk_chars` — a chunk the model refuses as too large is halved and
  asked again, down to this. Below it the document is reported as unjudged
  rather than split into fragments. At most `chunk_chars`.

## What is measured and what is guessed

The first live evaluation used the shipped manual: 71 documents, three
labelled queries and Jev as the model. It settled three things:

* **Score over Noul.** Score was best or equal at nearly every level, was the
  only question kept every relevant document, and read the fewest bodies.
* **Title and keywords are `supporting`.** A title labels a document rather
  than describing it, so a generic one, such as a module name or a project's
  name, gets a low answer rather than an unsure one. Counted against, a single
  such answer ruled out the best document for a query. Keywords are written
  for the same purpose and follow the same rule.
* **The level order.** A body was the best single judge in that evaluation,
  contents was next and titles were nearly useless. The cheap levels are
  there to save body reads, not to rule documents out. Summary comes before
  contents because it is shorter and says what a document is for.

`chunk_chars` is derived rather than measured. Jev accepts 32k tokens for the
state and the longest question together, and English runs at about four
characters a token. 60000 leaves room for the question and for text that
tokenises badly.

Everything else is a guessed starting point: the weights, `yes`, `no`, `clamp`
and the other sizes. Score answers were seen to saturate, with the top results
at 0.99, so its thresholds want tuning of their own.

## How to tune

1. **Keep the evidence.** A result carries every level's answer for every
   document it kept, so a run over labelled queries can be saved once and
   re-scored many times.
2. **Re-score without the model.** Load an edited file with
   `Tuning.read_file(path)`, and apply its `scoring` to the kept evidence.
   Changes to `weight`, `supporting`, `yes`, `no` and `clamp` cost nothing to
   try this way. Changes to the questions, the levels or the sizes change what
   the model is asked, and need a new run.
3. **Live-test the result.** Run a known query through both the MCP tool and
   `outrage smart-search`, and check that the documents that should come back
   do.
