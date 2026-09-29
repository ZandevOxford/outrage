# outrage.ingest
0 0 1

### *exception* outrage.ingest.IngestError(code: str, \*\*details: Any)
433 433 11

### *class* outrage.ingest.IngestResult(source: Path, key: str, title: str, characters: int, format: Literal['markdown'], title_key: str | None, dry_run: bool)
828 828 17

#### source *: Path*
1605 1605 23

#### key *: str*
1736 1736 27

#### title *: str*
1843 1843 31

#### characters *: int*
1955 1955 35

#### format *: Literal['markdown']*
2082 2082 39

#### title_key *: str | None*
2224 2224 43

#### dry_run *: bool*
2435 2435 47

### outrage.ingest.available() → bool
2580 2580 51

### outrage.ingest.ingest_document(store: Store, source: str | PathLike[str], key: str, \*, title: str | None = None, overwrite: bool = False, dry_run: bool = False) → IngestResult
3361 3363 66
