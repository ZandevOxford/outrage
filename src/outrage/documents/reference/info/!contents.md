# outrage.info
0 0 1

### *class* outrage.info.Info(version: str, python: str, prefix: str, command: tuple[str, ...] = (), directory: str | None = None, mount_config: tuple[str, ...] = (), log: str | None = None, log_content: str | None = None, mounts: tuple[MountInfo, ...] = ())
1182 1182 23

#### version *: str*
2392 2392 29

#### python *: str*
2470 2470 31

#### prefix *: str*
2874 2874 39

#### command *: tuple[str, ...]*
3067 3067 43

#### directory *: str | None*
3402 3402 49

#### mount_config *: tuple[str, ...]*
3745 3745 55

#### log *: str | None*
3964 3964 59

#### log_content *: str | None*
4174 4174 63

#### mounts *: tuple[MountInfo, ...]*
4391 4391 67

### *class* outrage.info.MountInfo(mount: str, path: str | None, kind: str, read_only: bool, versioned: bool | None = None)
4570 4570 71

#### mount *: str*
5206 5206 77

#### path *: str | None*
5346 5346 81

#### kind *: str*
5658 5658 87

#### read_only *: bool*
5913 5913 92

#### versioned *: bool | None*
6046 6046 96

### outrage.info.describe(opened: Store, \*, directory: str | PathLike[str] | None = None, mount_config: Sequence[str] = (), log: EventLog | None = None) → Info
6509 6509 105

### outrage.info.mount_infos(opened: Store) → tuple[MountInfo, ...]
7887 7889 120
