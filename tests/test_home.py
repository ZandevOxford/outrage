"""The writable built-in store shared across projects."""

import concurrent.futures
import json
import os
from pathlib import Path

import pytest

from outrage import home, messages
from outrage.eventlog import EventLog
from outrage.store_sqlite import SqliteStore


def fake_home(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))


def test_the_path_is_user_wide_and_not_the_project_store(monkeypatch, tmp_path):
    fake_home(monkeypatch, tmp_path)
    monkeypatch.setenv("OUTRAGE_DIR", str(tmp_path / "project"))

    assert home.path() == tmp_path / ".outrage" / "home.sqlite"


def test_a_new_home_store_gets_the_exact_shipped_readme(monkeypatch, tmp_path):
    fake_home(monkeypatch, tmp_path)

    with home.open_store() as opened:
        assert opened.retrieve_document(home.README_KEY).content == home.readme()
        assert opened.retrieve_document("readme/!title").content == home.README_TITLE


def test_a_custom_readme_is_never_replaced(monkeypatch, tmp_path):
    fake_home(monkeypatch, tmp_path)
    database = home.path()
    with SqliteStore(database.parent, filename=database.name) as opened:
        opened.store_document("readme", "mine", title="Mine")

    with home.open_store() as reopened:
        assert reopened.retrieve_document("readme").content == "mine"
        assert reopened.retrieve_document("readme/!title").content == "Mine"


def test_a_nonempty_store_without_a_readme_is_left_alone(monkeypatch, tmp_path):
    fake_home(monkeypatch, tmp_path)
    database = home.path()
    with SqliteStore(database.parent, filename=database.name) as opened:
        opened.store_document("kept", "content")

    with home.open_store() as reopened:
        assert not reopened.exists("readme")
        assert reopened.retrieve_document("kept").content == "content"


def test_a_deliberately_emptied_store_is_seeded_again(monkeypatch, tmp_path):
    fake_home(monkeypatch, tmp_path)
    with home.open_store() as opened:
        opened.delete("readme")
        assert opened.get_documents(limit=1).total == 0

    with home.open_store() as reopened:
        assert reopened.retrieve_document("readme").content == home.readme()


def test_concurrent_first_opens_converge_on_one_bootstrap(monkeypatch, tmp_path):
    fake_home(monkeypatch, tmp_path)

    def open_and_read():
        with home.open_store() as opened:
            return opened.retrieve_document("readme").content

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        contents = list(pool.map(lambda _: open_and_read(), range(16)))

    assert contents == [home.readme()] * 16


def test_the_home_store_inherits_versioning_and_logs_outward_keys(monkeypatch, tmp_path):
    fake_home(monkeypatch, tmp_path)
    log = EventLog(tmp_path / "events.jsonl")

    with home.open_store(log=log, versioning=False) as opened:
        assert opened.versioning is False
        opened.store_document("shared", "global")
    log.close()

    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    writes = [event["args"]["key"] for event in events if event.get("op") == "store_document"]
    assert writes == ["home/readme", "home/shared"]


def test_an_open_failure_names_the_global_path_and_the_off_switch(monkeypatch, tmp_path):
    fake_home(monkeypatch, tmp_path)

    def refused(*args, **kwargs):
        raise PermissionError("not permitted")

    monkeypatch.setattr(home, "SqliteStore", refused)
    with pytest.raises(home.HomeStoreError) as raised:
        home.open_store()

    said = messages.render(raised.value)
    assert str(home.path()) in said
    assert "not permitted" in said
    assert "--unmount home" in said


def _config(tmp_path, text, mode=0o600):
    path = tmp_path / "config.toml"
    path.write_text(text, encoding="utf-8")
    path.chmod(mode)
    return path


def test_the_config_file_sits_beside_the_home_store(monkeypatch, tmp_path):
    fake_home(monkeypatch, tmp_path)

    assert home.config_path() == tmp_path / ".outrage" / "config.toml"


def test_no_config_file_is_an_empty_configuration(tmp_path):
    assert home.read_config(tmp_path / "config.toml") == {}


def test_a_private_config_file_is_read(tmp_path):
    path = _config(tmp_path, '[smart_search]\nmodel = "jev-1"\n')

    assert home.read_config(path) == {"smart_search": {"model": "jev-1"}}


@pytest.mark.skipif(os.name != "posix", reason="mode bits are POSIX")
@pytest.mark.parametrize("mode", [0o644, 0o640, 0o604, 0o620, 0o602, 0o610])
def test_a_config_file_others_can_open_is_refused_unread(tmp_path, mode):
    path = _config(tmp_path, "not toml at all [", mode)

    with pytest.raises(home.UserConfigError) as raised:
        home.read_config(path)
    assert raised.value.code == "user-config-exposed"
    assert raised.value.details["mode"] == f"{mode:o}"
    assert "chmod 600" in messages.render(raised.value)


def test_a_config_file_that_is_not_toml_is_refused(tmp_path):
    path = _config(tmp_path, "key = \n")

    with pytest.raises(home.UserConfigError) as raised:
        home.read_config(path)
    assert raised.value.code == "user-config-not-toml"
    assert str(path) in messages.render(raised.value)


def test_a_config_path_that_is_a_directory_is_unreadable(tmp_path):
    path = tmp_path / "config.toml"
    path.mkdir(mode=0o700)

    with pytest.raises(home.UserConfigError) as raised:
        home.read_config(path)
    assert raised.value.code == "user-config-unreadable"
