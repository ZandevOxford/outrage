"""What a store does, asked of the backend that can be written.

Every test here is about the contract :class:`outrage.store.Store` states -- keys,
ranges, subtrees, pages, excerpts, the event log -- rather than about how
SQLite keeps any of it. It runs against
:class:`~outrage.store_sqlite.SqliteStore`, and half of it writes -- so the
read-only parquet backend cannot pass this file, whatever the fixtures say.
That is checked the other way round, by putting one corpus into both backends
and comparing every answer: see ``test_store_parquet.py``. A future backend
that *can* be written should pass this file unchanged but for the fixtures at
the top. What is genuinely SQLite's own -- the schema, its migrations, the
connection per thread -- is in ``test_store_sqlite.py``.
"""

import ast
import json
import pathlib
import sqlite3
import threading
from datetime import UTC, datetime

import pytest

from conftest import in_threads, raises_rendered
from outrage import bulk, keys, messages
from outrage import store as store_module
from outrage.eventlog import EventLog
from outrage.keys import InvalidKeyError
from outrage.mounts import MountedStore
from outrage.store import (
    BoundedSubtree,
    FileStore,
    InvalidArgumentError,
    KeyNotFoundError,
    KeyRange,
    PatternNotFoundError,
    SearchCriterion,
    Store,
)
from outrage.store_files import FilesystemStore
from outrage.store_sqlite import SqliteStore


@pytest.fixture(params=["sqlite", "mounted", "files"])
def store(request, tmp_path):
    """The contract, asked of a store and of the table that presents as one.

    A mount table **is** a ``Store``: it answers this whole file, over keys
    spelled the way a caller spells them, and routes underneath. Asking the
    contract of it is the only check that says so -- a table tested only
    through its own tests is tested against what it does rather than against
    what a store is.

    A table of *one*, deliberately, and not because crossing does not matter.
    A mount point is a visible key: it lists in the level above it as its own
    kind, and describes itself from the inner store's root. So a table with a
    boundary inside this corpus would be answering correctly and still
    disagreeing with assertions that were written about one store, and the
    disagreement would be the design rather than a defect. Crossing is checked
    where its keys can be chosen for it -- differentially, one corpus in a
    single store and in a three-store table, in ``test_mounts.py``.

    Everything else still runs: every call routes, every key is translated in
    and out, every error is renamed on the way past, and ``segments`` builds
    its list with nothing to step over.
    """
    if request.param == "sqlite":
        with SqliteStore(tmp_path / "store") as s:
            yield s
        return
    if request.param == "files":
        with FilesystemStore(tmp_path / "tree") as tree:
            yield tree
        return
    with MountedStore.single(SqliteStore(tmp_path / "store")) as table:
        yield table


@pytest.fixture
def file_store(tmp_path):
    """A store that is a file, for the half of the contract about one.

    Backup, a format version, an audit and a repair are questions about
    *storage*, and a mount table refuses them rather than answering for its
    root: a check of three stores that silently reported one would be a clean
    bill of health for the two nobody looked at. So the tests that ask them ask
    a backend, and this fixture is what says which half of the file they are in.
    """
    with SqliteStore(tmp_path / "store") as s:
        yield s


@pytest.fixture
def logged(tmp_path):
    """A store that records what it is asked to do."""
    log = EventLog(tmp_path / "log.jsonl")
    with SqliteStore(tmp_path / "store", log=log) as s:
        yield s
    log.close()


def events(tmp_path) -> list[dict]:
    return [json.loads(line) for line in (tmp_path / "log.jsonl").read_text().splitlines()]


@pytest.fixture
def populated_file(file_store):
    """:func:`populated`, in a store that has a file."""
    return _populate(file_store)


@pytest.fixture
def populated(store):
    return _populate(store)


def _populate(store):
    store.store_document("context/a1b2/design", "# Store schema\n\nBody.")
    store.store_document("context/a1b2/design/!title", "Store schema")
    store.store_document("context/a1b2/task", "Add a delete tool.")
    store.store_document("context/a1b2/task/!title", "Delete tool")
    store.store_document("context/c3d4/design", "# Skill wording")
    store.store_document("context/c3d4/design/!title", "Skill wording")
    store.store_document("project/reference/implementation", "Notes.")
    return store


# -- setup ---------------------------------------------------------------


def test_reopening_keeps_content(tmp_path):
    with SqliteStore(tmp_path) as s:
        s.store_document("a", "hello")
    with SqliteStore(tmp_path) as s:
        assert s.retrieve_document("a").content == "hello"


def test_resolve_directory_prefers_explicit_then_env_then_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(store_module.ENV_DIR, raising=False)
    assert store_module.resolve_directory() == tmp_path / ".outrage"

    monkeypatch.setenv(store_module.ENV_DIR, str(tmp_path / "from-env"))
    assert store_module.resolve_directory() == tmp_path / "from-env"
    assert store_module.resolve_directory(tmp_path / "explicit") == tmp_path / "explicit"


# -- storing -------------------------------------------------------------


def test_store_overwrites(store):
    store.store_document("a/b", "first")
    store.store_document("a/b", "second")
    excerpt = store.retrieve_document("a/b")
    assert excerpt.content == "second"
    assert excerpt.total == len("second")


def test_store_returns_the_key_written(store):
    assert store.store_document("a/b", "x") == "a/b"


def test_store_validates_the_key(store):
    with pytest.raises(InvalidKeyError):
        store.store_document("context/!", "x")


def test_store_normalises_the_key_it_is_given(store):
    # Repeated and trailing delimiters are tidied rather than refused, so the
    # same document cannot be created twice by spelling its key two ways.
    store.store_document("a//b/", "x")
    assert store.retrieve_document("a/b").content == "x"


def test_format_is_detected_but_can_be_overridden(store):
    store.store_document("a/json", '{"title": "x"}')
    store.store_document("a/md", "# Heading")
    store.store_document("a/broken", "{not json")
    store.store_document("a/forced", '{"title": "x"}', format="markdown")

    assert store.retrieve_document("a/json").format == "json"
    assert store.retrieve_document("a/md").format == "markdown"
    assert store.retrieve_document("a/broken").format == "markdown"
    assert store.retrieve_document("a/forced").format == "markdown"


@pytest.mark.parametrize(
    "content",
    [
        "<!DOCTYPE html>\n<html><body>hi</body></html>",
        "<!doctype HTML>",
        '<html lang="en">',
        "\n\n  <html>",
    ],
)
def test_html_is_detected_when_it_announces_itself(store, content):
    store.store_document("a", content)
    assert store.retrieve_document("a").format == "html"


@pytest.mark.parametrize(
    "content",
    [
        # Markdown carries inline HTML, and a document opening with a tag is
        # the ordinary case rather than the HTML one. Only a doctype or the
        # root element counts.
        "<div class='note'>\n\n# Heading",
        "<img src='x.png'>",
        "<htmlish>",
        "Prose about <html> elements.",
    ],
)
def test_inline_html_is_still_markdown(store, content):
    store.store_document("a", content)
    assert store.retrieve_document("a").format == "markdown"


def test_plain_text_is_never_detected_only_asked_for(store):
    # There is no signal to detect: the same characters are valid markdown, so
    # a caller who means plain text is the only one who knows.
    store.store_document("a/detected", "Just some prose, no markup at all.")
    store.store_document("a/asked", "Just some prose, no markup at all.", format="text")

    assert store.retrieve_document("a/detected").format == "markdown"
    assert store.retrieve_document("a/asked").format == "text"


def test_format_must_be_known(store):
    with pytest.raises(ValueError, match="format"):
        store.store_document("a", "x", format="yaml")


def test_json_string_encoding_decodes_before_storing(store):
    store.store_document("a", '"Line one says \\"hi\\".\\nLine two."', encoding="json-string")

    # What is stored is the string the literal denotes, not the literal.
    assert store.retrieve_document("a").content == 'Line one says "hi".\nLine two.'


def test_json_string_encoding_applies_to_title_too(store):
    store.store_document("a", '"Body."', title='"A \\"quoted\\" title"', encoding="json-string")

    assert store.retrieve_document("a").content == "Body."
    assert store.retrieve_document("a/!title").content == 'A "quoted" title'


def test_json_string_encoding_applies_to_contents_too(store):
    store.store_document(
        "a",
        '"Body."',
        contents='"# A \\"quoted\\" heading"',
        encoding="json-string",
    )

    assert store.retrieve_document("a").content == "Body."
    assert store.retrieve_document("a/!contents").content == '# A "quoted" heading'


def test_encoding_must_be_known(store):
    with pytest.raises(ValueError, match="encoding"):
        store.store_document("a", '"x"', encoding="base64")


# The three cases below are the ones this encoding exists to catch. Each is a
# way a generated tool call has been seen to arrive damaged, and each must fail
# rather than store something that reads as if it were correct.


def test_json_string_encoding_rejects_trailing_scaffolding(store):
    with pytest.raises(InvalidArgumentError) as raised:
        store.store_document("a", '"A summary."</content>\n</invoke>\n', encoding="json-string")
    assert raised.value.code == "encoding-not-a-json-string"

    with pytest.raises(KeyNotFoundError):
        store.retrieve_document("a")


def test_json_string_encoding_rejects_scaffolding_inside_the_quotes(store):
    # Raw newlines are not legal inside a JSON string, which is what catches
    # scaffolding that lands before the closing quote rather than after it.
    with pytest.raises(InvalidArgumentError) as raised:
        store.store_document("a", '"A summary.</content>\n</invoke>\n"', encoding="json-string")
    assert raised.value.code == "encoding-not-a-json-string"


def test_json_string_encoding_rejects_unencoded_content(store):
    # A caller that asks for the encoding and then forgets to apply it fails
    # loudly, which is the property prose instructions cannot provide.
    with pytest.raises(InvalidArgumentError) as raised:
        store.store_document("a", "A plain unencoded summary.", encoding="json-string")
    assert raised.value.code == "encoding-not-a-json-string"


def test_json_string_encoding_rejects_non_strings(store):
    with pytest.raises(InvalidArgumentError) as raised:
        store.store_document("a", '{"summary": "A summary."}', encoding="json-string")
    assert raised.value.code == "encoding-not-a-string"
    assert raised.value.details["decoded"] == "dict"


def test_json_string_damage_is_still_a_value_error(store):
    # `except ValueError` around a store call predates the code, and the class
    # keeps the builtin so that it goes on working. See `errors.OutrageError`.
    with pytest.raises(ValueError):
        store.store_document("a", "unencoded", encoding="json-string")


def test_json_string_encoding_survives_a_document_full_of_scaffolding(store):
    # The store's own notes quote the scaffolding they describe. Encoding must
    # carry that content intact, not treat it as damage.
    text = "The leak looks like `</content>` followed by `</invoke>`.\n"
    store.store_document("a", json.dumps(text), encoding="json-string")

    assert store.retrieve_document("a").content == text


def test_metadata_and_document_are_independent(store):
    store.store_document("a/b", "body")
    store.store_document("a/b/!title", "Title")
    assert store.retrieve_document("a/b").content == "body"
    assert store.retrieve_document("a/b/!title").content == "Title"


def test_metadata_may_attach_to_an_implicit_key(store):
    store.store_document("context/!title", "All contexts")
    assert store.retrieve_document("context/!title").content == "All contexts"


def test_title_argument_writes_the_metadata_alongside(store):
    store.store_document("a/b", "body", title="A title")
    assert store.retrieve_document("a/b/!title").content == "A title"
    assert store.retrieve_document("a/b/!title").format == "markdown"


def test_title_argument_follows_an_allocated_number(store):
    written = store.store_document("context/?/design", "body", title="Design")
    assert written == "context/1/design"
    assert store.retrieve_document("context/1/design/!title").content == "Design"


def test_title_argument_overwrites_a_previous_title(store):
    store.store_document("a/b", "body", title="First")
    store.store_document("a/b", "body", title="Second")
    assert store.retrieve_document("a/b/!title").content == "Second"


def test_contents_argument_writes_and_overwrites_the_metadata_alongside(store):
    store.store_document("a/b", "body", contents="# First\n")
    store.store_document("a/b", "body", contents="# Second\n")
    stored = store.retrieve_document("a/b/!contents")
    assert stored.content == "# Second\n"
    assert stored.format == "markdown"


def test_contents_argument_follows_an_allocated_number(store):
    written = store.store_document("context/?/design", "body", contents="# Design\n")
    assert written == "context/1/design"
    assert store.retrieve_document("context/1/design/!contents").content == "# Design\n"


def test_title_argument_describes_a_metadata_namespace(store):
    # Metadata used not to take a title, on the grounds that it did not nest.
    # It nests now: `!` opens a namespace, and a namespace can be described.
    store.store_document("a/b/!changelog", "text", title="What changed")
    assert store.retrieve_document("a/b/!changelog/!title").content == "What changed"


def test_a_failed_title_write_leaves_no_document_behind(store):
    with pytest.raises(TypeError, match="title must be a string"):
        store.store_document("a/b", "body", title=object())
    with pytest.raises(KeyNotFoundError):
        store.retrieve_document("a/b")


def test_a_failed_contents_write_leaves_no_document_behind(store):
    with pytest.raises(TypeError, match="contents must be a string"):
        store.store_document("a/b", "body", contents=object())
    with pytest.raises(KeyNotFoundError):
        store.retrieve_document("a/b")


def test_updated_at_is_carried_rather_than_restamped(store):
    """The write that is a copy of a document that already exists.

    Every other write means "now" by it, which is why the argument is not on
    the MCP tool or on ``outrage set``: a client writing a document is writing
    it now. A transfer between two stores is the caller that legitimately
    knows better, and without this the copy says the whole corpus was written
    the moment it was copied - the one fact about a document nothing else can
    reconstruct.
    """
    store.store_document("a/b", "body", updated_at="2020-01-02T03:04:05+00:00")
    assert store.retrieve_document("a/b").updated_at == "2020-01-02T03:04:05+00:00"


def test_updated_at_is_normalised_to_utc(store):
    """One spelling, so that a string comparison keeps meaning what it says.

    A listing sorts on these and a check reads them. Half a corpus carrying an
    offset would compare wrongly against the half that does not, and every
    value the package writes itself is UTC at second precision.
    """
    store.store_document("a/b", "body", updated_at="2020-01-02T05:04:05+02:00")
    assert store.retrieve_document("a/b").updated_at == "2020-01-02T03:04:05+00:00"


def test_updated_at_without_an_offset_is_read_as_utc(store):
    store.store_document("a/b", "body", updated_at="2020-01-02T03:04:05")
    assert store.retrieve_document("a/b").updated_at == "2020-01-02T03:04:05+00:00"


def test_updated_at_stamps_the_title_written_beside_it(store):
    """The pair is written as one thing, so it is dated as one thing.

    A title dated later than the document it titles would say an edit happened
    that did not - and a copy that carried the document's timestamp and
    stamped its title with the copy's would produce exactly that.
    """
    store.store_document("a/b", "body", title="A title", updated_at="2020-01-02T03:04:05+00:00")
    assert store.retrieve_document("a/b/!title").updated_at == "2020-01-02T03:04:05+00:00"


def test_updated_at_stamps_the_contents_written_beside_it(store):
    store.store_document(
        "a/b",
        "body",
        contents="# Body\n",
        updated_at="2020-01-02T03:04:05+00:00",
    )
    assert store.retrieve_document("a/b/!contents").updated_at == "2020-01-02T03:04:05+00:00"


@pytest.mark.parametrize(
    "updated_at, error, match",
    [
        ("yesterday", ValueError, "ISO 8601"),
        ("", ValueError, "ISO 8601"),
        (1735689600, TypeError, "updated_at must be a string"),
    ],
)
def test_updated_at_must_be_a_timestamp(store, updated_at, error, match):
    with pytest.raises(error, match=match):
        store.store_document("a/b", "body", updated_at=updated_at)
    with pytest.raises(KeyNotFoundError):
        store.retrieve_document("a/b")


def test_a_write_that_names_no_timestamp_is_now(store):
    """None is the storage's own answer rather than one settled in front of it.

    Checked as a range rather than against a clock read here, because the two
    are the same second only most of the time.
    """
    before = _now()
    store.store_document("a/b", "body")
    assert before <= store.retrieve_document("a/b").updated_at <= _now()


def _now():
    return datetime.now(UTC).isoformat(timespec="seconds")


def test_a_key_may_mirror_a_file_path(store):
    store.store_document("notes/src/myfile.py", "Notes about myfile.")
    assert store.retrieve_document("notes/src/myfile.py").content == "Notes about myfile."
    assert [e.key for e in store.list_keys("notes/src").items] == ["notes/src/myfile.py"]


# -- copying -------------------------------------------------------------


@pytest.fixture
def source(tmp_path):
    """Somewhere to copy *from*, which is a store like any other.

    A database rather than the fixture's own backend, so that every target
    reads the same corpus: what varies in this section is the end doing the
    writing, which is the end ``copy_from`` is a method on.
    """
    with SqliteStore(tmp_path / "source") as other:
        yield _populate(other)


def test_copy_from_carries_every_document_metadata_included(store, source):
    """A copy that left every title behind is a store nothing can be surveyed by.

    Which is the same argument the export makes, and it is why the walk is
    ``list_keys`` all the way down: a subtree read selects documents *or*
    named metadata, and there is no "all of it" read to build a copy on.
    """
    list(store.copy_from(source))
    assert walk_keys(store) == walk_keys(source)
    assert store.retrieve_document("context/a1b2/design/!title").content == "Store schema"


def test_copy_from_carries_the_timestamp(store, source):
    """A copy rather than a restamping, which is what ``updated_at`` is for."""
    source.store_document("a/b", "body", updated_at="2020-01-02T03:04:05+00:00")
    list(store.copy_from(source))
    assert store.retrieve_document("a/b").updated_at == "2020-01-02T03:04:05+00:00"


def test_copy_from_reports_each_document_as_it_crosses(store, source):
    """One ``Transfer`` per document, as it happens rather than at the end.

    So an interrupted copy has reported exactly what it did, which is the
    property every transfer in this package streams to keep.
    """
    transfers = list(store.copy_from(source))
    assert [t.key for t in transfers] == walk_keys(source)
    assert {t.action for t in transfers} == {store_module.WROTE}
    assert sum(t.characters for t in transfers) > 0


def test_copy_from_skips_what_is_already_there(store, source):
    store.store_document("context/a1b2/task", "Mine.")
    actions = {t.key: t.action for t in store.copy_from(source)}
    assert actions["context/a1b2/task"] == store_module.SKIPPED
    assert store.retrieve_document("context/a1b2/task").content == "Mine."


def test_copy_from_overwrites_when_asked(store, source):
    store.store_document("context/a1b2/task", "Mine.")
    actions = {t.key: t.action for t in store.copy_from(source, on_conflict=store_module.OVERWRITE)}
    assert actions["context/a1b2/task"] == store_module.WROTE
    assert store.retrieve_document("context/a1b2/task").content == "Add a delete tool."


def test_copy_from_stops_at_the_first_collision_keeping_what_it_wrote(store, source):
    store.store_document("context/a1b2/task", "Mine.")
    transfers = list(store.copy_from(source, on_conflict=store_module.STOP))
    assert transfers[-1].action == store_module.STOPPED
    assert transfers[-1].key == "context/a1b2/task"
    # What came before it crossed, and nothing after it was tried.
    assert store.exists("context/a1b2/design")
    assert not store.exists("project/reference/implementation")


def test_copy_from_with_a_watermark_writes_nothing_when_the_target_moved(store, source):
    """The pre-pass: refused having written nothing, rather than half way through.

    The one outcome better than a copy that stops in the middle, and the whole
    reason the question is asked before the walk rather than at the collision.
    """
    store.store_document("context/a1b2/task", "Mine.", updated_at=NEW)

    with raises_rendered(store_module.ChangedSinceError, "written at 2026-06-01"):
        list(
            store.copy_from(
                source, on_conflict=store_module.OVERWRITE_UNCHANGED, unchanged_since=OLD
            )
        )
    assert not store.exists("context/a1b2/design")


def test_copy_from_overwrites_what_has_not_moved_since_the_watermark(store, source):
    store.store_document("context/a1b2/task", "Mine.", updated_at=OLD)

    actions = {
        t.key: t.action
        for t in store.copy_from(
            source, on_conflict=store_module.OVERWRITE_UNCHANGED, unchanged_since=NEW
        )
    }

    assert actions["context/a1b2/task"] == store_module.WROTE
    assert store.retrieve_document("context/a1b2/task").content == "Add a delete tool."


def test_copy_from_leaves_a_key_written_after_the_check_and_names_it(store, source):
    """The second layer, which only a write racing the copy can reach.

    Skipping rather than refusing here is the opposite call to the pre-pass and
    deliberate: a refusal in the middle leaves the copy half done and the
    caller reasoning about a cursor, where this completes the copy and hands
    the awkward case back as its own action.
    """
    store.store_document("context/a1b2/task", "Mine.", updated_at=OLD)
    transfers = store.copy_from(
        source, on_conflict=store_module.OVERWRITE_UNCHANGED, unchanged_since=NEW
    )
    first = next(transfers)
    # Between the check and the copy reaching that key, which is the window
    # the pre-pass shrinks and cannot close.
    store.store_document("context/a1b2/task", "Mine, since.", updated_at="2027-01-01T00:00:00Z")

    rest = {t.key: t for t in transfers}

    assert first.action == store_module.WROTE
    assert rest["context/a1b2/task"].action == store_module.CHANGED
    assert "2027-01-01" in rest["context/a1b2/task"].reason
    assert store.retrieve_document("context/a1b2/task").content == "Mine, since."
    # The rest of the copy still crossed.
    assert store.exists("project/reference/implementation")


def test_copy_from_measures_the_watermark_against_where_the_copy_lands(store, source):
    """The landing zone, not the whole target: a key nothing writes over is not a change."""
    store.store_document("elsewhere", "Mine.", updated_at=NEW)

    list(
        store.copy_from(
            source,
            prefix="archive",
            on_conflict=store_module.OVERWRITE_UNCHANGED,
            unchanged_since=OLD,
        )
    )

    assert store.exists("archive/context/a1b2/design")


def test_copy_from_refuses_a_rule_and_a_watermark_that_disagree(store, source):
    """Both pairings that mean nothing, rather than one of them resolved quietly.

    A watermark under plain ``overwrite`` reads as a guard and would buy only
    the pre-pass, replacing every collision after it unasked.
    """
    with raises_rendered(InvalidArgumentError, "needs unchanged_since"):
        list(store.copy_from(source, on_conflict=store_module.OVERWRITE_UNCHANGED))
    with raises_rendered(InvalidArgumentError, "the two disagree"):
        list(store.copy_from(source, on_conflict=store_module.OVERWRITE, unchanged_since=OLD))


def test_copy_from_refuses_a_conflict_mode_it_does_not_have(store, source):
    with pytest.raises(ValueError, match="on_conflict"):
        list(store.copy_from(source, on_conflict="clobber"))


def test_copy_from_bounds_by_subtree(store, source):
    list(store.copy_from(source, BoundedSubtree("context/a1b2")))
    assert walk_keys(store) == [
        "context/a1b2/design",
        "context/a1b2/design/!title",
        "context/a1b2/task",
        "context/a1b2/task/!title",
    ]


def test_copy_from_bounds_by_depth(store, source):
    """Depth is the subtree's, counted as every other read counts it.

    Metadata adds none, so a title crosses with the document it titles rather
    than counting as a level below it.
    """
    list(store.copy_from(source, BoundedSubtree("context", depth=1)))
    assert walk_keys(store) == []
    list(store.copy_from(source, BoundedSubtree("context", depth=2)))
    assert walk_keys(store) == [
        "context/a1b2/design",
        "context/a1b2/design/!title",
        "context/a1b2/task",
        "context/a1b2/task/!title",
        "context/c3d4/design",
        "context/c3d4/design/!title",
    ]


def test_copy_from_bounds_by_range(store, source):
    """The same range a read is bounded by, over the same order."""
    list(store.copy_from(source, key_range=KeyRange(after_subtree="context/a1b2")))
    assert walk_keys(store) == [
        "context/c3d4/design",
        "context/c3d4/design/!title",
        "project/reference/implementation",
    ]


def test_copy_from_grafts_under_a_prefix(store, source):
    list(store.copy_from(source, BoundedSubtree("context/c3d4"), prefix="archive/old"))
    assert walk_keys(store) == [
        "archive/old/context/c3d4/design",
        "archive/old/context/c3d4/design/!title",
    ]


def test_copy_from_reroots_onto_the_prefix_when_asked(store, source):
    """The spelling a move needs: the source key is stripped rather than kept.

    Grafted, the same call lands the documents at
    ``archive/old/context/c3d4/...``, and no second copy strips that back off
    again - which is why "these documents now live at another key" needed a
    flag rather than a second hop. ``context/68/findings``.
    """
    list(store.copy_from(source, BoundedSubtree("context/c3d4"), prefix="archive/old", reroot=True))
    assert walk_keys(store) == ["archive/old/design", "archive/old/design/!title"]


def test_copy_from_rerooted_lands_the_source_key_at_the_prefix_itself(store, source):
    """The subtree's own document goes *to* the target, not beneath it.

    The root case of the strip, and the one a graft cannot express at all: a
    document and the metadata below it arriving under one new name.
    """
    list(
        store.copy_from(
            source,
            BoundedSubtree("context/a1b2/design"),
            prefix="notes/schema",
            reroot=True,
        )
    )
    assert walk_keys(store) == ["notes/schema", "notes/schema/!title"]


def test_copy_from_rerooted_without_a_prefix_lands_at_the_root(store, source):
    """Stripping with nothing to graft onto is a subtree promoted to the top."""
    list(store.copy_from(source, BoundedSubtree("context/a1b2"), reroot=True))
    assert walk_keys(store) == ["design", "design/!title", "task", "task/!title"]


def _drained(transfers):
    """Every transfer, and the cursor the copy returned when it ran out.

    A ``for`` loop over a generator throws its return value away, and the
    resume cursor is that value: it is a fact about the run rather than a
    transfer, and it names a *source* key, which no transfer carries.
    """
    crossed = []
    while True:
        try:
            crossed.append(next(transfers))
        except StopIteration as stop:
            return crossed, stop.value


def test_copy_from_stops_at_a_limit_and_names_where_to_resume(store, source):
    crossed, cursor = _drained(store.copy_from(source, limit=3))

    assert len(crossed) == 3
    # The source key of the last document that crossed, not the key written
    # and not the one it stopped in front of.
    assert cursor == "context/a1b2/task"
    assert walk_keys(store) == ["context/a1b2/design", "context/a1b2/design/!title"] + [
        "context/a1b2/task"
    ]


def test_copy_from_resumed_from_its_cursor_copies_each_document_once(store, source):
    """The property the pair exists for: the pages tile the copy.

    Nothing crosses twice and nothing is stepped over, however the limit falls
    - which is what a caller taking a large subtree in pieces is relying on.
    """
    crossed, cursor, pages = [], None, 0
    while True:
        transferred, cursor = _drained(store.copy_from(source, cursor=cursor, limit=2))
        crossed += [t.key for t in transferred]
        pages += 1
        if cursor is None:
            break

    assert pages == 4
    assert crossed == walk_keys(source)
    assert walk_keys(store) == walk_keys(source)


def test_copy_from_run_out_returns_no_cursor(store, source):
    """A limit larger than what is left is not a page to come back for."""
    _, cursor = _drained(store.copy_from(source, limit=500))

    assert cursor is None


def test_copy_from_dry_run_reports_without_writing(store, source):
    transfers = list(store.copy_from(source, dry_run=True))
    assert [t.key for t in transfers] == walk_keys(source)
    assert walk_keys(store) == []


def test_copy_from_a_key_the_far_end_cannot_hold_fails_on_its_own(store, source):
    """One document that cannot cross does not end the transfer.

    A segment of ``..`` is a legal key and an impossible path component, so a
    tree refuses it and a database does not - which is the point: the copy
    reports what the far end said and carries on, and the corpus that arrives
    is the corpus that could.
    """
    source.store_document("notes/../escape", "Out.")
    transfers = {t.key: t for t in store.copy_from(source)}
    assert transfers["project/reference/implementation"].action == store_module.WROTE
    refused = isinstance(store, FilesystemStore)
    assert transfers["notes/../escape"].action == (
        store_module.FAILED if refused else store_module.WROTE
    )
    if refused:
        # The far end's own refusal, carried rather than worded: the walk hands
        # over the error and the front end writes the sentence. Rendered here
        # the way one would, to show the key it names survives the journey.
        failed = transfers["notes/../escape"]
        assert failed.reason is None
        assert failed.error is not None
        assert "notes/../escape" in messages.render(failed.error)


def test_copy_from_names_the_file_where_one_end_keeps_files(store, source, tmp_path):
    """Key to path, which is what an export report has always printed.

    The store on the far end is the only thing that knows which path, so a
    transfer asks it rather than mapping the key itself.
    """
    with FilesystemStore(tmp_path / "tree") as tree:
        transfers = {t.key: t.path for t in tree.copy_from(source)}
    assert transfers["context/a1b2/design"] == tmp_path / "tree/context/a1b2/design.md"
    assert transfers["context/a1b2/design/!title"] == (
        tmp_path / "tree/context/a1b2/design/!title.md"
    )
    # A database says nothing about where it keeps one document, because there
    # is nothing there a caller could open. Asked of a store this test names
    # rather than of the fixture, which is a tree in one of its three shapes.
    with SqliteStore(tmp_path / "target") as database:
        assert all(t.path is None for t in database.copy_from(source))


def test_a_copy_is_a_round_trip_through_any_backend(store, source, tmp_path):
    """Out to a tree and back, and the corpus is the one that left.

    The differential this project keeps finding things with, in the one shape
    a copy makes available: two backends and one corpus, compared key by key
    rather than counted.
    """
    with FilesystemStore(tmp_path / "tree") as tree:
        list(tree.copy_from(source))
        list(store.copy_from(tree))
    assert walk_keys(store) == walk_keys(source)
    for key in walk_keys(source):
        assert store.retrieve_document(key).content == source.retrieve_document(key).content
        assert store.retrieve_document(key).updated_at == source.retrieve_document(key).updated_at


def walk_keys(opened) -> list[str]:
    """Every stored key in one store, in order, containers dropped."""
    return [entry.key for entry in bulk.walk(opened, None) if entry.kind != "implicit"]


# -- autonumbering -------------------------------------------------------


def test_wildcard_numbers_from_one(store):
    assert store.store_document("tmp/?", "first") == "tmp/1"
    assert store.store_document("tmp/?", "second") == "tmp/2"
    assert store.retrieve_document("tmp/1").content == "first"


def test_wildcard_at_the_top_level(store):
    assert store.store_document("?", "x") == "1"


def test_wildcard_may_be_any_segment(store):
    assert store.store_document("context/?/design", "d") == "context/1/design"
    assert store.store_document("context/?/design", "d") == "context/2/design"
    # The allocated context is now addressable directly.
    store.store_document("context/2/task", "t")
    assert [e.key for e in store.list_keys("context/2").items] == [
        "context/2/design",
        "context/2/task",
    ]


def test_wildcard_counts_from_the_highest_number_in_use(store):
    store.store_document("tmp/1", "x")
    store.store_document("tmp/9", "x")
    store.store_document("tmp/notes", "x")
    assert store.store_document("tmp/?", "x") == "tmp/10"


def test_wildcard_does_not_fill_a_gap_left_by_a_deletion(store):
    store.store_document("tmp/?", "x")
    store.store_document("tmp/?", "x")
    store.delete("tmp/1")
    assert store.store_document("tmp/?", "x") == "tmp/3"


def test_wildcard_reuses_the_highest_number_once_it_is_deleted(store):
    # Numbers are unique among what exists, not reserved forever.
    store.store_document("tmp/?", "x")
    store.delete("tmp/1")
    assert store.store_document("tmp/?", "x") == "tmp/1"


def test_wildcard_avoids_keys_that_only_exist_implicitly(store):
    store.store_document("tmp/4/design", "x")
    assert store.store_document("tmp/?", "x") == "tmp/5"


def test_wildcard_avoids_a_number_carrying_only_metadata(store):
    store.store_document("tmp/4/!title", "x")
    assert store.store_document("tmp/?", "x") == "tmp/5"


def test_wildcard_numbering_is_per_parent(store):
    store.store_document("a/1", "x")
    store.store_document("a/2", "x")
    assert store.store_document("b/?", "x") == "b/1"
    assert store.store_document("a/?", "x") == "a/3"


def test_wildcard_ignores_the_metadata_of_its_own_parent(store):
    store.store_document("tmp/!title", "Scratch")
    assert store.store_document("tmp/?", "x") == "tmp/1"


def test_wildcard_on_a_metadata_key(store):
    assert store.store_document("tmp/?/!title", "Title") == "tmp/1/!title"


def test_wildcard_is_rejected_when_reading_or_deleting(store):
    store.store_document("tmp/1", "x")
    with pytest.raises(InvalidKeyError):
        store.retrieve_document("tmp/?")
    with pytest.raises(InvalidKeyError):
        store.delete("tmp/?")
    with pytest.raises(InvalidKeyError):
        store.get_documents(BoundedSubtree("tmp/?"))
    with pytest.raises(InvalidKeyError):
        store.list_keys("tmp/?")


def test_a_failed_write_leaves_no_allocation_behind(store):
    with pytest.raises(ValueError, match="format"):
        store.store_document("tmp/?", "x", format="yaml")
    assert store.store_document("tmp/?", "x") == "tmp/1"


# -- retrieving ----------------------------------------------------------


def test_retrieve_missing_key(store):
    with raises_rendered(KeyNotFoundError, "nothing is stored at or below"):
        store.retrieve_document("a/b")


def test_retrieve_says_when_a_key_is_a_container(populated):
    with raises_rendered(KeyNotFoundError, "4 key\\(s\\) lie beneath it"):
        populated.retrieve_document("context/a1b2")


def test_retrieve_missing_metadata_does_not_count_the_documents_descendants(populated):
    with raises_rendered(KeyNotFoundError, "nothing is stored at or below"):
        populated.retrieve_document("context/a1b2/!summary")


def test_retrieve_returns_whole_short_document(store):
    store.store_document("a", "hello")
    excerpt = store.retrieve_document("a")
    assert (excerpt.offset, excerpt.returned, excerpt.total) == (0, 5, 5)
    assert excerpt.next_offset is None
    assert not excerpt.truncated


def test_retrieve_caps_and_pages(store):
    store.store_document("a", "x" * 10_000)
    first = store.retrieve_document("a")
    assert first.returned == store_module.DEFAULT_MAX_CHARS
    assert first.total == 10_000
    assert first.next_offset == store_module.DEFAULT_MAX_CHARS
    assert first.truncated

    second = store.retrieve_document("a", offset=first.next_offset)
    assert second.returned == 2_000
    assert second.next_offset is None
    assert first.content + second.content == "x" * 10_000


def test_retrieve_character_range(store):
    store.store_document("a", "abcdefghij")
    excerpt = store.retrieve_document("a", offset=2, length=3)
    assert excerpt.content == "cde"
    assert excerpt.offset == 2
    assert excerpt.next_offset == 5


def test_length_is_capped_by_max_chars(store):
    store.store_document("a", "abcdefghij")
    assert store.retrieve_document("a", length=8, max_chars=3).content == "abc"


def test_offset_past_the_end_returns_nothing(store):
    store.store_document("a", "abc")
    excerpt = store.retrieve_document("a", offset=99)
    assert excerpt.content == ""
    assert excerpt.offset == 3
    assert excerpt.next_offset is None


def test_retrieve_from_a_literal_pattern(store):
    store.store_document("a", "intro\n## Design\nbody")
    excerpt = store.retrieve_document("a", pattern="## Design")
    assert excerpt.content == "## Design\nbody"
    assert excerpt.offset == 6


def test_pattern_occurrence_index(store):
    store.store_document("a", "one XX two XX three XX")
    assert store.retrieve_document("a", pattern="XX", occurrence=1).content == "XX three XX"
    assert store.retrieve_document("a", pattern="XX", occurrence=2).content == "XX"


def test_pattern_is_literal_not_regex(store):
    store.store_document("a", "cost is $5.00 (approx)")
    assert store.retrieve_document("a", pattern="$5.00").offset == 8
    with pytest.raises(PatternNotFoundError):
        store.retrieve_document("a", pattern=".*")


def test_pattern_searches_from_the_offset(store):
    store.store_document("a", "XX middle XX")
    assert store.retrieve_document("a", pattern="XX", offset=1).offset == 10


def test_pattern_not_found(store):
    store.store_document("a", "body")
    with pytest.raises(PatternNotFoundError):
        store.retrieve_document("a", pattern="absent")
    with pytest.raises(PatternNotFoundError):
        store.retrieve_document("a", pattern="body", occurrence=1)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"offset": -1}, "offset"),
        ({"pattern": ""}, "pattern"),
        ({"pattern": "a", "occurrence": -1}, "occurrence"),
        ({"length": -1}, "length"),
        ({"max_chars": 0}, "max_chars"),
    ],
)
def test_retrieve_rejects_bad_arguments(store, kwargs, match):
    store.store_document("a", "abc")
    with pytest.raises(ValueError, match=match):
        store.retrieve_document("a", **kwargs)


# -- reading by byte offset ----------------------------------------------
#
# The unit that survives leaving the store: a character offset is a fact about
# a Python string, and a byte offset still names the same place in a file the
# document was written out to. Every backend accepts one and returns identical
# content for it -- only the cost differs -- so these run against each of them
# from the same fixtures, and the parquet half of the same contract is the
# comparison battery in `test_store_parquet.py`.

#: A document whose characters are one, two, three and four bytes, so that
#: every arithmetic below is asking something a one-byte alphabet could not.
WIDE = "# Caf\u00e9\n\nna\u00efve \u2014 \U0001f600 tail\n\n## \u00dcber\n\nend\n"


@pytest.fixture
def wide(store):
    """The wide document, and its UTF-8, in a store."""
    store.store_document("wide", WIDE)
    return WIDE.encode()


def test_a_byte_offset_reads_from_that_byte(store, wide):
    heading = wide.index("## \u00dcber".encode())

    excerpt = store.retrieve_document("wide", byte_offset=heading)

    assert excerpt.content == WIDE[WIDE.index("## \u00dcber") :]
    assert excerpt.byte_offset == heading
    assert excerpt.total_bytes == len(wide)


def test_a_byte_read_reports_no_character_positions(store, request, wide):
    excerpt = store.retrieve_document("wide", byte_offset=0)

    # Not computed and quietly returned: converting means decoding the prefix,
    # which is the cost the byte offset exists to avoid. A caller wanting both
    # takes the pair an offset index already holds for the same position.
    assert excerpt.offset is None
    assert excerpt.next_offset is None
    assert excerpt.byte_offset == 0

    # The *total* is the one character number a byte read can carry, and
    # whether it does is a property of the backend rather than of the read.
    # A store that has the length written down answers from it; a directory of
    # files recomputes every derived fact and would have to read the document
    # to know, so it says it does not know rather than paying the scan the
    # byte offset was chosen to avoid.
    if request.node.callspec.params["store"] == "files":
        assert excerpt.total is None
    else:
        assert excerpt.total == len(WIDE)


def test_a_character_read_is_unchanged_and_says_where_it_is_in_bytes(store, wide):
    excerpt = store.retrieve_document("wide", offset=2)

    assert excerpt.offset == 2
    assert excerpt.total == len(WIDE)
    assert excerpt.content == WIDE[2:]
    assert excerpt.next_offset is None
    # The one number a caller could not have worked out for themselves.
    assert excerpt.byte_offset == len(WIDE[:2].encode())
    assert excerpt.total_bytes == len(wide)
    assert excerpt.next_byte_offset is None


def test_a_byte_offset_inside_a_character_snaps_backward(store, wide):
    emoji = wide.index("\U0001f600".encode())

    for inside in range(1, 4):
        excerpt = store.retrieve_document("wide", byte_offset=emoji + inside)

        # Backward, John's call, and the excerpt says where it actually began:
        # asked for and returned differing is normal and is not an error.
        assert excerpt.byte_offset == emoji
        assert excerpt.content.startswith("\U0001f600")


def test_a_cap_that_would_cut_a_character_trims_back(store, wide):
    excerpt = store.retrieve_document("wide", byte_offset=0, max_chars=6)

    assert excerpt.content == WIDE[:6]
    # Six characters, seven bytes: the cap counts characters whichever unit
    # addressed the read, because the budget a caller spends is context.
    assert excerpt.returned == 6
    assert excerpt.next_byte_offset == len(WIDE[:6].encode())
    assert wide[: excerpt.next_byte_offset].decode() == WIDE[:6]


def test_paging_by_byte_offset_reassembles_the_document(store, wide):
    parts, position, seen = [], 0, []
    while position is not None:
        part = store.retrieve_document("wide", byte_offset=position, max_chars=3)
        assert part.byte_offset == position
        seen.append(position)
        parts.append(part.content)
        position = part.next_byte_offset

    assert "".join(parts) == WIDE
    # Every continuation the store handed out was a character boundary, so no
    # snap ever fired: the walk is over positions it produced itself.
    assert all(wide[:at].decode().encode() == wide[:at] for at in seen)


def test_a_byte_read_that_ends_exactly_on_the_document_is_not_truncated(store):
    store.store_document("a", "abcdef")

    excerpt = store.retrieve_document("a", byte_offset=0, max_chars=6)

    assert excerpt.content == "abcdef"
    assert excerpt.next_byte_offset is None
    assert not excerpt.truncated


def test_a_byte_read_that_left_some_is_truncated(store, wide):
    excerpt = store.retrieve_document("wide", byte_offset=0, max_chars=4)

    # The definition `next_offset is not None` passes every other test here
    # and reports this one as a complete document.
    assert excerpt.next_offset is None
    assert excerpt.truncated


def test_a_byte_offset_past_the_end_returns_nothing(store, wide):
    excerpt = store.retrieve_document("wide", byte_offset=len(wide) + 99)

    assert excerpt.content == ""
    assert excerpt.byte_offset == len(wide)
    assert excerpt.next_byte_offset is None
    assert not excerpt.truncated


def test_a_document_ending_in_a_multibyte_character_pages_to_the_end(store):
    store.store_document("a", "ab\U0001f600")

    excerpt = store.retrieve_document("a", byte_offset=0, max_chars=2)
    rest = store.retrieve_document("a", byte_offset=excerpt.next_byte_offset)

    assert excerpt.content + rest.content == "ab\U0001f600"
    assert rest.next_byte_offset is None


def test_a_pattern_with_a_byte_offset_searches_from_that_byte(store, wide):
    excerpt = store.retrieve_document("wide", pattern="\u00dcber", byte_offset=0)

    assert excerpt.byte_offset == wide.index("\u00dcber".encode())
    assert excerpt.content.startswith("\u00dcber")

    # And from *at or after* it, as the character search does from an offset.
    store.store_document("twice", "\u00e9 XX middle \u00e9 XX")
    first = store.retrieve_document("twice", pattern="XX", byte_offset=0)
    after = store.retrieve_document("twice", pattern="XX", byte_offset=first.byte_offset + 1)
    assert after.content == "XX"


def test_a_pattern_a_byte_read_cannot_find_says_which_byte_it_looked_from(store, wide):
    with raises_rendered(PatternNotFoundError, "'wide' at or after byte offset 4"):
        store.retrieve_document("wide", pattern="absent", byte_offset=4)


def test_both_offsets_at_once_are_refused(store, wide):
    with raises_rendered(
        InvalidArgumentError,
        "cannot read 'wide' from two places at once: offset=1 counts characters "
        "and byte_offset=2 counts bytes; give one or the other",
    ):
        store.retrieve_document("wide", offset=1, byte_offset=2)


def test_a_zero_character_offset_beside_a_byte_offset_is_silence(store, wide):
    # Not the pair above: `offset=0` cannot be told from not passing one, and
    # does not need to be, since both spell the start of the document.
    assert store.retrieve_document("wide", offset=0, byte_offset=3).byte_offset == 3


def test_a_negative_byte_offset_is_refused(store, wide):
    with pytest.raises(ValueError, match="byte_offset"):
        store.retrieve_document("wide", byte_offset=-1)


def test_read_all_follows_the_unit_it_was_asked_in(store, wide):
    whole = store_module.read_all(store, "wide", byte_offset=0, max_chars=3)

    assert whole.content == WIDE
    assert whole.byte_offset == 0
    assert whole.offset is None
    assert not whole.truncated


# -- listing -------------------------------------------------------------


def test_list_root(populated):
    assert [e.key for e in populated.list_keys().items] == ["context", "project"]
    assert [e.kind for e in populated.list_keys().items] == ["implicit", "implicit"]


def test_list_includes_subkeys_and_metadata(populated):
    entries = populated.list_keys("context/a1b2").items
    assert [(e.key, e.kind) for e in entries] == [
        ("context/a1b2/design", "document"),
        ("context/a1b2/task", "document"),
    ]

    entries = populated.list_keys("context/a1b2/design").items
    assert [(e.key, e.kind) for e in entries] == [("context/a1b2/design/!title", "metadata")]


def test_list_reports_sizes_and_timestamps(populated):
    (entry,) = populated.list_keys("context/a1b2/task").items
    assert entry.key == "context/a1b2/task/!title"
    assert entry.size == len("Delete tool")
    assert entry.format == "markdown"
    assert entry.updated_at


def test_implicit_keys_have_no_content(populated):
    (entry,) = [e for e in populated.list_keys().items if e.key == "context"]
    assert entry.kind == "implicit"
    assert entry.size is None
    assert entry.updated_at is None


def test_a_key_with_content_and_children_lists_as_a_document(store):
    store.store_document("a", "body")
    store.store_document("a/b", "child")
    (entry,) = store.list_keys().items
    assert (entry.key, entry.kind) == ("a", "document")


def test_list_does_not_confuse_sibling_prefixes(store):
    store.store_document("a/b/c", "x")
    store.store_document("a/beta/d", "y")
    assert [e.key for e in store.list_keys("a").items] == ["a/b", "a/beta"]
    assert [e.key for e in store.list_keys("a/b").items] == ["a/b/c"]


def test_list_empty(store):
    assert store.list_keys().items == []
    assert store.list_keys("nothing/here").items == []


# -- what lies below each listed key --------------------------------------


def _below(store, key=None, **flags):
    """A level as its descendant columns, keyed by the key they belong to."""
    return {
        entry.key: (entry.descendants, entry.descendant_documents, entry.descendant_chars)
        for entry in store.list_keys(key, **flags).items
    }


def test_a_listing_reports_nothing_about_subtrees_unless_asked(populated):
    """The default listing is unchanged, which is what makes the flags opt in.

    Asserted as None rather than as absent: the fields exist on every entry, so
    a caller that reads one without asking gets a value that says "not asked"
    and never a zero it could mistake for an empty subtree.
    """
    assert _below(populated) == {"context": (None, None, None), "project": (None, None, None)}


def test_descendant_counts_separate_documents_from_metadata(store):
    """The two counts, on the definition that metadata is metadata all the way down.

    ``a/!x/y`` is the case worth writing down. It *lists* inside ``a/!x`` as an
    ordinary document -- ``entry_kind`` decides by the last segment -- and it is
    still not counted as one here, because a key with a metadata segment
    anywhere above it is metadata as far as ``a`` is concerned. A count of
    listed kinds and this number are two different questions.
    """
    store.store_document("a", "AAA")
    store.store_document("a/b", "BB")
    store.store_document("a/b/c", "C")
    store.store_document("a/!title", "T")
    store.store_document("a/!x/y", "YY")

    assert _below(store, descendant_counts=True) == {"a": (4, 2, None)}
    # The same key, listed one level down, where it is a document by kind and
    # is still not one of `a`'s two.
    (inside,) = store.list_keys("a/!x").items
    assert (inside.key, inside.kind) == ("a/!x/y", "document")


def test_descendant_totals_exclude_the_key_they_belong_to(store):
    """An entry's own row is reported by ``size`` and never again below it.

    Strictly below, so the two halves of an entry do not overlap and adding
    them gives the whole subtree. Written with a body big enough to notice: if
    the key's own characters leaked in, this would read 9 and not 3.
    """
    store.store_document("a", "AAAAAA")
    store.store_document("a/b", "BBB")

    (entry,) = store.list_keys(descendant_counts=True, descendant_chars=True).items
    assert (entry.size, entry.descendants, entry.descendant_chars) == (6, 1, 3)


def test_the_two_flags_are_asked_for_separately(store):
    """Characters cost most, so wanting counts must not buy them by accident."""
    store.store_document("a/b", "BBB")

    assert _below(store, descendant_counts=True) == {"a": (1, 1, None)}
    assert _below(store, descendant_chars=True) == {"a": (None, None, 3)}
    assert _below(store, descendant_counts=True, descendant_chars=True) == {"a": (1, 1, 3)}


def test_descendants_agree_with_the_count_beside_them(populated):
    """The one property worth having: one meaning of "how many lie below".

    ``descendant_count``'s ``whole_subtree`` selection is what a listing
    reports, so a caller cannot read two numbers about the same subtree and
    find they disagree. Checked at every key rather than at a chosen one,
    because the disagreement this guards against is a definition drifting at
    the edges -- a metadata unit counted here and not there.
    """
    for entry in bulk.walk(populated, None):
        (listed,) = [
            e
            for e in populated.list_keys(_parent(entry.key), descendant_counts=True).items
            if e.key == entry.key
        ]
        assert listed.descendants == populated.descendant_count(entry.key, whole_subtree=True)


def _parent(key):
    """The key one level above ``key``, or None at the top."""
    above = key.rpartition("/")[0]
    return above or None


def test_descendant_totals_are_filled_over_the_page(store):
    """Bounded by ``limit``, unlike ``total`` and ``total_chars``.

    A page carries the numbers for the keys it holds and no others, which is
    what keeps a wide level from costing every subtree beneath it at once. So a
    level read two at a time reports the same numbers as one read whole, and a
    caller who stops after one page has paid for one page.
    """
    for name in "abcd":
        store.store_document(f"{name}/child", name * 3)

    whole = _below(store, descendant_counts=True, descendant_chars=True)
    paged, cursor = {}, None
    while True:
        page = store.list_keys(
            limit=2, cursor=cursor, descendant_counts=True, descendant_chars=True
        )
        paged |= {
            e.key: (e.descendants, e.descendant_documents, e.descendant_chars) for e in page.items
        }
        if page.next_cursor is None:
            break
        cursor = page.next_cursor

    assert paged == whole == {f"{name}": (1, 1, 3) for name in "abcd"}


def test_an_implicit_key_is_listed_and_not_counted(store):
    """A listing can show more children than the count below their parent.

    An implicit key has no row, so it is not one of the stored keys below
    anything -- while the keys that make it exist are. ``descendant_count`` has
    always answered this way and the columns beside it must, or a store holds
    two definitions of "how many lie below" that agree everywhere except where
    a container stands.
    """
    store.store_document("a/b/c", "CCC")
    store.store_document("a/d", "D")

    (entry,) = store.list_keys(descendant_counts=True).items
    # Two keys are listed inside `a`, and only a/b/c and a/d are stored: a/b
    # is a position in the order rather than a row, so it is one of the level's
    # children and none of the parent's descendants.
    assert [e.key for e in store.list_keys("a").items] == ["a/b", "a/d"]
    assert entry.descendants == 2
    assert entry.descendants == store.descendant_count("a", whole_subtree=True)


def test_an_implicit_key_reports_what_is_under_it(store):
    """A container holds nothing itself, which is not the same as holding none.

    Its own three columns are None because it has no row; its descendant
    columns are the whole point of listing it, and reading them as absent
    because the key is implicit would leave a level unable to say where its
    material is.
    """
    store.store_document("a/b/c", "CCC")

    (entry,) = store.list_keys(descendant_counts=True, descendant_chars=True).items
    assert (entry.kind, entry.size) == ("implicit", None)
    # a/b/c alone: a/b is implicit too, and implicit keys are not stored.
    assert (entry.descendants, entry.descendant_documents, entry.descendant_chars) == (1, 1, 3)


# -- the last key at a level ----------------------------------------------


def test_last_child_is_the_final_key_in_the_order_a_listing_walks(store):
    for name in ("2", "10", "9"):
        store.store_document(f"context/{name}/state", "x")
    # Not the highest spelling, which would be "9": the level orders the way
    # `sort_form` pads, and `?last` has to agree with what a listing shows.
    assert store.last_child("context") == "10"


def test_last_child_counts_a_key_that_only_has_things_below_it(store):
    store.store_document("context/1/state", "x")
    store.store_document("context/2/notes/a", "x")
    # `context/2` holds no document of its own. It is still the newest thread
    # of work, which is what `?last` is for.
    assert store.last_child("context") == "2"


def test_last_child_ignores_metadata(store):
    store.store_document("context/1", "x", title="One")
    # `!title` sorts after the document it belongs to at the same level, and
    # `?last` stands where a document segment goes.
    assert store.last_child("context") == "1"
    assert store.last_child("context/1") is None


def test_last_child_of_a_level_with_nothing_below_it(store):
    store.store_document("context/1", "x")
    assert store.last_child("nowhere") is None
    assert store.last_child(keys.ROOT) == "context"


# -- bulk reads ----------------------------------------------------------


def test_get_documents_returns_the_subtree(populated):
    keys_found = [e.key for e in populated.get_documents(BoundedSubtree("context")).items]
    assert keys_found == [
        "context/a1b2/design",
        "context/a1b2/task",
        "context/c3d4/design",
    ]


def test_get_documents_includes_the_key_itself(store):
    store.store_document("a", "body")
    store.store_document("a/b", "child")
    assert [e.key for e in store.get_documents(BoundedSubtree("a")).items] == ["a", "a/b"]


def test_get_documents_lists_titles_across_a_subtree(populated):
    survey = populated.get_documents(BoundedSubtree("context"), meta_name="title")
    found = {e.key: e.content for e in survey.items}
    assert found == {
        "context/a1b2/design/!title": "Store schema",
        "context/a1b2/task/!title": "Delete tool",
        "context/c3d4/design/!title": "Skill wording",
    }


def test_get_documents_accepts_several_metadata_names(store):
    store.store_document("a/!title", "T")
    store.store_document("a/!summary", "S")
    store.store_document("a/!other", "O")
    survey = store.get_documents(BoundedSubtree("a"), meta_name=["title", "summary"])
    found = [e.key for e in survey.items]
    assert found == ["a/!summary", "a/!title"]


def test_get_documents_rejects_an_empty_metadata_list(store):
    with pytest.raises(ValueError, match="meta_name"):
        store.get_documents(BoundedSubtree("a"), meta_name=[])


def test_get_documents_everything(populated):
    assert len(populated.get_documents().items) == 4


def test_get_documents_depth(populated):
    assert [e.key for e in populated.get_documents(BoundedSubtree("context", depth=0)).items] == []
    assert [e.key for e in populated.get_documents(BoundedSubtree("context", depth=1)).items] == []
    assert len(populated.get_documents(BoundedSubtree("context", depth=2)).items) == 3
    assert [e.key for e in populated.get_documents(BoundedSubtree(None, depth=1)).items] == []


def test_keys_missing_meta_names_what_a_title_survey_cannot_see(populated):
    # Only project/reference/implementation was stored without a title.
    assert populated.keys_missing_meta().items == ["project/reference/implementation"]
    assert populated.keys_missing_meta(BoundedSubtree("context")).items == []


def test_keys_missing_meta_follows_the_key_and_depth_filters(populated):
    assert populated.keys_missing_meta(BoundedSubtree("project")).items == [
        "project/reference/implementation"
    ]
    assert populated.keys_missing_meta(BoundedSubtree("project", depth=1)).items == []


def test_keys_missing_meta_takes_several_names(populated):
    populated.store_document("project/reference/implementation/!summary", "Notes.")
    assert populated.keys_missing_meta(meta_name=["title", "summary"]).items == []
    assert populated.keys_missing_meta(meta_name="title").items == [
        "project/reference/implementation"
    ]


def test_keys_missing_meta_rejects_an_empty_name_list(store):
    with pytest.raises(ValueError, match="must not be an empty sequence"):
        store.keys_missing_meta(meta_name=[])


def test_get_documents_truncates_each_document(store):
    store.store_document("a/b", "x" * 5_000)
    (excerpt,) = store.get_documents(BoundedSubtree("a")).items
    assert excerpt.returned == store_module.DEFAULT_BULK_MAX_CHARS
    assert excerpt.total == 5_000
    assert excerpt.next_offset == store_module.DEFAULT_BULK_MAX_CHARS


def test_get_documents_does_not_confuse_sibling_prefixes(store):
    store.store_document("a/b/c", "x")
    store.store_document("a/beta/d", "y")
    assert [e.key for e in store.get_documents(BoundedSubtree("a/b")).items] == ["a/b/c"]


# -- searching ----------------------------------------------------------


def criterion(pattern, match="contains", target="document", meta_name=None):
    return SearchCriterion(pattern, match, target, meta_name)


def test_find_documents_matches_full_bodies_and_reports_first_spans(store):
    store.store_document("notes/1", "before " + "x" * 9000 + " needle and needle")
    store.store_document("notes/2", "nothing here")

    page = store.find_documents(BoundedSubtree("notes"), criteria=[criterion("needle")])

    assert [match.document.key for match in page.matches] == ["notes/1"]
    assert page.matches[0].document.size == len("before " + "x" * 9000 + " needle and needle")
    assert page.matches[0].witnesses[0].source_key == "notes/1"
    assert (page.matches[0].witnesses[0].start, page.matches[0].witnesses[0].end) == (
        9008,
        9014,
    )
    assert page.matched == 1
    assert page.scanned == 2
    assert page.total_candidates == 2


def test_find_documents_supports_whole_lines_and_python_regex(store):
    store.store_document("notes/1", "Pythonic\nPython\nCPython")

    page = store.find_documents(
        BoundedSubtree("notes"),
        criteria=[criterion("Python", "line"), criterion(r"C(?=Python)", "regex")],
        combine="all",
    )

    witnesses = page.matches[0].witnesses
    assert [(w.criterion, w.start, w.end) for w in witnesses] == [(0, 9, 15), (1, 16, 17)]


def test_a_whole_line_criterion_matches_in_a_crlf_document(store):
    """Rule (c) of `plans/line-endings`: CRLF is an ordinary document shape.

    True before the rules and asserted after them, because rules (a) and (b)
    are what make such a document ordinary rather than rare: a store now keeps
    the endings a document arrived with, so every backend has to serve one.
    ``line`` strips the ending before comparing, deliberately.

    The regex criterion beside it is the documented limit, pinned rather than
    repaired: the pattern is the caller's own expression, ``$`` sits after the
    carriage return, and the store cannot rewrite what they asked for.
    `plans/line-endings/coping` is the audit, and ``find_documents``'s own
    description is where a caller reads it.
    """
    store.store_document("notes/1", "# One\r\n\r\nbody\r\nlast\r\n")

    lines = store.find_documents(BoundedSubtree("notes"), criteria=[criterion("body", "line")])
    anchored = store.find_documents(
        BoundedSubtree("notes"), criteria=[criterion("(?m)body$", "regex")]
    )

    witness = lines.matches[0].witnesses[0]
    assert (witness.start, witness.end) == (9, 13)
    assert anchored.matches == ()


def test_find_documents_groups_direct_metadata_evidence_onto_its_document(store):
    store.store_document("notes/1", "body without it")
    store.store_document("notes/1/!keywords", "Rust\nPython\nSearch")
    store.store_document("notes/1/!summary", "Python appears here too")
    store.store_document("notes/1/!history/1", "Python is nested metadata")

    page = store.find_documents(
        BoundedSubtree("notes"),
        criteria=[criterion("Python", "line", "metadata", ("keywords",))],
    )

    (match,) = page.matches
    assert match.document.key == "notes/1"
    assert match.witnesses == (
        store_module.MatchWitness(0, "notes/1/!keywords", "metadata", 5, 11),
    )


def test_find_documents_any_evaluates_every_criterion_for_stable_evidence(store):
    store.store_document("notes/1", "Python body")
    store.store_document("notes/1/!title", "Python title")

    page = store.find_documents(
        BoundedSubtree("notes"),
        criteria=[
            criterion("Python"),
            criterion("Python", target="metadata", meta_name=("title",)),
        ],
    )

    assert [w.criterion for w in page.matches[0].witnesses] == [0, 1]


def test_find_documents_all_requires_every_criterion(store):
    store.store_document("notes/1", "Python body")
    store.store_document("notes/2", "Rust body")

    page = store.find_documents(
        BoundedSubtree("notes"),
        criteria=[criterion("Python"), criterion("title", target="metadata")],
        combine="all",
    )

    assert page.matches == ()


def test_find_documents_cursor_bounds_the_candidate_scan_not_the_matches(store):
    for number in range(1, 6):
        store.store_document(f"notes/{number}", "match" if number == 5 else "miss")

    first = store.find_documents(
        BoundedSubtree("notes"), criteria=[criterion("match")], scan_limit=2
    )
    second = store.find_documents(
        BoundedSubtree("notes"),
        criteria=[criterion("match")],
        scan_limit=2,
        cursor=first.next_cursor,
    )
    third = store.find_documents(
        BoundedSubtree("notes"),
        criteria=[criterion("match")],
        scan_limit=2,
        cursor=second.next_cursor,
    )

    assert first.matches == () and first.next_cursor == "notes/2"
    assert second.matches == () and second.next_cursor == "notes/4"
    assert [match.document.key for match in third.matches] == ["notes/5"]
    assert third.next_cursor is None
    assert (first.scanned, second.scanned, third.scanned) == (2, 2, 1)
    assert first.total_candidates == second.total_candidates == third.total_candidates == 5


@pytest.mark.parametrize(
    ("criteria", "combine", "scan_limit", "message"),
    [
        ([], "any", None, "between 1 and 5"),
        ([criterion("x")] * 6, "any", None, "between 1 and 5"),
        ([criterion("")], "any", None, "empty pattern"),
        ([criterion("(", "regex")], "any", None, "invalid regex"),
        ([criterion("x", target="document", meta_name=("title",))], "any", None, "must be omitted"),
        ([criterion("x")], "some", None, "must be 'any' or 'all'"),
        ([criterion("x")], "any", 0, "must be positive"),
    ],
)
def test_find_documents_validates_its_contract(store, criteria, combine, scan_limit, message):
    with pytest.raises(InvalidArgumentError) as raised:
        store.find_documents(criteria=criteria, combine=combine, scan_limit=scan_limit)
    assert message in messages.render(raised.value)


# -- deleting ------------------------------------------------------------


def test_delete_takes_metadata_with_the_document(populated):
    removed = populated.delete("context/a1b2/design")
    assert removed == ["context/a1b2/design", "context/a1b2/design/!title"]
    with pytest.raises(KeyNotFoundError):
        populated.retrieve_document("context/a1b2/design/!title")


def test_delete_one_metadata_entry(populated):
    assert populated.delete("context/a1b2/design/!title") == ["context/a1b2/design/!title"]
    assert populated.retrieve_document("context/a1b2/design").content


def test_delete_leaves_descendants_unless_recursive(populated):
    assert populated.delete("context/a1b2") == []
    assert populated.retrieve_document("context/a1b2/design").content


def test_delete_recursive_removes_the_subtree(populated):
    removed = populated.delete("context/a1b2", recursive=True)
    assert removed == [
        "context/a1b2/design",
        "context/a1b2/design/!title",
        "context/a1b2/task",
        "context/a1b2/task/!title",
    ]
    assert [e.key for e in populated.list_keys("context").items] == ["context/c3d4"]


def test_delete_recursive_does_not_touch_sibling_prefixes(store):
    store.store_document("a/b/c", "x")
    store.store_document("a/beta/d", "y")
    assert store.delete("a/b", recursive=True) == ["a/b/c"]
    assert store.retrieve_document("a/beta/d").content == "y"


def test_delete_missing_key_is_not_an_error(store):
    assert store.delete("a/b") == []


def test_descendant_count_reports_what_a_plain_delete_would_keep(populated):
    assert populated.descendant_count("context/a1b2") == 4
    assert populated.delete("context/a1b2") == []
    assert populated.descendant_count("context/a1b2") == 4
    populated.delete("context/a1b2", recursive=True)
    assert populated.descendant_count("context/a1b2") == 0


def test_descendant_count_excludes_the_key_itself(store):
    store.store_document("a/b", "x", title="T")
    assert store.descendant_count("a/b") == 0
    assert store.descendant_count("a") == 2


def test_descendant_count_does_not_cross_a_sibling_prefix(store):
    store.store_document("a/b/c", "x")
    store.store_document("a/beta/d", "y")
    assert store.descendant_count("a/b") == 1


# -- the newest change, and the watermark measured against it -------------

OLD = "2026-01-01T00:00:00+00:00"
NEW = "2026-06-01T00:00:00+00:00"


def test_latest_change_is_the_newest_timestamp_below_the_key(store):
    store.store_document("a/b", "x", updated_at=OLD)
    store.store_document("a/c", "y", updated_at=NEW)

    assert store.latest_change("a") == NEW


def test_latest_change_is_none_where_the_selection_is_empty(store):
    assert store.latest_change("a") is None


def test_latest_change_counts_metadata(store):
    store.store_document("a/b", "x", updated_at=OLD)
    store.store_document("a/b/!title", "T", updated_at=NEW)

    # A title written since the watermark is a change to the subtree: the
    # aggregate has one meaning and it is the same one the count has.
    assert store.latest_change("a") == NEW


def test_latest_change_leaves_out_the_unit_a_plain_delete_takes(store):
    store.store_document("a", "x", updated_at=OLD)
    store.store_document("a/!title", "T", updated_at=NEW)

    assert store.latest_change("a") is None
    assert store.latest_change("a", whole_subtree=True) == NEW


def test_latest_change_selects_what_the_count_counts(populated):
    """The two are one selection asked two questions, so they agree on emptiness.

    Differential rather than by expectation: whatever the corpus, a key with
    nothing below it has no newest change, and a key with something below it
    has one. A guard measuring a different set from the count beside it would
    be answering about a subtree nobody named.
    """
    for key in ("", "context", "context/a1b2", "context/a1b2/design", "project"):
        for whole in (False, True):
            counted = populated.descendant_count(key, whole_subtree=whole)
            newest = populated.latest_change(key, whole_subtree=whole)
            assert (counted > 0) == (newest is not None), (key, whole)


def test_latest_change_does_not_cross_a_sibling_prefix(store):
    store.store_document("a/b/c", "x", updated_at=OLD)
    store.store_document("a/beta/d", "y", updated_at=NEW)

    assert store.latest_change("a/b") == OLD


def test_latest_change_is_bounded_by_the_range(store):
    store.store_document("a/b", "x", updated_at=OLD)
    store.store_document("a/c", "y", updated_at=NEW)

    assert store.latest_change("a", key_range=KeyRange(before="a/c")) == OLD


def test_a_delete_with_no_watermark_is_unchecked(store):
    store.store_document("a/b", "x", updated_at=NEW)

    assert store.delete("a/b") == ["a/b"]


def test_a_delete_is_refused_when_the_key_moved_since(store):
    store.store_document("a/b", "x", updated_at=NEW)

    with raises_rendered(store_module.ChangedSinceError, "written at 2026-06-01"):
        store.delete("a/b", unchanged_since=OLD)
    assert store.exists("a/b")


def test_a_delete_goes_through_when_nothing_moved_since(store):
    store.store_document("a/b", "x", updated_at=OLD)

    assert store.delete("a/b", unchanged_since=NEW) == ["a/b"]


def test_a_plain_delete_is_measured_over_the_unit_it_takes(store):
    """The metadata goes with the key, so a title written since is a change.

    And a child does not go, so a child written since is not one: a guard on
    the wrong keys refuses a delete that would have taken nothing anybody
    touched.
    """
    store.store_document("a", "x", updated_at=OLD)
    store.store_document("a/!title", "T", updated_at=NEW)
    store.store_document("a/b", "y", updated_at=NEW)

    with raises_rendered(store_module.ChangedSinceError):
        store.delete("a", unchanged_since=OLD)

    store.store_document("a/!title", "T", updated_at=OLD)
    assert store.delete("a", unchanged_since=OLD) == ["a", "a/!title"]


def test_a_recursive_delete_is_measured_over_the_subtree_it_takes(store):
    store.store_document("a", "x", updated_at=OLD)
    store.store_document("a/b/c", "y", updated_at=NEW)

    with raises_rendered(store_module.ChangedSinceError):
        store.delete("a", recursive=True, unchanged_since=OLD)
    assert store.exists("a/b/c")


def test_a_watermark_that_is_not_a_timestamp_is_a_sentence(store):
    store.store_document("a/b", "x")

    with raises_rendered(InvalidArgumentError, "ISO 8601"):
        store.delete("a/b", unchanged_since="last tuesday")


def test_a_watermark_is_compared_in_one_spelling(store):
    """An offset is not an hour of difference in the wrong direction.

    The comparison is a string comparison, so a caller writing 11:15+01:00 and
    a store holding 10:15+00:00 have named the same moment and must compare
    equal -- unnormalised, the first sorts after the second and the guard
    passes a write it should have refused.
    """
    store.store_document("a/b", "x", updated_at="2026-01-01T10:15:00+00:00")

    assert store.delete("a/b", unchanged_since="2026-01-01T11:15:00+01:00") == ["a/b"]


def test_storing_an_empty_document_is_not_a_deletion(store):
    store.store_document("a/b", "body")
    store.store_document("a/b", "")
    excerpt = store.retrieve_document("a/b")
    assert excerpt.content == ""
    assert excerpt.total == 0
    assert [e.key for e in store.list_keys("a").items] == ["a/b"]


# -- the event log ---------------------------------------------------------


def test_a_store_without_a_log_writes_nothing(tmp_path):
    with SqliteStore(tmp_path / "store") as s:
        s.store_document("a/b", "body")
        s.retrieve_document("a/b")

    # The store has to stay usable as a plain library, so the default has to
    # leave no trace at all rather than merely a small one.
    assert [p.name for p in tmp_path.iterdir()] == ["store"]


@pytest.mark.parametrize(
    ("call", "op"),
    [
        (lambda s: s.store_document("a/b", "body"), "store_document"),
        (lambda s: s.retrieve_document("a/b"), "retrieve_document"),
        (lambda s: s.list_keys("a").items, "list_keys"),
        (lambda s: s.get_documents(BoundedSubtree("a")).items, "get_documents"),
        (lambda s: s.keys_missing_meta(BoundedSubtree("a")).items, "keys_missing_meta"),
        (lambda s: s.descendant_count("a"), "descendant_count"),
        (lambda s: s.latest_change("a"), "latest_change"),
        (lambda s: s.delete("a/b"), "delete"),
    ],
)
def test_every_public_operation_is_recorded(logged, tmp_path, call, op):
    logged.store_document("a/b", "body")
    call(logged)

    assert op in [event["op"] for event in events(tmp_path)]


def test_the_arguments_recorded_are_the_ones_the_caller_passed(logged, tmp_path):
    logged.store_document("a/b", "body")
    logged.retrieve_document("a/b", max_chars=50)

    (event,) = [e for e in events(tmp_path) if e["op"] == "retrieve_document"]
    assert event["args"]["key"] == "a/b"
    assert event["args"]["max_chars"] == 50


def test_a_truncated_read_records_where_it_stopped(logged, tmp_path):
    logged.store_document("a/b", "x" * 500)
    logged.retrieve_document("a/b", max_chars=100)

    (event,) = [e for e in events(tmp_path) if e["op"] == "retrieve_document"]
    # Following the log forward from here is what says whether the caller ever
    # came back for the rest, which nothing else records.
    assert event["result"]["next_offset"] == 100
    assert event["result"]["total"] == 500


def test_a_failed_call_is_recorded_with_its_error(logged, tmp_path):
    with pytest.raises(KeyNotFoundError):
        logged.retrieve_document("nope")

    (event,) = [e for e in events(tmp_path) if e["op"] == "retrieve_document"]
    assert event["error"]["type"] == "KeyNotFoundError"
    assert "result" not in event


def test_stored_text_is_recorded_under_the_content_policy(logged, tmp_path):
    logged.store_document("a/b", "body", title="A title", contents="# Body\n")

    (event,) = [e for e in events(tmp_path) if e["op"] == "store_document"]
    assert event["args"]["content"]["text"] == "body"
    assert event["args"]["title"]["text"] == "A title"
    assert event["args"]["contents"]["text"] == "# Body\n"
    assert event["args"]["key"] == "a/b"


def test_a_delete_records_the_keys_it_removed(logged, tmp_path):
    logged.store_document("a/b", "body", title="A title")
    logged.delete("a/b")

    (event,) = [e for e in events(tmp_path) if e["op"] == "delete"]
    assert event["result"]["keys"] == ["a/b", "a/b/!title"]


def test_work_done_on_a_caller_s_behalf_is_recorded_too(logged, tmp_path):
    logged.store_document("a/b", "body")
    with pytest.raises(KeyNotFoundError):
        logged.retrieve_document("a")

    # Reading a container counts what lies beneath it, so that the failure can
    # say so rather than dead-ending. One call being more than one access is
    # exactly what the log is for.
    assert [e["op"] for e in events(tmp_path)][-2:] == ["descendant_count", "retrieve_document"]


def test_keys_missing_meta_is_one_access_now(logged, tmp_path):
    logged.store_document("a/b", "body")
    logged.keys_missing_meta(BoundedSubtree("a"))

    # It used to read every document in the subtree through get_documents and
    # throw the content away, which the log is what showed.
    assert [e["op"] for e in events(tmp_path)][-1:] == ["keys_missing_meta"]
    assert "get_documents" not in [e["op"] for e in events(tmp_path)]


# -- backup --------------------------------------------------------------


def documents_in(path) -> int:
    """Row count in a database file, read the way a restorer would."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return conn.execute("SELECT count(*) FROM documents").fetchone()[0]
    finally:
        conn.close()


def test_backup_holds_what_the_store_holds(populated_file):
    result = populated_file.backup()

    assert result.integrity == "ok"
    assert result.documents == 7
    assert result.bytes > 0
    assert documents_in(result.path) == 7


def test_backup_captures_writes_that_are_still_only_in_the_wal(populated_file, tmp_path):
    """The whole reason this lives in the store rather than in a caller.

    Nothing has been checkpointed, so the .sqlite file on its own is a database
    that opens cleanly and has almost nothing in it. Copying the file is the
    failure being guarded against, so the test states it directly.
    """
    copied = tmp_path / "copied.sqlite"
    copied.write_bytes(populated_file.path.read_bytes())
    try:
        by_copy = documents_in(copied)
    except sqlite3.DatabaseError:
        by_copy = 0  # Not even a schema yet, which is the same failure, harder.

    result = populated_file.backup()

    assert by_copy < 7, "a file copy would have been good enough, so this test proves nothing"
    assert documents_in(result.path) == 7


def test_a_backup_is_a_store_that_can_be_opened(populated_file, tmp_path):
    result = populated_file.backup()

    restored_dir = tmp_path / "restored"
    restored_dir.mkdir()
    (restored_dir / store_module.default_store_file()).write_bytes(result.path.read_bytes())

    with SqliteStore(restored_dir) as restored:
        assert restored.retrieve_document("context/a1b2/task").content == "Add a delete tool."


def test_backup_defaults_to_a_timestamped_name_below_the_store(populated_file):
    result = populated_file.backup()

    assert result.path.parent == (populated_file.directory / store_module.BACKUP_DIR_NAME).resolve()
    assert result.path.name.startswith("store-")
    assert result.path.suffix == ".sqlite"


def test_a_destination_directory_gets_the_default_name(populated_file, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    result = populated_file.backup(elsewhere)

    assert result.path.parent == elsewhere.resolve()
    assert result.path.name.startswith("store-")


def test_a_named_destination_is_used_as_given(populated_file, tmp_path):
    result = populated_file.backup(tmp_path / "snapshots" / "monday.sqlite")

    assert result.path == (tmp_path / "snapshots" / "monday.sqlite").resolve()


def test_an_existing_destination_is_refused(populated_file, tmp_path):
    target = tmp_path / "taken.sqlite"
    target.write_text("not a database")

    with raises_rendered(store_module.BackupError, "already exists"):
        populated_file.backup(target)

    assert target.read_text() == "not a database"


def test_an_existing_destination_can_be_replaced_on_purpose(populated_file, tmp_path):
    target = tmp_path / "taken.sqlite"
    target.write_text("not a database")

    result = populated_file.backup(target, overwrite=True)

    assert documents_in(result.path) == 7


def test_the_store_itself_is_refused_as_a_destination(populated_file):
    with raises_rendered(store_module.BackupError, "the store itself"):
        populated_file.backup(populated_file.path)

    # The refusal has to come before anything is unlinked, or the check that
    # protects the store is what destroys it.
    assert populated_file.retrieve_document("context/a1b2/task").content == "Add a delete tool."


def test_a_short_backup_is_refused_rather_than_returned(populated_file, monkeypatch):
    """The count is the only check that catches a copy which opens cleanly."""
    monkeypatch.setattr(
        SqliteStore,
        "_verify_backup",
        lambda self, target: (_ for _ in ()).throw(
            store_module.BackupError("backup-short", target=str(target), found=0, expected=7)
        ),
    )

    with raises_rendered(store_module.BackupError, "holds 0 documents"):
        populated_file.backup()


def test_a_backup_is_logged_with_what_it_wrote(logged, tmp_path):
    logged.store_document("a/b", "body")
    result = logged.backup(tmp_path / "snapshot.sqlite")

    (event,) = [e for e in events(tmp_path) if e["op"] == "backup"]
    assert event["result"]["documents"] == 1
    assert event["result"]["path"] == str(result.path)


# -- numeric segments ----------------------------------------------------


def test_numbered_keys_come_back_in_numeric_order(tmp_path):
    with SqliteStore(tmp_path) as s:
        for _ in range(12):
            s.store_document("findings/?", "a finding")

        found = s.get_documents(BoundedSubtree("findings")).items
        numbered = [e.key.rsplit("/", 1)[1] for e in found]
        assert numbered == [str(n) for n in range(1, 13)]
        listed = [e.key.rsplit("/", 1)[1] for e in s.list_keys("findings").items]
        assert listed == [str(n) for n in range(1, 13)]


def test_a_cursor_parked_on_a_key_does_not_miss_a_later_one(tmp_path):
    """The property pagination will rest on, checked at the store.

    Sorting keys as text puts 'findings/10' behind 'findings/9', so a reader
    resuming after the ninth would never see the tenth.
    """
    with SqliteStore(tmp_path) as s:
        for _ in range(9):
            s.store_document("findings/?", "before")
        ninth = s.list_keys("findings").items[-1].key
        tenth = s.store_document("findings/?", "after")

        assert (ninth, tenth) == ("findings/9", "findings/10")
        assert keys.sort_form(tenth) > keys.sort_form(ninth)


def test_a_padded_key_names_the_same_document_as_the_unpadded_one(tmp_path):
    with SqliteStore(tmp_path) as s:
        written = s.store_document("context/007/task", "the body")

        assert written == "context/7/task"
        assert s.retrieve_document("context/7/task").content == "the body"
        assert s.retrieve_document("context/00007/task").content == "the body"

        s.store_document("context/7/task", "replaced")
        assert s.retrieve_document("context/007/task").content == "replaced"
        assert len(s.get_documents(BoundedSubtree("context")).items) == 1


def test_allocation_counts_past_a_key_that_was_written_padded(tmp_path):
    with SqliteStore(tmp_path) as s:
        s.store_document("context/007", "seventh")
        assert s.store_document("context/?", "next") == "context/8"


# -- pagination ----------------------------------------------------------


def paged(call, *args, **kwargs) -> list:
    """Everything ``call`` returns, taken one page at a time through the cursor.

    Guards the two ways a cursor fails to terminate rather than looping on
    them: a page that returns nothing but asks to be resumed, and a cursor that
    does not move. Both hang a real caller, and a test that hangs reports
    nothing at all.
    """
    collected: list = []
    cursor = None
    for _ in range(1000):
        page = call(*args, cursor=cursor, **kwargs)
        collected += page.items
        if page.next_cursor is None:
            return collected
        assert page.items, "a page with a cursor and nothing in it never terminates"
        assert page.next_cursor != cursor, f"the cursor did not move past {cursor}"
        cursor = page.next_cursor
    raise AssertionError("the cursor never reached the end")


def a_level(store: Store, count: int) -> None:
    for number in range(1, count + 1):
        store.store_document(f"findings/{number}", f"finding {number}")


def test_a_page_states_the_size_of_the_whole(store):
    a_level(store, 12)

    page = store.list_keys("findings", limit=5)

    assert page.returned == 5
    # Without this a caller cannot tell 5 of 6 from 5 of 40000, and treats them
    # the same.
    assert page.total == 12
    assert page.total_chars == sum(len(f"finding {n}") for n in range(1, 13))
    assert page.next_cursor == "findings/5"


def test_the_last_page_carries_no_cursor(store):
    a_level(store, 3)

    page = store.list_keys("findings", limit=5)

    assert page.returned == 3
    assert page.next_cursor is None
    assert not page.truncated


def test_paging_a_level_sees_every_key_exactly_once(store):
    a_level(store, 12)

    whole = [entry.key for entry in store.list_keys("findings").items]
    by_page = [entry.key for entry in paged(store.list_keys, key="findings", limit=5)]

    assert by_page == whole
    assert len(whole) == 12


def test_a_cursor_pages_in_numeric_order(store):
    a_level(store, 12)

    page = store.list_keys("findings", limit=3)

    # The ordering the migration exists for: under text ordering this page is
    # 1, 10, 11 and the cursor parks after 11, never to see 2 through 9.
    assert [entry.key for entry in page.items] == ["findings/1", "findings/2", "findings/3"]


def test_a_parked_cursor_returns_what_was_written_after_it(store):
    a_level(store, 9)
    cursor = store.list_keys("findings", limit=9).items[-1].key

    # What another agent appends while the first is away. The next page and
    # what is new since I last looked are the same operation.
    store.store_document("findings/?", "written by someone else")

    page = store.list_keys("findings", cursor=cursor)

    assert [entry.key for entry in page.items] == ["findings/10"]


def test_a_cursor_may_be_written_padded(store):
    a_level(store, 4)

    page = store.list_keys("findings", cursor="findings/02")

    assert [entry.key for entry in page.items] == ["findings/3", "findings/4"]


def test_implicit_children_page_alongside_real_ones(store):
    # Alternating, so a page boundary falls between the two halves and either
    # half limited on its own would drop keys the other pushed past the edge.
    for number in range(1, 9):
        if number % 2:
            store.store_document(f"level/{number}", "content")
        else:
            store.store_document(f"level/{number}/beneath", "content")

    whole = [entry.key for entry in store.list_keys("level").items]
    by_page = [entry.key for entry in paged(store.list_keys, key="level", limit=3)]

    assert by_page == whole
    assert [entry.kind for entry in store.list_keys("level").items[:2]] == [
        "document",
        "implicit",
    ]


def test_a_key_that_is_both_real_and_a_container_is_counted_once(store):
    store.store_document("a/b", "content")
    store.store_document("a/b/c", "content")

    page = store.list_keys("a")

    assert [entry.key for entry in page.items] == ["a/b"]
    assert page.total == 1


def test_the_total_counts_implicit_keys_too(store):
    store.store_document("a/b/c", "content")
    store.store_document("a/d/e", "content")

    page = store.list_keys("a", limit=1)

    assert page.total == 2
    assert page.total_chars == 0


def test_get_documents_pages_the_collection(populated):
    whole = [excerpt.key for excerpt in populated.get_documents().items]

    by_page = [excerpt.key for excerpt in paged(populated.get_documents, limit=2)]

    assert by_page == whole
    assert len(whole) == 4


def test_get_documents_states_the_size_of_the_whole(populated):
    page = populated.get_documents(BoundedSubtree("context"), limit=1)

    assert page.returned == 1
    assert page.total == 3
    assert page.total_chars == sum(
        len(excerpt.content) for excerpt in populated.get_documents(BoundedSubtree("context")).items
    )
    assert page.next_cursor == "context/a1b2/design"


def test_a_page_is_capped_in_characters_as_well_as_in_documents(store):
    for number in range(1, 11):
        store.store_document(f"notes/{number}", "x" * 500)

    page = store.get_documents(
        BoundedSubtree("notes"),
        limit=10,
        max_chars=500,
        max_total_chars=1200,
    )

    # Both stated bounds are honoured by ten documents of five hundred
    # characters, which is five thousand characters. The second cap is what
    # makes the answer bounded rather than only bounded-sounding.
    assert page.returned == 2
    assert sum(excerpt.returned for excerpt in page.items) <= 1200
    assert page.next_cursor == "notes/2"
    assert page.total == 10


def test_a_document_larger_than_the_budget_still_comes_back(store):
    store.store_document("notes/1", "x" * 5000)
    store.store_document("notes/2", "y" * 5000)

    page = store.get_documents(BoundedSubtree("notes"), max_chars=5000, max_total_chars=100)

    # Otherwise the page is empty, the cursor does not move, and a caller
    # following it makes no progress for ever.
    assert page.returned == 1
    assert page.next_cursor == "notes/1"


def test_the_character_budget_pages_to_the_end(store):
    for number in range(1, 11):
        store.store_document(f"notes/{number}", "x" * 500)

    seen = [
        excerpt.key
        for excerpt in paged(store.get_documents, BoundedSubtree("notes"), max_total_chars=1200)
    ]

    assert len(seen) == 10
    assert seen == [excerpt.key for excerpt in store.get_documents(BoundedSubtree("notes")).items]


def test_get_documents_depth_still_bounds_a_paged_read(populated):
    page = populated.get_documents(BoundedSubtree("context", depth=2), limit=1)

    assert page.total == 3
    assert page.returned == 1
    walked = paged(populated.get_documents, BoundedSubtree("context", depth=2))
    assert [excerpt.key for excerpt in walked] == [
        "context/a1b2/design",
        "context/a1b2/task",
        "context/c3d4/design",
    ]


def test_keys_missing_meta_pages_and_states_the_whole(store):
    for number in range(1, 6):
        store.store_document(f"notes/{number}", "body")
    store.store_document("notes/3/!title", "Titled")

    page = store.keys_missing_meta(BoundedSubtree("notes"), limit=2)

    assert page.items == ["notes/1", "notes/2"]
    assert page.total == 4
    assert page.next_cursor == "notes/2"
    assert paged(store.keys_missing_meta, BoundedSubtree("notes"), limit=2) == [
        "notes/1",
        "notes/2",
        "notes/4",
        "notes/5",
    ]


def test_keys_missing_meta_wants_all_of_the_names_missing(store):
    store.store_document("a/b", "body")
    store.store_document("a/b/!title", "Titled")

    assert store.keys_missing_meta(BoundedSubtree("a"), meta_name=["title", "summary"]).items == []
    assert store.keys_missing_meta(BoundedSubtree("a"), meta_name="summary").items == ["a/b"]


def test_a_level_of_nothing_but_containers_pages_to_the_end(store):
    for number in range(1, 13):
        store.store_document(f"level/{number}/beneath", "content")

    by_page = [entry.key for entry in paged(store.list_keys, key="level", limit=3)]

    # Every key on this level is implicit, so nothing from the real half is
    # over-fetched to cover a half that stopped one short of saying there is
    # more. The half has to carry that signal itself.
    assert by_page == [f"level/{number}" for number in range(1, 13)]


def test_containers_sort_as_numbers_like_everything_else(store):
    for number in range(1, 13):
        store.store_document(f"level/{number}/beneath", "content")

    # Under a limit, which is what makes the ordering decide *which* keys the
    # page holds rather than only what order they are printed in.
    listed = [entry.key for entry in store.list_keys("level", limit=2).items]

    # These keys have no row of their own, so they have no stored sort_key
    # either. Ordering them as text is the failure the whole migration exists
    # to remove, reintroduced on the one half that cannot use the column.
    assert listed == ["level/1", "level/2"]


def test_missing_meta_stats_counts_without_listing(populated):
    stats = populated.missing_meta_stats()

    assert stats.total == 1
    assert stats.sample == []
    assert stats.total_chars > 0


def test_missing_meta_stats_samples_when_asked(populated):
    assert populated.missing_meta_stats(sample=10).sample == ["project/reference/implementation"]


def test_missing_meta_stats_bounds_by_the_surveys_own_cursors(store):
    for key in ["n/1", "n/2", "n/3", "n/4"]:
        store.store_document(key, "body")
    store.store_document("n/2/!title", "T")

    whole = store.missing_meta_stats(BoundedSubtree("n"), sample=10)
    below = store.missing_meta_stats(
        BoundedSubtree("n"),
        window=KeyRange(before_inclusive="n/2/!title"),
        sample=10,
    )
    above = store.missing_meta_stats(
        BoundedSubtree("n"),
        window=KeyRange(after="n/2/!title"),
        sample=10,
    )

    # Exclusive below, inclusive above, so the two halves partition the whole.
    assert whole.sample == ["n/1", "n/3", "n/4"]
    assert below.sample == ["n/1"]
    assert above.sample == ["n/3", "n/4"]
    assert below.total + above.total == whole.total


def test_missing_meta_stats_places_a_document_where_its_metadata_would_sort(store):
    for key in ["a", "a/x", "a/y"]:
        store.store_document(key, "body")
    store.store_document("a/y/!title", "T")

    # The survey walks metadata order, and since schema 5 that order *is*
    # document order: a/!title < a/x/!title < a/y/!title, exactly as
    # a < a/x < a/y. Everything above therefore sits on the same side of the
    # cursor in both orderings.
    below = store.missing_meta_stats(window=KeyRange(before_inclusive="a/y/!title"), sample=10)
    assert below.sample == ["a", "a/x"]
    assert store.missing_meta_stats(window=KeyRange(after="a/y/!title"), sample=10).sample == []

    # Two separate defects put `a` on the wrong side of this before: the `:`
    # separator until schema 4, and then `/` as the sort delimiter until
    # schema 5. Both are closed, and this pins them.
    assert keys.sort_form("a/!title") < keys.sort_form("a/x/!title")
    assert keys.sort_form("a") < keys.sort_form("a/x")


def test_missing_meta_stats_rejects_an_empty_name_list(store):
    with pytest.raises(ValueError):
        store.missing_meta_stats(meta_name=[])


def test_survey_windows_tile_over_adversarial_keys(tmp_path):
    """Windows must tile whatever the keys look like, not just tidy ones.

    Built from the characters that sort around ``/``: ``-`` (0x2D) and ``.``
    (0x2E) both sort below it and are legal in a segment, so under schema 4 a
    document could sort before a sibling while its metadata sorted after that
    sibling's. A window bounded by document keys double counts exactly there --
    but only for some sets of which documents carry the metadata, so this
    sweeps every one of them rather than a few tidy prefixes.

    ``a/ c`` is here for schema 5 specifically. Its segment *begins* with a
    space (0x20), which sorts below ``!`` (0x21) -- so under schema 4 it would
    have sorted ahead of ``a/!title`` and put metadata after a sibling
    document. Segments could not begin that way then; they can now, and the
    sort form marks segments rather than trusting where ``!`` falls.

    The sweep doubles with every key added, so this stays deliberately small
    and adversarial rather than large.
    """
    keyset = ["a", "a-x", "a.y", "a/ c", "a/b", "a/b/c", "ab", "b"]

    for mask in range(1, 2 ** len(keyset)):
        titled = [k for i, k in enumerate(keyset) if mask >> i & 1]
        store = SqliteStore(tmp_path / f"s{mask}")
        for key in keyset:
            store.store_document(key, "body")
        for key in titled:
            store.store_document(f"{key}/!title", "T")

        after, seen, counted = None, [], 0
        while True:
            page = store.get_documents(meta_name=["title"], limit=1, cursor=after)
            window = store.missing_meta_stats(
                window=KeyRange(after=after, before_inclusive=page.next_cursor),
                meta_name=["title"],
                sample=100,
            )
            seen += window.sample
            counted += window.total
            if page.next_cursor is None:
                break
            after = page.next_cursor

        whole = store.keys_missing_meta(meta_name=["title"], limit=1000)
        assert sorted(seen) == sorted(whole.items), f"titled={titled}"
        assert len(seen) == len(set(seen)), f"double counted, titled={titled}"
        assert counted == whole.total, f"titled={titled}"
        store.connection.close()


def test_a_document_and_its_metadata_survive_the_rebuild_in_order(file_store):
    # The property the whole sort form exists for, read back through the file_store
    # rather than asserted on the encoding.
    for key in ["a", "a-x", "a/b"]:
        file_store.store_document(key, "body", title="T")

    listed = [
        r["key"]
        for r in file_store.connection.execute("SELECT key FROM documents ORDER BY sort_key")
    ]
    assert listed == [
        "a",
        "a/!title",
        "a/b",
        "a/b/!title",
        "a-x",
        "a-x/!title",
    ]


def test_metadata_may_have_a_subtree(store):
    # Schema 5 dropped the leaf rule: a path may continue below a `!` segment,
    # and everything under it is metadata rather than a document.
    store.store_document("a", "body", title="T")
    store.store_document("a/!embedding/openai", "[0.1]")

    assert store.retrieve_document("a/!embedding/openai").content == "[0.1]"

    # The intermediate exists implicitly, exactly as a document subtree's does.
    listed = {e.key: e.kind for e in store.list_keys("a").items}
    assert listed["a/!embedding"] == "implicit"
    assert listed["a/!title"] == "metadata"

    # A survey for `title` must not match the sub-path, or every entry beneath
    # a metadata key would count as one.
    page = store.get_documents(meta_name=["title"])
    assert [d.key for d in page.items] == ["a/!title"]


# -- range bounds --------------------------------------------------------


@pytest.fixture
def ranged(store):
    """Four top level keys, the middle one with a subtree of its own."""
    store.store_document("a", "A")
    store.store_document("m", "M")
    store.store_document("m/!title", "Middle")
    store.store_document("m/x", "MX")
    store.store_document("m/x/deep", "MXD")
    store.store_document("z", "Z")
    return store


def keys_of(page) -> list[str]:
    return [item.key for item in page.items]


def test_a_zero_limit_counts_a_window_without_reading_it(ranged):
    # What a caller reading several windows asks of the ones past the end of
    # its page: the totals still describe the whole collection, so every window
    # has to be counted even after the page is full.
    page = ranged.get_documents(limit=0)
    assert page.items == []
    assert page.total == 5  # the documents; the title is not one of them
    assert page.next_cursor is None


def test_before_excludes_the_key_and_everything_below_it(ranged):
    # Not just the key: a descendant sorts after its parent, so a bound that
    # stopped at the key alone would still walk into its subtree.
    assert keys_of(ranged.get_documents(key_range=KeyRange(before="m"))) == ["a"]


def test_after_subtree_starts_past_the_whole_subtree(ranged):
    assert keys_of(ranged.get_documents(key_range=KeyRange(after_subtree="m"))) == ["z"]


def test_a_cursor_stops_at_the_key_and_a_subtree_bound_stops_past_it(ranged):
    # The distinction the two exist for. `after` resumes a page, so it is
    # exclusive of the key and inclusive of that key's children; nothing else
    # can say "past all of this", which is what stepping over a mount needs.
    assert keys_of(ranged.get_documents(cursor="m")) == ["m/x", "m/x/deep", "z"]
    assert keys_of(ranged.get_documents(key_range=KeyRange(after_subtree="m"))) == ["z"]


def test_final_subtree_runs_to_the_end_of_the_subtree(ranged):
    within = ranged.get_documents(key_range=KeyRange(final_subtree="m"))
    assert keys_of(within) == ["a", "m", "m/x", "m/x/deep"]


def test_a_key_and_a_subtree_bound_compose(ranged):
    inside = ranged.get_documents(BoundedSubtree("m"), key_range=KeyRange(before="m/x"))
    assert keys_of(inside) == ["m"]
    past = ranged.get_documents(BoundedSubtree("m"), key_range=KeyRange(after_subtree="m/x"))
    assert keys_of(past) == []


def test_the_windows_either_side_of_a_subtree_tile_the_rest(ranged):
    whole = ranged.get_documents()
    below = ranged.get_documents(key_range=KeyRange(before="m"))
    above = ranged.get_documents(key_range=KeyRange(after_subtree="m"))

    assert keys_of(below) + keys_of(above) == ["a", "z"]
    assert below.total + above.total == whole.total - 3  # m, m/x, m/x/deep
    assert below.total_chars + above.total_chars == whole.total_chars - len("M" + "MX" + "MXD")


def test_range_bounds_count_the_window_and_a_cursor_does_not(ranged):
    # The bounds are part of the selection, so a count taken over them counts
    # the window and windows can be added up. The cursor is not: a page's
    # totals have never depended on where the reader had got to.
    windowed = ranged.get_documents(key_range=KeyRange(before="m"))
    assert windowed.total == 1

    resumed = ranged.get_documents(cursor="a")
    assert resumed.total == ranged.get_documents().total
    assert keys_of(resumed) == ["m", "m/x", "m/x/deep", "z"]


def test_metadata_travels_with_the_document_it_belongs_to(ranged):
    survey = ranged.get_documents(key_range=KeyRange(before="m"), meta_name=["title"])
    assert keys_of(survey) == []
    survey = ranged.get_documents(key_range=KeyRange(final_subtree="m"), meta_name=["title"])
    assert keys_of(survey) == ["m/!title"]


def test_keys_missing_meta_takes_the_same_bounds(ranged):
    ranged.store_document("a/!title", "A")
    whole = ranged.keys_missing_meta(meta_name="title")
    below = ranged.keys_missing_meta(key_range=KeyRange(before="m"), meta_name="title")
    above = ranged.keys_missing_meta(key_range=KeyRange(after_subtree="m"), meta_name="title")

    # `m` carries a title of its own; the two below it do not.
    assert whole.items == ["m/x", "m/x/deep", "z"]
    assert below.items == []
    assert above.items == ["z"]
    assert below.total + above.total == whole.total - 2


def test_missing_meta_stats_bounds_the_range_and_the_window_separately(ranged):
    # The range bound is measured against the document's own position and the
    # cursor against the position its title would have taken. A document is
    # inside a skipped subtree because of where the document is.
    gap = ranged.missing_meta_stats(key_range=KeyRange(before="m"), meta_name="title", sample=10)
    assert gap.sample == ["a"]

    gap = ranged.missing_meta_stats(
        key_range=KeyRange(after_subtree="m"),
        meta_name="title",
        sample=10,
    )
    assert gap.sample == ["z"]

    # Both kinds at once: the window inside the range.
    gap = ranged.missing_meta_stats(
        key_range=KeyRange(after_subtree="m"),
        window=KeyRange(before_inclusive="z/!title"),
        meta_name="title",
        sample=10,
    )
    assert gap.sample == ["z"]


def test_a_subtree_bound_on_the_root_is_refused(ranged):
    # Everything is beneath the root, so no bound can be drawn around it. The
    # alternative is a bound that quietly matches nothing.
    with pytest.raises(ValueError, match="no subtree bounds"):
        ranged.get_documents(key_range=KeyRange(before=None, after_subtree=""))


def test_sort_subtree_end_bounds_a_subtree_in_sort_order():
    assert keys.sort_form("a") < keys.sort_form("a/!title") < keys.sort_subtree_end("a")
    assert keys.sort_form("a/b/c") < keys.sort_subtree_end("a")
    # The trap `subtree_range` exists for, in sort space: `a` does not contain
    # `a-x`, however much the two look alike.
    assert keys.sort_subtree_end("a") < keys.sort_form("a-x")
    with pytest.raises(ValueError, match="no subtree bounds"):
        keys.sort_subtree_end("")


# -- a key's place in its parent's listing --------------------------------


def test_level_entry_describes_a_stored_key(ranged):
    entry = ranged.level_entry("m")
    assert (entry.kind, entry.size) == ("document", 1)
    assert ranged.level_entry("m/!title").kind == "metadata"


def test_level_entry_describes_a_key_that_only_has_something_below_it(store):
    store.store_document("a/b", "body")
    entry = store.level_entry("a")
    assert (entry.kind, entry.size) == ("implicit", None)


def test_level_entry_sees_a_key_that_holds_only_metadata(store):
    # The corner a cheaper pair of questions gets wrong: metadata sits *at* a
    # key, so this key has no document and no descendants and still appears in
    # its parent's listing.
    store.store_document("a/!title", "T")
    assert store.level_entry("a").kind == "implicit"
    assert store.exists("a") is False
    assert store.descendant_count("a") == 0


def test_level_entry_is_none_for_a_key_the_store_does_not_hold(ranged):
    assert ranged.level_entry("nothing") is None
    assert ranged.level_entry("m/x/deeper") is None


def test_level_entry_refuses_the_root(ranged):
    with pytest.raises(ValueError, match="not a child of anything"):
        ranged.level_entry("")


def test_level_entry_agrees_with_the_listing_it_describes(ranged):
    ranged.store_document("implied/below", "b")
    level = {entry.key: entry for entry in ranged.list_keys().items}
    for key in ["a", "m", "z", "implied"]:
        assert ranged.level_entry(key) == level[key], key


# -- concurrency ---------------------------------------------------------
#
# The server runs its sync tool handlers in a worker pool, so two tool calls
# issued in one batch reach the store from two threads at once. A single shared
# connection made that corrupt: SQLite raised `bad parameter or other API
# misuse`, and about a third of the failures were empty pages that raised
# nothing at all. Every other test here is single-threaded and so could not see
# it. See `project/reference/planned/concurrency`.


def test_concurrent_reads_are_neither_corrupt_nor_silently_empty(store):
    for i in range(20):
        store.store_document(f"a/doc{i}", "body", title=f"title {i}")

    def read(_):
        for _ in range(200):
            page = store.get_documents(BoundedSubtree("a"), meta_name=["title"])
            # The loud failure was an exception; the quiet one was a page
            # reporting a total it did not carry, with no cursor to say why.
            assert page.returned == len(page.items)
            assert page.total == 20
            assert page.items

    in_threads(read)


def test_concurrent_writes_do_not_hand_out_a_number_twice(store):
    """`?` allocation reads the highest number in use, then writes past it.

    Across connections that is only safe because the write takes the lock up
    front -- `BEGIN IMMEDIATE` -- and because a writer waits its turn instead
    of failing on the spot, which is what `BUSY_TIMEOUT_MS` buys.
    """
    allocated = []
    lock = threading.Lock()

    def allocate(_):
        mine = [store.store_document("c/?/doc", "x", title="a") for _ in range(20)]
        with lock:
            allocated.extend(mine)

    in_threads(allocate, threads=5)

    assert len(allocated) == 100
    assert len(set(allocated)) == 100


# -- the root ------------------------------------------------------------


def test_a_document_can_be_stored_at_the_root(store):
    store.store_document("", "# This store\n\nWhat it holds.")
    assert store.retrieve_document("").content.startswith("# This store")
    assert store.exists("")


@pytest.mark.parametrize("written", ["", "/", "///"])
def test_every_spelling_of_the_root_reaches_one_document(store, written):
    store.store_document(written, "body")
    assert store.retrieve_document("").content == "body"
    assert store.list_keys().total == 0  # nothing lists as a child of itself


def test_a_title_on_the_root_is_stored_as_its_own_metadata(store):
    store.store_document("", "body", title="This store")
    assert store.retrieve_document("!title").content == "This store"


def test_the_root_is_not_a_child_of_itself(populated):
    populated.store_document("", "body")
    keys_at_top = [entry.key for entry in populated.list_keys().items]
    assert "" not in keys_at_top
    assert keys_at_top == ["context", "project"]


def test_the_root_is_not_counted_into_the_top_level(populated):
    before = populated.list_keys()
    populated.store_document("", "body of the root")
    after = populated.list_keys()
    # The row exists and is readable; what it must not do is appear in, or be
    # counted into, the level it is the parent of.
    assert after.total == before.total
    assert after.total_chars == before.total_chars


def test_root_metadata_does_list_below_the_root(populated):
    populated.store_document("", "body", title="This store")
    keys_at_top = [entry.key for entry in populated.list_keys().items]
    # Metadata on the root is a child of the root, unlike the root itself, and
    # sorts ahead of the subkeys the way any document's metadata does.
    assert keys_at_top == ["!title", "context", "project"]


def test_the_root_document_is_read_by_a_subtree_read(populated):
    populated.store_document("", "body")
    found = [excerpt.key for excerpt in populated.get_documents().items]
    assert "" in found
    assert found[0] == ""  # and it sorts first


def test_none_and_the_root_name_the_same_scope(populated):
    populated.store_document("", "body")
    assert [e.key for e in populated.list_keys(None).items] == [
        e.key for e in populated.list_keys("").items
    ]
    assert (
        populated.get_documents(BoundedSubtree(None)).total
        == populated.get_documents(BoundedSubtree("")).total
    )


def test_depth_is_counted_from_the_root(populated):
    populated.store_document("", "root body")
    populated.store_document("readme", "top level body")
    # The root is depth 0, so `depth=0` names it and nothing else. The segment
    # count SQLite computes is delimiters plus one, which would make the root
    # depth 1 and exclude it from the one selection that is only about it.
    assert [e.key for e in populated.get_documents(BoundedSubtree("", depth=0)).items] == [""]
    found = populated.get_documents(BoundedSubtree("", depth=1)).items
    assert [e.key for e in found] == ["", "readme"]


def test_descendant_count_from_the_root_counts_everything_below_it(populated):
    before = populated.descendant_count("")
    populated.store_document("", "body", title="This store")
    # Strictly below, and metadata is never a descendant of the key it sits on
    # -- true of the root exactly as it is of any other key, so neither of the
    # two rows just written is counted.
    assert populated.descendant_count("") == before
    assert before == populated.descendant_count("context") + populated.descendant_count("project")


def test_deleting_the_root_takes_its_metadata_and_leaves_the_rest(populated):
    populated.store_document("", "body", title="This store")
    removed = populated.delete("")
    assert sorted(removed) == ["", "!title"]
    assert populated.list_keys().total == 2  # context and project, untouched


def test_recursive_delete_at_the_root_empties_the_store(populated):
    populated.store_document("", "body")
    removed = populated.delete("", recursive=True)
    assert "" in removed
    assert populated.get_documents().total == 0


def test_a_survey_by_title_sees_the_stores_own_title(populated):
    populated.store_document("", "body", title="This store")
    survey = populated.get_documents(meta_name=["title"])
    assert "!title" in [excerpt.key for excerpt in survey.items]


def test_a_root_document_without_a_title_is_reported_as_missing_one(populated):
    populated.store_document("", "body")
    missing = populated.keys_missing_meta(meta_name="title")
    assert "" in missing.items


def test_the_roots_missing_title_is_measured_where_it_would_have_sorted(populated):
    # The root is the one document whose metadata is *not* its sort form plus a
    # suffix: it contributes no segment, so `!title` is a first segment rather
    # than one joined onto a previous. Concatenating anyway still tiles, so
    # nothing would be double counted -- it would just be filed under a later
    # window than the one its title would really have sorted in.
    populated.store_document("", "body")
    first = populated.missing_meta_stats(
        window=KeyRange(before_inclusive="context/a1b2/design/!title"),
        meta_name="title",
        sample=5,
    )
    later = populated.missing_meta_stats(
        window=KeyRange(after="context/a1b2/design/!title"),
        meta_name="title",
        sample=5,
    )
    assert "" in first.sample
    assert "" not in later.sample


def test_autonumbering_allocates_at_the_top_level(store):
    assert store.store_document("?", "first") == "1"
    assert store.store_document("?", "second") == "2"


def test_a_title_on_the_root_with_no_document_is_named_in_a_check(file_store, tmp_path):
    from outrage import maintenance

    # Legal, and easy to reach: titling a file_store is not the same as writing a
    # document at its root. The report has to be able to name the root, or the
    # detail line carries a blank where a key should be.
    file_store.store_document("!title", "This file_store")
    report = maintenance.check(file_store)
    notes = [p for p in report.problems if p.code == maintenance.METADATA_WITHOUT_DOCUMENT]
    assert notes and notes[0].detail == "/"


# -- a metadata namespace ------------------------------------------------


@pytest.fixture
def namespaced(store):
    """A document carrying a metadata namespace with documents inside it.

    The shape the whole section is about: ``a`` carries ``changelog``, the
    changelog describes itself, and it holds numbered notes which carry titles
    of their own.
    """
    store.store_document("a", "the document", title="A")
    store.store_document("a/!changelog", "what this log is", title="Changelog")
    store.store_document("a/!changelog/22", "the twenty-second note", title="Note 22")
    store.store_document("a/b", "a child document", title="B")
    return store


def test_a_metadata_namespace_holds_documents_of_its_own(namespaced):
    assert namespaced.retrieve_document("a/!changelog/22").content == "the twenty-second note"
    assert namespaced.retrieve_document("a/!changelog").content == "what this log is"


def test_a_metadata_namespace_lists_like_any_other_level(namespaced):
    level = namespaced.list_keys("a/!changelog")
    assert [(entry.key, entry.kind) for entry in level.items] == [
        ("a/!changelog/!title", "metadata"),
        ("a/!changelog/22", "document"),
    ]


def test_a_survey_does_not_descend_into_a_metadata_namespace(namespaced):
    # The default John chose: from `a`, the changelog's own entries are not
    # `a`'s titles, and the notes inside it are not `a`'s documents. Reaching
    # them is a matter of *scope*, not of depth.
    titles = namespaced.get_documents(meta_name=["title"])
    assert [entry.key for entry in titles.items] == ["a/!title", "a/b/!title"]

    documents = namespaced.get_documents()
    assert [entry.key for entry in documents.items] == ["a", "a/b"]


def test_a_survey_scoped_inside_a_metadata_namespace_reads_it(namespaced):
    # Scoped there, the same two questions are asked *relative to the scope*:
    # `22` is a document and its `!title` is a title. Every row in this subtree
    # carries `changelog`, so the stored split cannot answer either one.
    scoped = BoundedSubtree("a/!changelog")
    assert [entry.key for entry in namespaced.get_documents(scoped).items] == [
        "a/!changelog",
        "a/!changelog/22",
    ]
    assert [entry.key for entry in namespaced.get_documents(scoped, meta_name=["title"]).items] == [
        "a/!changelog/!title",
        "a/!changelog/22/!title",
    ]


def test_keys_missing_meta_reads_a_metadata_namespace_from_inside_it(namespaced):
    namespaced.store_document("a/!changelog/23", "no title on this one")
    assert namespaced.keys_missing_meta(BoundedSubtree("a/!changelog")).items == ["a/!changelog/23"]
    # And from outside it, the notes are not documents to be missing a title.
    assert namespaced.keys_missing_meta().items == []


def test_nothing_below_a_metadata_segment_adds_depth(namespaced):
    # Levels and depth are decoupled: the namespace is reached by a level walk
    # and never by asking for more depth. So a depth filter that reaches `a`
    # reaches its whole metadata subtree, which is the cost that was accepted.
    shallow = namespaced.get_documents(BoundedSubtree("a", depth=0), meta_name=["title"])
    assert [entry.key for entry in shallow.items] == ["a/!title"]

    inside = namespaced.get_documents(BoundedSubtree("a/!changelog", depth=0))
    assert [entry.key for entry in inside.items] == ["a/!changelog", "a/!changelog/22"]


def test_a_number_is_allocated_inside_a_metadata_namespace(namespaced):
    # `document/!changelog/?` allocating sequential notes is the use case the
    # container reading exists for. A metadata *name* is still chosen rather
    # than counted -- what is numbered here is an ordinary child.
    assert namespaced.store_document("a/!changelog/?", "the next note") == "a/!changelog/23"


def test_last_child_skips_metadata_at_whatever_level_it_stands(namespaced):
    # `?last` stands where an ordinary segment goes, so inside the changelog it
    # names the newest note and never the changelog's own title.
    assert namespaced.last_child("a/!changelog") == "22"
    assert namespaced.last_child("a") == "b"


def test_a_metadata_namespace_holding_only_documents_reads_as_a_container(store):
    store.store_document("a/!changelog/22", "a note")
    with raises_rendered(KeyNotFoundError, "lie beneath it"):
        store.retrieve_document("a/!changelog")


def test_descendant_count_of_a_metadata_namespace_counts_its_contents(namespaced):
    # What a plain delete would keep. The changelog's own title goes with it,
    # so it is not counted; the note and the note's title stay, so they are.
    assert namespaced.descendant_count("a/!changelog") == 2
    # And from `a`, the whole metadata unit goes, leaving only the child.
    assert namespaced.descendant_count("a") == 2


def test_whole_subtree_counts_the_key_s_own_metadata_and_the_default_does_not(namespaced):
    # Two questions, and a caller has to say which. The default is what a plain
    # delete would *keep*; `whole_subtree` is what a recursive one takes, which
    # is also what `bulk.walk` reports -- so a preview counting with the first
    # and walking the second is short by the unit, and goes negative once it
    # reaches past the ordinary children.
    assert namespaced.descendant_count("a") == 2
    assert namespaced.descendant_count("a", whole_subtree=True) == 7

    # The same distinction inside a namespace: the changelog's own title is the
    # unit here, and nothing else moves.
    assert namespaced.descendant_count("a/!changelog") == 2
    assert namespaced.descendant_count("a/!changelog", whole_subtree=True) == 3


def test_whole_subtree_is_what_a_recursive_delete_takes(namespaced):
    # Stated as the identity rather than as two numbers: whatever the corpus,
    # a recursive delete returns the key itself plus everything this counts.
    counted = namespaced.descendant_count("a", whole_subtree=True)
    assert len(namespaced.delete("a", recursive=True)) == counted + 1


def test_a_plain_delete_of_a_metadata_namespace_keeps_what_is_inside_it(namespaced):
    # The same rule as a document: the key and its own metadata are one unit
    # and go together, and everything else below waits for `recursive`. That
    # is what `descendant_count` reports, and what a front end refuses on.
    assert namespaced.delete("a/!changelog") == ["a/!changelog", "a/!changelog/!title"]
    assert [entry.key for entry in namespaced.get_documents().items] == ["a", "a/b"]
    assert namespaced.descendant_count("a/!changelog") == 2

    assert namespaced.delete("a/!changelog", recursive=True) == [
        "a/!changelog/22",
        "a/!changelog/22/!title",
    ]


def test_deleting_a_document_takes_its_whole_metadata_subtree(namespaced):
    # One unit: what a delete leaves behind is what `descendant_count` reports.
    assert namespaced.delete("a") == [
        "a",
        "a/!changelog",
        "a/!changelog/!title",
        "a/!changelog/22",
        "a/!changelog/22/!title",
        "a/!title",
    ]
    assert [entry.key for entry in namespaced.get_documents().items] == ["a/b"]


# -- the interface -------------------------------------------------------
#
# `Store` is abstract, and these are the two things that fact has to buy: that
# a backend cannot half-implement it and be instantiated anyway, and that every
# operation a caller reaches for is named on the interface rather than only on
# the backend that happens to be in front of them.


def test_the_store_interface_cannot_be_instantiated():
    with pytest.raises(TypeError, match="abstract"):
        Store()


def test_every_operation_a_caller_uses_is_declared_abstract():
    """A method a backend may silently not implement is not a contract.

    Named one by one rather than derived from the class, so that dropping
    ``@abstractmethod`` from one of them fails here instead of quietly making
    it optional for the next backend.
    """
    assert Store.__abstractmethods__ == frozenset(
        {
            "store_document",
            "delete",
            "descendant_count",
            "exists",
            "level_entry",
            "retrieve_document",
            "list_keys",
            "get_documents",
            "missing_meta_stats",
            "keys_missing_meta",
            "close",
        }
    )
    # Maintenance, which needs a file to answer and so is `FileStore`'s. A
    # backend quietly not implementing these would let a store be reported
    # sound without anything having looked at the storage, which is the answer
    # this codebase keeps refusing.
    assert FileStore.__abstractmethods__ - Store.__abstractmethods__ == frozenset(
        {
            "stored_format_version",
            "audit_rows",
            "check_file",
            "repair",
        }
    )
    # `backup` is the exception, and deliberately: every file store can copy
    # itself by writing its documents into a fresh one, so the base implements
    # it and a backend with a native copy overrides. Left abstract, a new
    # backend would have to write one before it could be backed up at all.
    assert "backup" not in FileStore.__abstractmethods__


def test_validation_normalises_what_a_backend_then_writes():
    """The arguments as they are written, with every refusal already made.

    The shared half of ``store_document``: a backend gets the parsed key, the
    decoded content, a format that is never None, and decoded metadata. Only
    the wildcard is left to it, because which number a ``?`` becomes is read
    from the store inside the transaction that writes it.
    """
    parsed, content, format, title, contents, updated_at = Store._validated(
        "notes/?",
        '"{\\"a\\": 1}"',
        None,
        title='"Numbers"',
        contents='"# Numbers\\n"',
        encoding="json-string",
    )
    assert parsed.has_wildcard
    assert content == '{"a": 1}'
    # Detected after the decode, not before: the JSON *literal* the caller sent
    # is a string, and it is the document inside it that is an object.
    assert format == "json"
    assert title == "Numbers"
    assert contents == "# Numbers\n"
    # None survives: what "now" means is the storage's own answer, and a
    # timestamp settled here would be the moment the arguments were checked
    # rather than the moment the document was written.
    assert updated_at is None


def test_every_backend_validates_by_calling_the_shared_check():
    """A backend that validated differently would be a second namespace.

    Read from the source rather than exercised, because the failure it guards
    against is a backend quietly doing its own checks: that passes every
    behavioural test written against *it*, and diverges only where nobody
    looked. There is one backend today, and this is what a second one has to
    pass on the day it is written.
    """
    stores = 0
    for path in sorted(pathlib.Path(store_module.__file__).parent.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.ClassDef):
                continue
            if not any(
                isinstance(b, ast.Name) and b.id in ("Store", "FileStore") for b in node.bases
            ):
                continue
            # A backend names the file it keeps; ``MountedStore`` is a ``Store``
            # that keeps nothing and validates by delegating to the store it
            # routed to, which is the one honest way to answer this.
            if not any(
                isinstance(item, ast.Assign)
                and any(
                    getattr(target, "id", None) == "default_filename" for target in item.targets
                )
                for item in node.body
            ):
                continue
            for method in node.body:
                if not isinstance(method, ast.FunctionDef) or method.name != "store_document":
                    continue
                stores += 1
                assert any(
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "_validated"
                    for call in ast.walk(method)
                ), f"{path.name}: {node.name}.store_document validates on its own"
    assert stores, "no backend found to check"


def test_a_store_named_no_file_takes_its_own_backend_s_default(tmp_path):
    """None means *this* backend's store file, not the package's default.

    The two agree while there is one backend, and are still asked separately:
    a store constructed directly names its own class, so it can never be
    opened under a file name some other backend chose. Every front end asks
    :func:`~outrage.store.default_store_file` instead, which is what keeps the
    command line and the server from naming a backend to print a default.
    """
    s = SqliteStore(tmp_path / ".outrage")
    try:
        assert s.path.name == SqliteStore.default_filename
    finally:
        s.close()
    assert store_module.default_store_file() == SqliteStore.default_filename


def test_what_the_interface_settles_is_settled_once(tmp_path):
    """Where the file is, and the directory around it, come from the base.

    A backend that re-answered either would be free to disagree with
    ``store_file`` about what ``--dir`` and a mount spec mean, which is the one
    rule ``context/24/decisions`` exists to keep in one place. The base is
    :class:`FileStore` rather than :class:`Store` since 2026-08-27: a store
    kept in no file settles none of this, and a mount table is the one.
    """
    s = SqliteStore(tmp_path / ".outrage", filename="ref.sqlite")
    try:
        assert s.directory == tmp_path / ".outrage"
        assert s.path == tmp_path / ".outrage" / "ref.sqlite"
        assert type(s).__init__ is not Store.__init__
        assert s.backup_path.__func__ is FileStore.backup_path
    finally:
        s.close()
