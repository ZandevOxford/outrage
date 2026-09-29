# outrage.smartsearch
0 0 1

### outrage.smartsearch.DEFAULT_BATCH_SIZE *= 50*
2919 2919 49

### outrage.smartsearch.DEFAULT_CHUNK_CHARS *= 60000*
3121 3121 54

### outrage.smartsearch.DEFAULT_LIMIT *= 100*
3471 3471 61

### outrage.smartsearch.DEFAULT_MAX_CHUNKS *= 16*
3651 3651 66

### outrage.smartsearch.DEFAULT_SHAPES *: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], Literal['questions', 'state']]* *= {'body': 'state', 'contents': 'questions', 'keywords': 'questions', 'summary': 'questions', 'title': 'questions'}*
3846 3846 71

### outrage.smartsearch.DEFAULT_VALUE_CHARS *= 8000*
4392 4392 75

### outrage.smartsearch.LEVELS *: tuple[Literal['title', 'keywords', 'summary', 'contents', 'body'], ...]* *= ('title', 'keywords', 'summary', 'contents', 'body')*
4583 4583 80

### outrage.smartsearch.MIN_CHUNK_CHARS *= 1000*
5211 5211 89

### outrage.smartsearch.NOUL_QUESTIONS *: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], LevelQuestions]* *= {'body': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`body\` is the text, or one part of it, of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the text, or one part of it, of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={})), 'contents': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`contents\` is the table of contents (its headings) of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the table of contents (its headings) of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={})), 'keywords': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`keywords\` is the keywords of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the keywords of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={})), 'summary': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`summary\` is the summary of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the summary of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={})), 'title': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`title\` is the title of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the title of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={}))}*
5400 5400 94

### outrage.smartsearch.SCORE_QUESTIONS *: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], LevelQuestions]* *= {'body': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`body\` is the text, or one part of it, of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the text, or one part of it, of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'contents': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`contents\` is the table of contents (its headings) of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the table of contents (its headings) of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'keywords': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`keywords\` is the keywords of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the keywords of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'summary': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`summary\` is the summary of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the summary of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'title': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`title\` is the title of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the title of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}))}*
8006 8006 98

### *class* outrage.smartsearch.Answer(probability: float | None = None, score: float | None = None, probabilities: tuple[float, ...] = (), confidence: float | None = None)
12186 12186 107

#### probability *: float | None*
13154 13154 117

#### score *: float | None*
13306 13306 119

#### probabilities *: tuple[float, ...]*
13452 13452 121

#### confidence *: float | None*
13611 13611 123

#### as_probability(levels: int | None = None) → float
13762 13762 125

### outrage.smartsearch.Decision
14297 14299 134

### *class* outrage.smartsearch.Evidence(level: Literal['title', 'keywords', 'summary', 'contents', 'body'], answer: Answer, probability: float, chunks: int = 1, partial: bool = False)
14517 14519 140

#### level *: Literal['title', 'keywords', 'summary', 'contents', 'body']*
15117 15119 146

#### answer *: Answer*
15257 15259 148

#### probability *: float*
15312 15314 150

#### chunks *: int*
15448 15450 154

#### partial *: bool*
15646 15648 159

### *class* outrage.smartsearch.Judge(\*args, \*\*kwargs)
15873 15875 164

#### judge(state: str, questions: Mapping[str, Question]) → Judgement
16315 16317 174

### *exception* outrage.smartsearch.JudgeError(code: str, \*\*details: Any)
16647 16651 176

### *class* outrage.smartsearch.Judgement(answers: Mapping[str, Answer], input_tokens: int = 0)
17060 17064 182

#### answers *: Mapping[str, Answer]*
17537 17541 188

#### input_tokens *: int*
17745 17749 190

### outrage.smartsearch.Level
17829 17833 192

### *class* outrage.smartsearch.LevelCounts(asked: int = 0, yes: int = 0, no: int = 0, missing: int = 0, unjudged: int = 0)
18072 18076 198

#### asked *: int*
18606 18610 204

#### yes *: int*
18716 18720 208

#### no *: int*
18791 18795 210

#### missing *: int*
18865 18869 212

#### unjudged *: int*
19036 19040 217

### *class* outrage.smartsearch.LevelQuestions(questions: Question, state: Question)
19116 19120 219

#### questions *: Question*
19401 19405 225

#### state *: Question*
19536 19540 229

### *class* outrage.smartsearch.Match(key: str, probability: float, decision: Literal['yes', 'unsure'], decided_at: Literal['title', 'keywords', 'summary', 'contents', 'body'] | None, evidence: tuple[Evidence, ...])
19658 19662 233

#### key *: str*
20373 20377 239

#### probability *: float*
20447 20451 241

#### decision *: Literal['yes', 'unsure']*
20534 20538 243

#### decided_at *: Literal['title', 'keywords', 'summary', 'contents', 'body'] | None*
20642 20646 245

#### evidence *: tuple[Evidence, ...]*
20954 20958 250

### *class* outrage.smartsearch.Question(kind: ~typing.Literal['noul', 'score'], text: str, criteria: tuple[str, ...] = (), instructions: ~collections.abc.Mapping[str, str] = <factory>)
21085 21089 252

#### kind *: Literal['noul', 'score']*
21778 21782 264

#### text *: str*
21994 21998 269

#### criteria *: tuple[str, ...]*
22069 22073 271

#### instructions *: Mapping[str, str]*
22289 22293 275

### *class* outrage.smartsearch.Scoring(weights: ~collections.abc.Mapping[~typing.Literal['title', 'keywords', 'summary', 'contents', 'body'], float] = <factory>, supporting: frozenset[~typing.Literal['title', 'keywords', 'summary', 'contents', 'body']] = frozenset({'keywords', 'title'}), yes: float = 0.8, no: float = 0.2)
22524 22528 277

#### weights *: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], float]*
23851 23855 297

#### supporting *: frozenset[Literal['title', 'keywords', 'summary', 'contents', 'body']]*
24150 24154 299

#### yes *: float*
24576 24580 305

#### no *: float*
24725 24729 309

#### combine(evidence: Sequence[Evidence]) → float
24847 24851 313

#### decide(probability: float) → Literal['yes', 'no', 'unsure']
25143 25149 317

### outrage.smartsearch.Shape
25373 25381 321

### *class* outrage.smartsearch.SmartSearchResult(key: str | None, query: str, matches: tuple[Match, ...], unjudged: tuple[Unjudged, ...], levels: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], LevelCounts], documents: int, total: int, next_cursor: str | None, unavailable: tuple[str, ...], input_tokens: int)
25819 25827 332

#### key *: str | None*
27364 27372 342

#### query *: str*
27503 27511 344

#### matches *: tuple[Match, ...]*
27579 27587 346

#### unjudged *: tuple[Unjudged, ...]*
27746 27754 350

#### levels *: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], LevelCounts]*
27877 27885 352

#### documents *: int*
28158 28166 354

#### total *: int*
28265 28273 358

#### next_cursor *: str | None*
28375 28383 362

#### unavailable *: tuple[str, ...]*
28522 28530 364

#### input_tokens *: int*
28716 28724 368

### *exception* outrage.smartsearch.StateTooLarge(code: str, \*\*details: Any)
28800 28808 370

### *class* outrage.smartsearch.Unjudged(key: str, level: Literal['title', 'keywords', 'summary', 'contents', 'body'], code: str, details: Mapping[str, object], evidence: tuple[Evidence, ...])
29126 29134 376

#### key *: str*
29913 29921 382

#### level *: Literal['title', 'keywords', 'summary', 'contents', 'body']*
29987 29995 384

#### code *: str*
30127 30135 386

#### details *: Mapping[str, object]*
30296 30304 390

#### evidence *: tuple[Evidence, ...]*
30533 30541 392

### outrage.smartsearch.refusals(query: str, levels: Sequence[str] = LEVELS, shapes: Mapping[str, str] | None = None) → list[Refusal]
30707 30715 396

### outrage.smartsearch.smart_search(store: Store, key: str | None, query: str, judge: Judge, \*, depth: int | None = None, limit: int = DEFAULT_LIMIT, after: str | None = None, levels: Sequence[Literal['title', 'keywords', 'summary', 'contents', 'body']] = LEVELS, shapes: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], Literal['questions', 'state']] | None = None, questions: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], LevelQuestions] = SCORE_QUESTIONS, scoring: Scoring | None = None, batch_size: int = DEFAULT_BATCH_SIZE, value_chars: int = DEFAULT_VALUE_CHARS, chunk_chars: int = DEFAULT_CHUNK_CHARS, max_chunks: int = DEFAULT_MAX_CHUNKS) → SmartSearchResult
31446 31456 400
