"""Tests for routing one key namespace across several stores.

Driven through the server's own dispatch wherever the behaviour is a caller's,
because the translation is only correct if it is correct at the boundary a
caller actually sees. The table itself is tested directly where the question is
about routing rather than about a tool result.
"""

from pathlib import Path
from typing import Any

import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from rage import keys
from rage.mounts import (
    MOUNT_KIND,
    READ_ONLY_MOUNT_KIND,
    MountError,
    Mounts,
    open_mounts,
    parse_spec,
)
from rage.server import build_server, parse_args
from rage.store import Store, StoreFileError


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
    root = Store(tmp_path / "root")
    ref = Store(tmp_path / "ref")
    deep = Store(tmp_path / "deep")

    root.store_document("context/1/state", "Where we got to.", title="State")
    root.store_document("notes/readme.md", "Notes about a file.", title="A file")

    ref.store_document("", "The reference base.", title="Reference")
    ref.store_document("python/asyncio", "Event loops.", title="asyncio")
    ref.store_document("python/typing", "Annotations.", title="typing")

    deep.store_document("a", "Deep.", title="Deep")

    built = Mounts({"": root, "ref": ref, "lib/deep": deep})
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
    with Store(tmp_path) as store, pytest.raises(MountError, match="at the root"):
        Mounts({"ref": store})


def test_a_mount_point_may_not_be_metadata(tmp_path):
    with Store(tmp_path) as store, pytest.raises(MountError, match="may not be metadata"):
        Mounts({"": store, "!title": store})


def test_mounts_below_a_key_are_the_ones_a_subtree_read_misses(table):
    assert [m.prefix for m in table.below(keys.ROOT)] == ["lib/deep", "ref"]
    assert [m.prefix for m in table.below("lib")] == ["lib/deep"]
    # A mount answers for its own point rather than being missed by it.
    assert table.below("ref") == []
    assert table.below("context") == []


# -- reading and writing across a boundary ---------------------------------


def test_a_read_crosses_a_mount_and_comes_back_named_from_outside(server):
    result = call(server, "retrieve_document", key="ref/python/asyncio")
    assert result["key"] == "ref/python/asyncio"
    assert result["content"] == "Event loops."


def test_the_mount_point_reads_the_inner_root(server):
    assert call(server, "retrieve_document", key="ref")["content"] == "The reference base."
    assert call(server, "retrieve_document", key="ref/!title")["content"] == "Reference"


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
    assert call(server, "retrieve_document", key="lib/deep/a")["content"] == "Deep."


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


# -- what stops at a boundary, and says so ---------------------------------


def test_a_survey_says_which_mounts_it_did_not_read(server):
    result = call(server, "get_documents", meta_name=["title"])
    assert result["mounts_not_searched"] == ["lib/deep", "ref"]
    assert "were not read" in result["note"]
    assert all(not key["key"].startswith("ref/") for key in result["documents"])


def test_a_survey_inside_a_mount_has_nothing_to_warn_about(server):
    result = call(server, "get_documents", key="ref", meta_name=["title"])
    assert "mounts_not_searched" not in result
    assert [d["key"] for d in result["documents"]] == [
        "ref/!title",
        "ref/python/asyncio/!title",
        "ref/python/typing/!title",
    ]


def test_keys_missing_meta_is_named_from_outside_and_says_what_it_skipped(server, table):
    table.resolve("ref").store.store_document("python/untitled", "No title.")
    result = call(server, "keys_missing_meta", key="ref")
    assert result["keys"] == ["ref/python/untitled"]
    assert "mounts_not_searched" not in result


def test_a_recursive_delete_stops_at_a_mount_and_says_so(server, table):
    result = call(server, "delete_keys", key="lib", recursive=True)
    assert result["mounts_kept"] == ["lib/deep"]
    assert "stops at a mount boundary" in result["note"]
    assert table.resolve("lib/deep").store.exists("a")


def test_a_single_store_result_says_nothing_about_mounts(tmp_path):
    with Store(tmp_path) as store:
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
    with Store(tmp_path) as store:
        store.store_document(_deep_key(keys.MAX_SEGMENTS), "at the limit")
        with pytest.raises(keys.InvalidKeyError, match="at most 64 are allowed"):
            store.store_document(_deep_key(keys.MAX_SEGMENTS + 1), "over it")


def test_a_mount_point_may_not_exceed_half_the_namespace(tmp_path):
    with Store(tmp_path) as store:
        Mounts({"": store, _deep_key(keys.MAX_SEGMENTS): store})
        with pytest.raises(keys.InvalidKeyError, match="at most 64 are allowed"):
            Mounts({"": store, _deep_key(keys.MAX_SEGMENTS + 1): store})
        with pytest.raises(keys.InvalidKeyError, match="at most 64 are allowed"):
            parse_spec(f"{_deep_key(keys.MAX_SEGMENTS + 1)}=/srv/x")


def test_two_full_halves_still_join(tmp_path):
    """The worst case the bounds allow, end to end through the server.

    A mount point at exactly the store bound holding a key at exactly the store
    bound: the joined key is `MAX_JOINED_SEGMENTS` long. This is the case that
    used to be dropped.

    Note what the deepest key cannot have: a title. Metadata is a segment, so a
    document at the store bound has no room for one *inside its own store* —
    which is why the joined bound needs no allowance for it. The store refuses
    it, and the namespace above never sees a key the store could not hold.
    """
    root = Store(tmp_path / "root")
    inner = Store(tmp_path / "inner")
    point = _deep_key(keys.MAX_SEGMENTS)
    deepest = _deep_key(keys.MAX_SEGMENTS)
    titled = _deep_key(keys.MAX_SEGMENTS - 1)
    inner.store_document(deepest, "as deep as it goes")
    inner.store_document(titled, "one shallower", title="Titled")

    with pytest.raises(keys.InvalidKeyError):
        inner.store_document(deepest, "x", title="no room for this")

    with Mounts({"": root, point: inner}) as table:
        joined = f"{point}/{deepest}"
        assert joined.count(keys.DELIMITER) + 1 == keys.MAX_JOINED_SEGMENTS
        assert keys.fits(joined)

        server = build_server(table)
        assert call(server, "retrieve_document", key=joined)["content"] == "as deep as it goes"

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
    root = Store(tmp_path / "root")
    inner = Store(tmp_path / "inner")
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
            "from an older rage",
        ),
    )
    inner.connection.commit()

    with Mounts({"": root, "old": inner}) as table:
        mount = table.resolve("old").mount
        with pytest.raises(MountError, match="has no name in this namespace"):
            mount.outer(legacy)


# -- shadowing -------------------------------------------------------------


def test_a_mount_shadows_what_the_store_beneath_it_holds(tmp_path):
    root = Store(tmp_path / "root")
    inner = Store(tmp_path / "inner")
    root.store_document("ref/hidden", "Unreachable.", title="Hidden")
    inner.store_document("shown", "Reachable.", title="Shown")

    with Mounts({"": root, "ref": inner}) as table:
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
    root = Store(tmp_path / "root")
    inner = Store(tmp_path / "inner")

    root.store_document("readme", "The readme.", title="Readme")
    root.store_document("project", "The index.", title="Project")
    root.store_document("project/reference/env", "How to run.", title="Env")
    root.store_document("project/untitled", "No title here.")
    root.store_document("zzz", "Last.", title="Last")

    inner.store_document("", "Mounted.", title="Mounted root")
    inner.store_document("shown", "Reachable.", title="Shown")

    with Mounts({"": root, "project": inner}) as built:
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
    assert survey(shadowed_server, meta_name=["title"]) == ["readme/!title", "zzz/!title"]
    assert survey(shadowed_server, depth=1) == ["readme", "zzz"]

    # And the titles the survey shows are the ones a read can reach.
    for key in survey(shadowed_server, meta_name=["title"]):
        assert call(shadowed_server, "retrieve_document", key=key)["content"]

    # The mount's own documents are not in it either, and the answer says so
    # rather than letting a total that looks whole imply otherwise. A listing
    # crosses the boundary; a query does not.
    result = call(shadowed_server, "get_documents", meta_name=["title"])
    assert result["mounts_not_searched"] == ["project"]


def test_a_shadowed_key_is_not_named_as_missing_metadata(shadowed_server):
    # `project/untitled` has no title and is unreachable. Naming it would send
    # a caller to a key that does not answer, which is the whole failure.
    assert call(shadowed_server, "keys_missing_meta")["keys"] == []


def test_without_meta_does_not_count_what_it_cannot_show(shadowed_server):
    result = call(shadowed_server, "get_documents", meta_name=["title"])
    assert result["without_meta"] == {"total": 0, "total_chars": 0, "sample": []}


def test_a_survey_counts_the_windows_it_actually_read(shadowed_server):
    result = call(shadowed_server, "get_documents", meta_name=["title"])
    assert result["total"] == 2 == result["returned"]
    # `Project`, the title of the document the mount shadows, is not among them.
    assert result["total_chars"] == len("Readme") + len("Last")


def test_the_mounts_own_title_is_what_the_survey_shows_at_the_mount_point(shadowed_server):
    # The mount point resolves to the mounted store, so `project/!title` is the
    # inner root's title and not the shadowed one underneath it.
    assert call(shadowed_server, "retrieve_document", key="project/!title")["content"] == (
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

    assert seen == ["readme/!title", "zzz/!title"]
    assert counted == 2
    assert sampled == ["aaa", "yyy"]
    assert len(sampled) == len(set(sampled)), "double counted across windows"
    assert call(server, "keys_missing_meta")["keys"] == sampled


def test_a_page_ending_on_a_window_edge_still_says_there_is_more(shadowing):
    # The case that would truncate the collection silently. The window in
    # front of the mount holds exactly one document, so the store fills the
    # page and reaches the window's end at the same moment and has no cursor of
    # its own to give. Whether there is another page is a question only the
    # windows behind it can answer.
    server = build_server(shadowing)
    page = call(server, "get_documents", meta_name=["title"], limit=1)

    assert [d["key"] for d in page["documents"]] == ["readme/!title"]
    assert page["next_cursor"] == "readme/!title"

    rest = call(server, "get_documents", meta_name=["title"], limit=1, after=page["next_cursor"])
    assert [d["key"] for d in rest["documents"]] == ["zzz/!title"]
    assert rest["next_cursor"] is None


def test_a_character_budget_is_spent_across_the_windows_not_per_window(shadowing):
    # One budget for the page, however many windows it is read in. Spent per
    # window instead, a page would return one budget's worth for each mount.
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

    assert seen == ["aaa", "readme", "yyy", "zzz"]


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
    root = Store(tmp_path / "root")
    inner = Store(tmp_path / "inner")
    root.store_document("ref/!title", "Stale title")
    inner.store_document("", "Mounted.", title="Mounted root")

    with Mounts({"": root, "ref": inner}) as table:
        listing = call(build_server(table), "list_keys")
        assert [e["key"] for e in listing["entries"]] == ["ref"]
        assert listing["total"] == 1
        assert listing["total_chars"] == len("Mounted.")


def test_a_nested_mount_leaves_no_empty_window(tmp_path):
    # Two mounts, one inside the other. The outer one's range already covers
    # the inner, and a window drawn between them would be empty.
    root = Store(tmp_path / "root")
    outer = Store(tmp_path / "outer")
    nested = Store(tmp_path / "nested")
    root.store_document("a", "A", title="A")
    root.store_document("lib/hidden", "Unreachable.", title="Hidden")
    root.store_document("lib/deep/alsohidden", "Unreachable.", title="Also")
    root.store_document("z", "Z", title="Z")
    outer.store_document("shown", "Reachable.", title="Shown")
    nested.store_document("deeper", "Reachable.", title="Deeper")

    with Mounts({"": root, "lib": outer, "lib/deep": nested}) as table:
        server = build_server(table)
        assert survey(server, meta_name=["title"]) == ["a/!title", "z/!title"]
        assert call(server, "get_documents", meta_name=["title"])["total"] == 2


def test_a_survey_inside_a_mount_still_stops_at_a_mount_below_it(tmp_path):
    # The windows are named as the *answering* store names them, so a mount
    # nested inside another is stepped over in that store's own key space.
    root = Store(tmp_path / "root")
    outer = Store(tmp_path / "outer")
    nested = Store(tmp_path / "nested")
    outer.store_document("a", "A", title="A")
    outer.store_document("deep/hidden", "Unreachable.", title="Hidden")
    nested.store_document("shown", "Reachable.", title="Shown")

    with Mounts({"": root, "lib": outer, "lib/deep": nested}) as table:
        server = build_server(table)
        result = call(server, "get_documents", key="lib", meta_name=["title"])
        assert [d["key"] for d in result["documents"]] == ["lib/a/!title"]
        assert result["mounts_not_searched"] == ["lib/deep"]


def test_nothing_changes_for_a_key_with_no_mount_below_it(table):
    # The single window case is the same query it always was, so a store with
    # no mount under the key answers exactly as it did before any of this.
    result = call(build_server(table), "get_documents", key="context", meta_name=["title"])
    assert [d["key"] for d in result["documents"]] == ["context/1/state/!title"]
    assert result["total"] == 1
    assert "mounts_not_searched" not in result


# -- configuration ---------------------------------------------------------


def test_a_mount_spec_is_a_key_and_a_store_file():
    # The file is relative to the store directory and stays as written: the
    # spec is parsed here and resolved against a directory only when opened.
    assert parse_spec("ref=reference.sqlite") == ("ref", Path("reference.sqlite"))
    assert parse_spec("lib/ref=x")[0] == "lib/ref"


def test_a_mount_file_is_relative_to_the_store_directory(tmp_path):
    # An absolute path would make --dir a lie and a configuration unmovable;
    # `..` would reach outside the directory an operator named.
    with pytest.raises(StoreFileError, match="absolute path"):
        open_mounts(tmp_path / "root", ["ref=/srv/reference.sqlite"])
    with pytest.raises(StoreFileError, match=r"climbs out"):
        open_mounts(tmp_path / "root", ["ref=../elsewhere.sqlite"])


def test_a_malformed_mount_spec_is_refused_before_anything_is_opened(tmp_path):
    with pytest.raises(MountError, match="KEY=FILE form"):
        parse_spec("ref")
    with pytest.raises(MountError, match="names no store file"):
        parse_spec("ref=")
    with pytest.raises(MountError, match="no mount point"):
        parse_spec("=/srv/x")
    # And nothing was created for the mount that could not be described.
    with pytest.raises(MountError):
        open_mounts(tmp_path / "root", ["ref"])
    assert not (tmp_path / "root").exists()


def test_the_server_takes_repeated_mount_arguments():
    args = parse_args(
        ["--dir", "/tmp/root", "--mount", "ref=ref.sqlite", "--mount", "lib=lib.sqlite"]
    )
    assert args.mounts == ["ref=ref.sqlite", "lib=lib.sqlite"]
    assert parse_args([]).mounts == []


def test_the_root_mount_defaults_to_the_usual_store_file():
    from rage.store import DB_FILENAME

    assert parse_args([]).root_mount == DB_FILENAME
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


def test_the_instructions_carry_the_root_readme(tmp_path):
    from rage.server import instructions

    root = Store(tmp_path / "root")
    inner = Store(tmp_path / "inner")
    root.store_document("readme", "The root store.")
    inner.store_document("readme", "The mounted store.")
    with Mounts({"": root, "ref": inner}) as table:
        text = instructions(table)
    assert "The root store." in text
    assert "The mounted store." not in text


# -- one connection per thread, per store ---------------------------------


def test_every_mount_gets_its_own_connection_in_every_thread(table):
    """The per-thread tracking already spans stores, and this is what says so.

    ``Store`` holds its own ``threading.local``, so N stores in one thread is
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
    stores = [Store(tmp_path / "root"), Store(tmp_path / "ref")]
    with Mounts({"": stores[0], "ref": stores[1]}):
        for store in stores:
            store.exists("a")  # opens this thread's connection
    # Asked of the tracking rather than of the connection: `Store.connection`
    # reopens on demand, so a closed store looks open again the moment it is
    # asked, and a test that read it would pass whether or not anything closed.
    for store in stores:
        assert store._local.conn is None


def test_two_things_worth_saying_are_both_said(tmp_path):
    """A note carries every reason, not whichever ran last."""
    root = Store(tmp_path / "root")
    inner = Store(tmp_path / "inner")
    root.store_document("lib/keep/below", "kept")
    inner.store_document("a", "x")

    with Mounts({"": root, "lib/deep": inner}) as table:
        server = build_server(table)
        result = call(server, "delete_keys", key="lib")
        assert result["remaining"] == 1
        assert result["mounts_kept"] == ["lib/deep"]
        assert "pass recursive=true" in result["note"]
        assert "stops at a mount boundary" in result["note"]


def test_rage_check_finds_a_key_that_predates_the_bound(tmp_path):
    """The discovery path for the one remaining way a join can fail.

    `Mount.outer` raises when it meets such a key, which is correct and late.
    This is what looks before anything tries.
    """
    from rage import maintenance

    with Store(tmp_path) as store:
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
                "from an older rage",
            ),
        )
        store.connection.commit()

        report = maintenance.check(store)
        deep = [p for p in report.problems if "more than 64 segments" in p.summary]
        assert len(deep) == 1
        assert "cannot be mounted" in deep[0].detail
        assert not report.sound

        # A store nobody has done that to says nothing about depth.
    with Store(tmp_path / "clean") as clean:
        clean.store_document("ordinary", "fine")
        assert not [p for p in maintenance.check(clean).problems if "segments" in p.summary]


# -- read-only mounts -----------------------------------------------------
#
# The motivating case of the whole feature: a shared read-mostly reference base
# beside a local read-write store. The refusal lives in the routing, so these
# drive it through the server wherever a caller would see it, and through the
# table where the question is about how the table was described.


@pytest.fixture
def read_only_table(tmp_path):
    """As `table`, but `ref` refuses writes and `lib/deep` still accepts them."""
    root = Store(tmp_path / "root")
    ref = Store(tmp_path / "ref")
    deep = Store(tmp_path / "deep")

    root.store_document("context/1/state", "Where we got to.", title="State")
    ref.store_document("", "The reference base.", title="Reference")
    ref.store_document("python/asyncio", "Event loops.", title="asyncio")
    deep.store_document("a", "Deep.", title="Deep")

    built = Mounts({"": root, "ref": ref, "lib/deep": deep}, read_only=["ref"])
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
    before = call(read_only_server, "retrieve_document", key="ref/python/asyncio")
    call_expecting_error(
        read_only_server, "store_document", key="ref/python/asyncio", content="Rewritten."
    )
    after = call(read_only_server, "retrieve_document", key="ref/python/asyncio")
    assert after["content"] == before["content"]
    assert after["updated_at"] == before["updated_at"]
    # And nothing was created alongside it either.
    assert call(read_only_server, "list_keys", key="ref/notes")["total"] == 0


def test_a_read_only_mount_still_reads(read_only_server):
    assert call(read_only_server, "retrieve_document", key="ref")["content"] == (
        "The reference base."
    )
    assert call(read_only_server, "retrieve_document", key="ref/python/asyncio")["content"] == (
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
    assert call(read_only_server, "retrieve_document", key="lib/deep/b")["content"] == "Written."


def test_the_root_is_unaffected(read_only_server):
    call(read_only_server, "store_document", key="context/2/task", content="Task.", title="Task")
    assert call(read_only_server, "retrieve_document", key="context/2/task")["content"] == "Task."


def test_a_delete_above_a_read_only_mount_is_allowed_and_says_what_it_kept(read_only_table):
    """The delete resolves to the root, which is writable; the mount is untouched."""
    server = build_server(read_only_table)
    result = call(server, "delete_keys", key="", recursive=True)
    assert "ref" in result["mounts_kept"]
    assert call(server, "retrieve_document", key="ref/python/asyncio")["content"] == "Event loops."


def test_a_read_only_flag_naming_nothing_mounted_is_refused(tmp_path):
    """A typo that would otherwise start a server with everything writable."""
    root = Store(tmp_path / "root")
    ref = Store(tmp_path / "ref")
    try:
        with pytest.raises(MountError) as raised:
            Mounts({"": root, "ref": ref}, read_only=["reference"])
        assert "nothing is mounted at 'reference'" in str(raised.value)
    finally:
        root.close()
        ref.close()


def test_the_root_cannot_be_mounted_read_only(tmp_path):
    root = Store(tmp_path / "root")
    try:
        with pytest.raises(MountError) as raised:
            Mounts({"": root}, read_only=[""])
        assert "root" in str(raised.value)
    finally:
        root.close()


def test_a_read_only_mount_is_not_created_when_it_does_not_exist(tmp_path):
    """`Store` would happily make one, and an empty reference base reads as fine."""
    missing = tmp_path / "base" / "not-there.sqlite"
    with pytest.raises(MountError) as raised:
        open_mounts(tmp_path / "base", (), ["ref=not-there.sqlite"])
    assert "read-only mount" in str(raised.value)
    assert not missing.exists()


def test_open_mounts_marks_only_the_read_only_specs(tmp_path):
    Store(tmp_path / "base", filename="ref.sqlite").close()
    Store(tmp_path / "base", filename="extra.sqlite").close()
    with open_mounts(
        tmp_path / "base", ["lib=extra.sqlite"], ["ref=ref.sqlite"]
    ) as built:
        assert [m.prefix for m in built.read_only] == ["ref"]
        assert built.resolve("ref/x").read_only
        assert not built.resolve("lib/x").read_only
        assert not built.resolve("anything").read_only


def test_the_same_mount_point_cannot_be_both(tmp_path):
    Store(tmp_path / "base", filename="ref.sqlite").close()
    with pytest.raises(MountError) as raised:
        open_mounts(tmp_path / "base", ["ref=ref.sqlite"], ["ref=ref.sqlite"])
    assert "more than one store is mounted" in str(raised.value)


def test_the_server_takes_mount_ro_from_the_command_line():
    args = parse_args(["--mount", "lib=lib.sqlite", "--mount-ro", "ref=ref.sqlite"])
    assert args.mounts == ["lib=lib.sqlite"]
    assert args.read_only_mounts == ["ref=ref.sqlite"]


def test_nothing_is_read_only_by_default(table):
    assert table.read_only == []
    assert not table.resolve("ref/python/asyncio").read_only


def test_the_server_reports_a_bad_mount_table_as_one_line(tmp_path, capsys):
    """`errors.py`'s rule, which the server did not follow: an answer, not a traceback."""
    from rage.server import main

    assert main(["--dir", str(tmp_path / "root"), "--mount", "no-delimiter"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("rage: ")
    assert "KEY=FILE" in err


def test_the_server_reports_a_missing_read_only_store_as_one_line(tmp_path, capsys):
    from rage.server import main

    missing = tmp_path / "base" / "not-there.sqlite"
    assert main(["--dir", str(tmp_path / "base"), "--mount-ro", "ref=not-there.sqlite"]) == 1
    assert "read-only mount" in capsys.readouterr().err
    assert not missing.exists()
