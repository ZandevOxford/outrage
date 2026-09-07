"""Document title extraction from Markdown and HTML."""

import pytest

from outrage import titles


def test_markdown_title_is_the_first_non_empty_single_hash_heading():
    markdown = "## Section\n\n#   \n\n   # Document title ###\n\n# Later\n"

    assert titles.markdown_title(markdown) == "Document title"


def test_markdown_title_ignores_fenced_code_in_both_spellings():
    markdown = "```markdown\n# Not this\n```\n~~~\n# Nor this\n~~~\n# This one\n"

    assert titles.markdown_title(markdown) == "This one"


@pytest.mark.parametrize("markdown", ["", "## Section\n", "    # Indented code\n"])
def test_markdown_without_a_level_one_heading_has_no_title(markdown):
    assert titles.markdown_title(markdown) is None


def test_html_title_wins_over_an_earlier_h1_and_becomes_plain_text():
    html = "<h1>Fallback <a href='/guide'>guide</a></h1><title> The &amp; proper title </title>"

    assert titles.html_title(html) == "The & proper title"


def test_html_uses_first_non_empty_h1_when_title_is_absent_or_empty():
    html = (
        "<title>   </title><h1> Guide <small>for</small> "
        "<a href='/agents'>agents</a><img src='map' alt='map &amp; key'><br>Next</h1>"
        "<h1>Later</h1>"
    )

    assert titles.html_title(html) == "Guide for agentsmap & key Next"


def test_html_hidden_content_does_not_enter_the_fallback():
    html = "<h1>A<script>script</script>B<style>style</style>C<template>x</template>D</h1>"

    assert titles.html_title(html) == "ABCD"


@pytest.mark.parametrize("html", ["", "<p>Untitled</p>", "<title></title><h1></h1>"])
def test_html_without_a_non_empty_candidate_has_no_title(html):
    assert titles.html_title(html) is None


def test_parse_title_dispatches_by_declared_format():
    assert titles.parse_title("# Markdown\n", "markdown") == "Markdown"
    assert titles.parse_title("<h1>HTML</h1>", "html") == "HTML"


def test_parse_title_refuses_an_unsupported_format():
    with pytest.raises(ValueError, match="markdown.*html"):
        titles.parse_title("A title", "text")


@pytest.mark.parametrize(
    ("call", "expected"),
    [
        (lambda: titles.markdown_title(None), "markdown must be a string"),
        (lambda: titles.html_title(None), "html must be a string"),
        (lambda: titles.parse_title("# Title", None), "format must be a string"),
    ],
)
def test_title_inputs_must_be_strings(call, expected):
    with pytest.raises(TypeError, match=expected):
        call()
