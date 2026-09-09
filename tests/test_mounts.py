"""Tests for routing one key namespace across several stores.

Driven through the server's own dispatch wherever the behaviour is a caller's,
because the translation is only correct if it is correct at the boundary a
caller actually sees. The table itself is tested directly where the question is
about routing rather than about a tool result.
"""

import itertools
import json
from pathlib import Path
from typing import Any

import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from conftest import answers_alike, page_facts, raises_rendered, walk_documents, walk_level
from outrage import bulk, keys, messages
from outrage.eventlog import EventLog
from outrage.mounts import (
    MOUNT_KIND,
    READ_ONLY_MOUNT_KIND,
    MountedStore,
    MountError,
    ReadOnlyMountError,
    Spec,
    open_mounts,
    parse_options,
    parse_spec,
    unparse,
)
from outrage.server import build_server, parse_args
from outrage.store import (
    EVERYTHING,
    FAILED,
    OVERWRITE,
    UNBOUNDED,
    WROTE,
    BackendError,
    BoundedSubtree,
    ChangedSinceError,
    FileStore,
    KeyNotFoundError,
    KeyRange,
    ReadOnlyStoreError,
    SearchCriterion,
    Store,
    StoreFileError,
)
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
def table(tmp_path):
    """A root store, a reference base at `ref`, and a deep mount at `lib/deep`."""
    root = SqliteStore(tmp_path / "root")
    ref = SqliteStore(tmp_path / "ref")
    deep = SqliteStore(tmp_path / "deep")

    root.store_document("context/1/state", "Where we got to.", title="State")
    root.store_document("notes/readme.md", "Notes about a file.", title="A file")

    ref.store_document("", "The reference base.", title="Reference")
    ref.store_document("python/asyncio", "Event loops.", title="asyncio")
    ref.store_document("python/typing", "Annotations.", title="typing")

    deep.store_document("a", "Deep.", title="Deep")

    built = MountedStore({"": root, "ref": ref, "lib/deep": deep})
    yield built
    built.close()


@pytest.fixture
def server(table):
    return build_server(table)


# -- the key grammar the routing rests on ---------------------------------


def test_a_prefix_is_stripped_by_segment_not_by_character():
    assert keys.strip_prefix("ref", "ref/a") == "a"
    assert keys.strip_prefix("ref", "reference/a") is None
    assert keys.strip_prefix("ref", "ref") == keys.ROOT
    assert keys.strip_prefix(keys.ROOT, "a/b") == "a/b"


def test_a_prefix_and_a_strip_are_inverses():
    for prefix, inner in [("ref", "a/b"), ("ref", ""), ("", "a"), ("lib/deep", "x/!title")]:
        assert keys.strip_prefix(prefix, keys.with_prefix(prefix, inner)) == inner


def test_the_mount_point_is_the_inner_root():
    assert keys.with_prefix("ref", keys.ROOT) == "ref"


# -- routing ---------------------------------------------------------------


def test_the_longest_prefix_owns_a_key(table):
    assert table.resolve("ref/python/typing").mount.prefix == "ref"
    assert table.resolve("ref").key == keys.ROOT
    assert table.resolve("lib/deep/a").mount.prefix == "lib/deep"
    # `lib` itself belongs to nobody but the root: a mount owns its point and
    # what is below it, never what is above.
    assert table.resolve("lib").mount.prefix == keys.ROOT
    assert table.resolve("reference").mount.prefix == keys.ROOT
    assert table.resolve(None).mount.prefix == keys.ROOT


def test_a_table_needs_a_root(tmp_path):
    with SqliteStore(tmp_path) as store, raises_rendered(MountError, "at the root"):
        MountedStore({"ref": store})


def test_a_mount_point_may_not_be_metadata(tmp_path):
    with SqliteStore(tmp_path) as store, raises_rendered(MountError, "may not be metadata"):
        MountedStore({"": store, "!title": store})


def test_mounts_below_a_key_are_the_ones_a_subtree_read_misses(table):
    assert [m.prefix for m in table.below(keys.ROOT)] == ["lib/deep", "ref"]
    assert [m.prefix for m in table.below("lib")] == ["lib/deep"]
    # A mount answers for its own point rather than being missed by it.
    assert table.below("ref") == []
    assert table.below("context") == []


# -- reading and writing across a boundary ---------------------------------


def test_a_read_crosses_a_mount_and_comes_back_named_from_outside(server):
    result = call(server, "read_document", key="ref/python/asyncio")
    assert result["key"] == "ref/python/asyncio"
    assert result["content"] == "Event loops."


def test_the_mount_point_reads_the_inner_root(server):
    assert call(server, "read_document", key="ref")["content"] == "The reference base."
    assert call(server, "read_document", key="ref/!title")["content"] == "Reference"


def test_a_write_lands_in_the_mounted_store(server, table):
    result = call(server, "store_document", key="ref/python/dataclasses", content="Frozen.")
    assert result["key"] == "ref/python/dataclasses"
    inner = table.resolve("ref").store
    assert inner.retrieve_document("python/dataclasses").content == "Frozen."
    # And nothing landed in the root store under that name.
    assert not table.root.store.exists("ref/python/dataclasses")


def test_an_allocated_segment_is_allocated_inside_the_mount(server, table):
    result = call(server, "store_document", key="ref/notes/?", content="One.", title="One")
    assert result["key"] == "ref/notes/1"
    assert result["generated"] is True
    assert result["title_key"] == "ref/notes/1/!title"
    assert table.resolve("ref").store.exists("notes/1")


def test_store_events_name_keys_in_the_mounted_namespace(tmp_path):
    log = EventLog(tmp_path / "log.jsonl")
    with open_mounts(tmp_path / "stores", ["ref=ref.sqlite"], log=log) as table:
        assert table.store_document("ref/notes/?", "One.", title="One") == "ref/notes/1"
        assert table.delete("ref/notes/1") == ["ref/notes/1", "ref/notes/1/!title"]
    log.close()

    recorded = [json.loads(line) for line in (tmp_path / "log.jsonl").read_text().splitlines()]
    wrote = next(event for event in recorded if event.get("op") == "store_document")
    deleted = next(event for event in recorded if event.get("op") == "delete")

    assert wrote["args"]["key"] == "ref/notes/?"
    assert wrote["result"]["key"] == "ref/notes/1"
    assert deleted["args"]["key"] == "ref/notes/1"
    assert deleted["result"]["keys"] == ["ref/notes/1", "ref/notes/1/!title"]


def test_a_delete_crosses_a_mount(server, table):
    result = call(server, "delete_keys", key="ref/python/typing", recursive=True)
    assert result["deleted"] == ["ref/python/typing", "ref/python/typing/!title"]
    assert not table.resolve("ref").store.exists("python/typing")


# -- listings -------------------------------------------------------------


def test_a_mount_point_appears_in_the_listing_above_it(server):
    entries = {e["key"]: e for e in call(server, "list_keys")["entries"]}
    assert set(entries) == {"context", "notes", "ref", "lib"}
    assert entries["ref"]["kind"] == MOUNT_KIND
    # Described by the inner root, which is how a mount says what it is.
    assert entries["ref"]["size"] == len("The reference base.")
    # `lib` is a key only because something is mounted below it.
    assert entries["lib"]["kind"] == "implicit"


def test_a_mount_nested_below_an_implicit_key_is_reachable(server):
    entries = {e["key"]: e for e in call(server, "list_keys", key="lib")["entries"]}
    assert entries["lib/deep"]["kind"] == MOUNT_KIND
    assert call(server, "read_document", key="lib/deep/a")["content"] == "Deep."


def test_a_listing_inside_a_mount_is_named_from_outside(server):
    result = call(server, "list_keys", key="ref/python")
    # Metadata lists under the document it describes, not under the level, so
    # this is the two documents and nothing else.
    assert [e["key"] for e in result["entries"]] == ["ref/python/asyncio", "ref/python/typing"]
    assert result["total"] == 2


def test_the_level_total_counts_the_mounts_it_gained(server):
    result = call(server, "list_keys")
    assert result["total"] == len(result["entries"]) == 4


def test_a_paged_listing_merges_mounts_before_it_cuts(server):
    first = call(server, "list_keys", limit=2)
    assert [e["key"] for e in first["entries"]] == ["context", "lib"]
    assert first["total"] == 4
    second = call(server, "list_keys", limit=2, after=first["next_cursor"])
    assert [e["key"] for e in second["entries"]] == ["notes", "ref"]
    assert second["next_cursor"] is None


def test_a_cursor_from_another_mount_is_refused(server):
    message = call_expecting_error(server, "list_keys", key="ref", after="context/1")
    assert "not below" in message


# -- what crosses a boundary -----------------------------------------------


def test_a_survey_crosses_every_mount_below_it(server):
    # It used to stop at the first boundary and name what it had skipped. The
    # scope that made it do so was about staging the work, not about what a
    # survey should mean -- see `planned/mounts/crossing`.
    result = call(server, "get_documents", meta_name=["title"])
    assert "mounts_not_searched" not in result
    assert "were not read" not in (result.get("note") or "")
    assert any(d["key"].startswith("ref/") for d in result["documents"])


def test_a_survey_inside_a_mount_has_nothing_to_warn_about(server):
    result = call(server, "get_documents", key="ref", meta_name=["title"])
    assert "mounts_not_searched" not in result
    assert [d["key"] for d in result["documents"]] == [
        "ref/!title",
        "ref/python/asyncio/!title",
        "ref/python/typing/!title",
    ]


def test_keys_missing_meta_is_named_from_outside(server, table):
    table.resolve("ref").store.store_document("python/untitled", "No title.")
    result = call(server, "keys_missing_meta", key="ref")
    assert result["keys"] == ["ref/python/untitled"]
    assert "mounts_not_searched" not in result


def test_a_recursive_delete_crosses_a_mount_below_the_key(server, table):
    # The dangerous half of consistency, and taken deliberately: a delete that
    # stopped at a boundary while every other tool crossed it would leave the
    # caller to find the rule out from what survived.
    result = call(server, "delete_keys", key="lib", recursive=True)
    assert "mounts_kept" not in result
    assert "lib/deep/a" in result["deleted"]
    assert not table.resolve("lib/deep").store.exists("a")


def test_a_recursive_delete_does_not_report_shadowed_keys_as_deleted(shadowing):
    # The defect crossing started from, and the reason it is a defect rather
    # than a limitation: the delete removed the outer store's shadowed rows and
    # reported them under outer names, and reading `project` straight after
    # returned content. A report a caller can disprove in the next call.
    server = build_server(shadowing)
    result = call(server, "delete_keys", key="", recursive=True)

    for key in result["deleted"]:
        assert call_expecting_error(server, "read_document", key=key)

    # `project` is deleted because the *mount's* root document was deleted, not
    # because the shadowed one underneath it was.
    assert "project" in result["deleted"]
    assert "project/shown" in result["deleted"]
    assert "project/untitled" not in result["deleted"]


def test_a_recursive_delete_skips_a_read_only_mount_and_says_so(tmp_path):
    # One read-only mount below the key does not veto the whole delete: what
    # can go, goes, and what stayed is named rather than left to be noticed.
    root = SqliteStore(tmp_path / "root")
    writable = SqliteStore(tmp_path / "writable")
    frozen = SqliteStore(tmp_path / "frozen")
    root.store_document("lib/own", "Outer.", title="Outer")
    writable.store_document("a", "Writable.", title="A")
    frozen.store_document("b", "Frozen.", title="B")

    with MountedStore(
        {"": root, "lib/soft": writable, "lib/hard": frozen}, read_only=["lib/hard"]
    ) as table:
        server = build_server(table)
        result = call(server, "delete_keys", key="lib", recursive=True)

        assert result["mounts_kept"] == ["lib/hard"]
        assert "refuse a delete" in result["note"]
        assert sorted(result["deleted"]) == [
            "lib/own",
            "lib/own/!title",
            "lib/soft/a",
            "lib/soft/a/!title",
        ]
        assert frozen.exists("b")
        assert not writable.exists("a")


def test_a_cursor_is_recomputed_at_every_boundary(tmp_path):
    # Paging one document at a time across three stores. A cursor names a key
    # in the one namespace and means something different to each store it
    # crosses, so a page that carried it inward once would either repeat a
    # store's first rows or skip past them.
    root = SqliteStore(tmp_path / "root")
    outer = SqliteStore(tmp_path / "outer")
    nested = SqliteStore(tmp_path / "nested")
    root.store_document("aaa", "Root, before.", title="A")
    root.store_document("zzz", "Root, after.", title="Z")
    outer.store_document("m", "Outer.", title="M")
    nested.store_document("n", "Nested.", title="N")

    with MountedStore({"": root, "lib": outer, "lib/deep": nested}) as table:
        server = build_server(table)
        after, seen = None, []
        while True:
            page = call(server, "get_documents", limit=1, after=after)
            seen += [d["key"] for d in page["documents"]]
            if page["next_cursor"] is None:
                break
            after = page["next_cursor"]
            assert len(seen) < 10, "cursor is not advancing"

    assert seen == ["aaa", "lib/deep/n", "lib/m", "zzz"]
    assert len(seen) == len(set(seen)), "a segment was read twice"


def test_a_depth_budget_is_translated_into_a_mounted_store(tmp_path):
    # Depth is counted from the key that was asked about, so a store mounted
    # further down gets the part of the budget the descent did not spend.
    root = SqliteStore(tmp_path / "root")
    ref = SqliteStore(tmp_path / "ref")
    root.store_document("top", "Root.", title="Top")
    ref.store_document("", "The mount point.", title="Mount")
    ref.store_document("one", "One down.", title="One")
    ref.store_document("one/two", "Two down.", title="Two")

    with MountedStore({"": root, "ref": ref}) as table:
        server = build_server(table)
        assert survey(server, depth=1) == ["ref", "top"]
        assert survey(server, depth=2) == ["ref", "ref/one", "top"]
        assert survey(server, depth=3) == ["ref", "ref/one", "ref/one/two", "top"]
        # Past the budget the mount is stepped over but not entered, and the
        # rows it shadows do not reappear in its place.
        assert survey(server, depth=0) == []


def test_a_failed_read_names_the_key_the_caller_asked_for(server):
    """The defect in `planned/error-naming`, through the real dispatch.

    The store raised about `python/nope`, which is not a key in this namespace
    at all: used as written it addresses the root store. What comes back has to
    be the key the caller could send again.
    """
    message = call_expecting_error(server, "read_document", key="ref/python/nope")
    assert "nothing is stored at or below 'ref/python/nope'" in message


def test_a_container_inside_a_mount_gives_advice_that_works(server):
    """The worst of the three faults, and the one a caller cannot detect.

    `list_keys('python')` asks the store *above* the mount, which holds nothing
    there -- so following the advice returns an empty listing rather than an
    error, and the caller concludes the keys do not exist.
    """
    message = call_expecting_error(server, "read_document", key="ref/python")
    assert "no content stored at 'ref/python'" in message
    named = message[message.index("no content") :]
    assert "'python'" not in named.replace("'ref/python'", "")

    # And the advice, followed literally, answers.
    listed = call(server, "list_keys", key="ref/python")
    assert [e["key"] for e in listed["entries"]] == ["ref/python/asyncio", "ref/python/typing"]


def test_an_empty_mounted_store_is_not_reported_as_a_blank_key(tmp_path):
    """`planned/root-key/impact` finding 7: a blank key is invisible in a report."""
    root, empty = SqliteStore(tmp_path / "root"), SqliteStore(tmp_path / "empty")
    with MountedStore({"": root, "blank": empty}) as table:
        message = call_expecting_error(build_server(table), "read_document", key="blank")
    assert "at or below 'blank'" in message
    assert "at or below ''" not in message


def test_a_single_store_result_says_nothing_about_mounts(tmp_path):
    with SqliteStore(tmp_path) as store:
        store.store_document("a", "x", title="A")
        server = build_server(store)
        result = call(server, "get_documents", meta_name=["title"])
        assert "mounts_not_searched" not in result
        assert "dropped" not in result
        assert "note" not in result


# -- the two halves always join -------------------------------------------


def _deep_key(segments: int) -> str:
    return keys.DELIMITER.join(str(n) for n in range(segments))


def test_the_joined_bound_is_two_halves_of_the_store_bound():
    """The relationship the whole scheme rests on, stated once as a test."""
    assert keys.MAX_JOINED_SEGMENTS == 2 * keys.MAX_SEGMENTS


def test_a_store_key_may_not_exceed_half_the_namespace(tmp_path):
    with SqliteStore(tmp_path) as store:
        store.store_document(_deep_key(keys.MAX_SEGMENTS), "at the limit")
        with raises_rendered(keys.InvalidKeyError, "at most 64 are allowed"):
            store.store_document(_deep_key(keys.MAX_SEGMENTS + 1), "over it")


def test_a_mount_point_may_not_exceed_half_the_namespace(tmp_path):
    with SqliteStore(tmp_path) as store:
        MountedStore({"": store, _deep_key(keys.MAX_SEGMENTS): store})
        with raises_rendered(keys.InvalidKeyError, "at most 64 are allowed"):
            MountedStore({"": store, _deep_key(keys.MAX_SEGMENTS + 1): store})
        with raises_rendered(keys.InvalidKeyError, "at most 64 are allowed"):
            parse_spec(f"{_deep_key(keys.MAX_SEGMENTS + 1)}=/srv/x")


def test_two_full_halves_still_join(tmp_path):
    """The worst case the bounds allow, end to end through the server.

    A mount point at exactly the store bound holding a key at exactly the store
    bound: the joined key is `MAX_JOINED_SEGMENTS` long. This is the case that
    used to be dropped.

    Note what the deepest key cannot have: a title. Metadata is a segment, so a
    document at the store bound has no room for one *inside its own store* -
    which is why the joined bound needs no allowance for it. The store refuses
    it, and the namespace above never sees a key the store could not hold.
    """
    root = SqliteStore(tmp_path / "root")
    inner = SqliteStore(tmp_path / "inner")
    point = _deep_key(keys.MAX_SEGMENTS)
    deepest = _deep_key(keys.MAX_SEGMENTS)
    titled = _deep_key(keys.MAX_SEGMENTS - 1)
    inner.store_document(deepest, "as deep as it goes")
    inner.store_document(titled, "one shallower", title="Titled")

    with pytest.raises(keys.InvalidKeyError):
        inner.store_document(deepest, "x", title="no room for this")

    with MountedStore({"": root, point: inner}) as table:
        joined = f"{point}/{deepest}"
        assert joined.count(keys.DELIMITER) + 1 == keys.MAX_JOINED_SEGMENTS
        assert keys.fits(joined)

        server = build_server(table)
        assert call(server, "read_document", key=joined)["content"] == "as deep as it goes"

        survey = call(server, "get_documents", key=point, meta_name=["title"])
        assert [d["key"] for d in survey["documents"]] == [f"{point}/{titled}/!title"]
        # Nothing is left out of any of it any more.
        assert "dropped" not in survey

        # A write at the deepest titled key reports a title_key that parses.
        written = call(
            server, "store_document", key=f"{point}/{titled}", content="rewritten", title="T"
        )
        assert written["title_key"] == f"{point}/{titled}/!title"


def test_a_key_predating_the_bound_fails_loudly_rather_than_silently(tmp_path):
    """The one way the join can still fail, and what it does about it.

    `MAX_SEGMENTS` was 128 until 2026-08-20, so a store written before that can
    hold a key too deep to name from a mount point. `Mount.outer` cannot return
    such a key, and says which store and which key rather than handing back a
    string that fails to parse one call later.
    """
    root = SqliteStore(tmp_path / "root")
    inner = SqliteStore(tmp_path / "inner")
    legacy = _deep_key(keys.MAX_JOINED_SEGMENTS)
    # Written under the wider bound the store used to enforce, which is the
    # only way to produce one now.
    inner.connection.execute(
        "INSERT INTO documents (key, doc_key, meta_name, parent, sort_key, content, "
        "format, updated_at) VALUES (?, ?, NULL, ?, ?, ?, 'markdown', '2026-01-01T00:00:00+00:00')",
        (
            legacy,
            legacy,
            keys.parse(legacy, max_segments=keys.MAX_JOINED_SEGMENTS).parent,
            keys.sort_form(legacy),
            "from an older outrage",
        ),
    )
    inner.connection.commit()

    with MountedStore({"": root, "old": inner}) as table:
        mount = table.resolve("old").mount
        with raises_rendered(MountError, "has no name in this namespace"):
            mount.outer(legacy)


# -- shadowing -------------------------------------------------------------


def test_a_mount_shadows_what_the_store_beneath_it_holds(tmp_path):
    root = SqliteStore(tmp_path / "root")
    inner = SqliteStore(tmp_path / "inner")
    root.store_document("ref/hidden", "Unreachable.", title="Hidden")
    inner.store_document("shown", "Reachable.", title="Shown")

    with MountedStore({"": root, "ref": inner}) as table:
        server = build_server(table)
        assert [m.prefix for m in table.shadowing()] == ["ref"]
        assert [e["key"] for e in call(server, "list_keys", key="ref")["entries"]] == ["ref/shown"]
        # And the level above counts the mount point once, not twice.
        listing = call(server, "list_keys")
        assert [e["key"] for e in listing["entries"]] == ["ref"]
        assert listing["total"] == 1


def test_nothing_shadows_when_the_mount_point_is_empty(table):
    assert table.shadowing() == []


@pytest.fixture
def shadowing(tmp_path):
    """A root store whose `project` subtree a mount stands in front of."""
    root = SqliteStore(tmp_path / "root")
    inner = SqliteStore(tmp_path / "inner")

    root.store_document("readme", "The readme.", title="Readme")
    root.store_document("project", "The index.", title="Project")
    root.store_document("project/reference/env", "How to run.", title="Env")
    root.store_document("project/untitled", "No title here.")
    root.store_document("zzz", "Last.", title="Last")

    inner.store_document("", "Mounted.", title="Mounted root")
    inner.store_document("shown", "Reachable.", title="Shown")

    with MountedStore({"": root, "project": inner}) as built:
        yield built


@pytest.fixture
def shadowed_server(shadowing):
    return build_server(shadowing)


def survey(server, **arguments):
    return [d["key"] for d in call(server, "get_documents", **arguments)["documents"]]


def test_a_survey_does_not_report_what_reading_by_key_would_refuse(shadowed_server):
    # The failure this fixes. A survey rooted *above* a mount point used to
    # walk the outer store straight through the shadowed subtree, because that
    # store still holds every row and nothing removed them -- so it listed 44
    # keys that reading them then refused. `list_keys` upheld the invariant and
    # the traversals did not.
    #
    # The subtree is now read as segments rather than windows, so the shadowed
    # stretch is not merely stepped over: the mount standing in front of it is
    # read in its place. `project/!title` is the *mount's* title, and the
    # documents the mount shadows are still absent.
    assert survey(shadowed_server, meta_name=["title"]) == [
        "project/!title",
        "project/shown/!title",
        "readme/!title",
        "zzz/!title",
    ]
    assert survey(shadowed_server, depth=1) == ["project", "readme", "zzz"]

    # And the titles the survey shows are the ones a read can reach.
    for key in survey(shadowed_server, meta_name=["title"]):
        assert call(shadowed_server, "read_document", key=key)["content"]

    # Nothing was skipped, so there is nothing to warn about.
    result = call(shadowed_server, "get_documents", meta_name=["title"])
    assert "mounts_not_searched" not in result


def test_a_shadowed_key_is_not_named_as_missing_metadata(shadowed_server):
    # `project/untitled` has no title and is unreachable. Naming it would send
    # a caller to a key that does not answer, which is the whole failure.
    assert call(shadowed_server, "keys_missing_meta")["keys"] == []


def test_without_meta_does_not_count_what_it_cannot_show(shadowed_server):
    result = call(shadowed_server, "get_documents", meta_name=["title"])
    assert result["without_meta"] == {"total": 0, "total_chars": 0, "sample": []}


def test_a_survey_counts_the_segments_it_actually_read(shadowed_server):
    result = call(shadowed_server, "get_documents", meta_name=["title"])
    assert result["total"] == 4 == result["returned"]
    # The mount's own titles are counted and the shadowed `Project` is not,
    # which is the same rule stated from both sides: a total counts what the
    # answer could show.
    assert result["total_chars"] == len("Readme") + len("Last") + len("Mounted root") + len("Shown")


def test_the_mounts_own_title_is_what_the_survey_shows_at_the_mount_point(shadowed_server):
    # The mount point resolves to the mounted store, so `project/!title` is the
    # inner root's title and not the shadowed one underneath it.
    assert call(shadowed_server, "read_document", key="project/!title")["content"] == (
        "Mounted root"
    )


def test_paging_a_survey_across_a_mount_tiles_without_gap_or_overlap(shadowing):
    # Untitled documents either side of the mount and one inside the stretch it
    # shadows. `without_meta` describes this page's own window, so paging has
    # to tile those windows exactly: no document counted twice, none missed,
    # and the shadowed one never counted at all.
    root = shadowing.root.store
    root.store_document("aaa", "Before the mount, untitled.")
    root.store_document("yyy", "After the mount, untitled.")
    server = build_server(shadowing)

    after, seen, counted, sampled = None, [], 0, []
    while True:
        page = call(server, "get_documents", meta_name=["title"], limit=1, after=after)
        seen += [d["key"] for d in page["documents"]]
        counted += page["without_meta"]["total"]
        sampled += page["without_meta"]["sample"]
        if page["next_cursor"] is None:
            break
        after = page["next_cursor"]
        assert len(seen) < 10, "cursor is not advancing"

    assert seen == [
        "project/!title",
        "project/shown/!title",
        "readme/!title",
        "zzz/!title",
    ]
    assert counted == 2
    assert sampled == ["aaa", "yyy"]
    assert len(sampled) == len(set(sampled)), "double counted across segments"
    assert call(server, "keys_missing_meta")["keys"] == sampled


def test_a_page_ending_on_a_segment_edge_still_says_there_is_more(shadowing):
    # The case that would truncate the collection silently. The stretch in
    # front of the mount holds exactly one document, so the store fills the
    # page and reaches that stretch's end at the same moment and has no cursor
    # of its own to give. Whether there is another page is a question only the
    # segments behind it can answer -- and they are now in other stores, which
    # cannot even be asked with the same cursor.
    shadowing.root.store.store_document("aaa", "Before the mount.", title="First")
    server = build_server(shadowing)
    page = call(server, "get_documents", meta_name=["title"], limit=1)

    assert [d["key"] for d in page["documents"]] == ["aaa/!title"]
    assert page["next_cursor"] == "aaa/!title"

    rest = call(server, "get_documents", meta_name=["title"], limit=1, after=page["next_cursor"])
    assert [d["key"] for d in rest["documents"]] == ["project/!title"]
    assert rest["next_cursor"] == "project/!title"


def test_a_character_budget_is_spent_across_the_segments_not_per_segment(shadowing):
    # One budget for the page, however many segments it is read in, and however
    # many stores those segments belong to. Spent per segment instead, a page
    # would return one budget's worth for each mount.
    root = shadowing.root.store
    root.store_document("aaa", "x" * 400, title="Before")
    root.store_document("yyy", "y" * 400, title="After")
    server = build_server(shadowing)

    page = call(server, "get_documents", max_total_chars=500, limit=100)
    returned = sum(d["returned"] for d in page["documents"])

    # Spent per window this page would have carried `yyy` too, on a second
    # budget of its own, and returned 816 characters against a stated 500.
    assert returned <= 500
    assert page["next_cursor"] is not None

    seen = [d["key"] for d in page["documents"]]
    while page["next_cursor"] is not None:
        page = call(
            server, "get_documents", max_total_chars=500, limit=100, after=page["next_cursor"]
        )
        seen += [d["key"] for d in page["documents"]]
        assert len(seen) < 20, "cursor is not advancing"

    assert seen == ["aaa", "project", "project/shown", "readme", "yyy", "zzz"]


def test_paging_keys_missing_meta_across_a_mount_reaches_both_sides(shadowing):
    # Untitled keys either side of the mount, so a page has to cross it.
    root = shadowing.root.store
    root.store_document("aaa", "Before the mount, untitled.")
    root.store_document("yyy", "After the mount, untitled.")
    server = build_server(shadowing)

    after, seen = None, []
    while True:
        page = call(server, "keys_missing_meta", limit=1, after=after)
        seen += page["keys"]
        if page["next_cursor"] is None:
            break
        after = page["next_cursor"]
        assert len(seen) < 10, "cursor is not advancing"

    assert seen == ["aaa", "yyy"]
    assert call(server, "keys_missing_meta")["total"] == 2


def test_a_listing_counts_the_mount_and_not_what_it_replaced(shadowed_server):
    listing = call(shadowed_server, "list_keys")
    assert [e["key"] for e in listing["entries"]] == ["project", "readme", "zzz"]
    assert listing["total"] == 3
    # The mount's own root document, never the 10 characters of the document it
    # stands in front of, which this same listing declines to show.
    assert listing["total_chars"] == len("The readme.") + len("Last.") + len("Mounted.")


def test_a_listing_counts_a_mount_point_the_store_holds_only_metadata_for(tmp_path):
    # The corner a cheaper test missed: metadata sits *at* a key, so `ref` here
    # has no document and no descendants, and still occupies a position in the
    # level the store counted.
    root = SqliteStore(tmp_path / "root")
    inner = SqliteStore(tmp_path / "inner")
    root.store_document("ref/!title", "Stale title")
    inner.store_document("", "Mounted.", title="Mounted root")

    with MountedStore({"": root, "ref": inner}) as table:
        listing = call(build_server(table), "list_keys")
        assert [e["key"] for e in listing["entries"]] == ["ref"]
        assert listing["total"] == 1
        assert listing["total_chars"] == len("Mounted.")


def test_a_nested_mount_is_read_in_its_place(tmp_path):
    # Two mounts, one inside the other. Nesting needs no case of its own: the
    # inner mount is not reached from the root at all, it is reached from the
    # store containing it, which is what makes the segment list recursive.
    root = SqliteStore(tmp_path / "root")
    outer = SqliteStore(tmp_path / "outer")
    nested = SqliteStore(tmp_path / "nested")
    root.store_document("a", "A", title="A")
    root.store_document("lib/hidden", "Unreachable.", title="Hidden")
    root.store_document("lib/deep/alsohidden", "Unreachable.", title="Also")
    root.store_document("z", "Z", title="Z")
    outer.store_document("shown", "Reachable.", title="Shown")
    nested.store_document("deeper", "Reachable.", title="Deeper")

    with MountedStore({"": root, "lib": outer, "lib/deep": nested}) as table:
        server = build_server(table)
        # Both mounts read, both shadowed documents absent, and all four in the
        # order the one namespace puts them rather than the order the stores
        # were reached in.
        assert survey(server, meta_name=["title"]) == [
            "a/!title",
            "lib/deep/deeper/!title",
            "lib/shown/!title",
            "z/!title",
        ]
        assert call(server, "get_documents", meta_name=["title"])["total"] == 4


def test_a_survey_inside_a_mount_crosses_a_mount_below_it(tmp_path):
    # The segments are named as the *answering* store names them, so a mount
    # nested inside another is entered from that store's own key space.
    root = SqliteStore(tmp_path / "root")
    outer = SqliteStore(tmp_path / "outer")
    nested = SqliteStore(tmp_path / "nested")
    outer.store_document("a", "A", title="A")
    outer.store_document("deep/hidden", "Unreachable.", title="Hidden")
    nested.store_document("shown", "Reachable.", title="Shown")

    with MountedStore({"": root, "lib": outer, "lib/deep": nested}) as table:
        server = build_server(table)
        result = call(server, "get_documents", key="lib", meta_name=["title"])
        assert [d["key"] for d in result["documents"]] == [
            "lib/a/!title",
            "lib/deep/shown/!title",
        ]
        assert "mounts_not_searched" not in result


def test_nothing_changes_for_a_key_with_no_mount_below_it(table):
    # The single window case is the same query it always was, so a store with
    # no mount under the key answers exactly as it did before any of this.
    result = call(build_server(table), "get_documents", key="context", meta_name=["title"])
    assert [d["key"] for d in result["documents"]] == ["context/1/state/!title"]
    assert result["total"] == 1
    assert "mounts_not_searched" not in result


# -- table algebra: remounted ----------------------------------------------
#
# `remounted` opens nothing and closes nothing: it is the shape of the new
# table and no more. When a table is swapped, and who then owns the stores that
# fell out of it, is `outrage.remount` and is tested there.


def test_a_surviving_mount_keeps_the_very_same_store(table, tmp_path):
    """Shared by identity, which is the whole of why sharing is safe.

    A store learns one thing about its own mounting, ``mount_point``, and only
    the event log reads it -- so a store may be shared between two tables only
    at the same prefix. Copying the surviving mounts whole is what guarantees
    that, and this asserts the identity rather than the behaviour, because a
    reopened store would answer every read the same way and differ only in
    having a second connection to the same file.
    """
    before = {m.prefix: m.store for m in table}
    with SqliteStore(tmp_path / "extra") as extra:
        after = table.remounted(mount={"extra": extra})

    for prefix, store in before.items():
        assert after.resolve(prefix).mount.store is store
    assert after.resolve("extra").mount.store is extra
    assert [m.prefix for m in after] == ["", "extra", "lib/deep", "ref"]


def test_the_table_it_was_built_from_is_unchanged(table, tmp_path):
    """The immutability the whole design rests on, asserted rather than read."""
    with SqliteStore(tmp_path / "extra") as extra:
        table.remounted(mount={"extra": extra}, unmount=["ref"])

    assert [m.prefix for m in table] == ["", "lib/deep", "ref"]
    assert table.resolve("ref/python/typing").mount.prefix == "ref"
    assert table.retrieve_document("ref/python/typing").content == "Annotations."


def test_a_new_mount_answers_and_an_unmounted_one_falls_to_the_root(table):
    root = table.root.store
    root.store_document("ref/left", "Left behind under the mount.", title="Left")

    # Shadowed while `ref` is mounted: the outer store is never consulted for a
    # key a mount claims.
    assert not table.exists("ref/left")

    after = table.remounted(unmount=["ref"])
    assert after.retrieve_document("ref/left").content == "Left behind under the mount."
    with pytest.raises(KeyNotFoundError):
        after.retrieve_document("ref/python/typing")


def test_removals_are_applied_before_additions_so_a_store_can_move(table, tmp_path):
    moved = table.resolve("ref").mount.store
    after = table.remounted(mount={"lib/ref": moved}, unmount=["ref"])

    assert after.resolve("lib/ref").mount.store is moved
    assert after.retrieve_document("lib/ref/python/typing").content == "Annotations."
    assert [m.prefix for m in after] == ["", "lib/deep", "lib/ref"]


def test_a_mount_at_a_point_something_holds_replaces_it(table, tmp_path):
    with SqliteStore(tmp_path / "other") as other:
        other.store_document("python/typing", "Something else.", title="Other")
        after = table.remounted(mount={"ref": other})

        assert after.resolve("ref").mount.store is other
        assert after.retrieve_document("ref/python/typing").content == "Something else."
        assert len(after) == len(table)


def test_the_root_is_refused_in_both_arguments(table, tmp_path):
    with SqliteStore(tmp_path / "extra") as extra:
        with raises_rendered(MountError, "at the root of a running server"):
            table.remounted(mount={keys.ROOT: extra})
        with raises_rendered(MountError, "cannot be unmounted"):
            table.remounted(unmount=[keys.ROOT])


def test_unmounting_what_is_not_mounted_is_refused(table):
    """A mistyped unmount leaves behind the mount it was meant to take away."""
    with raises_rendered(MountError, "nothing is mounted at 'lib'"):
        table.remounted(unmount=["lib"])
    # A mount point below one that exists is not a match either.
    with raises_rendered(MountError, "nothing is mounted at 'ref/python'"):
        table.remounted(unmount=["ref/python"])


def test_a_surviving_read_only_mount_stays_read_only(tmp_path):
    stores = [SqliteStore(tmp_path / "root"), SqliteStore(tmp_path / "ref")]
    with MountedStore({"": stores[0], "ref": stores[1]}, read_only=["ref"]) as table:
        with SqliteStore(tmp_path / "extra") as extra:
            after = table.remounted(mount={"extra": extra})
        assert [m.prefix for m in after.read_only] == ["ref"]
        assert not after.resolve("extra").read_only


def test_a_replaced_mount_does_not_inherit_read_only(tmp_path):
    """A replacement states what it is; nothing carries over from what it replaced.

    The other way round is the failure worth refusing: a mount asked for
    read-write that came up read-only because something at that point once was,
    with nothing in the call saying so.
    """
    stores = [SqliteStore(tmp_path / "root"), SqliteStore(tmp_path / "ref")]
    with MountedStore({"": stores[0], "ref": stores[1]}, read_only=["ref"]) as table:
        with SqliteStore(tmp_path / "other") as other:
            after = table.remounted(mount={"ref": other})
            assert after.read_only == []

            again = table.remounted(mount={"ref": other}, read_only=["ref"])
            assert [m.prefix for m in again.read_only] == ["ref"]


def test_every_constructor_invariant_is_re_checked(table, tmp_path):
    """The result goes through ``__init__``, so this states it rather than restating them."""
    with SqliteStore(tmp_path / "extra") as extra:
        with raises_rendered(MountError, "may not be metadata"):
            table.remounted(mount={"lib/!title": extra})
        with raises_rendered(MountError, "cannot be mounted read-only"):
            table.remounted(mount={"extra": extra}, read_only=[keys.ROOT])
        with raises_rendered(MountError, "nothing is mounted at 'nowhere'"):
            table.remounted(mount={"extra": extra}, read_only=["nowhere"])


def test_two_spellings_of_one_prefix_are_a_duplicate(table, tmp_path):
    """The one duplicate ``__init__`` cannot see, because a dict has collapsed it."""
    with SqliteStore(tmp_path / "extra") as extra:
        with raises_rendered(MountError, "more than one store is mounted at 'extra'"):
            table.remounted(mount={"extra": extra, "/extra/": extra})


def test_remounting_nothing_is_a_new_table_holding_the_same_stores(table):
    after = table.remounted()
    assert after is not table
    assert [(m.prefix, m.store) for m in after] == [(m.prefix, m.store) for m in table]


# -- configuration ---------------------------------------------------------


def test_a_mount_spec_is_a_key_and_a_store_file():
    # The file is relative to the store directory and stays as written: the
    # spec is parsed here and resolved against a directory only when opened.
    assert parse_spec("ref=reference.sqlite") == ("ref", Spec(Path("reference.sqlite")))
    assert parse_spec("lib/ref=x")[0] == "lib/ref"


def test_a_mount_spec_may_carry_options_after_its_store_file():
    """``KEY=FILE,NAME=VALUE``: the mount(8) shape, and why it is that shape.

    An option written *inside* the value keeps one mount to one option
    occurrence, which is what leaves overriding an entry from a mount
    configuration a matter of replacing it whole. A second flag keyed by mount
    point would have needed a rule for what a later ``--mount`` at that point
    did to the options an earlier source set.
    """
    assert parse_spec("export=docs,type=files") == ("export", Spec(Path("docs"), "files"))
    assert parse_spec("export=docs") == ("export", Spec(Path("docs"), None))
    # The root takes the value half alone, and the same grammar.
    assert parse_options("docs,type=files") == Spec(Path("docs"), "files")
    # And it renders back to what it was read from, which is what a mount
    # table relies on: a file is defined as the options it stands for.
    assert unparse(Spec(Path("docs"), "files")) == "docs,type=files"
    assert unparse(Spec(Path("docs"))) == "docs"


def test_an_option_that_is_not_one_is_refused_rather_than_ignored():
    """The rule a mount configuration already follows for a field it does not know.

    A mount is read later, by somebody who is not watching, and an option that
    silently did nothing is the failure least likely to be noticed: a mount
    that is not the store it says reads as a store that is simply empty.
    """
    with raises_rendered(MountError, "not a mount option"):
        parse_spec("ref=r.sqlite,mode=fast")
    with raises_rendered(MountError, "is not an option"):
        parse_spec("ref=r.sqlite,files")
    with raises_rendered(MountError, "twice"):
        parse_spec("ref=r.sqlite,type=files,type=sqlite")
    # The value is not checked here: which backends exist is the store's
    # question, and a second list of their names kept here to answer it a
    # moment earlier is the duplicate vocabulary this grammar avoids.
    assert parse_spec("ref=r.sqlite,type=nonsense")[1].type == "nonsense"


def test_a_store_file_holding_the_option_delimiter_has_no_spelling():
    """The price of options in the value, paid where it is noticed.

    Refused in both directions: a comma typed after the file starts an option,
    and one that reached a ``Spec`` some other way -- a table in ``mounts.toml``
    -- is refused when it is rendered, because the argument it would render to
    reads back as something else.
    """
    with raises_rendered(MountError, "is not an option"):
        parse_spec("ref=a,b.sqlite")
    with raises_rendered(MountError, "no spelling that reads back as itself"):
        unparse(Spec(Path("a,b.sqlite")))


def test_a_mount_may_name_the_backend_that_keeps_it(tmp_path):
    """``type=files`` is the only way to mount a directory of files.

    Which backend keeps a store follows from its file extension, and a
    directory has none to read. So this is the case the option exists for, and
    the test is that the store really is a tree: a document written through the
    mount is a file on disk.
    """
    with open_mounts(tmp_path / "root", ["tree=documents,type=files"]) as table:
        table.store_document("tree/note", "written through the mount")
        assert table.retrieve_document("tree/note").content == "written through the mount"
    assert (tmp_path / "root" / "documents" / "note.md").read_text() == (
        "written through the mount"
    )


def test_a_spec_carries_every_option_and_renders_them_back_in_one_order():
    """Two options now, so the round trip is about more than one word.

    A parsed spec no longer knows the order they were written in, so
    ``unparse`` settles one -- what has to survive is what the options *say*,
    and two specs meaning the same thing rendering the same way is what a mount
    table's override comparison rests on.
    """
    spec = Spec(Path("bundle"), "files", "keep")
    assert parse_options("bundle,type=files,extensions=keep") == spec
    assert parse_options("bundle,extensions=keep,type=files") == spec
    assert unparse(spec) == "bundle,type=files,extensions=keep"
    assert unparse(Spec(Path("bundle"), None, "keep")) == "bundle,extensions=keep"
    assert parse_spec("docs=bundle,extensions=keep") == ("docs", Spec(Path("bundle"), None, "keep"))


def test_a_mount_may_name_how_its_file_names_line_up_with_keys(tmp_path):
    """``extensions=keep`` is what mounts a bundle whose documents link by name.

    The evidence is the link: the document says ``guide/intro.md``, so under
    this mapping that string is a key. Mounted the other way it is not, and
    every such link in the corpus names a key the store does not hold.
    """
    bundle = tmp_path / "root" / "bundle"
    (bundle / "guide").mkdir(parents=True)
    (bundle / "index.md").write_text("see [the guide](guide/intro.md)")
    (bundle / "guide" / "intro.md").write_text("# Intro")

    with open_mounts(tmp_path / "root", ["docs=bundle,type=files,extensions=keep"]) as table:
        assert table.retrieve_document("docs/guide/intro.md").content == "# Intro"
    with open_mounts(tmp_path / "root", ["docs=bundle,type=files"]) as table:
        assert table.retrieve_document("docs/guide/intro").content == "# Intro"


def test_a_backend_kept_in_a_file_refuses_a_mapping_it_has_no_question_about(tmp_path):
    """Refused rather than ignored, for the reason an unknown option is.

    How a file name lines up with a key is a question only a directory of files
    has. A database mounted with an answer to it read as though the option had
    worked would be the failure a mount configuration is least able to notice.
    """
    with raises_rendered(BackendError, "cannot be asked for 'keep' extensions"):
        with open_mounts(tmp_path / "root", ["ref=r.sqlite,extensions=keep"]):
            pass


def test_a_named_backend_that_does_not_exist_is_refused(tmp_path):
    """Unlike an unrecognised extension, which falls back to the default.

    An extension is a guess at what somebody meant and a ``type=`` is what they
    said. A mount that quietly opened as some other kind of store would read as
    a store that is simply empty, which is the one failure a mount
    configuration cannot notice.
    """
    with raises_rendered(BackendError, "there is no 'nonsense' backend"):
        with open_mounts(tmp_path / "root", ["ref=r.sqlite,type=nonsense"]):
            pass
    assert not (tmp_path / "root" / "r.sqlite").exists()


def test_the_root_mount_takes_the_same_options_as_any_other(tmp_path):
    """``--root-mount docs,type=files`` reads a tree as the whole store.

    The root is a mount like the others in everything but not having a mount
    point, so it takes the value half of the same grammar rather than a
    spelling of its own.
    """
    with open_mounts(tmp_path / "root", root_mount="documents,type=files") as table:
        table.store_document("note", "the tree is the store")
    assert (tmp_path / "root" / "documents" / "note.md").exists()


def test_a_tree_mount_is_a_name_inside_the_store_directory(tmp_path):
    """And earns every refusal a database mounted beside it earns.

    ``FilesystemStore`` is constructed at a path when it is an export target,
    which is a path somebody typed. A mount is not that: it is a name relative
    to ``--dir`` like every other store, so the same rule refuses an absolute
    one and one that climbs out.
    """
    with raises_rendered(StoreFileError, "absolute path"):
        open_mounts(tmp_path / "root", ["tree=/srv/documents,type=files"])
    with raises_rendered(StoreFileError, r"climbs out"):
        open_mounts(tmp_path / "root", ["tree=../documents,type=files"])
    # Refused before the directory it named was made, which for a tree is the
    # refusal doing something a database's would not: an unrefused one would
    # have left a directory outside --dir with nothing in it to explain itself.
    assert not (tmp_path / "documents").exists()


def test_a_mount_file_is_relative_to_the_store_directory(tmp_path):
    # An absolute path would make --dir a lie and a configuration unmovable;
    # `..` would reach outside the directory an operator named.
    with raises_rendered(StoreFileError, "absolute path"):
        open_mounts(tmp_path / "root", ["ref=/srv/reference.sqlite"])
    with raises_rendered(StoreFileError, r"climbs out"):
        open_mounts(tmp_path / "root", ["ref=../elsewhere.sqlite"])


def test_a_malformed_mount_spec_is_refused_before_anything_is_opened(tmp_path):
    with raises_rendered(MountError, "KEY=FILE form"):
        parse_spec("ref")
    with raises_rendered(MountError, "names no store file"):
        parse_spec("ref=")
    with raises_rendered(MountError, "no mount point"):
        parse_spec("=/srv/x")
    # And nothing was created for the mount that could not be described.
    with pytest.raises(MountError):
        open_mounts(tmp_path / "root", ["ref"])
    assert not (tmp_path / "root").exists()


def test_the_server_takes_repeated_mount_arguments():
    args = parse_args(
        [
            "--no-mount-config",
            "--dir",
            "/tmp/root",
            "--mount",
            "ref=ref.sqlite",
            "--mount",
            "lib=lib.sqlite",
        ]
    )
    assert args.mounts == ["ref=ref.sqlite", "lib=lib.sqlite"]
    assert parse_args(["--no-mount-config"]).mounts == []


def test_the_root_mount_defaults_to_the_usual_store_file():
    from outrage.store import default_store_file

    assert parse_args([]).root_mount == default_store_file()
    assert parse_args(["--root-mount", "main.sqlite"]).root_mount == "main.sqlite"


def test_mounts_open_together_and_close_together(tmp_path):
    # One directory, several files: the root mount and every --mount live side
    # by side in the directory --dir names.
    with open_mounts(tmp_path / "base", ["ref=reference.sqlite"]) as table:
        assert [m.prefix for m in table] == ["", "ref"]
        assert (tmp_path / "base" / "store.sqlite").exists()
        assert (tmp_path / "base" / "reference.sqlite").exists()


def test_the_root_mount_can_be_named(tmp_path):
    with open_mounts(tmp_path / "base", root_mount="main.sqlite") as table:
        assert table.root.store.path == tmp_path / "base" / "main.sqlite"
        assert not (tmp_path / "base" / "store.sqlite").exists()


def test_a_mount_file_may_sit_in_a_subdirectory(tmp_path):
    # Relative, not flat: nothing else would create the subdirectory, so the
    # store makes its own parent on the way in.
    with open_mounts(tmp_path / "base", ["ref=stores/reference.sqlite"]) as table:
        assert table.resolve("ref/x").mount.store.path.exists()
        assert (tmp_path / "base" / "stores" / "reference.sqlite").exists()


def test_the_instructions_name_the_root_readme_only(tmp_path):
    from outrage.server import NO_README, READ_README, instructions

    root = SqliteStore(tmp_path / "root")
    inner = SqliteStore(tmp_path / "inner")
    inner.store_document("readme", "The mounted store.")

    # A mounted store's readme is not named either: a session that has not read
    # the root's cannot act on a second one, and the mount shows up in a
    # listing anyway. So a mounted readme leaves the text saying there is none.
    with MountedStore({"": root, "ref": inner}) as table:
        assert NO_README in instructions(table)

    root.store_document("readme", "The root store.")
    with MountedStore({"": root, "ref": inner}) as table:
        text = instructions(table)
    assert READ_README in text
    assert "The root store." not in text
    assert "The mounted store." not in text


# -- one connection per thread, per store ---------------------------------


def test_every_mount_gets_its_own_connection_in_every_thread(table):
    """The per-thread tracking already spans stores, and this is what says so.

    ``SqliteStore`` holds its own ``threading.local``, so N stores in one thread is
    N connections rather than one shared between them -- the fix recorded in
    ``project/reference/planned/concurrency`` needed nothing added for mounts.
    Worth a test rather than a reading of the code, because the failure it
    guards against is the one that returned empty result sets and raised
    nothing.
    """
    import concurrent.futures

    def read_everything() -> list[str]:
        found = []
        for mount in table:
            found += [e.key for e in mount.store.list_keys(keys.ROOT).items]
        return found

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = [f.result() for f in [pool.submit(read_everything) for _ in range(24)]]

    assert results and all(r == results[0] for r in results)
    assert results[0]


def test_a_table_closes_every_store_it_holds(tmp_path):
    stores = [SqliteStore(tmp_path / "root"), SqliteStore(tmp_path / "ref")]
    with MountedStore({"": stores[0], "ref": stores[1]}):
        for store in stores:
            store.exists("a")  # opens this thread's connection
    # Asked of the tracking rather than of the connection: `SqliteStore.connection`
    # reopens on demand, so a closed store looks open again the moment it is
    # asked, and a test that read it would pass whether or not anything closed.
    for store in stores:
        assert store._local.conn is None


def test_two_things_worth_saying_are_both_said(tmp_path):
    """A note carries every reason, not whichever ran last."""
    root = SqliteStore(tmp_path / "root")
    inner = SqliteStore(tmp_path / "inner")
    root.store_document("lib/keep/below", "kept")
    inner.store_document("a", "x")

    with MountedStore({"": root, "lib/deep": inner}, read_only=["lib/deep"]) as table:
        server = build_server(table)
        result = call(server, "delete_keys", key="lib")
        # `remaining` crosses, so it counts the read-only mount's row too --
        # and then has to say that `recursive` would not reach it, or the
        # advice it gives is wrong about part of the number it just gave.
        assert result["remaining"] == 2
        assert result["mounts_kept"] == ["lib/deep"]
        assert "pass recursive=true" in result["note"]
        assert "refuse a delete" in result["note"]


def test_outrage_check_finds_a_key_that_predates_the_bound(tmp_path):
    """The discovery path for the one remaining way a join can fail.

    `Mount.outer` raises when it meets such a key, which is correct and late.
    This is what looks before anything tries.
    """
    from outrage import maintenance

    with SqliteStore(tmp_path) as store:
        store.store_document("ordinary", "fine")
        legacy = _deep_key(keys.MAX_SEGMENTS + 1)
        store.connection.execute(
            "INSERT INTO documents (key, doc_key, meta_name, parent, sort_key, content, "
            "format, updated_at) VALUES (?, ?, NULL, ?, ?, ?, 'markdown', "
            "'2026-01-01T00:00:00+00:00')",
            (
                legacy,
                legacy,
                keys.parse(legacy, max_segments=keys.MAX_JOINED_SEGMENTS).parent,
                keys.sort_form(legacy),
                "from an older outrage",
            ),
        )
        store.connection.commit()

        report = maintenance.check(store)
        deep = [p for p in report.problems if p.code == maintenance.KEYS_TOO_DEEP]
        assert len(deep) == 1
        assert "cannot be mounted" in deep[0].detail
        assert not report.sound

        # A store nobody has done that to says nothing about depth.
    with SqliteStore(tmp_path / "clean") as clean:
        clean.store_document("ordinary", "fine")
        assert not [
            p for p in maintenance.check(clean).problems if p.code == maintenance.KEYS_TOO_DEEP
        ]


# -- read-only mounts -----------------------------------------------------
#
# The motivating case of the whole feature: a shared read-mostly reference base
# beside a local read-write store. The refusal lives in the routing, so these
# drive it through the server wherever a caller would see it, and through the
# table where the question is about how the table was described.


@pytest.fixture
def read_only_table(tmp_path):
    """As `table`, but `ref` refuses writes and `lib/deep` still accepts them."""
    root = SqliteStore(tmp_path / "root")
    ref = SqliteStore(tmp_path / "ref")
    deep = SqliteStore(tmp_path / "deep")

    root.store_document("context/1/state", "Where we got to.", title="State")
    ref.store_document("", "The reference base.", title="Reference")
    ref.store_document("python/asyncio", "Event loops.", title="asyncio")
    deep.store_document("a", "Deep.", title="Deep")

    built = MountedStore({"": root, "ref": ref, "lib/deep": deep}, read_only=["ref"])
    yield built
    built.close()


@pytest.fixture
def read_only_server(read_only_table):
    return build_server(read_only_table)


def test_a_read_only_mount_refuses_a_write_below_it(read_only_server):
    message = call_expecting_error(
        read_only_server, "store_document", key="ref/python/asyncio", content="Rewritten."
    )
    assert "read-only" in message
    assert "ref" in message


def test_a_read_only_mount_refuses_a_write_at_the_mount_point(read_only_server):
    message = call_expecting_error(
        read_only_server, "store_document", key="ref", content="Rewritten."
    )
    assert "read-only" in message


def test_a_read_only_mount_refuses_an_allocating_write(read_only_server):
    """`?` must be refused too: it is the write that does not name its own key."""
    message = call_expecting_error(
        read_only_server, "store_document", key="ref/notes/?", content="New."
    )
    assert "read-only" in message


def test_a_read_only_mount_refuses_a_delete(read_only_server):
    message = call_expecting_error(read_only_server, "delete_keys", key="ref/python/asyncio")
    assert "read-only" in message


def test_a_refused_write_leaves_the_store_exactly_as_it_was(read_only_server, read_only_table):
    """The point of refusing in the routing: the store is never reached at all."""
    before = call(read_only_server, "read_document", key="ref/python/asyncio")
    call_expecting_error(
        read_only_server, "store_document", key="ref/python/asyncio", content="Rewritten."
    )
    after = call(read_only_server, "read_document", key="ref/python/asyncio")
    assert after["content"] == before["content"]
    assert after["updated_at"] == before["updated_at"]
    # And nothing was created alongside it either.
    assert call(read_only_server, "list_keys", key="ref/notes")["total"] == 0


def test_a_read_only_mount_still_reads(read_only_server):
    assert call(read_only_server, "read_document", key="ref")["content"] == ("The reference base.")
    assert call(read_only_server, "read_document", key="ref/python/asyncio")["content"] == (
        "Event loops."
    )
    titles = call(read_only_server, "get_documents", key="ref", meta_name=["title"])
    assert {d["key"] for d in titles["documents"]} == {"ref/!title", "ref/python/asyncio/!title"}


def test_a_listing_says_which_mount_is_read_only(read_only_server):
    entries = {e["key"]: e for e in call(read_only_server, "list_keys")["entries"]}
    assert entries["ref"]["kind"] == READ_ONLY_MOUNT_KIND
    # The writable mount is unchanged, so the kind is what distinguishes them.
    assert entries["lib"]["kind"] == "implicit"
    assert call(read_only_server, "list_keys", key="lib")["entries"][0]["kind"] == MOUNT_KIND


def test_a_writable_mount_is_unaffected(read_only_server):
    call(read_only_server, "store_document", key="lib/deep/b", content="Written.", title="B")
    assert call(read_only_server, "read_document", key="lib/deep/b")["content"] == "Written."


def test_the_root_is_unaffected(read_only_server):
    call(read_only_server, "store_document", key="context/2/task", content="Task.", title="Task")
    assert call(read_only_server, "read_document", key="context/2/task")["content"] == "Task."


def test_a_delete_above_a_read_only_mount_is_allowed_and_says_what_it_kept(read_only_table):
    """The delete resolves to the root, which is writable; the mount is untouched."""
    server = build_server(read_only_table)
    result = call(server, "delete_keys", key="", recursive=True)
    assert "ref" in result["mounts_kept"]
    assert call(server, "read_document", key="ref/python/asyncio")["content"] == "Event loops."


def test_a_read_only_flag_naming_nothing_mounted_is_refused(tmp_path):
    """A typo that would otherwise start a server with everything writable."""
    root = SqliteStore(tmp_path / "root")
    ref = SqliteStore(tmp_path / "ref")
    try:
        with pytest.raises(MountError) as raised:
            MountedStore({"": root, "ref": ref}, read_only=["reference"])
        assert "nothing is mounted at 'reference'" in messages.render(raised.value)
    finally:
        root.close()
        ref.close()


def test_the_root_cannot_be_mounted_read_only(tmp_path):
    root = SqliteStore(tmp_path / "root")
    try:
        with pytest.raises(MountError) as raised:
            MountedStore({"": root}, read_only=[""])
        assert "root" in str(raised.value)
    finally:
        root.close()


def test_a_read_only_mount_is_not_created_when_it_does_not_exist(tmp_path):
    """A store would happily make one, and an empty reference base reads as fine."""
    missing = tmp_path / "base" / "not-there.sqlite"
    with pytest.raises(MountError) as raised:
        open_mounts(tmp_path / "base", (), ["ref=not-there.sqlite"])
    assert "read-only mount" in messages.render(raised.value)
    assert not missing.exists()


def test_open_mounts_marks_only_the_read_only_specs(tmp_path):
    SqliteStore(tmp_path / "base", filename="ref.sqlite").close()
    SqliteStore(tmp_path / "base", filename="extra.sqlite").close()
    with open_mounts(tmp_path / "base", ["lib=extra.sqlite"], ["ref=ref.sqlite"]) as built:
        assert [m.prefix for m in built.read_only] == ["ref"]
        assert built.resolve("ref/x").read_only
        assert not built.resolve("lib/x").read_only
        assert not built.resolve("anything").read_only


def test_the_same_mount_point_cannot_be_both(tmp_path):
    SqliteStore(tmp_path / "base", filename="ref.sqlite").close()
    with pytest.raises(MountError) as raised:
        open_mounts(tmp_path / "base", ["ref=ref.sqlite"], ["ref=ref.sqlite"])
    assert "more than one store is mounted" in messages.render(raised.value)


def test_the_server_takes_mount_ro_from_the_command_line():
    args = parse_args(
        [
            "--no-mount-config",
            "--mount",
            "lib=lib.sqlite",
            "--mount-ro",
            "ref=ref.sqlite",
        ]
    )
    assert args.mounts == ["lib=lib.sqlite"]
    assert args.read_only_mounts == ["ref=ref.sqlite"]


def test_nothing_is_read_only_by_default(table):
    assert table.read_only == []
    assert not table.resolve("ref/python/asyncio").read_only


def test_the_server_reports_a_bad_mount_table_as_one_line(tmp_path, capsys):
    """`errors.py`'s rule, which the server did not follow: an answer, not a traceback."""
    from outrage.server import main

    assert main(["--dir", str(tmp_path / "root"), "--mount", "no-delimiter"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("outrage: ")
    assert "KEY=FILE" in err


def test_the_server_reports_a_missing_read_only_store_as_one_line(tmp_path, capsys):
    from outrage.server import main

    missing = tmp_path / "base" / "not-there.sqlite"
    assert main(["--dir", str(tmp_path / "base"), "--mount-ro", "ref=not-there.sqlite"]) == 1
    assert "read-only mount" in capsys.readouterr().err
    assert not missing.exists()


# -- a mount whose backend cannot be written -------------------------------


def a_packed_store(directory: Path, name: str = "ref.parquet") -> Path:
    from outrage.store_parquet import ParquetStore

    ParquetStore.build(
        directory / name,
        [
            ("python/os/path/join", "Join one or more path components.", None, None),
            ("python/os/path/join/!title", "os.path.join", None, None),
            ("python/os/getcwd", "Return the current working directory.", None, None),
        ],
    )
    return directory / name


def test_a_parquet_mount_is_read_only_without_anyone_saying_so(tmp_path):
    """The flag records a decision about a store that could be written.

    This records what the storage *is*. A mount that reported itself writable
    because nobody passed --mount-ro would be telling every caller something no
    write could make true, so the backend decides and the flag only adds.
    """
    pytest.importorskip("pyarrow", reason="the parquet backend is an optional extra")
    a_packed_store(tmp_path / "base")

    with open_mounts(tmp_path / "base", ["ref=ref.parquet"]) as table:
        mount = table.resolve("ref/python/os/getcwd")
        assert mount.read_only
        assert [m.prefix for m in table.read_only] == ["ref"]
        assert [m.kind for m in table.read_only] == [READ_ONLY_MOUNT_KIND]


def test_a_parquet_mount_refuses_a_write_without_offering_a_flag(tmp_path):
    """Which of the two refusals it is matters, and the store is what knows.

    A read-only *mount* tells the caller which flag to drop. A read-only
    *backend* must not, because no way of starting the server makes the write
    succeed - and the mount layer refuses first, so without this it would give
    advice that costs someone a restart to find out is wrong. Found by
    mounting a real one and writing to it.
    """
    pytest.importorskip("pyarrow", reason="the parquet backend is an optional extra")
    a_packed_store(tmp_path / "base")
    SqliteStore(tmp_path / "base", filename="flagged.sqlite").close()

    with open_mounts(tmp_path / "base", ["ref=ref.parquet"], ["ro=flagged.sqlite"]) as table:
        with raises_rendered(ReadOnlyStoreError, "No way of starting the server") as raised:
            table.resolve("ref/python/new").writable()
        assert raised.value.code == "store-read-only"

        # And a store that *could* be written still says how to change it --
        # both ways, since a tool caller and an operator have different ones.
        with raises_rendered(ReadOnlyMountError, "Mounting it again writable") as raised:
            table.resolve("ro/anything").writable()
        assert raised.value.code == "mount-read-only"

        # It must not offer the parquet store as a possible cause. It cannot be
        # one: `writable` asks the store before the configuration, so a backend
        # that refuses writes has already raised `store-read-only` above and
        # never reaches this code. The sentence said otherwise until
        # 2026-09-06, which is an explanation that cannot be the explanation --
        # worse than a shorter sentence, and the sort of thing only a reading
        # finds because both codes and both raises were correct.
        assert "parquet" not in messages.render(raised.value)


def test_a_parquet_mount_reads_through_the_server(tmp_path):
    """The point of the whole piece: a reference base behind a prefix."""
    pytest.importorskip("pyarrow", reason="the parquet backend is an optional extra")
    a_packed_store(tmp_path / "base")
    SqliteStore(tmp_path / "base", filename="store.sqlite").close()

    with open_mounts(tmp_path / "base", ["ref=ref.parquet"]) as table:
        server = build_server(table)
        read = call(server, "read_document", key="ref/python/os/getcwd")
        assert read["content"] == "Return the current working directory."

        survey = call(server, "get_documents", key="ref", meta_name=["title"])
        assert [d["key"] for d in survey["documents"]] == ["ref/python/os/path/join/!title"]

        listed = call(server, "list_keys", key="ref/python/os")
        assert [e["key"] for e in listed["entries"]] == [
            "ref/python/os/getcwd",
            "ref/python/os/path",
        ]

        refused = call_expecting_error(server, "store_document", key="ref/python/new", content="x")
        assert "written whole rather than updated in place" in refused
        # The key is named as the *caller* sees it, through the mount prefix.
        assert "'ref/python/new'" in refused


def test_a_parquet_store_cannot_be_the_root_mount(tmp_path):
    """The root owns every key no mount claims, so nothing would have anywhere
    to go. Reading one directly is a different question, and the command line's.
    """
    pytest.importorskip("pyarrow", reason="the parquet backend is an optional extra")
    a_packed_store(tmp_path / "base", "root.parquet")

    with raises_rendered(MountError, "nothing would have anywhere to go") as raised:
        open_mounts(tmp_path / "base", root_mount="root.parquet")
    assert raised.value.code == "mount-root-not-writable"


def test_a_missing_parquet_mount_is_refused_rather_than_created(tmp_path):
    """A SQLite mount that is not there is created empty; this one is not.

    The same protection --mount-ro gets from `mount-read-only-missing`, and it
    holds here without the flag: an empty reference base is one no read could
    ever contradict.
    """
    pytest.importorskip("pyarrow", reason="the parquet backend is an optional extra")

    with raises_rendered(BackendError, "no parquet store at"):
        open_mounts(tmp_path / "base", ["ref=absent.parquet"])
    assert not (tmp_path / "base" / "absent.parquet").exists()


# -- ?last across the table -------------------------------------------------


def test_last_sees_a_mount_point(table, server):
    # The root level of the namespace is `context`, `lib`, `notes` and `ref`,
    # and only two of those are keys any store holds. Without the mount half,
    # `?last` would name `notes` -- a key the caller can see it is not the
    # last one.
    assert table.last_child(keys.ROOT) == "ref"
    assert call(server, "list_keys", key="?last")["key"] == "ref"


def test_last_routes_into_the_store_it_resolves_to(server):
    # Resolved before the routing, which is the order that matters: a `?last`
    # naming a mount decides which store answers.
    assert call(server, "read_document", key="?last")["content"] == "The reference base."
    assert call(server, "read_document", key="?last/python/typing")["content"] == "Annotations."


def test_last_inside_a_mounted_store_is_named_from_outside(table, server):
    assert table.last_child("ref/python") == "typing"
    assert call(server, "get_documents", key="ref/?last")["key"] == "ref/python"


def test_last_at_a_level_holding_only_mounts(table):
    # `lib` exists because `lib/deep` is mounted; no store holds a row there.
    assert table.last_child("lib") == "deep"
    assert table.last_child("lib/deep") == "a"


def test_last_refuses_a_read_only_mount_the_way_a_named_key_would(tmp_path):
    root = SqliteStore(tmp_path / "root")
    ref = SqliteStore(tmp_path / "ref")
    ref.store_document("a", "Reference.")
    built = MountedStore({"": root, "ref": ref}, read_only={"ref"})
    try:
        message = call_expecting_error(
            build_server(built), "store_document", key="?last/b", content="x"
        )
        assert "ref" in message
    finally:
        built.close()


# -- the contract, as a comparison ----------------------------------------
#
# A mount table is a ``Store``, and ``test_store.py`` asks it the whole
# contract -- but as a table of *one*, because a mount point is a visible key
# and a boundary inside that corpus would disagree with assertions written
# about a single store while behaving exactly as designed.
#
# So crossing is checked the other way round, the way the parquet backend is:
# one corpus, put into a single store and into a four-store table that splits
# it, the same battery of calls put to each, and every answer asserted equal.
# That is stronger than expectations written down twice, because it compares
# against a live oracle -- and it guards precisely what the table exists to
# claim, that a caller cannot tell where the boundaries are.
#
# Two differences are declared rather than asserted away, and they are the
# whole of what a mount changes: a mount point lists as its own **kind**, which
# is the only place the fact is announced at all, and the two stores were
# written at different moments, so their timestamps differ.

#: Chosen for the places a boundary could show. Every mount point holds a
#: document *and* has children, so the inner store's root has to answer for
#: both; ``a/z`` and ``context`` sit behind mounts so the stretches either side
#: of one are non-empty; ``a-x`` sorts between ``a`` and its own children under
#: a naive ordering; and the numeric segments sort wrong as text.
_SPLIT_CORPUS = [
    ("", "root document"),
    ("!title", "The store itself"),
    ("a", "a body"),
    ("a/!title", "A"),
    ("a/!changelog", "what changed"),
    ("a/!changelog/!title", "Changelog"),
    ("a/!changelog/22", "note twenty-two"),
    ("a/!changelog/22/!title", "Note 22"),
    ("a/2", "a two"),
    ("a/10", "a ten"),
    ("a/10/!title", "A ten"),
    ("a/b", "a b body"),
    ("a/b/!title", "A b"),
    ("a/b/c", "deep"),
    ("a/b/c/!title", "Deep"),
    ("a/b/c/d", "deeper"),
    ("a/z", "a zed"),
    ("a-x", "adversarial sibling"),
    ("a-x/!title", "A-x"),
    ("b", "b body"),
    ("b/!title", "B"),
    ("b/1", "b one"),
    ("context/1/design", "design one"),
    ("context/10/design", "design ten"),
    ("context/10/design/!title", "Ten"),
    ("z", "last"),
]

#: Where the table breaks the corpus up. ``a/b/c`` inside ``a/b`` is a **nested**
#: mount, which is reached from the store containing it rather than from the
#: root -- so the recursion in ``_segments`` is under these assertions too.
_SPLIT_POINTS = ["a/b", "a/b/c", "b"]


def _routed(key: str) -> tuple[str, str]:
    """The mount that owns ``key`` in the split table, and its name inside it."""
    owner = ""
    for point in _SPLIT_POINTS:
        if (key == point or key.startswith(point + "/")) and len(point) > len(owner):
            owner = point
    return owner, key if not owner else key[len(owner) + 1 :]


@pytest.fixture
def whole(tmp_path):
    """The corpus in one store."""
    with SqliteStore(tmp_path / "one") as store:
        for key, content in _SPLIT_CORPUS:
            store.store_document(key, content)
        yield store


@pytest.fixture
def split(tmp_path):
    """The same corpus, cut across four stores behind one namespace."""
    stores = {keys.ROOT: SqliteStore(tmp_path / "many")}
    for point in _SPLIT_POINTS:
        name = point.replace(keys.DELIMITER, "-")
        stores[point] = SqliteStore(tmp_path / "many", filename=f"{name}.sqlite")
    for key, content in _SPLIT_CORPUS:
        owner, inner = _routed(key)
        stores[owner].store_document(inner, content)
    with MountedStore(stores) as table:
        yield table


#: A mount point announces itself with its ``kind`` and in no other way, so the
#: comparison takes that one word out. Everything else about the entry -- that
#: it is there, its size, its format -- has to match the single store, and
#: those are what a mount describing itself from the inner store's root is for.
def _one_kind(kind: str) -> str:
    return "document" if kind in (MOUNT_KIND, READ_ONLY_MOUNT_KIND) else kind


def _one_page(page):
    return (
        [(e.key, _one_kind(e.kind), e.size, e.format) for e in page.items],
        page.returned,
        page.total,
        page.total_chars,
        page.next_cursor,
    )


def _level(store, key):
    seen, totals = walk_level(store, key)
    return [(k, _one_kind(kind), size, form) for k, kind, size, form in seen], totals


def _entry(store, key):
    found = store.level_entry(key)
    return None if found is None else (found.key, _one_kind(found.kind), found.size, found.format)


def _read(store, key):
    got = store.retrieve_document(key)
    return got.key, got.content, got.format, got.offset, got.returned, got.total, got.next_offset


def _search_page(page):
    """Search facts excluding timestamps, which differ between the two corpora."""
    return (
        [
            (
                (
                    match.document.key,
                    _one_kind(match.document.kind),
                    match.document.size,
                    match.document.format,
                ),
                tuple(
                    (w.criterion, w.source_key, w.source, w.start, w.end) for w in match.witnesses
                ),
            )
            for match in page.matches
        ],
        page.matched,
        page.matched_chars,
        page.scanned,
        page.total_candidates,
        page.total_candidate_chars,
        page.next_cursor,
    )


_SPLIT_KEYS = [
    "",
    "a",
    "a/2",
    "a/10",
    "a/b",
    "a/b/c",
    "a/b/c/d",
    "a/z",
    "a-x",
    "b",
    "b/1",
    "context",
    "context/10",
    "z",
    "nope",
    "a/b/nope",
    "a/!changelog",
    "a/!changelog/22",
]

_SPLIT_RANGES = [
    UNBOUNDED,
    KeyRange(after="a"),
    KeyRange(after="a/b"),
    KeyRange(after_inclusive="a/b"),
    KeyRange(after_subtree="a/b"),
    KeyRange(before="a/b"),
    KeyRange(before_inclusive="a/b"),
    KeyRange(final_subtree="a/b"),
    KeyRange(after="a", before="z"),
    KeyRange(after_subtree="a", before_inclusive="context/10"),
    KeyRange(after_inclusive="a/b/c", final_subtree="b"),
    KeyRange(after="nope"),
]

_SPLIT_SUBTREES = [
    EVERYTHING,
    BoundedSubtree(key="a"),
    BoundedSubtree(key="a/!changelog"),
    BoundedSubtree(key="a", depth=1),
    BoundedSubtree(key="a", depth=2),
    BoundedSubtree(key="a/b"),
    BoundedSubtree(key="a/b", depth=0),
    BoundedSubtree(key="b"),
    BoundedSubtree(key=None, depth=1),
    BoundedSubtree(key=None, depth=2),
    BoundedSubtree(key="nope"),
]


def test_a_split_table_answers_every_read_the_way_one_store_holding_it_all_does(whole, split):
    """A caller cannot tell where the boundaries are.

    Written as one test rather than parametrised into thousands because what is
    asserted is a single claim -- *these are the same store* -- and a run
    reporting thousands of passes would say it thousands of times and locate a
    failure no better than the assertion does.
    """
    for key in _SPLIT_KEYS:
        answers_alike(whole, split, lambda s, k=key: s.exists(k))
        answers_alike(whole, split, lambda s, k=key: s.descendant_count(k))
        answers_alike(whole, split, lambda s, k=key: s.latest_change(k))
        answers_alike(whole, split, lambda s, k=key: s.latest_change(k, whole_subtree=True))
        answers_alike(whole, split, lambda s, k=key: _read(s, k))
        answers_alike(whole, split, lambda s, k=key: s.last_child(k))
        if key != keys.ROOT:
            answers_alike(whole, split, lambda s, k=key: _entry(s, k))
        for limit in (None, 1, 2, 100):
            answers_alike(
                whole,
                split,
                lambda s, k=key, n=limit: _one_page(s.list_keys(k, limit=n)),
            )
        answers_alike(whole, split, lambda s, k=key: _level(s, k))

    for subtree, key_range in itertools.product(_SPLIT_SUBTREES, _SPLIT_RANGES):
        for meta in (None, "title", ["title", "summary"]):
            answers_alike(
                whole,
                split,
                lambda s, t=subtree, r=key_range, m=meta: page_facts(
                    s.get_documents(t, key_range=r, meta_name=m)
                ),
            )
            answers_alike(
                whole,
                split,
                lambda s, t=subtree, r=key_range, m=meta: walk_documents(s, t, r, m),
            )
        for meta in ("title", ["title", "x"]):
            answers_alike(
                whole,
                split,
                lambda s, t=subtree, r=key_range, m=meta: page_facts(
                    s.keys_missing_meta(t, key_range=r, meta_name=m)
                ),
            )
            for window in _SPLIT_RANGES:
                answers_alike(
                    whole,
                    split,
                    lambda s, t=subtree, r=key_range, m=meta, w=window: s.missing_meta_stats(
                        t, key_range=r, window=w, meta_name=m, sample=3
                    ),
                )

    searches = [
        ([SearchCriterion("body", "contains", "document")], "any"),
        ([SearchCriterion("A", "contains", "metadata", ("title",))], "any"),
        (
            [
                SearchCriterion(r"\bdesign\b", "regex", "document"),
                SearchCriterion("Ten", "line", "metadata", ("title",)),
            ],
            "all",
        ),
    ]
    for subtree, key_range, (criteria, combine), scan_limit in itertools.product(
        _SPLIT_SUBTREES,
        (UNBOUNDED, KeyRange(after="a"), KeyRange(final_subtree="b")),
        searches,
        (None, 3),
    ):
        answers_alike(
            whole,
            split,
            lambda s, t=subtree, r=key_range, c=criteria, both=combine, n=scan_limit: _search_page(
                s.find_documents(
                    t,
                    criteria=c,
                    combine=both,
                    key_range=r,
                    scan_limit=n,
                )
            ),
        )


# -- what the contract found ----------------------------------------------


def test_a_key_with_a_mount_below_it_still_lists_as_what_it_is(tmp_path):
    """A mount *point* shadows; a mount below a key does not.

    The mirror image of ``planned/mounts/shadow-leak``. There, a survey offered
    keys that reading refused; here a listing hid a key that reading returns --
    a document with a mount somewhere beneath it came back as an implicit
    container, with no size, no format and no timestamp, while
    ``retrieve_document`` and ``level_entry`` both reported it as a document.
    A caller comparing the two would have had no way to tell which was lying.
    """
    outer = SqliteStore(tmp_path, filename="outer.sqlite")
    inner = SqliteStore(tmp_path, filename="inner.sqlite")
    outer.store_document("a", "really there")
    inner.store_document("", "the mount")
    with MountedStore({keys.ROOT: outer, "a/b": inner}) as table:
        (entry,) = table.list_keys().items
        assert (entry.key, entry.kind, entry.size) == ("a", "document", len("really there"))
        assert table.list_keys().total_chars == len("really there")
        assert entry == table.level_entry("a")
        # And the mount itself is still spliced into the level it stands in.
        (below,) = table.list_keys("a").items
        assert (below.key, below.kind, below.size) == ("a/b", MOUNT_KIND, len("the mount"))


def test_a_count_across_a_boundary_includes_the_mount_point_and_its_metadata(tmp_path):
    """Two rows a count taken from the inside cannot see.

    ``descendant_count`` measures from a store's own root and counts neither the
    row at it nor that row's metadata, because a key's metadata does not lie
    beneath the key. From outside, both of those rows *are* beneath the key
    being counted -- they are the mount point and its title -- so a count that
    forgot them told a caller to pass ``recursive`` for fewer keys than were
    really there.
    """
    outer = SqliteStore(tmp_path, filename="outer.sqlite")
    inner = SqliteStore(tmp_path, filename="inner.sqlite")
    outer.store_document("a", "a")
    inner.store_document("", "mounted")
    inner.store_document("!title", "Mounted")
    inner.store_document("c", "below")
    with MountedStore({keys.ROOT: outer, "a/b": inner}) as table:
        # a/b, a/b/!title, a/b/c.
        assert table.descendant_count("a") == 3
        assert table.descendant_count("a/b") == 1


def test_a_whole_subtree_count_across_a_boundary_does_not_count_the_unit_twice(tmp_path):
    """The two halves of a crossing count must not overlap.

    From outside, a mounted store's own root row and its metadata are both
    beneath the key being counted, so a count taken from the inside has to put
    them back. Under ``whole_subtree`` the inside already reports the metadata
    half -- that is what the flag asks for -- so only the root document row is
    missing, and reaching for ``_rows_at`` there would count the title twice.
    """
    from outrage import bulk

    outer = SqliteStore(tmp_path, filename="outer.sqlite")
    inner = SqliteStore(tmp_path, filename="inner.sqlite")
    outer.store_document("a", "a", title="A")
    inner.store_document("", "mounted")
    inner.store_document("!title", "Mounted")
    inner.store_document("c", "below")
    with MountedStore({keys.ROOT: outer, "a/b": inner}) as table:
        # a/b, a/b/!title, a/b/c -- and not a/!title, which a plain delete of
        # `a` would take with it.
        assert table.descendant_count("a") == 3
        # The same three, plus a/!title: four, not the five a doubled title
        # would give. Asserted against the walk rather than against a number,
        # because agreeing with the walk is the whole property -- that is what
        # a preview lists, and what the count is subtracted from.
        assert [entry.key for entry in bulk.walk(table, "a")] == [
            "a/!title",
            "a/b",
            "a/b/!title",
            "a/b/c",
        ]
        assert table.descendant_count("a", whole_subtree=True) == 4


def test_the_newest_change_crosses_a_boundary_the_way_a_count_does(tmp_path):
    """The maximum over the mounts, including the two rows the inside cannot see.

    A store mounted below the key answers about its own root as though it were
    the top of the world, so from outside its root row and that row's metadata
    are changes *beneath* the key -- the asymmetry ``_kept_below`` exists for,
    in the shape a maximum needs. Asked of the same corpus in one store, which
    is the only statement of what the right answer is.
    """
    single = SqliteStore(tmp_path, filename="single.sqlite")
    outer = SqliteStore(tmp_path, filename="outer.sqlite")
    inner = SqliteStore(tmp_path, filename="inner.sqlite")
    old, new, newest = (
        "2026-01-01T00:00:00+00:00",
        "2026-06-01T00:00:00+00:00",
        "2026-09-01T00:00:00+00:00",
    )
    for store in (single, outer):
        store.store_document("a/kept", "kept", updated_at=old)
    for key, moment in (("", new), ("!title", newest), ("c", old)):
        inner.store_document(key, "x", updated_at=moment)
        outside = keys.with_prefix("a/b", key) if key else "a/b"
        single.store_document(outside, "x", updated_at=moment)

    with MountedStore({keys.ROOT: outer, "a/b": inner}) as table:
        assert table.latest_change("a") == single.latest_change("a") == newest
        # The mount point's own row, which the store inside it reports as its
        # root and no count taken from in there can see.
        inner.store_document("!title", "x", updated_at=old)
        single.store_document("a/b/!title", "x", updated_at=old)
        assert table.latest_change("a") == single.latest_change("a") == new


def test_a_delete_across_a_boundary_is_refused_before_any_mount_is_asked(tmp_path):
    """The watermark is checked over the table, not handed to each store in turn.

    A recursive delete is one store's call at a time, so a mount asked to
    measure its own stretch would let the second refuse a run the first had
    already carried out. The whole point of the precondition is that a refused
    run has removed nothing.
    """
    outer = SqliteStore(tmp_path, filename="outer.sqlite")
    inner = SqliteStore(tmp_path, filename="inner.sqlite")
    old, new = "2026-01-01T00:00:00+00:00", "2026-06-01T00:00:00+00:00"
    outer.store_document("a", "a", updated_at=old)
    outer.store_document("a/kept", "kept", updated_at=old)
    inner.store_document("c", "below", updated_at=new)

    with MountedStore({keys.ROOT: outer, "a/b": inner}) as table:
        with raises_rendered(ChangedSinceError, "written at 2026-06-01"):
            table.delete("a", recursive=True, unchanged_since=old)
        # Nothing went, including from the mount that had not moved.
        assert table.exists("a/kept")
        assert table.exists("a/b/c")


def test_a_container_count_crosses_into_what_is_mounted_below_it(tmp_path):
    """A store counts to its own edge, and only the table can count past it.

    The same corpus in one store and in a table, asked the same question: the
    number a caller is given for what lies beneath a key has to be the same
    either way, or the mount is visible in an answer that is not about mounts.
    Before this, the table gave the root store's own count and left out every
    row of the mount -- 536 against the 12,780 in one mounted store alone, live.
    """
    single = SqliteStore(tmp_path, filename="single.sqlite")
    outer = SqliteStore(tmp_path, filename="outer.sqlite")
    inner = SqliteStore(tmp_path, filename="inner.sqlite")
    for store in (single, outer):
        store.store_document("a/kept", "kept", title="Kept")
    for key, content in (("", "the mount"), ("!title", "Mounted"), ("c", "below")):
        inner.store_document(key, content)
        single.store_document(keys.with_prefix("a/b", key) if key else "a/b", content)

    with MountedStore({keys.ROOT: outer, "a/b": inner}) as table:
        with raises_rendered(KeyNotFoundError, "5 key\\(s\\) lie beneath") as table_said:
            table.retrieve_document("a")
        with raises_rendered(KeyNotFoundError, "5 key\\(s\\) lie beneath") as store_said:
            single.retrieve_document("a")
        assert table_said.value.details == store_said.value.details
        assert table.descendant_count("a") == single.descendant_count("a") == 5


def test_reading_an_implicit_ancestor_of_a_mount_does_not_call_it_empty(tmp_path):
    """`key-not-found` says "nothing is stored at or below", which was false.

    No store holds a row at ``a`` when the only thing under it is the mount at
    ``a/b``: the outer one has nothing there and the inner one cannot see where
    it was mounted. The store answering said so, and the sentence it said it
    with claims the subtree is empty while a whole store sits in it -- and it
    withholds the advice that would have found it.

    Asked of a plain store holding the same keys as well, which is the
    specification the table is supposed to meet: what a caller is told about a
    key cannot depend on whether a mount is what put the content below it.
    """
    single = SqliteStore(tmp_path, filename="single.sqlite")
    outer = SqliteStore(tmp_path, filename="outer.sqlite")
    inner = SqliteStore(tmp_path, filename="inner.sqlite")
    inner.store_document("c", "below", title="Below")
    single.store_document("a/b/c", "below", title="Below")
    with MountedStore({keys.ROOT: outer, "a/b": inner}) as table:
        with raises_rendered(KeyNotFoundError, "no content stored at 'a'") as table_said:
            table.retrieve_document("a")
        with raises_rendered(KeyNotFoundError, "no content stored at 'a'") as store_said:
            single.retrieve_document("a")
        assert table_said.value.code == store_said.value.code == "key-is-a-container"
        assert table_said.value.details == store_said.value.details
        # And the advice, followed literally, answers -- the same advice, and
        # the same answer, as without a mount in it.
        assert [e.key for e in table.list_keys("a").items] == ["a/b"]
        assert [e.key for e in single.list_keys("a").items] == ["a/b"]

    # A key with genuinely nothing below it still gets the other sentence.
    with MountedStore({keys.ROOT: outer, "a/b": inner}) as table:
        with raises_rendered(KeyNotFoundError, "nothing is stored at or below 'z'"):
            table.retrieve_document("z")
        with raises_rendered(KeyNotFoundError, "nothing is stored at or below 'z'"):
            single.retrieve_document("z")


def test_level_entry_describes_an_implicit_ancestor_the_listing_offers(tmp_path):
    """The listing/level disagreement again, in the direction with no row to win.

    A mount at ``a/b`` puts ``a`` into the root listing through ``children``,
    and ``level_entry`` asked the store behind it, which has never heard of the
    key. One call offered ``a`` and the other said there was no such key on the
    level it came from -- the mirror of the shadowed document in
    ``test_a_listing_counts_the_mount_and_not_what_it_replaced``, where the
    store's own row is what settles it.

    Against a plain store holding the same keys, as above. The equivalence
    stops at the mount point itself, where ``kind`` is the one field that says
    a mount is there at all -- ``test_a_single_store_result_says_nothing_about
    _mounts`` is that half.
    """
    single = SqliteStore(tmp_path, filename="single.sqlite")
    outer = SqliteStore(tmp_path, filename="outer.sqlite")
    inner = SqliteStore(tmp_path, filename="inner.sqlite")
    inner.store_document("c", "below")
    single.store_document("a/b/c", "below")
    with MountedStore({keys.ROOT: outer, "a/b": inner}) as table:
        (entry,) = table.list_keys().items
        assert (entry.key, entry.kind) == ("a", "implicit")
        assert table.level_entry("a") == entry
        # An implicit ancestor is described the same whether a mount or a row
        # is what lies below it.
        assert table.level_entry("a") == single.level_entry("a")
        # A key nothing lies below is still nothing, and says so the same way.
        assert table.level_entry("z") is single.level_entry("z") is None


def test_a_copy_out_of_a_table_carries_every_store_it_spans(table, tmp_path):
    """The whole namespace, spelled the way the table spells it.

    A copy takes a ``Store`` as its source and a table *is* one, so a corpus
    kept in three files crosses into one as the keys a caller reads, not as
    the keys each mounted store knows itself by. That is the whole argument
    for the table being a store rather than a router in front of the server.
    """
    with SqliteStore(tmp_path / "one") as flat:
        transfers = list(flat.copy_from(table))
        assert [entry.key for entry in bulk.walk(flat, None) if entry.kind != "implicit"] == [
            "context/1/state",
            "context/1/state/!title",
            "lib/deep/a",
            "lib/deep/a/!title",
            "notes/readme.md",
            "notes/readme.md/!title",
            "ref",
            "ref/!title",
            "ref/python/asyncio",
            "ref/python/asyncio/!title",
            "ref/python/typing",
            "ref/python/typing/!title",
        ]
        assert flat.retrieve_document("ref").content == "The reference base."
        assert flat.retrieve_document("lib/deep/a").content == "Deep."
    # `lib` holds nothing itself and neither does the mount point at
    # `lib/deep`, whose store has no root document. Neither is a document that
    # failed to read; they are keys with nothing at them.
    assert all(transfer.action == WROTE for transfer in transfers)


def test_a_copy_into_a_table_lands_in_the_store_that_owns_the_key(table, tmp_path):
    """Routing, on the writing side, with no new code to do it.

    Each document is written through ``store_document``, which the table
    routes as it routes any write, so a copy into a table is distributed
    across its stores by the same rule that decides where a single write goes.
    """
    with SqliteStore(tmp_path / "source") as source:
        source.store_document("ref/python/asyncio", "Replaced.")
        source.store_document("lib/deep/b", "New.")
        list(table.copy_from(source, on_conflict=OVERWRITE))
    assert table.retrieve_document("ref/python/asyncio").content == "Replaced."
    assert table.retrieve_document("lib/deep/b").content == "New."
    # In the store that owns it, under the key that store knows it by.
    assert table.resolve("lib/deep/b").store.retrieve_document("b").content == "New."


def test_a_table_has_no_file_to_answer_for_and_is_not_a_file_store(tmp_path):
    """A backup or a check of one store out of three is not an answer.

    It would be a clean bill of health for the stores nobody looked at, which is
    the failure this project keeps finding rather than a convenience.

    **Said by the type rather than by a refusal**, since 2026-08-27. These eight
    were declared on the table to raise ``mount-has-no-file``, which was a class
    spelling out in eight sentences what one line of its inheritance now says:
    a table is a :class:`~outrage.store.Store` and not a
    :class:`~outrage.store.FileStore`. A caller holding one and wanting a file
    is holding the wrong thing, and this is how it asks.
    """
    with (
        MountedStore.single(SqliteStore(tmp_path / "a")) as table,
        SqliteStore(tmp_path / "b") as one,
    ):
        assert isinstance(table, Store)
        assert not isinstance(table, FileStore)
        assert isinstance(one, FileStore)
        for member in (
            "path",
            "directory",
            "stored_format_version",
            "backup",
            "backup_path",
            "audit_rows",
            "check_file",
            "repair",
        ):
            assert not hasattr(table, member), f"a table should not answer {member!r}"
            # Asked of an open store rather than of the class, because ``path``
            # and ``directory`` are settled per store and the other six are not.
            assert hasattr(one, member), f"{member!r} should be a file store's"


def test_a_mount_point_describes_itself_when_its_place_in_a_level_is_asked_for(tmp_path):
    """``level_entry`` and ``list_keys`` have to agree about a mount point.

    The store beneath it has no row there, and asking it would answer about
    whatever the mount shadows -- which is the row the listing has just declined
    to show. So the mount describes itself, from the inner store's root, in both.
    """
    outer = SqliteStore(tmp_path, filename="outer.sqlite")
    inner = SqliteStore(tmp_path, filename="inner.sqlite")
    outer.store_document("ref", "shadowed, and unreachable")
    inner.store_document("", "the reference base")
    with MountedStore({keys.ROOT: outer, "ref": inner}) as table:
        (listed,) = table.list_keys().items
        assert table.level_entry("ref") == listed
        assert (listed.kind, listed.size) == (MOUNT_KIND, len("the reference base"))


def test_a_failure_in_the_root_mount_still_spells_the_root_the_way_a_reader_reads_it(tmp_path):
    """The root is ``/`` in a sentence, never the empty string.

    Found live, comparing the whole tool surface against the server before this
    change. Naming used to happen at the MCP boundary with the *mount's* own
    outward function, which for the root mount is the identity -- so the front
    end's namer never ran and a failure at the root printed ``''``, "the empty
    string that reads like a missing value" the namer exists to prevent. Now
    that only a crossing renames, an error from the root mount reaches the
    front end untouched and is spelled by it.
    """
    store = SqliteStore(tmp_path)
    store.store_document("a", "below")
    with MountedStore.single(store) as table:
        server = build_server(table)
        assert "'/'" in call_expecting_error(server, "read_document", key="")


def test_read_only_mounts_below_a_key_are_named_without_being_deleted(tmp_path):
    """What a delete kept back is a sentence, so it is asked for separately.

    ``delete`` answers with the keys that went. A mount that refused is not a
    key, and folding it into that list would make a caller unable to tell the
    two apart.
    """
    root = SqliteStore(tmp_path, filename="root.sqlite")
    kept = SqliteStore(tmp_path, filename="kept.sqlite")
    root.store_document("a/x", "gone")
    kept.store_document("y", "safe")
    with MountedStore({keys.ROOT: root, "a/ref": kept}, read_only=["a/ref"]) as table:
        assert table.read_only_below("a") == ["a/ref"]
        assert table.delete("a", recursive=True) == ["a/x"]
        assert table.retrieve_document("a/ref/y").content == "safe"


def test_a_read_only_mount_the_key_is_inside_is_named_too(tmp_path):
    """The other direction, and the one a copy needs.

    ``read_only_below`` looks downwards, which is the whole question for a
    delete: the key names the top of what is being removed, so every mount that
    can refuse it is underneath. A copy names where documents *land*, and the
    mount that refuses them is as often the one they are landing inside -- above
    the key, and invisible to the downward question.
    """
    root = SqliteStore(tmp_path, filename="root.sqlite")
    kept = SqliteStore(tmp_path, filename="kept.sqlite")
    deeper = SqliteStore(tmp_path, filename="deeper.sqlite")
    with MountedStore(
        {keys.ROOT: root, "ref": kept, "ref/deep": deeper}, read_only=["ref", "ref/deep"]
    ) as table:
        assert table.read_only_below("ref/notes") == []
        assert table.read_only_at_or_below("ref/notes") == ["ref"]
        # Both, in key order, when the key is inside one and above another.
        assert table.read_only_at_or_below("ref") == ["ref", "ref/deep"]
        # A writable key is unchanged by the new question.
        assert table.read_only_at_or_below("elsewhere") == []


def test_a_copy_landing_inside_a_read_only_mount_names_it_once(tmp_path):
    """Twenty failures and no mount named, which is what live use looked like.

    Every document fails, each failure carries the whole read-only refusal, and
    the failures are *sampled* -- so the one fact reached the caller five times
    as an excerpt and never once as a sentence. `mounts_kept` and the wording
    for it both existed; the table was being asked the delete's question.
    """
    root = SqliteStore(tmp_path, filename="root.sqlite")
    kept = SqliteStore(tmp_path, filename="kept.sqlite")
    for n in range(3):
        root.store_document(f"notes/{n}", f"Note {n}.")

    with MountedStore({keys.ROOT: root, "ref": kept}, read_only=["ref"]) as table:
        server = build_server(table)
        result = call(server, "copy_tree", source="notes", target="ref/notes")

        assert result["mounts_kept"] == ["ref"]
        assert "refuse a write at or below" in result["note"]
        assert "'ref'" in result["note"]


def test_a_dry_run_and_real_copy_report_the_same_read_only_refusal(tmp_path):
    source = SqliteStore(tmp_path, filename="source.sqlite")
    root = SqliteStore(tmp_path, filename="root.sqlite")
    kept = SqliteStore(tmp_path, filename="kept.sqlite")
    source.store_document("notes/one", "One.")

    with source, MountedStore({keys.ROOT: root, "ref": kept}, read_only=["ref"]) as table:
        preview = list(table.copy_from(source, prefix="ref", dry_run=True))
        actual = list(table.copy_from(source, prefix="ref"))

        assert [transfer.action for transfer in preview] == [FAILED]
        assert [transfer.action for transfer in actual] == [FAILED]
        assert preview[0].error is not None and preview[0].error.code == "mount-read-only"
        assert actual[0].error is not None and actual[0].error.code == "mount-read-only"
        assert kept.list_keys().items == []


def test_an_error_from_inside_a_mount_names_the_key_the_caller_passed(tmp_path):
    """Renamed where the crossing happens, so every front end gets it.

    A store refuses a key by the name it knows, which is the name with the
    prefix taken off -- so a failed read of ``ref/nope`` used to report
    ``'nope'``, a key in no namespace anybody can pass back. Fixing it at the
    MCP boundary left the command line with no mount table to fix it with.
    """
    root = SqliteStore(tmp_path, filename="root.sqlite")
    inner = SqliteStore(tmp_path, filename="inner.sqlite")
    with MountedStore({keys.ROOT: root, "ref": inner}) as table:
        with raises_rendered(KeyNotFoundError, "'ref/nope'") as raised:
            table.retrieve_document("ref/nope")
        assert raised.value.details["key"] == "ref/nope"
