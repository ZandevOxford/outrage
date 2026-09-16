"""Tests for the error log, which exists for a reader who is not there yet.

Its whole reason to be separate from the event log is that it is on when
nothing asked for it, so the first test below is the one that matters: a server
given no ``--log`` at all still leaves the reason it would not start. The rest
guard the two properties that make it safe to have always on -- it can never
break a startup, and it cannot grow without bound.

`issues/9` is what asked for it; `plans/startup-error-log` is the design.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from outrage import errorlog
from outrage.errors import OutrageError
from outrage.mounts import MountError

REPO = Path(__file__).resolve().parent.parent


def records(directory: Path) -> list[dict]:
    """Every record in the error log, as a reader afterwards would find it."""
    file = errorlog.path_for(directory)
    if not file.exists():
        return []
    return [json.loads(line) for line in file.read_text().splitlines() if line.strip()]


def test_an_outrage_error_records_its_code(tmp_path):
    errorlog.record(tmp_path, "start", MountError("mount-duplicate", mount="a"), message="said")

    (entry,) = records(tmp_path)
    assert entry["event"] == "start"
    assert entry["code"] == "mount-duplicate"
    assert entry["message"] == "said"
    assert "traceback" not in entry, "an OutrageError is an answer, not a bug"


def test_anything_else_records_its_traceback(tmp_path):
    """The reason the file holds more than the sentence stderr already had."""
    try:
        raise RuntimeError("the inside of a bug")
    except RuntimeError as exc:
        errorlog.record(tmp_path, "start", exc)

    (entry,) = records(tmp_path)
    assert entry["error"] == "RuntimeError"
    assert "the inside of a bug" in entry["traceback"]
    assert "test_anything_else_records_its_traceback" in entry["traceback"]
    assert "code" not in entry


def test_the_file_is_not_world_readable(tmp_path):
    """0600, the rule the event log follows: it carries absolute paths."""
    errorlog.record(tmp_path, "start", MountError("mount-duplicate", mount="a"))

    mode = errorlog.path_for(tmp_path).stat().st_mode
    assert not mode & stat.S_IRGRP
    assert not mode & stat.S_IROTH


def test_a_failure_to_write_does_not_raise(tmp_path, capsys):
    """The trade the event log states: an unrecorded failure beats a dead server.

    A directory where the file should be is the simplest way to make every
    write fail without making the path itself invalid.
    """
    errorlog.path_for(tmp_path).mkdir()

    errorlog.record(tmp_path, "start", MountError("mount-duplicate", mount="a"))

    assert "could not record" in capsys.readouterr().err


def test_the_message_is_not_composed_here(tmp_path):
    """Rendering belongs to `messages`, which knows which front end is asking."""
    errorlog.record(tmp_path, "start", MountError("mount-duplicate", mount="a"))

    (entry,) = records(tmp_path)
    assert "message" not in entry


def test_the_cap_drops_the_oldest_and_keeps_whole_records(tmp_path):
    for n in range(200):
        errorlog.record(tmp_path, "start", None, cap=2000, n=n)

    kept = records(tmp_path)
    # One record over the cap, because the ceiling is on what is already there
    # when a record arrives: trimming after the write could drop the newest.
    assert 2000 < errorlog.path_for(tmp_path).stat().st_size <= 2000 + 200
    # Whole records, newest kept: a reader never meets half a line, and what
    # survives is what was most recently worth recording.
    assert kept, "the trim kept nothing at all"
    assert [entry["n"] for entry in kept] == sorted(entry["n"] for entry in kept)
    assert kept[-1]["n"] == 199


def test_a_cap_of_zero_never_trims(tmp_path):
    """`cap=0` is off, not "keep nothing" -- the accident worth naming."""
    for n in range(20):
        errorlog.record(tmp_path, "start", None, cap=0, n=n)

    assert len(records(tmp_path)) == 20


def test_tail_splits_on_record_boundaries():
    data = b'{"n": 1}\n{"n": 2}\n{"n": 3}\n'
    assert errorlog._tail(data, 18) == b'{"n": 2}\n{"n": 3}\n'
    assert errorlog._tail(data, 8) == b""


@pytest.mark.parametrize("logging", [False, True])
def test_a_real_server_records_why_it_would_not_start(tmp_path, logging):
    """The whole point, driven as a client would drive it.

    Parametrised over ``--log`` to say the thing the design turns on: the error
    log is not a view of the event log, so it is there either way.
    """
    argv = [
        sys.executable,
        "-m",
        "outrage",
        "--dir",
        str(tmp_path),
        "--mount",
        "b=x.sqlite,type=nonsense",
    ]
    if logging:
        argv.append("--log")

    result = subprocess.run(argv, input="", capture_output=True, text=True, cwd=REPO)

    assert result.returncode == 1
    (entry,) = records(tmp_path)
    assert entry["code"] == "backend-unknown"
    assert entry["event"] == "run"
    assert entry["pid"] != os.getpid()


def test_a_configuration_that_will_not_parse_is_recorded(tmp_path):
    """The case with no directory answered yet, so the environment names one."""
    config = tmp_path / "bad.toml"
    config.write_text("this is not = = toml\n")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "outrage",
            "--dir",
            str(tmp_path),
            "--mount-config",
            str(config),
        ],
        input="",
        capture_output=True,
        text=True,
        cwd=REPO,
        env={**os.environ, "OUTRAGE_DIR": str(tmp_path)},
    )

    assert result.returncode == 1
    (entry,) = records(tmp_path)
    assert entry["event"] == "parse-args"
    assert entry["code"] == "mount-config-not-toml"


def test_a_server_that_starts_records_nothing(tmp_path):
    """A file that fills up with successes is one nobody reads."""
    result = subprocess.run(
        [sys.executable, "-m", "outrage", "--dir", str(tmp_path)],
        input="",
        capture_output=True,
        text=True,
        cwd=REPO,
    )

    assert result.returncode == 0
    assert records(tmp_path) == []


def test_record_takes_any_outrage_error(tmp_path):
    """`code` comes off the base class, not off any one error type."""

    class Odd(OutrageError):
        pass

    errorlog.record(tmp_path, "start", Odd("some-code"))

    (entry,) = records(tmp_path)
    assert entry["code"] == "some-code"
