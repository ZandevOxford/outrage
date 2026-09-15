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

### outrage.mountfile.HOME_FLAG *= '--mount-home'*
4444 4444

### outrage.mountfile.HOME_MOUNT *= 'home'*
4646 4646

### outrage.mountfile.FIELDS *= ('root-mount', 'mount', 'mount-ro')*
4760 4760

### outrage.mountfile.MOUNT_FIELD *= 'mount'*
5043 5043

### outrage.mountfile.PATH_FIELD *= 'path'*
5159 5159

### outrage.mountfile.MOUNT_FLAG *= '--mount'*
5499 5499

### outrage.mountfile.NO_CONFIG_FLAG *= '--no-mount-config'*
5584 5584

### outrage.mountfile.READ_ONLY_FIELD *= 'mount-ro'*
6003 6003

### outrage.mountfile.READ_ONLY_FLAG *= '--mount-ro'*
6103 6103

### outrage.mountfile.ROOT_FIELD *= 'root-mount'*
6236 6236

### outrage.mountfile.ROOT_FLAG *= '--root-mount'*
6540 6540

### outrage.mountfile.TYPED_SOURCE *= 'the command line'*
6742 6742

### outrage.mountfile.UNMOUNT_FLAG *= '--unmount'*
6877 6877

### *exception* outrage.mountfile.MountFileError(code: str, \*\*details: Any)
7149 7149

### *class* outrage.mountfile.MountTable(path: Path, root: Spec | None, mounts: tuple[tuple[str, Spec], ...], read_only: tuple[tuple[str, Spec], ...])
7560 7560

#### path *: Path*
8424 8424

#### root *: Spec | None*
8507 8507

#### mounts *: tuple[tuple[str, Spec], ...]*
8693 8693

#### read_only *: tuple[tuple[str, Spec], ...]*
8995 8995

#### options() → list[str]
9279 9279

### *class* outrage.mountfile.Origin(mount: str | None, flag: str, value: str, source: str)
9467 9469

#### mount *: str | None*
10297 10299

#### flag *: str*
10478 10480

#### value *: str*
10553 10555

#### source *: str*
10629 10631

#### *property* read_only *: bool*
10788 10790

#### *property* file *: str*
10882 10884

#### *property* store *: Spec*
11295 11297

### *class* outrage.mountfile.Starter(path: Path, action: str, text: str, missing: str)
11417 11419

#### path *: Path*
11870 11872

#### action *: str*
11953 11955

#### text *: str*
12057 12059

#### missing *: str*
12198 12200

#### *property* writes *: bool*
12480 12482

### outrage.mountfile.directory_in(argv: Sequence[str]) → str | None
12571 12573

### outrage.mountfile.origins(argv: Sequence[str], \*, directory: str | PathLike[str] | None = None, front: int = 0, builtin: bool = False) → list[Origin]
13118 13122

### outrage.mountfile.plan_starter(directory: str | PathLike[str], \*, root_mount: str | None = None, mounts: Sequence[str] = (), read_only_mounts: Sequence[str] = ()) → Starter
14157 14163

### outrage.mountfile.read(path: str | PathLike[str]) → MountTable
15817 15825

### outrage.mountfile.sources(argv: Sequence[str], \*, directory: str | PathLike[str] | None = None, front: int = 0, builtin: bool = False) → list[str]
16445 16455

### outrage.mountfile.spliced(argv: Sequence[str], \*, directory: str | PathLike[str] | None = None, front: int = 0, builtin: bool = False) → list[str]
18010 18022

### outrage.mountfile.starter_text(table: MountTable) → str
20604 20618

### outrage.mountfile.write_starter(starter: Starter) → None
21038 21054
