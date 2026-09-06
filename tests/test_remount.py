"""Changing the mount table of a running server.

Two questions, and the suite is not the important one. The first is whether a
tool caller can mount, read across the new boundary and unmount again, and it
is asked by driving an in-process server over a **two-store** table: a single
store cannot show a key named for the wrong reader, and this feature is
entirely about which store answers.

The second is the claim the whole design rests on and nothing else tests --
that a call holding a table goes on working while another thread replaces it.
The table itself is immutable, so what is being asserted is that a change
builds a new one and shares the stores it kept rather than reopening or closing
them.
"""

from __future__ import annotations

import concurrent.futures
import threading
from typing import Any

import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from outrage import keys, remount, shipped
from outrage.mounts import MountedStore, MountError
from outrage.remount import Live
from outrage.server import build_server
from outrage.store_sqlite import SqliteStore


def call(server, name: str, **arguments: Any) -> Any:
    result = anyio.run(server.call_tool, name, arguments)
    assert not result.is_error, result.content
    return result.structured_content


def call_expecting_error(server, name: str, **arguments: Any) -> str:
    with pytest.raises(ToolError) as raised:
        anyio.run(server.call_tool, name, arguments)
    return str(raised.value)


@pytest.fixture
def base(tmp_path):
    """A store directory holding the root store and two others to mount."""
    directory = tmp_path / "base"
    directory.mkdir()

    with SqliteStore(directory, filename="outrage.sqlite") as root:
        root.store_document("context/1/state", "Where we got to.", title="State")
        # Left under a key that a mount will claim, which is what makes
        # shadowing and revealing observable at all.
        root.store_document("ref/left", "Left behind under the mount.", title="Left")
    with SqliteStore(directory, filename="reference.sqlite") as reference:
        reference.store_document("", "The reference base.", title="Reference")
        reference.store_document("python/typing", "Annotations.", title="typing")
    with SqliteStore(directory, filename="other.sqlite") as other:
        other.store_document("python/typing", "Something else entirely.", title="other")
    return directory


@pytest.fixture
def live(base):
    """A live table of two stores: the root, and a reference base at `ref`."""
    root = SqliteStore(base, filename="outrage.sqlite")
    mounted = SqliteStore(base, filename="reference.sqlite", mount_point="ref")
    with Live(MountedStore({keys.ROOT: root, "ref": mounted}), directory=base) as opened:
        yield opened


@pytest.fixture
def server(live):
    return build_server(live, directory=live.directory)


def mounts(result) -> list[str]:
    return [one["mount"] for one in result["mounts"]]


# -- the table, through the tools -------------------------------------------


def test_a_mounted_store_answers_the_moment_it_is_mounted(server, base):
    before = call_expecting_error(server, "read_document", key="lib/python/typing")
    assert "lib/python/typing" in before

    said = call(server, "mount", key="lib", file="other.sqlite")
    assert mounts(said) == ["/", "lib", "ref"]

    read = call(server, "read_document", key="lib/python/typing")
    assert read["content"] == "Something else entirely."


def test_an_unmounted_store_stops_answering_and_the_root_takes_the_key_back(server):
    """The reveal, which is the half a caller is least likely to have in mind."""
    assert call(server, "read_document", key="ref/python/typing")["content"] == "Annotations."
    # `ref/left` is in the root store and shadowed by the mount above it.
    assert "ref/left" in call_expecting_error(server, "read_document", key="ref/left")

    said = call(server, "unmount", key="ref")
    assert mounts(said) == ["/"]

    assert call(server, "read_document", key="ref/left")["content"] == (
        "Left behind under the mount."
    )
    assert "ref/python/typing" in call_expecting_error(
        server, "read_document", key="ref/python/typing"
    )


def test_a_mount_at_a_point_something_holds_replaces_it_and_says_so(server):
    said = call(server, "mount", key="ref", file="other.sqlite")

    assert mounts(said) == ["/", "ref"]
    assert "already mounted at 'ref'" in said["note"]
    assert call(server, "read_document", key="ref/python/typing")["content"] == (
        "Something else entirely."
    )


def test_a_mount_over_keys_the_store_beneath_holds_says_they_are_hidden(server):
    call(server, "unmount", key="ref")
    said = call(server, "mount", key="ref", file="other.sqlite")

    assert "unreachable while this is mounted" in said["note"]
    assert "Unmount to reach them again" in said["note"]


def test_an_unmount_that_reveals_keys_says_what_is_there_now(server):
    said = call(server, "unmount", key="ref")

    assert "now holds keys there" in said["note"]
    assert "shadowed by the mount rather than removed by it" in said["note"]


def test_every_change_says_it_lasts_only_as_long_as_this_server(server):
    """The one thing a caller cannot work out: the answer looks like a restart's."""
    for said in [
        call(server, "mount", key="lib", file="other.sqlite"),
        call(server, "unmount", key="lib"),
    ]:
        assert "lasts as long as this server" in said["note"]
        assert "mount configuration file" in said["note"]


def test_a_read_only_mount_refuses_a_write_and_names_both_ways_out(server):
    call(server, "mount", key="lib", file="other.sqlite", read_only=True)

    said = call_expecting_error(server, "store_document", key="lib/a", content="No.")
    assert "read-only through this server" in said
    # Both remedies, each qualified by whose it is: the advice varies by reader
    # where the spelling does not, which is what the error side cannot carry.
    assert "`mount` tool" in said
    assert "--mount rather than --mount-ro" in said

    call(server, "mount", key="lib", file="other.sqlite")
    assert call(server, "store_document", key="lib/a", content="Yes.")["stored"] == 4


def test_a_read_only_mount_of_a_file_that_is_not_there_is_refused(server):
    said = call_expecting_error(server, "mount", key="lib", file="nope.sqlite", read_only=True)

    assert "has no store at" in said
    assert "mistyped name would mount as an empty store" in said


def test_the_root_can_be_neither_mounted_over_nor_unmounted(server):
    mounted = call_expecting_error(server, "mount", key="", file="other.sqlite")
    assert "at the root of a running server" in mounted
    assert "--root-mount" in mounted

    assert "cannot be unmounted" in call_expecting_error(server, "unmount", key="")


def test_unmounting_nothing_is_refused_rather_than_passed_over(server):
    said = call_expecting_error(server, "unmount", key="lib")

    assert "nothing is mounted at 'lib'" in said
    # The tool's spelling, not the server flag's: this is the one message the
    # two front ends really do spell two ways.
    assert "so unmount there removes nothing" in said


def test_a_store_file_must_still_be_named_relative_to_the_store_directory(server, base):
    said = call_expecting_error(server, "mount", key="lib", file=str(base / "other.sqlite"))

    assert "is an absolute path" in said
    assert "`info` is what reports which one this is" in said


# -- the manual, which is the reason `file` may be omitted -------------------


def test_the_shipped_manual_can_be_unmounted_and_put_back_by_name(base):
    """The reserved spelling, and why it exists: a tree in site-packages has none.

    John's call of 2026-09-06, over refusing to unmount a store the tool cannot
    restore, and over allowing it one way with a note. ``outrage`` is the only
    entry today; the shape is the point.
    """
    root = SqliteStore(base, filename="outrage.sqlite")
    table = MountedStore(
        {keys.ROOT: root, shipped.MOUNT_POINT: shipped.open_documents()},
        read_only=[shipped.MOUNT_POINT],
    )
    with Live(table, directory=base) as live:
        server = build_server(live, directory=base)
        assert call(server, "read_document", key="outrage/readme")["content"]

        call(server, "unmount", key=shipped.MOUNT_POINT)
        assert "outrage/readme" in call_expecting_error(
            server, "read_document", key="outrage/readme"
        )

        said = call(server, "mount", key=shipped.MOUNT_POINT)
        assert mounts(said) == ["/", "outrage"]
        # Always read-only: the next upgrade replaces the tree, so a writable
        # remount would be an invitation to lose the writing.
        assert [one["read_only"] for one in said["mounts"]] == [False, True]
        assert call(server, "read_document", key="outrage/readme")["content"]


def test_a_key_outrage_ships_nothing_for_needs_a_file(server):
    said = call_expecting_error(server, "mount", key="lib")

    assert "outrage ships no store for 'lib'" in said
    assert "'outrage'" in said


def test_the_shipped_store_has_no_backend_to_choose(server):
    said = call_expecting_error(server, "mount", key=shipped.MOUNT_POINT, type="files")

    assert "opened by name and not from a file" in said


# -- the claim the design rests on ------------------------------------------


def test_a_traversal_holding_a_table_finishes_against_it_while_another_changes(live, base):
    """One snapshot per call, and a store shared rather than reopened or closed.

    The failure this rules out is the one that kept mounts to start-time
    configuration: a subtree read crossing mounts is a sequence of per-store
    segments with a cursor recomputed at each boundary, so a table changing
    underneath one has no defined answer. It cannot happen because a change
    never edits a table -- and this holds a half-finished traversal open across
    a change to show it.
    """
    snapshot = live.table
    first = snapshot.list_keys(keys.ROOT, limit=1)
    assert first.next_cursor is not None

    live.mount("lib", file="other.sqlite")
    live.unmount("ref")

    rest = snapshot.list_keys(keys.ROOT, limit=100, cursor=first.next_cursor)
    assert [entry.key for entry in first.items] + [entry.key for entry in rest.items] == [
        "context",
        "ref",
    ]
    # And the store that traversal was reading is still open: it survived the
    # change because the new table shares it, at the same prefix.
    assert snapshot.retrieve_document("ref/python/typing").content == "Annotations."


def test_a_store_that_falls_out_of_the_table_is_closed_and_one_that_stays_is_not(live):
    """Ownership, stated as identity: in no live table is what closes a store."""
    root = live.table.root.store
    dropped = live.table.resolve("ref").mount.store
    dropped.exists("a")  # opens this thread's connection

    live.unmount("ref")

    assert live.table.root.store is root
    # Asked of the tracking, not of the connection: `SqliteStore.connection`
    # reopens on demand, so a closed store looks open the moment it is asked.
    assert dropped._local.conn is None
    # The root is in both tables, so nothing closed it out from under a caller.
    assert live.table.retrieve_document("context/1/state").content == "Where we got to."


def test_a_surviving_store_is_never_reopened(live):
    before = {mount.prefix: mount.store for mount in live.table}
    live.mount("lib", file="other.sqlite")

    for prefix, store in before.items():
        assert live.table.resolve(prefix).mount.store is store


def test_readers_and_a_change_run_together_without_a_lock_between_them(live):
    """Readers take no lock at all -- `live.table` is a plain attribute load.

    So what this asks is that a reader never sees a half-built table and never
    reads a store the changing thread has closed. Threads rather than a
    contrived interleaving, because the shape being tested is that there is
    nothing to interleave.
    """
    stop = threading.Event()
    failures: list[BaseException] = []

    def read() -> int:
        seen = 0
        while not stop.is_set():
            table = live.table
            try:
                assert table.retrieve_document("context/1/state").content
                assert [mount.prefix for mount in table][0] == keys.ROOT
            except BaseException as exc:  # noqa: BLE001 - re-raised on the main thread
                failures.append(exc)
                return seen
            seen += 1
        return seen

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        readers = [pool.submit(read) for _ in range(4)]
        for _ in range(20):
            live.mount("lib", file="other.sqlite")
            live.unmount("lib")
        stop.set()
        counts = [reader.result() for reader in readers]

    assert not failures, failures
    assert all(count > 0 for count in counts)


# -- withholding the tools --------------------------------------------------


def test_a_server_built_without_them_offers_neither(live):
    server = build_server(live, remount_tool=False)
    tools = {tool.name for tool in anyio.run(server.list_tools)}

    assert "mount" not in tools and "unmount" not in tools
    # And the table it serves is still the live one, so nothing else changes.
    assert "read_document" in tools


def test_a_plain_table_is_wrapped_so_there_is_one_path(base):
    """Every caller that passes a table rather than a `Live` still gets the tools."""
    with SqliteStore(base, filename="outrage.sqlite") as root:
        server = build_server(MountedStore.single(root), directory=base)
        said = call(server, "mount", key="lib", file="other.sqlite")

        assert mounts(said) == ["/", "lib"]


# -- what the table algebra will not do, reached through the live one --------


def test_a_change_that_cannot_be_described_leaves_the_table_alone(live, base):
    before = live.table

    with pytest.raises(MountError):
        live.mount("!title", file="other.sqlite")

    assert live.table is before
    assert [mount.prefix for mount in live.table] == ["", "ref"]


def test_the_shipped_table_is_a_mapping_rather_than_a_special_case():
    """One entry today, and the shape is what is being kept."""
    assert set(remount.SHIPPED) == {shipped.MOUNT_POINT}
