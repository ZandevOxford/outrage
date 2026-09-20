# outrage.pgservice

The connection details for a PostgreSQL store, read from libpq's own file.

A Postgres store is named by a host, a database, a user and whatever it takes
to authenticate, and none of that belongs in a mount table: a mount table is
committed with the project and these are per device and partly secret. libpq
already has a file for exactly this -- the **connection service file**,
`pg_service.conf` -- which is INI format and lists named connections, so a
mount names a file and a service in it rather than carrying the details
itself. Nothing here is invented: the format is libpq's and the lookup is
libpq's.

This module is the reader, and it holds **no driver import**. It answers what
the connection parameters are, which is a question about a file, and it is
worth answering without a server, without psycopg installed, and before any
socket is opened. That is also what lets every problem be reported at once.

## Why it is parsed here rather than handed to libpq

`service=` in a connection string would make libpq do all of this, and it is
not enough, for three reasons.

1. **Several mounts can name different files.** libpq's only per-process
   switch is the `PGSERVICEFILE` environment variable, and a `servicefile`
   connection parameter exists only in recent versions, which the bundled
   client library may not be.
2. **A relative certificate path should resolve against the service file.**
   libpq resolves one against the *working directory*, which a server started
   by an MCP client cannot rely on knowing.
3. **Validation can report every problem in one refusal** rather than
   stopping at whichever one libpq noticed first.

## Three deviations from libpq, all deliberate

* **A relative path parameter resolves against the directory holding the
  service file**, per the reason above, and `~` in one is expanded. libpq
  does neither.
* **A named file that is not there is refused** -- every one of
  [`PATH_PARAMETERS`](#outrage.pgservice.PATH_PARAMETERS), not only the certificates. libpq is silent about a
  missing `passfile` and simply carries on without a password, which turns a
  typo into an authentication failure much later and somewhere else.
* **The system-wide file is consulted only when \`\`PGSYSCONFDIR\`\` is set.**
  libpq knows its own compiled-in `sysconfdir` and nothing here can, short
  of running `pg_config`. Anyone relying on the system file can set the
  variable, and the refusal for a service nobody can find names every path
  that was searched, so the gap is visible rather than silent.

## Reading, and what comes back

[`resolve()`](#outrage.pgservice.resolve) is the whole surface. It returns a [`Resolution`](#outrage.pgservice.Resolution), which
carries the [`Service`](#outrage.pgservice.Service) when there is one and a
[`Refusal`](errors.md#outrage.errors.Refusal) for every reason there is not. It raises
nothing: which of those reasons are fatal, and what to do about them, is the
caller's question -- an unreachable server is tolerated at startup and a file
that will not parse is not, and neither judgement is this module's to make.

## Secrets

The point of the file is that the secret stays in it. So a password reaches
[`Service.parameters`](#outrage.pgservice.Service.parameters), which is what psycopg is called with, and reaches
nothing else: [`Service.redacted`](#outrage.pgservice.Service.redacted) is what any output is built from, and
`Service` has a `__repr__` of its own so that a traceback, a log line or
an error detail cannot print one by accident.

### outrage.pgservice.ADDED_PARAMETERS *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)]* *= {'application_name': 'outrage', 'connect_timeout': '5'}*

Parameters outrage adds when the entry sets neither. `connect_timeout`
because an MCP server that hangs at startup is a session that never
arrives, and `application_name` so that `pg_stat_activity` says who is
holding a connection.

### outrage.pgservice.CONNECTION_PARAMETERS *= frozenset({'application_name', 'channel_binding', 'client_encoding', 'connect_timeout', 'dbname', 'fallback_application_name', 'gssdelegation', 'gssencmode', 'gsslib', 'host', 'hostaddr', 'keepalives', 'keepalives_count', 'keepalives_idle', 'keepalives_interval', 'krbsrvname', 'load_balance_hosts', 'options', 'passfile', 'password', 'port', 'replication', 'require_auth', 'requirepeer', 'ssl_max_protocol_version', 'ssl_min_protocol_version', 'sslcert', 'sslcertmode', 'sslcompression', 'sslcrl', 'sslcrldir', 'sslkey', 'sslmode', 'sslnegotiation', 'sslpassword', 'sslrootcert', 'sslsni', 'target_session_attrs', 'tcp_user_timeout', 'user'})*

Every libpq connection keyword, which is exactly what a service entry may
hold. libpq refuses anything else as an invalid connection option and so do
we -- a misspelled parameter is otherwise a setting that silently does not
apply, and `sslmode` is the one where that is dangerous.

`service` is deliberately absent: an entry naming another service is what
libpq calls a nested service specification and refuses, and
[`NESTED_PARAMETER`](#outrage.pgservice.NESTED_PARAMETER) is where that is reported.

### outrage.pgservice.DEFAULT_SERVICE *= 'outrage'*

The service a mount reads when it names none. A store shared across a
person's own devices is the case this exists for, and naming it after the
project means the usual file needs one entry and the usual mount needs no
option at all.

### outrage.pgservice.NESTED_PARAMETER *= 'service'*

The parameter an entry may not set, because libpq will not follow it and
neither will this: a service entry naming a service is a loop waiting to
be written.

### outrage.pgservice.NO_DEFAULT_SECTION *= '\\x00'*

The section configparser would otherwise treat as defaults inherited by
every other one. libpq has no such notion -- `[DEFAULT]` in a service
file is a service called `DEFAULT` -- so the default section is pointed
at a name no file can hold instead of being switched off, which
configparser has no way to do.

### outrage.pgservice.PATH_PARAMETERS *= frozenset({'passfile', 'sslcert', 'sslcrl', 'sslcrldir', 'sslkey', 'sslrootcert'})*

Parameters whose value is a path, resolved against the service file and
required to exist. `sslcrldir` is a directory and the rest are files;
both are checked only for being there, because a certificate that is
unreadable or malformed is the server's answer to give, not ours.

### outrage.pgservice.REDACTION *= '(not shown)'*

What [`Service.redacted`](#outrage.pgservice.Service.redacted) puts where a secret was. Deliberately not an
empty string and not a run of asterisks: both read as a value, and this
reads as an absence.

### *class* outrage.pgservice.Resolution(service: [Service](#outrage.pgservice.Service) | [None](https://docs.python.org/3/builtins/constants.html#None) = None, refusals: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Refusal](errors.md#outrage.errors.Refusal), ...] = (), searched: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), ...] = ())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

What a lookup found: a service, or every reason there is not one.

Both halves are values because a refusal reports **every** reason it will
not proceed, and an exception cannot: raising ends the survey that found
it, so a caller repairs one thing, runs again, and meets the next.

#### service *: [Service](#outrage.pgservice.Service) | [None](https://docs.python.org/3/builtins/constants.html#None)*

The entry, when there is one. `None` whenever [`refusals`](#outrage.pgservice.Resolution.refusals) is not empty.

#### refusals *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Refusal](errors.md#outrage.errors.Refusal), ...]*

Every reason the service could not be used, reported together.

#### searched *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), ...]*

The files the lookup considered, in the order libpq would consider them.

### outrage.pgservice.SECRET_PARAMETERS *= frozenset({'password', 'sslpassword'})*

Parameter values that never reach any output. `sslpassword` is here for
the same reason `password` is: it unlocks a private key.

### outrage.pgservice.SERVICE_FILE_VARIABLE *= 'PGSERVICEFILE'*

libpq's override for the personal service file. When it is set, the file it
names is the personal one and `~/.pg_service.conf` is not consulted.

### outrage.pgservice.SYSCONF_VARIABLE *= 'PGSYSCONFDIR'*

The directory holding the system-wide service file. libpq falls back to its
compiled-in value; see the deviation in the module docstring.

### outrage.pgservice.SYSTEM_FILE_NAME *= 'pg_service.conf'*

The system-wide service file, inside [`SYSCONF_VARIABLE`](#outrage.pgservice.SYSCONF_VARIABLE)'s directory.
Named without the leading dot, as libpq spells it there.

### outrage.pgservice.SYSTEM_TRUST_STORE *= 'system'*

The value of `sslrootcert` that names no file: libpq 16 and later read
the operating system's own trust store when it is given.

### *class* outrage.pgservice.Service(name: [str](https://docs.python.org/3/builtins/stdtypes.html#str), path: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), parameters: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)])

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One service entry, validated, with paths resolved and defaults added.

[`parameters`](#outrage.pgservice.Service.parameters) is the connection keyword mapping and is what the
driver is called with. Everything a person is shown is built from
[`redacted`](#outrage.pgservice.Service.redacted) instead.

#### name *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

The service, as it is spelled in the file.

#### path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

The service file it was read from.

#### parameters *: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)]*

The connection keywords, secrets included. For the driver, not output.

#### *property* redacted *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)]*

The parameters with every secret replaced by [`REDACTION`](#outrage.pgservice.REDACTION).

The whole mapping rather than a chosen subset, so that a caller
reporting a connection has one place to take fields from and cannot
reach a secret by adding one to its list.

#### *property* holds_secret *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

Whether the entry itself carries a secret, rather than deferring it.

What `outrage check` asks before looking at the file's permissions:
a service file only other people can read is a problem when the
password is in it and not when it is in `~/.pgpass` or a key file.

### outrage.pgservice.USER_FILE_NAME *= '.pg_service.conf'*

The personal service file, in the user's home directory.

### outrage.pgservice.candidates(file: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, \*, environ: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None) → [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), ...]

The service files to search, in libpq's order.

A named `file` is the only candidate: naming one is saying which, and
falling back from it would mean reading an entry the caller did not ask
for. Otherwise it is the personal file -- [`SERVICE_FILE_VARIABLE`](#outrage.pgservice.SERVICE_FILE_VARIABLE) if
that is set, else [`USER_FILE_NAME`](#outrage.pgservice.USER_FILE_NAME) in the home directory -- and then
the system-wide file, which is only findable when
[`SYSCONF_VARIABLE`](#outrage.pgservice.SYSCONF_VARIABLE) is set.

`environ` is a parameter rather than a read of [`os.environ`](https://docs.python.org/3/library/os.html#os.environ) so
that the lookup can be tested without setting variables in the process
running the test.

### outrage.pgservice.resolve(file: [str](https://docs.python.org/3/builtins/stdtypes.html#str) | [PathLike](https://docs.python.org/3/library/os.html#os.PathLike)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None, service: [str](https://docs.python.org/3/builtins/stdtypes.html#str) = DEFAULT_SERVICE, \*, environ: [Mapping](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [str](https://docs.python.org/3/builtins/stdtypes.html#str)] | [None](https://docs.python.org/3/builtins/constants.html#None) = None) → [Resolution](#outrage.pgservice.Resolution)

Find `service` and return it, or every reason it cannot be used.

The steps are libpq's, in libpq's order: find the files, read the first
one that holds the service, then check what it holds. A file that exists
and will not parse stops the search rather than being skipped, because a
reader who silently moved on to the next file would connect somewhere the
person did not mean.

Validation is one pass over the whole entry, so an entry with a
misspelled parameter *and* a missing certificate is refused for both at
once.
