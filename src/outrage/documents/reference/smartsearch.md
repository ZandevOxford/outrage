# outrage.smartsearch

Screen a bounded slice of documents against a query with a System One
judge. A configurable cascade examines progressively richer metadata and then
the body, retaining the evidence used to rank every document not ruled out.

The cascade the `outrage-search` agent follows, moved out of an agent's
context and into the library: every document in the slice is judged at the
first level -- its `!title`, as shipped -- and only the ones that level
leaves unsure go on to the next, through richer metadata to the body. What
comes back is every document not ruled out, best first. The calling agent
reads none of it.

**The judging is not done here.** A [`Judge`](#outrage.smartsearch.Judge) answers questions about a
piece of state -- the protocol System One models speak -- and this module
decides what to ask, of which documents, and what the answers add up to. So the
suite runs against a fake, and a second model or a local server is a different
judge rather than a different cascade.

What is expected to change as the cascade is measured is not in this module
at all. The levels and their order, the question asked at each, **which way
round** each is asked (the query as the state and many documents as the
questions, or each document as the state and the query with its one question),
the scoring constants and the request sizes are a [`Tuning`](#outrage.smartsearch.Tuning), read from
a JSON file shipped in the package, [`TUNING_PATH`](#outrage.smartsearch.TUNING_PATH), beside a readme
saying what each part means and how to tune it. What stays here is the rules:
what each [`Kind`](#outrage.smartsearch.Kind) of level reads, and how [`Scoring`](#outrage.smartsearch.Scoring) turns the
per-level answers into a decision -- one object over the evidence, which the
result keeps whole so that a tuning run can re-score without asking the
model again.

Two rules carry over from the agent unchanged. **Missing metadata is unsure,
never no**: a document without a summary has told the cascade nothing, so it
goes on to the next level as it was. And **a partial value cannot justify a
no**: a truncated title, or a body judged in fewer chunks than it has, can
count for a document but never against it.

A third rule, from measuring, is that **a supporting level can count only
for a document**. A title or keywords label a document rather than describe
it, so a generic one gets a low answer rather than an unsure one; counted
against, a single such answer ruled out the best document for a query. The
tuning says which levels are supporting, and [`Scoring.supporting`](#outrage.smartsearch.Scoring.supporting)
applies it.

Content leaves the machine whenever the judge is a remote service, which is
the front ends' to say; this module cannot tell one judge from another.

### outrage.smartsearch.QUERY *= 'query'*

The name the query is sent under, in the state or beside the question.

### outrage.smartsearch.RULES *= ('log-odds-sum',)*

How each combination rule is named in the tuning. The rule is code, so a
second one is a new name here and a new [`Scoring.combine()`](#outrage.smartsearch.Scoring.combine).

### outrage.smartsearch.TUNING_FORMAT *= 1*

The tuning file's layout version; a file naming another is refused.

### outrage.smartsearch.TUNING_NAMES *= ('format', 'question', 'levels', 'scoring', 'requests', 'kind', 'criteria', 'text', 'name', 'meta', 'what', 'shape', 'weight', 'supporting', 'rule', 'yes', 'no', 'clamp', 'limit', 'batch_size', 'value_chars', 'chunk_chars', 'max_chunks', 'min_chunk_chars', 'note', 'value', 'contents', 'body', 'questions', 'state', 'score', 'noul', 'log-odds-sum')*

Every name the tuning file accepts, as field names and as the values of its
enumerated fields, so that the readme can be held to describing all of them.

### outrage.smartsearch.TUNING_PATH *= ('smart-search', 'tuning.json')*

Where the tuning lives in the shipped documents tree, which is what serves it
as `outrage/smart-search/tuning` beside the readme describing it.

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

### *class* outrage.smartsearch.Evidence(level: [str](https://docs.python.org/3/builtins/stdtypes.html#str), answer: [Answer](#outrage.smartsearch.Answer), probability: [float](https://docs.python.org/3/builtins/functions.html#float), chunks: [int](https://docs.python.org/3/builtins/functions.html#int) = 1, partial: [bool](https://docs.python.org/3/builtins/functions.html#bool) = False)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

What one level said about one document, kept whole for re-scoring.

#### level *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

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

#### judge(state: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)], questions: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Question](#outrage.smartsearch.Question)]) → [Judgement](#outrage.smartsearch.Judgement)

### *exception* outrage.smartsearch.JudgeError(code: [str](https://docs.python.org/3/builtins/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`RuntimeError`](https://docs.python.org/3/builtins/exceptions.html#RuntimeError)

A request to the judge failed, after whatever retrying the client does.

### *class* outrage.smartsearch.Judgement(answers: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Answer](#outrage.smartsearch.Answer)], input_tokens: [int](https://docs.python.org/3/builtins/functions.html#int) = 0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A judge's answers to one request, by the ids the questions were sent under.

#### answers *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Answer](#outrage.smartsearch.Answer)]*

#### input_tokens *: [int](https://docs.python.org/3/builtins/functions.html#int)*

### outrage.smartsearch.Kind

What a level reads: a plain metadata value, a `!contents` index (judged on
its headings, its offsets kept for chunking the body), or the body itself.
Behaviour rather than a number, so the tuning picks one per level but cannot
invent another.

alias of [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)['value', 'contents', 'body']

### outrage.smartsearch.Level

A level's name, as the tuning defines it: a metadata name for a level that
reads metadata, or whatever the tuning calls the level reading the body.

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

### *class* outrage.smartsearch.LevelTuning(name: [str](https://docs.python.org/3/builtins/stdtypes.html#str), kind: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['value', 'contents', 'body'], meta: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None), shape: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['questions', 'state'], weight: [float](https://docs.python.org/3/builtins/functions.html#float), supporting: [bool](https://docs.python.org/3/builtins/functions.html#bool), question: [Question](#outrage.smartsearch.Question))

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One level of the cascade, as the tuning defines it.

#### name *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

What the level is called, in a result and in a request's `levels`.

#### kind *: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['value', 'contents', 'body']*

#### meta *: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)*

The metadata name read, without its `!`; None for the body.

#### shape *: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['questions', 'state']*

#### weight *: [float](https://docs.python.org/3/builtins/functions.html#float)*

#### supporting *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

#### question *: [Question](#outrage.smartsearch.Question)*

The question, with the level's placeholders filled in.

### *class* outrage.smartsearch.Match(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str), probability: [float](https://docs.python.org/3/builtins/functions.html#float), decision: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['yes', 'unsure'], decided_at: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None), evidence: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Evidence](#outrage.smartsearch.Evidence), ...])

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One document not ruled out.

#### key *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

#### probability *: [float](https://docs.python.org/3/builtins/functions.html#float)*

#### decision *: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['yes', 'unsure']*

#### decided_at *: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None)*

The level at which it was decided a match, or None when no level did
and it is here as still unsure.

#### evidence *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Evidence](#outrage.smartsearch.Evidence), ...]*

### *class* outrage.smartsearch.Question(kind: ~typing.Literal['noul', 'score'], text: str, criteria: tuple[str, ...] = (), instructions: ~collections.abc.Mapping[str, str] = <factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One question put to a judge, in terms that do not depend on the wire.

`text` names what it is about in backticks, the way System One expects a
question to point at its data: a field of the state, or of
`instructions`, the named values that travel beside the text rather than
inside it. Which of the two holds the query and which the document's value
is the level's [`Shape`](#outrage.smartsearch.Shape), and the text reads the same either way.

#### kind *: [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['noul', 'score']*

`"noul"` answers one probability of yes; `"score"` picks one of
`criteria` and answers a probability for each.

#### text *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

#### criteria *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]*

For a score, what each level means, lowest first. Two to ten of them.

#### instructions *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)]*

### *class* outrage.smartsearch.Requests(limit: [int](https://docs.python.org/3/builtins/functions.html#int), batch_size: [int](https://docs.python.org/3/builtins/functions.html#int), value_chars: [int](https://docs.python.org/3/builtins/functions.html#int), chunk_chars: [int](https://docs.python.org/3/builtins/functions.html#int), max_chunks: [int](https://docs.python.org/3/builtins/functions.html#int), min_chunk_chars: [int](https://docs.python.org/3/builtins/functions.html#int))

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

How much is read and sent at once. See [`TUNING_PATH`](#outrage.smartsearch.TUNING_PATH)'s readme.

#### limit *: [int](https://docs.python.org/3/builtins/functions.html#int)*

#### batch_size *: [int](https://docs.python.org/3/builtins/functions.html#int)*

#### value_chars *: [int](https://docs.python.org/3/builtins/functions.html#int)*

#### chunk_chars *: [int](https://docs.python.org/3/builtins/functions.html#int)*

#### max_chunks *: [int](https://docs.python.org/3/builtins/functions.html#int)*

#### min_chunk_chars *: [int](https://docs.python.org/3/builtins/functions.html#int)*

### *class* outrage.smartsearch.Scoring(weights: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [float](https://docs.python.org/3/builtins/functions.html#float)], supporting: [frozenset](https://docs.python.org/3/builtins/stdtypes.html#frozenset)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)], yes: [float](https://docs.python.org/3/builtins/functions.html#float), no: [float](https://docs.python.org/3/builtins/functions.html#float), clamp: [float](https://docs.python.org/3/builtins/functions.html#float))

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

How evidence from the levels becomes a probability and a decision.

**Weighted log-odds, summed**: each level adds `weight * logit(p)`,
scaled by the answer's confidence where it has one, and the combined
probability is the sigmoid of the total. Two near misses therefore add up
to more than either, where per-level thresholds would carry both as unsure
and forget them. The levels are not independent -- a title and a summary
written together say much the same thing -- and weights below one are the
damping for that.

The numbers come from the tuning file, [`TUNING_PATH`](#outrage.smartsearch.TUNING_PATH), and are a
starting point rather than a result: measuring the cascade against
labelled queries is what sets them. Other
rules the measuring may prefer -- the strongest level rather than the sum,
a small fitted model over the per-level answers, or the last level alone
with the earlier ones only pruning -- are each a different [`combine()`](#outrage.smartsearch.Scoring.combine).

#### weights *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [float](https://docs.python.org/3/builtins/functions.html#float)]*

How much each level's answer counts, by level name.

#### supporting *: [frozenset](https://docs.python.org/3/builtins/stdtypes.html#frozenset)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]*

Levels whose evidence can count for a document and never against it, as
partial evidence cannot. A label too generic to say anything gets a low
answer, not an unsure one, and must not rule the document out.

#### yes *: [float](https://docs.python.org/3/builtins/functions.html#float)*

At or above this, a document is decided a match and stops cascading.

#### no *: [float](https://docs.python.org/3/builtins/functions.html#float)*

At or below this, a document is ruled out.

#### clamp *: [float](https://docs.python.org/3/builtins/functions.html#float)*

How close to 0 or 1 a probability is taken to be, so that a certain
answer adds a large finite amount rather than an infinite one.

#### combine(evidence: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[Evidence](#outrage.smartsearch.Evidence)]) → [float](https://docs.python.org/3/builtins/functions.html#float)

The probability that a document matches, on everything seen so far.

#### decide(probability: [float](https://docs.python.org/3/builtins/functions.html#float)) → [Literal](https://docs.python.org/3/library/typing.html#typing.Literal)['yes', 'no', 'unsure']

Yes, no, or carry on to the next level.

### outrage.smartsearch.Shape

Which way round a level is asked.

Every request carries two named values, the query and one value of a
document, and the question names both in backticks whichever side each is
on. `"questions"` puts the query in the state and one document's value
beside each question, so one request judges many documents. `"state"` puts
the document's value in the state and the query beside its one question, a
request per document.

alias of [`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)['questions', 'state']

### *class* outrage.smartsearch.SmartSearchResult(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None), query: [str](https://docs.python.org/3/builtins/stdtypes.html#str), matches: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Match](#outrage.smartsearch.Match), ...], unjudged: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Unjudged](#outrage.smartsearch.Unjudged), ...], levels: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [LevelCounts](#outrage.smartsearch.LevelCounts)], documents: [int](https://docs.python.org/3/builtins/functions.html#int), total: [int](https://docs.python.org/3/builtins/functions.html#int), next_cursor: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None), unavailable: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...], input_tokens: [int](https://docs.python.org/3/builtins/functions.html#int))

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

#### levels *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [LevelCounts](#outrage.smartsearch.LevelCounts)]*

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

### *class* outrage.smartsearch.Tuning(levels: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[LevelTuning](#outrage.smartsearch.LevelTuning), ...], scoring: [Scoring](#outrage.smartsearch.Scoring), requests: [Requests](#outrage.smartsearch.Requests), source: [str](https://docs.python.org/3/builtins/stdtypes.html#str))

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Everything about the cascade that is a number or a sentence, not a rule.

Read from a JSON file -- the packaged one, [`TUNING_PATH`](#outrage.smartsearch.TUNING_PATH), unless a
caller names another -- so that the levels, the questions, the scoring
constants and the request sizes can be tuned without touching the code.

#### levels *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[LevelTuning](#outrage.smartsearch.LevelTuning), ...]*

In cascade order.

#### scoring *: [Scoring](#outrage.smartsearch.Scoring)*

#### requests *: [Requests](#outrage.smartsearch.Requests)*

#### source *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

Where it was read from, as a refusal names it.

#### *property* names *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), ...]*

The level names, in cascade order.

#### level(name: [str](https://docs.python.org/3/builtins/stdtypes.html#str)) → [LevelTuning](#outrage.smartsearch.LevelTuning)

The level called `name`; a [`KeyError`](https://docs.python.org/3/builtins/exceptions.html#KeyError) for one it lacks.

#### *classmethod* read(data: [object](https://docs.python.org/3/builtins/functions.html#object), source: [str](https://docs.python.org/3/builtins/stdtypes.html#str)) → [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Tuning](#outrage.smartsearch.Tuning) | [None](https://docs.python.org/3/builtins/constants.html#None), [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[Refusal](errors.md#outrage.errors.Refusal)]]

`data` as a tuning, and every problem with it at once.

`data` is the parsed JSON, from wherever it came: `source` is
only what a refusal names, so that a second file's problems can be
told from the packaged one's. The tuning is None whenever there is a
refusal, since there is no sensible part of a cascade to run.

#### *classmethod* read_file(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/builtins/constants.html#None) = None) → [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Tuning](#outrage.smartsearch.Tuning) | [None](https://docs.python.org/3/builtins/constants.html#None), [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[Refusal](errors.md#outrage.errors.Refusal)]]

[`read()`](#outrage.smartsearch.Tuning.read) over a file, the packaged tuning by default.

#### *classmethod* load(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/builtins/constants.html#None) = None) → [Tuning](#outrage.smartsearch.Tuning)

[`read_file()`](#outrage.smartsearch.Tuning.read_file), raising the first refusal as its error.

### *class* outrage.smartsearch.Unjudged(key: [str](https://docs.python.org/3/builtins/stdtypes.html#str), level: [str](https://docs.python.org/3/builtins/stdtypes.html#str), code: [str](https://docs.python.org/3/builtins/stdtypes.html#str), details: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [object](https://docs.python.org/3/builtins/functions.html#object)], evidence: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Evidence](#outrage.smartsearch.Evidence), ...])

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A document the cascade could not finish, and why.

#### key *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

#### level *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

#### code *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

The failure's code, which [`outrage.messages`](messages.md#module-outrage.messages) renders.

#### details *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [object](https://docs.python.org/3/builtins/functions.html#object)]*

#### evidence *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Evidence](#outrage.smartsearch.Evidence), ...]*

Whatever the levels before this one said.

### outrage.smartsearch.packaged_tuning() → [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Tuning](#outrage.smartsearch.Tuning) | [None](https://docs.python.org/3/builtins/constants.html#None), [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Refusal](errors.md#outrage.errors.Refusal), ...]]

The tuning shipped in the package, and every problem with it.

Read once per process, so an edit to the file reaches the next process
rather than one already running -- the same as an edit to the code.

### outrage.smartsearch.refusals(query: [str](https://docs.python.org/3/builtins/stdtypes.html#str), levels: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, \*, tuning: [Tuning](#outrage.smartsearch.Tuning) | [None](https://docs.python.org/3/builtins/constants.html#None) = None) → [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[Refusal](errors.md#outrage.errors.Refusal)]

Every reason these arguments cannot be searched with, at once.

`tuning` is the packaged one by default, and its own problems are
among the reasons, so a front end asking this hears of a broken file too.

### outrage.smartsearch.smart_search(store: [Store](store.md#outrage.store.Store), key: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None), query: [str](https://docs.python.org/3/builtins/stdtypes.html#str), judge: [Judge](#outrage.smartsearch.Judge), \*, tuning: [Tuning](#outrage.smartsearch.Tuning) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, depth: [int](https://docs.python.org/3/builtins/functions.html#int) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, limit: [int](https://docs.python.org/3/builtins/functions.html#int) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, after: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, levels: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None) → [SmartSearchResult](#outrage.smartsearch.SmartSearchResult)

Screen one slice of the documents under `key` against `query`.

The slice is a page of the subtree's documents, `limit` of them after
`after`, exactly as `get_documents` would page it. Each is judged at
the first of `levels` -- every level of `tuning` by default, in its
order -- and carried to the next only while the combined evidence leaves
it unsure.

`tuning` is [`packaged_tuning()`](#outrage.smartsearch.packaged_tuning) by default: everything about the
cascade that is a number or a sentence rather than a rule.

Raises the first of [`refusals()`](#outrage.smartsearch.refusals) as an error; a front end wanting
every reason calls that first. A failed request never
raises: its documents are reported in [`SmartSearchResult.unjudged`](#outrage.smartsearch.SmartSearchResult.unjudged).
