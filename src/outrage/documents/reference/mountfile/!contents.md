# outrage.mountfile
0 0 1

### outrage.mountfile.BUILTIN_SOURCE *= 'built in'*
2743 2743 46

### outrage.mountfile.CONFIG_FLAG *= '--mount-config'*
2853 2853 50

### outrage.mountfile.DEFAULT_NAME *= 'mounts.toml'*
3177 3177 57

### outrage.mountfile.DIR_FLAG *= '--dir'*
3446 3446 63

### outrage.mountfile.DOCS_FLAG *= '--mount-docs'*
3626 3626 68

### outrage.mountfile.DOCS_MOUNT *= 'outrage'*
4328 4328 81

### outrage.mountfile.HOME_FLAG *= '--mount-home'*
4627 4627 87

### outrage.mountfile.HOME_MOUNT *= 'home'*
4829 4829 92

### outrage.mountfile.FIELDS *= ('root-mount', 'mount', 'mount-ro')*
4943 4943 96

### outrage.mountfile.MOUNT_FIELD *= 'mount'*
5226 5226 102

### outrage.mountfile.PATH_FIELD *= 'path'*
5342 5342 106

### outrage.mountfile.MOUNT_FLAG *= '--mount'*
5916 5916 117

### outrage.mountfile.NO_CONFIG_FLAG *= '--no-mount-config'*
6001 6001 121

### outrage.mountfile.READ_ONLY_FIELD *= 'mount-ro'*
6420 6420 130

### outrage.mountfile.READ_ONLY_FLAG *= '--mount-ro'*
6520 6520 134

### outrage.mountfile.ROOT_FIELD *= 'root-mount'*
6653 6653 138

### outrage.mountfile.ROOT_FLAG *= '--root-mount'*
6957 6957 145

### outrage.mountfile.TYPED_SOURCE *= 'the command line'*
7159 7159 150

### outrage.mountfile.UNMOUNT_FLAG *= '--unmount'*
7294 7294 154

### *exception* outrage.mountfile.MountFileError(code: str, \*\*details: Any)
7566 7566 160

### *class* outrage.mountfile.MountTable(path: Path, root: Spec | None, mounts: tuple[tuple[str, Spec], ...], read_only: tuple[tuple[str, Spec], ...])
7977 7977 166

#### path *: Path*
8841 8841 172

#### root *: Spec | None*
8924 8924 174

#### mounts *: tuple[tuple[str, Spec], ...]*
9110 9110 178

#### read_only *: tuple[tuple[str, Spec], ...]*
9412 9412 182

#### options() → list[str]
9696 9696 186

### *class* outrage.mountfile.Origin(mount: str | None, flag: str, value: str, source: str)
9884 9886 190

#### mount *: str | None*
10714 10716 202

#### flag *: str*
10895 10897 206

#### value *: str*
10970 10972 208

#### source *: str*
11046 11048 210

#### *property* read_only *: bool*
11205 11207 214

#### *property* file *: str*
11299 11301 216

#### *property* store *: Spec*
11712 11714 225

### *class* outrage.mountfile.Starter(path: Path, action: str, text: str, missing: str)
11834 11836 229

#### path *: Path*
12287 12289 235

#### action *: str*
12370 12372 237

#### text *: str*
12474 12476 241

#### missing *: str*
12615 12617 245

#### *property* writes *: bool*
12897 12899 252

### outrage.mountfile.directory_in(argv: Sequence[str]) → str | None
12988 12990 254

### outrage.mountfile.origins(argv: Sequence[str], \*, directory: str | PathLike[str] | None = None, front: int = 0, builtin: bool = False) → list[Origin]
13535 13539 262

### outrage.mountfile.plan_starter(directory: str | PathLike[str], \*, root_mount: str | None = None, mounts: Sequence[str] = (), read_only_mounts: Sequence[str] = ()) → Starter
14574 14580 270

### outrage.mountfile.read(path: str | PathLike[str]) → MountTable
16234 16242 289

### outrage.mountfile.sources(argv: Sequence[str], \*, directory: str | PathLike[str] | None = None, front: int = 0, builtin: bool = False) → list[str]
16862 16872 299

### outrage.mountfile.spliced(argv: Sequence[str], \*, directory: str | PathLike[str] | None = None, front: int = 0, builtin: bool = False) → list[str]
18427 18439 317

### outrage.mountfile.starter_text(table: MountTable) → str
21021 21035 351

### outrage.mountfile.write_starter(starter: Starter) → None
21455 21471 360
