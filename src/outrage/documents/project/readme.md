# Outrage

A simple RAG (Retrieval-Augmented Generation) system for LLMs, designed to just
work with minimal setup, and provide a memory that interoperates between
coding harnesses such as Claude Code, Codex, Cursor, and Copilot CLI.

## Features

* Simple to get started with - built in initialisation configures everything.
* Hierarchical key based store of data and arbitrary metadata.
* LLM search - LLM subagents add summary and keyword metadata to documents, and
  LLM subagents can search documents and metadata.
* Multiple data stores including parquet based stores for large-scale reference
  material, and an experimental PostgreSQL store shared by several devices.
* Explicit support for command-line coding agents: Claude Code, OpenAI Codex
  CLI, Cursor Agent, and GitHub Copilot CLI.
* Command line tools for manipulating the data stores.

## Getting started

Set up a 3.12 or later Python environment.

Install outrage with:

`pip install "outrage[all]"`

That includes every optional backend and document reader. A plain
`pip install outrage` leaves them out, for an install that only ever holds
session context.

To set up a project to use Outrage, change directory to the root of the project
and run:

`outrage init`

And that's it. That will set up the MCP server, tools, skills, agents and hooks
such that when you run your LLM harness the agent will use the Outrage store
as a memory.

The server also mounts a writable user-wide store at `home`, kept in an
`.outrage` directory in your home directory.

One minor issue when using Copilot CLI: the working directory must be inside a
Git repository. Otherwise, Copilot CLI will fail to load the MCP servers and
other configuration.

## Documentation

All of it is in `src/outrage/documents`, a documentation tree written to be read
*through the store*: it ships in the wheel, and the server mounts it read-only
at the `outrage` key **by default**, so a session reads the manual with the same
tools it reads everything else with. (`--mount-docs` is the flag; it exists for
the command line, which does not mount it unasked.) It is ordinary markdown as
well, so the links below work here too.

* **[the documents](src/outrage/documents/readme.md)** - the top of that tree,
  and where to start. Keys, the command line, the tools and the conventions all
  hang off it.
* **[the design](src/outrage/documents/design.md)** - components, the key
  namespace and its grammar, what text is and how it is encoded, tool semantics
  and the SQLite schema. Decisions that are deferred or still open are recorded
  at the end. Read as `outrage/design` through the store.
* **[the implementation](src/outrage/documents/implementation.md)** - what is
  built so far and the planned build order, stage by stage. `outrage/implementation`.
* **[the API reference](src/outrage/documents/reference.md)** - a page per
  module, **generated from the docstrings** and committed. Do not edit a page
  there by hand: it is build output, and `tests/test_reference.py` fails when it
  stops matching the source.
* **[importers](src/outrage/documents/importers.md)** - turning an outside
  source into a store, starting with Wikimedia dumps. `outrage/importers`.
* **[development](src/outrage/documents/development.md)** - the development
  environment, and configuring the stores and mounts a checkout runs against.
  `outrage/development`.

## Components

* **MCP server** - Python, stdio, for local use. Exposes the store as tools.
* **Data store** - a Python library, independent of MCP so that it can be tested
  and reused on its own. One interface with five backends behind it, each
  named for how it reads, and which one a store *file* uses follows from its
  extension. **SQLite** is the read-write default: a store accumulated a
  document at a time, which is what session context and notes on a codebase
  are. Parquet files are written whole by `outrage pack` and read many times,
  for a reference base of tens of thousands of documents or more - 11× smaller
  than the same corpus in SQLite. **DuckDB** reads them, one file or many, and
  is what a `.parquet` store file opens with; **PyArrow** reads one file with
  an index held in memory, and is asked for with `type=pyarrow`. Both refuse
  writes, which is the storage rather than a setting. **Files** is a directory
  with one file per key,
  which is what `outrage export` already wrote: the tree a person edits by hand,
  readable as a store rather than only as a transfer. **PostgreSQL**,
  experimental for now, is the one store that is not on this machine:
  read-write, shared by every device that can reach the server, and asked for
  with `type=postgres`.
* **Client integrations** - packaged project skills and agents for Claude Code,
  OpenAI Codex CLI and GitHub Copilot CLI, plus a session-start hook for each.
  They cover when to store and retrieve, the key conventions, and the moment a
  skill would not be reached on its own. `outrage init` installs each client's
  files without replacing configuration it does not own.
* **Event log** - an optional JSON lines record of the requests made and the
  store accesses beneath them, for answering afterwards what a session actually
  did. Off unless `outrage config --log` or `outrage-server --log` asks for it.
* **Backup** - `outrage backup` copies the database through SQLite and checks
  what it wrote. In the library rather than the tool, because a store in WAL
  mode keeps recent writes in a sidecar file and copying the `.sqlite` alone
  yields a near-empty database that still opens cleanly. A PostgreSQL store is
  copied into a local SQLite file instead, so the backup opens with no server.

## Parquet stores

Outrage also supports read-only data stores in Parquet format, written by
`outrage pack` with pyarrow and read through DuckDB. Because those are optional
dependencies, support isn't included by default.

Install the extra to add Parquet support:

`pip install "outrage[parquet]"`

A `.parquet` store file is one packed file, or a pattern over many. A reference
base too large for one file, or that arrives in pieces, is read as Parquet parts
in any order:

`outrage-server --mount-ro ref=reference.parquet`

`outrage-server --mount-ro ref=parts/*.parquet`

`outrage-server --mount-ro ref=parts,type=duckdb`

The last reads every `.parquet` file directly inside a directory, which has no
extension to say which backend it needs. `type=pyarrow` reads a single file with
pyarrow instead, which is also what still opens a file written by `outrage`
before 0.4.0.

## A shared PostgreSQL store

**Experimental.** It works, and has been run against a local server and a
managed one on Amazon RDS, but it is new: its configuration and behaviour may
still change in a minor release, which the stable interfaces of 1.0 do not.

One store, on a server, shared by every device that can reach it - a laptop and
a desktop working from the same memory rather than from two that drift. It
needs the extra:

`pip install "outrage[postgres]"`

**The connection details are not outrage's to hold.** A mount names a libpq
[connection service
file](https://www.postgresql.org/docs/current/libpq-pgservice.html) - the
standard file `psql` and everything else that speaks libpq already read - and
an entry in it:

```ini
# ~/.pg_service.conf
[outrage]
host=db.example.com
dbname=memory
user=me
sslmode=verify-full
```

`outrage-server --mount shared=~/.pg_service.conf,type=postgres`

The file may be absolute or start with `~`, unlike every other backend's store
file, which is a name inside `--dir`: this one is a connection's configuration
rather than the store, and the standard place for it is the home directory.
Leave it out entirely - `--mount shared=,type=postgres` - for libpq's own
lookup. `service=NAME` names a different entry; the default is `outrage`.

**The store is the connection's schema**, so one database holds as many stores
as you like, each asked for with libpq's own spelling:

```ini
options=-csearch_path=memory
```

The schema and its tables are created on first open. `outrage schema status`
reports the version a store is at and what this build would do with it, and
`outrage schema create --version N` makes a blank one at a chosen version - for
a team whose oldest client is behind. A client never migrates a shared store by
opening it: it operates at the version it finds, and changing that is a command
somebody runs.

**Keep the password out of the service file.** libpq reads `~/.pgpass` on
every connection, so a line there is all a password needs, and an entry can
name another file with `passfile=`; `PGPASSWORD` works too. The file must be
readable by you alone (`chmod 600`), and a `:` or `\` in the password is
escaped with a `\`:

```text
# ~/.pgpass - host:port:database:user:password
db.example.com:5432:memory:me:the-password
```

**No password ever appears in output**, wherever it is kept: `outrage info`,
`outrage check`, `outrage schema status` and every error report name the
service, host, database, user and schema, and show any secret as
`(not shown)`.

**Verify the server, not only the encryption.** `sslmode=require` encrypts but
accepts any certificate; `verify-full` checks that the certificate names the
host and was issued by an authority you trust. Those authorities are read
from `~/.postgresql/root.crt` unless the entry names a file with
`sslrootcert` - give it an absolute path, which every libpq client reads the
same way - and `sslrootcert=system` trusts the operating system's store, which
covers a server with a public certificate. A managed server often has its own
authority instead: for **Amazon RDS** it is AWS's bundle,
`https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem`, saved
locally. Two things about RDS in particular:

* **The cluster's security group has to admit you.** A new cluster in the
  VPC's `default` group admits nothing from outside it, and a connection
  simply times out, which outrage reports as a server it cannot reach.
* **Use a password, not IAM authentication.** An IAM token lasts fifteen
  minutes and libpq cannot fetch a new one, so it would stop working at the
  first reconnect. And a password in an RDS-managed secret is rotated,
  weekly by default, which leaves every device's `.pgpass` stale: give
  outrage a login role with a password of its own.

`outrage check shared` reports the schema version, its floors and the state of
the store; `outrage backup shared` writes a consistent snapshot into a local
`.sqlite` file, which opens, mounts and checks with no server at all.

When `outrage-server` starts, a server that cannot be reached leaves that
mount unavailable and every other mount working, so a laptop off the network
still starts. A service file that cannot be read, a login the server rejects,
or a database that is not there is a mistake in the configuration and stops the
start instead. An `outrage` command is stricter: it opens every mount it is
given, and stops when one cannot be reached, even for a key in another store.
