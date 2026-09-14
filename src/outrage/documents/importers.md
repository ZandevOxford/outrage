# Importers

An importer turns an outside source of documents into a store Outrage can
mount. Each is a separate distribution with its own command, kept under
`import/` in the repository, so a project that never imports anything installs
none of their dependencies.

For now there is one.

## MediaWiki

**[The MediaWiki importer](../../../import/mediawiki/README.md)** turns a
Wikimedia content dump - Wikipedia, or any other wiki Wikimedia publishes - into
a directory of Parquet parts, one per dump piece, readable as each one
completes. It is the distribution `outrage-mediawiki`, with the command
`mediawiki-import`, and
[its command line](../../../import/mediawiki/cli.md) is documented beside it.

A directory of parts is mounted through DuckDB, which needs the `duckdb` or
`parquet` extra, either as the directory or as a pattern over its parts:

`pip install "outrage[duckdb]"`

`outrage-server --mount-ro ref=parts,type=duckdb`

`outrage-server --mount-ro ref=parts/*.parquet`
