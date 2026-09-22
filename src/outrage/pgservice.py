"""The connection details for a PostgreSQL store, read from libpq's own file.

A Postgres store is named by a host, a database, a user and whatever it takes
to authenticate, and none of that belongs in a mount table: a mount table is
committed with the project and these are per device and partly secret. libpq
already has a file for exactly this -- the **connection service file**,
``pg_service.conf`` -- which is INI format and lists named connections, so a
mount names a file and a service in it rather than carrying the details
itself. Nothing here is invented: the format is libpq's and the lookup is
libpq's.

This module is the reader, and it holds **no driver import**. It answers what
the connection parameters are, which is a question about a file, and it is
worth answering without a server, without psycopg installed, and before any
socket is opened. That is also what lets every problem be reported at once.

## Why it is parsed here rather than handed to libpq

``service=`` in a connection string would make libpq do all of this, and it is
not enough, for three reasons.

1. **Several mounts can name different files.** libpq's only per-process
   switch is the ``PGSERVICEFILE`` environment variable, and a ``servicefile``
   connection parameter exists only in recent versions, which the bundled
   client library may not be.
2. **A relative certificate path should resolve against the service file.**
   libpq resolves one against the *working directory*, which a server started
   by an MCP client cannot rely on knowing.
3. **Validation can report every problem in one refusal** rather than
   stopping at whichever one libpq noticed first.

## Three deviations from libpq, all deliberate

* **A relative path parameter resolves against the directory holding the
  service file**, per the reason above, and ``~`` in one is expanded. libpq
  does neither.
* **A named file that is not there is refused** -- every one of
  :data:`PATH_PARAMETERS`, not only the certificates. libpq is silent about a
  missing ``passfile`` and simply carries on without a password, which turns a
  typo into an authentication failure much later and somewhere else.
* **The system-wide file is consulted only when ``PGSYSCONFDIR`` is set.**
  libpq knows its own compiled-in ``sysconfdir`` and nothing here can, short
  of running ``pg_config``. Anyone relying on the system file can set the
  variable, and the refusal for a service nobody can find names every path
  that was searched, so the gap is visible rather than silent.

## Reading, and what comes back

:func:`resolve` is the whole surface. It returns a :class:`Resolution`, which
carries the :class:`Service` when there is one and a
:class:`~outrage.errors.Refusal` for every reason there is not. It raises
nothing: which of those reasons are fatal, and what to do about them, is the
caller's question -- an unreachable server is tolerated at startup and a file
that will not parse is not, and neither judgement is this module's to make.

## Secrets

The point of the file is that the secret stays in it. So a password reaches
:attr:`Service.parameters`, which is what psycopg is called with, and reaches
nothing else: :attr:`Service.redacted` is what any output is built from, and
``Service`` has a ``__repr__`` of its own so that a traceback, a log line or
an error detail cannot print one by accident.
"""

from __future__ import annotations

import configparser
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .errors import Refusal

#: The service a mount reads when it names none. A store shared across a
#: person's own devices is the case this exists for, and naming it after the
#: project means the usual file needs one entry and the usual mount needs no
#: option at all.
DEFAULT_SERVICE = "outrage"

#: libpq's override for the personal service file. When it is set, the file it
#: names is the personal one and ``~/.pg_service.conf`` is not consulted.
SERVICE_FILE_VARIABLE = "PGSERVICEFILE"

#: The directory holding the system-wide service file. libpq falls back to its
#: compiled-in value; see the deviation in the module docstring.
SYSCONF_VARIABLE = "PGSYSCONFDIR"

#: The personal service file, in the user's home directory.
USER_FILE_NAME = ".pg_service.conf"

#: The system-wide service file, inside :data:`SYSCONF_VARIABLE`'s directory.
#: Named without the leading dot, as libpq spells it there.
SYSTEM_FILE_NAME = "pg_service.conf"

#: Parameters outrage adds when the entry sets neither. ``connect_timeout``
#: because an MCP server that hangs at startup is a session that never
#: arrives, and ``application_name`` so that ``pg_stat_activity`` says who is
#: holding a connection.
ADDED_PARAMETERS: Mapping[str, str] = {"connect_timeout": "5", "application_name": "outrage"}

#: Parameter values that never reach any output. ``sslpassword`` is here for
#: the same reason ``password`` is: it unlocks a private key.
SECRET_PARAMETERS = frozenset({"password", "sslpassword"})

#: What :attr:`Service.redacted` puts where a secret was. Deliberately not an
#: empty string and not a run of asterisks: both read as a value, and this
#: reads as an absence.
REDACTION = "(not shown)"

#: Parameters whose value is a path, resolved against the service file and
#: required to exist. ``sslcrldir`` is a directory and the rest are files;
#: both are checked only for being there, because a certificate that is
#: unreadable or malformed is the server's answer to give, not ours.
PATH_PARAMETERS = frozenset({"passfile", "sslcert", "sslcrl", "sslcrldir", "sslkey", "sslrootcert"})

#: The value of ``sslrootcert`` that names no file: libpq 16 and later read
#: the operating system's own trust store when it is given.
SYSTEM_TRUST_STORE = "system"

#: Every libpq connection keyword, which is exactly what a service entry may
#: hold. libpq refuses anything else as an invalid connection option and so do
#: we -- a misspelled parameter is otherwise a setting that silently does not
#: apply, and ``sslmode`` is the one where that is dangerous.
#:
#: ``service`` is deliberately absent: an entry naming another service is what
#: libpq calls a nested service specification and refuses, and
#: :data:`NESTED_PARAMETER` is where that is reported.
CONNECTION_PARAMETERS = frozenset(
    {
        "application_name",
        "channel_binding",
        "client_encoding",
        "connect_timeout",
        "dbname",
        "fallback_application_name",
        "gssdelegation",
        "gssencmode",
        "gsslib",
        "host",
        "hostaddr",
        "keepalives",
        "keepalives_count",
        "keepalives_idle",
        "keepalives_interval",
        "krbsrvname",
        "load_balance_hosts",
        "options",
        "passfile",
        "password",
        "port",
        "replication",
        "require_auth",
        "requirepeer",
        "ssl_max_protocol_version",
        "ssl_min_protocol_version",
        "sslcert",
        "sslcertmode",
        "sslcompression",
        "sslcrl",
        "sslcrldir",
        "sslkey",
        "sslmode",
        "sslnegotiation",
        "sslpassword",
        "sslrootcert",
        "sslsni",
        "target_session_attrs",
        "tcp_user_timeout",
        "user",
    }
)

#: The parameter an entry may not set, because libpq will not follow it and
#: neither will this: a service entry naming a service is a loop waiting to
#: be written.
NESTED_PARAMETER = "service"

#: The section configparser would otherwise treat as defaults inherited by
#: every other one. libpq has no such notion -- ``[DEFAULT]`` in a service
#: file is a service called ``DEFAULT`` -- so the default section is pointed
#: at a name no file can hold instead of being switched off, which
#: configparser has no way to do.
NO_DEFAULT_SECTION = "\x00"


@dataclass(frozen=True, slots=True, repr=False)
class Service:
    """One service entry, validated, with paths resolved and defaults added.

    :attr:`parameters` is the connection keyword mapping and is what the
    driver is called with. Everything a person is shown is built from
    :attr:`redacted` instead.
    """

    name: str
    """The service, as it is spelled in the file."""

    path: Path
    """The service file it was read from."""

    parameters: Mapping[str, str]
    """The connection keywords, secrets included. For the driver, not output."""

    @property
    def redacted(self) -> dict[str, str]:
        """The parameters with every secret replaced by :data:`REDACTION`.

        The whole mapping rather than a chosen subset, so that a caller
        reporting a connection has one place to take fields from and cannot
        reach a secret by adding one to its list.
        """
        return {
            key: REDACTION if key in SECRET_PARAMETERS else value
            for key, value in self.parameters.items()
        }

    @property
    def holds_secret(self) -> bool:
        """Whether the entry itself carries a secret, rather than deferring it.

        What ``outrage check`` asks before looking at the file's permissions:
        a service file only other people can read is a problem when the
        password is in it and not when it is in ``~/.pgpass`` or a key file.
        """
        return any(key in SECRET_PARAMETERS for key in self.parameters)

    def __repr__(self) -> str:
        """Built from :attr:`redacted`, so no rendering of this can leak.

        A generated ``__repr__`` would print the password into any traceback,
        log line or test failure that touched one of these, which is a way of
        losing a secret that nobody would think to look for.
        """
        inside = ", ".join(f"{key}={value!r}" for key, value in self.redacted.items())
        return f"Service(name={self.name!r}, path={str(self.path)!r}, {inside})"


@dataclass(frozen=True, slots=True)
class Resolution:
    """What a lookup found: a service, or every reason there is not one.

    Both halves are values because a refusal reports **every** reason it will
    not proceed, and an exception cannot: raising ends the survey that found
    it, so a caller repairs one thing, runs again, and meets the next.
    """

    service: Service | None = None
    """The entry, when there is one. ``None`` whenever :attr:`refusals` is not empty."""

    refusals: tuple[Refusal, ...] = ()
    """Every reason the service could not be used, reported together."""

    searched: tuple[Path, ...] = ()
    """The files the lookup considered, in the order libpq would consider them."""


def candidates(
    file: str | os.PathLike[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> tuple[Path, ...]:
    """The service files to search, in libpq's order.

    A named ``file`` is the only candidate: naming one is saying which, and
    falling back from it would mean reading an entry the caller did not ask
    for. Otherwise it is the personal file -- :data:`SERVICE_FILE_VARIABLE` if
    that is set, else :data:`USER_FILE_NAME` in the home directory -- and then
    the system-wide file, which is only findable when
    :data:`SYSCONF_VARIABLE` is set.

    ``environ`` is a parameter rather than a read of :data:`os.environ` so
    that the lookup can be tested without setting variables in the process
    running the test.
    """
    if file is not None:
        return (Path(file).expanduser(),)

    seen = os.environ if environ is None else environ
    named = seen.get(SERVICE_FILE_VARIABLE)
    personal = Path(named).expanduser() if named else Path.home() / USER_FILE_NAME

    sysconfdir = seen.get(SYSCONF_VARIABLE)
    if not sysconfdir:
        return (personal,)
    return (personal, Path(sysconfdir).expanduser() / SYSTEM_FILE_NAME)


def resolve(
    file: str | os.PathLike[str] | None = None,
    service: str = DEFAULT_SERVICE,
    *,
    environ: Mapping[str, str] | None = None,
) -> Resolution:
    """Find ``service`` and return it, or every reason it cannot be used.

    The steps are libpq's, in libpq's order: find the files, read the first
    one that holds the service, then check what it holds. A file that exists
    and will not parse stops the search rather than being skipped, because a
    reader who silently moved on to the next file would connect somewhere the
    person did not mean.

    Validation is one pass over the whole entry, so an entry with a
    misspelled parameter *and* a missing certificate is refused for both at
    once.
    """
    searched = candidates(file, environ=environ)
    named = file is not None
    # Kept apart from `searched` for the refusal's sake: a service "not
    # defined in" a file that is not there reads as a file missing a section,
    # and sends its reader to edit something they cannot find.
    missing: list[Path] = []

    for path in searched:
        parsed, refusals = _parse(path, named=named)
        if refusals:
            return Resolution(refusals=tuple(refusals), searched=searched)
        if parsed is None:
            missing.append(path)
            continue
        if not parsed.has_section(service):
            continue
        return _entry(path, service, parsed[service], searched)

    return Resolution(
        refusals=(
            Refusal(
                "service-not-found",
                overridable=False,
                service=service,
                searched=[str(one) for one in searched],
                missing=[str(one) for one in missing],
            ),
        ),
        searched=searched,
    )


def _parse(path: Path, *, named: bool) -> tuple[configparser.RawConfigParser | None, list[Refusal]]:
    """Read one candidate file, or say why it could not be read.

    ``None`` with no refusals means the file is not there, which is only a
    problem when the caller named it: the personal file is routinely absent on
    a machine that uses the system one, and libpq treats that as nothing
    happening rather than as an error.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        if named:
            return None, [Refusal("service-file-missing", overridable=False, path=str(path))]
        return None, []
    # A UnicodeDecodeError is a ValueError rather than an OSError, so it is
    # named here: without it a file holding one stray byte reaches a caller as
    # a traceback instead of as the configuration error it is.
    except (OSError, UnicodeDecodeError) as exc:
        return None, [
            Refusal("service-file-unreadable", overridable=False, path=str(path), reason=str(exc))
        ]

    parser = configparser.RawConfigParser(
        default_section=NO_DEFAULT_SECTION,
        delimiters=("=",),
        comment_prefixes=("#",),
        inline_comment_prefixes=None,
        empty_lines_in_values=False,
        interpolation=None,
    )
    # libpq compares a keyword exactly, so lowercasing here would accept a
    # `Host=` that libpq itself would refuse as an invalid connection option.
    parser.optionxform = str  # type: ignore[method-assign]
    try:
        parser.read_string(text, source=str(path))
    except configparser.Error as exc:
        return None, [
            Refusal("service-file-malformed", overridable=False, path=str(path), reason=str(exc))
        ]
    return parser, []


def _entry(
    path: Path,
    service: str,
    section: Mapping[str, str],
    searched: tuple[Path, ...],
) -> Resolution:
    """Check one entry and build the parameters a driver is called with."""
    refusals: list[Refusal] = []
    parameters: dict[str, str] = {}

    for parameter, value in section.items():
        if parameter == NESTED_PARAMETER:
            refusals.append(
                Refusal("service-entry-nested", overridable=False, service=service, path=str(path))
            )
            continue
        if parameter not in CONNECTION_PARAMETERS:
            refusals.append(
                Refusal(
                    "service-parameter-unknown",
                    overridable=False,
                    service=service,
                    path=str(path),
                    parameter=parameter,
                )
            )
            continue
        parameters[parameter] = value

    for parameter in sorted(PATH_PARAMETERS & set(parameters)):
        resolved, missing = _at(path, parameter, parameters[parameter])
        parameters[parameter] = resolved
        if missing:
            refusals.append(
                Refusal(
                    "service-parameter-missing-file",
                    overridable=False,
                    service=service,
                    path=str(path),
                    parameter=parameter,
                    file=resolved,
                )
            )

    if refusals:
        return Resolution(refusals=tuple(refusals), searched=searched)

    for parameter, value in ADDED_PARAMETERS.items():
        parameters.setdefault(parameter, value)

    return Resolution(
        service=Service(name=service, path=path, parameters=parameters),
        searched=searched,
    )


def _at(path: Path, parameter: str, value: str) -> tuple[str, bool]:
    """A path parameter resolved against the service file, and whether it is there.

    ``sslrootcert=system`` names the operating system's trust store rather
    than a file, so it is passed through untouched and asked nothing about.
    An empty value is untouched for the same reason: libpq reads one as the
    parameter being unset, and resolving it would turn it into the directory
    the service file is in.
    """
    if not value:
        return value, False
    if parameter == "sslrootcert" and value == SYSTEM_TRUST_STORE:
        return value, False
    resolved = Path(value).expanduser()
    if not resolved.is_absolute():
        resolved = path.parent / resolved
    return str(resolved), not resolved.exists()


__all__ = [
    "ADDED_PARAMETERS",
    "CONNECTION_PARAMETERS",
    "DEFAULT_SERVICE",
    "NESTED_PARAMETER",
    "NO_DEFAULT_SECTION",
    "PATH_PARAMETERS",
    "REDACTION",
    "Resolution",
    "SECRET_PARAMETERS",
    "SERVICE_FILE_VARIABLE",
    "SYSCONF_VARIABLE",
    "SYSTEM_FILE_NAME",
    "SYSTEM_TRUST_STORE",
    "Service",
    "USER_FILE_NAME",
    "candidates",
    "resolve",
]
