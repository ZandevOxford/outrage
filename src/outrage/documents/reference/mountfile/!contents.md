# outrage.mountfile
0 0

### outrage.mountfile.BUILTIN_SOURCE *= 'built in'*
2687 2687

### outrage.mountfile.CONFIG_FLAG *= '--mount-config'*
2797 2797

### outrage.mountfile.DEFAULT_NAME *= 'mounts.toml'*
3121 3121

### outrage.mountfile.DIR_FLAG *= '--dir'*
3390 3390

### outrage.mountfile.DOCS_FLAG *= '--mount-docs'*
3570 3570

### outrage.mountfile.DOCS_MOUNT *= 'outrage'*
4272 4272

### outrage.mountfile.FIELDS *= ('root-mount', 'mount', 'mount-ro')*
4571 4571

### outrage.mountfile.MOUNT_FIELD *= 'mount'*
4854 4854

### outrage.mountfile.PATH_FIELD *= 'path'*
4970 4970

### outrage.mountfile.MOUNT_FLAG *= '--mount'*
5310 5310

### outrage.mountfile.NO_CONFIG_FLAG *= '--no-mount-config'*
5395 5395

### outrage.mountfile.READ_ONLY_FIELD *= 'mount-ro'*
5885 5885

### outrage.mountfile.READ_ONLY_FLAG *= '--mount-ro'*
5985 5985

### outrage.mountfile.ROOT_FIELD *= 'root-mount'*
6118 6118

### outrage.mountfile.ROOT_FLAG *= '--root-mount'*
6422 6422

### outrage.mountfile.TYPED_SOURCE *= 'the command line'*
6624 6624

### outrage.mountfile.UNMOUNT_FLAG *= '--unmount'*
6759 6759

### *exception* outrage.mountfile.MountFileError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
7031 7031

### *class* outrage.mountfile.MountTable(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), root: [Spec](mounts.md#outrage.mounts.Spec) | [None](https://docs.python.org/3/library/constants.html#None), mounts: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Spec](mounts.md#outrage.mounts.Spec)], ...], read_only: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Spec](mounts.md#outrage.mounts.Spec)], ...])
7440 7440

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
8296 8296

#### root *: [Spec](mounts.md#outrage.mounts.Spec) | [None](https://docs.python.org/3/library/constants.html#None)*
8379 8379

#### mounts *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Spec](mounts.md#outrage.mounts.Spec)], ...]*
8564 8564

#### read_only *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Spec](mounts.md#outrage.mounts.Spec)], ...]*
8863 8863

#### options() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
9144 9144

### *class* outrage.mountfile.Origin(mount: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), flag: [str](https://docs.python.org/3/library/stdtypes.html#str), value: [str](https://docs.python.org/3/library/stdtypes.html#str), source: [str](https://docs.python.org/3/library/stdtypes.html#str))
9330 9332

#### mount *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
10154 10156

#### flag *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
10333 10335

#### value *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
10407 10409

#### source *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
10482 10484

#### *property* read_only *: [bool](https://docs.python.org/3/library/functions.html#bool)*
10640 10642

#### *property* file *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
10733 10735

#### *property* store *: [Spec](mounts.md#outrage.mounts.Spec)*
11145 11147

### *class* outrage.mountfile.Starter(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), action: [str](https://docs.python.org/3/library/stdtypes.html#str), text: [str](https://docs.python.org/3/library/stdtypes.html#str), missing: [str](https://docs.python.org/3/library/stdtypes.html#str))
11267 11269

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
11716 11718

#### action *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
11799 11801

#### text *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
11902 11904

#### missing *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
12042 12044

#### *property* writes *: [bool](https://docs.python.org/3/library/functions.html#bool)*
12323 12325

### outrage.mountfile.directory_in(argv: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
12413 12415

### outrage.mountfile.origins(argv: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, front: [int](https://docs.python.org/3/library/functions.html#int) = 0, builtin: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Origin](#outrage.mountfile.Origin)]
12957 12961

### outrage.mountfile.plan_starter(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, root_mount: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, mounts: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), read_only_mounts: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = ()) → [Starter](#outrage.mountfile.Starter)
13989 13995

### outrage.mountfile.read(path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [MountTable](#outrage.mountfile.MountTable)
15643 15651

### outrage.mountfile.spliced(argv: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, front: [int](https://docs.python.org/3/library/functions.html#int) = 0, builtin: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
16269 16279

### outrage.mountfile.starter_text(table: [MountTable](#outrage.mountfile.MountTable)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
18864 18876

### outrage.mountfile.write_starter(starter: [Starter](#outrage.mountfile.Starter)) → [None](https://docs.python.org/3/library/constants.html#None)
19297 19311
