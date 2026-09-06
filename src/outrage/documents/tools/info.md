Report what this server is: its Python environment, its stores, and its log.

Takes no arguments and reads no documents. Everything it names is a path on
the machine the server runs on, absolute, so a caller elsewhere can act on it.

`python`, `prefix` and `command` are the environment. Use `command` to run
outrage's command line in the same installation this server is: an install is
often editable, so the working tree is the build, and the `outrage` on a
caller's PATH is a different one or none at all. `command` is empty when this
installation has no console script.

`mounts` is the table as it was **opened**, one entry per store, with the file
each is kept in and whether writes are refused there. `directory` holds those
files, the log and the backups; `mount_config` names the configuration files
the table was read from, which is where a mount is changed.

`log` and `log_content` say whether this server is recording what it does and
how much document text it keeps. They describe this server and say nothing
about any other process reading the same stores.

The tool is on by default and a server can be started without it.
