# outrage.home

The writable document store shared by every project for one user.

This store is deliberately outside a project's store directory.  It is a
built-in mount rather than an ordinary mount specification, so the rule that
keeps every configured store path relative to `--dir` remains intact.

The same directory holds the user's configuration file, `config.toml`. It is
named for Outrage as a whole rather than for any one feature, because a file
already on people's machines is expensive to rename, and each feature reads
its own table from it.

### outrage.home.CONFIG_EXPOSED_BITS *= 63*

Permission bits that must be clear on the configuration file: any access
at all by group or others, as libpq requires of `.pgpass`.

### outrage.home.CONFIG_FILE *= 'config.toml'*

The user's configuration file, beside the home store.

### outrage.home.DIRECTORY_NAME *= '.outrage'*

The directory beneath the user's home that holds Outrage state.

### *exception* outrage.home.HomeStoreError(code: [str](https://docs.python.org/3/builtins/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`OSError`](https://docs.python.org/3/builtins/exceptions.html#OSError)

Raised when the built-in home store cannot be opened or bootstrapped.

### outrage.home.MOUNT_POINT *= 'home'*

The namespace prefix where the user-wide store is mounted.

### outrage.home.README_DOCUMENT *= 'home_readme'*

The shipped template used to bootstrap the home store.

### outrage.home.README_KEY *= 'readme'*

The bootstrap document's key inside the home store.

### outrage.home.README_TITLE *= 'Home store'*

The bootstrap document's title metadata.

### outrage.home.STORE_FILE *= 'home.sqlite'*

The distinct file name that cannot alias a project root store.

### *exception* outrage.home.UserConfigError(code: [str](https://docs.python.org/3/builtins/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`ValueError`](https://docs.python.org/3/builtins/exceptions.html#ValueError)

Raised when the user's configuration file cannot be used.

### outrage.home.config_path() → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

The user's configuration file, which need not exist.

### outrage.home.open_store(\*, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, mount_point: [str](https://docs.python.org/3/builtins/stdtypes.html#str) = MOUNT_POINT, versioning: [bool](https://docs.python.org/3/builtins/functions.html#bool) = True) → [Store](store.md#outrage.store.Store)

Open the home store and seed its minimal readme when it is empty.

### outrage.home.path() → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

The user-wide store file, independent of project directory settings.

### outrage.home.read_config(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/builtins/constants.html#None) = None) → [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]

The user's configuration as a table, or an empty one when there is no file.

**A file other users can open is refused before it is read**, since it may
hold an API key, and a key readable by others has to be treated as out.
Refusing says so; ignoring the file instead would leave its owner puzzled
about why their settings had no effect. Any group or other access counts,
writing included, as a key that others can redirect is as bad as one they
can read. POSIX only: Windows permissions are not mode bits.

### outrage.home.readme() → [str](https://docs.python.org/3/builtins/stdtypes.html#str)

The shipped home-store conventions used for a new store's readme.
