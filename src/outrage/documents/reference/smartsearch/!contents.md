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

### outrage.smartsearch.DEFAULT_SHAPES *: Mapping[str, Literal['questions', 'state']]* *= {'body': 'state', 'contents': 'questions', 'keywords': 'questions', 'summary': 'questions', 'title': 'questions'}*
3846 3846 71

### outrage.smartsearch.DEFAULT_VALUE_CHARS *= 8000*
4328 4328 75

### outrage.smartsearch.LEVELS *: tuple[str, ...]* *= ('title', 'keywords', 'summary', 'contents', 'body')*
4519 4519 80

### outrage.smartsearch.MIN_CHUNK_CHARS *= 1000*
5083 5083 89

### outrage.smartsearch.NOUL_QUESTIONS *: Mapping[str, LevelQuestions]* *= {'body': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`body\` is the text, or one part of it, of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the text, or one part of it, of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={})), 'contents': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`contents\` is the table of contents (its headings) of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the table of contents (its headings) of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={})), 'keywords': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`keywords\` is the keywords of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the keywords of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={})), 'summary': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`summary\` is the summary of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the summary of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={})), 'title': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`title\` is the title of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the title of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={}))}*
5272 5272 94

### outrage.smartsearch.RULES *= ('log-odds-sum',)*
7814 7814 98

### outrage.smartsearch.SCORE_QUESTIONS *: Mapping[str, LevelQuestions]* *= {'body': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`body\` is the text, or one part of it, of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the text, or one part of it, of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'contents': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`contents\` is the table of contents (its headings) of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the table of contents (its headings) of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'keywords': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`keywords\` is the keywords of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the keywords of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'summary': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`summary\` is the summary of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the summary of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'title': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`title\` is the title of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the title of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}))}*
8042 8042 103

### outrage.smartsearch.TUNING_FORMAT *= 1*
12158 12158 112

### outrage.smartsearch.TUNING_NAMES *= ('format', 'question', 'levels', 'scoring', 'requests', 'kind', 'criteria', 'questions', 'state', 'name', 'meta', 'what', 'shape', 'weight', 'supporting', 'rule', 'yes', 'no', 'clamp', 'limit', 'batch_size', 'value_chars', 'chunk_chars', 'max_chunks', 'min_chunk_chars', 'note', 'value', 'contents', 'body', 'score', 'noul', 'log-odds-sum')*
12272 12272 116

### outrage.smartsearch.TUNING_PATH *= ('smart-search', 'tuning.json')*
12809 12809 121

### *class* outrage.smartsearch.Answer(probability: float | None = None, score: float | None = None, probabilities: tuple[float, ...] = (), confidence: float | None = None)
13027 13027 126

#### probability *: float | None*
13995 13995 136

#### score *: float | None*
14147 14147 138

#### probabilities *: tuple[float, ...]*
14293 14293 140

#### confidence *: float | None*
14452 14452 142

#### as_probability(levels: int | None = None) → float
14603 14603 144

### outrage.smartsearch.Decision
15138 15140 153

### *class* outrage.smartsearch.Evidence(level: str, answer: Answer, probability: float, chunks: int = 1, partial: bool = False)
15358 15360 159

#### level *: str*
15894 15896 165

#### answer *: Answer*
15970 15972 167

#### probability *: float*
16025 16027 169

#### chunks *: int*
16161 16163 173

#### partial *: bool*
16359 16361 178

### *class* outrage.smartsearch.Judge(\*args, \*\*kwargs)
16586 16588 183

#### judge(state: str, questions: Mapping[str, Question]) → Judgement
17028 17030 193

### *exception* outrage.smartsearch.JudgeError(code: str, \*\*details: Any)
17360 17364 195

### *class* outrage.smartsearch.Judgement(answers: Mapping[str, Answer], input_tokens: int = 0)
17773 17777 201

#### answers *: Mapping[str, Answer]*
18250 18254 207

#### input_tokens *: int*
18458 18462 209

### outrage.smartsearch.Kind
18542 18546 211

### outrage.smartsearch.Level
18929 18933 220

### *class* outrage.smartsearch.LevelCounts(asked: int = 0, yes: int = 0, no: int = 0, missing: int = 0, unjudged: int = 0)
19109 19113 225

#### asked *: int*
19643 19647 231

#### yes *: int*
19753 19757 235

#### no *: int*
19828 19832 237

#### missing *: int*
19902 19906 239

#### unjudged *: int*
20073 20077 244

### *class* outrage.smartsearch.LevelQuestions(questions: Question, state: Question)
20153 20157 246

#### questions *: Question*
20438 20442 252

#### state *: Question*
20573 20577 256

### *class* outrage.smartsearch.LevelTuning(name: str, kind: Literal['value', 'contents', 'body'], meta: str | None, shape: Literal['questions', 'state'], weight: float, supporting: bool, questions: LevelQuestions)
20695 20699 260

#### name *: str*
21495 21499 266

#### kind *: Literal['value', 'contents', 'body']*
21638 21642 270

#### meta *: str | None*
21754 21758 272

#### shape *: Literal['questions', 'state']*
21955 21959 276

#### weight *: float*
22065 22069 278

#### supporting *: bool*
22147 22151 280

#### questions *: LevelQuestions*
22231 22235 282

### *class* outrage.smartsearch.Match(key: str, probability: float, decision: Literal['yes', 'unsure'], decided_at: str | None, evidence: tuple[Evidence, ...])
22376 22380 286

#### key *: str*
23027 23031 292

#### probability *: float*
23101 23105 294

#### decision *: Literal['yes', 'unsure']*
23188 23192 296

#### decided_at *: str | None*
23296 23300 298

#### evidence *: tuple[Evidence, ...]*
23544 23548 303

### *class* outrage.smartsearch.Question(kind: ~typing.Literal['noul', 'score'], text: str, criteria: tuple[str, ...] = (), instructions: ~collections.abc.Mapping[str, str] = <factory>)
23675 23679 305

#### kind *: Literal['noul', 'score']*
24368 24372 317

#### text *: str*
24584 24588 322

#### criteria *: tuple[str, ...]*
24659 24663 324

#### instructions *: Mapping[str, str]*
24879 24883 328

### *class* outrage.smartsearch.Requests(limit: int, batch_size: int, value_chars: int, chunk_chars: int, max_chunks: int, min_chunk_chars: int)
25114 25118 330

#### limit *: int*
25779 25783 336

#### batch_size *: int*
25856 25860 338

#### value_chars *: int*
25938 25942 340

#### chunk_chars *: int*
26021 26025 342

#### max_chunks *: int*
26104 26108 344

#### min_chunk_chars *: int*
26186 26190 346

### *class* outrage.smartsearch.Scoring(weights: Mapping[str, float]=<factory>, supporting: frozenset[str] = frozenset({'keywords', 'title'}), yes: float = 0.8, no: float = 0.2, clamp: float = 0.0001)
26273 26277 348

#### weights *: Mapping[str, float]*
27771 27775 368

#### supporting *: frozenset[str]*
28006 28010 370

#### yes *: float*
28368 28372 376

#### no *: float*
28517 28521 380

#### clamp *: float*
28639 28643 384

#### combine(evidence: Sequence[Evidence]) → float
28852 28856 389

#### decide(probability: float) → Literal['yes', 'no', 'unsure']
29148 29154 393

### outrage.smartsearch.Shape
29378 29386 397

### *class* outrage.smartsearch.SmartSearchResult(key: str | None, query: str, matches: tuple[Match, ...], unjudged: tuple[Unjudged, ...], levels: Mapping[str, LevelCounts], documents: int, total: int, next_cursor: str | None, unavailable: tuple[str, ...], input_tokens: int)
29824 29832 408

#### key *: str | None*
31305 31313 418

#### query *: str*
31444 31452 420

#### matches *: tuple[Match, ...]*
31520 31528 422

#### unjudged *: tuple[Unjudged, ...]*
31687 31695 426

#### levels *: Mapping[str, LevelCounts]*
31818 31826 428

#### documents *: int*
32035 32043 430

#### total *: int*
32142 32150 434

#### next_cursor *: str | None*
32252 32260 438

#### unavailable *: tuple[str, ...]*
32399 32407 440

#### input_tokens *: int*
32593 32601 444

### *exception* outrage.smartsearch.StateTooLarge(code: str, \*\*details: Any)
32677 32685 446

### *class* outrage.smartsearch.Tuning(levels: tuple[LevelTuning, ...], scoring: Scoring, requests: Requests, source: str)
33003 33011 452

#### levels *: tuple[LevelTuning, ...]*
33740 33748 462

#### scoring *: Scoring*
33894 33902 466

#### requests *: Requests*
33952 33960 468

#### source *: str*
34013 34021 470

#### *property* names *: tuple[str, ...]*
34138 34146 474

#### level(name: str) → LevelTuning
34331 34339 478

#### *classmethod* read(data: object, source: str) → tuple[Tuning | None, list[Refusal]]
34580 34590 482

#### *classmethod* read_file(path: Path | None = None) → tuple[Tuning | None, list[Refusal]]
35343 35355 491

#### *classmethod* load(path: Path | None = None) → Tuning
35889 35903 495

### *class* outrage.smartsearch.Unjudged(key: str, level: str, code: str, details: Mapping[str, object], evidence: tuple[Evidence, ...])
36198 36214 499

#### key *: str*
36921 36937 505

#### level *: str*
36995 37011 507

#### code *: str*
37071 37087 509

#### details *: Mapping[str, object]*
37240 37256 513

#### evidence *: tuple[Evidence, ...]*
37477 37493 515

### outrage.smartsearch.packaged_tuning() → tuple[Tuning | None, tuple[Refusal, ...]]
37651 37667 519

### outrage.smartsearch.refusals(query: str, levels: Sequence[str] | None = None, shapes: Mapping[str, str] | None = None, \*, tuning: Tuning | None = None) → list[Refusal]
38182 38200 526

### outrage.smartsearch.smart_search(store: Store, key: str | None, query: str, judge: Judge, \*, tuning: Tuning | None = None, depth: int | None = None, limit: int | None = None, after: str | None = None, levels: Sequence[str] | None = None, shapes: Mapping[str, Literal['questions', 'state']] | None = None, questions: Mapping[str, LevelQuestions] | None = None, scoring: Scoring | None = None, batch_size: int | None = None, value_chars: int | None = None, chunk_chars: int | None = None, max_chunks: int | None = None) → SmartSearchResult
39248 39268 533
