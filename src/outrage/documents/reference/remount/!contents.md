# outrage.remount
0 0 1

### outrage.remount.BUILTINS *: Mapping[str, Builtin]* *= mappingproxy({'outrage': Builtin(opener=<function open_documents>, lent=True), 'home': Builtin(opener=<function open_store>, lent=False)})*
2346 2346 42

### *class* outrage.remount.Builtin(opener: Callable[[...], Store], lent: bool)
2791 2791 46

#### opener *: Callable[[...], Store]*
3190 3190 52

#### lent *: bool*
3345 3345 54

### *class* outrage.remount.Changed(table: MountedStore, notes: tuple[Note, ...] = ())
3423 3423 56

#### table *: MountedStore*
4067 4067 67

#### notes *: tuple[Note, ...]*
4137 4137 69

### *class* outrage.remount.Live(table: MountedStore, \*, directory: str | PathLike[str] | None = None, log: EventLog | None = None, versioning: bool = True)
4259 4259 71

#### *property* table *: MountedStore*
6128 6128 95

#### *property* directory *: PathLike[str]*
6272 6272 99

#### mount(key: str, \*, file: str | PathLike[str] | None = None, type: str | None = None, extensions: str | None = None, read_only: bool = False) → Changed
6488 6488 103

#### unmount(key: str) → Changed
8360 8362 125

#### close() → None
8800 8804 134

### outrage.remount.notes_for_mount(after: MountedStore, prefix: str, \*, replaced: bool, builtin: bool = False, created: str | None = None) → list[Note]
8920 8926 138

### outrage.remount.notes_for_unmount(after: MountedStore, prefix: str, \*, started: bool = True) → list[Note]
10773 10781 164
