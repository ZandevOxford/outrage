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

### outrage.smartsearch.RULES *= ('log-odds-sum',)*
8006 8006 98

### outrage.smartsearch.SCORE_QUESTIONS *: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], LevelQuestions]* *= {'body': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`body\` is the text, or one part of it, of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the text, or one part of it, of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'contents': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`contents\` is the table of contents (its headings) of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the table of contents (its headings) of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'keywords': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`keywords\` is the keywords of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the keywords of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'summary': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`summary\` is the summary of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the summary of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'title': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`title\` is the title of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the title of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}))}*
8234 8234 103

### outrage.smartsearch.TUNING_FORMAT *= 1*
12414 12414 112

### outrage.smartsearch.TUNING_NAMES *= ('format', 'question', 'levels', 'scoring', 'requests', 'kind', 'criteria', 'questions', 'state', 'name', 'meta', 'what', 'shape', 'weight', 'supporting', 'rule', 'yes', 'no', 'clamp', 'limit', 'batch_size', 'value_chars', 'chunk_chars', 'max_chunks', 'min_chunk_chars', 'note', 'value', 'contents', 'body', 'score', 'noul', 'log-odds-sum')*
12528 12528 116

### outrage.smartsearch.TUNING_PATH *= ('smart-search', 'tuning.json')*
13065 13065 121

### *class* outrage.smartsearch.Answer(probability: float | None = None, score: float | None = None, probabilities: tuple[float, ...] = (), confidence: float | None = None)
13283 13283 126

#### probability *: float | None*
14251 14251 136

#### score *: float | None*
14403 14403 138

#### probabilities *: tuple[float, ...]*
14549 14549 140

#### confidence *: float | None*
14708 14708 142

#### as_probability(levels: int | None = None) → float
14859 14859 144

### outrage.smartsearch.Decision
15394 15396 153

### *class* outrage.smartsearch.Evidence(level: Literal['title', 'keywords', 'summary', 'contents', 'body'], answer: Answer, probability: float, chunks: int = 1, partial: bool = False)
15614 15616 159

#### level *: Literal['title', 'keywords', 'summary', 'contents', 'body']*
16214 16216 165

#### answer *: Answer*
16354 16356 167

#### probability *: float*
16409 16411 169

#### chunks *: int*
16545 16547 173

#### partial *: bool*
16743 16745 178

### *class* outrage.smartsearch.Judge(\*args, \*\*kwargs)
16970 16972 183

#### judge(state: str, questions: Mapping[str, Question]) → Judgement
17412 17414 193

### *exception* outrage.smartsearch.JudgeError(code: str, \*\*details: Any)
17744 17748 195

### *class* outrage.smartsearch.Judgement(answers: Mapping[str, Answer], input_tokens: int = 0)
18157 18161 201

#### answers *: Mapping[str, Answer]*
18634 18638 207

#### input_tokens *: int*
18842 18846 209

### outrage.smartsearch.Kind
18926 18930 211

### outrage.smartsearch.Level
19313 19317 220

### *class* outrage.smartsearch.LevelCounts(asked: int = 0, yes: int = 0, no: int = 0, missing: int = 0, unjudged: int = 0)
19556 19560 226

#### asked *: int*
20090 20094 232

#### yes *: int*
20200 20204 236

#### no *: int*
20275 20279 238

#### missing *: int*
20349 20353 240

#### unjudged *: int*
20520 20524 245

### *class* outrage.smartsearch.LevelQuestions(questions: Question, state: Question)
20600 20604 247

#### questions *: Question*
20885 20889 253

#### state *: Question*
21020 21024 257

### *class* outrage.smartsearch.LevelTuning(name: str, kind: Literal['value', 'contents', 'body'], meta: str | None, shape: Literal['questions', 'state'], weight: float, supporting: bool, questions: LevelQuestions)
21142 21146 261

#### name *: str*
21942 21946 267

#### kind *: Literal['value', 'contents', 'body']*
22085 22089 271

#### meta *: str | None*
22201 22205 273

#### shape *: Literal['questions', 'state']*
22402 22406 277

#### weight *: float*
22512 22516 279

#### supporting *: bool*
22594 22598 281

#### questions *: LevelQuestions*
22678 22682 283

### *class* outrage.smartsearch.Match(key: str, probability: float, decision: Literal['yes', 'unsure'], decided_at: Literal['title', 'keywords', 'summary', 'contents', 'body'] | None, evidence: tuple[Evidence, ...])
22823 22827 287

#### key *: str*
23538 23542 293

#### probability *: float*
23612 23616 295

#### decision *: Literal['yes', 'unsure']*
23699 23703 297

#### decided_at *: Literal['title', 'keywords', 'summary', 'contents', 'body'] | None*
23807 23811 299

#### evidence *: tuple[Evidence, ...]*
24119 24123 304

### *class* outrage.smartsearch.Question(kind: ~typing.Literal['noul', 'score'], text: str, criteria: tuple[str, ...] = (), instructions: ~collections.abc.Mapping[str, str] = <factory>)
24250 24254 306

#### kind *: Literal['noul', 'score']*
24943 24947 318

#### text *: str*
25159 25163 323

#### criteria *: tuple[str, ...]*
25234 25238 325

#### instructions *: Mapping[str, str]*
25454 25458 329

### *class* outrage.smartsearch.Requests(limit: int, batch_size: int, value_chars: int, chunk_chars: int, max_chunks: int, min_chunk_chars: int)
25689 25693 331

#### limit *: int*
26354 26358 337

#### batch_size *: int*
26431 26435 339

#### value_chars *: int*
26513 26517 341

#### chunk_chars *: int*
26596 26600 343

#### max_chunks *: int*
26679 26683 345

#### min_chunk_chars *: int*
26761 26765 347

### *class* outrage.smartsearch.Scoring(weights: ~collections.abc.Mapping[~typing.Literal['title', 'keywords', 'summary', 'contents', 'body'], float] = <factory>, supporting: frozenset[~typing.Literal['title', 'keywords', 'summary', 'contents', 'body']] = frozenset({'keywords', 'title'}), yes: float = 0.8, no: float = 0.2, clamp: float = 0.0001)
26848 26852 349

#### weights *: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], float]*
28198 28202 369

#### supporting *: frozenset[Literal['title', 'keywords', 'summary', 'contents', 'body']]*
28497 28501 371

#### yes *: float*
28923 28927 377

#### no *: float*
29072 29076 381

#### clamp *: float*
29194 29198 385

#### combine(evidence: Sequence[Evidence]) → float
29407 29411 390

#### decide(probability: float) → Literal['yes', 'no', 'unsure']
29703 29709 394

### outrage.smartsearch.Shape
29933 29941 398

### *class* outrage.smartsearch.SmartSearchResult(key: str | None, query: str, matches: tuple[Match, ...], unjudged: tuple[Unjudged, ...], levels: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], LevelCounts], documents: int, total: int, next_cursor: str | None, unavailable: tuple[str, ...], input_tokens: int)
30379 30387 409

#### key *: str | None*
31924 31932 419

#### query *: str*
32063 32071 421

#### matches *: tuple[Match, ...]*
32139 32147 423

#### unjudged *: tuple[Unjudged, ...]*
32306 32314 427

#### levels *: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], LevelCounts]*
32437 32445 429

#### documents *: int*
32718 32726 431

#### total *: int*
32825 32833 435

#### next_cursor *: str | None*
32935 32943 439

#### unavailable *: tuple[str, ...]*
33082 33090 441

#### input_tokens *: int*
33276 33284 445

### *exception* outrage.smartsearch.StateTooLarge(code: str, \*\*details: Any)
33360 33368 447

### *class* outrage.smartsearch.Tuning(levels: tuple[LevelTuning, ...], scoring: Scoring, requests: Requests, source: str)
33686 33694 453

#### levels *: tuple[LevelTuning, ...]*
34423 34431 463

#### scoring *: Scoring*
34577 34585 467

#### requests *: Requests*
34635 34643 469

#### source *: str*
34696 34704 471

#### *property* names *: tuple[str, ...]*
34821 34829 475

#### level(name: str) → LevelTuning
35014 35022 479

#### *classmethod* read(data: object, source: str) → tuple[Tuning | None, list[Refusal]]
35263 35273 483

#### *classmethod* read_file(path: Path | None = None) → tuple[Tuning | None, list[Refusal]]
36026 36038 492

#### *classmethod* load(path: Path | None = None) → Tuning
36572 36586 496

### *class* outrage.smartsearch.Unjudged(key: str, level: Literal['title', 'keywords', 'summary', 'contents', 'body'], code: str, details: Mapping[str, object], evidence: tuple[Evidence, ...])
36881 36897 500

#### key *: str*
37668 37684 506

#### level *: Literal['title', 'keywords', 'summary', 'contents', 'body']*
37742 37758 508

#### code *: str*
37882 37898 510

#### details *: Mapping[str, object]*
38051 38067 514

#### evidence *: tuple[Evidence, ...]*
38288 38304 516

### outrage.smartsearch.refusals(query: str, levels: Sequence[str] = LEVELS, shapes: Mapping[str, str] | None = None) → list[Refusal]
38462 38478 520

### outrage.smartsearch.smart_search(store: Store, key: str | None, query: str, judge: Judge, \*, depth: int | None = None, limit: int = DEFAULT_LIMIT, after: str | None = None, levels: Sequence[Literal['title', 'keywords', 'summary', 'contents', 'body']] = LEVELS, shapes: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], Literal['questions', 'state']] | None = None, questions: Mapping[Literal['title', 'keywords', 'summary', 'contents', 'body'], LevelQuestions] = SCORE_QUESTIONS, scoring: Scoring | None = None, batch_size: int = DEFAULT_BATCH_SIZE, value_chars: int = DEFAULT_VALUE_CHARS, chunk_chars: int = DEFAULT_CHUNK_CHARS, max_chunks: int = DEFAULT_MAX_CHUNKS) → SmartSearchResult
39201 39219 524
