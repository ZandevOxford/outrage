# outrage.ingest
0 0

### *exception* outrage.ingest.IngestError(code: str, \*\*details: Any)
296 296

### *class* outrage.ingest.IngestResult(source: Path, key: str, title: str, characters: int, format: Literal['markdown'], title_key: str | None, dry_run: bool)
691 691

#### source *: Path*
1468 1468

#### key *: str*
1599 1599

#### title *: str*
1706 1706

#### characters *: int*
1818 1818

#### format *: Literal['markdown']*
1945 1945

#### title_key *: str | None*
2087 2087

#### dry_run *: bool*
2298 2298

### outrage.ingest.available() → bool
2443 2443

### outrage.ingest.ingest_document(store: Store, source: str | PathLike[str], key: str, \*, title: str | None = None, overwrite: bool = False, dry_run: bool = False) → IngestResult
3224 3226
