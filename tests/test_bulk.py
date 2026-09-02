"""Tests for bulk import and export.

Two halves. The mapping between a key and a path is a pure function and is
tested as one, in both directions and on the keys that do not have an obvious
path at all. The transfers are tested for what they refuse as much as for what
they move: a run that stops, skips or fails has to say so, since the exit
status and the report are the only parts of that a caller ever sees.
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

import pytest

from outrage import bulk, messages
from outrage import store as store_module
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


# -- which trees a copy may stream between -------------------------------


def test_a_graft_refuses_only_a_target_inside_the_source():
    """One direction is dangerous and the other is shipped.

    Grafted, everything lands beneath ``target`` *and* its own source key, so
    only a target inside the source is inside the walk. ``copy a/b a`` writes
    ``a/a/b/...``, which the walk of ``a/b`` never reaches, and refusing it
    would widen the rule past the danger - ``context/68/decisions`` 1.
    """
    with pytest.raises(bulk.OverlappingCopyError):
        bulk.overlapping("a/b", "a/b/inside")
    with pytest.raises(bulk.OverlappingCopyError):
        bulk.overlapping("a/b", "a/b")
    bulk.overlapping("a/b", "a")
    bulk.overlapping("a/b", "elsewhere")


def test_a_reroot_refuses_an_overlap_in_either_direction():
    """Stripping the source key puts the landing zone back inside the walk.

    ``a/b`` re-rooted onto ``a`` sends ``a/b/b/x`` to ``a/b/x``: inside the
    subtree still being read, and later in the order than the key that was
    being copied when it was written.
    """
    with pytest.raises(bulk.OverlappingCopyError) as refused:
        bulk.overlapping("a/b", "a", reroot=True)
    assert "still reading" in messages.render(refused.value)

    with pytest.raises(bulk.OverlappingCopyError):
        bulk.overlapping("a/b", "a/b/inside", reroot=True)
    bulk.overlapping("a/b", "elsewhere", reroot=True)


def test_a_key_is_matched_by_segment_rather_than_by_characters():
    """``a/b`` does not contain ``a/bb``, however alike the strings look."""
    bulk.overlapping("a/b", "a/bb", reroot=True)
    bulk.overlapping("a/bb", "a/b", reroot=True)


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
        # And the timestamp, which the round trip used to drop: an export
        # dates each file by the document it holds and an import dates each
        # document by the file it came from, so the corpus that comes back is
        # the corpus that left.
        assert after[key].updated_at == excerpt.updated_at


def test_an_export_dates_each_file_by_the_document_it_holds(store, tmp_path):
    """The mtime *is* a tree's ``updated_at``, so a copy into one sets it.

    Which is what makes the round trip above lossless, and what makes an
    exported tree sort by age the way the store does.
    """
    store.store_document("a/b", "body", updated_at="2020-01-02T03:04:05+00:00")
    target = tmp_path / "out"

    list(bulk.export_tree(store, None, target))

    written = datetime.fromtimestamp((target / "a/b.md").stat().st_mtime, UTC)
    assert written.isoformat(timespec="seconds") == "2020-01-02T03:04:05+00:00"


def test_an_import_dates_each_document_by_the_file_it_came_from(store, tmp_path):
    """A change of meaning, and a deliberate one.

    An import used to stamp everything with the moment it ran. It carries the
    file's own time now, for the same reason every other copy carries a
    timestamp: the alternative says the whole corpus was written at once, and
    that is the one fact about a document nothing can reconstruct afterwards.
    """
    source = a_tree(tmp_path / "in")
    os.utime(source / "project.md", (1577934245, 1577934245))  # 2020-01-02T03:04:05Z

    list(bulk.import_tree(store, source))

    assert store.retrieve_document("project").updated_at == "2020-01-02T03:04:05+00:00"


def test_export_leaves_a_file_that_is_already_there(populated, tmp_path):
    target = tmp_path / "out"
    (target / "project").mkdir(parents=True)
    (target / "project/!title.md").write_text("mine, not the store's")

    moved = list(bulk.export_tree(populated, "project", target))

    assert (store_module.SKIPPED, "project/!title") in actions(moved)
    assert (target / "project/!title.md").read_text() == "mine, not the store's"


def test_export_overwrites_when_asked(populated, tmp_path):
    target = tmp_path / "out"
    (target / "project").mkdir(parents=True)
    (target / "project/!title.md").write_text("mine, not the store's")

    moved = list(bulk.export_tree(populated, "project", target, on_conflict=store_module.OVERWRITE))

    assert (store_module.WROTE, "project/!title") in actions(moved)
    assert (target / "project/!title.md").read_text() == "The project"


def test_export_stops_at_the_first_conflict_and_says_where(populated, tmp_path):
    target = tmp_path / "out"
    (target / "project").mkdir(parents=True)
    (target / "project/!title.md").write_text("mine")

    moved = list(bulk.export_tree(populated, "project", target, on_conflict=store_module.STOP))

    assert moved[-1].action == store_module.STOPPED
    assert moved[-1].key == "project/!title"
    # Everything before the conflict stands, and nothing after it was tried:
    # what a stop can honestly promise, and all of it.
    assert (target / "project.md").exists()
    assert not (target / "project/reference/env.json").exists()


def test_export_dry_run_writes_nothing_and_reports_the_same(populated, tmp_path):
    target = tmp_path / "out"

    moved = list(bulk.export_tree(populated, None, target, dry_run=True))

    assert [transfer.action for transfer in moved] == [store_module.WROTE] * 5
    assert not target.exists()


def test_export_refuses_to_write_outside_the_directory(store, tmp_path):
    store.store_document("a/../escaped", "out of the tree")
    target = tmp_path / "out"

    moved = list(bulk.export_tree(store, None, target))

    assert [transfer.action for transfer in moved] == [store_module.FAILED]
    assert not (tmp_path / "escaped.md").exists()


def test_export_reports_a_file_it_cannot_write_and_carries_on(populated, tmp_path):
    target = tmp_path / "out"
    target.mkdir()
    # A plain file where a document's directory has to go: the store cannot
    # help with this and the caller has to be told which key it cost.
    (target / "project").write_text("in the way")

    moved = list(bulk.export_tree(populated, None, target))

    assert (store_module.FAILED, "project/!title") in actions(moved)
    assert (store_module.WROTE, "notes/src/myfile.py") in actions(moved)


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

    # Key order, because an import is a copy out of a store now and a store
    # walks its keys. It used to be the file walk's name order, which put
    # `project.md` after the directory `project/` that sorts beside it.
    assert [transfer.key for transfer in moved] == [
        "project",
        "project/!title",
        "project/reference/env",
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

    assert (store_module.SKIPPED, "project") in actions(moved)
    assert store.retrieve_document("project").content == "mine, not the file's"


def test_import_overwrites_when_asked(store, tmp_path):
    a_tree(tmp_path / "in")
    store.store_document("project", "mine, not the file's")

    moved = list(bulk.import_tree(store, tmp_path / "in", on_conflict=store_module.OVERWRITE))

    assert (store_module.WROTE, "project") in actions(moved)
    assert store.retrieve_document("project").content == "# Project"


def test_import_stops_at_the_first_conflict_keeping_what_it_wrote(store, tmp_path):
    a_tree(tmp_path / "in")
    store.store_document("project/reference/env", "mine")

    moved = list(bulk.import_tree(store, tmp_path / "in", on_conflict=store_module.STOP))

    assert moved[-1].action == store_module.STOPPED
    assert moved[-1].key == "project/reference/env"
    # The two keys before it in the walk are in, and stay in. A stop is not a
    # rollback, and the report is what makes the difference visible.
    assert store.exists("project")
    assert store.exists("project/!title")


def test_import_dry_run_stores_nothing(store, tmp_path):
    a_tree(tmp_path / "in")

    moved = list(bulk.import_tree(store, tmp_path / "in", dry_run=True))

    assert [transfer.action for transfer in moved] == [store_module.WROTE] * 3
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


@pytest.mark.parametrize(
    "make, key",
    [
        pytest.param(
            lambda source, outside: (source / "link").symlink_to(outside),
            "link/elsewhere",
            id="symlink",
        ),
        pytest.param(
            lambda source, outside: (source / "binary.md").write_bytes(b"\xff\xfe\x00\x01"),
            "binary",
            id="not-text",
        ),
        pytest.param(
            lambda source, outside: (source / "?.md").write_text("allocate me a number"),
            # No key to ask about: `?` is not one, which is the whole reason
            # the file cannot be a document.
            None,
            id="not-a-key",
        ),
    ],
)
def test_import_takes_what_the_tree_holds_as_a_document_and_nothing_else(
    store, tmp_path, make, key
):
    """What is not a document does not cross, and the run is unharmed.

    **And it is no longer reported**, which is what changed when an import
    became a copy out of a ``FilesystemStore``. The old walk went file by file
    and named each one it could not take; the store walks documents, and a
    symlink, a file that is not UTF-8 text and a name no key spells are not
    documents to it. ``FilesystemStore.check_file`` is what names the last two
    today, and nothing a person can run reaches it over a foreign tree - so
    this is a real loss in what an import tells you, pinned here rather than
    left to be discovered.
    """
    source = a_tree(tmp_path / "in")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "elsewhere.md").write_text("not in the tree")
    make(source, outside)

    moved = list(bulk.import_tree(store, source))

    if key is not None:
        assert not store.exists(key)
    assert other_keys(moved) == {"project", "project/!title", "project/reference/env"}
    # The failure bounds one file, not the run.
    assert store.retrieve_document("project").content == "# Project"


def test_import_takes_the_first_of_two_files_claiming_one_key(store, tmp_path):
    """One key, one document, and the tree decides which file holds it.

    The first in name order, which is the file every *read* of that tree
    returns too - so an import of it stores what reading it would have shown.
    The second used to be reported as a conflict; a store has no second
    document to report.
    """
    source = tmp_path / "in"
    source.mkdir()
    (source / "a.md").write_text("markdown")
    (source / "a.json").write_text('{"format": "json"}')

    moved = list(bulk.import_tree(store, source))

    assert [transfer.action for transfer in moved] == [store_module.WROTE]
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


def test_the_root_document_is_the_file_named_by_the_extension_alone(store):
    # Settled by taking the mapping's own answer: the root has no segments, so
    # its file is named by the empty stem. No key has an empty last segment, so
    # `.md` collides with nothing, and only the file at the *top* of the tree
    # is read back as the root.
    assert bulk.path_for_key("") == PurePosixPath(".md")
    assert bulk.path_for_key("", "json") == PurePosixPath(".json")
    assert bulk.key_for_path(".md") == ("", "markdown")
    assert bulk.key_for_path(".md", "a") == ("a", "markdown")
    # Further down it is a name like any other leading-dot name, because the
    # key it would otherwise mean does not exist.
    assert bulk.key_for_path("a/.md") == ("a/.md", None)


def test_root_metadata_maps_like_any_other_key():
    # Only the document at the root is stuck; its metadata has a segment and
    # so has a name, and the mapping round trips.
    assert bulk.path_for_key("!title") == PurePosixPath("!title.md")
    assert bulk.key_for_path("!title.md") == ("!title", "markdown")


def test_the_root_document_survives_the_round_trip(populated, tmp_path):
    populated.store_document("", "the root body", title="This store")
    transfers = list(bulk.export_tree(populated, None, tmp_path / "out"))

    assert [t.key for t in transfers if t.action == store_module.FAILED] == []
    assert (tmp_path / "out" / ".md").read_text() == "the root body"
    assert (tmp_path / "out" / "!title.md").read_text() == "This store"


def test_an_import_keeps_the_root_document_its_dotfile_skip_would_drop(populated, tmp_path):
    # The one exception the skip makes, and the reason it exists: the file is
    # hidden because the mapping names it by its extension alone, not because
    # somebody else's tree happened to hide it.
    populated.store_document("", "the root body")
    list(bulk.export_tree(populated, None, tmp_path / "out"))
    (tmp_path / "out" / ".ignored.md").write_text("not a document of ours")

    with SqliteStore(tmp_path / "second") as second:
        transfers = list(bulk.import_tree(second, tmp_path / "out"))
        assert second.retrieve_document("").content == "the root body"
    assert ".ignored" not in " ".join(str(t.key) for t in transfers)


def test_an_omitted_key_exports_from_the_root(populated, tmp_path):
    named = actions(bulk.export_tree(populated, "", tmp_path / "a", dry_run=True))
    omitted = actions(bulk.export_tree(populated, None, tmp_path / "b", dry_run=True))
    assert named == omitted


# -- one document, to a file and back ------------------------------------


def test_a_document_exports_to_a_file_named_by_an_id_and_its_format(populated, tmp_path):
    exported = bulk.export_document(populated, "project/reference/env", tmp_path / "export")

    assert exported.path.parent == tmp_path / "export"
    assert exported.path.name.startswith(bulk.FALLBACK_PREFIX)
    assert exported.path.suffix == ".json"
    assert exported.path.read_text() == '{"python": "3.14"}'


def test_exporting_a_key_twice_leaves_the_first_file_alone(populated, tmp_path):
    """The collision that happens is two agents, not two keys.

    The mapped name this replaces stopped two *keys* landing on one file and
    did nothing about two sessions editing one key, where the second export
    destroyed the first's unimported edit. ``plans/robust-editing``.
    """
    first = bulk.export_document(populated, "project", tmp_path / "export")
    populated.store_document("project", "# Project, edited")
    second = bulk.export_document(populated, "project", tmp_path / "export")

    assert second.path != first.path
    assert first.path.read_text() == "# Project"
    assert second.path.read_text() == "# Project, edited"


def test_a_document_longer_than_one_read_is_exported_whole(store, tmp_path):
    store.store_document("long", "x" * (store_module.DEFAULT_MAX_CHARS * 3))

    exported = bulk.export_document(store, "long", tmp_path / "export")

    assert exported.path.read_text() == "x" * (store_module.DEFAULT_MAX_CHARS * 3)
    assert exported.excerpt.total == store_module.DEFAULT_MAX_CHARS * 3


def test_a_key_with_no_path_of_its_own_is_exported_like_any_other(store, tmp_path):
    """What was the fallback is now the only naming, so this key is no longer a case."""
    store.store_document("a/./b", '{"traversal": true}', format="json")

    exported = bulk.export_document(store, "a/./b", tmp_path / "export")

    assert exported.path.parent == tmp_path / "export"
    assert exported.path.suffix == ".json"
    assert exported.record.key == "a/./b"


def test_two_keys_never_land_on_one_file(store, tmp_path):
    """Including the pair a case-insensitive filesystem used to collapse.

    ``export A``, ``export a``, ``import A`` silently stored ``a``'s content,
    which was accepted rather than fixed while the name came from the key.
    """
    store.store_document("A", "upper")
    store.store_document("a", "lower")

    one = bulk.export_document(store, "A", tmp_path / "export")
    two = bulk.export_document(store, "a", tmp_path / "export")

    assert one.path != two.path
    assert one.path.read_text() == "upper"
    assert two.path.read_text() == "lower"


def test_the_root_document_is_exported_like_any_other(store, tmp_path):
    store.store_document("", "# The store")

    exported = bulk.export_document(store, "", tmp_path / "export")

    assert exported.path.parent == tmp_path / "export"
    assert exported.path.read_text() == "# The store"
    assert exported.record.key == ""


def test_an_edited_file_imports_back_and_reports_both_sizes(populated, tmp_path):
    exported = bulk.export_document(populated, "project", tmp_path / "export")
    exported.path.write_text("# Project, edited by hand")

    imported = bulk.import_document(populated, "project", exported.path, tmp_path / "export")

    assert imported == bulk.Imported(key="project", stored=25, previous=9)
    assert populated.retrieve_document("project").content == "# Project, edited by hand"


def test_an_import_may_store_at_a_key_the_file_did_not_come_from(populated, tmp_path):
    exported = bulk.export_document(populated, "project", tmp_path / "export")

    imported = bulk.import_document(populated, "project/copy", exported.path, tmp_path / "export")

    assert imported.previous is None
    assert imported.unchecked == "exported from 'project'"
    assert populated.retrieve_document("project/copy").content == "# Project"


def test_an_import_takes_its_format_from_the_file_name(populated, tmp_path):
    exported = bulk.export_document(populated, "project/reference/env", tmp_path / "export")

    bulk.import_document(populated, "project/reference/env", exported.path, tmp_path / "export")

    assert populated.retrieve_document("project/reference/env").format == "json"


def test_an_empty_file_is_stored_rather_than_refused(populated, tmp_path):
    exported = bulk.export_document(populated, "project", tmp_path / "export")
    exported.path.write_text("")

    imported = bulk.import_document(populated, "project", exported.path, tmp_path / "export")

    assert (imported.stored, imported.previous) == (0, 9)
    assert populated.retrieve_document("project").content == ""


def test_an_import_of_a_key_that_held_nothing_says_so(populated, tmp_path):
    (tmp_path / "export").mkdir()
    (tmp_path / "export" / "new.md").write_text("fresh")

    imported = bulk.import_document(
        populated, "new", tmp_path / "export" / "new.md", tmp_path / "export"
    )

    assert imported.previous is None


def test_an_import_refuses_a_file_outside_the_export_directory(populated, tmp_path):
    outside = tmp_path / "elsewhere.md"
    outside.write_text("not exported")

    with pytest.raises(bulk.UnmappableError) as raised:
        bulk.import_document(populated, "project", outside, tmp_path / "export")

    assert raised.value.code == "import-file-escapes-tree"
    assert populated.retrieve_document("project").content == "# Project"


def test_an_import_refuses_a_path_that_climbs_out_of_the_export_directory(populated, tmp_path):
    (tmp_path / "export").mkdir()
    (tmp_path / "elsewhere.md").write_text("not exported")

    with pytest.raises(bulk.UnmappableError) as raised:
        bulk.import_document(
            populated, "project", PurePosixPath("../elsewhere.md"), tmp_path / "export"
        )

    assert raised.value.code == "import-file-escapes-tree"


def test_an_import_refuses_a_file_that_is_not_there(populated, tmp_path):
    (tmp_path / "export").mkdir()

    with pytest.raises(bulk.FileMissingError) as raised:
        bulk.import_document(
            populated, "project", tmp_path / "export" / "gone.md", tmp_path / "export"
        )

    assert raised.value.code == "import-file-missing"


def test_a_missing_file_named_relatively_says_what_it_was_relative_to(populated, tmp_path):
    """The doubled path a relative one produces has to read as what it is.

    ``.outrage/export/x.md`` typed where a person is standing is looked for
    inside the export directory, so the joined path repeats the segment and
    reads as a bug in the tool unless the sentence names the directory.
    ``context/66/state``.
    """
    (tmp_path / "export").mkdir()

    with pytest.raises(bulk.FileMissingError) as raised:
        bulk.import_document(
            populated, "project", PurePosixPath("export/gone.md"), tmp_path / "export"
        )

    rendered = messages.render(raised.value)
    assert "'export/gone.md' is relative to the export directory" in rendered
    assert str(tmp_path / "export") in rendered


def test_a_missing_file_named_absolutely_is_reported_without_the_clause(populated, tmp_path):
    """Nothing to explain: the path in the sentence is the path that was given."""
    (tmp_path / "export").mkdir()

    with pytest.raises(bulk.FileMissingError) as raised:
        bulk.import_document(
            populated, "project", tmp_path / "export" / "gone.md", tmp_path / "export"
        )

    assert "relative to" not in messages.render(raised.value)


def test_an_import_refuses_a_file_that_is_not_text(populated, tmp_path):
    from outrage.store_files import NotTextError

    (tmp_path / "export").mkdir()
    (tmp_path / "export" / "binary.md").write_bytes(b"\xff\xfe\x00")

    with pytest.raises(NotTextError):
        bulk.import_document(
            populated, "project", tmp_path / "export" / "binary.md", tmp_path / "export"
        )


# -- the export record, and the check it makes possible --------------------
#
# The half of `plans/robust-editing` that is not about naming: an export
# records what it handed out, and an import compares it with what is there now.
# The three questions a record can answer are in `plans/robust-editing/record`.


def test_an_export_records_what_it_handed_out(populated, tmp_path):
    exported = bulk.export_document(populated, "project", tmp_path / "export")

    written = bulk.ExportRecord.read(exported.path)
    assert written == exported.record
    assert written.key == "project"
    assert written.content_sha256 == bulk.content_hash("# Project")
    assert written.format == "markdown"
    assert written.updated_at == populated.retrieve_document("project").updated_at
    assert bulk.ExportRecord.path_for(exported.path).name.endswith(bulk.RECORD_SUFFIX)


def test_an_import_is_refused_when_the_document_changed_underneath_it(populated, tmp_path):
    """The reason for the whole thread: the second writer used to win silently."""
    exported = bulk.export_document(populated, "project", tmp_path / "export")
    exported.path.write_text("# Project, my edit")
    populated.store_document("project", "# Project, somebody else's")

    with pytest.raises(bulk.StaleImportError) as raised:
        bulk.import_document(populated, "project", exported.path, tmp_path / "export")

    assert raised.value.code == "import-stale"
    assert populated.retrieve_document("project").content == "# Project, somebody else's"


def test_a_refused_import_names_both_times_and_the_way_out(populated, tmp_path):
    exported = bulk.export_document(populated, "project", tmp_path / "export")
    populated.store_document("project", "# Project, somebody else's")

    with pytest.raises(bulk.StaleImportError) as raised:
        bulk.import_document(populated, "project", exported.path, tmp_path / "export")

    rendered = messages.render(raised.value)
    assert exported.record.exported_at in rendered
    assert populated.retrieve_document("project").updated_at in rendered
    assert "overwrite" in rendered


def test_overwrite_stores_the_stale_file_and_says_what_it_displaced(populated, tmp_path):
    exported = bulk.export_document(populated, "project", tmp_path / "export")
    exported.path.write_text("# Project, my edit")
    populated.store_document("project", "# Project, somebody else's")
    displaced = populated.retrieve_document("project").updated_at

    imported = bulk.import_document(
        populated, "project", exported.path, tmp_path / "export", overwrite=True
    )

    assert (imported.overwritten, imported.changed_at) == (True, displaced)
    assert populated.retrieve_document("project").content == "# Project, my edit"


def test_a_document_deleted_since_the_export_is_a_change_like_any_other(populated, tmp_path):
    """The edit was made against content that is no longer what is there."""
    exported = bulk.export_document(populated, "project", tmp_path / "export")
    populated.delete("project")

    with pytest.raises(bulk.StaleImportError) as raised:
        bulk.import_document(populated, "project", exported.path, tmp_path / "export")

    assert "deleted since" in messages.render(raised.value)


def test_a_cross_key_import_is_not_refused_by_the_target_having_changed(populated, tmp_path):
    """The record's hash is the *source* key's content.

    Comparing it against a different target would refuse every copy around the
    store as stale, so the question is asked only when the keys agree.
    ``plans/robust-editing/record``.
    """
    exported = bulk.export_document(populated, "project", tmp_path / "export")
    populated.store_document("project/copy", "something else entirely")

    imported = bulk.import_document(populated, "project/copy", exported.path, tmp_path / "export")

    assert imported.unchecked == "exported from 'project'"
    assert populated.retrieve_document("project/copy").content == "# Project"


def test_a_file_with_no_record_is_imported_and_reported_unchecked(populated, tmp_path):
    """A missing record degrades to not getting the check, not to being wrong."""
    exported = bulk.export_document(populated, "project", tmp_path / "export")
    bulk.ExportRecord.path_for(exported.path).unlink()
    exported.path.write_text("# Project, edited")

    imported = bulk.import_document(populated, "project", exported.path, tmp_path / "export")

    assert imported.unchecked == "no export record"
    assert populated.retrieve_document("project").content == "# Project, edited"


def test_an_unreadable_record_degrades_to_no_check_rather_than_a_refusal(populated, tmp_path):
    exported = bulk.export_document(populated, "project", tmp_path / "export")
    bulk.ExportRecord.path_for(exported.path).write_text("not json at all")

    imported = bulk.import_document(populated, "project", exported.path, tmp_path / "export")

    assert imported.unchecked == "no export record"


def test_a_record_carrying_a_later_versions_field_is_still_read(populated, tmp_path):
    """Unknown fields are ignored, so a newer writer does not cost this reader
    the check it can still make."""
    exported = bulk.export_document(populated, "project", tmp_path / "export")
    beside = bulk.ExportRecord.path_for(exported.path)
    held = json.loads(beside.read_text())
    held["recorded_by_something_later"] = "whatever it is"
    beside.write_text(json.dumps(held))
    exported.path.write_text("# Project, edited")

    imported = bulk.import_document(populated, "project", exported.path, tmp_path / "export")

    assert imported.unchecked is None


def test_an_unedited_file_says_the_edit_changed_nothing(populated, tmp_path):
    """The silent no-op: a replace whose anchor matched nothing round-trips
    perfectly cleanly, and the record notices it for free."""
    exported = bulk.export_document(populated, "project", tmp_path / "export")

    imported = bulk.import_document(populated, "project", exported.path, tmp_path / "export")

    assert imported.unedited is True


def test_an_edited_file_is_not_reported_as_unedited(populated, tmp_path):
    exported = bulk.export_document(populated, "project", tmp_path / "export")
    exported.path.write_text("# Project, edited")

    imported = bulk.import_document(populated, "project", exported.path, tmp_path / "export")

    assert imported.unedited is False


# -- the sweep, which is what a name of its own for every export costs ------


def _age(path, seconds):
    moment = time.time() - seconds
    os.utime(path, (moment, moment))


def test_the_sweep_removes_an_export_and_its_record_once_they_are_old(populated, tmp_path):
    exported = bulk.export_document(populated, "project", tmp_path / "export")
    beside = bulk.ExportRecord.path_for(exported.path)
    for path in (exported.path, beside):
        _age(path, bulk.EXPORT_MAX_AGE.total_seconds() + 60)

    removed = bulk.sweep_exports(tmp_path / "export")

    assert removed == 2
    assert not exported.path.exists()
    assert not beside.exists()


def test_the_sweep_keeps_a_record_whose_export_is_still_being_edited(populated, tmp_path):
    """They age together, by the newer of the two.

    A file edited days after it came out is still being worked on, and sweeping
    the record out from under it would cost exactly the check it is there for.
    """
    exported = bulk.export_document(populated, "project", tmp_path / "export")
    beside = bulk.ExportRecord.path_for(exported.path)
    _age(beside, bulk.EXPORT_MAX_AGE.total_seconds() + 60)

    assert bulk.sweep_exports(tmp_path / "export") == 0
    assert beside.exists()


def test_the_sweep_keeps_what_is_not_yet_old(populated, tmp_path):
    exported = bulk.export_document(populated, "project", tmp_path / "export")
    _age(exported.path, bulk.EXPORT_MAX_AGE.total_seconds() - 3600)

    assert bulk.sweep_exports(tmp_path / "export") == 0
    assert exported.path.exists()


def test_an_export_sweeps_what_is_old_on_its_way_past(populated, tmp_path):
    stale = bulk.export_document(populated, "project", tmp_path / "export")
    for path in (stale.path, bulk.ExportRecord.path_for(stale.path)):
        _age(path, bulk.EXPORT_MAX_AGE.total_seconds() + 60)

    fresh = bulk.export_document(populated, "project", tmp_path / "export")

    assert not stale.path.exists()
    assert fresh.path.exists()


def test_the_sweep_says_nothing_about_a_directory_that_is_not_there(tmp_path):
    assert bulk.sweep_exports(tmp_path / "never-made") == 0


# -- the export directory, which is now outside the project ----------------


def test_the_export_root_is_created_private_to_this_user(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))

    root = bulk.export_root()

    assert root.parent == tmp_path
    assert root.is_dir()
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    # Stable per user rather than per process: a restart mid-edit must not
    # strand the file, because the session that comes back wanted it.
    assert bulk.export_root() == root


def test_the_export_root_refuses_a_path_that_is_not_a_directory(tmp_path, monkeypatch):
    """``gettempdir()`` is shared, so a name another user got to first is
    refused rather than written into."""
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    (tmp_path / bulk._export_dir_name()).write_text("somebody else's file")

    with pytest.raises(bulk.ExportRootError) as raised:
        bulk.export_root()

    assert raised.value.code == "export-root-unusable"
    assert "not a directory" in messages.render(raised.value)


def test_the_export_root_refuses_a_symbolic_link(tmp_path, monkeypatch):
    """Seen as itself rather than followed, which is the substitution refused."""
    (tmp_path / "temp").mkdir()
    (tmp_path / "elsewhere").mkdir()
    (tmp_path / "temp" / bulk._export_dir_name()).symlink_to(tmp_path / "elsewhere")
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path / "temp"))

    with pytest.raises(bulk.ExportRootError) as raised:
        bulk.export_root()

    assert "symbolic link" in messages.render(raised.value)


def test_a_second_import_of_the_same_file_is_not_refused_by_the_first(populated, tmp_path):
    """A successful import renews the record, or the tool is one edit per export.

    Without it the next import is refused against a change this call made, and
    an agent that hits that on its own second import learns to pass
    ``overwrite`` -- which is the guard being thrown away. ``context/106/findings``.
    """
    exported = bulk.export_document(populated, "project", tmp_path / "export")
    exported.path.write_text("# Project, first edit")
    bulk.import_document(populated, "project", exported.path, tmp_path / "export")
    exported.path.write_text("# Project, second edit")

    imported = bulk.import_document(populated, "project", exported.path, tmp_path / "export")

    assert imported.unchecked is None
    assert imported.overwritten is False
    assert populated.retrieve_document("project").content == "# Project, second edit"


def test_a_renewed_record_still_catches_another_writer(populated, tmp_path):
    """The renewal must not become a way of never being refused again."""
    exported = bulk.export_document(populated, "project", tmp_path / "export")
    exported.path.write_text("# Project, my edit")
    bulk.import_document(populated, "project", exported.path, tmp_path / "export")
    populated.store_document("project", "# Project, somebody else's")
    exported.path.write_text("# Project, my second edit")

    with pytest.raises(bulk.StaleImportError):
        bulk.import_document(populated, "project", exported.path, tmp_path / "export")


def test_a_renewed_record_carries_what_was_stored(populated, tmp_path):
    exported = bulk.export_document(populated, "project", tmp_path / "export")
    exported.path.write_text("# Project, edited")

    bulk.import_document(populated, "project", exported.path, tmp_path / "export")

    renewed = bulk.ExportRecord.read(exported.path)
    assert renewed.content_sha256 == bulk.content_hash("# Project, edited")
    assert renewed.updated_at == populated.retrieve_document("project").updated_at
    assert renewed.key == "project"


def test_a_cross_key_import_leaves_the_record_naming_where_it_came_from(populated, tmp_path):
    """Renewing it would silently turn a copy into an edit claim on the target."""
    exported = bulk.export_document(populated, "project", tmp_path / "export")
    exported.path.write_text("# Project, copied")

    bulk.import_document(populated, "project/copy", exported.path, tmp_path / "export")

    assert bulk.ExportRecord.read(exported.path) == exported.record
