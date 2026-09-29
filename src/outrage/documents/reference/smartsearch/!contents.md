# outrage.smartsearch
0 0 1

### outrage.smartsearch.DEFAULT_BATCH_SIZE *= 50*
2764 2764 47

### outrage.smartsearch.DEFAULT_CHUNK_CHARS *= 60000*
2966 2966 52

### outrage.smartsearch.DEFAULT_LIMIT *= 100*
3316 3316 59

### outrage.smartsearch.DEFAULT_MAX_CHUNKS *= 16*
3496 3496 64

### outrage.smartsearch.DEFAULT_SHAPES *: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], Literal['questions', 'state']]* *= {'body': 'state', 'contents': 'questions', 'keywords': 'questions', 'summary': 'questions', 'title': 'questions'}*
3691 3691 69

### outrage.smartsearch.DEFAULT_VALUE_CHARS *= 8000*
4237 4237 73

### outrage.smartsearch.LEVELS *: tuple[Literal['title', 'keywords', 'summary', 'contents', 'body'], ...]* *= ('title', 'keywords', 'summary', 'contents', 'body')*
4428 4428 78

### outrage.smartsearch.MIN_CHUNK_CHARS *= 1000*
5056 5056 87

### outrage.smartsearch.NOUL_QUESTIONS *: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], LevelQuestions]* *= {'body': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`body\` is the text, or one part of it, of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the text, or one part of it, of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={})), 'contents': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`contents\` is the table of contents (its headings) of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the table of contents (its headings) of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={})), 'keywords': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`keywords\` is the keywords of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the keywords of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={})), 'summary': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`summary\` is the summary of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the summary of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={})), 'title': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`title\` is the title of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the title of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={}))}*
5245 5245 92

### outrage.smartsearch.SCORE_QUESTIONS *: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], LevelQuestions]* *= {'body': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`body\` is the text, or one part of it, of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the text, or one part of it, of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'contents': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`contents\` is the table of contents (its headings) of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the table of contents (its headings) of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'keywords': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`keywords\` is the keywords of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the keywords of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'summary': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`summary\` is the summary of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the summary of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'title': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`title\` is the title of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the title of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}))}*
7851 7851 96

### *class* outrage.smartsearch.Answer(probability: float | None = None, score: float | None = None, probabilities: tuple[float, ...] = (), confidence: float | None = None)
12031 12031 105

#### probability *: float | None*
12999 12999 115

#### score *: float | None*
13151 13151 117

#### probabilities *: tuple[float, ...]*
13297 13297 119

#### confidence *: float | None*
13456 13456 121

#### as_probability(levels: int | None = None) → float
13607 13607 123

### outrage.smartsearch.Decision
14142 14144 132

### *class* outrage.smartsearch.Evidence(level: Literal['title', 'keywords', 'summary', 'contents', 'body'], answer: Answer, probability: float, chunks: int = 1, partial: bool = False)
14362 14364 138

#### level *: Literal['title', 'keywords', 'summary', 'contents', 'body']*
14962 14964 144

#### answer *: Answer*
15102 15104 146

#### probability *: float*
15157 15159 148

#### chunks *: int*
15293 15295 152

#### partial *: bool*
15491 15493 157

### *class* outrage.smartsearch.Judge(\*args, \*\*kwargs)
15718 15720 162

#### judge(state: str, questions: Mapping[str, Question]) → Judgement
16160 16162 172

### *exception* outrage.smartsearch.JudgeError(code: str, \*\*details: Any)
16492 16496 174

### *class* outrage.smartsearch.Judgement(answers: Mapping[str, Answer], input_tokens: int = 0)
16905 16909 180

#### answers *: Mapping[str, Answer]*
17382 17386 186

#### input_tokens *: int*
17590 17594 188

### outrage.smartsearch.Level
17674 17678 190

### *class* outrage.smartsearch.LevelCounts(asked: int = 0, yes: int = 0, no: int = 0, missing: int = 0, unjudged: int = 0)
17917 17921 196

#### asked *: int*
18451 18455 202

#### yes *: int*
18561 18565 206

#### no *: int*
18636 18640 208

#### missing *: int*
18710 18714 210

#### unjudged *: int*
18881 18885 215

### *class* outrage.smartsearch.LevelQuestions(questions: Question, state: Question)
18961 18965 217

#### questions *: Question*
19246 19250 223

#### state *: Question*
19381 19385 227

### *class* outrage.smartsearch.Match(key: str, probability: float, decision: Literal['yes', 'unsure'], decided_at: Literal['title', 'keywords', 'summary', 'contents', 'body'] | None, evidence: tuple[Evidence, ...])
19503 19507 231

#### key *: str*
20218 20222 237

#### probability *: float*
20292 20296 239

#### decision *: Literal['yes', 'unsure']*
20379 20383 241

#### decided_at *: Literal['title', 'keywords', 'summary', 'contents', 'body'] | None*
20487 20491 243

#### evidence *: tuple[Evidence, ...]*
20799 20803 248

### *class* outrage.smartsearch.Question(kind: ~typing.Literal['noul', 'score'], text: str, criteria: tuple[str, ...] = (), instructions: ~collections.abc.Mapping[str, str] = <factory>)
20930 20934 250

#### kind *: Literal['noul', 'score']*
21623 21627 262

#### text *: str*
21839 21843 267

#### criteria *: tuple[str, ...]*
21914 21918 269

#### instructions *: Mapping[str, str]*
22134 22138 273

### *class* outrage.smartsearch.Scoring(weights: ~collections.abc.Mapping[~typing.Literal['title', 'keywords', 'summary', 'contents', 'body'], float] = <factory>, supporting: frozenset[~typing.Literal['title', 'keywords', 'summary', 'contents', 'body']] = frozenset({'keywords', 'title'}), yes: float = 0.8, no: float = 0.2)
22369 22373 275

#### weights *: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], float]*
23696 23700 295

#### supporting *: frozenset[Literal['title', 'keywords', 'summary', 'contents', 'body']]*
23995 23999 297

#### yes *: float*
24421 24425 303

#### no *: float*
24570 24574 307

#### combine(evidence: Sequence[Evidence]) → float
24692 24696 311

#### decide(probability: float) → Literal['yes', 'no', 'unsure']
24988 24994 315

### outrage.smartsearch.Shape
25218 25226 319

### *class* outrage.smartsearch.SmartSearchResult(key: str | None, query: str, matches: tuple[Match, ...], unjudged: tuple[Unjudged, ...], levels: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], LevelCounts], documents: int, total: int, next_cursor: str | None, unavailable: tuple[str, ...], input_tokens: int)
25664 25672 330

#### key *: str | None*
27209 27217 340

#### query *: str*
27348 27356 342

#### matches *: tuple[Match, ...]*
27424 27432 344

#### unjudged *: tuple[Unjudged, ...]*
27591 27599 348

#### levels *: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], LevelCounts]*
27722 27730 350

#### documents *: int*
28003 28011 352

#### total *: int*
28110 28118 356

#### next_cursor *: str | None*
28220 28228 360

#### unavailable *: tuple[str, ...]*
28367 28375 362

#### input_tokens *: int*
28561 28569 366

### *exception* outrage.smartsearch.StateTooLarge(code: str, \*\*details: Any)
28645 28653 368

### *class* outrage.smartsearch.Unjudged(key: str, level: Literal['title', 'keywords', 'summary', 'contents', 'body'], code: str, details: Mapping[str, object], evidence: tuple[Evidence, ...])
28971 28979 374

#### key *: str*
29758 29766 380

#### level *: Literal['title', 'keywords', 'summary', 'contents', 'body']*
29832 29840 382

#### code *: str*
29972 29980 384

#### details *: Mapping[str, object]*
30141 30149 388

#### evidence *: tuple[Evidence, ...]*
30378 30386 390

### outrage.smartsearch.refusals(query: str, levels: Sequence[str] = LEVELS, shapes: Mapping[str, str] | None = None) → list[Refusal]
30552 30560 394

### outrage.smartsearch.smart_search(store: Store, key: str | None, query: str, judge: Judge, \*, depth: int | None = None, limit: int = DEFAULT_LIMIT, after: str | None = None, levels: Sequence[Literal['title', 'keywords', 'summary', 'contents', 'body']] = LEVELS, shapes: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], Literal['questions', 'state']] | None = None, questions: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], LevelQuestions] = SCORE_QUESTIONS, scoring: Scoring | None = None, batch_size: int = DEFAULT_BATCH_SIZE, value_chars: int = DEFAULT_VALUE_CHARS, chunk_chars: int = DEFAULT_CHUNK_CHARS, max_chunks: int = DEFAULT_MAX_CHUNKS) → SmartSearchResult
31291 31301 398
