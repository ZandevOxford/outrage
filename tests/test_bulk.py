"""Tests for bulk import and export.

Two halves. The mapping between a key and a path is a pure function and is
tested as one, in both directions and on the keys that do not have an obvious
path at all. The transfers are tested for what they refuse as much as for what
they move: a run that stops, skips or fails has to say so, since the exit
status and the report are the only parts of that a caller ever sees.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

import pytest
from conftest import raises_rendered

from outrage import bulk
from outrage.keys import InvalidKeyError
from outrage.store import FORMATS
from outrage.store_sqlite import SqliteStore


@pytest.fixture
def store(tmp_path):
    with SqliteStore(tmp_path / "store") as opened:
        yield opened


@pytest.fixture
def populated(store):
    store.store_document("project", "# Project", title="The project")
    store.store_document("project/reference/env", '{"python": "3.14"}', title="Env")
    store.store_document("notes/src/myfile.py", "note about a file")
    return store


def actions(transfers) -> list[tuple[str, str | None]]:
    return [(transfer.action, transfer.key) for transfer in transfers]


# -- the mapping ---------------------------------------------------------


@pytest.mark.parametrize(
    ("key", "format", "path"),
    [
        ("a", "markdown", "a.md"),
        ("a/b", "markdown", "a/b.md"),
        ("a/b", "json", "a/b.json"),
        ("a/b", "text", "a/b.txt"),
        ("a/b", "html", "a/b.html"),
        ("a/b/!title", "markdown", "a/b/!title.md"),
        ("notes/src/myfile.py", "markdown", "notes/src/myfile.py.md"),
    ],
)
def test_a_key_maps_to_a_path_and_back(key, format, path):
    assert bulk.path_for_key(key, format) == PurePosixPath(path)
    assert bulk.key_for_path(path) == (key, format)


def test_a_document_and_its_container_are_a_file_beside_a_directory(populated):
    # The whole reason documents carry an extension: `project` is a document
    # and also has a subtree, and no path is both a file and a directory.
    assert bulk.path_for_key("project", "markdown") == PurePosixPath("project.md")
    assert bulk.path_for_key("project/reference/env", "json").parts[:2] == ("project", "reference")


def test_a_name_carrying_no_known_extension_is_kept_whole():
    assert bulk.key_for_path("src/myfile.py") == ("src/myfile.py", None)
    assert bulk.key_for_path("plain") == ("plain", None)
    # `.htm` and `.text` are near misses on purpose: an export never writes
    # either, so an import reads them as part of the name rather than
    # stripping a suffix nothing here put there.
    assert bulk.key_for_path("page.htm") == ("page.htm", None)
    assert bulk.key_for_path("notes.text") == ("notes.text", None)


def test_every_stored_format_has_an_extension():
    # The mapping is what an export names a file by, so a format the store
    # accepts and this does not know would be exported as markdown and import
    # back as something else.
    assert set(bulk.EXTENSION_BY_FORMAT) == set(FORMATS)
    assert len(set(bulk.EXTENSION_BY_FORMAT.values())) == len(FORMATS)


def test_a_prefix_grafts_the_tree_somewhere_else():
    assert bulk.key_for_path("b.md", "a") == ("a/b", "markdown")
    assert bulk.key_for_path("x/y.md", "a/b") == ("a/b/x/y", "markdown")


def test_a_traversing_segment_has_no_path():
    # `.` and `..` became legal segments when the grammar widened to mirror a
    # filesystem. As path components they climb out of the directory being
    # written, so the key is refused rather than followed.
    for key in ("a/../b", "a/./b", ".."):
        with pytest.raises(bulk.UnmappableError):
            bulk.path_for_key(key, "markdown")


def test_a_file_named_for_the_wildcard_is_refused():
    # Reaching store_document, a whole segment of `?` means "allocate me a
    # number", so an import would invent keys instead of mirroring the source.
    with pytest.raises(InvalidKeyError):
        bulk.key_for_path("a/?.md")


# -- export --------------------------------------------------------------


def test_export_writes_documents_and_their_metadata(populated, tmp_path):
    target = tmp_path / "out"

    moved = list(bulk.export_tree(populated, None, target))

    assert [transfer.key for transfer in moved] == [
        "notes/src/myfile.py",
        "project",
        "project/!title",
        "project/reference/env",
        "project/reference/env/!title",
    ]
    assert (target / "project.md").read_text() == "# Project"
    # A survey by title is worth nothing if the export it came from left every
    # title behind.
    assert (target / "project/!title.md").read_text() == "The project"
    assert (target / "project/reference/env.json").read_text() == '{"python": "3.14"}'


def test_export_of_a_subtree_writes_the_path_it_came_from(populated, tmp_path):
    target = tmp_path / "out"

    list(bulk.export_tree(populated, "project/reference", target))

    # Full keys rather than paths relative to the key asked for, which is what
    # makes an exported subtree import back to where it was.
    assert (target / "project/reference/env.json").exists()
    assert not (target / "env.json").exists()


def test_export_of_a_key_includes_the_document_stored_at_it(populated, tmp_path):
    target = tmp_path / "out"

    moved = list(bulk.export_tree(populated, "project", target))

    # `walk` lists what is below a key, which is right for a listing and wrong
    # for an export: a key is a document and a container at once.
    assert moved[0].key == "project"
    assert (target / "project.md").read_text() == "# Project"


def test_export_and_import_round_trip_every_key(populated, tmp_path):
    target = tmp_path / "out"
    list(bulk.export_tree(populated, None, target))
    before = {
        entry.key: populated.retrieve_document(entry.key)
        for entry in bulk.walk(populated, None)
        if entry.kind != "implicit"
    }

    with SqliteStore(tmp_path / "fresh") as fresh:
        list(bulk.import_tree(fresh, target))
        after = {
            entry.key: fresh.retrieve_document(entry.key)
            for entry in bulk.walk(fresh, None)
            if entry.kind != "implicit"
        }

    assert after.keys() == before.keys()
    for key, excerpt in before.items():
        assert after[key].content == excerpt.content
        assert after[key].format == excerpt.format


def test_export_leaves_a_file_that_is_already_there(populated, tmp_path):
    target = tmp_path / "out"
    (target / "project").mkdir(parents=True)
    (target / "project/!title.md").write_text("mine, not the store's")

    moved = list(bulk.export_tree(populated, "project", target))

    assert (bulk.SKIPPED, "project/!title") in actions(moved)
    assert (target / "project/!title.md").read_text() == "mine, not the store's"


def test_export_overwrites_when_asked(populated, tmp_path):
    target = tmp_path / "out"
    (target / "project").mkdir(parents=True)
    (target / "project/!title.md").write_text("mine, not the store's")

    moved = list(bulk.export_tree(populated, "project", target, on_conflict=bulk.OVERWRITE))

    assert (bulk.WROTE, "project/!title") in actions(moved)
    assert (target / "project/!title.md").read_text() == "The project"


def test_export_stops_at_the_first_conflict_and_says_where(populated, tmp_path):
    target = tmp_path / "out"
    (target / "project").mkdir(parents=True)
    (target / "project/!title.md").write_text("mine")

    moved = list(bulk.export_tree(populated, "project", target, on_conflict=bulk.STOP))

    assert moved[-1].action == bulk.STOPPED
    assert moved[-1].key == "project/!title"
    # Everything before the conflict stands, and nothing after it was tried:
    # what a stop can honestly promise, and all of it.
    assert (target / "project.md").exists()
    assert not (target / "project/reference/env.json").exists()


def test_export_dry_run_writes_nothing_and_reports_the_same(populated, tmp_path):
    target = tmp_path / "out"

    moved = list(bulk.export_tree(populated, None, target, dry_run=True))

    assert [transfer.action for transfer in moved] == [bulk.WROTE] * 5
    assert not target.exists()


def test_export_refuses_to_write_outside_the_directory(store, tmp_path):
    store.store_document("a/../escaped", "out of the tree")
    target = tmp_path / "out"

    moved = list(bulk.export_tree(store, None, target))

    assert [transfer.action for transfer in moved] == [bulk.FAILED]
    assert not (tmp_path / "escaped.md").exists()


def test_export_reports_a_file_it_cannot_write_and_carries_on(populated, tmp_path):
    target = tmp_path / "out"
    target.mkdir()
    # A plain file where a document's directory has to go: the store cannot
    # help with this and the caller has to be told which key it cost.
    (target / "project").write_text("in the way")

    moved = list(bulk.export_tree(populated, None, target))

    assert (bulk.FAILED, "project/!title") in actions(moved)
    assert (bulk.WROTE, "notes/src/myfile.py") in actions(moved)


def test_export_writes_as_it_goes(populated, tmp_path):
    target = tmp_path / "out"

    transfers = bulk.export_tree(populated, None, target)
    first = next(transfers)

    # Lazy, not merely streamed in name: an export that reads the subtree
    # before writing anything fails at exactly the size an export matters at.
    assert first.key == "notes/src/myfile.py"
    assert [path.name for path in target.rglob("*.md")] == ["myfile.py.md"]


# -- import --------------------------------------------------------------


def a_tree(root: Path) -> Path:
    (root / "project/reference").mkdir(parents=True)
    (root / "project.md").write_text("# Project")
    (root / "project/!title.md").write_text("The project")
    (root / "project/reference/env.json").write_text('{"python": "3.14"}')
    return root


def test_import_stores_a_directory_as_documents(store, tmp_path):
    a_tree(tmp_path / "in")

    moved = list(bulk.import_tree(store, tmp_path / "in"))

    assert [transfer.key for transfer in moved] == [
        "project/!title",
        "project/reference/env",
        "project",
    ]
    assert store.retrieve_document("project").content == "# Project"
    assert store.retrieve_document("project/reference/env").format == "json"


def test_import_stores_beneath_a_key(store, tmp_path):
    a_tree(tmp_path / "in")

    list(bulk.import_tree(store, tmp_path / "in", "archive/2026"))

    assert store.retrieve_document("archive/2026/project").content == "# Project"


def test_import_leaves_a_key_that_already_holds_something(store, tmp_path):
    a_tree(tmp_path / "in")
    store.store_document("project", "mine, not the file's")

    moved = list(bulk.import_tree(store, tmp_path / "in"))

    assert (bulk.SKIPPED, "project") in actions(moved)
    assert store.retrieve_document("project").content == "mine, not the file's"


def test_import_overwrites_when_asked(store, tmp_path):
    a_tree(tmp_path / "in")
    store.store_document("project", "mine, not the file's")

    moved = list(bulk.import_tree(store, tmp_path / "in", on_conflict=bulk.OVERWRITE))

    assert (bulk.WROTE, "project") in actions(moved)
    assert store.retrieve_document("project").content == "# Project"


def test_import_stops_at_the_first_conflict_keeping_what_it_wrote(store, tmp_path):
    a_tree(tmp_path / "in")
    store.store_document("project", "mine")

    moved = list(bulk.import_tree(store, tmp_path / "in", on_conflict=bulk.STOP))

    assert moved[-1].action == bulk.STOPPED
    assert moved[-1].key == "project"
    # The two files before it in the walk are in, and stay in. A stop is not a
    # rollback, and the report is what makes the difference visible.
    assert store.exists("project/!title")


def test_import_dry_run_stores_nothing(store, tmp_path):
    a_tree(tmp_path / "in")

    moved = list(bulk.import_tree(store, tmp_path / "in", dry_run=True))

    assert [transfer.action for transfer in moved] == [bulk.WROTE] * 3
    assert not store.exists("project")


def test_import_skips_hidden_files_unless_asked(store, tmp_path):
    source = a_tree(tmp_path / "in")
    (source / ".DS_Store").write_bytes(b"junk")
    (source / ".hidden").mkdir()
    (source / ".hidden/secret.md").write_text("not asked for")

    assert "hidden" not in str(actions(bulk.import_tree(store, source)))

    with SqliteStore(tmp_path / "other") as other:
        moved = list(bulk.import_tree(other, source, hidden=True))

    assert other_keys(moved) >= {".DS_Store", ".hidden/secret"}


def other_keys(transfers) -> set[str]:
    return {transfer.key for transfer in transfers if transfer.key is not None}


def test_import_does_not_follow_a_symlink(store, tmp_path):
    source = a_tree(tmp_path / "in")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "elsewhere.md").write_text("not in the tree")
    (source / "link").symlink_to(outside)

    moved = list(bulk.import_tree(store, source))

    # Reported rather than followed: a link out imports what nobody named, and
    # a link back in imports the same documents twice under two keys.
    assert (bulk.SKIPPED, None) in actions(moved)
    assert not store.exists("link/elsewhere")


def test_import_reports_a_file_it_cannot_read_and_carries_on(store, tmp_path):
    source = a_tree(tmp_path / "in")
    (source / "binary.md").write_bytes(b"\xff\xfe\x00\x01")

    moved = list(bulk.import_tree(store, source))

    assert (bulk.FAILED, "binary") in actions(moved)
    # The failure bounds one file, not the run.
    assert store.exists("project")


def test_import_reports_a_name_that_is_not_a_key(store, tmp_path):
    source = a_tree(tmp_path / "in")
    (source / "?.md").write_text("would ask the store to allocate a number")

    moved = list(bulk.import_tree(store, source))

    assert (bulk.FAILED, None) in actions(moved)
    assert [entry.key for entry in bulk.levels(store, None)] == ["project"]


def test_import_treats_two_files_landing_on_one_key_as_a_conflict(store, tmp_path):
    source = tmp_path / "in"
    source.mkdir()
    (source / "a.md").write_text("markdown")
    (source / "a.json").write_text('{"format": "json"}')

    moved = list(bulk.import_tree(store, source))

    assert [transfer.action for transfer in moved] == [bulk.WROTE, bulk.SKIPPED]
    assert store.retrieve_document("a").format == "json"


def test_import_refuses_a_source_that_is_not_there(store, tmp_path):
    with pytest.raises(bulk.SourceMissingError):
        list(bulk.import_tree(store, tmp_path / "nowhere"))


def test_an_unknown_conflict_mode_is_refused(store, tmp_path):
    a_tree(tmp_path / "in")
    with pytest.raises(ValueError):
        list(bulk.import_tree(store, tmp_path / "in", on_conflict="clobber"))


# -- what the store had to add -------------------------------------------


def test_exists_asks_about_the_key_itself(store):
    store.store_document("a/b", "content")

    assert store.exists("a/b")
    # A container holds nothing itself, so a document may still be written to
    # it -- which is why an import asks about the key rather than the subtree.
    assert not store.exists("a")
    assert not store.exists("a/c")


# -- the root ------------------------------------------------------------


def test_the_root_document_has_no_path_yet(store):
    # Parked, not decided: the empty stem gives `.md`, which is hidden, which
    # an import skips by default -- so a round trip would drop the root
    # document rather than relocate it. Refused loudly until that is settled.
    with raises_rendered(bulk.UnmappableError, "no file name"):
        bulk.path_for_key("")


def test_root_metadata_maps_like_any_other_key():
    # Only the document at the root is stuck; its metadata has a segment and
    # so has a name, and the mapping round trips.
    assert bulk.path_for_key("!title") == PurePosixPath("!title.md")
    assert bulk.key_for_path("!title.md") == ("!title", "markdown")


def test_exporting_reports_the_root_document_rather_than_dropping_it(populated, tmp_path):
    populated.store_document("", "the root body", title="This store")
    transfers = list(bulk.export_tree(populated, None, tmp_path / "out"))

    failed = [t for t in transfers if t.action == bulk.FAILED]
    assert [t.key for t in failed] == [""]
    assert "no file name" in failed[0].reason
    # The title is exported even though the document it belongs to is not.
    assert (tmp_path / "out" / "!title.md").read_text() == "This store"


def test_an_omitted_key_exports_from_the_root(populated, tmp_path):
    named = actions(bulk.export_tree(populated, "", tmp_path / "a", dry_run=True))
    omitted = actions(bulk.export_tree(populated, None, tmp_path / "b", dry_run=True))
    assert named == omitted
