"""The filesystem backend: that it agrees with SQLite, and what is only its own.

``test_store.py`` says a second backend that can be written should pass it
unchanged but for the fixtures at the top, and this one does -- it is the third
parameter of that file's ``store`` fixture, which is the primary evidence for
what it is. So the contract is not restated here.

What is here is the second kind of evidence and the divergences. The comparison
below is the same shape as ``test_store_parquet.py``'s: one corpus, put into
both backends, the same battery of calls to each, every answer asserted equal.
It is stronger than re-running the contract against expectations, because a
live oracle cannot drift; and it is what says that a store and a tree are the
same namespace rather than two that look alike.

The divergences are the three the module docstring names, plus what only a
directory has: a file somebody else put there, two files claiming one key, and
the round trip through ``outrage export``.
"""

from __future__ import annotations

import itertools
import os
from datetime import datetime

import pytest

from conftest import answers_alike, page_facts, raises_rendered, walk_documents, walk_level
from outrage import bulk, keys, maintenance
from outrage import store as store_module
from outrage.store import (
    EVERYTHING,
    UNBOUNDED,
    BoundedSubtree,
    KeyNotFoundError,
    KeyRange,
    StoreFileError,
)
from outrage.store_files import DEFAULT_TREE_NAME, FilesystemStore, NotTextError
from outrage.store_sqlite import SqliteStore

#: The corpus ``test_store_parquet.py`` chose, for the same reasons and with
#: one addition: numeric segments that sort wrong as text, a sibling (``a-x``)
#: that sorts between a key and its own children under a naive ordering, a
#: document at the root, metadata on the root, JSON beside markdown, a document
#: with children, and -- the addition -- a key whose last segment already ends
#: in something that looks like an extension, which is the one shape a mapping
#: through file names can lose. ``crlf`` is a second addition, from
#: `plans/line-endings`: a document whose line endings the two backends have to
#: agree about, where one holds a string and the other holds a file.
CORPUS = [
    ("", "root document"),
    ("!title", "The store itself"),
    ("a", "a body"),
    ("a/!title", "A"),
    ("a/!summary", "sum of a"),
    ("a/!changelog", "what changed"),
    ("a/!changelog/!title", "Changelog"),
    ("a/!changelog/22", "note twenty-two"),
    ("a/!changelog/22/!title", "Note 22"),
    ("a/2", "a two"),
    ("a/10", "a ten"),
    ("a/10/!title", "A ten"),
    ("a/b", "a b body"),
    ("a/b/c", "deep"),
    ("a/b/c/!title", "Deep"),
    ("a-x", "adversarial sibling"),
    ("a-x/!title", "A-x"),
    ("b", '{"json": true}'),
    ("b/!title", "B"),
    ("context/1/design", "design one"),
    ("context/2/design", "design two"),
    ("context/10/design", "design ten"),
    ("context/10/design/!title", "Ten"),
    ("crlf", "# One\r\n\r\nbody\r\n"),
    ("notes/src/file.py", "note"),
    ("z", "last"),
]

_KEYS = [
    "",
    "a",
    "a/b",
    "a/10",
    "context",
    "context/10",
    "notes",
    "z",
    "a-x",
    "nope",
    "a/b/c",
    "a/!changelog",
    "a/!changelog/22",
    "crlf",
]

_RANGES = [
    UNBOUNDED,
    KeyRange(after="a"),
    KeyRange(after_inclusive="a"),
    KeyRange(after_subtree="a"),
    KeyRange(before="b"),
    KeyRange(before_inclusive="b"),
    KeyRange(final_subtree="a"),
    KeyRange(after="a", before="z"),
    KeyRange(after_subtree="a", before="z"),
    KeyRange(after_inclusive="context/2", final_subtree="context/10"),
    KeyRange(after="nope"),
]

_SUBTREES = [
    EVERYTHING,
    BoundedSubtree(key="a"),
    BoundedSubtree(key="a", depth=0),
    BoundedSubtree(key="a", depth=1),
    BoundedSubtree(key="context", depth=2),
    BoundedSubtree(key=None, depth=1),
    BoundedSubtree(key="nope"),
    BoundedSubtree(key="", depth=0),
    BoundedSubtree(key="a/!changelog"),
    BoundedSubtree(key="a/!changelog", depth=0),
]

_METAS = [None, "title", ["title"], ["title", "summary"], ["summary"]]


@pytest.fixture
def sqlite(tmp_path):
    """The corpus in the backend the other one is compared against."""
    with SqliteStore(tmp_path / "s") as store:
        for key, content in CORPUS:
            store.store_document(key, content)
        yield store


@pytest.fixture
def tree(tmp_path, sqlite):
    """The same corpus as a directory, with the timestamps made to match.

    A tree keeps no timestamp of its own -- ``updated_at`` is the file's
    modification time, which is an approximation and documented as one -- so
    the mtimes are set from what SQLite recorded. Otherwise every comparison of
    a listing entry would be a comparison of two clocks, and the one thing this
    file is not about is the clock.
    """
    with FilesystemStore(tmp_path / "tree") as store:
        for key, content in CORPUS:
            store.store_document(key, content)
        for key, _ in CORPUS:
            when = datetime.fromisoformat(sqlite.retrieve_document(key).updated_at).timestamp()
            os.utime(store._file_for(key), (when, when))
        yield store


@pytest.fixture
def files(tmp_path):
    """A small tree, for what needs no comparison."""
    with FilesystemStore(tmp_path / "tree") as store:
        store.store_document("a", "a body", title="A")
        store.store_document("a/b", "below")
        yield store


def test_a_tree_is_opened_either_at_a_path_or_as_a_name_in_a_directory(tmp_path):
    """The two callers a tree has, and why they cannot be one constructor.

    An export target is an absolute path somebody typed, and ``store_file``
    refuses those -- correctly, for the store file it is about. A *mount* is
    the opposite: a name relative to ``--dir``, like every other store, and it
    has to earn every refusal that rule makes or a tree would be the one
    backend able to sit outside the directory a table describes.
    """
    typed = tmp_path / "elsewhere" / "corpus"
    with FilesystemStore(typed) as store:
        assert store.root == typed

    with FilesystemStore.in_directory(tmp_path / ".outrage", filename="documents") as store:
        assert store.root == tmp_path / ".outrage" / "documents"
        # The directory around the tree is the one holding it, so a backup
        # lands beside the corpus rather than inside it.
        assert store.directory == tmp_path / ".outrage"

    # And with no name at all it is the tree beside the store files, rather
    # than whatever the *package* default backend calls its file.
    with FilesystemStore.in_directory(tmp_path / "bare") as store:
        assert store.root == tmp_path / "bare" / DEFAULT_TREE_NAME

    with raises_rendered(StoreFileError, "absolute path"):
        FilesystemStore.in_directory(tmp_path, filename="/srv/corpus")
    with raises_rendered(StoreFileError, "climbs out"):
        FilesystemStore.in_directory(tmp_path, filename="../corpus")


# -- the contract, as a comparison ---------------------------------------


def test_a_store_and_a_tree_answer_every_read_identically(sqlite, tree):
    """The contract, checked against a live oracle rather than expectations.

    The same battery ``test_store_parquet.py`` puts to the columnar backend,
    for the same reason and written as one test for the same one: what is being
    asserted is a single claim -- *these are the same namespace* -- and a run
    reporting thousands of passes would say it thousands of times and locate a
    failure no better than the assertion does.
    """
    for key in _KEYS:
        answers_alike(sqlite, tree, lambda s, k=key: s.exists(k))
        answers_alike(sqlite, tree, lambda s, k=key: s.descendant_count(k))
        answers_alike(sqlite, tree, lambda s, k=key: s.latest_change(k))
        answers_alike(sqlite, tree, lambda s, k=key: s.latest_change(k, whole_subtree=True))
        answers_alike(sqlite, tree, lambda s, k=key: s.retrieve_document(k))
        if key != keys.ROOT:
            answers_alike(sqlite, tree, lambda s, k=key: s.level_entry(k))
        for limit in (None, 1, 2, 100):
            answers_alike(sqlite, tree, lambda s, k=key, n=limit: s.list_keys(k, limit=n))
        answers_alike(sqlite, tree, lambda s, k=key: walk_level(s, k))

    for key, key_range in itertools.product(_KEYS, _RANGES):
        answers_alike(sqlite, tree, lambda s, k=key, r=key_range: s.latest_change(k, key_range=r))

    for subtree, key_range, meta in itertools.product(_SUBTREES, _RANGES, _METAS):
        answers_alike(
            sqlite,
            tree,
            lambda s, t=subtree, r=key_range, m=meta: page_facts(
                s.get_documents(t, key_range=r, meta_name=m)
            ),
        )
        answers_alike(
            sqlite, tree, lambda s, t=subtree, r=key_range, m=meta: walk_documents(s, t, r, m)
        )

    names = ["title", ["title", "x"]]
    for subtree, key_range, meta in itertools.product(_SUBTREES, _RANGES, names):
        answers_alike(
            sqlite,
            tree,
            lambda s, t=subtree, r=key_range, m=meta: page_facts(
                s.keys_missing_meta(t, key_range=r, meta_name=m)
            ),
        )
        for window in _RANGES:
            answers_alike(
                sqlite,
                tree,
                lambda s, t=subtree, r=key_range, m=meta, w=window: s.missing_meta_stats(
                    t, key_range=r, window=w, meta_name=m, sample=3
                ),
            )


def test_a_store_and_a_tree_agree_under_every_combination_of_caps(sqlite, tree):
    """The three bounds on a read multiply, and they page to the same end."""
    for limit, max_chars, total in itertools.product((1, 3), (2, 1000), (None, 5, 10_000)):
        answers_alike(
            sqlite,
            tree,
            lambda s, n=limit, c=max_chars, t=total: walk_documents(
                s, EVERYTHING, UNBOUNDED, None, limit=n, max_chars=c, max_total_chars=t
            ),
        )


def test_the_round_trip_through_an_export_is_the_same_store(sqlite, tmp_path):
    """Export, read the tree as a store, import it back, and compare all three.

    The end-to-end proof that one mapping is at work rather than three: the
    walkers that write the tree, the store that reads it, and the walker that
    reads it back. A key that any of them spelled differently would show up as
    a disagreement about the corpus.
    """
    out = tmp_path / "out"
    transfers = list(bulk.export_tree(sqlite, None, out))
    assert [t.key for t in transfers if t.action != store_module.WROTE] == []

    with FilesystemStore(out) as exported, SqliteStore(tmp_path / "back") as second:
        assert [(e.key, e.content) for e in exported.get_documents(limit=None).items] == [
            (e.key, e.content) for e in sqlite.get_documents(limit=None).items
        ]
        for transfer in bulk.import_tree(second, out):
            assert transfer.action == store_module.WROTE
        assert [(e.key, e.content, e.format) for e in second.get_documents(limit=None).items] == [
            (e.key, e.content, e.format) for e in sqlite.get_documents(limit=None).items
        ]


# -- what is only a tree's -----------------------------------------------


def test_the_root_document_is_the_file_named_by_its_extension(files):
    files.store_document("", "the whole store", title="Everything")

    assert (files.root / ".md").read_text() == "the whole store"
    assert files.retrieve_document("").content == "the whole store"
    # And it is not a child of itself: the level below the root holds the keys
    # in the tree, not the file naming the tree's own document.
    assert [entry.key for entry in files.list_keys().items] == ["!title", "a"]


def test_a_changed_format_leaves_exactly_one_file(files):
    files.store_document("a", "a body", "markdown")
    files.store_document("a", '{"a": 1}', "json")

    assert [path.name for path in sorted(files.root.iterdir()) if path.is_file()] == ["a.json"]
    assert files.retrieve_document("a").format == "json"


def test_a_segment_that_is_not_a_path_component_is_refused(files):
    # A documented divergence: `.` and `..` are legal keys and impossible
    # paths, so this backend cannot hold them and says so rather than writing
    # somewhere else.
    with raises_rendered(bulk.UnmappableError, "not a path component"):
        files.store_document("a/../escape", "nope")
    with raises_rendered(bulk.UnmappableError, "not a path component"):
        files.store_document(".", "nope")


def test_a_key_that_would_land_outside_the_tree_is_refused(files, tmp_path):
    # The traversal that is actually reachable is in the *target tree* rather
    # than in the namespace: a symlinked directory anywhere along the path is
    # enough, and no unusual key is needed. See `planned/export-traversal`.
    outside = tmp_path / "outside"
    outside.mkdir()
    (files.root / "linked").symlink_to(outside)

    with raises_rendered(bulk.UnmappableError, "outside the directory"):
        files.store_document("linked/escaped", "nope")
    assert list(outside.iterdir()) == []


def test_a_segment_that_is_a_path_on_windows_stays_one_component_here(files):
    """The other half of ``planned/export-traversal``, pinned where it can be.

    A segment may hold a backslash and a colon -- the grammar was widened to
    mirror a filesystem, and `:` was made legal deliberately. On POSIX both are
    ordinary characters and one component, which is what this asserts. On
    Windows the same string re-parses into components off a Windows path, and a
    colon becomes a drive letter that drops the target from the path entirely;
    what catches those is :func:`outrage.bulk.contained_path`, which resolves
    the joined path rather than inspecting the segments, and so needs no
    per-platform list of what a component may look like.

    Not asserted on Windows, because there is no Windows here -- the same gap
    ``planned/hook-install/windows`` records.
    """
    stored = files.store_document("a\\..\\..\\evil", "still inside")

    assert files.retrieve_document(stored).content == "still inside"
    assert (files.root / "a\\..\\..\\evil.md").is_file()


def test_a_symlink_in_the_tree_is_not_a_document(files, tmp_path):
    # Not followed, in either sense, for the reason an import does not follow
    # one: a link out of the tree reads what the caller did not name, and a
    # link back into it reads the same document twice under two keys.
    (tmp_path / "elsewhere.md").write_text("not ours")
    (files.root / "linked.md").symlink_to(tmp_path / "elsewhere.md")

    assert "linked" not in [entry.key for entry in files.list_keys().items]
    assert not files.exists("linked")


def test_a_file_that_is_not_text_is_reported_rather_than_mangled(files):
    (files.root / "binary.md").write_bytes(b"\xff\xfe\x00 not text")

    # The walk passes over it, so it is in no listing and no page ...
    assert "binary" not in [entry.key for entry in files.list_keys().items]
    # ... and reading it by name says what is wrong rather than returning
    # something that has quietly lost bytes.
    with raises_rendered(NotTextError, "does not hold UTF-8 text"):
        files.retrieve_document("binary")

    report = maintenance.check(files)
    assert any(problem.code == maintenance.FILES_NOT_TEXT for problem in report.problems)


def test_a_byte_read_that_is_not_text_is_reported_the_same_way(files):
    (files.root / "binary.md").write_bytes(b"\xff\xfe\x00 not text")

    # The seeking path decodes its own window rather than going through
    # `_text`, so it has to give the same refusal rather than a UnicodeError
    # escaping from inside a read.
    with raises_rendered(NotTextError, "does not hold UTF-8 text"):
        files.retrieve_document("binary", byte_offset=0)


def test_a_byte_offset_addresses_the_file_as_it_is_on_disk(files):
    (files.root / "crlf.md").write_bytes(b"# One\r\n\r\nbody\r\n")

    byte_read = files.retrieve_document("crlf", byte_offset=7)

    # What a byte offset means outside the store: the file. Seven bytes in is
    # past `# One\r\n`, which is where anything byte-addressed -- an editor's
    # goto-byte, `dd`, a range handed to a fast edit tool -- would also land.
    assert byte_read.content == "\r\nbody\r\n"
    assert byte_read.total_bytes == 15

    # And the character path agrees, which is what `plans/line-endings` fixed:
    # this asserted the divergence until rule (a) settled which way round it
    # went. A directory of files returns what is on disk, so both numbers on a
    # `!contents` line over this document name the same place.
    assert files.retrieve_document("crlf").content == "# One\r\n\r\nbody\r\n"
    assert files.retrieve_document("crlf").total_bytes == 15


def test_a_directory_of_files_returns_the_bytes_that_are_on_disk(files):
    """Rule (a) of `plans/line-endings`, asked of the backend it changed.

    Reading with universal newlines gave a store that returned text its own
    file did not hold and counted a length the file did not have -- `issues/3`,
    and the worse half of it, because the file on disk was right and the
    document reported was not. So the two things asserted are the two that were
    wrong: the content encodes back to the file byte for byte, and the size in
    a listing is the length of the content a read returns.
    """
    written = "# One\r\n\r\nbody \u00e9\r\n".encode()
    (files.root / "crlf.md").write_bytes(written)

    read = files.retrieve_document("crlf")

    assert read.content.encode() == written
    assert read.total_bytes == len(written)
    entry = next(item for item in files.list_keys().items if item.key == "crlf")
    assert entry.size == len(read.content)


def test_two_files_claiming_one_key_read_once_and_are_reported(files):
    files.store_document("one", "markdown body", "markdown")
    (files.root / "one.json").write_text('{"json": true}')

    assert files.retrieve_document("one").content == '{"json": true}'
    assert [entry.key for entry in files.list_keys().items].count("one") == 1

    report = maintenance.check(files)
    assert any(problem.code == maintenance.KEYS_DOUBLED for problem in report.problems)


def test_a_foreign_tree_can_be_opened_with_its_dotfiles_left_alone(tmp_path):
    (tmp_path / "foreign").mkdir()
    (tmp_path / "foreign" / "README.md").write_text("a project")
    (tmp_path / "foreign" / ".hidden.md").write_text("not a document of theirs")
    (tmp_path / "foreign" / ".md").write_text("nor is this")

    with FilesystemStore(tmp_path / "foreign", hidden=False) as store:
        assert [entry.key for entry in store.list_keys().items] == ["README"]
        # The root document is **not** subject to the skip, whichever tree this
        # is. It is hidden because the mapping names it by its extension alone,
        # and a store that could not read its own root would be one this
        # package's own export cannot round trip.
        assert store.retrieve_document("").content == "nor is this"

    # And with the default, which is what a store of this package's own writing
    # wants: everything the tree holds.
    with FilesystemStore(tmp_path / "foreign") as store:
        assert ".hidden" in [entry.key for entry in store.list_keys().items]


def test_an_empty_directory_is_not_a_key(files):
    (files.root / "hollow" / "deeper").mkdir(parents=True)

    assert [entry.key for entry in files.list_keys().items] == ["a"]
    assert files.level_entry("hollow") is None
    with pytest.raises(KeyNotFoundError):
        files.retrieve_document("hollow")


def test_a_delete_takes_the_directories_it_emptied(files):
    files.store_document("deep/down/here", "x")

    assert files.delete("deep", recursive=True) == ["deep/down/here"]
    assert not (files.root / "deep").exists()
    # And stops at the tree itself, which is the store rather than a key.
    assert files.root.is_dir()


def test_a_backup_is_a_copy_that_was_read_back(files, tmp_path):
    copy = files.backup(tmp_path / "copy")

    assert copy.path == tmp_path / "copy"
    assert copy.integrity == "ok"
    assert copy.documents == 3
    with FilesystemStore(copy.path) as restored:
        assert restored.retrieve_document("a/b").content == "below"


def test_a_backup_carries_the_metadata_and_the_timestamps(files, tmp_path):
    """A copy that restamped the corpus would open cleanly and be a lie.

    The three documents include a title, which is what a store is surveyed by:
    a backup that dropped every ``!title`` is one nothing could be read back
    from usefully, and it would still count three rows.
    """
    dated = "2019-03-04T05:06:07+00:00"
    files.store_document("a/b", "below", updated_at=dated)
    copy = files.backup(tmp_path / "copy")

    with FilesystemStore(copy.path) as restored:
        assert restored.retrieve_document("a/!title").content == "A"
        assert restored.retrieve_document("a/b").updated_at == dated


def test_a_backup_of_a_tree_carries_its_documents_and_not_its_directory(files, tmp_path):
    """The one thing a tree gave up when it stopped copying itself with ``cp``.

    ``FilesystemStore.backup`` was ``shutil.copytree`` until 2026-08-27, and a
    backup was byte-faithful to the directory. It is the base's copy now -- the
    same one every other store gets -- so what crosses is what this store holds
    as a *document*, and a symbolic link is not one: ``exists`` says the key
    holds nothing and every read passes it over.

    Four things a tree can hold are not documents -- a link, a file that is not
    text, a name no key spells, and the second of two files claiming one key.
    :meth:`~outrage.store_files.FilesystemStore.check_file` names three of
    them, and a link is the one it does not, so this is the least visible of
    the four and the one worth pinning.
    """
    (files.root / "elsewhere.md").symlink_to(tmp_path / "nowhere.md")

    copy = files.backup(tmp_path / "copy")

    assert copy.documents == 3
    assert not (copy.path / "elsewhere.md").exists()
    # And the store agrees it never held it, which is why the copy is complete
    # rather than short: the link is not a key that went missing.
    assert not files.exists("elsewhere")
    assert maintenance.check(files).sound


def test_a_backup_that_came_up_short_is_refused_rather_than_returned(files, tmp_path, monkeypatch):
    """Comparing keys is the check here, so it has to be able to fail.

    Every key rather than a count of them, because a copy that lost one
    document and gained another counts the same and is not a backup.
    """
    original = FilesystemStore.audit_rows
    calls = itertools.count()

    def short(self):
        rows = list(original(self))
        # The *copy* is read second, and it is the one made to come up short.
        return iter(rows if next(calls) == 0 else rows[:-1])

    monkeypatch.setattr(FilesystemStore, "audit_rows", short)
    with raises_rendered(store_module.BackupError, "1 keys missing"):
        files.backup(tmp_path / "copy")


def test_a_backup_reads_its_copy_the_way_the_store_reads_itself(files, tmp_path):
    """``opened_at`` carries ``hidden``, and the root document is a dotfile.

    A copy opened under the default policy would read every key but the root's
    own, and come up one short against a store that holds one -- a failure with
    nothing wrong behind it. So the store that verifies is opened the way this
    one was.
    """
    files.store_document("", "the tree itself")

    copy = files.backup(tmp_path / "copy")

    assert copy.documents == 4
    with FilesystemStore(copy.path) as restored:
        assert restored.retrieve_document("").content == "the tree itself"


def test_a_check_reports_what_a_hand_edited_tree_can_hold(files):
    (files.root / "not a key" / "x.md").parent.mkdir()
    (files.root / "not a key" / "x.md").write_text("inside a name with spaces")

    report = maintenance.check(files)
    assert report.details["files"] != "0"
    # A name with a space *is* a key, so this one is fine: the grammar was
    # widened to mirror a filesystem, and this is the half that means.
    assert report.sound
    assert files.retrieve_document("not a key/x").content == "inside a name with spaces"


def test_a_repair_does_nothing_and_says_so(files):
    assert files.repair() == []
    # Not the same sentence as "nothing to check": what a check finds here is
    # somebody's file, and a store that renamed or removed one would be losing
    # what it was asked to keep.
    assert files.stored_format_version == files.format_version


# -- a tree whose file names are the keys ---------------------------------
#
# The second mapping, `extensions="keep"`. What it is for is a documentation
# bundle this package did not write, whose documents link to each other by file
# name: under `strip` every one of those links names a key the store does not
# hold. So the tests below are mostly about the *names*, and the two that are
# not are about what the extension had been buying.


@pytest.fixture
def bundle(tmp_path):
    """A documentation bundle as somebody else would have written it."""
    root = tmp_path / "bundle"
    (root / "guide").mkdir(parents=True)
    (root / "index.md").write_text("see [the guide](guide/intro.md)\n")
    (root / "guide" / "intro.md").write_text("# Intro\n")
    (root / "guide" / "data.json").write_text('{"a": 1}\n')
    (root / "Makefile").write_text("all:\n")
    return root


def test_a_bundle_read_with_extensions_kept_holds_the_keys_its_links_name(bundle):
    """The point of the mode, asserted as the link in the corpus.

    The document says `guide/intro.md`, so that has to be a key. Read the same
    tree the other way and it is not -- which is the defect the mode exists to
    answer rather than a preference about naming.
    """
    with FilesystemStore(bundle, extensions="keep") as kept:
        linked = kept.retrieve_document("index.md").content.split("(")[1].rstrip(")\n")
        assert linked == "guide/intro.md"
        assert kept.retrieve_document(linked).content == "# Intro\n"
        listed, _ = walk_level(kept, None)
        assert [key for key, *_ in listed] == ["Makefile", "guide", "index.md"]

    with FilesystemStore(bundle) as stripped:
        with pytest.raises(KeyNotFoundError):
            stripped.retrieve_document("guide/intro.md")
        assert stripped.retrieve_document("guide/intro").content == "# Intro\n"


def test_a_kept_name_still_declares_its_format(bundle):
    # The key changes and what the file says it holds does not.
    with FilesystemStore(bundle, extensions="keep") as kept:
        assert kept.retrieve_document("guide/data.json").format == "json"
        assert kept.retrieve_document("index.md").format == "markdown"
        # A name declaring nothing is detected on the way out, exactly as it
        # is under `strip`: the mapping decides the key, not the reading.
        assert kept.retrieve_document("Makefile").format == "markdown"


def test_a_write_to_a_kept_tree_reads_back_at_the_key_it_was_given(tmp_path):
    with FilesystemStore(tmp_path / "kept", extensions="keep") as kept:
        kept.store_document("notes.md", "# Notes\n")
        kept.store_document("plain", "no extension here")

        assert (kept.root / "notes.md").read_text() == "# Notes\n"
        # Nothing appended: the key is the path, so a key spelling no
        # extension is written to a file with none.
        assert (kept.root / "plain").is_file()
        assert not (kept.root / "plain.md").exists()
        assert kept.retrieve_document("notes.md").content == "# Notes\n"
        assert kept.retrieve_document("plain").content == "no extension here"


def test_a_format_a_kept_key_contradicts_is_refused_at_the_write(tmp_path):
    """The file would say markdown and hold JSON, and would read back markdown.

    Refused rather than written, because the name is part of the key here and
    is what every reader of the tree -- this store included -- will believe.
    """
    with FilesystemStore(tmp_path / "kept", extensions="keep") as kept:
        with raises_rendered(bulk.UnmappableError, "Spell the key with the extension"):
            kept.store_document("guide.md", '{"a": 1}', "json")
        assert not (kept.root / "guide.md").exists()
        # Said differently, or spelled differently, and it lands.
        kept.store_document("guide.json", '{"a": 1}', "json")
        kept.store_document("guide.md", '{"a": 1}', "markdown")
        assert kept.retrieve_document("guide.json").format == "json"


def test_a_document_that_keeps_its_name_still_carries_the_keys_below_it(tmp_path):
    """The container convention, which is what makes `keep` writable.

    A name in a directory is a file or a directory and not both, so a document
    keeping its whole name had nowhere to put so much as a title. `.!name` is
    where they go, and the file keeps the name a link in the bundle points at.
    """
    with FilesystemStore(tmp_path / "kept", extensions="keep") as kept:
        kept.store_document("guide.md", "# Guide\n", title="Guide")
        kept.store_document("guide.md/chapter", "the first")
        kept.store_document("guide.md/!changelog", "what changed")
        kept.store_document("guide.md/!changelog/22", "note twenty-two")

        # The document is untouched -- which is the whole point, since that is
        # the name the bundle's own links spell.
        assert (kept.root / "guide.md").read_text() == "# Guide\n"
        assert (kept.root / ".!guide.md" / "!title.md").read_text() == "Guide"
        assert (kept.root / ".!guide.md" / "chapter").read_text() == "the first"
        # Inside the container it is the ordinary mapping again, so metadata
        # carries its extension and needs no container of its own: the file
        # `!changelog.md` and the directory `!changelog/` are two names.
        assert (kept.root / ".!guide.md" / "!changelog.md").exists()
        assert (kept.root / ".!guide.md" / "!changelog" / "22").exists()

        assert kept.retrieve_document("guide.md/!title").content == "Guide"
        assert kept.retrieve_document("guide.md/!changelog/22").content == "note twenty-two"
        assert [key for key, *_ in walk_level(kept, "guide.md")[0]] == [
            "guide.md/!changelog",
            "guide.md/!title",
            "guide.md/chapter",
        ]


def test_a_bundles_own_directories_are_left_plain(tmp_path):
    """Only a segment that could name a file takes the prefix.

    A container that is a plain name stays a plain directory, which is what
    keeps a bundle browsable and an export of one a bundle.
    """
    with FilesystemStore(tmp_path / "kept", extensions="keep") as kept:
        kept.store_document("guide/intro.md", "# Intro\n")

        assert (kept.root / "guide" / "intro.md").exists()
        assert not (kept.root / ".!guide").exists()
        assert kept.retrieve_document("guide/intro.md").content == "# Intro\n"


def test_a_file_wearing_the_container_prefix_is_the_displaced_document(tmp_path):
    """Entry type makes the collision spelling symmetric.

    A prefixed directory is the container beside a plain document; a prefixed
    file is the document beside a plain directory. Both spell the same key.
    """
    root = tmp_path / "kept"
    root.mkdir()
    (root / ".!notes").write_text("a document")
    (root / "notes").mkdir()
    (root / "notes" / "x").write_text("below")
    (root / "ordinary.md").write_text("a document")

    with FilesystemStore(root, extensions="keep") as kept:
        assert [key for key, *_ in walk_level(kept, None)[0]] == ["notes", "ordinary.md"]
        assert kept.retrieve_document("notes").content == "a document"
        assert kept.retrieve_document("notes/x").content == "below"
        report = maintenance.check(kept)
        assert report.sound

    assert bulk.key_for_path(".!notes", extensions="keep") == ("notes", None)


def test_a_document_with_no_extension_gets_a_container_too(tmp_path):
    """`notes` and `notes/` are one name, so the tree is what says which.

    Nothing in the segment distinguishes a document from a bundle's own
    directory, so the container cannot be chosen by the name: a file being
    there is what says one is needed. Which means a key with no extension is
    as writable as any other.
    """
    with FilesystemStore(tmp_path / "kept", extensions="keep") as kept:
        kept.store_document("notes", "a body", title="Notes")
        kept.store_document("notes/x", "below")

        assert (kept.root / "notes").read_text() == "a body"
        assert (kept.root / ".!notes" / "!title.md").read_text() == "Notes"
        assert (kept.root / ".!notes" / "x").read_text() == "below"
        assert kept.retrieve_document("notes/!title").content == "Notes"
        assert kept.retrieve_document("notes/x").content == "below"

        # And a plain directory nobody wrote a document at stays plain, which
        # is the other half of the same question.
        kept.store_document("chapter/one", "first")
        assert (kept.root / "chapter" / "one").exists()
        assert not (kept.root / ".!chapter").exists()


def test_a_kept_tree_serves_a_document_written_after_its_child(tmp_path):
    """The prefixed file is the reverse-order exception to the plain directory."""
    with FilesystemStore(tmp_path / "kept", extensions="keep") as kept:
        kept.store_document("chapter/one", "first")
        kept.store_document("chapter", "a body", title="Chapter")

        assert (kept.root / ".!chapter").read_text() == "a body"
        assert (kept.root / "chapter" / "one").read_text() == "first"
        assert (kept.root / "chapter" / "!title.md").read_text() == "Chapter"
        assert kept.retrieve_document("chapter").content == "a body"
        assert kept.retrieve_document("chapter/one").content == "first"
        assert kept.retrieve_document("chapter/!title").content == "Chapter"
        assert [key for key, *_ in walk_level(kept, None)[0]] == ["chapter"]
        assert [key for key, *_ in walk_level(kept, "chapter")[0]] == [
            "chapter/!title",
            "chapter/one",
        ]

    # `strip` is unchanged: the extension already keeps the document and its
    # directory apart, so no collision spelling is needed.
    with FilesystemStore(tmp_path / "stripped") as stripped:
        stripped.store_document("chapter/one", "first")
        stripped.store_document("chapter", "a body")
        assert (stripped.root / "chapter.md").read_text() == "a body"
        assert (stripped.root / "chapter" / "one.md").read_text() == "first"
        assert stripped.retrieve_document("chapter").content == "a body"


def test_a_kept_tree_cannot_double_a_key(tmp_path):
    """`a.md` beside `a.json` is two keys here, where stripping made it one.

    The doubling `check_file` reports is a corpus saying two things about one
    key. A kept tree cannot produce one: a key is a file name whole, so two
    names are two keys, and the check has nothing to find.
    """
    root = tmp_path / "kept"
    root.mkdir()
    (root / "a.md").write_text("markdown")
    (root / "a.json").write_text('{"a": 1}')

    with FilesystemStore(root, extensions="keep") as kept:
        assert kept.retrieve_document("a.md").content == "markdown"
        assert kept.retrieve_document("a.json").content == '{"a": 1}'
        assert maintenance.check(kept).sound

    with FilesystemStore(root) as stripped:
        report = maintenance.check(stripped)
        assert not report.sound


def test_a_backup_of_a_kept_tree_is_read_the_way_it_was_written(bundle, tmp_path):
    """``opened_at`` carries the mapping, for the reason it carries ``hidden``.

    A copy opened under the other mode holds not one key of the store it came
    from, so a verified backup would come up short with nothing wrong behind
    it -- the same failure with nothing behind it, one step further along.
    """
    with FilesystemStore(bundle, extensions="keep") as kept:
        copy = kept.backup(tmp_path / "copy")

    assert copy.documents == 4
    with FilesystemStore(copy.path, extensions="keep") as restored:
        assert restored.retrieve_document("guide/intro.md").content == "# Intro\n"


def test_a_mount_names_the_mapping_and_a_bad_one_is_refused(tmp_path):
    """``in_directory`` is the mount's way in, and it takes the option too."""
    (tmp_path / "bundle").mkdir()
    (tmp_path / "bundle" / "page.md").write_text("a page")

    with FilesystemStore.in_directory(tmp_path, filename="bundle", extensions="keep") as kept:
        assert kept.retrieve_document("page.md").content == "a page"

    with raises_rendered(store_module.BackendError, "no 'kept' way of naming"):
        FilesystemStore.in_directory(tmp_path, filename="bundle", extensions="kept")


def test_a_backend_kept_in_one_file_refuses_the_option_rather_than_ignoring_it(tmp_path):
    """The rule the option grammar already follows, one layer down.

    A caller who wrote `extensions=keep` on a database meant something by it,
    and an option that silently did nothing is the failure a mount
    configuration is least able to notice.
    """
    with raises_rendered(store_module.BackendError, "holds its documents as rows") as raised:
        store_module.default_store(tmp_path, filename="s.sqlite", extensions="keep")
    assert raised.value.code == "backend-takes-no-extensions"


#: A bundle-shaped corpus: every document carries an extension, which is what a
#: tree somebody else wrote looks like, and every shape the container convention
#: has to hold -- a document with metadata, with an ordinary child, with
#: metadata that itself has children, and a plain directory beside a document of
#: the same stem (`guide/` beside `guide.md`), which under `keep` are two keys.
#:
#: `guide` holds no document of its own, and cannot: a file named `guide` and
#: the directory `guide/` are one name, so a bundle never has both and neither
#: can a tree. That is the one shape the container convention does not reach,
#: and `test_an_extensionless_key_is_the_one_shape_keep_still_cannot_hold` is
#: where it is asserted rather than quietly avoided here.
_KEPT_CORPUS = [
    ("", "root document"),
    ("!title", "The bundle"),
    ("guide.md", "# Guide"),
    ("guide.md/!title", "The guide"),
    ("guide.md/!summary", "what it covers"),
    ("guide.md/chapter", "an ordinary child"),
    ("guide.md/!changelog", "what changed"),
    ("guide.md/!changelog/22", "note twenty-two"),
    ("guide/intro.md", "# Intro"),
    ("guide/data.json", '{"a": 1}'),
    ("index.md", "see [the guide](guide/intro.md)"),
    ("Makefile", "all:\n"),
]

_KEPT_KEYS = ["", *(key for key, _ in _KEPT_CORPUS), "guide.md/nope", "nope.md"]

_KEPT_SUBTREES = [
    EVERYTHING,
    BoundedSubtree(key="guide.md"),
    BoundedSubtree(key="guide.md", depth=0),
    BoundedSubtree(key="guide.md", depth=1),
    BoundedSubtree(key="guide.md/!changelog"),
    BoundedSubtree(key="guide"),
    BoundedSubtree(key=None, depth=1),
]


@pytest.fixture
def kept_pair(tmp_path):
    """One bundle-shaped corpus in SQLite and in a tree that keeps extensions."""
    with (
        SqliteStore(tmp_path / "s") as sqlite,
        FilesystemStore(tmp_path / "kept", extensions="keep") as kept,
    ):
        for key, content in _KEPT_CORPUS:
            sqlite.store_document(key, content)
            kept.store_document(key, content)
        for key, _ in _KEPT_CORPUS:
            when = datetime.fromisoformat(sqlite.retrieve_document(key).updated_at).timestamp()
            os.utime(kept._file_for(key), (when, when))
        yield sqlite, kept


def _listed(page):
    """A level as its keys, kinds and sizes: everything but the format.

    Which is left out because it is the one thing the two really do disagree
    about, and it has a test of its own below. A listing does not open a file --
    an unmeasured walk cannot -- so a tree answers `format` from the *name*, and
    under `keep` a *document* whose name declares none answers None where a
    database answers what it detected when it was stored. Metadata is not
    affected: it carries its extension there, as it does under `strip`.
    """
    return [(entry.key, entry.kind, entry.size) for entry in page.items]


def test_a_kept_tree_is_the_same_namespace_as_a_store(kept_pair):
    """The contract under the second mapping, against a live oracle.

    The same claim `test_a_store_and_a_tree_answer_every_read_identically`
    makes for `strip`, and it is the one that says the container convention is
    a *spelling* rather than a different namespace: a caller reading through a
    kept tree cannot tell it from a database holding the same keys.
    """
    sqlite, kept = kept_pair
    for key in _KEPT_KEYS:
        answers_alike(sqlite, kept, lambda s, k=key: s.exists(k))
        answers_alike(sqlite, kept, lambda s, k=key: s.descendant_count(k))
        answers_alike(sqlite, kept, lambda s, k=key: s.retrieve_document(k))
        for limit in (None, 1, 2, 100):
            answers_alike(sqlite, kept, lambda s, k=key, n=limit: _listed(s.list_keys(k, limit=n)))

    for subtree, meta in itertools.product(_KEPT_SUBTREES, _METAS):
        answers_alike(
            sqlite,
            kept,
            lambda s, t=subtree, m=meta: page_facts(s.get_documents(t, meta_name=m)),
        )
        answers_alike(sqlite, kept, lambda s, t=subtree, m=meta: walk_documents(s, t, UNBOUNDED, m))


def test_a_kept_listing_reports_the_format_the_name_declares(kept_pair):
    """The one place the two disagree, asserted rather than left out.

    A listing does not open the file it lists, so a tree can only report the
    format its *name* declares -- and under `keep` a key with no extension is a
    file with none. Reading it detects markdown, as it does for any file whose
    name says nothing, so this is a disagreement between a listing and a read
    rather than a document stored wrong.

    Not new, and not the container convention's doing: a strip tree holding a
    foreign `myfile.py` answers the same way. `keep` reaches it wherever a
    bundle holds a document with no extension -- a `Makefile`, a `LICENSE`.
    Metadata was the case that made it ordinary, and metadata carrying its
    extension is what took that away.
    """
    sqlite, kept = kept_pair

    assert sqlite.level_entry("Makefile").format == "markdown"
    assert kept.level_entry("Makefile").format is None
    assert kept.level_entry("guide.md").format == "markdown"

    # Metadata is the case this *used* to cover and no longer does: it carries
    # its format's extension now, so a listing knows what it holds without
    # opening it, and the two agree.
    answers_alike(sqlite, kept, lambda s: s.level_entry("guide.md/!title"))
    assert kept.level_entry("guide.md/!title").format == "markdown"

    # And a read agrees with the database either way, because it has the
    # content in front of it.
    assert kept.retrieve_document("Makefile").format == "markdown"
    answers_alike(sqlite, kept, lambda s: s.retrieve_document("Makefile"))


def test_a_delete_takes_the_container_it_emptied(kept_pair):
    """The prune walks up from the file, so a container goes when its last key does."""
    _, kept = kept_pair
    assert (kept.root / ".!guide.md").is_dir()

    kept.delete("guide.md", recursive=True)

    assert not (kept.root / ".!guide.md").exists()
    assert not (kept.root / "guide.md").exists()
    # The plain directory of the same stem is a different key and survives.
    assert kept.retrieve_document("guide/intro.md").content == "# Intro"
