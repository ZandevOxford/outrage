"""Reading a libpq service file, and the four ways doing it quietly goes wrong.

The reader is worth this much testing because everything it gets wrong is
silent. A parameter that is misspelled is a setting that never applies, and
``sslmode`` is the one where that means connecting in the clear. A relative
certificate path resolved against the wrong directory is a file that is simply
not found, later, by the driver. A password is a value that is correct
everywhere and must appear nowhere. And a lookup that reads the wrong file
connects successfully to the wrong database.

So the shape here is: the file says what libpq says it says, every problem is
reported together rather than one per run, and no output holds a secret.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from outrage import messages, pgservice
from outrage.errors import OutrageError

PLANTED = "hunter2-%(not-interpolated)s"


def write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def a_file(directory: pathlib.Path, text: str, name: str = "pg_service.conf") -> pathlib.Path:
    return write(directory / name, text)


def codes(resolution: pgservice.Resolution) -> list[str]:
    return [refusal.code for refusal in resolution.refusals]


def rendered(resolution: pgservice.Resolution) -> str:
    return " ".join(messages.render(one.as_error()) for one in resolution.refusals)


def test_an_entry_becomes_the_parameters_a_driver_is_called_with(tmp_path):
    """The whole promise, and the defaults outrage adds on top of it."""
    path = a_file(
        tmp_path,
        """
        [outrage]
        host=db.example.net
        dbname=outrage
        user=someone
        sslmode=verify-full
        """.replace("        ", ""),
    )

    found = pgservice.resolve(path).service

    assert found is not None
    assert found.name == "outrage"
    assert found.path == path
    assert found.parameters == {
        "host": "db.example.net",
        "dbname": "outrage",
        "user": "someone",
        "sslmode": "verify-full",
        "connect_timeout": "5",
        "application_name": "outrage",
    }


def test_an_entry_setting_a_default_keeps_its_own_value(tmp_path):
    """Added, not imposed: a file that says five seconds is too short wins."""
    path = a_file(tmp_path, "[outrage]\nhost=db.example.net\nconnect_timeout=30\n")

    found = pgservice.resolve(path).service

    assert found is not None
    assert found.parameters["connect_timeout"] == "30"
    assert found.parameters["application_name"] == "outrage"


def test_the_service_is_named_separately_from_the_file(tmp_path):
    path = a_file(
        tmp_path,
        "[outrage]\ndbname=mine\n\n[team]\ndbname=ours\noptions=-csearch_path=notes\n",
    )

    assert pgservice.resolve(path).service.parameters["dbname"] == "mine"
    ours = pgservice.resolve(path, "team").service
    assert ours.parameters["dbname"] == "ours"
    assert ours.parameters["options"] == "-csearch_path=notes"


# -- the secret ------------------------------------------------------------


def test_a_password_in_the_entry_reaches_the_driver_and_nothing_else(tmp_path):
    """The point of the file: the secret is in it, and it stays in it.

    ``parameters`` is what psycopg is called with, so the password has to be
    there. Everything a person or a log could see is built from ``redacted``,
    and ``repr`` is checked because that is the one that leaks by accident --
    a traceback, a log line, or a failing assertion printing the object.
    """
    path = a_file(tmp_path, f"[outrage]\nhost=db.example.net\npassword={PLANTED}\n")

    found = pgservice.resolve(path).service

    assert found.parameters["password"] == PLANTED
    assert found.redacted["password"] == pgservice.REDACTION
    assert found.redacted["host"] == "db.example.net"
    assert PLANTED not in repr(found)
    assert pgservice.REDACTION in repr(found)
    assert found.holds_secret


def test_an_entry_with_no_secret_says_so(tmp_path):
    """What `outrage check` asks before it looks at the file's permissions."""
    write(tmp_path / "client.pem", "-----BEGIN CERTIFICATE-----\n")
    path = a_file(tmp_path, "[outrage]\nhost=db.example.net\nsslcert=client.pem\n")

    assert not pgservice.resolve(path).service.holds_secret


def test_no_refusal_about_an_entry_carries_its_password(tmp_path):
    """A refusal is rendered at somebody, so the facts in it are output too."""
    path = a_file(
        tmp_path,
        f"[outrage]\nhost=db.example.net\npassword={PLANTED}\nhsot=typo\n",
    )

    refused = pgservice.resolve(path)

    assert codes(refused) == ["service-parameter-unknown"]
    assert PLANTED not in rendered(refused)
    assert PLANTED not in repr(refused.refusals)


def test_a_password_holding_a_percent_is_not_interpolated(tmp_path):
    """configparser's own default would eat this one, and quietly."""
    path = a_file(tmp_path, f"[outrage]\npassword={PLANTED}\n")

    assert pgservice.resolve(path).service.parameters["password"] == PLANTED


# -- the lookup ------------------------------------------------------------


def test_a_named_file_is_the_only_one_read(tmp_path):
    """Naming a file is saying which, so there is nothing to fall back to."""
    named = a_file(tmp_path / "named", "[other]\ndbname=x\n")
    elsewhere = a_file(tmp_path / "home", "[outrage]\ndbname=wrong\n", name=".pg_service.conf")

    refused = pgservice.resolve(named, environ={"HOME": str(elsewhere.parent)})

    assert codes(refused) == ["service-not-found"]
    assert refused.searched == (named,)


def test_a_lookup_that_found_no_file_says_so_rather_than_naming_a_section(tmp_path):
    """A service "not defined in" a file that is not there sends its reader to
    edit a file they cannot find."""
    home = tmp_path / "home"
    home.mkdir()

    refused = pgservice.resolve(environ={"PGSERVICEFILE": str(home / ".pg_service.conf")})
    said = _as_error(refused)

    assert "no PostgreSQL service file was found" in said
    assert str(home / ".pg_service.conf") in said
    assert "is defined in" not in said


def test_a_file_without_the_section_is_named_apart_from_one_that_is_not_there(tmp_path):
    personal = a_file(tmp_path, "[other]\ndbname=x\n", name=".pg_service.conf")
    system = tmp_path / "etc"

    refused = pgservice.resolve(
        environ={"PGSERVICEFILE": str(personal), pgservice.SYSCONF_VARIABLE: str(system)}
    )
    said = _as_error(refused)

    assert f"is defined in {personal}." in said
    assert f"Nothing is at {system / 'pg_service.conf'}" in said
    assert "`service=`" not in said


def _as_error(resolution: pgservice.Resolution) -> str:
    (refusal,) = resolution.refusals
    return messages.render(OutrageError(refusal.code, **dict(refusal.details)))


def test_the_default_lookup_is_the_one_libpq_does(tmp_path, monkeypatch):
    """Personal file first, then the system one, and the variable ahead of both."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()

    assert pgservice.candidates(environ={}) == (pathlib.Path.home() / pgservice.USER_FILE_NAME,)
    assert pgservice.candidates(environ={pgservice.SYSCONF_VARIABLE: "/etc/pg"}) == (
        pathlib.Path.home() / pgservice.USER_FILE_NAME,
        pathlib.Path("/etc/pg/pg_service.conf"),
    )
    assert pgservice.candidates(environ={pgservice.SERVICE_FILE_VARIABLE: "~/named.conf"}) == (
        pathlib.Path.home() / "named.conf",
    )


def test_the_system_file_answers_for_a_service_the_personal_one_lacks(tmp_path):
    personal = a_file(tmp_path / "home", "[team]\ndbname=ours\n", name=".pg_service.conf")
    a_file(tmp_path / "etc", "[outrage]\ndbname=shared\n")
    environ = {
        pgservice.SERVICE_FILE_VARIABLE: str(personal),
        pgservice.SYSCONF_VARIABLE: str(tmp_path / "etc"),
    }

    found = pgservice.resolve(environ=environ).service

    assert found.parameters["dbname"] == "shared"
    assert found.path == tmp_path / "etc" / "pg_service.conf"


def test_the_personal_file_wins_for_a_service_both_define(tmp_path):
    personal = a_file(tmp_path / "home", "[outrage]\ndbname=mine\n", name=".pg_service.conf")
    a_file(tmp_path / "etc", "[outrage]\ndbname=shared\n")
    environ = {
        pgservice.SERVICE_FILE_VARIABLE: str(personal),
        pgservice.SYSCONF_VARIABLE: str(tmp_path / "etc"),
    }

    assert pgservice.resolve(environ=environ).service.parameters["dbname"] == "mine"


def test_a_personal_file_that_is_not_there_is_not_a_failure(tmp_path):
    """Normal on a machine that uses the system file, so it is not reported."""
    a_file(tmp_path / "etc", "[outrage]\ndbname=shared\n")
    environ = {
        pgservice.SERVICE_FILE_VARIABLE: str(tmp_path / "nowhere.conf"),
        pgservice.SYSCONF_VARIABLE: str(tmp_path / "etc"),
    }

    assert pgservice.resolve(environ=environ).service.parameters["dbname"] == "shared"


def test_a_file_the_mount_named_and_that_is_not_there_is_refused(tmp_path):
    refused = pgservice.resolve(tmp_path / "nowhere.conf")

    assert codes(refused) == ["service-file-missing"]
    assert "nowhere.conf" in rendered(refused)


def test_a_service_nobody_defines_names_every_file_that_was_searched(tmp_path):
    """The refusal has to be able to say where it looked, since the lookup is
    three places and only one of them is visible in the mount."""
    personal = a_file(tmp_path / "home", "[team]\ndbname=ours\n", name=".pg_service.conf")
    environ = {
        pgservice.SERVICE_FILE_VARIABLE: str(personal),
        pgservice.SYSCONF_VARIABLE: str(tmp_path / "etc"),
    }

    refused = pgservice.resolve(environ=environ)

    said = rendered(refused)
    assert "outrage" in said
    assert str(personal) in said
    assert str(tmp_path / "etc" / "pg_service.conf") in said


def test_a_file_that_will_not_parse_stops_the_search(tmp_path):
    """Skipping on to the next file would connect somewhere nobody meant."""
    personal = a_file(tmp_path / "home", "dbname=ours\n", name=".pg_service.conf")
    a_file(tmp_path / "etc", "[outrage]\ndbname=shared\n")
    environ = {
        pgservice.SERVICE_FILE_VARIABLE: str(personal),
        pgservice.SYSCONF_VARIABLE: str(tmp_path / "etc"),
    }

    refused = pgservice.resolve(environ=environ)

    assert codes(refused) == ["service-file-malformed"]


# -- what the file may say -------------------------------------------------


def test_a_parameter_libpq_does_not_have_is_refused(tmp_path):
    path = a_file(tmp_path, "[outrage]\nhost=db.example.net\nsslmoed=verify-full\n")

    refused = pgservice.resolve(path)

    assert codes(refused) == ["service-parameter-unknown"]
    assert "sslmoed" in rendered(refused)


def test_a_parameter_in_the_wrong_case_is_refused_as_libpq_refuses_it(tmp_path):
    """configparser would lower-case it and let through what libpq will not."""
    path = a_file(tmp_path, "[outrage]\nHost=db.example.net\n")

    assert codes(pgservice.resolve(path)) == ["service-parameter-unknown"]


def test_an_entry_naming_another_service_is_refused(tmp_path):
    path = a_file(tmp_path, "[outrage]\nservice=team\n\n[team]\ndbname=ours\n")

    refused = pgservice.resolve(path)

    assert codes(refused) == ["service-entry-nested"]


def test_a_default_section_is_an_ordinary_service(tmp_path):
    """libpq has no inherited defaults, and configparser's would be invisible."""
    path = a_file(tmp_path, "[DEFAULT]\ndbname=everything\n\n[outrage]\nhost=db.example.net\n")

    found = pgservice.resolve(path).service

    assert "dbname" not in found.parameters
    assert pgservice.resolve(path, "DEFAULT").service.parameters["dbname"] == "everything"


def test_a_file_that_is_not_utf_8_is_refused_rather_than_raising(tmp_path):
    """A UnicodeDecodeError is a ValueError, so `except OSError` misses it.

    Without this the reader hands a caller a traceback where it owes them a
    configuration error, which is the one thing every refusal here is for.
    """
    path = tmp_path / "pg_service.conf"
    path.write_bytes(b"[outrage]\nuser=jos\xe9\n")

    refused = pgservice.resolve(path)

    assert codes(refused) == ["service-file-unreadable"]
    assert "utf-8" in rendered(refused)


def test_a_parameter_set_twice_is_refused_rather_than_silently_resolved(tmp_path):
    path = a_file(tmp_path, "[outrage]\ndbname=one\ndbname=two\n")

    assert codes(pgservice.resolve(path)) == ["service-file-malformed"]


def test_the_refusal_about_a_malformed_file_is_one_sentence(tmp_path):
    """configparser says where it gave up over three lines, quoting the line.

    Found by reading the output rather than by the suite: the reason landed in
    the middle of the advice and broke it across three lines.
    """
    path = a_file(tmp_path, "-----BEGIN CERTIFICATE-----\n")

    said = rendered(pgservice.resolve(path))

    assert "\n" not in said
    assert "BEGIN CERTIFICATE" in said


def test_a_comment_and_a_blank_line_are_what_they_look_like(tmp_path):
    path = a_file(
        tmp_path,
        "# the shared store\n\n[outrage]\nhost=db.example.net  # not a comment\n",
    )

    found = pgservice.resolve(path).service

    assert found.parameters["host"] == "db.example.net  # not a comment"


# -- the paths in it -------------------------------------------------------


def test_a_relative_certificate_resolves_against_the_service_file(tmp_path, monkeypatch):
    """Run from somewhere else entirely, because the working directory is what
    libpq would have used and is what a client-started server cannot rely on."""
    certificate = write(tmp_path / "conf" / "ca.pem", "-----BEGIN CERTIFICATE-----\n")
    path = a_file(tmp_path / "conf", "[outrage]\nsslrootcert=ca.pem\n")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    found = pgservice.resolve(path).service

    assert found.parameters["sslrootcert"] == str(certificate)


def test_a_certificate_that_is_not_there_is_refused_before_anything_connects(tmp_path):
    path = a_file(tmp_path, "[outrage]\nhost=db.example.net\nsslrootcert=ca.pem\n")

    refused = pgservice.resolve(path)

    assert codes(refused) == ["service-parameter-missing-file"]
    assert str(tmp_path / "ca.pem") in rendered(refused)


def test_an_absolute_certificate_is_left_where_it_is(tmp_path):
    certificate = write(tmp_path / "ca.pem", "x")
    path = a_file(tmp_path / "conf", f"[outrage]\nsslrootcert={certificate}\n")

    assert pgservice.resolve(path).service.parameters["sslrootcert"] == str(certificate)


def test_the_system_trust_store_names_no_file(tmp_path):
    """`sslrootcert=system` is libpq's way of saying the OS knows; it is not a path."""
    path = a_file(tmp_path, "[outrage]\nsslrootcert=system\n")

    found = pgservice.resolve(path).service

    assert found.parameters["sslrootcert"] == pgservice.SYSTEM_TRUST_STORE


def test_an_empty_path_parameter_is_left_alone(tmp_path):
    """libpq reads one as the parameter being unset.

    Resolving it against the file would turn `sslcert=` into the directory
    the service file is in, which is a certificate outrage invented.
    """
    path = a_file(tmp_path, "[outrage]\nsslcert=\n")

    found = pgservice.resolve(path)

    assert found.refusals == ()
    assert found.service.parameters["sslcert"] == ""


def test_a_named_passfile_that_is_not_there_is_refused(tmp_path):
    """Where outrage is stricter than libpq, which ignores one and connects
    without a password -- a typo that surfaces as an authentication failure."""
    path = a_file(tmp_path, "[outrage]\npassfile=.pgpass\n")

    assert codes(pgservice.resolve(path)) == ["service-parameter-missing-file"]


# -- every reason at once --------------------------------------------------


def test_every_problem_in_one_entry_is_reported_together(tmp_path):
    """One reason a run sends somebody round the loop once per problem."""
    path = a_file(
        tmp_path,
        "[outrage]\nhsot=db.example.net\nsslmoed=require\nsslrootcert=ca.pem\nsslkey=key.pem\n",
    )

    refused = pgservice.resolve(path)

    assert codes(refused) == [
        "service-parameter-unknown",
        "service-parameter-unknown",
        "service-parameter-missing-file",
        "service-parameter-missing-file",
    ]
    assert refused.service is None


def test_a_refused_entry_yields_no_service_at_all(tmp_path):
    path = a_file(tmp_path, "[outrage]\nhost=db.example.net\nhsot=db.example.net\n")

    assert pgservice.resolve(path).service is None


@pytest.mark.parametrize("overridable", [True, False])
def test_no_refusal_here_is_something_a_flag_can_pass(tmp_path, overridable):
    """A connection outrage was told to make wrongly is not a caller's to force."""
    path = a_file(tmp_path, "[outrage]\nhsot=db.example.net\n")

    assert all(not one.overridable for one in pgservice.resolve(path).refusals)


# -- the module itself -----------------------------------------------------


def test_the_reader_imports_no_driver():
    """It answers a question about a file, so it answers it without psycopg.

    Checked by reading the source rather than by importing, because an import
    inside a function is exactly the shape that would not show up in
    ``sys.modules`` until something called it.
    """
    source = pathlib.Path(pgservice.__file__).read_text(encoding="utf-8")
    imported = {
        node.module.split(".")[0] if isinstance(node, ast.ImportFrom) else None
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "psycopg" not in imported and "psycopg2" not in imported
