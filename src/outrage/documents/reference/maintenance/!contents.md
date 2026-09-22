# outrage.maintenance
0 0 1

### outrage.maintenance.DATABASE_DAMAGED *= 'database-damaged'*
1984 1984 37

### outrage.maintenance.FILES_NOT_KEYS *= 'files-not-keys'*
2098 2098 41

### outrage.maintenance.FILES_NOT_TEXT *= 'files-not-text'*
2220 2220 45

### outrage.maintenance.FORMAT_OLDER *= 'format-older'*
2334 2334 49

### outrage.maintenance.FORMAT_TOO_NEW *= 'format-too-new'*
2497 2497 54

### outrage.maintenance.KEYS_DOUBLED *= 'keys-doubled'*
2636 2636 58

### outrage.maintenance.KEYS_TOO_DEEP *= 'keys-too-deep'*
2764 2764 62

### outrage.maintenance.LENGTH_CACHE_STALE *= 'length-cache-stale'*
2926 2926 66

### outrage.maintenance.METADATA_WITHOUT_DOCUMENT *= 'metadata-without-document'*
3066 3066 70

### outrage.maintenance.PROBLEM_CODES *= ('format-too-new', 'format-older', 'keys-too-deep', 'rows-under-wrong-key', 'metadata-without-document', 'database-damaged', 'length-cache-stale', 'wal-uncheckpointed', 'files-not-keys', 'keys-doubled', 'files-not-text', 'rows-out-of-order', 'read-only-to-this-build', 'triggers-missing')*
3215 3215 74

### outrage.maintenance.READ_ONLY_TO_THIS_BUILD *= 'read-only-to-this-build'*
3752 3752 80

### outrage.maintenance.ROWS_OUT_OF_ORDER *= 'rows-out-of-order'*
4013 4013 86

### outrage.maintenance.ROWS_UNDER_WRONG_KEY *= 'rows-under-wrong-key'*
4154 4154 90

### outrage.maintenance.TRIGGERS_MISSING *= 'triggers-missing'*
4301 4301 94

### outrage.maintenance.WAL_UNCHECKPOINTED *= 'wal-uncheckpointed'*
4586 4586 100

### *exception* outrage.maintenance.CheckError(code: str, \*\*details: Any)
4833 4833 106

### *class* outrage.maintenance.Problem(code: str, severity: str, summary: str, detail: str = '', repairable: bool = False)
5220 5220 112

#### code *: str*
7072 7072 141

#### severity *: str*
7147 7147 143

#### summary *: str*
7226 7226 145

#### detail *: str* *= ''*
7304 7304 147

#### repairable *: bool* *= False*
7388 7388 149

### *class* outrage.maintenance.Repaired(action: str, before: int, after: int, unit: str = 'bytes')
7482 7482 151

#### action *: str*
8324 8324 164

#### before *: int*
8401 8401 166

#### after *: int*
8479 8479 168

#### unit *: str* *= 'bytes'*
8556 8556 170

### *class* outrage.maintenance.Report(path: Path, backend: str = '', format_version: int = 0, documents: int = 0, metadata: int = 0, characters: int = 0, details: dict[str, str]=<factory>, problems: list[Problem] = <factory>)
8643 8643 172

#### path *: Path*
9440 9440 178

#### backend *: str* *= ''*
9523 9523 180

#### format_version *: int* *= 0*
9822 9822 186

#### documents *: int* *= 0*
9914 9914 188

#### metadata *: int* *= 0*
10001 10001 190

#### characters *: int* *= 0*
10087 10087 192

#### details *: dict[str, str]*
10175 10175 194

#### problems *: list[Problem]*
10782 10782 203

#### *property* sound *: bool*
10904 10904 205

#### *property* repairable *: list[Problem]*
11057 11057 209

### outrage.maintenance.check(store: FileStore) → Report
11554 11554 218

### outrage.maintenance.repair(store: FileStore) → list[Repaired]
11964 11966 227

### outrage.maintenance.require_store(directory: Path, filename: str | None = None) → Path
12550 12554 237
