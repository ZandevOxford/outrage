# outrage.systemone
0 0 1

### outrage.systemone.DEFAULT_MODEL *= 'jev-latest'*
1067 1067 21

### outrage.systemone.DEFAULT_URL *= 'https://api.typesafe.ai/v1/systemone'*
1171 1171 25

### outrage.systemone.DETAIL_CHARS *= 300*
1289 1289 29

### outrage.systemone.KEY_VARIABLE *= 'TYPESAFE_API_KEY'*
1507 1507 35

### *class* outrage.systemone.RetryPolicy(max_retries: int = 2, backoff_initial: float = 0.5, backoff_max: float = 5.0, backoff_jitter: float = 0.25, statuses: frozenset[int] = <factory>, timeout: float = 30.0)
1613 1613 39

#### max_retries *: int*
2380 2380 45

#### backoff_initial *: float*
2463 2463 47

#### backoff_max *: float*
2554 2554 49

#### backoff_jitter *: float*
2641 2641 51

#### statuses *: frozenset[int]*
2731 2731 53

#### timeout *: float*
2884 2884 55

#### delay(attempt: int, retry_after: str | None = None) → float
2967 2967 57

### *class* outrage.systemone.Settings(url: str = 'https://api.typesafe.ai/v1/systemone', model: str = 'jev-latest', key: str | None = None)
3330 3332 61

#### url *: str*
3847 3849 67

#### model *: str*
3921 3923 69

#### key *: str | None*
3997 3999 71

#### *classmethod* from_environment(environ: Mapping[str, str] | None = None) → Self
4243 4245 76

#### *property* configured *: bool*
4689 4693 80

### *class* outrage.systemone.SystemOne(settings: Settings, \*, retry: RetryPolicy | None = None, transport: BaseTransport | None = None, sleep: Callable[[float], None] = time.sleep)
4998 5002 88

#### close() → None
5897 5901 98

#### judge(state: str, questions: Mapping[str, Question]) → Judgement
5976 5982 100
