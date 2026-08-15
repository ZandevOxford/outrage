import pytest

from rage import keys
from rage.keys import InvalidKeyError


@pytest.mark.parametrize(
    ("key", "doc_key", "meta_name", "parent"),
    [
        ("context", "context", None, ""),
        ("context.a1b2", "context.a1b2", None, "context"),
        ("context.a1b2.design", "context.a1b2.design", None, "context.a1b2"),
        ("context.a1b2.design:title", "context.a1b2.design", "title", "context.a1b2.design"),
        ("context:title", "context", "title", "context"),
        (
            "project.reference.implementation",
            "project.reference.implementation",
            None,
            "project.reference",
        ),
        ("a_b-c.d9:x_1", "a_b-c.d9", "x_1", "a_b-c.d9"),
    ],
)
def test_parse_derives_columns(key, doc_key, meta_name, parent):
    parsed = keys.parse(key)
    assert parsed.key == key
    assert parsed.doc_key == doc_key
    assert parsed.meta_name == meta_name
    assert parsed.parent == parent
    assert parsed.is_metadata == (meta_name is not None)


@pytest.mark.parametrize(
    "key",
    [
        "",
        ".",
        ":",
        ":title",
        ".context",
        "context.",
        "context..a1b2",
        "context:",
        "context:title:extra",
        "context:sub.title",
        "context.a1b2:",
        "con text",
        "context/a1b2",
        "context.a1b2!",
        "café",
        "context\n",
    ],
)
def test_parse_rejects_invalid_keys(key):
    with pytest.raises(InvalidKeyError):
        keys.parse(key)


def test_parse_rejects_non_strings():
    with pytest.raises(InvalidKeyError):
        keys.parse(None)


def test_is_valid():
    assert keys.is_valid("a.b:c")
    assert not keys.is_valid("a..b")


def test_metadata_may_attach_to_an_implicit_key():
    # `context` need not have content of its own for `context:title` to be legal.
    assert keys.parse("context:title").parent == "context"


def test_ancestors():
    assert keys.ancestors("context") == []
    assert keys.ancestors("context.a1b2.design") == ["context", "context.a1b2"]
    assert keys.ancestors("context.a1b2.design:title") == [
        "context",
        "context.a1b2",
        "context.a1b2.design",
    ]


def test_depth_ignores_the_metadata_suffix():
    assert keys.depth("context") == 1
    assert keys.depth("context.a1b2") == 2
    assert keys.depth("context.a1b2:title") == 2


def test_subtree_range_covers_the_whole_subtree():
    lo, hi = keys.subtree_range("a.b")
    assert lo <= "a.b.c" < hi
    assert lo <= "a.b.c.d.e" < hi


@pytest.mark.parametrize("other", ["a.beta", "a.b_c", "a.b-c", "a.b", "a.c", "a", "a-b.c"])
def test_subtree_range_excludes_prefix_collisions(other):
    lo, hi = keys.subtree_range("a.b")
    assert not (lo <= other < hi)


def test_subtree_range_of_metadata_key_uses_the_document_key():
    assert keys.subtree_range("a.b:title") == keys.subtree_range("a.b")
