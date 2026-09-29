# outrage.maintenance
0 0 1

### outrage.maintenance.DATABASE_DAMAGED *= 'database-damaged'*
2138 2138 39

### outrage.maintenance.FILES_NOT_KEYS *= 'files-not-keys'*
2252 2252 43

### outrage.maintenance.FILES_NOT_TEXT *= 'files-not-text'*
2374 2374 47

### outrage.maintenance.FORMAT_OLDER *= 'format-older'*
2488 2488 51

### outrage.maintenance.FORMAT_TOO_NEW *= 'format-too-new'*
2651 2651 56

### outrage.maintenance.KEYS_DOUBLED *= 'keys-doubled'*
2790 2790 60

### outrage.maintenance.KEYS_TOO_DEEP *= 'keys-too-deep'*
2918 2918 64

### outrage.maintenance.LENGTH_CACHE_STALE *= 'length-cache-stale'*
3080 3080 68

### outrage.maintenance.METADATA_WITHOUT_DOCUMENT *= 'metadata-without-document'*
3220 3220 72

### outrage.maintenance.PROBLEM_CODES *= ('format-too-new', 'format-older', 'keys-too-deep', 'rows-under-wrong-key', 'metadata-without-document', 'database-damaged', 'length-cache-stale', 'wal-uncheckpointed', 'files-not-keys', 'keys-doubled', 'files-not-text', 'rows-out-of-order', 'read-only-to-this-build', 'triggers-missing')*
3369 3369 76

### outrage.maintenance.READ_ONLY_TO_THIS_BUILD *= 'read-only-to-this-build'*
3906 3906 82

### outrage.maintenance.ROWS_OUT_OF_ORDER *= 'rows-out-of-order'*
4167 4167 88

### outrage.maintenance.ROWS_UNDER_WRONG_KEY *= 'rows-under-wrong-key'*
4308 4308 92

### outrage.maintenance.TRIGGERS_MISSING *= 'triggers-missing'*
4455 4455 96

### outrage.maintenance.WAL_UNCHECKPOINTED *= 'wal-uncheckpointed'*
4740 4740 102

### *exception* outrage.maintenance.CheckError(code: str, \*\*details: Any)
4987 4987 108

### *class* outrage.maintenance.Problem(code: str, severity: str, summary: str, detail: str = '', repairable: bool = False)
5374 5374 114

#### code *: str*
7226 7226 143

#### severity *: str*
7301 7301 145

#### summary *: str*
7380 7380 147

#### detail *: str* *= ''*
7458 7458 149

#### repairable *: bool* *= False*
7542 7542 151

### *class* outrage.maintenance.Repaired(action: str, before: int, after: int, unit: str = 'bytes')
7636 7636 153

#### action *: str*
8478 8478 166

#### before *: int*
8555 8555 168

#### after *: int*
8633 8633 170

#### unit *: str* *= 'bytes'*
8710 8710 172

### *class* outrage.maintenance.Report(path: Path, backend: str = '', format_version: int = 0, documents: int = 0, metadata: int = 0, characters: int = 0, details: dict[str, str]=<factory>, problems: list[Problem] = <factory>)
8797 8797 174

#### path *: Path*
9594 9594 180

#### backend *: str* *= ''*
9677 9677 182

#### format_version *: int* *= 0*
9976 9976 188

#### documents *: int* *= 0*
10068 10068 190

#### metadata *: int* *= 0*
10155 10155 192

#### characters *: int* *= 0*
10241 10241 194

#### details *: dict[str, str]*
10329 10329 196

#### problems *: list[Problem]*
10936 10936 205

#### *property* sound *: bool*
11058 11058 207

#### *property* repairable *: list[Problem]*
11211 11211 211

### outrage.maintenance.check(store: FileStore) → Report
11708 11708 220

### outrage.maintenance.repair(store: FileStore) → list[Repaired]
12118 12120 229

### outrage.maintenance.require_store(directory: Path, filename: str | None = None) → Path
12704 12708 239
