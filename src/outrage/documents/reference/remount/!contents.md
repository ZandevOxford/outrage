# outrage.remount
0 0

### outrage.remount.SHIPPED *: Mapping[str, Callable[[...], Store]]* *= mappingproxy({'outrage': <function open_documents>})*
2346 2346

### *class* outrage.remount.Changed(table: MountedStore, notes: tuple[Note, ...] = ())
3220 3220

#### table *: MountedStore*
3862 3862

#### notes *: tuple[Note, ...]*
3932 3932

### *class* outrage.remount.Live(table: MountedStore, \*, directory: str | PathLike[str] | None = None, log: EventLog | None = None, versioning: bool = True)
4053 4053

#### *property* table *: MountedStore*
5916 5916

#### *property* directory *: PathLike[str]*
6060 6060

#### mount(key: str, \*, file: str | PathLike[str] | None = None, type: str | None = None, extensions: str | None = None, read_only: bool = False) → Changed
6275 6275

#### unmount(key: str) → Changed
8360 8362

#### close() → None
8799 8803

### outrage.remount.notes_for_mount(after: MountedStore, prefix: str, \*, replaced: bool, shipped: bool = False, created: str | None = None) → list[Note]
8918 8924

### outrage.remount.notes_for_unmount(after: MountedStore, prefix: str, \*, started: bool = True) → list[Note]
10767 10775
