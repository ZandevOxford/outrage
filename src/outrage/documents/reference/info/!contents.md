# outrage.info
0 0

### *class* outrage.info.Info(version: [str](https://docs.python.org/3/library/stdtypes.html#str), python: [str](https://docs.python.org/3/library/stdtypes.html#str), prefix: [str](https://docs.python.org/3/library/stdtypes.html#str), command: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...] = (), directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, mount_config: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...] = (), log: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, log_content: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, mounts: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[MountInfo](#outrage.info.MountInfo), ...] = ())
1182 1182

#### version *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
2377 2377

#### python *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
2454 2454

#### prefix *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
2857 2857

#### command *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...]*
3049 3049

#### directory *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
3382 3382

#### mount_config *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), ...]*
3723 3723

#### log *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
3940 3940

#### log_content *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
4148 4148

#### mounts *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[MountInfo](#outrage.info.MountInfo), ...]*
4363 4363

### *class* outrage.info.MountInfo(mount: [str](https://docs.python.org/3/library/stdtypes.html#str), path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), kind: [str](https://docs.python.org/3/library/stdtypes.html#str), read_only: [bool](https://docs.python.org/3/library/functions.html#bool))
4541 4541

#### mount *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
5024 5024

#### path *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
5163 5163

#### kind *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
5473 5473

#### read_only *: [bool](https://docs.python.org/3/library/functions.html#bool)*
5727 5727

### outrage.info.describe(opened: [Store](store.md#outrage.store.Store), \*, directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, mount_config: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Info](#outrage.info.Info)
5859 5859

### outrage.info.mount_infos(opened: [Store](store.md#outrage.store.Store)) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[MountInfo](#outrage.info.MountInfo), ...]
7232 7234
