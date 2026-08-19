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


# -- what a segment may hold ---------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        "café",                  # the namespace is unicode
        "notes/mon café.md",     # spaces and all
        "con text",
        "notes/where?.md",       # `?` is only special as a whole segment
        "context/a1b2!",         # `!` is only special at the start of one
        "a/./b",                 # keys are never resolved, so these navigate
        "a/../b",                # nothing and are ordinary text
        "a/b:title",             # `:` is an ordinary character since schema 5
        "a:.",
        "notes/c++/main.cpp",
        "notes/50%.txt",
        "context\n",             # only characters *below* tab are excluded
    ],
)
def test_a_segment_may_hold_almost_anything(key):
    # The rule is that a key can mirror a filesystem path without transforming
    # the names it carries, so the exclusions are `/` and the control
    # characters below tab -- nothing else.
    assert keys.is_valid(key)


@pytest.mark.parametrize("bad", ["\x00", "\x01", "\x08"])
def test_control_characters_below_tab_are_refused(bad):
    # Excluded so the sort form can mark segments without escaping, and so a
    # NUL cannot truncate a key inside some C string along the way.
    with pytest.raises(InvalidKeyError, match="below"):
        keys.parse(f"a/x{bad}y")


def test_refusing_a_control_character_names_it():
    with pytest.raises(InvalidKeyError, match=r"\\x00"):
        keys.parse("a/\x00")


def test_tab_is_the_lowest_character_a_segment_may_hold():
    assert keys.is_valid("a/\t")
    assert not keys.is_valid("a/\x08")
    assert ord(keys.MIN_SEGMENT_CHAR) == 9


# -- normalisation --------------------------------------------------------


@pytest.mark.parametrize(
    ("written", "stored"),
    [
        ("/context", "context"),
        ("context/", "context"),
        ("/context/", "context"),
        ("context//a1b2", "context/a1b2"),
        ("context///a1b2//design", "context/a1b2/design"),
    ],
)
def test_delimiters_are_tidied_before_the_key_is_judged(written, stored):
    assert keys.parse(written).key == stored


@pytest.mark.parametrize("key", ["", "/", "//", "///"])
def test_there_is_no_root_key(key):
    # Slash normalisation runs first, so these all reduce to the empty string
    # and are then refused like any other empty key. The root is the parent of
    # a top level key, not a key you can address.
    with pytest.raises(InvalidKeyError, match="must not be empty"):
        keys.parse(key)


def test_root_is_not_a_valid_key():
    assert not keys.is_valid(keys.ROOT)


# -- what is still refused ------------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        "!title",       # metadata with no document above it
        "!title/x",
        "context/!",    # a metadata segment with no name
        "context/!/x",
        "a/?",          # a wildcard outside a write
    ],
)
def test_parse_rejects_invalid_keys(key):
    with pytest.raises(InvalidKeyError):
        keys.parse(key)


def test_parse_rejects_non_strings():
    with pytest.raises(InvalidKeyError):
        keys.parse(None)


def test_a_segment_is_bounded():
    assert keys.is_valid("a/" + "x" * keys.MAX_SEGMENT_CHARS)
    with pytest.raises(InvalidKeyError, match="at most"):
        keys.parse("a/" + "x" * (keys.MAX_SEGMENT_CHARS + 1))


def test_a_key_is_bounded():
    assert keys.is_valid("/".join("x" * keys.MAX_SEGMENTS))
    with pytest.raises(InvalidKeyError, match="at most"):
        keys.parse("/".join("x" * (keys.MAX_SEGMENTS + 1)))


def test_is_valid():
    assert keys.is_valid("a/b/!c")
    assert keys.is_valid("a//b")  # normalised, not refused
    assert not keys.is_valid("")


def test_metadata_may_attach_to_an_implicit_key():
    # `context` need not have content of its own for `context/!title` to be legal.
    assert keys.parse("context/!title").parent == "context"


# -- metadata is not a leaf ----------------------------------------------


@pytest.mark.parametrize(
    ("key", "doc_key", "meta_name", "parent"),
    [
        ("a/!title", "a", "title", "a"),
        ("a/!title/b", "a", "title/b", "a/!title"),
        ("a/!title/b/c", "a", "title/b/c", "a/!title/b"),
        ("a/!a/!b", "a", "a/!b", "a/!a"),
        ("a/b/!embedding/openai", "a/b", "embedding/openai", "a/b/!embedding"),
    ],
)
def test_a_path_may_continue_below_a_metadata_segment(key, doc_key, meta_name, parent):
    parsed = keys.parse(key)
    assert parsed.doc_key == doc_key
    assert parsed.meta_name == meta_name
    assert parsed.parent == parent


def test_everything_below_a_metadata_segment_is_metadata():
    # There is no document under a metadata path: the key splits at its *first*
    # `!`, so `meta_name` is non-null for the whole subtree. That is what keeps
    # `meta_name IS NULL` an honest test for "is a document".
    assert keys.parse("a/!title/b").is_metadata
    assert keys.parse("a/!title/b/c/d").is_metadata


def test_a_metadata_subtree_does_not_answer_to_its_parents_name():
    # A survey asking for `title` must match the entry itself and not the
    # documents hanging below it, or every sub-path would count as a title.
    assert keys.parse("a/!title").meta_name == "title"
    assert keys.parse("a/!title/b").meta_name != "title"


def test_parent_is_the_key_without_its_last_segment():
    # One rule, documents and metadata alike -- which is what lets metadata
    # list alongside a document's subkeys.
    for key in ("a/b", "a/!title", "a/!title/b", "notes/src/myfile.py"):
        assert keys.parse(key).parent == key.rsplit("/", 1)[0]


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


def test_only_a_whole_segment_is_a_wildcard():
    # `?` inside a segment is ordinary text, so a key can mirror a filename
    # that contains one.
    for key in ("tmp/a?b", "tmp/?x", "tmp/x:?"):
        assert keys.parse(key, allow_wildcard=True).has_wildcard is False
        assert keys.is_valid(key)


def test_two_wildcards_are_refused():
    with pytest.raises(InvalidKeyError, match="more than one"):
        keys.parse("tmp/?/?", allow_wildcard=True)


def test_a_metadata_segment_cannot_be_allocated():
    # Allocation numbers a document's children; a metadata name is chosen, not
    # counted, so `?` there is a mistake worth naming.
    with pytest.raises(InvalidKeyError, match="document part"):
        keys.parse("a/!title/?", allow_wildcard=True)


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


def test_ancestors_of_a_metadata_subtree_include_the_metadata_above_it():
    assert keys.ancestors("a/!title/b") == ["a", "a/!title"]


def test_depth_ignores_metadata_segments():
    assert keys.depth("context") == 1
    assert keys.depth("context/a1b2") == 2
    assert keys.depth("context/a1b2/!title") == 2
    assert keys.depth("context/a1b2/!title/deep") == 2
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
    # is allowed to contain. These bound stored keys, not sort forms, so the
    # sort markers never reach them.
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


def test_numbers_wider_than_the_pad_stop_sorting_numerically():
    # Recorded rather than fixed. 16 digits covers epoch milliseconds and
    # microseconds, so this needs numbers no key will hold. Note where the
    # limit actually bites: an over-width number still sorts correctly against
    # a padded shorter one, because padding leaves those starting with `0`.
    # It is two over-width numbers of *different* lengths that part.
    wider = "1" * (keys._SORT_WIDTH + 2)
    narrower = "2" * (keys._SORT_WIDTH + 1)
    assert int(wider) > int(narrower)
    assert keys.is_valid(f"a/{wider}")
    assert keys.sort_form(f"a/{wider}") < keys.sort_form(f"a/{narrower}")

    # Up to the pad width, ordering is numeric as promised.
    assert keys.sort_form("a/2") < keys.sort_form("a/" + "9" * keys._SORT_WIDTH)


# -- the sort form -------------------------------------------------------


def test_sort_form_is_not_a_key_the_caller_ever_sees():
    # It exists only for ORDER BY, and is now not merely different from the key
    # but not a legal key at all: its markers sit below what a segment may hold.
    assert keys.sort_form("a/1") != "a/1"
    assert not keys.is_valid(keys.sort_form("a/1"))


def test_sort_form_markers_cannot_occur_in_a_segment():
    # This is what makes the encoding injective without escaping.
    for marker in (keys._SORT_META, keys._SORT_DOC, keys._SORT_DELIMITER):
        assert marker < keys.MIN_SEGMENT_CHAR


def test_distinct_keys_never_share_a_sort_form():
    # Load bearing: pagination resumes with `sort_key > ?` over a non-unique
    # index, so two rows sharing a sort key would mean resuming past one
    # silently skipped the other.
    written = [
        "a", "a/b", "a-x", "a.y", "ab", "a/!title", "a/!title/b", "a/b/!title",
        "a/\x01x", "a/\x02x", "a/\x03x", "a/!1", "a/1", "a/01",
    ]
    stored = {keys.parse(k).key for k in written if keys.is_valid(k)}
    assert len({keys.sort_form(k) for k in stored}) == len(stored)


def test_metadata_sorts_with_its_document_rather_than_after_its_subtree():
    docs = ["a", "a/b", "a/b/c", "ab", "b"]
    by_doc = sorted(docs, key=keys.sort_form)
    by_meta = sorted(docs, key=lambda d: keys.sort_form(f"{d}/!title"))
    assert by_doc == by_meta


def test_the_two_orders_now_agree_over_segment_chars_below_the_delimiter():
    # Schema 4 could not do this. `-` and `.` are legal segment characters that
    # sort below `/`, so with `/` as the sort delimiter `a` sorted before `a-x`
    # while `a/!title` sorted *after* `a-x/!title`. Joining the sort form with a
    # delimiter below every legal segment character closes it.
    assert keys.sort_form("a") < keys.sort_form("a-x")
    assert keys.sort_form("a/!title") < keys.sort_form("a-x/!title")

    # The price, taken knowingly: a subtree now sorts immediately after its
    # parent rather than after prefix-sharing siblings.
    assert keys.sort_form("a/b") < keys.sort_form("a-x")


def test_document_order_and_metadata_order_agree_over_an_adversarial_set():
    # The set that found the double count in schema 4, swept as one property
    # rather than checked case by case.
    docs = ["a", "a-x", "a.y", "a/b", "a/b/c", "ab", "b"]
    by_doc = sorted(docs, key=keys.sort_form)
    by_meta = sorted(docs, key=lambda d: keys.sort_form(f"{d}/!title"))
    assert by_doc == by_meta


def test_a_metadata_segment_sorts_before_any_sibling_document():
    # No longer resting on where `!` happens to sort -- the sort form marks
    # metadata explicitly, so this holds whatever a segment begins with.
    assert keys.sort_form("a/!title") < keys.sort_form("a/-b")
    assert keys.sort_form("a/!title") < keys.sort_form("a/.b")
    assert keys.sort_form("a/!title") < keys.sort_form("a/0")
    assert keys.sort_form("a/!title") < keys.sort_form("a/\t")
    assert keys.sort_form("a/!2") < keys.sort_form("a/!10")


def test_the_old_metadata_suffix_is_now_ordinary_text():
    # `:` was refused until schema 5 to catch the pre-schema-4 spelling. The
    # namespace is unreleased and a filename may contain `:`, so it is an
    # ordinary character now; `migrate_legacy` survives only for the schema 2
    # to 3 migration, which reads keys written before `!` existed.
    assert keys.parse("context/5/state:title").doc_key == "context/5/state:title"
    assert keys.migrate_legacy("context/5/state:title") == "context/5/state/!title"
    assert keys.migrate_legacy("context/5/state") == "context/5/state"
