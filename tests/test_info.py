"""What a front end can say about the process it is running in."""

from __future__ import annotations

import sys

from outrage import config, eventlog, info, mounts, shipped
from outrage.eventlog import EventLog
from outrage.store_sqlite import SqliteStore


def test_a_lone_store_is_the_root_of_a_namespace_of_one(tmp_path):
    """Describing a store must not need a table built around it.

    A table refuses a root that will not take writes, so building one to
    describe a store would fail where reading that store succeeds.
    """
    with SqliteStore(tmp_path) as store:
        described = info.describe(store, directory=tmp_path)

    assert described.mounts == (
        info.MountInfo(
            mount="/",
            path=str((tmp_path / "store.sqlite").resolve()),
            kind=mounts.ROOT_KIND,
            read_only=False,
        ),
    )


def test_every_path_is_absolute_however_the_directory_was_written(tmp_path, monkeypatch):
    """The working directory a process started in is what a reader cannot recover."""
    monkeypatch.chdir(tmp_path)
    with SqliteStore(".outrage") as store:
        described = info.describe(store, directory=".outrage", mount_config=["mounts.toml"])

    assert described.directory == str((tmp_path / ".outrage").resolve())
    assert described.mount_config == (str((tmp_path / "mounts.toml").resolve()),)
    assert described.mounts[0].path == str((tmp_path / ".outrage" / "store.sqlite").resolve())


def test_the_interpreter_is_not_resolved_through_its_symlinks(tmp_path, monkeypatch):
    """A virtual environment's python links to the one it was made from.

    Resolving it would name the environment a caller must *not* use, which is
    the opposite of what reporting it is for.
    """
    link = tmp_path / "python"
    link.symlink_to(sys.executable)
    monkeypatch.setattr(sys, "executable", str(link))

    with SqliteStore(tmp_path) as store:
        described = info.describe(store)

    assert described.python == str(link)


def test_no_console_script_is_reported_as_no_command(tmp_path, monkeypatch):
    """`python -m outrage` is the server, so there is no second spelling to offer."""
    monkeypatch.setattr(config, "script_command", lambda *args, **kwargs: None)

    with SqliteStore(tmp_path) as store:
        described = info.describe(store)

    assert described.command == ()


def test_a_store_directory_is_not_guessed_at(tmp_path):
    with SqliteStore(tmp_path) as store:
        described = info.describe(store)

    assert described.directory is None


def test_the_log_is_this_process_and_nothing_is_claimed_without_one(tmp_path):
    with SqliteStore(tmp_path) as store:
        assert info.describe(store).log is None
        assert info.describe(store, log=eventlog.NULL).log_content is None

        log = EventLog(tmp_path / "log.jsonl", content="full")
        try:
            described = info.describe(store, log=log)
        finally:
            log.close()

    assert described.log == str((tmp_path / "log.jsonl").resolve())
    assert described.log_content == "full"


def test_a_mount_is_described_as_it_was_opened(tmp_path):
    """Including one nobody named: the shipped documentation is lent to the table."""
    with SqliteStore(tmp_path, filename="ref.sqlite") as reference:
        reference.store_document("asyncio", "the reference")
    with mounts.open_mounts(
        tmp_path, read_only_specs=["ref=ref.sqlite"], attached=shipped.attached()
    ) as table:
        described = info.describe(table, directory=tmp_path)

    by_point = {mount.mount: mount for mount in described.mounts}
    assert by_point["ref"].kind == mounts.READ_ONLY_MOUNT_KIND
    assert by_point["ref"].read_only is True
    assert by_point["/"].kind == mounts.ROOT_KIND
    assert by_point[shipped.MOUNT_POINT].path == str(shipped.tree().resolve())
