"""The generated half of the shipped documentation, and whether it is still true.

`src/outrage/documents/reference` is rendered from the docstrings in
`src/outrage` and committed. Committed build output has one failure mode that
absent build output does not: a stale page mounts, lists, reads and surveys
exactly like a current one, so nothing about using the store says the reference
stopped matching the code. `context/71` in the outrage store is the design; this
is the guard it left open.

**Two checks, and they fail for different reasons.**

The invariants below run on the committed tree with no Sphinx and in
milliseconds. They do not know whether the reference is current -- they know
whether the render was *sound*, and every defect this work turned up was one
they would have caught, silently, in output that built cleanly: a dropped
keyword-only separator, smartquotes reaching a builder that had opted out, a
title written beside another file claiming the same key.

`test_the_reference_is_not_stale` is the other question, and the expensive one.
It re-renders into a temporary tree and compares, which needs the `docs` extra
and about four seconds. It catches what no amount of reading the committed files
can: a docstring that changed and a page that did not.

The rebuild goes to a temporary directory on purpose. A test that regenerated in
place would repair the thing it is checking, pass for ever, and edit the working
tree while doing it.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from outrage import shipped
from outrage.maintenance import Report
from outrage.store_files import FilesystemStore

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"

# The tools live in `tools/` rather than in the package -- they are run by hand
# after a docs build, not imported by anything outrage installs - so they go on
# the path here, the way `test_harness_delivery.py` reaches its own.
sys.path.insert(0, str(REPO / "tools"))

import document_titles  # noqa: E402
import render_reference  # noqa: E402

#: The section's own document, and the directory holding the module pages.
SECTION = render_reference.SECTION


def section_files(root: Path) -> dict[str, str]:
    """Every file of the reference section under `root`, keyed by relative path.

    A mapping rather than a list so that a failure names the page that differs
    instead of reporting that two directories are not equal.
    """
    found = [root / f"{SECTION}.md", *(root / SECTION).rglob("*")]
    return {str(p.relative_to(root)): p.read_text() for p in sorted(found) if p.is_file()}


def pages(root: Path) -> list[Path]:
    """The documents of the section, metadata files excluded."""
    found = [root / f"{SECTION}.md", *(root / SECTION).rglob("*.md")]
    return [p for p in sorted(found) if p.is_file() and not p.name.startswith("!")]


def test_the_section_is_there_at_all():
    assert pages(shipped.tree()), "no reference section in the documents tree"


def test_no_signature_lost_its_keyword_only_marker():
    """The defect that made this file necessary.

    Sphinx wraps the PEP 3102 keyword-only ``*`` in an ``abbreviation`` node.
    The markdown builder had no handler for it, so it dropped the node and
    emitted ``f(a, b, , log=None)`` -- a doubled comma, and a signature that no
    longer says which parameters are keyword-only. It affected 79 of them, and
    the build succeeded. ``docs/conf.py`` carries the fix.
    """
    offenders = {p.name: len(re.findall(r", ,", p.read_text())) for p in pages(shipped.tree())}
    assert not {name: n for name, n in offenders.items() if n}


def test_no_smartquote_reached_the_markdown():
    """`--` is written as `--`, because these files are committed source.

    Smartquotes are right for HTML and wrong here, and
    ``smartquotes_excludes`` in ``docs/conf.py`` turns them off for this
    builder. It is only half the fix: they are applied when a page is *parsed*,
    and ``-M`` shares one doctree cache between builders, so a markdown build
    after an HTML one once emitted 275 en dashes with the setting present and
    correct. The other half is the separate ``-d`` on the ``markdown`` target.

    If a docstring ever wants a real en or em dash, this is the test to change,
    and the change should be deliberate rather than a surprise.
    """
    offenders = {
        p.name: p.read_text().count("–") + p.read_text().count("—")
        for p in pages(shipped.tree())
    }
    assert not {name: n for name, n in offenders.items() if n}


def test_every_relative_link_resolves():
    """The module pages link to each other, and the promoted page was rewritten.

    Flattening moves `api/index.md` up to `reference.md` while its siblings move
    into `reference/`, so that one page's links are rewritten and the others'
    are deliberately not. This is what says the rewrite was right. Absolute
    links -- intersphinx to docs.python.org -- are left alone.
    """
    broken = []
    for page in pages(shipped.tree()):
        for match in re.finditer(r"\]\((?!\w+:|#)([^)#]+)(#[^)]*)?\)", page.read_text()):
            if not (page.parent / match.group(1)).resolve().exists():
                broken.append(f"{page.name} -> {match.group(1)}")
    assert broken == []


def test_no_key_is_held_by_more_than_one_file():
    """A generator writing `!title.md` beside a hand-written `!title.txt`.

    Both spell the key `cli/!title`; the extension names the format and nothing
    else. Nothing failed when it happened -- one entry listed, one document
    returned -- and the tree resolved it by name order, so the generated title
    silently shadowed the written one. This is the check that knows, and it
    covers the whole tree rather than the section, because the collision is
    between the two halves.
    """
    root = shipped.tree()
    report = Report(path=root)
    with FilesystemStore(root, create=False) as store:
        store.check_file(report)

    assert report.problems == []


@pytest.fixture(scope="module")
def regenerated(tmp_path_factory) -> Path:
    """Render the reference again, from the current docstrings, into a temp tree.

    ``python -m sphinx`` rather than ``make -C docs markdown``, and it is worth
    saying why that is not the flag duplication it looks like: everything in the
    Makefile target is about strictness and caching -- ``-W``, ``-a -E``, its own
    ``-d`` -- and none of it changes what is written. Every content decision is
    in ``docs/conf.py``, which this reads. A fresh output directory has its own
    doctree cache, which is the condition the ``-d`` exists to guarantee.
    """
    for module in ("sphinx", "sphinx_markdown_builder"):
        pytest.importorskip(
            module,
            reason=f"{module} is needed to re-render the reference; install the docs extra",
        )

    build = tmp_path_factory.mktemp("markdown")
    result = subprocess.run(
        [sys.executable, "-m", "sphinx", "-b", "markdown", str(DOCS), str(build)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    dest = tmp_path_factory.mktemp("documents")
    assert render_reference.rearrange(build, dest) == 0
    assert document_titles.main([str(dest)]) == 0
    return dest


def test_the_reference_is_not_stale(regenerated):
    """Re-rendering from the current docstrings changes nothing.

    The whole reason the section can be committed. A page here is build output,
    and the source is the docstring it came from -- so a docstring edited
    without a re-render leaves a page that is well-formed, mounts, reads,
    surveys, and is wrong.

    The pipeline is deterministic: a full regenerate over the committed tree is
    byte-identical, checked before this test was written, so a difference here
    is a real one and not a rebuild artefact.

    To fix a failure, do not edit the page. Run::

        make -C docs markdown
        python tools/render_reference.py docs/_build/markdown src/outrage/documents
        python tools/document_titles.py src/outrage/documents
    """
    fresh = section_files(regenerated)
    committed = section_files(shipped.tree())

    # Two assertions rather than one: a page added or removed is a different
    # failure from a page whose content moved, and reads very differently.
    assert sorted(fresh) == sorted(committed)
    assert fresh == committed
