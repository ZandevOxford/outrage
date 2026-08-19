import pytest

from rage import keys
from rage.keys import InvalidKeyError


@pytest.mark.parametrize(
    ("key", "doc_key", "meta_name", "parent"),
    [
        ("context", "context", None, ""),
        ("context/a1b2", "context/a1b2", None, "context"),
        ("context/a1b2/design", "context/a1b2/design", None, "context/a1b2"),
        ("context/a1b2/design/!title", "context/a1b2/design", "title", "context/a1b2/design"),
        ("context/!title", "context", "title", "context"),
        (
            "project/reference/implementation",
            "project/reference/implementation",
            None,
            "project/reference",
        ),
        ("a_b-c/d9/!x_1", "a_b-c/d9", "x_1", "a_b-c/d9"),
    ],
)
def test_parse_derives_columns(key, doc_key, meta_name, parent):
    parsed = keys.parse(key)
    assert parsed.key == key
    assert parsed.doc_key == doc_key
    assert parsed.meta_name == meta_name
    assert parsed.parent == parent
    assert parsed.is_metadata == (meta_name is not None)
    assert not parsed.has_wildcard


@pytest.mark.parametrize(
    "key",
    ["notes/src/myfile.py", "notes/README.md", "a.b", "v1.2.3/notes"],
)
def test_periods_are_ordinary_segment_characters(key):
    # The point of the slash delimiter: a key can mirror a path.
    assert keys.is_valid(key)
    assert keys.parse(key).doc_key == key


def test_a_filename_like_key_nests_under_its_directory():
    parsed = keys.parse("notes/src/myfile.py")
    assert parsed.parent == "notes/src"
    assert keys.ancestors("notes/src/myfile.py") == ["notes", "notes/src"]


@pytest.mark.parametrize(
    "key",
    [
        "",
        "/",
        ":",
        ":title",
        "/context",
        "context/",
        "context//a1b2",
        "context:",
        "context/!title:extra",
        "context/!sub/title",   # a ! segment may only come last
        "context/!a/!b",        # nor may there be two of them
        "context/!",            # nor one with no name
        "!title",               # nor metadata with no document above it
        "context/a1b2:title",   # the pre schema 4 spelling
        "context/a1b2:",
        "con text",
        "context/a1b2!",
        "café",
        "context\n",
        "a/./b",
        "a/../b",
        "a:.",
        "a/?",
    ],
)
def test_parse_rejects_invalid_keys(key):
    with pytest.raises(InvalidKeyError):
        keys.parse(key)


def test_rejecting_a_segment_says_what_a_segment_may_contain():
    with pytest.raises(InvalidKeyError, match=r"A-Z a-z 0-9 _ \. -"):
        keys.parse("context/1/notes on the build")


def test_parse_rejects_non_strings():
    with pytest.raises(InvalidKeyError):
        keys.parse(None)


def test_is_valid():
    assert keys.is_valid("a/b/!c")
    assert not keys.is_valid("a//b")


def test_metadata_may_attach_to_an_implicit_key():
    # `context` need not have content of its own for `context/!title` to be legal.
    assert keys.parse("context/!title").parent == "context"


# -- wildcards -----------------------------------------------------------


@pytest.mark.parametrize(
    ("key", "wildcard_parent"),
    [("?", ""), ("tmp/?", "tmp"), ("context/?/design", "context"), ("tmp/?/!title", "tmp")],
)
def test_wildcard_parent_is_the_key_enclosing_the_wildcard(key, wildcard_parent):
    parsed = keys.parse(key, allow_wildcard=True)
    assert parsed.has_wildcard
    assert parsed.wildcard_parent == wildcard_parent


def test_wildcard_is_rejected_unless_allowed():
    # Reads and deletes parse without it, so `?` can never read as a pattern.
    with pytest.raises(InvalidKeyError, match="only when storing"):
        keys.parse("tmp/?")


@pytest.mark.parametrize("key", ["tmp/?/?", "tmp/a?b", "tmp/?x", "tmp/x:?"])
def test_invalid_wildcards(key):
    with pytest.raises(InvalidKeyError):
        keys.parse(key, allow_wildcard=True)


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("tmp/?", "tmp/7"),
        ("context/?/design", "context/7/design"),
        ("tmp/?/!title", "tmp/7/!title"),
        ("?", "7"),
    ],
)
def test_substitute_wildcard(key, expected):
    assert keys.substitute_wildcard(key, "7") == expected


def test_substitute_wildcard_needs_a_wildcard():
    with pytest.raises(InvalidKeyError):
        keys.substitute_wildcard("tmp/a", "7")


# -- derived values ------------------------------------------------------


def test_ancestors():
    assert keys.ancestors("context") == []
    assert keys.ancestors("context/a1b2/design") == ["context", "context/a1b2"]
    assert keys.ancestors("context/a1b2/design/!title") == [
        "context",
        "context/a1b2",
        "context/a1b2/design",
    ]


def test_depth_ignores_the_metadata_suffix():
    assert keys.depth("context") == 1
    assert keys.depth("context/a1b2") == 2
    assert keys.depth("context/a1b2/!title") == 2
    assert keys.depth("notes/src/myfile.py") == 3


def test_subtree_range_covers_the_whole_subtree():
    lo, hi = keys.subtree_range("a/b")
    assert lo <= "a/b/c" < hi
    assert lo <= "a/b/c/d/e" < hi


@pytest.mark.parametrize(
    "other",
    ["a/beta", "a/b_c", "a/b-c", "a/b.c", "a/b0", "a/b", "a/c", "a", "a-b/c"],
)
def test_subtree_range_excludes_prefix_collisions(other):
    lo, hi = keys.subtree_range("a/b")
    assert not (lo <= other < hi)


def test_subtree_bounds_are_adjacent_code_points():
    # Nothing can sort between them but the subtree itself, whatever a segment
    # is allowed to contain.
    assert ord(keys._AFTER_DELIMITER) == ord(keys.DELIMITER) + 1


def test_subtree_range_of_metadata_key_uses_the_document_key():
    assert keys.subtree_range("a/b/!title") == keys.subtree_range("a/b")


# -- numeric segments ----------------------------------------------------


def test_a_numeric_segment_loses_its_leading_zeros():
    assert keys.parse("context/007/task").key == "context/7/task"
    assert keys.parse("context/007/task").doc_key == "context/7/task"
    assert keys.parse("context/007/task").parent == "context/7"


def test_zero_survives_being_normalised():
    assert keys.parse("a/000").key == "a/0"
    assert keys.normalise_segment("0") == "0"


def test_only_wholly_numeric_segments_are_touched():
    for segment in ("0x", "x0", "v01", "1.2", "01-a"):
        assert keys.normalise_segment(segment) == segment


def test_a_numeric_metadata_name_normalises_too():
    # Metadata names are segments and are ordered like them, so treating them
    # differently would make '!01' and '!1' two names where '/01' and '/1' are
    # one key.
    assert keys.parse("a/!007").key == "a/!7"
    assert keys.parse("a/!007").meta_name == "7"


def test_sort_form_orders_numbers_as_numbers():
    unordered = ["a/10", "a/2", "a/1", "a/20", "a/3"]
    assert sorted(unordered, key=keys.sort_form) == ["a/1", "a/2", "a/3", "a/10", "a/20"]


def test_sort_form_leaves_words_alone_and_keeps_depth_apart():
    assert sorted(["a/b/1", "a/2", "a/beta"], key=keys.sort_form) == ["a/2", "a/b/1", "a/beta"]


def test_sort_form_is_not_a_key_the_caller_ever_sees():
    # It exists only for ORDER BY. Anything handed back is the normalised key.
    assert keys.sort_form("a/1") != "a/1"
    assert keys.parse(keys.sort_form("a/1")).key == "a/1"


def test_the_old_metadata_suffix_is_refused_by_name():
    # Every stored key and every line of prose used `:` until schema 4, so the
    # useful refusal is the one that says what to write instead. Accepting it
    # quietly would be worse: `a:title` would name a document beside `a`.
    with pytest.raises(InvalidKeyError) as raised:
        keys.parse("context/5/state:title")
    assert "context/5/state/!title" in str(raised.value)
    assert keys.migrate_legacy("context/5/state:title") == "context/5/state/!title"
    assert keys.migrate_legacy("context/5/state") == "context/5/state"


def test_metadata_sorts_with_its_document_rather_than_after_its_subtree():
    # The reason `!` was chosen. `:` sorted above `/`, so a document's metadata
    # sorted after its whole subtree while the document sorted before it. That
    # split is closed: for a key and its descendants the two orders agree.
    docs = ["a", "a/b", "a/b/c", "ab", "b"]
    by_doc = sorted(docs, key=keys.sort_form)
    by_meta = sorted(docs, key=lambda d: keys.sort_form(f"{d}/!title"))
    assert by_doc == by_meta


def test_the_two_orders_still_part_over_a_segment_char_below_the_delimiter():
    # What `!` does *not* fix, recorded so it is not rediscovered as a bug.
    # `-` and `.` are legal segment characters and sort below `/`, so appending
    # a metadata segment does not preserve order in general: `a` sorts before
    # `a-x`, but `a/!title` sorts after `a-x/!title`.
    assert keys.sort_form("a") < keys.sort_form("a-x")
    assert keys.sort_form("a-x/!title") < keys.sort_form("a/!title")

    # This is why a survey window is still not an interval of document keys,
    # and why Store.missing_meta_stats still measures at a synthesised
    # position. Closing it fully would need the delimiter itself to sort below
    # every segment character, which would reorder documents, not just
    # metadata -- `a/b` would come before `a-x`.
    assert keys.sort_form("a-x") < keys.sort_form("a/b")


def test_a_metadata_segment_sorts_before_any_sibling_document():
    # `!` is below every character a segment may begin with, which is what puts
    # a document's metadata immediately after the document itself.
    assert keys.sort_form("a/!title") < keys.sort_form("a/-b")
    assert keys.sort_form("a/!title") < keys.sort_form("a/.b")
    assert keys.sort_form("a/!title") < keys.sort_form("a/0")
    assert keys.sort_form("a/!2") < keys.sort_form("a/!10")
