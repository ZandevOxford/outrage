# Postgres

**Experimental.** It works, and has been run against a local server and a
managed one on Amazon RDS, but it is new: its configuration and behaviour may
still change in a minor release, which the stable interfaces of 1.0 do not.

A PostgreSQL store is one store on a server, shared by every device that can
reach it - a laptop and a desktop working from the same memory rather than two
that drift. It needs the extra:

`pip install "outrage[postgres]"`

## Connecting

**The connection details are not Outrage's to hold.** A mount names a libpq
[connection service file](https://www.postgresql.org/docs/current/libpq-pgservice.html) -
the standard file `psql` and everything else that speaks libpq already read -
and an entry in it:

```ini
# ~/.pg_service.conf
[outrage]
host=db.example.com
dbname=memory
user=me
sslmode=verify-full
```

Mount it in `mounts.toml`:

```toml
[mount]
shared = { path = "~/.pg_service.conf", type = "postgres", service = "outrage" }
```

or for one run, `--mount shared=~/.pg_service.conf,type=postgres`. Leave the
file out - `--mount shared=,type=postgres` - for libpq's own lookup.
`service=` names a different entry; the default is `outrage`.

## One database, many stores

**The store is the connection's schema**, so one database holds as many stores
as you like, each chosen with libpq's own spelling in its service entry:

```ini
options=-csearch_path=memory
```

The schema and its tables are created on first open.

**Give every device the same role.** A dry run's `checked_at` is held back to
the start of the oldest transaction open on the database, so that a write
still in flight when it looked is caught by `unchanged_since` afterwards.
PostgreSQL shows another role's transactions only to a role granted
`pg_read_all_stats`. Without that grant, a write in flight from a device
connecting as another role can pass `unchanged_since` unseen.

## Passwords

**Keep the password out of the service file.** libpq reads `~/.pgpass` on
every connection, and an entry can name another file with `passfile=`;
`PGPASSWORD` works too. The file must be readable by you alone
(`chmod 600`), and a `:` or `\` in the password is escaped with a `\`:

```text
# ~/.pgpass - host:port:database:user:password
db.example.com:5432:memory:me:the-password
```

No password ever appears in Outrage's output: `outrage info`, `outrage check`,
`outrage schema status` and every error show a secret as `(not shown)`.

## Verifying the server

`sslmode=require` encrypts but accepts any certificate; `verify-full` checks
that the certificate names the host and was issued by an authority you trust.
Those authorities are read from `~/.postgresql/root.crt` unless the entry
names a file with `sslrootcert` - give it an absolute path - and
`sslrootcert=system` trusts the operating system's store.

## Amazon RDS

* **Trust AWS's authority.** Save
  `https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem` locally
  and name it with `sslrootcert`.
* **The cluster's security group has to admit you.** A new cluster in the
  VPC's `default` group admits nothing from outside it, and a connection simply
  times out, which Outrage reports as a server it cannot reach.
* **Use a password, not IAM authentication.** An IAM token lasts fifteen
  minutes and libpq cannot fetch a new one. A password in an RDS-managed secret
  is rotated, weekly by default, leaving every device's `.pgpass` stale: give
  Outrage a login role with a password of its own.

## Schema versions

A store on one machine is migrated by whichever build opens it. A shared store
is not, since several clients of different versions may use it: a client
operates at the version it finds.

* `outrage schema status shared` reports the version, its floors and what this
  build would do on open.
* `outrage schema create --version N shared` makes a blank store at a chosen
  version, for a team whose oldest client is behind.

## Working offline

A server that cannot be reached leaves that mount unavailable and every other
mount working, so a laptop off the network still starts the server and runs
commands with the same configuration. Nothing below the mount can be read or
written until it opens again. [Mounting data stores](mounting-data-stores.md)
says how an unavailable mount behaves.

## Checking and backing up

`outrage check shared` reports the schema version, its floors and the state of
the store. `outrage backup shared` writes a consistent snapshot into a local
`.sqlite` file, which opens, mounts and checks with no server at all.
[Export and backup](export-and-backup.md).
