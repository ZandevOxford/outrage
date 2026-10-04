# outrage.smartsearch
0 0 1

### outrage.smartsearch.QUERY *= 'query'*
2797 2797 48

### outrage.smartsearch.RULES *= ('log-odds-sum',)*
2912 2912 52

### outrage.smartsearch.TUNING_FORMAT *= 1*
3140 3140 57

### outrage.smartsearch.TUNING_NAMES *= ('format', 'question', 'levels', 'scoring', 'requests', 'kind', 'criteria', 'text', 'name', 'meta', 'what', 'shape', 'weight', 'supporting', 'rule', 'yes', 'no', 'clamp', 'limit', 'batch_size', 'value_chars', 'chunk_chars', 'max_chunks', 'min_chunk_chars', 'note', 'value', 'contents', 'body', 'questions', 'state', 'score', 'noul', 'log-odds-sum')*
3254 3254 61

### outrage.smartsearch.TUNING_PATH *= ('smart-search', 'tuning.json')*
3799 3799 66

### *class* outrage.smartsearch.Answer(probability: float | None = None, score: float | None = None, probabilities: tuple[float, ...] = (), confidence: float | None = None)
4017 4017 71

#### probability *: float | None*
4985 4985 81

#### score *: float | None*
5137 5137 83

#### probabilities *: tuple[float, ...]*
5283 5283 85

#### confidence *: float | None*
5442 5442 87

#### as_probability(levels: int | None = None) → float
5593 5593 89

### outrage.smartsearch.Decision
6128 6130 98

### *class* outrage.smartsearch.Evidence(level: str, answer: Answer, probability: float, chunks: int = 1, partial: bool = False)
6348 6350 104

#### level *: str*
6884 6886 110

#### answer *: Answer*
6960 6962 112

#### probability *: float*
7015 7017 114

#### chunks *: int*
7151 7153 118

#### partial *: bool*
7349 7351 123

### *class* outrage.smartsearch.Judge(\*args, \*\*kwargs)
7576 7578 128

#### judge(state: Mapping[str, str], questions: Mapping[str, Question]) → Judgement
8018 8020 138

### *exception* outrage.smartsearch.JudgeError(code: str, \*\*details: Any)
8502 8506 140

### *class* outrage.smartsearch.Judgement(answers: Mapping[str, Answer], input_tokens: int = 0)
8915 8919 146

#### answers *: Mapping[str, Answer]*
9392 9396 152

#### input_tokens *: int*
9600 9604 154

### outrage.smartsearch.Kind
9684 9688 156

### outrage.smartsearch.Level
10071 10075 165

### *class* outrage.smartsearch.LevelCounts(asked: int = 0, yes: int = 0, no: int = 0, missing: int = 0, unjudged: int = 0)
10251 10255 170

#### asked *: int*
10785 10789 176

#### yes *: int*
10895 10899 180

#### no *: int*
10970 10974 182

#### missing *: int*
11044 11048 184

#### unjudged *: int*
11215 11219 189

### *class* outrage.smartsearch.LevelTuning(name: str, kind: Literal['value', 'contents', 'body'], meta: str | None, shape: Literal['questions', 'state'], weight: float, supporting: bool, question: Question)
11295 11299 191

#### name *: str*
12082 12086 197

#### kind *: Literal['value', 'contents', 'body']*
12225 12229 201

#### meta *: str | None*
12341 12345 203

#### shape *: Literal['questions', 'state']*
12542 12546 207

#### weight *: float*
12652 12656 209

#### supporting *: bool*
12734 12738 211

#### question *: Question*
12818 12822 213

### *class* outrage.smartsearch.Match(key: str, probability: float, decision: Literal['yes', 'unsure'], decided_at: str | None, evidence: tuple[Evidence, ...])
12935 12939 217

#### key *: str*
13586 13590 223

#### probability *: float*
13660 13664 225

#### decision *: Literal['yes', 'unsure']*
13747 13751 227

#### decided_at *: str | None*
13855 13859 229

#### evidence *: tuple[Evidence, ...]*
14103 14107 234

### *class* outrage.smartsearch.Question(kind: ~typing.Literal['noul', 'score'], text: str, criteria: tuple[str, ...] = (), instructions: ~collections.abc.Mapping[str, str] = <factory>)
14234 14238 236

#### kind *: Literal['noul', 'score']*
14944 14948 248

#### text *: str*
15160 15164 253

#### criteria *: tuple[str, ...]*
15235 15239 255

#### instructions *: Mapping[str, str]*
15455 15459 259

### *class* outrage.smartsearch.Requests(limit: int, batch_size: int, value_chars: int, chunk_chars: int, max_chunks: int, min_chunk_chars: int)
15690 15694 261

#### limit *: int*
16355 16359 267

#### batch_size *: int*
16432 16436 269

#### value_chars *: int*
16514 16518 271

#### chunk_chars *: int*
16597 16601 273

#### max_chunks *: int*
16680 16684 275

#### min_chunk_chars *: int*
16762 16766 277

### *class* outrage.smartsearch.Scoring(weights: Mapping[str, float], supporting: frozenset[str], yes: float, no: float, clamp: float)
16849 16853 279

#### weights *: Mapping[str, float]*
18544 18548 300

#### supporting *: frozenset[str]*
18832 18836 304

#### yes *: float*
19194 19198 310

#### no *: float*
19343 19347 314

#### clamp *: float*
19465 19469 318

#### combine(evidence: Sequence[Evidence]) → float
19678 19682 323

#### decide(probability: float) → Literal['yes', 'no', 'unsure']
19974 19980 327

### outrage.smartsearch.Shape
20204 20212 331

### *class* outrage.smartsearch.SmartSearchResult(key: str | None, query: str, matches: tuple[Match, ...], unjudged: tuple[Unjudged, ...], levels: Mapping[str, LevelCounts], documents: int, total: int, next_cursor: str | None, unavailable: tuple[str, ...], input_tokens: int)
20763 20771 344

#### key *: str | None*
22244 22252 354

#### query *: str*
22383 22391 356

#### matches *: tuple[Match, ...]*
22459 22467 358

#### unjudged *: tuple[Unjudged, ...]*
22626 22634 362

#### levels *: Mapping[str, LevelCounts]*
22757 22765 364

#### documents *: int*
22974 22982 366

#### total *: int*
23081 23089 370

#### next_cursor *: str | None*
23191 23199 374

#### unavailable *: tuple[str, ...]*
23338 23346 376

#### input_tokens *: int*
23532 23540 380

### *exception* outrage.smartsearch.StateTooLarge(code: str, \*\*details: Any)
23616 23624 382

### *class* outrage.smartsearch.Tuning(levels: tuple[LevelTuning, ...], scoring: Scoring, requests: Requests, source: str)
23942 23950 388

#### levels *: tuple[LevelTuning, ...]*
24679 24687 398

#### scoring *: Scoring*
24833 24841 402

#### requests *: Requests*
24891 24899 404

#### source *: str*
24952 24960 406

#### *property* names *: tuple[str, ...]*
25077 25085 410

#### level(name: str) → LevelTuning
25270 25278 414

#### *classmethod* read(data: object, source: str) → tuple[Tuning | None, list[Refusal]]
25519 25529 418

#### *classmethod* read_file(path: Path | None = None) → tuple[Tuning | None, list[Refusal]]
26282 26294 427

#### *classmethod* load(path: Path | None = None) → Tuning
26828 26842 431

### *class* outrage.smartsearch.Unjudged(key: str, level: str, code: str, details: Mapping[str, object], evidence: tuple[Evidence, ...])
27137 27153 435

#### key *: str*
27860 27876 441

#### level *: str*
27934 27950 443

#### code *: str*
28010 28026 445

#### details *: Mapping[str, object]*
28179 28195 449

#### evidence *: tuple[Evidence, ...]*
28416 28432 451

### outrage.smartsearch.packaged_tuning() → tuple[Tuning | None, tuple[Refusal, ...]]
28590 28606 455

### outrage.smartsearch.refusals(query: str, levels: Sequence[str] | None = None, \*, tuning: Tuning | None = None) → list[Refusal]
29121 29139 462

### outrage.smartsearch.smart_search(store: Store, key: str | None, query: str, judge: Judge, \*, tuning: Tuning | None = None, depth: int | None = None, limit: int | None = None, after: str | None = None, levels: Sequence[str] | None = None) → SmartSearchResult
29894 29914 469
