# outrage.systemone
0 0 1

### outrage.systemone.BASE_URL_VARIABLE *= 'TYPESAFE_BASE_URL'*
1589 1589 28

### outrage.systemone.CONFIG_NAMES *= ('key', 'base_url', 'model')*
1730 1730 32

### outrage.systemone.CONFIG_TABLE *= 'smart_search'*
1949 1949 37

### outrage.systemone.DEFAULT_BASE_URL *= 'https://api.typesafe.ai'*
2056 2056 41

### outrage.systemone.DEFAULT_MODEL *= 'jev-latest'*
2162 2162 45

### outrage.systemone.DETAIL_CHARS *= 300*
2266 2266 49

### outrage.systemone.ENDPOINT_PATH *= '/v1/systemone'*
2484 2484 55

### outrage.systemone.KEY_VARIABLE *= 'TYPESAFE_API_KEY'*
2590 2590 59

### outrage.systemone.MODEL_VARIABLE *= 'TYPESAFE_DEFAULT_MODEL'*
2724 2724 63

### *class* outrage.systemone.RetryPolicy(max_retries: int = 2, backoff_initial: float = 0.5, backoff_max: float = 5.0, backoff_jitter: float = 0.25, statuses: frozenset[int] = <factory>, timeout: float = 30.0)
2863 2863 67

#### max_retries *: int*
3630 3630 73

#### backoff_initial *: float*
3713 3713 75

#### backoff_max *: float*
3804 3804 77

#### backoff_jitter *: float*
3891 3891 79

#### statuses *: frozenset[int]*
3981 3981 81

#### timeout *: float*
4134 4134 83

#### delay(attempt: int, retry_after: str | None = None) → float
4217 4217 85

### *class* outrage.systemone.Settings(base_url: str = 'https://api.typesafe.ai', model: str = 'jev-latest', key: str | None = None, key_source: str | None = None)
4580 4582 89

#### base_url *: str*
5234 5236 95

#### model *: str*
5415 5417 99

#### key *: str | None*
5491 5493 101

#### key_source *: str | None*
5820 5822 107

#### *property* url *: str*
6079 6081 112

#### *classmethod* read(environ: Mapping[str, str] | None = None, path: Path | None = None) → tuple[Self, list[Refusal]]
6192 6194 116

#### *classmethod* load(environ: Mapping[str, str] | None = None, path: Path | None = None) → Self
7458 7462 129

#### *property* configured *: bool*
8079 8085 133

### *class* outrage.systemone.SystemOne(settings: Settings, \*, retry: RetryPolicy | None = None, transport: BaseTransport | None = None, sleep: Callable[[float], None] = time.sleep)
8474 8480 142

#### close() → None
9373 9379 152

#### judge(state: Mapping[str, str], questions: Mapping[str, Question]) → Judgement
9452 9460 154
