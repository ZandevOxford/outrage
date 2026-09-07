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
7242 7242

#### path *: Path*
8098 8098

#### root *: Spec | None*
8181 8181

#### mounts *: tuple[tuple[str, Spec], ...]*
8366 8366

#### read_only *: tuple[tuple[str, Spec], ...]*
8665 8665

#### options() → list[str]
8946 8946

### *class* outrage.mountfile.Origin(mount: str | None, flag: str, value: str, source: str)
9132 9134

#### mount *: str | None*
9956 9958

#### flag *: str*
10135 10137

#### value *: str*
10209 10211

#### source *: str*
10284 10286

#### *property* read_only *: bool*
10442 10444

#### *property* file *: str*
10535 10537

#### *property* store *: Spec*
10947 10949

### *class* outrage.mountfile.Starter(path: Path, action: str, text: str, missing: str)
11069 11071

#### path *: Path*
11518 11520

#### action *: str*
11601 11603

#### text *: str*
11704 11706

#### missing *: str*
11844 11846

#### *property* writes *: bool*
12125 12127

### outrage.mountfile.directory_in(argv: Sequence[str]) → str | None
12215 12217

### outrage.mountfile.origins(argv: Sequence[str], \*, directory: str | PathLike[str] | None = None, front: int = 0, builtin: bool = False) → list[Origin]
12759 12763

### outrage.mountfile.plan_starter(directory: str | PathLike[str], \*, root_mount: str | None = None, mounts: Sequence[str] = (), read_only_mounts: Sequence[str] = ()) → Starter
13791 13797

### outrage.mountfile.read(path: str | PathLike[str]) → MountTable
15445 15453

### outrage.mountfile.sources(argv: Sequence[str], \*, directory: str | PathLike[str] | None = None, front: int = 0, builtin: bool = False) → list[str]
16071 16081

### outrage.mountfile.spliced(argv: Sequence[str], \*, directory: str | PathLike[str] | None = None, front: int = 0, builtin: bool = False) → list[str]
17628 17640

### outrage.mountfile.starter_text(table: MountTable) → str
20242 20256

### outrage.mountfile.write_starter(starter: Starter) → None
20675 20691
