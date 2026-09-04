"""Programmatic Markdown heading indexes."""

from __future__ import annotations

import pytest

from outrage import contents
from outrage.mounts import MountedStore, ReadOnlyMountError
from outrage.store import InvalidArgumentError
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

    assert rendered == (
        "# Top\n0\n\n"
        f"## Second ###\n{markdown.index('## Second')}\n\n"
        "Setext heading\n"
        "==============\n"
        f"{markdown.index('Setext heading')}\n"
    )


def test_offsets_are_python_characters_and_keep_crlf_out_of_the_heading():
    markdown = "π\r\n# Héading\r\ntext\r\n"

    assert contents.render_contents(markdown) == "# Héading\n3\n"
    assert len("π\r\n".encode()) != 3


def test_a_multiline_setext_heading_is_kept_as_one_heading():
    markdown = "A long\nheading\n-------\nBody.\n"

    assert contents.render_contents(markdown) == "A long\nheading\n-------\n0\n"


def test_an_empty_or_heading_free_document_has_an_empty_index():
    assert contents.render_contents("") == ""
    assert contents.render_contents("Just prose.\n") == ""


def test_make_contents_writes_default_metadata_and_leaves_source_unchanged(store):
    markdown = "# One\nBody.\n\n## Two\nMore.\n"
    store.store_document("manual", markdown, format="markdown")

    result = contents.make_contents(store, "/manual/")

    expected = "# One\n0\n\n## Two\n13\n"
    assert result == contents.ContentsResult(
        source_key="manual",
        metadata_key="manual/!contents",
        headings=2,
        source_characters=len(markdown),
        characters=len(expected),
    )
    assert store.retrieve_document("manual/!contents").content == expected
    assert store.retrieve_document("manual/!contents").format == "markdown"
    assert store.retrieve_document("manual").content == markdown


def test_custom_metadata_is_regenerated_in_place(store):
    store.store_document("manual", "# Current\n", format="markdown")
    store.store_document("manual/!outline", "stale", format="text")

    result = contents.make_contents(store, "manual", metadata_name="outline")

    assert result.metadata_key == "manual/!outline"
    assert store.retrieve_document("manual/!outline").content == "# Current\n0\n"


@pytest.mark.parametrize("metadata_name", ["", "!contents", "nested/contents"])
def test_metadata_name_must_be_one_direct_name(store, metadata_name):
    store.store_document("manual", "# One\n", format="markdown")

    with pytest.raises(InvalidArgumentError) as raised:
        contents.make_contents(store, "manual", metadata_name=metadata_name)

    assert raised.value.code == "contents-metadata-name"
    assert not store.exists("manual/!contents")


def test_source_must_be_stored_as_markdown(store):
    store.store_document("manual", "# Looks like Markdown", format="text")

    with pytest.raises(InvalidArgumentError) as raised:
        contents.make_contents(store, "manual")

    assert raised.value.code == "contents-not-markdown"
    assert not store.exists("manual/!contents")


def test_root_document_gets_root_metadata(store):
    store.store_document("", "# Store\n", format="markdown")

    result = contents.make_contents(store, "")

    assert result.metadata_key == "!contents"
    assert store.retrieve_document("!contents").content == "# Store\n0\n"


def test_make_contents_reads_past_the_normal_document_page(store):
    markdown = "# First\n" + "x" * 9000 + "\n## Last\n"
    store.store_document("large", markdown, format="markdown")

    result = contents.make_contents(store, "large")

    assert result.headings == 2
    assert store.retrieve_document("large/!contents").content.endswith(
        f"## Last\n{markdown.index('## Last')}\n"
    )


def test_source_and_generated_metadata_route_through_a_mount(store, tmp_path):
    with SqliteStore(tmp_path / "mounted") as mounted:
        mounted.store_document("manual", "# Mounted\n", format="markdown")
        table = MountedStore({"": store, "ref": mounted})

        result = contents.make_contents(table, "ref/manual")

        assert result.metadata_key == "ref/manual/!contents"
        assert mounted.retrieve_document("manual/!contents").content == "# Mounted\n0\n"
        assert not store.exists("ref/manual/!contents")


def test_a_read_only_mount_refuses_the_generated_metadata(store, tmp_path):
    with SqliteStore(tmp_path / "mounted") as mounted:
        mounted.store_document("manual", "# Mounted\n", format="markdown")
        table = MountedStore({"": store, "ref": mounted}, read_only={"ref"})

        with pytest.raises(ReadOnlyMountError):
            contents.make_contents(table, "ref/manual")

        assert not mounted.exists("manual/!contents")
