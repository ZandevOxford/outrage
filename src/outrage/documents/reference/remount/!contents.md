# outrage.remount
0 0

### outrage.remount.SHIPPED *: Mapping[str, Callable[[...], Store]]* *= mappingproxy({'outrage': <function open_documents>})*
2346 2346

### *class* outrage.remount.Changed(table: MountedStore, notes: tuple[Note, ...] = ())
3221 3221

#### table *: MountedStore*
3865 3865

#### notes *: tuple[Note, ...]*
3935 3935

### *class* outrage.remount.Live(table: MountedStore, \*, directory: str | PathLike[str] | None = None, log: EventLog | None = None, versioning: bool = True)
4057 4057

#### *property* table *: MountedStore*
5926 5926

#### *property* directory *: PathLike[str]*
6070 6070

#### mount(key: str, \*, file: str | PathLike[str] | None = None, type: str | None = None, extensions: str | None = None, read_only: bool = False) → Changed
6286 6286

#### unmount(key: str) → Changed
8380 8382

#### close() → None
8820 8824

### outrage.remount.notes_for_mount(after: MountedStore, prefix: str, \*, replaced: bool, shipped: bool = False, created: str | None = None) → list[Note]
8940 8946

### outrage.remount.notes_for_unmount(after: MountedStore, prefix: str, \*, started: bool = True) → list[Note]
10795 10803
