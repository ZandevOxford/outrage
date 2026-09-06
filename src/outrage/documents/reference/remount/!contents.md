# outrage.remount
0 0

### outrage.remount.SHIPPED *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[...], [Store](store.md#outrage.store.Store)]]* *= mappingproxy({'outrage': <function open_documents>})*
2346 2346

### *class* outrage.remount.Changed(table: [MountedStore](mounts.md#outrage.mounts.MountedStore), notes: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Note](notes.md#outrage.notes.Note), ...] = ())
3220 3220

#### table *: [MountedStore](mounts.md#outrage.mounts.MountedStore)*
3862 3862

#### notes *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Note](notes.md#outrage.notes.Note), ...]*
3932 3932

### *class* outrage.remount.Live(table: [MountedStore](mounts.md#outrage.mounts.MountedStore), \*, directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None)
4053 4053

#### *property* table *: [MountedStore](mounts.md#outrage.mounts.MountedStore)*
5661 5661

#### *property* directory *: [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*
5805 5805

#### mount(key: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, file: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, type: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, extensions: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, read_only: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [Changed](#outrage.remount.Changed)
6020 6020

#### unmount(key: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [Changed](#outrage.remount.Changed)
8105 8107

#### close() → [None](https://docs.python.org/3/library/constants.html#None)
8544 8548

### outrage.remount.notes_for_mount(after: [MountedStore](mounts.md#outrage.mounts.MountedStore), prefix: [str](https://docs.python.org/3/library/stdtypes.html#str), \*, replaced: [bool](https://docs.python.org/3/library/functions.html#bool), shipped: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]
8663 8669

### outrage.remount.notes_for_unmount(after: [MountedStore](mounts.md#outrage.mounts.MountedStore), prefix: [str](https://docs.python.org/3/library/stdtypes.html#str)) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Note](notes.md#outrage.notes.Note)]
10114 10122
