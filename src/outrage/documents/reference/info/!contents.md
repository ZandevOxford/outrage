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

### *class* outrage.info.MountInfo(mount: str, path: str | None, kind: str, read_only: bool, versioned: bool | None = None, target: dict[str, str] | None = None, unavailable: dict[str, Any] | None = None)
4570 4570 71

#### mount *: str*
5745 5745 77

#### path *: str | None*
5885 5885 81

#### kind *: str*
6197 6197 87

#### read_only *: bool*
6529 6529 93

#### versioned *: bool | None*
6821 6821 99

#### target *: dict[str, str] | None*
7284 7284 108

#### unavailable *: dict[str, Any] | None*
7824 7824 114

### outrage.info.describe(opened: Store, \*, directory: str | PathLike[str] | None = None, mount_config: Sequence[str] = (), log: EventLog | None = None) → Info
8275 8275 120

### outrage.info.mount_infos(opened: Store) → tuple[MountInfo, ...]
9653 9655 135
