# outrage.smartsearch
0 0 1

### outrage.smartsearch.RULES *= ('log-odds-sum',)*
2795 2795 48

### outrage.smartsearch.TUNING_FORMAT *= 1*
3023 3023 53

### outrage.smartsearch.TUNING_NAMES *= ('format', 'question', 'levels', 'scoring', 'requests', 'kind', 'criteria', 'questions', 'state', 'name', 'meta', 'what', 'shape', 'weight', 'supporting', 'rule', 'yes', 'no', 'clamp', 'limit', 'batch_size', 'value_chars', 'chunk_chars', 'max_chunks', 'min_chunk_chars', 'note', 'value', 'contents', 'body', 'score', 'noul', 'log-odds-sum')*
3137 3137 57

### outrage.smartsearch.TUNING_PATH *= ('smart-search', 'tuning.json')*
3674 3674 62

### *class* outrage.smartsearch.Answer(probability: float | None = None, score: float | None = None, probabilities: tuple[float, ...] = (), confidence: float | None = None)
3892 3892 67

#### probability *: float | None*
4860 4860 77

#### score *: float | None*
5012 5012 79

#### probabilities *: tuple[float, ...]*
5158 5158 81

#### confidence *: float | None*
5317 5317 83

#### as_probability(levels: int | None = None) → float
5468 5468 85

### outrage.smartsearch.Decision
6003 6005 94

### *class* outrage.smartsearch.Evidence(level: str, answer: Answer, probability: float, chunks: int = 1, partial: bool = False)
6223 6225 100

#### level *: str*
6759 6761 106

#### answer *: Answer*
6835 6837 108

#### probability *: float*
6890 6892 110

#### chunks *: int*
7026 7028 114

#### partial *: bool*
7224 7226 119

### *class* outrage.smartsearch.Judge(\*args, \*\*kwargs)
7451 7453 124

#### judge(state: str, questions: Mapping[str, Question]) → Judgement
7893 7895 134

### *exception* outrage.smartsearch.JudgeError(code: str, \*\*details: Any)
8225 8229 136

### *class* outrage.smartsearch.Judgement(answers: Mapping[str, Answer], input_tokens: int = 0)
8638 8642 142

#### answers *: Mapping[str, Answer]*
9115 9119 148

#### input_tokens *: int*
9323 9327 150

### outrage.smartsearch.Kind
9407 9411 152

### outrage.smartsearch.Level
9794 9798 161

### *class* outrage.smartsearch.LevelCounts(asked: int = 0, yes: int = 0, no: int = 0, missing: int = 0, unjudged: int = 0)
9974 9978 166

#### asked *: int*
10508 10512 172

#### yes *: int*
10618 10622 176

#### no *: int*
10693 10697 178

#### missing *: int*
10767 10771 180

#### unjudged *: int*
10938 10942 185

### *class* outrage.smartsearch.LevelQuestions(questions: Question, state: Question)
11018 11022 187

#### questions *: Question*
11303 11307 193

#### state *: Question*
11438 11442 197

### *class* outrage.smartsearch.LevelTuning(name: str, kind: Literal['value', 'contents', 'body'], meta: str | None, shape: Literal['questions', 'state'], weight: float, supporting: bool, questions: LevelQuestions)
11560 11564 201

#### name *: str*
12360 12364 207

#### kind *: Literal['value', 'contents', 'body']*
12503 12507 211

#### meta *: str | None*
12619 12623 213

#### shape *: Literal['questions', 'state']*
12820 12824 217

#### weight *: float*
12930 12934 219

#### supporting *: bool*
13012 13016 221

#### questions *: LevelQuestions*
13096 13100 223

### *class* outrage.smartsearch.Match(key: str, probability: float, decision: Literal['yes', 'unsure'], decided_at: str | None, evidence: tuple[Evidence, ...])
13241 13245 227

#### key *: str*
13892 13896 233

#### probability *: float*
13966 13970 235

#### decision *: Literal['yes', 'unsure']*
14053 14057 237

#### decided_at *: str | None*
14161 14165 239

#### evidence *: tuple[Evidence, ...]*
14409 14413 244

### *class* outrage.smartsearch.Question(kind: ~typing.Literal['noul', 'score'], text: str, criteria: tuple[str, ...] = (), instructions: ~collections.abc.Mapping[str, str] = <factory>)
14540 14544 246

#### kind *: Literal['noul', 'score']*
15233 15237 258

#### text *: str*
15449 15453 263

#### criteria *: tuple[str, ...]*
15524 15528 265

#### instructions *: Mapping[str, str]*
15744 15748 269

### *class* outrage.smartsearch.Requests(limit: int, batch_size: int, value_chars: int, chunk_chars: int, max_chunks: int, min_chunk_chars: int)
15979 15983 271

#### limit *: int*
16644 16648 277

#### batch_size *: int*
16721 16725 279

#### value_chars *: int*
16803 16807 281

#### chunk_chars *: int*
16886 16890 283

#### max_chunks *: int*
16969 16973 285

#### min_chunk_chars *: int*
17051 17055 287

### *class* outrage.smartsearch.Scoring(weights: Mapping[str, float], supporting: frozenset[str], yes: float, no: float, clamp: float)
17138 17142 289

#### weights *: Mapping[str, float]*
18833 18837 310

#### supporting *: frozenset[str]*
19121 19125 314

#### yes *: float*
19483 19487 320

#### no *: float*
19632 19636 324

#### clamp *: float*
19754 19758 328

#### combine(evidence: Sequence[Evidence]) → float
19967 19971 333

#### decide(probability: float) → Literal['yes', 'no', 'unsure']
20263 20269 337

### outrage.smartsearch.Shape
20493 20501 341

### *class* outrage.smartsearch.SmartSearchResult(key: str | None, query: str, matches: tuple[Match, ...], unjudged: tuple[Unjudged, ...], levels: Mapping[str, LevelCounts], documents: int, total: int, next_cursor: str | None, unavailable: tuple[str, ...], input_tokens: int)
20939 20947 352

#### key *: str | None*
22420 22428 362

#### query *: str*
22559 22567 364

#### matches *: tuple[Match, ...]*
22635 22643 366

#### unjudged *: tuple[Unjudged, ...]*
22802 22810 370

#### levels *: Mapping[str, LevelCounts]*
22933 22941 372

#### documents *: int*
23150 23158 374

#### total *: int*
23257 23265 378

#### next_cursor *: str | None*
23367 23375 382

#### unavailable *: tuple[str, ...]*
23514 23522 384

#### input_tokens *: int*
23708 23716 388

### *exception* outrage.smartsearch.StateTooLarge(code: str, \*\*details: Any)
23792 23800 390

### *class* outrage.smartsearch.Tuning(levels: tuple[LevelTuning, ...], scoring: Scoring, requests: Requests, source: str)
24118 24126 396

#### levels *: tuple[LevelTuning, ...]*
24855 24863 406

#### scoring *: Scoring*
25009 25017 410

#### requests *: Requests*
25067 25075 412

#### source *: str*
25128 25136 414

#### *property* names *: tuple[str, ...]*
25253 25261 418

#### level(name: str) → LevelTuning
25446 25454 422

#### *classmethod* read(data: object, source: str) → tuple[Tuning | None, list[Refusal]]
25695 25705 426

#### *classmethod* read_file(path: Path | None = None) → tuple[Tuning | None, list[Refusal]]
26458 26470 435

#### *classmethod* load(path: Path | None = None) → Tuning
27004 27018 439

### *class* outrage.smartsearch.Unjudged(key: str, level: str, code: str, details: Mapping[str, object], evidence: tuple[Evidence, ...])
27313 27329 443

#### key *: str*
28036 28052 449

#### level *: str*
28110 28126 451

#### code *: str*
28186 28202 453

#### details *: Mapping[str, object]*
28355 28371 457

#### evidence *: tuple[Evidence, ...]*
28592 28608 459

### outrage.smartsearch.packaged_tuning() → tuple[Tuning | None, tuple[Refusal, ...]]
28766 28782 463

### outrage.smartsearch.refusals(query: str, levels: Sequence[str] | None = None, \*, tuning: Tuning | None = None) → list[Refusal]
29297 29315 470

### outrage.smartsearch.smart_search(store: Store, key: str | None, query: str, judge: Judge, \*, tuning: Tuning | None = None, depth: int | None = None, limit: int | None = None, after: str | None = None, levels: Sequence[str] | None = None) → SmartSearchResult
30070 30090 477
