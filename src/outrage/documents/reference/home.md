# outrage.home

The writable document store shared by every project for one user.

This store is deliberately outside a project's store directory.  It is a
built-in mount rather than an ordinary mount specification, so the rule that
keeps every configured store path relative to `--dir` remains intact.

### outrage.home.DIRECTORY_NAME *= '.outrage'*

The directory beneath the user's home that holds Outrage state.

### *exception* outrage.home.HomeStoreError(code: [str](https://docs.python.org/3/builtins/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))

Bases: [`OutrageError`](errors.md#outrage.errors.OutrageError), [`OSError`](https://docs.python.org/3/builtins/exceptions.html#OSError)

Raised when the built-in home store cannot be opened or bootstrapped.

### outrage.home.MOUNT_POINT *= 'home'*

The namespace prefix where the user-wide store is mounted.

### outrage.home.README *= "# Home store\\n\\nThis writable store is shared by every Outrage project for this user.\\nKeep durable user-wide knowledge here; keep project-specific state and\\ndecisions in the project's root store. Changes here affect every project.\\n\\nNo namespace beyond 'readme' is prescribed yet. Add titles and routes as the\\nstore grows.\\n"*

The minimal document seeded into a new or deliberately emptied home store.

### outrage.home.README_KEY *= 'readme'*

The bootstrap document's key inside the home store.

### outrage.home.README_TITLE *= 'Home store'*

The bootstrap document's title metadata.

### outrage.home.STORE_FILE *= 'home.sqlite'*

The distinct file name that cannot alias a project root store.

### outrage.home.open_store(\*, log: [EventLog](eventlog.md#outrage.eventlog.EventLog) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, mount_point: [str](https://docs.python.org/3/builtins/stdtypes.html#str) = MOUNT_POINT, versioning: [bool](https://docs.python.org/3/builtins/functions.html#bool) = True) → [Store](store.md#outrage.store.Store)

Open the home store and seed its minimal readme when it is empty.

### outrage.home.path() → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

The user-wide store file, independent of project directory settings.
