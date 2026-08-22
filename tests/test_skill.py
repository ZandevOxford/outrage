"""Checks on the packaged skill.

Nothing here exercises behaviour; the skill is prose. What these guard is that
the prose is still where the two things that load it expect to find it: the
package, for a later install into another project, and the symlink under
``.claude`` that makes this project use its own skill.
"""

from __future__ import annotations

from pathlib import Path

import outrage

SKILL = Path(outrage.__file__).parent / "skills" / "rage" / "SKILL.md"
REPO = Path(__file__).resolve().parents[1]
DOGFOOD = REPO / ".claude" / "skills" / "rage" / "SKILL.md"


def _frontmatter(text: str) -> dict[str, str]:
    """Parse the leading ``---`` block. Values are single line, so this is enough."""
    assert text.startswith("---\n"), "skill must open with a frontmatter block"
    block, _, _ = text[4:].partition("\n---\n")
    fields = {}
    for line in block.splitlines():
        name, _, value = line.partition(":")
        fields[name.strip()] = value.strip()
    return fields


def test_skill_is_packaged():
    # Shipped inside the package rather than only in the repository, so that
    # installing outrage anywhere carries the skill it is meant to be used with.
    assert SKILL.is_file()


def test_frontmatter_names_the_skill():
    fields = _frontmatter(SKILL.read_text())
    assert fields["name"] == "rage"
    # The description is the only part always in context, so it is what decides
    # whether the skill is ever reached.
    assert len(fields["description"]) > 100


def test_dogfood_symlink_resolves_to_the_packaged_skill():
    # This project uses its own skill through a symlink. A broken link would
    # leave the skill quietly unloaded, which is the failure mode this whole
    # store exists to avoid, so it fails the suite instead.
    assert DOGFOOD.resolve() == SKILL.resolve()
