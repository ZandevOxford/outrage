# outrage.mountfile
0 0 1

### outrage.mountfile.BUILTIN_SOURCE *= 'built in'*
2560 2560 43

### outrage.mountfile.CONFIG_FLAG *= '--mount-config'*
2670 2670 47

### outrage.mountfile.DEFAULT_NAME *= 'mounts.toml'*
2994 2994 54

### outrage.mountfile.DIR_FLAG *= '--dir'*
3263 3263 60

### outrage.mountfile.DOCS_FLAG *= '--mount-docs'*
3443 3443 65

### outrage.mountfile.DOCS_MOUNT *= 'outrage'*
4145 4145 78

### outrage.mountfile.HOME_FLAG *= '--mount-home'*
4444 4444 84

### outrage.mountfile.HOME_MOUNT *= 'home'*
4646 4646 89

### outrage.mountfile.FIELDS *= ('root-mount', 'mount', 'mount-ro')*
4760 4760 93

### outrage.mountfile.MOUNT_FIELD *= 'mount'*
5043 5043 99

### outrage.mountfile.PATH_FIELD *= 'path'*
5159 5159 103

### outrage.mountfile.MOUNT_FLAG *= '--mount'*
5733 5733 114

### outrage.mountfile.NO_CONFIG_FLAG *= '--no-mount-config'*
5818 5818 118

### outrage.mountfile.READ_ONLY_FIELD *= 'mount-ro'*
6237 6237 127

### outrage.mountfile.READ_ONLY_FLAG *= '--mount-ro'*
6337 6337 131

### outrage.mountfile.ROOT_FIELD *= 'root-mount'*
6470 6470 135

### outrage.mountfile.ROOT_FLAG *= '--root-mount'*
6774 6774 142

### outrage.mountfile.TYPED_SOURCE *= 'the command line'*
6976 6976 147

### outrage.mountfile.UNMOUNT_FLAG *= '--unmount'*
7111 7111 151

### *exception* outrage.mountfile.MountFileError(code: str, \*\*details: Any)
7383 7383 157

### *class* outrage.mountfile.MountTable(path: Path, root: Spec | None, mounts: tuple[tuple[str, Spec], ...], read_only: tuple[tuple[str, Spec], ...])
7794 7794 163

#### path *: Path*
8658 8658 169

#### root *: Spec | None*
8741 8741 171

#### mounts *: tuple[tuple[str, Spec], ...]*
8927 8927 175

#### read_only *: tuple[tuple[str, Spec], ...]*
9229 9229 179

#### options() → list[str]
9513 9513 183

### *class* outrage.mountfile.Origin(mount: str | None, flag: str, value: str, source: str)
9701 9703 187

#### mount *: str | None*
10531 10533 199

#### flag *: str*
10712 10714 203

#### value *: str*
10787 10789 205

#### source *: str*
10863 10865 207

#### *property* read_only *: bool*
11022 11024 211

#### *property* file *: str*
11116 11118 213

#### *property* store *: Spec*
11529 11531 222

### *class* outrage.mountfile.Starter(path: Path, action: str, text: str, missing: str)
11651 11653 226

#### path *: Path*
12104 12106 232

#### action *: str*
12187 12189 234

#### text *: str*
12291 12293 238

#### missing *: str*
12432 12434 242

#### *property* writes *: bool*
12714 12716 249

### outrage.mountfile.directory_in(argv: Sequence[str]) → str | None
12805 12807 251

### outrage.mountfile.origins(argv: Sequence[str], \*, directory: str | PathLike[str] | None = None, front: int = 0, builtin: bool = False) → list[Origin]
13352 13356 259

### outrage.mountfile.plan_starter(directory: str | PathLike[str], \*, root_mount: str | None = None, mounts: Sequence[str] = (), read_only_mounts: Sequence[str] = ()) → Starter
14391 14397 267

### outrage.mountfile.read(path: str | PathLike[str]) → MountTable
16051 16059 286

### outrage.mountfile.sources(argv: Sequence[str], \*, directory: str | PathLike[str] | None = None, front: int = 0, builtin: bool = False) → list[str]
16679 16689 296

### outrage.mountfile.spliced(argv: Sequence[str], \*, directory: str | PathLike[str] | None = None, front: int = 0, builtin: bool = False) → list[str]
18244 18256 314

### outrage.mountfile.starter_text(table: MountTable) → str
20838 20852 348

### outrage.mountfile.write_starter(starter: Starter) → None
21272 21288 357
