"""``__all__`` and what each module actually defines, kept in step.

The rule these guard: **every public name a module defines is declared, and
everything declared is defined there.** Like ``test_messages.py`` this is a
rule about the source rather than about behaviour, so it is checked by reading
the code -- a name added tomorrow without a line in ``__all__`` should fail
here, rather than quietly becoming public in one place and absent from another.

It is not only tidiness. Sphinx autodoc honours ``__all__``, so a public name
missing from it is missing from the generated reference as well, with nothing
to say it was left out: that is how ``store.KeyRange``, ``store.BoundedSubtree``
and ``mounts.Segment`` came to be undocumented while the store's own index told
sessions to go and read about them.

The reverse half is what keeps a re-export from being documented twice. A name
imported from a sibling module is documented where it is defined, so listing it
here as well would put a second copy of the same class under a module that does
not define it.
"""

from __future__ import annotations

import ast
import importlib
import pathlib

import pytest

import outrage

PACKAGE = pathlib.Path(outrage.__file__).parent
MODULES = sorted(p.stem for p in PACKAGE.glob("*.py") if not p.stem.startswith("_"))


def _defined(module: str) -> list[str]:
    """The public names assigned or declared at the top level of ``module``.

    Read from the source rather than from the imported module, because
    ``vars()`` cannot tell a name the module defines from one it imported:
    a plain ``str`` constant carries no ``__module__`` to ask.
    """
    tree = ast.parse((PACKAGE / f"{module}.py").read_text())
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            names.append(node.name)
        elif isinstance(node, ast.Assign):
            names += [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.append(node.target.id)
    return [n for n in names if not n.startswith("_") and n != "__all__"]


@pytest.mark.parametrize("module", MODULES)
def test_module_declares_an_all(module: str) -> None:
    assert hasattr(importlib.import_module(f"outrage.{module}"), "__all__"), (
        f"outrage.{module} declares no __all__, so what it offers is whatever "
        f"happens not to start with an underscore"
    )


@pytest.mark.parametrize("module", MODULES)
def test_every_public_name_is_declared(module: str) -> None:
    declared = set(importlib.import_module(f"outrage.{module}").__all__)
    undeclared = [n for n in _defined(module) if n not in declared]
    assert not undeclared, (
        f"outrage.{module} defines {undeclared} without declaring them in "
        f"__all__; add them, or give them a leading underscore if they are "
        f"not meant to be public. Undeclared names are absent from the "
        f"generated documentation as well"
    )


@pytest.mark.parametrize("module", MODULES)
def test_everything_declared_is_defined_here(module: str) -> None:
    defined = set(_defined(module))
    stale = [n for n in importlib.import_module(f"outrage.{module}").__all__ if n not in defined]
    assert not stale, (
        f"outrage.{module} declares {stale} in __all__ but does not define them. "
        f"A re-exported name is documented where it is defined; declaring it "
        f"again here documents a second copy under a module that does not "
        f"define it"
    )


@pytest.mark.parametrize("module", MODULES)
def test_nothing_is_declared_twice(module: str) -> None:
    names = importlib.import_module(f"outrage.{module}").__all__
    duplicated = sorted({n for n in names if names.count(n) > 1})
    assert not duplicated, f"outrage.{module} lists {duplicated} in __all__ more than once"


def _documented_data(module: str) -> tuple[set[str], set[str]]:
    """The module-level constants of ``module``, and which of them autodoc sees.

    Sphinx picks up a ``#:`` comment block immediately above an assignment, or
    one trailing it on the same line. Anything else -- a bare constant, or the
    second name under a comment written for the first -- is invisible in the
    reference, which is the failure this exists to catch.

    Only data is checked. ``undoc-members`` renders a function or a class that
    carries no docstring, but it does not reach a module constant, so data is
    the only kind that can be declared public and still vanish.
    """
    source = (PACKAGE / f"{module}.py").read_text()
    lines = source.splitlines()
    data, documented = set(), set()
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign):
            names = {t.id for t in node.targets if isinstance(t, ast.Name)}
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = {node.target.id}
        else:
            continue
        names = {n for n in names if not n.startswith("_")}
        data |= names
        above = lines[node.lineno - 2].lstrip() if node.lineno >= 2 else ""
        if above.startswith("#:") or "#:" in lines[node.lineno - 1]:
            documented |= names
    return data, documented


@pytest.mark.parametrize("module", MODULES)
def test_every_declared_constant_is_documented(module: str) -> None:
    """Declaring a constant public is not enough to make it appear in the docs.

    Autodoc renders a module constant only when it carries a ``#:`` comment of
    its own, and ``undoc-members`` does not change that. So a constant can be
    in ``__all__``, be used across the package, and still be absent from the
    reference with nothing anywhere to say so -- which is what had happened to
    ``store.SCHEMA_VERSION`` and to every second name of a shared comment run.
    """
    data, documented = _documented_data(module)
    declared = set(importlib.import_module(f"outrage.{module}").__all__)
    undocumented = sorted((data & declared) - documented)
    assert not undocumented, (
        f"outrage.{module} declares {undocumented} in __all__ with no `#:` "
        f"comment, so they are missing from the generated reference. A comment "
        f"written for the name above does not carry down to the next one"
    )


@pytest.mark.parametrize("module", MODULES)
def test_nothing_is_defined_twice(module: str) -> None:
    """A second definition shadows the first in silence, and this found one."""
    names = _defined(module)
    duplicated = sorted({n for n in names if names.count(n) > 1})
    assert not duplicated, (
        f"outrage.{module} defines {duplicated} more than once at the top level; "
        f"the later definition wins and the earlier one is dead"
    )
