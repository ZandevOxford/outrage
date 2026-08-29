# API reference

Grouped by layer rather than alphabetically: each group depends on the ones
above it, and nothing depends on a group below.

## The namespace

What a key is, and how a failure becomes a sentence. Everything else is
written in these terms.

* [outrage.keys](reference/keys.md)
* [outrage.errors](reference/errors.md)
* [outrage.messages](reference/messages.md)

## Storage

What a store is, the implementations of it, and the table that makes several
stores look like one namespace. [`outrage.store`](reference/store.md#module-outrage.store) is the contract; a caller
that does not care which storage it is reading stops there and never names a
backend. [`outrage.mounts`](reference/mounts.md#module-outrage.mounts) is a caller of that kind and a store itself:
a table of mounts **is** a `Store`, which is what lets one answer for many
without anything above it knowing.

The backends answer the same operations and are for different things.
[`outrage.store_sqlite`](reference/store_sqlite.md#module-outrage.store_sqlite) is the one a store is opened as by default:
read-write, accumulated a document at a time, and what session context and
notes on a codebase live in. [`outrage.store_parquet`](reference/store_parquet.md#module-outrage.store_parquet) is one file, written
whole and read many times, for a reference base of tens of thousands of
documents; it refuses writes, and `outrage pack` is how documents get into
one. [`outrage.store_files`](reference/store_files.md#module-outrage.store_files) is a directory of files, one per key, which is
what an export target and a working copy are -- the shape a person edits by
hand.

Which storage a store *file* is kept in follows from its extension --
`outrage.store._backend_for()` -- and a tree has no extension to read, so
a filesystem store is constructed directly at its path rather than opened by
name.

[`outrage.mountfile`](reference/mountfile.md#module-outrage.mountfile) is the table written down rather than typed: a TOML
file in the store directory, read as though its options had been given on the
command line at the point where the file is named. Both front ends read it, so
a project has one table rather than one per caller.

[`outrage.shipped`](reference/shipped.md#module-outrage.shipped) is the one mount neither of them can name: outrage's own
documentation, a filesystem store inside the installed package, mounted
read-only at `outrage`. A store file is relative to `--dir` and a tree in
`site-packages` is not, so it is opened by absolute path and lent to
[`outrage.mounts.open_mounts()`](reference/mounts.md#outrage.mounts.open_mounts) through its `attached` argument.

* [outrage.store](reference/store.md)
* [outrage.store_sqlite](reference/store_sqlite.md)
* [outrage.store_parquet](reference/store_parquet.md)
* [outrage.store_files](reference/store_files.md)
* [outrage.mounts](reference/mounts.md)
* [outrage.mountfile](reference/mountfile.md)
* [outrage.shipped](reference/shipped.md)

## Front ends

The two callers of the library. They differ in how they name a key to a
reader, which is what [`outrage.messages`](reference/messages.md#module-outrage.messages) is for.

* [outrage.server](reference/server.md)
* [outrage.cli](reference/cli.md)
* [outrage.bulk](reference/bulk.md)

## Around the edges

Configuration, installation, and the record of what happened.

* [outrage.config](reference/config.md)
* [outrage.install](reference/install.md)
* [outrage.eventlog](reference/eventlog.md)
* [outrage.logread](reference/logread.md)
* [outrage.maintenance](reference/maintenance.md)
