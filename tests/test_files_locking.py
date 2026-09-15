"""The files backend's write lock: what it is for, shown as the races it closes.

A tree has no transactions, so two writers interleaving on it can do what two
SQLite connections cannot: hand out one ``?`` number twice, leave a key holding
nothing, or pull a directory out from under a write. Every write unit takes one
lock per tree, and these tests are the races it is there to close.

Each race is **widened on purpose** rather than left to the scheduler: a wrapper
sleeps at the point the two writers have to interleave, so without the lock the
bad ordering is what happens, and with it the second writer simply waits. A
race left to chance passes on the old code nine runs in ten and says nothing.
Every one of these was run against the per-instance lock first and failed.

Two instances on one tree, not one instance shared, because that is what the
lock is keyed by: ``bulk`` and ``shipped`` construct their own, and a server
and a command line in one process would each hold one.
"""

from __future__ import annotations

import multiprocessing
import os
import threading
import time
from types import SimpleNamespace

import pytest

from conftest import in_threads, raises_rendered
from outrage import bulk, store_files
from outrage.store_files import FilesystemStore, StoreBusyError

#: Long enough that the second writer is certainly inside the window the first
#: one opened, and short enough that the file stays quick.
PAUSE = 0.1


@pytest.fixture
def pair(tmp_path):
    """Two stores on one tree, as two unrelated callers would open it."""
    root = tmp_path / "tree"
    return FilesystemStore(root), FilesystemStore(root)


def test_two_instances_on_one_tree_do_not_allocate_one_number_twice(pair, monkeypatch):
    """`?` reads the level and writes past its highest number.

    Two writers that both read before either writes both take ``1``, the second
    file replaces the first, and both callers are told the key is theirs.
    """
    trees = [*pair, *pair]
    next_number = FilesystemStore._next_number
    start = threading.Barrier(len(trees))

    def slow(self, parent):
        number = next_number(self, parent)
        time.sleep(PAUSE)
        return number

    monkeypatch.setattr(FilesystemStore, "_next_number", slow)
    allocated = [None] * len(trees)

    def allocate(i):
        start.wait()
        allocated[i] = trees[i].store_document("c/?/doc", f"from {i}")

    in_threads(allocate, threads=len(trees))

    assert len(set(allocated)) == len(trees)
    assert sorted(pair[0].retrieve_document(key).content for key in allocated) == sorted(
        f"from {i}" for i in range(len(trees))
    )


def test_storing_one_key_in_two_formats_at_once_leaves_one_of_them(pair, monkeypatch):
    """A write lands its file, then unlinks every other file claiming the key.

    A writes ``a.md``; B writes ``a.json``; A sees both and removes ``a.json``;
    B sees only ``a.md`` and removes that. Both calls succeed and the key is
    empty -- the worst of these, because nothing says so.
    """
    first, second = pair
    write_file = bulk._write_file
    written = threading.Event()

    def slow(path, content):
        write_file(path, content)
        written.set()
        time.sleep(PAUSE)

    monkeypatch.setattr(bulk, "_write_file", slow)

    def store(i):
        if i == 0:
            first.store_document("a", "# markdown", "markdown")
        else:
            written.wait()
            second.store_document("a", '{"json": true}', "json")

    in_threads(store, threads=2)

    assert first.exists("a")
    assert len(first._files_for("a")) == 1


def test_a_prune_does_not_remove_the_directory_a_write_is_landing_in(pair, monkeypatch):
    """A write makes its parent, then opens a temporary file inside it.

    A delete that empties that parent between the two removes it, and the
    write fails on a directory that was there a moment ago.
    """
    writer, deleter = pair
    deleter.store_document("x/y", "the only document in x")
    real = bulk.tempfile
    inside = threading.Event()

    def slow(*args, **kwargs):
        inside.set()
        time.sleep(PAUSE)
        return real.NamedTemporaryFile(*args, **kwargs)

    monkeypatch.setattr(bulk, "tempfile", SimpleNamespace(NamedTemporaryFile=slow))

    def work(i):
        if i == 0:
            writer.store_document("x/z", "landing beside it")
        else:
            inside.wait()
            deleter.delete("x/y")

    in_threads(work, threads=2)

    assert writer.retrieve_document("x/z").content == "landing beside it"
    assert not writer.exists("x/y")


def test_a_unit_can_call_another_on_the_same_tree(pair):
    """Re-entrant, because a write built out of writes takes the lock it holds."""
    first, second = pair
    with first._writing():
        second.store_document("a", "inside")
        second.delete("a")
    assert not first.exists("a")


def test_a_writer_that_cannot_get_the_lock_gives_up_and_says_so(pair, monkeypatch):
    """A bounded wait, as SQLite's `busy_timeout` is, rather than a hang."""
    holder, waiter = pair
    monkeypatch.setattr(store_files, "LOCK_TIMEOUT_SECONDS", 0.05)
    held, release = threading.Event(), threading.Event()

    def hold():
        with holder._writing():
            held.set()
            release.wait()

    thread = threading.Thread(target=hold)
    thread.start()
    try:
        held.wait()
        with raises_rendered(StoreBusyError, "busy.*nothing was written") as raised:
            waiter.store_document("a", "b")
        assert raised.value.code == "store-busy"
        assert not waiter.exists("a")
    finally:
        release.set()
        thread.join()

    waiter.store_document("a", "b")
    assert waiter.exists("a")


# -- across processes ------------------------------------------------------
#
# `spawn` rather than the platform default, so that a child starts from nothing
# the way a second server or a command line does, and so that the tests behave
# the same on macOS, Linux and Windows. What each child does is a module-level
# function because that is what `spawn` can hand to one. Windows is not run.

SPAWN = multiprocessing.get_context("spawn")

#: How long a child may take to start and import outrage before a test gives up.
STARTUP = 60


def _allocate_elsewhere(root, lock, count, start, results):
    """Allocate ``count`` numbers from a process of its own, widened as above."""
    next_number = FilesystemStore._next_number

    def slow(self, parent):
        number = next_number(self, parent)
        time.sleep(PAUSE / 4)
        return number

    FilesystemStore._next_number = slow
    tree = FilesystemStore(root, lock=lock)
    start.wait()
    results.put([tree.store_document("c/?/doc", "x") for _ in range(count)])


def _hold_elsewhere(root, held, release, die):
    """Take the lock from a process of its own, and let go or die holding it."""
    tree = FilesystemStore(root, lock="interprocess")
    with tree._writing():
        held.set()
        if die:
            os._exit(1)
        release.wait()


def _run(target, *args):
    process = SPAWN.Process(target=target, args=args)
    process.start()
    return process


def test_interprocess_writers_do_not_allocate_one_number_twice(tmp_path):
    root = tmp_path / "tree"
    start, results = SPAWN.Event(), SPAWN.Queue()
    processes = [
        _run(_allocate_elsewhere, root, "interprocess", 5, start, results) for _ in range(3)
    ]
    start.set()
    allocated = [key for _ in processes for key in results.get(timeout=STARTUP)]
    for process in processes:
        process.join(STARTUP)
        assert process.exitcode == 0

    assert len(allocated) == 15
    assert len(set(allocated)) == 15


def test_a_writer_in_another_process_holding_the_tree_makes_this_one_wait(tmp_path, monkeypatch):
    root = tmp_path / "tree"
    monkeypatch.setattr(store_files, "LOCK_TIMEOUT_SECONDS", 0.2)
    held, release = SPAWN.Event(), SPAWN.Event()
    holder = _run(_hold_elsewhere, root, held, release, False)
    try:
        assert held.wait(STARTUP)
        waiter = FilesystemStore(root, lock="interprocess")
        with raises_rendered(StoreBusyError, "busy"):
            waiter.store_document("a", "b")
        # A process-mode writer is not bound by it: the modes do not mix.
        FilesystemStore(root).store_document("unbound", "written anyway")
    finally:
        release.set()
        holder.join(STARTUP)

    waiter.store_document("a", "b")
    assert waiter.exists("a")


def test_a_holder_that_dies_does_not_keep_the_tree(tmp_path):
    """The OS lets go of a dead process's lock, which a lock file's presence would not."""
    root = tmp_path / "tree"
    held, release = SPAWN.Event(), SPAWN.Event()
    holder = _run(_hold_elsewhere, root, held, release, True)
    holder.join(STARTUP)
    assert held.is_set() and holder.exitcode == 1

    FilesystemStore(root, lock="interprocess").store_document("a", "after the crash")
    assert FilesystemStore(root).retrieve_document("a").content == "after the crash"


def test_the_lock_file_sits_beside_the_tree_and_only_when_asked_for(tmp_path):
    FilesystemStore(tmp_path / "plain").store_document("a", "b")
    assert not (tmp_path / "plain.lock").exists()

    shared = FilesystemStore(tmp_path / "shared", lock="interprocess")
    shared.store_document("a", "b")
    assert (tmp_path / "shared.lock").is_file()
    assert sorted(path.name for path in (tmp_path / "shared").iterdir()) == ["a.md"]
    assert shared.list_keys().total == 1
