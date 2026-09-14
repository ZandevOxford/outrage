# outrage.maintenance
0 0

### outrage.maintenance.DATABASE_DAMAGED *= 'database-damaged'*
1984 1984

### outrage.maintenance.FILES_NOT_KEYS *= 'files-not-keys'*
2098 2098

### outrage.maintenance.FILES_NOT_TEXT *= 'files-not-text'*
2220 2220

### outrage.maintenance.FORMAT_OLDER *= 'format-older'*
2334 2334

### outrage.maintenance.FORMAT_TOO_NEW *= 'format-too-new'*
2497 2497

### outrage.maintenance.KEYS_DOUBLED *= 'keys-doubled'*
2636 2636

### outrage.maintenance.KEYS_TOO_DEEP *= 'keys-too-deep'*
2764 2764

### outrage.maintenance.LENGTH_CACHE_STALE *= 'length-cache-stale'*
2926 2926

### outrage.maintenance.METADATA_WITHOUT_DOCUMENT *= 'metadata-without-document'*
3066 3066

### outrage.maintenance.PROBLEM_CODES *= ('format-too-new', 'format-older', 'keys-too-deep', 'rows-under-wrong-key', 'metadata-without-document', 'database-damaged', 'length-cache-stale', 'wal-uncheckpointed', 'files-not-keys', 'keys-doubled', 'files-not-text', 'rows-out-of-order')*
3215 3215

### outrage.maintenance.ROWS_OUT_OF_ORDER *= 'rows-out-of-order'*
3705 3705

### outrage.maintenance.ROWS_UNDER_WRONG_KEY *= 'rows-under-wrong-key'*
3846 3846

### outrage.maintenance.WAL_UNCHECKPOINTED *= 'wal-uncheckpointed'*
3993 3993

### *exception* outrage.maintenance.CheckError(code: str, \*\*details: Any)
4240 4240

### *class* outrage.maintenance.Problem(code: str, severity: str, summary: str, detail: str = '', repairable: bool = False)
4627 4627

#### code *: str*
6479 6479

#### severity *: str*
6554 6554

#### summary *: str*
6633 6633

#### detail *: str* *= ''*
6711 6711

#### repairable *: bool* *= False*
6795 6795

### *class* outrage.maintenance.Repaired(action: str, before: int, after: int, unit: str = 'bytes')
6889 6889

#### action *: str*
7731 7731

#### before *: int*
7808 7808

#### after *: int*
7886 7886

#### unit *: str* *= 'bytes'*
7963 7963

### *class* outrage.maintenance.Report(path: Path, backend: str = '', format_version: int = 0, documents: int = 0, metadata: int = 0, characters: int = 0, details: dict[str, str]=<factory>, problems: list[Problem] = <factory>)
8050 8050

#### path *: Path*
8847 8847

#### backend *: str* *= ''*
8930 8930

#### format_version *: int* *= 0*
9229 9229

#### documents *: int* *= 0*
9321 9321

#### metadata *: int* *= 0*
9408 9408

#### characters *: int* *= 0*
9494 9494

#### details *: dict[str, str]*
9582 9582

#### problems *: list[Problem]*
10189 10189

#### *property* sound *: bool*
10311 10311

#### *property* repairable *: list[Problem]*
10464 10464

### outrage.maintenance.check(store: FileStore) → Report
10961 10961

### outrage.maintenance.repair(store: FileStore) → list[Repaired]
11371 11373

### outrage.maintenance.require_store(directory: Path, filename: str | None = None) → Path
11957 11961
