# outrage.smartsearch
0 0 1

### outrage.smartsearch.DEFAULT_BATCH_SIZE *= 50*
2259 2259 40

### outrage.smartsearch.DEFAULT_CHUNK_CHARS *= 60000*
2461 2461 45

### outrage.smartsearch.DEFAULT_LIMIT *= 100*
2811 2811 52

### outrage.smartsearch.DEFAULT_MAX_CHUNKS *= 16*
2991 2991 57

### outrage.smartsearch.DEFAULT_SHAPES *: Mapping[Literal['title', 'summary', 'contents', 'body'], Literal['questions', 'state']]* *= {'body': 'state', 'contents': 'questions', 'summary': 'questions', 'title': 'questions'}*
3186 3186 62

### outrage.smartsearch.DEFAULT_VALUE_CHARS *= 8000*
3695 3695 66

### outrage.smartsearch.LEVELS *: tuple[Literal['title', 'summary', 'contents', 'body'], ...]* *= ('title', 'summary', 'contents', 'body')*
3886 3886 71

### outrage.smartsearch.MIN_CHUNK_CHARS *= 1000*
4414 4414 79

### outrage.smartsearch.NOUL_QUESTIONS *: Mapping[Literal['title', 'summary', 'contents', 'body'], LevelQuestions]* *= {'body': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`body\` is the text, or one part of it, of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the text, or one part of it, of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={})), 'contents': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`contents\` is the table of contents (its headings) of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the table of contents (its headings) of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={})), 'summary': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`summary\` is the summary of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the summary of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={})), 'title': LevelQuestions(questions=Question(kind='noul', text='The state is a search query. \`title\` is the title of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=(), instructions={}), state=Question(kind='noul', text='The state is the title of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=(), instructions={}))}*
4603 4603 84

### outrage.smartsearch.SCORE_QUESTIONS *: Mapping[Literal['title', 'summary', 'contents', 'body'], LevelQuestions]* *= {'body': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`body\` is the text, or one part of it, of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the text, or one part of it, of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'contents': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`contents\` is the table of contents (its headings) of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the table of contents (its headings) of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'summary': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`summary\` is the summary of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the summary of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={})), 'title': LevelQuestions(questions=Question(kind='score', text='The state is a search query. \`title\` is the title of the stored document at \`key\`. Is that document likely to be relevant to the query?', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}), state=Question(kind='score', text='The state is the title of one stored document. Is that document likely to be relevant to this search query: {query}', criteria=('no relevance to the query topic', 'relevant to a related topic', 'relevant to the query topic', 'directly addresses the query'), instructions={}))}*
6762 6762 88

### *class* outrage.smartsearch.Answer(probability: float | None = None, score: float | None = None, probabilities: tuple[float, ...] = (), confidence: float | None = None)
10102 10102 96

#### probability *: float | None*
11070 11070 106

#### score *: float | None*
11222 11222 108

#### probabilities *: tuple[float, ...]*
11368 11368 110

#### confidence *: float | None*
11527 11527 112

#### as_probability(levels: int | None = None) → float
11678 11678 114

### outrage.smartsearch.Decision
12213 12215 123

### *class* outrage.smartsearch.Evidence(level: Literal['title', 'summary', 'contents', 'body'], answer: Answer, probability: float, chunks: int = 1, partial: bool = False)
12433 12435 129

#### level *: Literal['title', 'summary', 'contents', 'body']*
13021 13023 135

#### answer *: Answer*
13149 13151 137

#### probability *: float*
13204 13206 139

#### chunks *: int*
13340 13342 143

#### partial *: bool*
13538 13540 148

### *class* outrage.smartsearch.Judge(\*args, \*\*kwargs)
13765 13767 153

#### judge(state: str, questions: Mapping[str, Question]) → Judgement
14207 14209 163

### *exception* outrage.smartsearch.JudgeError(code: str, \*\*details: Any)
14539 14543 165

### *class* outrage.smartsearch.Judgement(answers: Mapping[str, Answer], input_tokens: int = 0)
14952 14956 171

#### answers *: Mapping[str, Answer]*
15429 15433 177

#### input_tokens *: int*
15637 15641 179

### outrage.smartsearch.Level
15721 15725 181

### *class* outrage.smartsearch.LevelCounts(asked: int = 0, yes: int = 0, no: int = 0, missing: int = 0, unjudged: int = 0)
15952 15956 187

#### asked *: int*
16486 16490 193

#### yes *: int*
16596 16600 197

#### no *: int*
16671 16675 199

#### missing *: int*
16745 16749 201

#### unjudged *: int*
16916 16920 206

### *class* outrage.smartsearch.LevelQuestions(questions: Question, state: Question)
16996 17000 208

#### questions *: Question*
17281 17285 214

#### state *: Question*
17416 17420 218

### *class* outrage.smartsearch.Match(key: str, probability: float, decision: Literal['yes', 'unsure'], decided_at: Literal['title', 'summary', 'contents', 'body'] | None, evidence: tuple[Evidence, ...])
17538 17542 222

#### key *: str*
18241 18245 228

#### probability *: float*
18315 18319 230

#### decision *: Literal['yes', 'unsure']*
18402 18406 232

#### decided_at *: Literal['title', 'summary', 'contents', 'body'] | None*
18510 18514 234

#### evidence *: tuple[Evidence, ...]*
18810 18814 239

### *class* outrage.smartsearch.Question(kind: ~typing.Literal['noul', 'score'], text: str, criteria: tuple[str, ...] = (), instructions: ~collections.abc.Mapping[str, str] = <factory>)
18941 18945 241

#### kind *: Literal['noul', 'score']*
19634 19638 253

#### text *: str*
19850 19854 258

#### criteria *: tuple[str, ...]*
19925 19929 260

#### instructions *: Mapping[str, str]*
20145 20149 264

### *class* outrage.smartsearch.Scoring(weights: ~collections.abc.Mapping[~typing.Literal['title', 'summary', 'contents', 'body'], float] = <factory>, yes: float = 0.8, no: float = 0.2)
20380 20384 266

#### weights *: Mapping[Literal['title', 'summary', 'contents', 'body'], float]*
21568 21572 286

#### yes *: float*
21855 21859 288

#### no *: float*
22004 22008 292

#### combine(evidence: Sequence[Evidence]) → float
22126 22130 296

#### decide(probability: float) → Literal['yes', 'no', 'unsure']
22422 22428 300

### outrage.smartsearch.Shape
22652 22660 304

### *class* outrage.smartsearch.SmartSearchResult(key: str | None, query: str, matches: tuple[Match, ...], unjudged: tuple[Unjudged, ...], levels: Mapping[Literal['title', 'summary', 'contents', 'body'], LevelCounts], documents: int, total: int, next_cursor: str | None, unavailable: tuple[str, ...], input_tokens: int)
23098 23106 315

#### key *: str | None*
24631 24639 325

#### query *: str*
24770 24778 327

#### matches *: tuple[Match, ...]*
24846 24854 329

#### unjudged *: tuple[Unjudged, ...]*
25013 25021 333

#### levels *: Mapping[Literal['title', 'summary', 'contents', 'body'], LevelCounts]*
25144 25152 335

#### documents *: int*
25413 25421 337

#### total *: int*
25520 25528 341

#### next_cursor *: str | None*
25630 25638 345

#### unavailable *: tuple[str, ...]*
25777 25785 347

#### input_tokens *: int*
25971 25979 351

### *exception* outrage.smartsearch.StateTooLarge(code: str, \*\*details: Any)
26055 26063 353

### *class* outrage.smartsearch.Unjudged(key: str, level: Literal['title', 'summary', 'contents', 'body'], code: str, details: Mapping[str, object], evidence: tuple[Evidence, ...])
26381 26389 359

#### key *: str*
27156 27164 365

#### level *: Literal['title', 'summary', 'contents', 'body']*
27230 27238 367

#### code *: str*
27358 27366 369

#### details *: Mapping[str, object]*
27527 27535 373

#### evidence *: tuple[Evidence, ...]*
27764 27772 375

### outrage.smartsearch.refusals(query: str, levels: Sequence[str] = LEVELS, shapes: Mapping[str, str] | None = None) → list[Refusal]
27938 27946 379

### outrage.smartsearch.smart_search(store: Store, key: str | None, query: str, judge: Judge, \*, depth: int | None = None, limit: int = DEFAULT_LIMIT, after: str | None = None, levels: Sequence[Literal['title', 'summary', 'contents', 'body']] = LEVELS, shapes: Mapping[Literal['title', 'summary', 'contents', 'body'], Literal['questions', 'state']] | None = None, questions: Mapping[Literal['title', 'summary', 'contents', 'body'], LevelQuestions] = NOUL_QUESTIONS, scoring: Scoring | None = None, batch_size: int = DEFAULT_BATCH_SIZE, value_chars: int = DEFAULT_VALUE_CHARS, chunk_chars: int = DEFAULT_CHUNK_CHARS, max_chunks: int = DEFAULT_MAX_CHUNKS) → SmartSearchResult
28677 28687 383
