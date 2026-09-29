# outrage.smartsearch

Screen a bounded slice of documents against a query with a System One
judge. A configurable cascade examines progressively richer metadata and then
the body, retaining the evidence used to rank every document not ruled out.

The cascade the `outrage-search` agent follows, moved out of an agent's
context and into the library: every document in the slice is judged on its
`!title` first, and only the ones that level leaves unsure go on to its
`!keywords`, its `!summary`, then its `!contents`, then its body. What comes back is every
document not ruled out, best first. The calling agent reads none of it.

**The judging is not done here.** A [`Judge`](#outrage.smartsearch.Judge) answers questions about a
piece of state -- the protocol System One models speak -- and this module
decides what to ask, of which documents, and what the answers add up to. So the
suite runs against a fake, and a second model or a local server is a different
judge rather than a different cascade.

Three things here are expected to change as the cascade is measured, and each
is kept in one place so that tuning it touches nothing else:

* **the question asked at each level** is data, [`SCORE_QUESTIONS`](#outrage.smartsearch.SCORE_QUESTIONS) by
  default and [`NOUL_QUESTIONS`](#outrage.smartsearch.NOUL_QUESTIONS) as the alternative, since what a title can
  show is not what a body can;
* **which way round** a level is asked -- the query as the state and many
  documents as the questions, or each document as the state and the query as
  its one question -- is a [`Shape`](#outrage.smartsearch.Shape) per level, and the body is always the
  second, being too long to sit in a question;
* **how the per-level answers become a decision** is [`Scoring`](#outrage.smartsearch.Scoring), one
  object over the evidence, which the result keeps whole so that a tuning run
  can re-score without asking the model again.

Two rules carry over from the agent unchanged. **Missing metadata is unsure,
never no**: a document without a summary has told the cascade nothing, so it
goes on to the next level as it was. And **a partial value cannot justify a
no**: a truncated title, or a body judged in fewer chunks than it has, can
count for a document but never against it.

A third rule, from measuring: **a title or keywords can count only for a
document**. Both are written to label a document rather than to describe it,
so a short or generic one -- an API page titled by its module name, a README
titled with the project's -- is uninformative, and a yes-or-no question has no
answer for that but a low one. Counted against, a single such answer ruled out
the best document for a query. [`Scoring.supporting`](#outrage.smartsearch.Scoring.supporting) holds the rule.

Content leaves the machine whenever the judge is a remote service, which is
the front ends' to say; this module cannot tell one judge from another.

### outrage.smartsearch.DEFAULT_BATCH_SIZE *= 50*

Documents judged in one `"questions"` request. Each question is evaluated
in isolation, so this bounds the request rather than what the model weighs.

### outrage.smartsearch.DEFAULT_CHUNK_CHARS *= 60000*

Characters of body in one state. Jev takes 32k tokens for the state and the
longest question together, and English runs near four characters a token, so
this leaves room for the question and for text that tokenises badly. A chunk
the model still refuses as too large is halved and asked again.

### outrage.smartsearch.DEFAULT_LIMIT *= 100*

Documents in one slice, which is what bounds a result: the server keeps no
state, so a result for its slice cannot itself be paged.

### outrage.smartsearch.DEFAULT_MAX_CHUNKS *= 16*

Body chunks judged per document before the rest is left unread. A document
cut short this way is partial, so it can be kept but not ruled out.

### outrage.smartsearch.DEFAULT_SHAPES *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['title', 'keywords', 'summary', 'contents', 'body'], [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['questions', 'state']]* *= {'body': 'state', 'contents': 'questions', 'keywords': 'questions', 'summary': 'questions', 'title': 'questions'}*

A starting point: many short values to a request, and a body on its own.

### outrage.smartsearch.DEFAULT_VALUE_CHARS *= 8000*

Longest metadata value read for judging. A longer one is judged on its
first part and marked partial, so it cannot rule a document out.

### outrage.smartsearch.LEVELS *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['title', 'keywords', 'summary', 'contents', 'body'], ...]* *= ('title', 'keywords', 'summary', 'contents', 'body')*

The default cascade, cheapest and most telling first.

Keywords beside the title, being as short and written for the same purpose.
Summary before contents because a summary is the shorter of the two and says
more about what a document is for; a contents index is headings, which name
what is in a document without saying what it concludes.

### outrage.smartsearch.MIN_CHUNK_CHARS *= 1000*

Below this, halving a chunk the model refuses as too large stops, and the
document is reported unjudged rather than split into fragments.

### outrage.smartsearch.NOUL_QUESTIONS *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['title', 'keywords', 'summary', 'contents', 'body'], [LevelQuestions](#outrage.smartsearch.LevelQuestions)]* *= {'body': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`body\` is the text, or one part of it, of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the text, or one part of it, of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={})), 'contents': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`contents\` is the table of contents (its headings) of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the table of contents (its headings) of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={})), 'keywords': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`keywords\` is the keywords of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the keywords of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={})), 'summary': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`summary\` is the summary of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the summary of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={})), 'title': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`title\` is the title of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the title of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={}))}*

The alternative question at each level: a single probability of relevance.

### outrage.smartsearch.SCORE_QUESTIONS *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['title', 'keywords', 'summary', 'contents', 'body'], [LevelQuestions](#outrage.smartsearch.LevelQuestions)]* *= {'body': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`body\` is the text, or one part of it, of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the text, or one part of it, of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'contents': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`contents\` is the table of contents (its headings) of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the table of contents (its headings) of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'keywords': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`keywords\` is the keywords of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the keywords of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'summary': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`summary\` is the summary of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the summary of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'title': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`title\` is the title of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the title of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}))}*

The default question at each level: four ordered levels of relevance.

Better than Noul at most levels in the first measurement, and in John's own
testing: the tiers say what kind of match to look for, where a single
probability leaves the model to decide what "relevant" means. The same
criteria everywhere for now; tuning is what says whether a level wants its own.

### *class* outrage.smartsearch.Answer(probability: [float](https://docs.python.org/3/builtins/functions.html#float) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, score: [float](https://docs.python.org/3/builtins/functions.html#float) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, probabilities: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[float](https://docs.python.org/3/builtins/functions.html#float), ...] = (), confidence: [float](https://docs.python.org/3/builtins/functions.html#float) | [None](https://docs.python.org/3/builtins/constants.html#None) = None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

What a judge said about one question.

A Noul answer sets `probability`. A Score answer sets `score`, the
probability-weighted level counted from zero -- it can land between two --
and usually `probabilities` across every level and a `confidence`.

#### probability *: [float](https://docs.python.org/3/builtins/functions.html#float) | [None](https://docs.python.org/3/builtins/constants.html#None)*

#### score *: [float](https://docs.python.org/3/builtins/functions.html#float) | [None](https://docs.python.org/3/builtins/constants.html#None)*

#### probabilities *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[float](https://docs.python.org/3/builtins/functions.html#float), ...]*

#### confidence *: [float](https://docs.python.org/3/builtins/functions.html#float) | [None](https://docs.python.org/3/builtins/constants.html#None)*

#### as_probability(levels: [int](https://docs.python.org/3/builtins/functions.html#int) | [None](https://docs.python.org/3/builtins/constants.html#None) = None) → [float](https://docs.python.org/3/builtins/functions.html#float)

This answer as one probability of a match, from 0 to 1.

A Noul answer already is one. A score becomes its expected level scaled
to 0-1, which uses the whole distribution where there is one: a
document the model put evenly between *related* and *relevant* sits
between them rather than at whichever won.

### outrage.smartsearch.Decision

Where a level leaves a document: ruled in, ruled out, or carried to the next.

alias of [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)['yes', 'no', 'unsure']

### *class* outrage.smartsearch.Evidence(level: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['title', 'keywords', 'summary', 'contents', 'body'], answer: [Answer](#outrage.smartsearch.Answer), probability: [float](https://docs.python.org/3/builtins/functions.html#float), chunks: [int](https://docs.python.org/3/builtins/functions.html#int) = 1, partial: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

What one level said about one document, kept whole for re-scoring.

#### level *: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['title', 'keywords', 'summary', 'contents', 'body']*

#### answer *: [Answer](#outrage.smartsearch.Answer)*

#### probability *: [float](https://docs.python.org/3/builtins/functions.html#float)*

`answer` reduced to one probability of a match.

#### chunks *: [int](https://docs.python.org/3/builtins/functions.html#int)*

How many requests the level took for this document: one, or a body's
chunks. For a body, `answer` is the best chunk's.

#### partial *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

Whether the level judged less than all there was -- a truncated value,
or a body with chunks left unread. Partial evidence cannot count against.

### *class* outrage.smartsearch.Judge(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Anything that answers questions about a piece of state.

The System One protocol, reduced to what the cascade needs. A client
retries what is worth retrying before it raises, so a [`JudgeError`](#outrage.smartsearch.JudgeError)
reaching the cascade is final for the documents that request carried.

#### judge(state: [str](https://docs.python.org/3/builtins/stdtypes.html#str), questions: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Question](#outrage.smartsearch.Question)]) → [Judgement](#outrage.smartsearch.Judgement)

### *exception* outrage.smartsearch.JudgeError(code: [str](https://docs.python.org/3/builtins/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`RuntimeError`](https://docs.python.org/3/builtins/exceptions.html#RuntimeError)

A request to the judge failed, after whatever retrying the client does.

### *class* outrage.smartsearch.Judgement(answers: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Answer](#outrage.smartsearch.Answer)], input_tokens: [int](https://docs.python.org/3/builtins/functions.html#int) = 0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A judge's answers to one request, by the ids the questions were sent under.

#### answers *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Answer](#outrage.smartsearch.Answer)]*

#### input_tokens *: [int](https://docs.python.org/3/builtins/functions.html#int)*

### outrage.smartsearch.Level

What a level judges: a metadata value by its name, or the document itself.

alias of [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)['title', 'keywords', 'summary', 'contents', 'body']

### *class* outrage.smartsearch.LevelCounts(asked: [int](https://docs.python.org/3/builtins/functions.html#int) = 0, yes: [int](https://docs.python.org/3/builtins/functions.html#int) = 0, no: [int](https://docs.python.org/3/builtins/functions.html#int) = 0, missing: [int](https://docs.python.org/3/builtins/functions.html#int) = 0, unjudged: [int](https://docs.python.org/3/builtins/functions.html#int) = 0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

What happened at one level, across the slice.

#### asked *: [int](https://docs.python.org/3/builtins/functions.html#int)*

Documents judged at this level.

#### yes *: [int](https://docs.python.org/3/builtins/functions.html#int)*

#### no *: [int](https://docs.python.org/3/builtins/functions.html#int)*

#### missing *: [int](https://docs.python.org/3/builtins/functions.html#int)*

Documents that reached this level without the metadata it reads, and
so went on unchanged.

#### unjudged *: [int](https://docs.python.org/3/builtins/functions.html#int)*

### *class* outrage.smartsearch.LevelQuestions(questions: [Question](#outrage.smartsearch.Question), state: [Question](#outrage.smartsearch.Question))

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The question for one level, in each of the two shapes.

#### questions *: [Question](#outrage.smartsearch.Question)*

Asked with the query as the state; the document is in its instructions.

#### state *: [Question](#outrage.smartsearch.Question)*

Asked with the document's value as the state; names `{query}`.

### *class* outrage.smartsearch.Match(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str), probability: [float](https://docs.python.org/3/builtins/functions.html#float), decision: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['yes', 'unsure'], decided_at: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['title', 'keywords', 'summary', 'contents', 'body'] | [None](https://docs.python.org/3/builtins/constants.html#None), evidence: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Evidence](#outrage.smartsearch.Evidence), ...])

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One document not ruled out.

#### key *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

#### probability *: [float](https://docs.python.org/3/builtins/functions.html#float)*

#### decision *: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['yes', 'unsure']*

#### decided_at *: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['title', 'keywords', 'summary', 'contents', 'body'] | [None](https://docs.python.org/3/builtins/constants.html#None)*

The level at which it was decided a match, or None when no level did
and it is here as still unsure.

#### evidence *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Evidence](#outrage.smartsearch.Evidence), ...]*

### *class* outrage.smartsearch.Question(kind: ~typing.Literal['noul', 'score'], text: str, criteria: tuple[str, ...] = (), instructions: ~collections.abc.Mapping[str, str] = <factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One question put to a judge, in terms that do not depend on the wire.

`text` may name `{query}`, which is filled in when the query is not the
state. `instructions` are the facts the question is about -- for the
`"questions"` shape, the document's key and the value being judged. They
travel beside the text rather than inside it, so the text names them in
backticks, the way System One expects a question to point at its data.

#### kind *: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['noul', 'score']*

`"noul"` answers one probability of yes; `"score"` picks one of
`criteria` and answers a probability for each.

#### text *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

#### criteria *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]*

For a score, what each level means, lowest first. Two to ten of them.

#### instructions *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)]*

### *class* outrage.smartsearch.Scoring(weights: ~collections.abc.Mapping[~typing.Literal['title', 'keywords', 'summary', 'contents', 'body'], float] = <factory>, supporting: frozenset[~typing.Literal['title', 'keywords', 'summary', 'contents', 'body']] = frozenset({'keywords', 'title'}), yes: float = 0.8, no: float = 0.2)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

How evidence from the levels becomes a probability and a decision.

**Weighted log-odds, summed**: each level adds `weight * logit(p)`,
scaled by the answer's confidence where it has one, and the combined
probability is the sigmoid of the total. Two near misses therefore add up
to more than either, where per-level thresholds would carry both as unsure
and forget them. The levels are not independent -- a title and a summary
written together say much the same thing -- and weights below one are the
damping for that.

The weights and thresholds here are a starting point and not a result:
measuring the cascade against labelled queries is what sets them. Other
rules the measuring may prefer -- the strongest level rather than the sum,
a small fitted model over the per-level answers, or the last level alone
with the earlier ones only pruning -- are each a different [`combine()`](#outrage.smartsearch.Scoring.combine).

#### weights *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['title', 'keywords', 'summary', 'contents', 'body'], [float](https://docs.python.org/3/builtins/functions.html#float)]*

#### supporting *: [frozenset](https://docs.python.org/3/builtins/stdtypes.html#frozenset)[[Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['title', 'keywords', 'summary', 'contents', 'body']]*

Levels whose evidence can count for a document and never against it, as
partial evidence cannot. A label too generic to say anything gets a low
answer, not an unsure one, and must not rule the document out.

#### yes *: [float](https://docs.python.org/3/builtins/functions.html#float)*

At or above this, a document is decided a match and stops cascading.

#### no *: [float](https://docs.python.org/3/builtins/functions.html#float)*

At or below this, a document is ruled out.

#### combine(evidence: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[Evidence](#outrage.smartsearch.Evidence)]) → [float](https://docs.python.org/3/builtins/functions.html#float)

The probability that a document matches, on everything seen so far.

#### decide(probability: [float](https://docs.python.org/3/builtins/functions.html#float)) → [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['yes', 'no', 'unsure']

Yes, no, or carry on to the next level.

### outrage.smartsearch.Shape

Which way round a level is asked.

`"questions"` puts the query in the state and one document in each question,
so one request judges many documents. `"state"` puts the document in the
state and the query in its one question, a request per document. Both are
measured; if one wins everywhere the other goes.

alias of [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)['questions', 'state']

### *class* outrage.smartsearch.SmartSearchResult(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None), query: [str](https://docs.python.org/3/builtins/stdtypes.html#str), matches: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Match](#outrage.smartsearch.Match), ...], unjudged: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Unjudged](#outrage.smartsearch.Unjudged), ...], levels: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['title', 'keywords', 'summary', 'contents', 'body'], [LevelCounts](#outrage.smartsearch.LevelCounts)], documents: [int](https://docs.python.org/3/builtins/functions.html#int), total: [int](https://docs.python.org/3/builtins/functions.html#int), next_cursor: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None), unavailable: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...], input_tokens: [int](https://docs.python.org/3/builtins/functions.html#int))

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The whole answer for one slice.

`total` and `next_cursor` are over the *input* -- the documents of the
subtree -- since the matches cannot be paged: the next slice is asked for
with `after=next_cursor`.

#### key *: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)*

#### query *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

#### matches *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Match](#outrage.smartsearch.Match), ...]*

Every document not ruled out, best first.

#### unjudged *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Unjudged](#outrage.smartsearch.Unjudged), ...]*

#### levels *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['title', 'keywords', 'summary', 'contents', 'body'], [LevelCounts](#outrage.smartsearch.LevelCounts)]*

#### documents *: [int](https://docs.python.org/3/builtins/functions.html#int)*

Documents in this slice.

#### total *: [int](https://docs.python.org/3/builtins/functions.html#int)*

Documents in the whole subtree.

#### next_cursor *: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)*

#### unavailable *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]*

Mount points the slice had to leave out.

#### input_tokens *: [int](https://docs.python.org/3/builtins/functions.html#int)*

### *exception* outrage.smartsearch.StateTooLarge(code: [str](https://docs.python.org/3/builtins/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`JudgeError`](#outrage.smartsearch.JudgeError)

The judge refused a request as too long. The cascade halves and retries.

### *class* outrage.smartsearch.Unjudged(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str), level: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['title', 'keywords', 'summary', 'contents', 'body'], code: [str](https://docs.python.org/3/builtins/stdtypes.html#str), details: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [object](https://docs.python.org/3/builtins/functions.html#object)], evidence: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Evidence](#outrage.smartsearch.Evidence), ...])

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A document the cascade could not finish, and why.

#### key *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

#### level *: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['title', 'keywords', 'summary', 'contents', 'body']*

#### code *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

The failure's code, which [`outrage.messages`](messages.md#module-outrage.messages) renders.

#### details *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [object](https://docs.python.org/3/builtins/functions.html#object)]*

#### evidence *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Evidence](#outrage.smartsearch.Evidence), ...]*

Whatever the levels before this one said.

### outrage.smartsearch.refusals(query: [str](https://docs.python.org/3/builtins/stdtypes.html#str), levels: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] = LEVELS, shapes: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None) → [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[Refusal](errors.md#outrage.errors.Refusal)]

Every reason these arguments cannot be searched with, at once.

### outrage.smartsearch.smart_search(store: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None), query: [str](https://docs.python.org/3/builtins/stdtypes.html#str), judge: [Judge](#outrage.smartsearch.Judge), \*, depth: [int](https://docs.python.org/3/builtins/functions.html#int) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, limit: [int](https://docs.python.org/3/builtins/functions.html#int) = DEFAULT_LIMIT, after: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, levels: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['title', 'keywords', 'summary', 'contents', 'body']] = LEVELS, shapes: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['title', 'keywords', 'summary', 'contents', 'body'], [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['questions', 'state']] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, questions: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['title', 'keywords', 'summary', 'contents', 'body'], [LevelQuestions](#outrage.smartsearch.LevelQuestions)] = SCORE_QUESTIONS, scoring: [Scoring](#outrage.smartsearch.Scoring) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, batch_size: [int](https://docs.python.org/3/builtins/functions.html#int) = DEFAULT_BATCH_SIZE, value_chars: [int](https://docs.python.org/3/builtins/functions.html#int) = DEFAULT_VALUE_CHARS, chunk_chars: [int](https://docs.python.org/3/builtins/functions.html#int) = DEFAULT_CHUNK_CHARS, max_chunks: [int](https://docs.python.org/3/builtins/functions.html#int) = DEFAULT_MAX_CHUNKS) → [SmartSearchResult](#outrage.smartsearch.SmartSearchResult)

Screen one slice of the documents under `key` against `query`.

The slice is a page of the subtree's documents, `limit` of them after
`after`, exactly as `get_documents` would page it. Each is judged at
the first of `levels` and carried to the next only while the combined
evidence leaves it unsure.

Raises the first of [`refusals()`](#outrage.smartsearch.refusals) as an error; a front end wanting
every reason calls that first. A failed request never
raises: its documents are reported in [`SmartSearchResult.unjudged`](#outrage.smartsearch.SmartSearchResult.unjudged).
