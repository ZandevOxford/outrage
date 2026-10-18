# Export and backup

To export data from *outrage* in bulk, there are three main options:

* Use the *backup* function, which will keep everything suitable for restoring.
* Use the *export* function, which writes documents as ordinary files which can
  be viewed and edited as usual.
* Use mounts and copy data into them.

## Backup

`outrage backup`

copies the root store to a timestamped file under `backups/` in the store
directory, then checks what it wrote against the source. Name a mount to back
that one up instead, and `--to` to choose where it goes:

`outrage backup ref --to ~/backups/ref.sqlite`

**Never copy a SQLite store with `cp`.** A store in WAL mode keeps recent
writes in a sidecar file, and a copy of the `.sqlite` alone opens cleanly but
is missing them. `outrage backup` copies through SQLite itself and checks the
copy's integrity, schema version and row count.

A PostgreSQL store is backed up into a local `.sqlite` file: one consistent
snapshot that opens with no server. [Postgres](postgres.md).

### Restoring

A backup is an ordinary store. Mount it to look inside before restoring:

`outrage ls --mount old=backups/store-2026-10-18.sqlite old`

To restore, stop anything using the store and put the backup in its place.
*(Draft: confirm the procedure, including what happens to any `-wal` and
`-shm` files left beside the old store.)*

## Export and import

`outrage export DIRECTORY [key]`

writes a subtree as a directory with one file per document. A key segment is a
directory, and a document is a file whose extension names its format; a title
is the file `!title.md` beside its document's directory. Paths are written
from the top of the namespace, so an export of `plans` lands in
`DIRECTORY/plans/`.

`outrage import DIRECTORY [key]`

is the inverse. A `.md` or `.json` extension is stripped and read as the
format; any other file name becomes the key whole.

Both leave anything already there alone by default; `--on-conflict` chooses
`overwrite` or `stop` instead, and `--dry-run` reports what would happen.

**Export is not a backup.** It carries the documents and their metadata, but
not the earlier versions or anything else the database keeps about them.

### Editing a store as files

An exported tree can be mounted directly rather than imported back:

`--mount notes=notes,type=files`

That makes a directory a read-write store a person can edit with any editor.

`--extensions keep` on export, import or a `files` mount makes a whole file
name the key, so `guide.md` is the key `guide.md`. Use it for a documentation
bundle whose files link to each other by name.

## Copying within the namespace

`outrage copy SOURCE TARGET` copies a subtree beneath another key, including
between mounted stores. `--reroot` lands it *at* `TARGET` instead, which is
what moving a subtree needs.

The `copy_tree` tool is the equivalent in the MCP server.

## Checking a store

`outrage check` reports whether a store is sound, and `outrage check --repair`
fixes what can be fixed - for SQLite, folding the write-ahead log back into the
database. No repair changes a document.

## Using mounts as an export

If you mount a file backed store, then any files copied into it become visible
in the file system. This can be used as an alternative to export.

Alternatively, you can create a new [Parquet store](parquet-stores.md) as
an archive of part of the tree.

## References

* [Command line](../cli.md) - `backup`, `export`, `import`, `copy` and
  `check`.
* [Mounting data stores](mounting-data-stores.md)
