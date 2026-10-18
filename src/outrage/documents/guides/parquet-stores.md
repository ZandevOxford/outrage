# Parquet stores

A Parquet store is a read-only store written once and read many times: a
reference base of tens of thousands of documents or more, around 11 times
smaller than the same corpus in SQLite. It needs the extra:

`pip install "outrage[parquet]"`

## Making one

Parquet stores are not updated in place; `outrage pack` writes one whole.
From a directory of files, mapped to keys as `outrage import` maps them:

`outrage pack .outrage/reference.parquet --from-dir ./manuals`

or from an existing store, whose documents, metadata and timestamps all come
across:

`outrage pack .outrage/reference.parquet --from-store staging.sqlite`

The second is the usual way to build a reference base: accumulate it in a
SQLite store, then compact it. A key prefix packs only that subtree, or stores
a directory's documents beneath it. Nothing is written until the whole file
is, so an interrupted pack leaves nothing behind.

The file to write is a path from the working directory, unlike a mount,
which is relative to the store directory. Writing it into `.outrage/` is what
lets the mount below name it as `reference.parquet`.

## Mounting it

Mount a Parquet store read-only:

```toml
[mount-ro]
ref = "reference.parquet"
```

or for one run, `--mount-ro ref=reference.parquet`. A `.parquet` file is read
through DuckDB.

**A store too large for one file**, or one that arrives in pieces, is read as
parts in any order:

```text
--mount-ro ref=parts/*.parquet
--mount-ro ref=parts,type=duckdb
```

The second reads every `.parquet` file directly inside a directory, which has
no extension to say which backend it needs.

`type=pyarrow` reads a single file with PyArrow instead, holding an index in
memory. It is also what still opens a file written before 0.4.0.

## Reading one directly

A packed file can be the whole store for one command:

`outrage ls --store reference.parquet --no-mount-config`

`--no-mount-config` is needed where a `mounts.toml` would otherwise mount
writable stores around it, since a mount table needs a writable root.

## Checking one

`outrage check ref` reports how many parts and rows a Parquet store has, and
how many rows repeat a key.

## Importing a wiki

The separate `outrage-mediawiki` distribution turns a Wikimedia content dump
into a directory of Parquet parts, readable as each one completes.
[Importers](../importers.md).

## Reference

* [Command line](../cli.md#pack) - `outrage pack`.
* [Mounting data stores](mounting-data-stores.md) - the mount table.
