"""Programmatic Markdown and HTML heading indexes."""

from __future__ import annotations

import pytest

from outrage import contents
from outrage.mounts import MountedStore, ReadOnlyMountError
from outrage.store import InvalidArgumentError
from outrage.store_files import FilesystemStore
from outrage.store_sqlite import SqliteStore


@pytest.fixture
def store(tmp_path):
    with SqliteStore(tmp_path) as opened:
        yield opened


def test_render_contents_keeps_literal_headings_and_replaces_bodies_with_offsets():
    markdown = (
        "# Top\n"
        "Introduction.\n\n"
        "## Second ###\n"
        "Body.\n\n"
        "````markdown\n"
        "# Not a heading\n"
        "```\n"
        "````\n\n"
        "Setext heading\n"
        "==============\n"
        "Last body.\n"
    )

    rendered = contents.render_contents(markdown)

    # Two numbers per heading, character offset then byte offset. This
    # document is ASCII, so they are the same number and the *shape* is what
    # is being asserted; the pair coming apart is the test below.
    assert rendered == (
        "# Top\n0 0\n\n"
        f"## Second ###\n{markdown.index('## Second')} {markdown.index('## Second')}\n\n"
        "Setext heading\n"
        "==============\n"
        f"{markdown.index('Setext heading')} {markdown.index('Setext heading')}\n"
    )


def test_each_heading_carries_its_character_offset_and_its_byte_offset():
    markdown = "π\r\n# Héading\r\ntext\r\n"

    # Three characters in and four bytes in: the same position, in the two
    # units, which is the whole reason both are written down. A reader with
    # the document as a string wants the first; a reader with the document as
    # a file wants the second.
    assert contents.render_contents(markdown) == "# Héading\n3 4\n"
    assert len("π\r\n".encode()) == 4


def test_link_targets_are_stripped_by_default_and_can_be_kept():
    markdown = (
        '# A [string](https://example.test/types_(one)) and [*display text*](target "title")\n'
    )

    assert contents.render_contents(markdown) == "# A string and *display text*\n0 0\n"
    assert contents.render_contents(markdown, strip_links=False) == f"{markdown.rstrip()}\n0 0\n"


def test_an_unclosed_link_is_kept_literal():
    markdown = "# [Not a complete link](somewhere\n"

    assert contents.render_contents(markdown) == "# [Not a complete link](somewhere\n0 0\n"


def test_link_syntax_in_code_or_escaped_text_is_not_a_link():
    markdown = r"# `[code](target)` and \[literal](target) and [link](target)" + "\n"

    assert contents.render_contents(markdown) == (
        r"# `[code](target)` and \[literal](target) and link" + "\n0 0\n"
    )


def test_a_byte_offset_from_an_index_lands_on_its_heading_in_every_backend(store, tmp_path):
    """The pair, checked by using it -- which is what it is for.

    Both numbers name the same heading, and the byte one names it in a store
    that seeks to it and in a store that converts. A backend that confused the
    two would pass every rendering test above and fail this.
    """
    markdown = "# Café\n\nnaïve — 😀 body\n\n## Über\n\nend\n"
    store.store_document("manual", markdown, format="markdown")
    contents.make_contents(store, "manual")

    tree = FilesystemStore(tmp_path / "tree")
    tree.store_document("manual", markdown, format="markdown")

    last = store.retrieve_document("manual/!contents").content.splitlines()[-1]
    characters, byte_offset = (int(number) for number in last.split())

    assert markdown[characters:].startswith("## Über")
    with tree:
        for opened in (store, tree):
            assert opened.retrieve_document("manual", byte_offset=byte_offset).content.startswith(
                "## Über"
            )


def test_an_index_of_a_crlf_source_is_lf_and_still_addresses_it(store, tmp_path):
    """Both rules of `plans/line-endings` meeting on one operation.

    The source keeps the endings it arrived with -- rule (a), and in a
    directory of files that means the bytes on disk. The index the store
    *authors* over it is LF -- rule (b), because a generated document has no
    ending to preserve. And the offsets in that LF index still name the
    headings in the CRLF source, in both units and in both backends, which is
    the only thing that makes the pair worth writing down.
    """
    markdown = "# Café\r\n\r\nnaïve — 😀 body\r\n\r\n## Über\r\n\r\nend\r\n"
    store.store_document("manual", markdown, format="markdown")
    tree = FilesystemStore(tmp_path / "tree")
    tree.store_document("manual", markdown, format="markdown")

    with tree:
        for opened in (store, tree):
            index = contents.make_contents(opened, "manual")
            written = opened.retrieve_document("manual/!contents").content

            assert opened.retrieve_document("manual").content == markdown
            assert index.source_bytes == len(markdown.encode())
            assert "\r" not in written

            characters, byte_offset = (int(number) for number in written.splitlines()[-1].split())
            assert markdown[characters:].startswith("## Über")
            assert markdown.encode()[byte_offset:].startswith("## Über".encode())
            assert opened.retrieve_document("manual", byte_offset=byte_offset).content.startswith(
                "## Über"
            )


def test_a_multiline_setext_heading_is_kept_as_one_heading():
    markdown = "A long\nheading\n-------\nBody.\n"

    assert contents.render_contents(markdown) == "A long\nheading\n-------\n0 0\n"


def test_an_empty_or_heading_free_document_has_an_empty_index():
    assert contents.render_contents("") == ""
    assert contents.render_contents("Just prose.\n") == ""


def test_html_headings_become_plain_markdown_with_readable_text():
    html = (
        '<H1 class="title"> Guide <small>for</small> '
        '<a href="/agents">agents</a></H1>\n'
        "<h2>Caf&eacute; <em>setup</em> <code>now</code> "
        '<img src="map.png" alt="map &amp; key"><br>Next</h2>'
    )
    second = html.index("<h2>")

    assert contents.render_html_contents(html) == (
        f"# Guide for agents\n0 0\n\n## Café setup now map & key Next\n{second} {second}\n"
    )


@pytest.mark.parametrize("level", range(1, 7))
def test_each_html_heading_level_maps_to_the_same_markdown_level(level):
    html = f"<h{level}>Heading</h{level}>"

    assert contents.render_html_contents(html) == f"{'#' * level} Heading\n0 0\n"


def test_html_heading_offsets_address_the_original_non_ascii_crlf_source():
    html = "π\r\n<p>body</p>\r\n<H2 data-x='1'>Über</H2>"
    offset = html.index("<H2")
    byte_offset = len(html[:offset].encode())

    rendered = contents.render_html_contents(html)

    assert rendered == f"## Über\n{offset} {byte_offset}\n"
    assert html[offset:].startswith("<H2")
    assert html.encode()[byte_offset:].startswith(b"<H2")


def test_html_non_visible_content_does_not_enter_a_heading():
    html = (
        "<h1>A<!-- comment --><script>script</script>B"
        "<style>style</style>C<template><b>template</b></template>D</h1>"
    )

    assert contents.render_html_contents(html) == "# ABCD\n0 0\n"


def test_html_parser_bounds_recovery_for_unclosed_and_nested_headings():
    html = "<h1>One<h2>Two</h3><h4></h4>"

    assert contents.render_html_contents(html) == ("# One\n0 0\n\n## Two\n7 7\n\n####\n19 19\n")


def test_html_without_headings_has_an_empty_index():
    assert contents.render_html_contents("<p>Just prose.</p>") == ""


def test_make_contents_writes_default_metadata_and_leaves_source_unchanged(store):
    markdown = "# One\nBody.\n\n## Two\nMore.\n"
    store.store_document("manual", markdown, format="markdown")

    result = contents.make_contents(store, "/manual/")

    expected = "# One\n0 0\n\n## Two\n13 13\n"
    assert result == contents.ContentsResult(
        source_key="manual",
        metadata_key="manual/!contents",
        headings=2,
        source_characters=len(markdown),
        source_bytes=len(markdown.encode()),
        characters=len(expected),
    )
    assert store.retrieve_document("manual/!contents").content == expected
    assert store.retrieve_document("manual/!contents").format == "markdown"
    assert store.retrieve_document("manual").content == markdown


def test_make_contents_writes_an_html_index_and_leaves_source_unchanged(store):
    html = "<!doctype html>\n<h1><a href='/one'>One</a></h1>\n<p>Body.</p>\n"
    store.store_document("manual", html, format="html")

    result = contents.make_contents(store, "manual", strip_links=False)

    offset = html.index("<h1>")
    expected = f"# One\n{offset} {offset}\n"
    assert result == contents.ContentsResult(
        source_key="manual",
        metadata_key="manual/!contents",
        headings=1,
        source_characters=len(html),
        source_bytes=len(html.encode()),
        characters=len(expected),
    )
    assert store.retrieve_document("manual/!contents").content == expected
    assert store.retrieve_document("manual/!contents").format == "markdown"
    assert store.retrieve_document("manual").content == html


def test_custom_metadata_is_regenerated_in_place(store):
    store.store_document("manual", "# Current\n", format="markdown")
    store.store_document("manual/!outline", "stale", format="text")

    result = contents.make_contents(store, "manual", metadata_name="outline")

    assert result.metadata_key == "manual/!outline"
    assert store.retrieve_document("manual/!outline").content == "# Current\n0 0\n"


@pytest.mark.parametrize("metadata_name", ["", "!contents", "nested/contents"])
def test_metadata_name_must_be_one_direct_name(store, metadata_name):
    store.store_document("manual", "# One\n", format="markdown")

    with pytest.raises(InvalidArgumentError) as raised:
        contents.make_contents(store, "manual", metadata_name=metadata_name)

    assert raised.value.code == "contents-metadata-name"
    assert not store.exists("manual/!contents")


def test_source_must_be_stored_as_markdown_or_html(store):
    store.store_document("manual", "# Looks like Markdown", format="text")

    with pytest.raises(InvalidArgumentError) as raised:
        contents.make_contents(store, "manual")

    assert raised.value.code == "contents-not-markdown"
    assert not store.exists("manual/!contents")


def test_root_document_gets_root_metadata(store):
    store.store_document("", "# Store\n", format="markdown")

    result = contents.make_contents(store, "")

    assert result.metadata_key == "!contents"
    assert store.retrieve_document("!contents").content == "# Store\n0 0\n"


def test_make_contents_reads_past_the_normal_document_page(store):
    markdown = "# First\n" + "x" * 9000 + "\n## Last\n"
    store.store_document("large", markdown, format="markdown")

    result = contents.make_contents(store, "large")

    assert result.headings == 2
    assert store.retrieve_document("large/!contents").content.endswith(
        f"## Last\n{markdown.index('## Last')} {markdown.index('## Last')}\n"
    )


def test_source_and_generated_metadata_route_through_a_mount(store, tmp_path):
    with SqliteStore(tmp_path / "mounted") as mounted:
        mounted.store_document("manual", "# Mounted\n", format="markdown")
        table = MountedStore({"": store, "ref": mounted})

        result = contents.make_contents(table, "ref/manual")

        assert result.metadata_key == "ref/manual/!contents"
        assert mounted.retrieve_document("manual/!contents").content == "# Mounted\n0 0\n"
        assert not store.exists("ref/manual/!contents")


def test_html_source_and_generated_metadata_route_through_a_mount(store, tmp_path):
    with SqliteStore(tmp_path / "mounted") as mounted:
        mounted.store_document("manual", "<h1>Mounted <em>HTML</em></h1>", format="html")
        table = MountedStore({"": store, "ref": mounted})

        result = contents.make_contents(table, "ref/manual")

        assert result.metadata_key == "ref/manual/!contents"
        assert mounted.retrieve_document("manual/!contents").content == "# Mounted HTML\n0 0\n"
        assert not store.exists("ref/manual/!contents")


def test_a_read_only_mount_refuses_the_generated_metadata(store, tmp_path):
    with SqliteStore(tmp_path / "mounted") as mounted:
        mounted.store_document("manual", "# Mounted\n", format="markdown")
        table = MountedStore({"": store, "ref": mounted}, read_only={"ref"})

        with pytest.raises(ReadOnlyMountError):
            contents.make_contents(table, "ref/manual")

        assert not mounted.exists("manual/!contents")
