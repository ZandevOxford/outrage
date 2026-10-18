# Mounting data stores

A session sees one namespace of keys, but it can be made of several stores. A
**mount** attaches a store at a key, and that store answers for the key and
everything below it. The store answering for everything no mount claims is the
**root mount**, `store.sqlite` by default.

## The kinds of store

Which backend opens a store follows from its file name, or from `type=` where
the name cannot say.

| Backend | Named by | Writes | Use it for |
| --- | --- | --- | --- |
| SQLite | `.sqlite` | yes | the default: context accumulated a document at a time |
| DuckDB | `.parquet`, a pattern, or `type=duckdb` | no | large reference material; [Parquet stores](parquet-stores.md) |
| PyArrow | `type=pyarrow` | no | one Parquet file with an in-memory index |
| Files | `type=files` | yes | a directory of files a person edits by hand |
| PostgreSQL | `type=postgres` | yes | one store shared between devices; [Postgres](postgres.md) |

`parquet` is another name for `duckdb`, and `postgresql` for `postgres`.

## The mount table

A project's mounts are written down in `mounts.toml` in the store directory
(`.outrage/` by default), which the MCP server and the command line both read:

```toml
# Every FILE is relative to this directory.
root-mount = "store.sqlite"

[mount]
team = "team.sqlite"                        # read-write
docs = { path = "docs", type = "files" }    # a directory of files

[mount-ro]
ref = "reference.sqlite"                    # writes here are refused
```

A store file is always relative to the store directory, so the table can move
with it. A PostgreSQL mount is the exception: it names a service file, which
may be absolute or start with `~`.

`outrage init --mount KEY=FILE` or `outrage config --mount KEY=FILE` writes the
file, commented, when a project has none. After that it is maintained by hand,
and a run naming a mount the table lacks prints the lines to add.

## Mounting for one run

Every command that reads the store takes the same options, so a person sees
the namespace the server serves:

* `--mount KEY=FILE` and `--mount-ro KEY=FILE` add a mount, or replace the one
  the table has at `KEY`;
* `--unmount KEY` removes one;
* `--mount-config FILE` reads another table at that point in the line;
* `--no-mount-config` ignores `mounts.toml` entirely.

Options after the table win, which is how a committed table gets one entry
overridden for a single run. A mount's options follow a comma:
`--mount docs=docs,type=files`.

**Check before you open.** Opening a read-write mount creates it, so a mistyped
file name becomes an empty store that looks like one with nothing in it yet.
`outrage mounts` reports the table a command line would open, without opening
any of it, and which source each entry came from.

## Mounting from a session

Unless the server was started with `--no-remount`, an agent can use the
`mount` and `unmount` tools to change the table for as long as the server runs.
A mount **shadows**: what the store beneath held at those keys is unreachable
until it is unmounted, rather than merged.

## The built-in mounts

The MCP server mounts `outrage` (this documentation, read-only) and `home` (the
user-wide store) on its own. `--unmount outrage` or `--unmount home` leaves one
out, and mounting your own store at either key replaces it. The command line
mounts neither unless `--mount-docs` or `--mount-home` asks.

## A mount that will not open

A store that cannot be reached - a PostgreSQL server off the network, say -
leaves that mount **unavailable** and every other mount working. Nothing below
it can be read or written until it opens again: listings show it as
`unavailable mount`, surveys and searches leave it out and say so, and each
command warns about it on stderr. A mistake in the configuration, rather than
an unreachable server, stops the command instead.

## Reference

* [Command line](../cli.md) - every mount option in full.
* [Tools](../tools.md) - `mount` and `unmount`.
* [Development](../development.md) - the mount table as a checkout uses it.
