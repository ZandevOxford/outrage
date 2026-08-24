"""Checks on the packaged skill.

Nothing here exercises behaviour; the skill is prose. What these guard is that
the prose is still where the two things that load it expect to find it: the
package, for a later install into another project, and the symlink under
``.claude`` that makes this project use its own skill.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import outrage

SKILL = Path(outrage.__file__).parent / "skills" / "outrage" / "SKILL.md"
REPO = Path(__file__).resolve().parents[1]
DOGFOOD = REPO / ".claude" / "skills" / "outrage" / "SKILL.md"
# Where the symlink is meant to land. Not ``SKILL``: that is whichever copy is
# under test, and under ``OUTRAGE_TEST_INSTALLED`` it is an installed one,
# which this project's own configuration has no reason to point at.
IN_CHECKOUT = REPO / "src" / "outrage" / "skills" / "outrage" / "SKILL.md"
# `.claude/` is not committed - all of it is rendered output, this machine's
# configuration, or a canary - so a checkout that was never set up has none of
# it and skips. One that has it is asserted against, and the assertion is the
# invariant the symlink exists for rather than the symlink itself: what a
# client loads from `.claude/` here is what is in this checkout. A OneDrive
# conflict copy, which leaves a plain file holding the link target string, is
# exactly what that catches.
UNCONFIGURED = not (REPO / ".claude").is_dir()
NO_DOGFOOD = "no .claude/ in this checkout; `outrage init` installs one"


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
    assert fields["name"] == "outrage"
    # The description is the only part always in context, so it is what decides
    # whether the skill is ever reached.
    assert len(fields["description"]) > 100


@pytest.mark.skipif(UNCONFIGURED, reason=NO_DOGFOOD)
def test_dogfood_skill_is_the_one_in_the_checkout():
    # This project uses its own skill, linked from `.claude/`. A link that has
    # gone stale leaves the skill quietly unloaded, which is the failure mode
    # this whole store exists to avoid, so it fails the suite instead.
    assert DOGFOOD.read_text(encoding="utf-8") == IN_CHECKOUT.read_text(encoding="utf-8")
