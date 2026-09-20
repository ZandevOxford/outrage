"""The repository's source names nothing in this project's own store.

A comment or docstring is read by someone who has the repository and not the
store, and a docstring in ``src/`` is rendered into the published reference as
well, so a key there points at something the reader cannot open. The argument
belongs in the comment; the pointer belongs in ``file_notes``.

**This is a repository-wide rule, not a package one** -- John, 2026-09-12.
Sweeping ``import/`` from the ``outrage`` suite is a little inelegant, since
that is a separate distribution with its own dependencies and release cycle,
and it is still the right place: what the rule protects is a *reader of this
repository*, who does not care which of the two trees a file belongs to. The
sweep had covered only ``src/`` and ``tools/``, so ``import/`` arrived in
0.12.0 with nothing checking it.

So the walk is every Python file in the repository, minus the exemptions
below, rather than a list of blessed folders -- a new top-level tree is then
covered the day it appears instead of the day somebody remembers this file.

**``tests/`` is exempt, deliberately**, John's call of 2026-09-05: not
published, and a test naming the thread that produced it is close to a
citation. About 151 comments there name a key. That exemption is by directory
name, so ``import/mediawiki/tests/`` gets it for the same reason.

**``.claude/`` and ``.codex/`` are exempt** because they are neither committed
nor source: ``outrage init`` renders them from ``src/outrage/``, which this
sweep already covers, so a key found there is a key in ``src/`` reported at a
second address. They are also gitignored, so including them would make the
test's coverage depend on whether the checkout had been initialised -- and a
guard that checks more on one machine than another is the failure mode this
repository keeps paying for.

**``.outrage/`` is exempt for the second of those reasons**, added 2026-09-20.
It is the store directory: gitignored, per machine, and holding whatever a
past session happened to leave in ``archive/`` -- so a sweep over it checks a
different set of files on every checkout. It is also the one place where a
store key in a comment is *right*: a kept one-off script lives there because
it is not the repository, and ``workflow`` says the store document that
commissioned it gets the route.

This is only the searchable part of the rule. A key written without its
namespace root slips past it, and so does a comment narrating a change rather
than saying why the code is shaped the way it is. ``context/`` is also the key
grammar's own example namespace, so only a thread number the size real ones
have reached counts as a reference; ``context/5/state`` is an example.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent
REFERENCE = re.compile(r"\b(?:plans|issues)/|\bcontext/\d{3,}")

# Rendered output and build products, none of it committed source. `tests` is
# the one exemption that is about the rule rather than about what a directory
# is; the docstring says why each is here.
EXEMPT = frozenset(
    {
        "tests",
        ".claude",
        ".codex",
        ".outrage",
        "__pycache__",
        ".venv",
        ".git",
        ".ruff_cache",
        ".pytest_cache",
        "build",
        "dist",
        "_build",
    }
)


def swept() -> list[pathlib.Path]:
    """Every Python file the rule binds, as paths relative to the repository."""
    return [
        path.relative_to(ROOT)
        for path in sorted(ROOT.rglob("*.py"))
        if not EXEMPT & set(path.relative_to(ROOT).parts)
    ]


def test_no_store_references_in_repository_source():
    found = [
        f"{relative}:{number}: {line.strip()}"
        for relative in swept()
        for number, line in enumerate((ROOT / relative).read_text(encoding="utf-8").splitlines(), 1)
        if REFERENCE.search(line)
    ]
    assert not found, "store keys in repository source:\n" + "\n".join(found)


def test_the_sweep_reaches_every_tree_that_holds_source():
    """The walk is only worth anything if it is actually reaching the trees.

    A rglob that silently matched nothing -- a renamed folder, an exemption
    grown too broad -- would pass the rule above while checking air, which is
    the one failure this guard cannot otherwise show. So name the trees that
    must be in it, `import/` among them, and assert the exemptions hold.
    """
    swept_paths = swept()
    tops = {path.parts[0] for path in swept_paths if len(path.parts) > 1}
    assert {"src", "tools", "import", "docs"} <= tops, tops
    assert pathlib.Path("conftest.py") in swept_paths
    importer = ("import", "mediawiki", "src")
    assert any(path.parts[:3] == importer for path in swept_paths), "import/mediawiki/src missed"

    # The exemptions, which are as much of the contract as the walk is.
    assert not [path for path in swept_paths if "tests" in path.parts]
    assert not [path for path in swept_paths if path.parts[0] in {".claude", ".codex", ".outrage"}]
