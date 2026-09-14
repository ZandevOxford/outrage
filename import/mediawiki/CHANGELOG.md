# Changelog

## Unreleased

Initial implementation of `mediawiki-import`: completed-dump discovery, numeric
page-range selection, resumable SHA-256-verified downloads, streaming XML and
wikitext conversion, atomic Parquet parts, namespace selection, redirects as
independent alias metadata, conversion receipts, staged runs and concurrent
conversion.

The distribution is `outrage-mediawiki`, its package `outrage_mediawiki` and
its command `mediawiki-import`, in `import/mediawiki/` of the outrage
repository; it was `outrage-wikiimport`, `wikiimport` and `wiki-import` in
`import/` before it was ever published. Conversion receipts moved with the
name, from `.wikiimport` to `.mediawiki-import` in the download directory.
Every option now has help, and `cli.md` documents the command line.

Requires `outrage[parquet]>=0.14.0`, whose `parquet` extra installs duckdb as
well as pyarrow and whose pyarrow backend is `outrage.store_pyarrow`.
