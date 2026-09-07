# outrage.ingest
0 0

### *exception* outrage.ingest.IngestError(code: str, \*\*details: Any)
296 296

### *class* outrage.ingest.IngestResult(source: Path, key: str, title: str, characters: int, format: Literal['markdown'], title_key: str | None, dry_run: bool)
689 689

#### source *: Path*
1459 1459

#### key *: str*
1590 1590

#### title *: str*
1696 1696

#### characters *: int*
1807 1807

#### format *: Literal['markdown']*
1933 1933

#### title_key *: str | None*
2075 2075

#### dry_run *: bool*
2284 2284

### outrage.ingest.available() → bool
2428 2428

### outrage.ingest.ingest_document(store: Store, source: str | PathLike[str], key: str, \*, title: str | None = None, overwrite: bool = False, dry_run: bool = False) → IngestResult
3208 3210
