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

### *class* outrage.info.MountInfo(mount: str, path: str | None, kind: str, read_only: bool)
4541 4541

#### mount *: str*
5024 5024

#### path *: str | None*
5163 5163

#### kind *: str*
5473 5473

#### read_only *: bool*
5727 5727

### outrage.info.describe(opened: Store, \*, directory: str | PathLike[str] | None = None, mount_config: Sequence[str] = (), log: EventLog | None = None) → Info
5859 5859

### outrage.info.mount_infos(opened: Store) → tuple[MountInfo, ...]
7232 7234
