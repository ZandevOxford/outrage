# outrage.config
0 0

### outrage.config.PROJECT_CONFIG_NAME *= '.mcp.json'*
850 850

### outrage.config.SCOPES *= ('project', 'user')*
1007 1007

### outrage.config.SCRIPT_NAME *= 'outrage-server'*
1174 1174

### outrage.config.SERVERS_FIELD *= 'mcpServers'*
1439 1439

### outrage.config.SERVER_NAME *= 'outrage'*
1629 1629

### outrage.config.USER_CONFIG_NAME *= '.claude.json'*
1816 1816

### *class* outrage.config.Change(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), scope: [str](https://docs.python.org/3/library/stdtypes.html#str), name: [str](https://docs.python.org/3/library/stdtypes.html#str), action: [str](https://docs.python.org/3/library/stdtypes.html#str), entry: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)], previous: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None))
2023 2023

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*
2915 2915

#### scope *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
2998 2998

#### name *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
3073 3073

#### action *: [str](https://docs.python.org/3/library/stdtypes.html#str)*
3147 3147

#### entry *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*
3261 3261

#### previous *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None)*
3463 3463

#### *property* writes *: [bool](https://docs.python.org/3/library/functions.html#bool)*
3779 3779

### *exception* outrage.config.ConfigError(code: [str](https://docs.python.org/3/library/stdtypes.html#str), \*\*details: [Any](https://docs.python.org/3/library/typing.html#typing.Any))
3869 3869

### outrage.config.config_path(scope: [str](https://docs.python.org/3/library/stdtypes.html#str), project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
4265 4265

### outrage.config.default_store_dir(project_dir: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
4750 4752

### outrage.config.launch_command(executable: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
5182 5186

### outrage.config.merge_entry(previous: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)] | [None](https://docs.python.org/3/library/constants.html#None), entry: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]) → [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]
5982 5988

### outrage.config.mounts_in(args: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]
8021 8029

### outrage.config.plan(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), scope: [str](https://docs.python.org/3/library/stdtypes.html#str), entry: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)], name: [str](https://docs.python.org/3/library/stdtypes.html#str) = SERVER_NAME) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Change](#outrage.config.Change), [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)], [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]
8717 8727

### outrage.config.read_config(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)], [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)]
9773 9785

### outrage.config.server_entry(directory: [str](https://docs.python.org/3/library/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/library/stdtypes.html#str)], command: [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None) = None, \*, log: [Any](https://docs.python.org/3/library/typing.html#typing.Any) = None, log_content: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]
10587 10601

### outrage.config.split_args(args: [Sequence](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence)[[str](https://docs.python.org/3/library/stdtypes.html#str)]) → [list](https://docs.python.org/3/library/stdtypes.html#list)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]]]
12905 12921

### outrage.config.write_config(path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), config: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)], original: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) = None) → [None](https://docs.python.org/3/library/constants.html#None)
13910 13928
