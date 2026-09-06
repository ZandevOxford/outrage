# outrage.mountfile
0 0

### outrage.mountfile.BUILTIN_SOURCE *= 'built in'*
2560 2560

### outrage.mountfile.CONFIG_FLAG *= '--mount-config'*
2670 2670

### outrage.mountfile.DEFAULT_NAME *= 'mounts.toml'*
2994 2994

### outrage.mountfile.DIR_FLAG *= '--dir'*
3263 3263

### outrage.mountfile.DOCS_FLAG *= '--mount-docs'*
3443 3443

### outrage.mountfile.DOCS_MOUNT *= 'outrage'*
4145 4145

### outrage.mountfile.FIELDS *= ('root-mount', 'mount', 'mount-ro')*
4444 4444

### outrage.mountfile.MOUNT_FIELD *= 'mount'*
4727 4727

### outrage.mountfile.PATH_FIELD *= 'path'*
4843 4843

### outrage.mountfile.MOUNT_FLAG *= '--mount'*
5183 5183

### outrage.mountfile.NO_CONFIG_FLAG *= '--no-mount-config'*
5268 5268

### outrage.mountfile.READ_ONLY_FIELD *= 'mount-ro'*
5687 5687

### outrage.mountfile.READ_ONLY_FLAG *= '--mount-ro'*
5787 5787

### outrage.mountfile.ROOT_FIELD *= 'root-mount'*
5920 5920

### outrage.mountfile.ROOT_FLAG *= '--root-mount'*
6224 6224

### outrage.mountfile.TYPED_SOURCE *= 'the command line'*
6426 6426

### outrage.mountfile.UNMOUNT_FLAG *= '--unmount'*
6561 6561

### *exception* outrage.mountfile.MountFileError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
6833 6833

### *class* outrage.mountfile.MountTable(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), root: [Spec](mounts.md#outrage.mounts.Spec) | [None](https://docs.python.org/3/library/constants.html#None), mounts: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Spec](mounts.md#outrage.mounts.Spec)], ...], read_only: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Spec](mounts.md#outrage.mounts.Spec)], ...])
7242 7242

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
8098 8098

#### root *: [Spec](mounts.md#outrage.mounts.Spec) | [None](https://docs.python.org/3/library/constants.html#None)*
8181 8181

#### mounts *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Spec](mounts.md#outrage.mounts.Spec)], ...]*
8366 8366

#### read_only *: [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Spec](mounts.md#outrage.mounts.Spec)], ...]*
8665 8665

#### options() → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
8946 8946

### *class* outrage.mountfile.Origin(mount: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None), flag: [str](https://docs.python.org/3/library/stdtypes.html#str), value: [str](https://docs.python.org/3/library/stdtypes.html#str), source: [str](https://docs.python.org/3/library/stdtypes.html#str))
9132 9134

#### mount *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)*
9956 9958

#### flag *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
10135 10137

#### value *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
10209 10211

#### source *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
10284 10286

#### *property* read_only *: [bool](https://docs.python.org/3/library/functions.html#bool)*
10442 10444

#### *property* file *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
10535 10537

#### *property* store *: [Spec](mounts.md#outrage.mounts.Spec)*
10947 10949

### *class* outrage.mountfile.Starter(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), action: [str](https://docs.python.org/3/library/stdtypes.html#str), text: [str](https://docs.python.org/3/library/stdtypes.html#str), missing: [str](https://docs.python.org/3/library/stdtypes.html#str))
11069 11071

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
11518 11520

#### action *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
11601 11603

#### text *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
11704 11706

#### missing *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
11844 11846

#### *property* writes *: [bool](https://docs.python.org/3/library/functions.html#bool)*
12125 12127

### outrage.mountfile.directory_in(argv: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)
12215 12217

### outrage.mountfile.origins(argv: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, front: [int](https://docs.python.org/3/library/functions.html#int) = 0, builtin: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[Origin](#outrage.mountfile.Origin)]
12759 12763

### outrage.mountfile.plan_starter(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, root_mount: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None, mounts: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = (), read_only_mounts: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)] = ()) → [Starter](#outrage.mountfile.Starter)
13791 13797

### outrage.mountfile.read(path: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [MountTable](#outrage.mountfile.MountTable)
15445 15453

### outrage.mountfile.sources(argv: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, front: [int](https://docs.python.org/3/library/functions.html#int) = 0, builtin: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
16071 16081

### outrage.mountfile.spliced(argv: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)], \*, directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, front: [int](https://docs.python.org/3/library/functions.html#int) = 0, builtin: [bool](https://docs.python.org/3/library/functions.html#bool) = False) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
17628 17640

### outrage.mountfile.starter_text(table: [MountTable](#outrage.mountfile.MountTable)) → [str](https://docs.python.org/3/library/stdtypes.html#str)
20242 20256

### outrage.mountfile.write_starter(starter: [Starter](#outrage.mountfile.Starter)) → [None](https://docs.python.org/3/library/constants.html#None)
20675 20691
