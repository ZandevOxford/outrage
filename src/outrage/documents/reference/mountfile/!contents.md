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

### *exception* outrage.mountfile.MountFileError(code: str, \*\*details: Any)
6833 6833

### *class* outrage.mountfile.MountTable(path: Path, root: Spec | None, mounts: tuple[tuple[str, Spec], ...], read_only: tuple[tuple[str, Spec], ...])
7244 7244

#### path *: Path*
8108 8108

#### root *: Spec | None*
8191 8191

#### mounts *: tuple[tuple[str, Spec], ...]*
8377 8377

#### read_only *: tuple[tuple[str, Spec], ...]*
8679 8679

#### options() → list[str]
8963 8963

### *class* outrage.mountfile.Origin(mount: str | None, flag: str, value: str, source: str)
9151 9153

#### mount *: str | None*
9981 9983

#### flag *: str*
10162 10164

#### value *: str*
10237 10239

#### source *: str*
10313 10315

#### *property* read_only *: bool*
10472 10474

#### *property* file *: str*
10566 10568

#### *property* store *: Spec*
10979 10981

### *class* outrage.mountfile.Starter(path: Path, action: str, text: str, missing: str)
11101 11103

#### path *: Path*
11554 11556

#### action *: str*
11637 11639

#### text *: str*
11741 11743

#### missing *: str*
11882 11884

#### *property* writes *: bool*
12164 12166

### outrage.mountfile.directory_in(argv: Sequence[str]) → str | None
12255 12257

### outrage.mountfile.origins(argv: Sequence[str], \*, directory: str | PathLike[str] | None = None, front: int = 0, builtin: bool = False) → list[Origin]
12802 12806

### outrage.mountfile.plan_starter(directory: str | PathLike[str], \*, root_mount: str | None = None, mounts: Sequence[str] = (), read_only_mounts: Sequence[str] = ()) → Starter
13841 13847

### outrage.mountfile.read(path: str | PathLike[str]) → MountTable
15501 15509

### outrage.mountfile.sources(argv: Sequence[str], \*, directory: str | PathLike[str] | None = None, front: int = 0, builtin: bool = False) → list[str]
16129 16139

### outrage.mountfile.spliced(argv: Sequence[str], \*, directory: str | PathLike[str] | None = None, front: int = 0, builtin: bool = False) → list[str]
17694 17706

### outrage.mountfile.starter_text(table: MountTable) → str
20316 20330

### outrage.mountfile.write_starter(starter: Starter) → None
20750 20766
