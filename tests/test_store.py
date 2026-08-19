import json
import sqlite3
from pathlib import Path

import pytest

from rage import keys
from rage import store as store_module
from rage.eventlog import EventLog
from rage.keys import InvalidKeyError
from rage.store import KeyNotFoundError, PatternNotFoundError, Store


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path / "store") as s:
        yield s


@pytest.fixture
def logged(tmp_path):
    """A store that records what it is asked to do."""
    log = EventLog(tmp_path / "log.jsonl")
    with Store(tmp_path / "store", log=log) as s:
        yield s
    log.close()


def events(tmp_path) -> list[dict]:
    return [json.loads(line) for line in (tmp_path / "log.jsonl").read_text().splitlines()]


@pytest.fixture
def populated(store):
    store.store_document("context/a1b2/design", "# Store schema\n\nBody.")
    store.store_document("context/a1b2/design:title", "Store schema")
    store.store_document("context/a1b2/task", "Add a delete tool.")
    store.store_document("context/a1b2/task:title", "Delete tool")
    store.store_document("context/c3d4/design", "# Skill wording")
    store.store_document("context/c3d4/design:title", "Skill wording")
    store.store_document("project/reference/implementation", "Notes.")
    return store


# -- setup ---------------------------------------------------------------


def test_creates_directory_and_database(tmp_path):
    directory = tmp_path / "nested" / ".rage"
    with Store(directory) as s:
        assert s.path == directory / "store.sqlite"
    assert (directory / "store.sqlite").exists()


def test_reopening_keeps_content(tmp_path):
    with Store(tmp_path) as s:
        s.store_document("a", "hello")
    with Store(tmp_path) as s:
        assert s.retrieve_document("a").content == "hello"


def test_resolve_directory_prefers_explicit_then_env_then_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(store_module.ENV_DIR, raising=False)
    assert store_module.resolve_directory() == tmp_path / ".rage"

    monkeypatch.setenv(store_module.ENV_DIR, str(tmp_path / "from-env"))
    assert store_module.resolve_directory() == tmp_path / "from-env"
    assert store_module.resolve_directory(tmp_path / "explicit") == tmp_path / "explicit"


def test_rejects_a_newer_schema(tmp_path):
    with Store(tmp_path) as s:
        s._conn.execute("PRAGMA user_version=999")
        s._conn.commit()
    with pytest.raises(RuntimeError, match="newer version"):
        Store(tmp_path)


#: The table as it stood before ``sort_key`` was added. Spelled out rather than
#: taken from ``store._SCHEMA``, which is the *current* schema: building an old
#: store out of the new definition tests the migration against a database that
#: never existed.
_SCHEMA_BEFORE_SORT_KEY = """
CREATE TABLE documents (
  key        TEXT PRIMARY KEY,
  doc_key    TEXT NOT NULL,
  meta_name  TEXT,
  parent     TEXT NOT NULL,
  content    TEXT NOT NULL,
  format     TEXT,
  updated_at TEXT NOT NULL
);
"""


def an_old_store(directory: Path, version: int, rows: list[tuple]) -> None:
    """A store at ``version``, written the way that version wrote them."""
    directory.mkdir(exist_ok=True)
    conn = sqlite3.connect(directory / "store.sqlite")
    conn.executescript(_SCHEMA_BEFORE_SORT_KEY)
    conn.executemany(
        "INSERT INTO documents (key, doc_key, meta_name, parent, content, format, updated_at)"
        " VALUES (?, ?, ?, ?, ?, 'markdown', 'then')",
        rows,
    )
    conn.execute(f"PRAGMA user_version={version}")
    conn.commit()
    conn.close()


def test_migrates_period_delimited_keys_to_slashes(tmp_path):
    """A schema 1 store was written before the delimiter changed."""
    directory = tmp_path / ".rage"
    directory.mkdir()
    conn = sqlite3.connect(directory / "store.sqlite")
    conn.executescript(_SCHEMA_BEFORE_SORT_KEY)
    conn.executemany(
        "INSERT INTO documents (key, doc_key, meta_name, parent, content, format, updated_at)"
        " VALUES (?, ?, ?, ?, ?, 'markdown', 'then')",
        [
            ("context.a1b2.design", "context.a1b2.design", None, "context.a1b2", "Body."),
            (
                "context.a1b2.design:title",
                "context.a1b2.design",
                "title",
                "context.a1b2.design",
                "Store schema",
            ),
        ],
    )
    conn.execute("PRAGMA user_version=1")
    conn.commit()
    conn.close()

    with Store(directory) as s:
        assert s._conn.execute("PRAGMA user_version").fetchone()[0] == store_module.SCHEMA_VERSION
        assert s.retrieve_document("context/a1b2/design").content == "Body."
        assert [e.key for e in s.list_keys("context/a1b2")] == ["context/a1b2/design"]
        assert [e.key for e in s.get_documents("context", meta_name="title")] == [
            "context/a1b2/design:title"
        ]


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
        store.store_document("a//b", "x")


def test_format_is_detected_but_can_be_overridden(store):
    store.store_document("a/json", '{"title": "x"}')
    store.store_document("a/md", "# Heading")
    store.store_document("a/broken", "{not json")
    store.store_document("a/forced", '{"title": "x"}', format="markdown")

    assert store.retrieve_document("a/json").format == "json"
    assert store.retrieve_document("a/md").format == "markdown"
    assert store.retrieve_document("a/broken").format == "markdown"
    assert store.retrieve_document("a/forced").format == "markdown"


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
    assert store.retrieve_document("a:title").content == 'A "quoted" title'


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
    store.store_document("a/b:title", "Title")
    assert store.retrieve_document("a/b").content == "body"
    assert store.retrieve_document("a/b:title").content == "Title"


def test_metadata_may_attach_to_an_implicit_key(store):
    store.store_document("context:title", "All contexts")
    assert store.retrieve_document("context:title").content == "All contexts"


def test_title_argument_writes_the_metadata_alongside(store):
    store.store_document("a/b", "body", title="A title")
    assert store.retrieve_document("a/b:title").content == "A title"
    assert store.retrieve_document("a/b:title").format == "markdown"


def test_title_argument_follows_an_allocated_number(store):
    written = store.store_document("context/?/design", "body", title="Design")
    assert written == "context/1/design"
    assert store.retrieve_document("context/1/design:title").content == "Design"


def test_title_argument_overwrites_a_previous_title(store):
    store.store_document("a/b", "body", title="First")
    store.store_document("a/b", "body", title="Second")
    assert store.retrieve_document("a/b:title").content == "Second"


def test_title_argument_is_rejected_on_a_metadata_key(store):
    with pytest.raises(ValueError, match="cannot attach a title"):
        store.store_document("a/b:summary", "text", title="Nope")


def test_a_failed_title_write_leaves_no_document_behind(store):
    with pytest.raises(TypeError, match="title must be a string"):
        store.store_document("a/b", "body", title=object())
    with pytest.raises(KeyNotFoundError):
        store.retrieve_document("a/b")


def test_a_key_may_mirror_a_file_path(store):
    store.store_document("notes/src/myfile.py", "Notes about myfile.")
    assert store.retrieve_document("notes/src/myfile.py").content == "Notes about myfile."
    assert [e.key for e in store.list_keys("notes/src")] == ["notes/src/myfile.py"]


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
    assert [e.key for e in store.list_keys("context/2")] == ["context/2/design", "context/2/task"]


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
    store.store_document("tmp/4:title", "x")
    assert store.store_document("tmp/?", "x") == "tmp/5"


def test_wildcard_numbering_is_per_parent(store):
    store.store_document("a/1", "x")
    store.store_document("a/2", "x")
    assert store.store_document("b/?", "x") == "b/1"
    assert store.store_document("a/?", "x") == "a/3"


def test_wildcard_ignores_the_metadata_of_its_own_parent(store):
    store.store_document("tmp:title", "Scratch")
    assert store.store_document("tmp/?", "x") == "tmp/1"


def test_wildcard_on_a_metadata_key(store):
    assert store.store_document("tmp/?:title", "Title") == "tmp/1:title"


def test_wildcard_is_rejected_when_reading_or_deleting(store):
    store.store_document("tmp/1", "x")
    with pytest.raises(InvalidKeyError):
        store.retrieve_document("tmp/?")
    with pytest.raises(InvalidKeyError):
        store.delete("tmp/?")
    with pytest.raises(InvalidKeyError):
        store.get_documents("tmp/?")
    with pytest.raises(InvalidKeyError):
        store.list_keys("tmp/?")


def test_a_failed_write_leaves_no_allocation_behind(store):
    with pytest.raises(ValueError, match="format"):
        store.store_document("tmp/?", "x", format="yaml")
    assert store.store_document("tmp/?", "x") == "tmp/1"


# -- retrieving ----------------------------------------------------------


def test_retrieve_missing_key(store):
    with pytest.raises(KeyNotFoundError, match="nothing is stored at or below"):
        store.retrieve_document("a/b")


def test_retrieve_says_when_a_key_is_a_container(populated):
    with pytest.raises(KeyNotFoundError, match="4 key\\(s\\) lie beneath it"):
        populated.retrieve_document("context/a1b2")


def test_retrieve_missing_metadata_does_not_count_the_documents_descendants(populated):
    with pytest.raises(KeyNotFoundError, match="nothing is stored at or below"):
        populated.retrieve_document("context/a1b2:summary")


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
    assert [e.key for e in populated.list_keys()] == ["context", "project"]
    assert [e.kind for e in populated.list_keys()] == ["implicit", "implicit"]


def test_list_includes_subkeys_and_metadata(populated):
    entries = populated.list_keys("context/a1b2")
    assert [(e.key, e.kind) for e in entries] == [
        ("context/a1b2/design", "document"),
        ("context/a1b2/task", "document"),
    ]

    entries = populated.list_keys("context/a1b2/design")
    assert [(e.key, e.kind) for e in entries] == [("context/a1b2/design:title", "metadata")]


def test_list_reports_sizes_and_timestamps(populated):
    (entry,) = populated.list_keys("context/a1b2/task")
    assert entry.key == "context/a1b2/task:title"
    assert entry.size == len("Delete tool")
    assert entry.format == "markdown"
    assert entry.updated_at


def test_implicit_keys_have_no_content(populated):
    (entry,) = [e for e in populated.list_keys() if e.key == "context"]
    assert entry.kind == "implicit"
    assert entry.size is None
    assert entry.updated_at is None


def test_a_key_with_content_and_children_lists_as_a_document(store):
    store.store_document("a", "body")
    store.store_document("a/b", "child")
    (entry,) = store.list_keys()
    assert (entry.key, entry.kind) == ("a", "document")


def test_list_does_not_confuse_sibling_prefixes(store):
    store.store_document("a/b/c", "x")
    store.store_document("a/beta/d", "y")
    assert [e.key for e in store.list_keys("a")] == ["a/b", "a/beta"]
    assert [e.key for e in store.list_keys("a/b")] == ["a/b/c"]


def test_list_empty(store):
    assert store.list_keys() == []
    assert store.list_keys("nothing/here") == []


# -- bulk reads ----------------------------------------------------------


def test_get_documents_returns_the_subtree(populated):
    keys_found = [e.key for e in populated.get_documents("context")]
    assert keys_found == [
        "context/a1b2/design",
        "context/a1b2/task",
        "context/c3d4/design",
    ]


def test_get_documents_includes_the_key_itself(store):
    store.store_document("a", "body")
    store.store_document("a/b", "child")
    assert [e.key for e in store.get_documents("a")] == ["a", "a/b"]


def test_get_documents_lists_titles_across_a_subtree(populated):
    found = {e.key: e.content for e in populated.get_documents("context", meta_name="title")}
    assert found == {
        "context/a1b2/design:title": "Store schema",
        "context/a1b2/task:title": "Delete tool",
        "context/c3d4/design:title": "Skill wording",
    }


def test_get_documents_accepts_several_metadata_names(store):
    store.store_document("a:title", "T")
    store.store_document("a:summary", "S")
    store.store_document("a:other", "O")
    found = [e.key for e in store.get_documents("a", meta_name=["title", "summary"])]
    assert found == ["a:summary", "a:title"]


def test_get_documents_rejects_an_empty_metadata_list(store):
    with pytest.raises(ValueError, match="meta_name"):
        store.get_documents("a", meta_name=[])


def test_get_documents_everything(populated):
    assert len(populated.get_documents()) == 4


def test_get_documents_depth(populated):
    assert [e.key for e in populated.get_documents("context", depth=0)] == []
    assert [e.key for e in populated.get_documents("context", depth=1)] == []
    assert len(populated.get_documents("context", depth=2)) == 3
    assert [e.key for e in populated.get_documents(depth=1)] == []


def test_keys_missing_meta_names_what_a_title_survey_cannot_see(populated):
    # Only project/reference/implementation was stored without a title.
    assert populated.keys_missing_meta() == ["project/reference/implementation"]
    assert populated.keys_missing_meta("context") == []


def test_keys_missing_meta_follows_the_key_and_depth_filters(populated):
    assert populated.keys_missing_meta("project") == ["project/reference/implementation"]
    assert populated.keys_missing_meta("project", depth=1) == []


def test_keys_missing_meta_takes_several_names(populated):
    populated.store_document("project/reference/implementation:summary", "Notes.")
    assert populated.keys_missing_meta(meta_name=["title", "summary"]) == []
    assert populated.keys_missing_meta(meta_name="title") == ["project/reference/implementation"]


def test_keys_missing_meta_rejects_an_empty_name_list(store):
    with pytest.raises(ValueError, match="must not be an empty sequence"):
        store.keys_missing_meta(meta_name=[])


def test_get_documents_truncates_each_document(store):
    store.store_document("a/b", "x" * 5_000)
    (excerpt,) = store.get_documents("a")
    assert excerpt.returned == store_module.DEFAULT_BULK_MAX_CHARS
    assert excerpt.total == 5_000
    assert excerpt.next_offset == store_module.DEFAULT_BULK_MAX_CHARS


def test_get_documents_does_not_confuse_sibling_prefixes(store):
    store.store_document("a/b/c", "x")
    store.store_document("a/beta/d", "y")
    assert [e.key for e in store.get_documents("a/b")] == ["a/b/c"]


# -- deleting ------------------------------------------------------------


def test_delete_takes_metadata_with_the_document(populated):
    removed = populated.delete("context/a1b2/design")
    assert removed == ["context/a1b2/design", "context/a1b2/design:title"]
    with pytest.raises(KeyNotFoundError):
        populated.retrieve_document("context/a1b2/design:title")


def test_delete_one_metadata_entry(populated):
    assert populated.delete("context/a1b2/design:title") == ["context/a1b2/design:title"]
    assert populated.retrieve_document("context/a1b2/design").content


def test_delete_leaves_descendants_unless_recursive(populated):
    assert populated.delete("context/a1b2") == []
    assert populated.retrieve_document("context/a1b2/design").content


def test_delete_recursive_removes_the_subtree(populated):
    removed = populated.delete("context/a1b2", recursive=True)
    assert removed == [
        "context/a1b2/design",
        "context/a1b2/design:title",
        "context/a1b2/task",
        "context/a1b2/task:title",
    ]
    assert [e.key for e in populated.list_keys("context")] == ["context/c3d4"]


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
    assert [e.key for e in store.list_keys("a")] == ["a/b"]


# -- the event log ---------------------------------------------------------


def test_a_store_without_a_log_writes_nothing(tmp_path):
    with Store(tmp_path / "store") as s:
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
        (lambda s: s.list_keys("a"), "list_keys"),
        (lambda s: s.get_documents("a"), "get_documents"),
        (lambda s: s.keys_missing_meta("a"), "keys_missing_meta"),
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
    assert event["result"]["keys"] == ["a/b", "a/b:title"]


def test_work_done_on_a_caller_s_behalf_is_recorded_too(logged, tmp_path):
    logged.store_document("a/b", "body")
    logged.keys_missing_meta("a")

    # keys_missing_meta reads the subtree to decide what is missing. One call
    # being more than one access is exactly what the log is for.
    assert [e["op"] for e in events(tmp_path)][-2:] == ["get_documents", "keys_missing_meta"]


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
    (restored_dir / store_module.DB_FILENAME).write_bytes(result.path.read_bytes())

    with Store(restored_dir) as restored:
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

    with pytest.raises(store_module.BackupError, match="already exists"):
        populated.backup(target)

    assert target.read_text() == "not a database"


def test_an_existing_destination_can_be_replaced_on_purpose(populated, tmp_path):
    target = tmp_path / "taken.sqlite"
    target.write_text("not a database")

    result = populated.backup(target, overwrite=True)

    assert documents_in(result.path) == 7


def test_the_store_itself_is_refused_as_a_destination(populated):
    with pytest.raises(store_module.BackupError, match="the store itself"):
        populated.backup(populated.path)

    # The refusal has to come before anything is unlinked, or the check that
    # protects the store is what destroys it.
    assert populated.retrieve_document("context/a1b2/task").content == "Add a delete tool."


def test_a_short_backup_is_refused_rather_than_returned(populated, monkeypatch):
    """The count is the only check that catches a copy which opens cleanly."""
    monkeypatch.setattr(
        store_module.Store,
        "_verify_backup",
        lambda self, target: (_ for _ in ()).throw(
            store_module.BackupError("holds 0 documents but the store holds 7")
        ),
    )

    with pytest.raises(store_module.BackupError, match="holds 0 documents"):
        populated.backup()


def test_a_backup_is_logged_with_what_it_wrote(logged, tmp_path):
    logged.store_document("a/b", "body")
    result = logged.backup(tmp_path / "snapshot.sqlite")

    (event,) = [e for e in events(tmp_path) if e["op"] == "backup"]
    assert event["result"]["documents"] == 1
    assert event["result"]["path"] == str(result.path)


# -- numeric segments ----------------------------------------------------


def test_numbered_keys_come_back_in_numeric_order(tmp_path):
    with Store(tmp_path) as s:
        for _ in range(12):
            s.store_document("findings/?", "a finding")

        numbered = [e.key.rsplit("/", 1)[1] for e in s.get_documents("findings")]
        assert numbered == [str(n) for n in range(1, 13)]
        listed = [e.key.rsplit("/", 1)[1] for e in s.list_keys("findings")]
        assert listed == [str(n) for n in range(1, 13)]


def test_a_cursor_parked_on_a_key_does_not_miss_a_later_one(tmp_path):
    """The property pagination will rest on, checked at the store.

    Sorting keys as text puts 'findings/10' behind 'findings/9', so a reader
    resuming after the ninth would never see the tenth.
    """
    with Store(tmp_path) as s:
        for _ in range(9):
            s.store_document("findings/?", "before")
        ninth = s.list_keys("findings")[-1].key
        tenth = s.store_document("findings/?", "after")

        assert (ninth, tenth) == ("findings/9", "findings/10")
        assert keys.sort_form(tenth) > keys.sort_form(ninth)


def test_a_padded_key_names_the_same_document_as_the_unpadded_one(tmp_path):
    with Store(tmp_path) as s:
        written = s.store_document("context/007/task", "the body")

        assert written == "context/7/task"
        assert s.retrieve_document("context/7/task").content == "the body"
        assert s.retrieve_document("context/00007/task").content == "the body"

        s.store_document("context/7/task", "replaced")
        assert s.retrieve_document("context/007/task").content == "replaced"
        assert len(s.get_documents("context")) == 1


def test_allocation_counts_past_a_key_that_was_written_padded(tmp_path):
    with Store(tmp_path) as s:
        s.store_document("context/007", "seventh")
        assert s.store_document("context/?", "next") == "context/8"


def test_migrates_a_store_that_predates_the_sort_key(tmp_path):
    directory = tmp_path / ".rage"
    an_old_store(
        directory,
        version=2,
        rows=[
            ("notes/10", "notes/10", None, "notes", "tenth"),
            ("notes/2", "notes/2", None, "notes", "second"),
            ("notes/03", "notes/03", None, "notes", "third, written padded"),
        ],
    )

    with Store(directory) as s:
        assert s._conn.execute("PRAGMA user_version").fetchone()[0] == store_module.SCHEMA_VERSION
        # notes/03 was rewritten, not just indexed: the key it names has changed.
        assert [e.key for e in s.get_documents("notes")] == ["notes/2", "notes/3", "notes/10"]
        assert s.retrieve_document("notes/3").content == "third, written padded"


def test_a_store_holding_both_spellings_is_refused_rather_than_merged(tmp_path):
    directory = tmp_path / ".rage"
    an_old_store(
        directory,
        version=2,
        rows=[
            ("notes/1", "notes/1", None, "notes", "one spelling"),
            ("notes/01", "notes/01", None, "notes", "the other"),
        ],
    )

    # Nothing can tell which of the two was meant, so neither is thrown away.
    with pytest.raises(RuntimeError, match="one key once leading zeros"):
        Store(directory)


def test_a_migrated_store_has_exactly_the_schema_a_fresh_one_has(tmp_path):
    """Otherwise an older build writes rows a newer one cannot order.

    `ALTER TABLE ADD COLUMN` needs a default for a NOT NULL column, and that
    default outlives the migration: a server still running the previous build
    would insert an empty sort key without complaint, and those rows sort ahead
    of everything. Observed, not hypothetical.
    """
    migrated = tmp_path / "migrated"
    an_old_store(migrated, version=2, rows=[("notes/1", "notes/1", None, "notes", "body")])
    with Store(migrated):
        pass

    with Store(tmp_path / "fresh") as s:
        s.store_document("notes/1", "body")

    def shape(directory):
        conn = sqlite3.connect(directory / "store.sqlite")
        # name, type, notnull and default per column, plus the indexes. Not the
        # DDL text: ALTER TABLE RENAME quotes the table name, which differs
        # without meaning anything, while the column default -- the thing that
        # was actually wrong -- does not show up in a casual reading of it.
        columns = [tuple(row[1:5]) for row in conn.execute("PRAGMA table_info(documents)")]
        indexes = sorted(row[1] for row in conn.execute("PRAGMA index_list(documents)"))
        return columns, indexes

    assert shape(migrated) == shape(tmp_path / "fresh")

    columns, _ = shape(migrated)
    sort_key = [column for column in columns if column[0] == "sort_key"]
    assert sort_key == [("sort_key", "TEXT", 1, None)], "sort_key must be NOT NULL with no default"


def test_the_migration_fills_in_a_sort_key_for_every_row(tmp_path):
    directory = tmp_path / ".rage"
    an_old_store(
        directory,
        version=2,
        rows=[
            ("notes/1", "notes/1", None, "notes", "body"),
            ("notes/1:title", "notes/1", "title", "notes/1", "A title"),
        ],
    )

    with Store(directory) as s:
        empty = s._conn.execute("SELECT count(*) FROM documents WHERE sort_key = ''").fetchone()[0]
        assert empty == 0
