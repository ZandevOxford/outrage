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
4625 4625

#### code *: str*
6471 6471

#### severity *: str*
6545 6545

#### summary *: str*
6623 6623

#### detail *: str* *= ''*
6700 6700

#### repairable *: bool* *= False*
6783 6783

### *class* outrage.maintenance.Repaired(action: str, before: int, after: int, unit: str = 'bytes')
6876 6876

#### action *: str*
7713 7713

#### before *: int*
7789 7789

#### after *: int*
7866 7866

#### unit *: str* *= 'bytes'*
7942 7942

### *class* outrage.maintenance.Report(path: Path, backend: str = '', format_version: int = 0, documents: int = 0, metadata: int = 0, characters: int = 0, details: dict[str, str]=<factory>, problems: list[Problem] = <factory>)
8028 8028

#### path *: Path*
8818 8818

#### backend *: str* *= ''*
8901 8901

#### format_version *: int* *= 0*
9199 9199

#### documents *: int* *= 0*
9290 9290

#### metadata *: int* *= 0*
9376 9376

#### characters *: int* *= 0*
9461 9461

#### details *: dict[str, str]*
9548 9548

#### problems *: list[Problem]*
10152 10152

#### *property* sound *: bool*
10273 10273

#### *property* repairable *: list[Problem]*
10425 10425

### outrage.maintenance.check(store: FileStore) → Report
10921 10921

### outrage.maintenance.repair(store: FileStore) → list[Repaired]
11331 11333

### outrage.maintenance.require_store(directory: Path, filename: str | None = None) → Path
11916 11920
