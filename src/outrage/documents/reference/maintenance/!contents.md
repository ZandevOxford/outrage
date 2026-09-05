# outrage.maintenance
0 0

### *exception* outrage.maintenance.CheckError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
1984 1984

### *class* outrage.maintenance.Problem(severity: [str](https://docs.python.org/3/library/stdtypes.html#str), summary: [str](https://docs.python.org/3/library/stdtypes.html#str), detail: [str](https://docs.python.org/3/library/stdtypes.html#str) = '', repairable: [bool](https://docs.python.org/3/library/functions.html#bool) = False)
2369 2369

#### severity *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
3460 3460

#### summary *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
3538 3538

#### detail *: [str](https://docs.python.org/3/library/stdtypes.html#str)* *= ''*
3615 3615

#### repairable *: [bool](https://docs.python.org/3/library/functions.html#bool)* *= False*
3698 3698

### *class* outrage.maintenance.Repaired(action: [str](https://docs.python.org/3/library/stdtypes.html#str), before: [int](https://docs.python.org/3/library/functions.html#int), after: [int](https://docs.python.org/3/library/functions.html#int), unit: [str](https://docs.python.org/3/library/stdtypes.html#str) = 'bytes')
3791 3791

#### action *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
4628 4628

#### before *: [int](https://docs.python.org/3/library/functions.html#int)*
4704 4704

#### after *: [int](https://docs.python.org/3/library/functions.html#int)*
4781 4781

#### unit *: [str](https://docs.python.org/3/library/stdtypes.html#str)* *= 'bytes'*
4857 4857

### *class* outrage.maintenance.Report(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), backend: [str](https://docs.python.org/3/library/stdtypes.html#str) = '', format_version: [int](https://docs.python.org/3/library/functions.html#int) = 0, documents: [int](https://docs.python.org/3/library/functions.html#int) = 0, metadata: [int](https://docs.python.org/3/library/functions.html#int) = 0, characters: [int](https://docs.python.org/3/library/functions.html#int) = 0, details: dict[str, str]=<factory>, problems: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Problem](#outrage.maintenance.Problem)] = <factory>)
4943 4943

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
5733 5733

#### backend *: [str](https://docs.python.org/3/library/stdtypes.html#str)* *= ''*
5816 5816

#### format_version *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
6114 6114

#### documents *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
6205 6205

#### metadata *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
6291 6291

#### characters *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
6376 6376

#### details *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)]*
6463 6463

#### problems *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Problem](#outrage.maintenance.Problem)]*
7067 7067

#### *property* sound *: [bool](https://docs.python.org/3/library/functions.html#bool)*
7188 7188

#### *property* repairable *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Problem](#outrage.maintenance.Problem)]*
7340 7340

### outrage.maintenance.check(store: [FileStore](store.md#outrage.store.FileStore)) → [Report](#outrage.maintenance.Report)
7836 7836

### outrage.maintenance.repair(store: [FileStore](store.md#outrage.store.FileStore)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Repaired](#outrage.maintenance.Repaired)]
8246 8248

### outrage.maintenance.require_store(directory: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), filename: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
8831 8835
