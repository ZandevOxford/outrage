"""Every check this repository has, and the canonical way to invoke each one.

Running them together is the smaller half of why this exists. The larger half
is that the invocations were only written down inside the release and review
procedures, which are not in this repository, so anybody working from the
checkout alone had to reconstruct them - and reconstructing the omnidep one
wrong is easy and quiet. This file is the record; ``--list`` prints it.

Nothing here says the checks must be run as a set. Run one with ``--only``, or
type the command it names; the point is that the command is the same one every
time it is typed.

## The two that are not what you would guess

**omnidep takes the package alone.** ``--project pyproject.toml src/outrage``,
and not the repository, not ``tests``. omnidep 0.4 does not read PEP 621
optional dependencies, which is already why ``[tool.omnidep] ignore-imports``
lists the optional *runtime* imports in ``pyproject.toml``; the same blindness
means that pointing it at ``tests`` reports ``pytest``, ``PyYAML`` and
``anyio`` from the ``dev`` extra, and pointing it at the repository adds every
``tools/`` module the tests import through ``sys.path``. All twelve are
artefacts of the invocation rather than findings. Bare ``omnidep .`` is the
worst of both.

**The formatter is checked here but not enforced when work is reviewed.** The
review procedure deliberately formats only the files a change touched, because
this project has never committed to a globally clean formatter baseline. It has
one in practice - ``--check`` passes over all 293 files as of 2026-09-16 - and
the release procedure checks it, which is why it is here. So a ``format``
failure on a file nobody touched is a weaker finding than a ``ruff`` failure,
and reformatting the repository to clear it is not this script's suggestion.

## The one that writes

``documents`` runs the generator and then asserts it changed nothing, which is
the release-time form of "the committed reference matches the docstrings". It
is the only check here that can modify the working tree, and it does so before
it can report. That is safe - a regeneration over a current tree is a no-op,
and over a stale one it produces exactly the content that should have been
committed - but it is why it is listed last and why ``--skip documents`` is
worth knowing about mid-edit.

The suite covers the same ground non-destructively, from the other side:
``test_the_reference_is_not_stale`` regenerates into a temporary directory and
compares. So ``tests`` failing there and ``documents`` reporting a change are
one finding, not two.

## What this does not do

It does not build, tag, publish, or touch git beyond ``git diff --check`` and
reading status. Preparing a release runs all of this and then a great deal more
- the ``dist/`` gate, the installed-wheel test under
``OUTRAGE_TEST_INSTALLED=1``, the annotated tag - and that procedure is not
here. This is the checking part alone, lifted out so it can be run when nothing
is being released.
"""

from __future__ import annotations

import argparse
import dataclasses
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parent.parent

#: The importer is a second distribution in this repository, with its own
#: pyproject, its own suite and its own omnidep configuration. Checking it is
#: part of preparing a release, and it is easy to forget when the root suite
#: has just passed, so it is named here rather than remembered.
IMPORTER = "import/mediawiki"

#: Where the generator writes, and so what `documents` watches for changes.
GENERATED = "src/outrage/documents"

#: Stands in for the interpreter inside a command. Not the bare word `python`,
#: which appears in real arguments, and not a `{}` form, which would make every
#: literal brace in a command an escaping problem.
PYTHON = "@PYTHON@"


@dataclasses.dataclass(frozen=True)
class Check:
    """One check: what to run, and what a reader needs to know about it."""

    name: str
    argv: tuple[str, ...]
    """The command. :data:`PYTHON` in any part stands in for the interpreter,
    as a substring rather than a whole word, because ``make`` takes it as half
    of ``PYTHON=<interpreter>``."""

    note: str
    """Why this invocation and not a neighbouring one. Printed by ``--list``."""

    writes: bool = False
    """Whether running it can modify the working tree."""

    def command(self, python: str) -> list[str]:
        return [part.replace(PYTHON, python) for part in self.argv]


CHECKS: tuple[Check, ...] = (
    Check(
        name="tests",
        argv=(PYTHON, "-m", "pytest"),
        note="The whole root suite. testpaths in pyproject points it at tests/.",
    ),
    Check(
        name="doctests",
        argv=(PYTHON, "-m", "pytest", "--doctest-modules", "src/outrage"),
        note=(
            "Doctests live in the package, not in tests/, so they need their own "
            "run: the line above does not collect them."
        ),
    ),
    Check(
        name="ruff",
        argv=(PYTHON, "-m", "ruff", "check", "."),
        note="Lint. The repository, so it reaches tools/, docs/ and import/ too.",
    ),
    Check(
        name="format",
        argv=(PYTHON, "-m", "ruff", "format", "--check", "."),
        note=(
            "Formatting. Checked at release time; the review procedure formats "
            "only changed files. See the module docstring."
        ),
    ),
    Check(
        name="omnidep",
        argv=(PYTHON, "-m", "omnidep", "--project", "pyproject.toml", "src/outrage"),
        note=(
            "Imports against declared dependencies. The package alone - adding "
            "tests/ or the repository reports only artefacts. See the docstring."
        ),
    ),
    Check(
        name="importer-tests",
        argv=(PYTHON, "-m", "pytest", IMPORTER),
        note="The second distribution's own suite, against the installed outrage.",
    ),
    Check(
        name="importer-ruff",
        argv=(PYTHON, "-m", "ruff", "check", IMPORTER),
        note=(
            "Named although `ruff` above covers the path, because the importer "
            "has its own configuration and is easy to forget when it is run alone."
        ),
    ),
    Check(
        name="importer-omnidep",
        argv=(
            PYTHON,
            "-m",
            "omnidep",
            "--project",
            f"{IMPORTER}/pyproject.toml",
            f"{IMPORTER}/src/outrage_mediawiki",
        ),
        note=(
            "Its own pyproject ignores outrage on both sides: this checkout "
            "develops it as an editable sibling rather than managed metadata."
        ),
    ),
    Check(
        name="docs",
        argv=("make", "-C", "docs", "strict", f"PYTHON={PYTHON}"),
        note=(
            "Sphinx with warnings as errors. Needs no network: the intersphinx "
            "inventory is committed at docs/python_objects.inv."
        ),
    ),
    Check(
        name="whitespace",
        argv=("git", "diff", "--check"),
        note="Trailing whitespace and conflict markers in the unstaged diff.",
    ),
    Check(
        name="documents",
        argv=("make", "-C", "docs", "documents", f"PYTHON={PYTHON}"),
        note=(
            "Regenerates the shipped documents and must change nothing. The only "
            "check here that writes; see the module docstring."
        ),
        writes=True,
    ),
)


def generated_state() -> str:
    """A snapshot of the generated tree, for comparing across a regeneration."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", GENERATED],
        cwd=REPOSITORY,
        capture_output=True,
        text=True,
    )
    return result.stdout


def run_check(check: Check, python: str, *, echo: bool) -> tuple[bool, str]:
    """Run one check, returning whether it passed and a one-line reason."""
    command = check.command(python)
    if echo:
        print(f"\n\033[1m$ {' '.join(command)}\033[0m", flush=True)

    before = generated_state() if check.writes else None
    started = time.monotonic()
    result = subprocess.run(command, cwd=REPOSITORY)
    elapsed = time.monotonic() - started

    if result.returncode != 0:
        return False, f"exit {result.returncode} after {elapsed:.0f}s"

    if check.writes:
        after = generated_state()
        if after != before:
            # The command succeeded, so only this comparison can report it.
            print(
                f"\n{check.name}: the generator changed the tree, so what is "
                f"committed under {GENERATED} did not match its sources.\n"
                "Inspect `git status` and commit the regenerated files.",
                file=sys.stderr,
            )
            return False, f"regenerated {GENERATED} after {elapsed:.0f}s"

    return True, f"{elapsed:.0f}s"


def selected(only: Sequence[str], skip: Sequence[str]) -> list[Check]:
    """The checks to run, in declaration order, with names validated."""
    known = {check.name for check in CHECKS}
    for name in [*only, *skip]:
        if name not in known:
            raise SystemExit(
                f"check.py: unknown check {name!r}; --list shows the {len(CHECKS)} there are"
            )
    chosen = [c for c in CHECKS if (not only or c.name in only) and c.name not in skip]
    if not chosen:
        raise SystemExit("check.py: every check was skipped")
    return chosen


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check.py",
        description=(
            "Run this repository's checks, and record how each one is invoked. "
            "Everything passes on a clean tree; a failure is a finding."
        ),
        epilog="With no arguments, runs every check and reports a summary.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print each check, its exact command and why it is that command.",
    )
    parser.add_argument(
        "--only",
        metavar="NAME",
        action="append",
        default=[],
        help="Run only this check. Repeatable.",
    )
    parser.add_argument(
        "--skip",
        metavar="NAME",
        action="append",
        default=[],
        help="Run everything but this check. Repeatable.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help=(
            "Interpreter to run the checks with. Defaults to the one running "
            "this script, which is the project environment when it is invoked "
            "from there."
        ),
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="Run the remaining checks after one fails, rather than stopping.",
    )
    args = parser.parse_args(argv)

    if args.list:
        for check in CHECKS:
            print(f"\033[1m{check.name}\033[0m{'  (writes)' if check.writes else ''}")
            print(f"  {' '.join(check.command(args.python))}")
            print(f"  {check.note}")
        return 0

    checks = selected(args.only, args.skip)
    results: list[tuple[Check, bool, str]] = []
    for check in checks:
        passed, detail = run_check(check, args.python, echo=True)
        results.append((check, passed, detail))
        if not passed and not args.keep_going:
            break

    print("\n\033[1m--- summary ---\033[0m")
    for check, passed, detail in results:
        mark = "\033[32mpass\033[0m" if passed else "\033[31mFAIL\033[0m"
        print(f"  {mark}  {check.name:18} {detail}")
    if len(results) < len(checks):
        remaining = ", ".join(c.name for c in checks[len(results) :])
        print(f"  \033[33mnot run\033[0m  {remaining}")

    failed = [check.name for check, passed, _ in results if not passed]
    if failed:
        print(f"\nfailed: {', '.join(failed)}")
        return 1
    print(f"\nall {len(results)} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
