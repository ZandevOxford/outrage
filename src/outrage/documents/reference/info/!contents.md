# outrage.info
0 0

### *class* outrage.info.Info(version: str, python: str, prefix: str, command: tuple[str, ...] = (), directory: str | None = None, mount_config: tuple[str, ...] = (), log: str | None = None, log_content: str | None = None, mounts: tuple[MountInfo, ...] = ())
1182 1182

#### version *: str*
2377 2377

#### python *: str*
2454 2454

#### prefix *: str*
2857 2857

#### command *: tuple[str, ...]*
3049 3049

#### directory *: str | None*
3382 3382

#### mount_config *: tuple[str, ...]*
3723 3723

#### log *: str | None*
3940 3940

#### log_content *: str | None*
4148 4148

#### mounts *: tuple[MountInfo, ...]*
4363 4363

### *class* outrage.info.MountInfo(mount: str, path: str | None, kind: str, read_only: bool, versioned: bool | None = None)
4541 4541

#### mount *: str*
5169 5169

#### path *: str | None*
5308 5308

#### kind *: str*
5618 5618

#### read_only *: bool*
5872 5872

#### versioned *: bool | None*
6004 6004

### outrage.info.describe(opened: Store, \*, directory: str | PathLike[str] | None = None, mount_config: Sequence[str] = (), log: EventLog | None = None) → Info
6465 6465

### outrage.info.mount_infos(opened: Store) → tuple[MountInfo, ...]
7838 7840
