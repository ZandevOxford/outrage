# outrage.remount
0 0 1

### outrage.remount.BUILTINS *: Mapping[str, Builtin]* *= mappingproxy({'outrage': Builtin(opener=<function open_documents>, lent=True), 'home': Builtin(opener=<function open_store>, lent=False)})*
2504 2504 44

### *class* outrage.remount.Builtin(opener: Callable[[...], Store], lent: bool)
2949 2949 48

#### opener *: Callable[[...], Store]*
3348 3348 54

#### lent *: bool*
3503 3503 56

### *class* outrage.remount.Changed(table: MountedStore, notes: tuple[Note, ...] = ())
3581 3581 58

#### table *: MountedStore*
4225 4225 69

#### notes *: tuple[Note, ...]*
4295 4295 71

### *class* outrage.remount.Live(table: MountedStore, \*, directory: str | PathLike[str] | None = None, log: EventLog | None = None, versioning: bool = True)
4417 4417 73

#### *property* table *: MountedStore*
6286 6286 97

#### *property* directory *: PathLike[str]*
6430 6430 101

#### mount(key: str, \*, file: str | PathLike[str] | None = None, type: str | None = None, extensions: str | None = None, service: str | None = None, read_only: bool = False) → Changed
6646 6646 105

#### unmount(key: str) → Changed
8915 8917 132

#### close() → None
9355 9359 141

### outrage.remount.notes_for_mount(after: MountedStore, prefix: str, \*, replaced: bool, reopened: bool = False, builtin: bool = False, created: str | None = None) → list[Note]
9475 9481 145

### outrage.remount.notes_for_unmount(after: MountedStore, prefix: str, \*, started: bool = True) → list[Note]
11907 11915 180
