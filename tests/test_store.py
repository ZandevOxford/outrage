"""What a store does, asked of the backend that can be written.

Every test here is about the contract :class:`rage.store.Store` states -- keys,
ranges, subtrees, pages, excerpts, the event log -- rather than about how
SQLite keeps any of it. It runs against
:class:`~rage.store_sqlite.SqliteStore`, and half of it writes -- so the
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

import pytest
from conftest import in_threads, raises_rendered

from rage import keys
from rage import store as store_module
from rage.eventlog import EventLog
from rage.keys import InvalidKeyError
from rage.store import (
    BoundedSubtree,
    KeyNotFoundError,
    KeyRange,
    PatternNotFoundError,
    Store,
)
from rage.store_sqlite import SqliteStore


@pytest.fixture
def store(tmp_path):
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
def populated(store):
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
    assert store_module.resolve_directory() == tmp_path / ".rage"

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
        "<html lang=\"en\">",
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


def test_encoding_must_be_known(store):
    with pytest.raises(ValueError, match="encoding"):
        store.store_document("a", '"x"', encoding="base64")


# The three cases below are the ones this encoding exists to catch. Each is a
# way a generated tool call has been seen to arrive damaged, and each must fail
# rather than store something that reads as if it were correct.


def test_json_string_encoding_rejects_trailing_scaffolding(store):
    with pytest.raises(ValueError, match="not a valid JSON string literal"):
        store.store_document("a", '"A summary."</content>\n</invoke>\n', encoding="json-string")

    with pytest.raises(KeyNotFoundError):
        store.retrieve_document("a")


def test_json_string_encoding_rejects_scaffolding_inside_the_quotes(store):
    # Raw newlines are not legal inside a JSON string, which is what catches
    # scaffolding that lands before the closing quote rather than after it.
    with pytest.raises(ValueError, match="not a valid JSON string literal"):
        store.store_document("a", '"A summary.</content>\n</invoke>\n"', encoding="json-string")


def test_json_string_encoding_rejects_unencoded_content(store):
    # A caller that asks for the encoding and then forgets to apply it fails
    # loudly, which is the property prose instructions cannot provide.
    with pytest.raises(ValueError, match="not a valid JSON string literal"):
        store.store_document("a", "A plain unencoded summary.", encoding="json-string")


def test_json_string_encoding_rejects_non_strings(store):
    with pytest.raises(ValueError, match="decoded to dict"):
        store.store_document("a", '{"summary": "A summary."}', encoding="json-string")


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


def test_title_argument_is_rejected_on_a_metadata_key(store):
    with pytest.raises(ValueError, match="cannot attach a title"):
        store.store_document("a/b/!summary", "text", title="Nope")


def test_a_failed_title_write_leaves_no_document_behind(store):
    with pytest.raises(TypeError, match="title must be a string"):
        store.store_document("a/b", "body", title=object())
    with pytest.raises(KeyNotFoundError):
        store.retrieve_document("a/b")


def test_a_key_may_mirror_a_file_path(store):
    store.store_document("notes/src/myfile.py", "Notes about myfile.")
    assert store.retrieve_document("notes/src/myfile.py").content == "Notes about myfile."
    assert [e.key for e in store.list_keys("notes/src").items] == ["notes/src/myfile.py"]


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
    logged.store_document("a/b", "body", title="A title")

    (event,) = [e for e in events(tmp_path) if e["op"] == "store_document"]
    assert event["args"]["content"]["text"] == "body"
    assert event["args"]["title"]["text"] == "A title"
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


def test_backup_holds_what_the_store_holds(populated):
    result = populated.backup()

    assert result.integrity == "ok"
    assert result.documents == 7
    assert result.bytes > 0
    assert documents_in(result.path) == 7


def test_backup_captures_writes_that_are_still_only_in_the_wal(populated, tmp_path):
    """The whole reason this lives in the store rather than in a caller.

    Nothing has been checkpointed, so the .sqlite file on its own is a database
    that opens cleanly and has almost nothing in it. Copying the file is the
    failure being guarded against, so the test states it directly.
    """
    copied = tmp_path / "copied.sqlite"
    copied.write_bytes(populated.path.read_bytes())
    try:
        by_copy = documents_in(copied)
    except sqlite3.DatabaseError:
        by_copy = 0  # Not even a schema yet, which is the same failure, harder.

    result = populated.backup()

    assert by_copy < 7, "a file copy would have been good enough, so this test proves nothing"
    assert documents_in(result.path) == 7


def test_a_backup_is_a_store_that_can_be_opened(populated, tmp_path):
    result = populated.backup()

    restored_dir = tmp_path / "restored"
    restored_dir.mkdir()
    (restored_dir / store_module.default_store_file()).write_bytes(result.path.read_bytes())

    with SqliteStore(restored_dir) as restored:
        assert restored.retrieve_document("context/a1b2/task").content == "Add a delete tool."


def test_backup_defaults_to_a_timestamped_name_below_the_store(populated):
    result = populated.backup()

    assert result.path.parent == (populated.directory / store_module.BACKUP_DIR_NAME).resolve()
    assert result.path.name.startswith("store-")
    assert result.path.suffix == ".sqlite"


def test_a_destination_directory_gets_the_default_name(populated, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    result = populated.backup(elsewhere)

    assert result.path.parent == elsewhere.resolve()
    assert result.path.name.startswith("store-")


def test_a_named_destination_is_used_as_given(populated, tmp_path):
    result = populated.backup(tmp_path / "snapshots" / "monday.sqlite")

    assert result.path == (tmp_path / "snapshots" / "monday.sqlite").resolve()


def test_an_existing_destination_is_refused(populated, tmp_path):
    target = tmp_path / "taken.sqlite"
    target.write_text("not a database")

    with raises_rendered(store_module.BackupError, "already exists"):
        populated.backup(target)

    assert target.read_text() == "not a database"


def test_an_existing_destination_can_be_replaced_on_purpose(populated, tmp_path):
    target = tmp_path / "taken.sqlite"
    target.write_text("not a database")

    result = populated.backup(target, overwrite=True)

    assert documents_in(result.path) == 7


def test_the_store_itself_is_refused_as_a_destination(populated):
    with raises_rendered(store_module.BackupError, "the store itself"):
        populated.backup(populated.path)

    # The refusal has to come before anything is unlinked, or the check that
    # protects the store is what destroys it.
    assert populated.retrieve_document("context/a1b2/task").content == "Add a delete tool."


def test_a_short_backup_is_refused_rather_than_returned(populated, monkeypatch):
    """The count is the only check that catches a copy which opens cleanly."""
    monkeypatch.setattr(
        SqliteStore,
        "_verify_backup",
        lambda self, target: (_ for _ in ()).throw(
            store_module.BackupError("backup-short", target=str(target), found=0, expected=7)
        ),
    )

    with raises_rendered(store_module.BackupError, "holds 0 documents"):
        populated.backup()


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


def test_a_document_and_its_metadata_survive_the_rebuild_in_order(store):
    # The property the whole sort form exists for, read back through the store
    # rather than asserted on the encoding.
    for key in ["a", "a-x", "a/b"]:
        store.store_document(key, "body", title="T")

    listed = [
        r["key"]
        for r in store.connection.execute("SELECT key FROM documents ORDER BY sort_key")
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


def test_a_title_on_the_root_with_no_document_is_named_in_a_check(store, tmp_path):
    from rage import maintenance

    # Legal, and easy to reach: titling a store is not the same as writing a
    # document at its root. The report has to be able to name the root, or the
    # detail line carries a blank where a key should be.
    store.store_document("!title", "This store")
    report = maintenance.check(store)
    notes = [p for p in report.problems if p.summary == "some metadata has no document"]
    assert notes and notes[0].detail == "/"


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
            "backup",
            "close",
        }
    )


def test_validation_normalises_what_a_backend_then_writes():
    """The arguments as they are written, with every refusal already made.

    The shared half of ``store_document``: a backend gets the parsed key, the
    decoded content, a format that is never None, and the decoded title. Only
    the wildcard is left to it, because which number a ``?`` becomes is read
    from the store inside the transaction that writes it.
    """
    parsed, content, format, title = Store._validated(
        "notes/?", '"{\\"a\\": 1}"', None, title='"Numbers"', encoding="json-string"
    )
    assert parsed.has_wildcard
    assert content == '{"a": 1}'
    # Detected after the decode, not before: the JSON *literal* the caller sent
    # is a string, and it is the document inside it that is an object.
    assert format == "json"
    assert title == "Numbers"


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
            if not any(isinstance(b, ast.Name) and b.id == "Store" for b in node.bases):
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
    :func:`~rage.store.default_store_file` instead, which is what keeps the
    command line and the server from naming a backend to print a default.
    """
    s = SqliteStore(tmp_path / ".rage")
    try:
        assert s.path.name == SqliteStore.default_filename
    finally:
        s.close()
    assert store_module.default_store_file() == SqliteStore.default_filename


def test_what_the_interface_settles_is_settled_once(tmp_path):
    """Where the file is, and the directory around it, come from the base.

    A backend that re-answered either would be free to disagree with
    ``store_file`` about what ``--dir`` and a mount spec mean, which is the one
    rule ``context/24/decisions`` exists to keep in one place.
    """
    s = SqliteStore(tmp_path / ".rage", filename="ref.sqlite")
    try:
        assert s.directory == tmp_path / ".rage"
        assert s.path == tmp_path / ".rage" / "ref.sqlite"
        assert type(s).__init__ is not Store.__init__
        assert s.backup_path.__func__ is Store.backup_path
    finally:
        s.close()
