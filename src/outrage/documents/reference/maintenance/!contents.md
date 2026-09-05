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

### *class* outrage.maintenance.Repaired(action: [str](https://docs.python.org/3/library/stdtypes.html#str), before: [int](https://docs.python.org/3/library/functions.html#int), after: [int](https://docs.python.org/3/library/functions.html#int))
3791 3791

#### action *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
4175 4175

#### before *: [int](https://docs.python.org/3/library/functions.html#int)*
4251 4251

#### after *: [int](https://docs.python.org/3/library/functions.html#int)*
4328 4328

### *class* outrage.maintenance.Report(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), backend: [str](https://docs.python.org/3/library/stdtypes.html#str) = '', format_version: [int](https://docs.python.org/3/library/functions.html#int) = 0, documents: [int](https://docs.python.org/3/library/functions.html#int) = 0, metadata: [int](https://docs.python.org/3/library/functions.html#int) = 0, characters: [int](https://docs.python.org/3/library/functions.html#int) = 0, details: dict[str, str]=<factory>, problems: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Problem](#outrage.maintenance.Problem)] = <factory>)
4404 4404

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
5194 5194

#### backend *: [str](https://docs.python.org/3/library/stdtypes.html#str)* *= ''*
5277 5277

#### format_version *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
5575 5575

#### documents *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
5666 5666

#### metadata *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
5752 5752

#### characters *: [int](https://docs.python.org/3/library/functions.html#int)* *= 0*
5837 5837

#### details *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)]*
5924 5924

#### problems *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Problem](#outrage.maintenance.Problem)]*
6528 6528

#### *property* sound *: [bool](https://docs.python.org/3/library/functions.html#bool)*
6649 6649

#### *property* repairable *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Problem](#outrage.maintenance.Problem)]*
6801 6801

### outrage.maintenance.check(store: [FileStore](store.md#outrage.store.FileStore)) → [Report](#outrage.maintenance.Report)
7297 7297

### outrage.maintenance.repair(store: [FileStore](store.md#outrage.store.FileStore)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Repaired](#outrage.maintenance.Repaired)]
7707 7709

### outrage.maintenance.require_store(directory: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), filename: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
8292 8296
