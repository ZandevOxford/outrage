# Outrage MediaWiki importer

`mediawiki-import` downloads a Wikimedia `mediawiki_content_current` dump and turns
each compressed XML piece into an independently readable Parquet part. The
target is an Outrage directory-backed DuckDB store: completed parts become
available one by one, and no corpus-wide merge is required.

```sh
pip install -e import/mediawiki
mediawiki-import --download-dir ~/wikipedia --wiki simplewiki
outrage ls --dir ~/wikipedia --store simplewiki,type=duckdb
```

Downloads, control files and conversion receipts live in `--download-dir`.
The store defaults to `<download-dir>/<wiki>` and contains only `.parquet`
parts. An interrupted download resumes; a completed and verified download or
converted part is reused.

An article is stored at its mapped title and carries its exact title at
`!title`. Each redirect is one value below its target's `!aliases` namespace;
that representation lets aliases arriving in different parts accumulate
without rewriting an earlier part. Broken redirects remain as metadata below
an implicit target rather than requiring a corpus-wide reconciliation pass.

Use `--files N` for the first N pieces in numeric page-id order, `--stage`
to run only discovery, fetching or conversion, and `--dry-run` to inspect the
resolved dump without downloading it.

**[The command line](cli.md)** documents every option. It is generated from
the argument parser by `make -C docs documents` at the repository root, so
edit the parser's help rather than the page.

## Development

A distribution of its own, with its own version and changelog, developed
beside the `outrage` checkout two levels up. Its suite runs from this
directory and tests that checkout's `outrage` unless `OUTRAGE_TEST_INSTALLED=1`
is set:

```sh
cd import/mediawiki
pytest
```
