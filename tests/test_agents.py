"""Checks on the packaged agent definitions.

Like the skill, these are prose and nothing here exercises them. What is
guarded is what would fail silently: a definition that is no longer where the
loader looks, a broken dogfood symlink, or a tool grant that has drifted from
what the agent's procedure actually needs. A missing grant does not fail
loudly - the agent simply cannot do a step, and reports something plausible
instead.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import outrage

AGENTS = Path(outrage.__file__).parent / "agents"
REPO = Path(__file__).resolve().parents[1]
DOGFOOD = REPO / ".claude" / "agents"
# Where the symlinks are meant to land. Not ``AGENTS``: that is whichever copy
# is under test, and under ``OUTRAGE_TEST_INSTALLED`` it is an installed one,
# which this project's own configuration has no reason to point at.
IN_CHECKOUT = REPO / "src" / "outrage" / "agents"
# `.claude/` is not committed - all of it is rendered output, this machine's
# configuration, or a canary - so a checkout that was never set up has none of
# it and skips. One that has it is asserted against, and the assertion is the
# invariant the symlink exists for rather than the symlink itself: what a
# client loads from `.claude/` here is what is in this checkout. A OneDrive
# conflict copy, which leaves a plain file holding the link target string, is
# exactly what that catches.
UNCONFIGURED = not (REPO / ".claude").is_dir()
NO_DOGFOOD = "no .claude/ in this checkout; `outrage init` installs one"

NAMES = ["outrage-annotate", "outrage-backfill", "outrage-search"]


def _frontmatter(text: str) -> dict[str, str]:
    """Parse the leading ``---`` block. Values are single line, so this is enough."""
    assert text.startswith("---\n"), "an agent must open with a frontmatter block"
    block, _, _ = text[4:].partition("\n---\n")
    fields = {}
    for line in block.splitlines():
        name, _, value = line.partition(":")
        fields[name.strip()] = value.strip()
    return fields


def _fields(name: str) -> dict[str, str]:
    return _frontmatter((AGENTS / f"{name}.md").read_text())


def _tools(name: str) -> set[str]:
    return {t.strip() for t in _fields(name)["tools"].split(",") if t.strip()}


@pytest.mark.parametrize("name", NAMES)
def test_agent_is_packaged(name):
    # Shipped inside the package rather than only in the repository, so that
    # installing outrage anywhere carries the agents it is meant to be used with.
    assert (AGENTS / f"{name}.md").is_file()


@pytest.mark.parametrize("name", NAMES)
def test_frontmatter_name_matches_the_filename(name):
    # The loader keys on the frontmatter name; the filename is how a person
    # finds it. They being different is confusing rather than broken, which is
    # exactly the kind of thing that survives review.
    assert _fields(name)["name"] == name


@pytest.mark.parametrize("name", NAMES)
def test_description_is_substantial(name):
    # The description is the only part in context before the agent is chosen,
    # so it is what decides whether the agent is ever reached.
    assert len(_fields(name)["description"]) > 100


@pytest.mark.skipif(UNCONFIGURED, reason=NO_DOGFOOD)
@pytest.mark.parametrize("name", NAMES)
def test_dogfood_agent_is_the_one_in_the_checkout(name):
    # This project uses its own agents, linked from `.claude/` as the skill is.
    # A link that has gone stale leaves the agent quietly absent rather than
    # failing.
    assert (DOGFOOD / f"{name}.md").read_text(encoding="utf-8") == (
        IN_CHECKOUT / f"{name}.md"
    ).read_text(encoding="utf-8")


def test_annotate_can_read_and_write_but_nothing_else():
    tools = _tools("outrage-annotate")

    assert tools == {"mcp__outrage__read_document", "mcp__outrage__store_document"}
    # It writes one metadata value beside one document. Deletion is not part of
    # that, and an agent that can delete is one bad key away from removing the
    # document it was asked to describe.
    assert "mcp__outrage__delete_keys" not in tools


def test_search_reads_at_both_levels_but_does_not_write():
    tools = _tools("outrage-search")

    # The cascade needs all three: metadata a level at a time, whole documents
    # for what the metadata could not decide, and the keys carrying no metadata
    # at all, which a survey by that metadata cannot show.
    assert tools == {
        "mcp__outrage__get_documents",
        "mcp__outrage__read_document",
        "mcp__outrage__keys_missing_meta",
    }
    # Searching is a read. An agent that answers a question should not be able
    # to change the thing it was asked about.
    assert "mcp__outrage__store_document" not in tools


def test_backfill_surveys_and_delegates_but_does_not_write():
    tools = _tools("outrage-backfill")

    # What it actually asks for: the keys missing the metadata, not the
    # documents that already have it.
    assert "mcp__outrage__keys_missing_meta" in tools
    assert "Agent" in tools, "it generates by spawning outrage-annotate, so it needs to spawn"
    # Every write in the flow goes through outrage-annotate, so the metadata
    # contract - omit title, never touch the document key - lives in one place.
    assert "mcp__outrage__store_document" not in tools
    assert "mcp__outrage__delete_keys" not in tools
