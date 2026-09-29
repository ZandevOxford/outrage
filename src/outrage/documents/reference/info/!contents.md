# outrage.info
0 0 1

### *class* outrage.info.Info(version: str, python: str, prefix: str, command: tuple[str, ...] = (), directory: str | None = None, mount_config: tuple[str, ...] = (), log: str | None = None, log_content: str | None = None, mounts: tuple[MountInfo, ...] = ())
1334 1334 25

#### version *: str*
2544 2544 31

#### python *: str*
2622 2622 33

#### prefix *: str*
3026 3026 41

#### command *: tuple[str, ...]*
3219 3219 45

#### directory *: str | None*
3554 3554 51

#### mount_config *: tuple[str, ...]*
3897 3897 57

#### log *: str | None*
4116 4116 61

#### log_content *: str | None*
4326 4326 65

#### mounts *: tuple[MountInfo, ...]*
4543 4543 69

### *class* outrage.info.MountInfo(mount: str, path: str | None, kind: str, read_only: bool, versioned: bool | None = None, target: dict[str, str] | None = None, unavailable: dict[str, Any] | None = None)
4722 4722 73

#### mount *: str*
5897 5897 79

#### path *: str | None*
6037 6037 83

#### kind *: str*
6349 6349 89

#### read_only *: bool*
6681 6681 95

#### versioned *: bool | None*
6973 6973 101

#### target *: dict[str, str] | None*
7436 7436 110

#### unavailable *: dict[str, Any] | None*
7976 7976 116

### outrage.info.describe(opened: Store, \*, directory: str | PathLike[str] | None = None, mount_config: Sequence[str] = (), log: EventLog | None = None) → Info
8427 8427 122

### outrage.info.mount_infos(opened: Store) → tuple[MountInfo, ...]
9805 9807 137
