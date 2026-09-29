# outrage.systemone
0 0 1

### outrage.systemone.BASE_URL_VARIABLE *= 'TYPESAFE_BASE_URL'*
1411 1411 25

### outrage.systemone.CONFIG_NAMES *= ('key', 'base_url', 'model')*
1552 1552 29

### outrage.systemone.CONFIG_TABLE *= 'smart_search'*
1771 1771 34

### outrage.systemone.DEFAULT_BASE_URL *= 'https://api.typesafe.ai'*
1878 1878 38

### outrage.systemone.DEFAULT_MODEL *= 'jev-latest'*
1984 1984 42

### outrage.systemone.DETAIL_CHARS *= 300*
2088 2088 46

### outrage.systemone.ENDPOINT_PATH *= '/v1/systemone'*
2306 2306 52

### outrage.systemone.KEY_VARIABLE *= 'TYPESAFE_API_KEY'*
2412 2412 56

### outrage.systemone.MODEL_VARIABLE *= 'TYPESAFE_DEFAULT_MODEL'*
2546 2546 60

### *class* outrage.systemone.RetryPolicy(max_retries: int = 2, backoff_initial: float = 0.5, backoff_max: float = 5.0, backoff_jitter: float = 0.25, statuses: frozenset[int] = <factory>, timeout: float = 30.0)
2685 2685 64

#### max_retries *: int*
3452 3452 70

#### backoff_initial *: float*
3535 3535 72

#### backoff_max *: float*
3626 3626 74

#### backoff_jitter *: float*
3713 3713 76

#### statuses *: frozenset[int]*
3803 3803 78

#### timeout *: float*
3956 3956 80

#### delay(attempt: int, retry_after: str | None = None) → float
4039 4039 82

### *class* outrage.systemone.Settings(base_url: str = 'https://api.typesafe.ai', model: str = 'jev-latest', key: str | None = None, key_source: str | None = None)
4402 4404 86

#### base_url *: str*
5056 5058 92

#### model *: str*
5237 5239 96

#### key *: str | None*
5313 5315 98

#### key_source *: str | None*
5642 5644 104

#### *property* url *: str*
5901 5903 109

#### *classmethod* read(environ: Mapping[str, str] | None = None, path: Path | None = None) → tuple[Self, list[Refusal]]
6014 6016 113

#### *classmethod* load(environ: Mapping[str, str] | None = None, path: Path | None = None) → Self
7280 7284 126

#### *property* configured *: bool*
7901 7907 130

### *class* outrage.systemone.SystemOne(settings: Settings, \*, retry: RetryPolicy | None = None, transport: BaseTransport | None = None, sleep: Callable[[float], None] = time.sleep)
8296 8302 139

#### close() → None
9195 9201 149

#### judge(state: str, questions: Mapping[str, Question]) → Judgement
9274 9282 151
