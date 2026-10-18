# Importing documents

A store fills up a document at a time as agents work, but reference material
usually already exists somewhere: a directory of notes, a documentation
bundle, a pile of PDFs. This guide covers the ways to get it in, and how to
make it worth searching once it is there.

## Importing a directory

`outrage import DIRECTORY [key]`

stores every file under `DIRECTORY` as a document, beneath `key` or at the top
level. A path becomes a key: `notes/design.md` is stored at `notes/design`. A
`.md` or `.json` extension is stripped and read as the format; any other file
name is kept whole, so `src/myfile.py` is stored at the key `src/myfile.py`.

```text
outrage import ./manuals reference/manuals --dry-run
outrage import ./manuals reference/manuals
```

* **Nothing already stored is replaced** by default. `--on-conflict overwrite`
  replaces it, and `--on-conflict stop` stops at the first clash.
* `--dry-run` reports what would be stored without storing it.
* Files and directories whose names begin with a dot are skipped unless
  `--hidden` is given.
* A file named `!title.md` beside a document's directory becomes that
  document's title, which is how `outrage export` writes metadata, so an
  export imports back where it came from.
  [Export and backup](export-and-backup.md).

**Keep extensions for a bundle that links by file name.** Documentation whose
pages link to each other as `guide.md` keeps working only if the key is the
whole file name. Pass `--extensions keep`, and `notes.md` is stored at the key
`notes.md`.

## Converting PDFs and office documents

`outrage ingest SOURCE KEY` converts one local file to Markdown with
MarkItDown and stores it as one document:

`outrage ingest ./specs/protocol.pdf reference/protocol`

It reads PDF, Word, PowerPoint and Excel files, and needs the `documents`
extra: `pip install "outrage[documents]"`. The title comes from `--title`,
then the converted document, then the file name. An existing document is kept
unless `--overwrite` is given.

The same conversion is the `ingest_document` MCP tool, so an agent can be
asked to bring a file in itself. It reads only regular files on the server's
machine: URLs are refused, and converter plugins and remote services are not
enabled.

## Mounting files instead of importing them

A directory does not have to be copied in to be read. Mounted as a **file
store**, it is a store in its own right:

```toml
[mount]
manuals = { path = "manuals", type = "files" }
```

or for one run, `--mount manuals=manuals,type=files`. Each file is a document
under the same mapping `import` uses. Writes go back to the files, so a
person can keep editing them with any editor while sessions read them. The
path is relative to the store directory, like every other mount.
[Mounting data stores](mounting-data-stores.md).

Mount it read-only, with `[mount-ro]` or `--mount-ro`, when the directory
belongs to something else. A file store can also be the starting point for an
import: mount it, check what it holds with `outrage ls`, then copy what you
want into the main store with `outrage copy` or the `copy_tree` tool.

## Getting an agent to write documents

An agent can write documents directly with `store_document`, and this is
often the best import of all: ask it to read a codebase, a design discussion
or a set of files, and write up what it finds as documents under a key you
choose. Some ways to ask:

* *"Read the files in `docs/` and store a summary of each under
  `reference/docs/<name>`, with a title."*
* *"Store what we decided about the schema as `plans/schema`."*
* *"Split this document into one document per section under
  `reference/protocol/`, and leave an index at `reference/protocol`."*

The project's `readme` says where things belong, so an agent that has read it
will usually choose sensible keys itself.

## Making documents findable

Whichever way documents arrive, a session finds them through metadata first:
a title survey, then summaries. A document without a title appears in a survey
only as a count.

* **Titles and contents.** `make_metadata` writes a title parsed from a
  document's first heading and a `!contents` index of its headings, which lets
  a long document be read a section at a time. `outrage make_contents` does
  the contents from the command line.
* **Summaries.** The packaged `outrage-backfill` agent finds every document
  under a key that lacks a `!summary` and writes one for each, one
  `outrage-annotate` agent per document. Ask for it by name: *"backfill
  summaries under `reference/manuals`"*.
* `keys_missing_meta` lists what still lacks a title or summary.

Good titles and summaries also make [smart search](smart-search.md) cheaper
and more accurate.

## Building a Parquet store

For a large reference base - tens of thousands of documents or more - pack
the material into a read-only Parquet store instead of importing it into the
project store. It is much smaller and quicker to search, and it keeps the
reference material apart from the project's own memory.

The usual way is to import and annotate into a separate SQLite store, then
pack that:

```text
outrage import ./manuals --store staging.sqlite --no-mount-config
outrage pack .outrage/reference.parquet --from-store staging.sqlite
```

Titles, summaries and other metadata come across with the documents. Or pack
a directory directly:

`outrage pack .outrage/reference.parquet --from-dir ./manuals`

Then mount the result read-only, as `--mount-ro ref=reference.parquet`: a
mount is relative to the store directory, `.outrage/`, while the file `pack`
writes is a path from the working directory.
[Parquet stores](parquet-stores.md) has the rest, including stores in
several parts.

## Reference

* [Command line](../cli.md) - `import`, `ingest`, `make_contents`, `copy` and
  `pack` in full.
* [Tools](../tools.md) - `ingest_document`, `store_document`, `make_metadata`
  and `copy_tree`.
* [Importers](../importers.md) - separate tools that turn an outside source,
  such as a Wikipedia dump, into a store.
