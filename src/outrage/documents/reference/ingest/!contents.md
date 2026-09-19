# outrage.ingest
0 0 1

### *exception* outrage.ingest.IngestError(code: str, \*\*details: Any)
296 296 9

### *class* outrage.ingest.IngestResult(source: Path, key: str, title: str, characters: int, format: Literal['markdown'], title_key: str | None, dry_run: bool)
691 691 15

#### source *: Path*
1468 1468 21

#### key *: str*
1599 1599 25

#### title *: str*
1706 1706 29

#### characters *: int*
1818 1818 33

#### format *: Literal['markdown']*
1945 1945 37

#### title_key *: str | None*
2087 2087 41

#### dry_run *: bool*
2298 2298 45

### outrage.ingest.available() → bool
2443 2443 49

### outrage.ingest.ingest_document(store: Store, source: str | PathLike[str], key: str, \*, title: str | None = None, overwrite: bool = False, dry_run: bool = False) → IngestResult
3224 3226 64
