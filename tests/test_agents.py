"""Checks on the packaged agent definitions.

Like the skill, these are prose and nothing here exercises them. What is
guarded is what would fail silently: a definition that is no longer where the
loader looks, a broken dogfood symlink, or a tool grant that has drifted from
what the agent's procedure actually needs. A missing grant does not fail
loudly — the agent simply cannot do a step, and reports something plausible
instead.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import rage

AGENTS = Path(rage.__file__).parent / "agents"
REPO = Path(__file__).resolve().parents[1]
DOGFOOD = REPO / ".claude" / "agents"

NAMES = ["rage-annotate", "rage-backfill", "rage-search"]


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
    # installing rage anywhere carries the agents it is meant to be used with.
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


@pytest.mark.parametrize("name", NAMES)
def test_dogfood_symlink_resolves_to_the_packaged_agent(name):
    # This project uses its own agents through symlinks, as it does the skill.
    # A broken link leaves the agent quietly absent rather than failing.
    assert (DOGFOOD / f"{name}.md").resolve() == (AGENTS / f"{name}.md").resolve()


def test_annotate_can_read_and_write_but_nothing_else():
    tools = _tools("rage-annotate")

    assert tools == {"mcp__rage__retrieve_document", "mcp__rage__store_document"}
    # It writes one metadata value beside one document. Deletion is not part of
    # that, and an agent that can delete is one bad key away from removing the
    # document it was asked to describe.
    assert "mcp__rage__delete_keys" not in tools


def test_search_reads_at_both_levels_but_does_not_write():
    tools = _tools("rage-search")

    # The cascade needs all three: metadata a level at a time, whole documents
    # for what the metadata could not decide, and the keys carrying no metadata
    # at all, which a survey by that metadata cannot show.
    assert tools == {
        "mcp__rage__get_documents",
        "mcp__rage__retrieve_document",
        "mcp__rage__keys_missing_meta",
    }
    # Searching is a read. An agent that answers a question should not be able
    # to change the thing it was asked about.
    assert "mcp__rage__store_document" not in tools


def test_backfill_surveys_and_delegates_but_does_not_write():
    tools = _tools("rage-backfill")

    # What it actually asks for: the keys missing the metadata, not the
    # documents that already have it.
    assert "mcp__rage__keys_missing_meta" in tools
    assert "Agent" in tools, "it generates by spawning rage-annotate, so it needs to spawn"
    # Every write in the flow goes through rage-annotate, so the metadata
    # contract — omit title, never touch the document key — lives in one place.
    assert "mcp__rage__store_document" not in tools
    assert "mcp__rage__delete_keys" not in tools
