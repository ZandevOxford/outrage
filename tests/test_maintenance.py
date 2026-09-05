"""What a check can report, as a vocabulary rather than as sentences.

A :class:`~outrage.maintenance.Problem` carries a code and reads as prose, and
the two are for different readers: ``outrage check`` prints the prose, and
anything with something to *do* about a particular fault selects on the code.
They were one thing until 2026-09-05, which is why ``store_sqlite`` exported
its WAL summary as a constant -- a code wearing a sentence's clothes -- and why
the suite picked problems out of a report with ``"cached document lengths" in
p.summary``.

These guards keep the code half honest. There is no wording table here and no
guard about one: there is a single reader of the prose, so a table per audience
would be a table of one. ``plans/problem-codes`` holds that argument, and what
would change it.

Like ``test_notes.py`` and ``test_messages.py`` these are rules about where
code lives, so they are checked by reading the source: a problem raised
tomorrow with an invented code should fail here rather than reach a caller.
"""

from __future__ import annotations

import ast
import pathlib

import outrage
from outrage import maintenance

SOURCE = pathlib.Path(outrage.__file__).parent


def _raises() -> list[tuple[str, int, ast.Call]]:
    """Every ``Problem(...)`` built in the package, with where it is."""
    found = []
    for path in sorted(SOURCE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "Problem":
                found.append((path.name, node.lineno, node))
    return found


def _declared_names() -> set[str]:
    """The names in ``maintenance`` that look like a code constant.

    Every upper-case string it defines, which today is the codes and nothing
    else. A non-code constant of that shape added later fails the test below
    rather than passing quietly -- which is the right way round: whoever adds
    one has to say which of the two it is.
    """
    return {
        name
        for name, value in vars(maintenance).items()
        if name.isupper() and isinstance(value, str)
    }


def test_every_code_constant_is_named_in_the_published_list():
    """``PROBLEM_CODES`` is what a caller reads to know what a check can say."""
    declared = {getattr(maintenance, name) for name in _declared_names()}

    assert declared == set(maintenance.PROBLEM_CODES), (
        "a code constant missing from PROBLEM_CODES, or a constant there that "
        "is not a code; both leave a caller unable to enumerate them"
    )


def test_no_two_problems_share_a_code():
    assert len(set(maintenance.PROBLEM_CODES)) == len(maintenance.PROBLEM_CODES)


def test_every_code_is_spelled_the_way_the_others_are():
    """Kebab-case, as an error's code and a note's are: one vocabulary, one shape."""
    for code in maintenance.PROBLEM_CODES:
        assert code == code.lower().strip(), f"{code!r} is not lower case"
        assert " " not in code and "_" not in code, f"{code!r} is not kebab-case"


def test_no_problem_is_raised_with_a_code_written_out_at_the_site():
    """A literal is a code nothing checks, and a typo in one is a new code.

    The constant is what makes a misspelling a ``NameError`` where it is
    written, rather than a problem a caller's filter silently never matches.
    """
    for filename, lineno, call in _raises():
        assert call.args, f"{filename}:{lineno} builds a Problem without a code"
        assert not isinstance(call.args[0], ast.Constant), (
            f"{filename}:{lineno} passes its code as a literal; "
            f"use the constant in outrage.maintenance so a typo cannot compile"
        )


def test_every_declared_code_can_actually_be_reported():
    """A code nothing raises is a fault the store has stopped being able to have.

    Read by name rather than by value, because that is how a site names one:
    the constant reaches the backends through an import, so a code no module
    mentions is one no check can produce.
    """
    named: set[str] = set()
    for path in SOURCE.glob("*.py"):
        if path.name == "maintenance.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        # Through the local binding, which is not always the code's own name: a
        # module that once exported one of these has to import it under an
        # alias, or the old spelling resolves again with a new value.
        bound = {
            alias.asname or alias.name: alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }
        used = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        named |= {bound.get(name, name) for name in used}

    tree = ast.parse((SOURCE / "maintenance.py").read_text(encoding="utf-8"))
    inside = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "Problem"
    ]
    named |= {call.args[0].id for call in inside if isinstance(call.args[0], ast.Name)}

    unreported = _declared_names() - named - {"PROBLEM_CODES"}
    assert not unreported, f"codes nothing can report: {sorted(unreported)}"


def test_the_report_prints_the_prose_and_not_the_code():
    """The split, from the reading end: a person gets the sentence.

    Worth pinning because the temptation on adding a code is to print it, and
    a check's output is read by whoever is deciding whether their store is in
    trouble -- not by something matching on it.
    """
    import io

    from outrage import cli

    report = maintenance.Report(path=pathlib.Path("store.sqlite"), backend="sqlite")
    report.problems.append(
        maintenance.Problem(
            maintenance.WAL_UNCHECKPOINTED,
            "warning",
            "most of the store is in the write-ahead log",
            "12 bytes against 3",
        )
    )

    out = io.StringIO()
    cli._print_report(report, out)

    assert "most of the store is in the write-ahead log" in out.getvalue()
    assert maintenance.WAL_UNCHECKPOINTED not in out.getvalue()


def test_a_removed_public_name_does_not_come_back_as_a_re_export():
    """0.9.0 said `store_sqlite.WAL_UNCHECKPOINTED` was gone. It was not.

    The definition went, and the constant it was replaced by was imported into
    the same module by its own name -- so the attribute still resolved, with a
    *different value*: the problem code where it used to be that problem's
    summary. A caller comparing a summary against it stopped matching and was
    told nothing, which is the quiet failure the removal was for.

    Found by the post-publication checks, on the published wheel, after the
    changelog and the tag had both claimed the opposite. `plans/problem-codes`
    has the account; the import is aliased private now.
    """
    from outrage import store_sqlite

    assert not hasattr(store_sqlite, "WAL_UNCHECKPOINTED"), (
        "the name is public in maintenance and must not resolve here as well: "
        "same spelling, different value, and nothing to notice"
    )
    assert maintenance.WAL_UNCHECKPOINTED == "wal-uncheckpointed"
