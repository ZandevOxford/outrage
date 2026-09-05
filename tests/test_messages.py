"""The wording layer, and the two halves of it staying in step.

The rule these guard: **the library layers carry facts, the front ends write
sentences.** It is a rule about where code lives, so it is worth checking by
reading the code rather than by exercising every failure - a raise site added
tomorrow with a message baked into it should fail here, not silently reach a
user in whatever shape it was written.

See ``project/reference/planned/error-naming`` for the defect that prompted it.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from conftest import long_options
from outrage import cli, keys, messages
from outrage.errors import OutrageError
from outrage.mounts import Mount, MountedStore, ReadOnlyMountError
from outrage.store import KeyNotFoundError
from outrage.store_sqlite import SqliteStore

SOURCE = pathlib.Path(messages.__file__).parent


def _outrage_errors() -> set[str]:
    """Every exception class in the package that ends up a ``OutrageError``.

    Derived from the source rather than listed here. A hand-kept list is a
    second place to remember a new error, and the way it fails is silent: a
    class missing from it makes every raise site invisible to the three tests
    below, so a code with no template, a message composed at the raise site,
    and a template nothing raises all pass. That happened when the parquet
    backend added two.

    Resolved transitively, so a class inheriting one of the others is counted
    however deep the chain goes, and read from ``ast`` rather than by importing
    because the raise sites are read that way too and the two must agree about
    which files they are looking at.
    """
    bases: dict[str, set[str]] = {}
    for path in sorted(SOURCE.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ClassDef):
                bases[node.name] = {b.id for b in node.bases if isinstance(b, ast.Name)}

    errors = {"OutrageError"}
    while True:
        found = {name for name, parents in bases.items() if parents & errors}
        if found <= errors:
            return errors
        errors |= found


OUTRAGE_ERRORS = _outrage_errors()


def _raises() -> list[tuple[str, int, ast.Call]]:
    """Every ``raise SomeOutrageError(...)`` in the package, with where it is."""
    found = []
    for path in sorted(SOURCE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
                continue
            function = node.exc.func
            name = getattr(function, "id", getattr(function, "attr", None))
            if name in OUTRAGE_ERRORS:
                found.append((path.name, node.lineno, node.exc))
    return found


#: Stand-in details by shape rather than by meaning. A key has to be a string a
#: namer can parse, a count has to survive arithmetic, and a plural has to be
#: iterable; nothing here is about what the value would really be.
_COUNTS = {"beneath", "segments", "limit", "length", "found", "expected", "occurrence", "offset"}
_PLURALS = {"mounts"}


def _stand_in(detail: str) -> object:
    if detail in _COUNTS:
        return 1
    if detail in _PLURALS:
        return ["a"]
    return "a"


def test_every_raise_names_a_code_that_has_a_template():
    """A code with no sentence is a caller reading an AssertionError instead."""
    table = messages.codes()
    for filename, lineno, call in _raises():
        assert call.args, f"{filename}:{lineno} raises without a code"
        first = call.args[0]
        assert isinstance(first, ast.Constant) and isinstance(first.value, str), (
            f"{filename}:{lineno} passes a computed first argument; "
            f"a code must be a literal so this test can find it"
        )
        assert first.value in table, f"{filename}:{lineno} has no template for {first.value!r}"


def test_no_raise_site_composes_a_message():
    """The rule itself: facts go in, prose does not.

    An f-string as the code is the shape this catches - it is what every one of
    these raise sites looked like before, and what writing a new one from
    memory would produce.
    """
    for filename, lineno, call in _raises():
        assert not isinstance(call.args[0], ast.JoinedStr), (
            f"{filename}:{lineno} builds its message where it is raised; "
            f"pass a code and details, and put the wording in messages.py"
        )
        assert len(call.args) == 1, (
            f"{filename}:{lineno} passes more than a code positionally; "
            f"details are keyword arguments"
        )


def test_every_template_is_used_by_a_raise_site():
    """Wording nothing can produce is wording nobody maintains."""
    raised = {
        call.args[0].value
        for _, _, call in _raises()
        if call.args and isinstance(call.args[0], ast.Constant)
    }
    unused = set(messages.codes()) - raised
    assert not unused, f"templates nothing raises: {sorted(unused)}"


def test_every_template_renders_from_the_details_its_raise_site_passes():
    """Rendering must not be the thing that fails when something else has."""
    for filename, lineno, call in _raises():
        code = call.args[0].value
        details = {keyword.arg: _stand_in(keyword.arg) for keyword in call.keywords if keyword.arg}
        error = OutrageError(code, **details)
        rendered = messages.render(error)
        assert isinstance(rendered, str) and rendered, f"{filename}:{lineno} renders nothing"


def test_str_is_a_developer_rendering_not_a_message():
    """So that anything printing an error straight at a user looks wrong."""
    error = KeyNotFoundError("key-not-found", key="python/nope")
    assert str(error) == "KeyNotFoundError('key-not-found', key='python/nope')"
    assert messages.render(error) == "nothing is stored at or below 'python/nope'"


def test_the_namer_is_what_makes_one_error_two_sentences(tmp_path):
    """The whole point: the same failure, named for whoever is reading it."""
    error = KeyNotFoundError("key-not-found", key="python/nope")

    # The command line, which opened one store directory.
    assert messages.render(error) == "nothing is stored at or below 'python/nope'"

    # The server, for which that store sits behind a mount point.
    mount = Mount(prefix="ref", store=None)  # type: ignore[arg-type]
    assert messages.render(error, name=mount.outer) == (
        "nothing is stored at or below 'ref/python/nope'"
    )


def test_the_root_of_a_mounted_store_is_not_reported_as_a_blank_key(tmp_path):
    """`planned/root-key/impact` finding 7, reached through a mount."""
    error = KeyNotFoundError("key-not-found", key=keys.ROOT)
    assert messages.render(error) == "nothing is stored at or below '/'"

    mount = Mount(prefix="blank", store=None)  # type: ignore[arg-type]
    assert messages.render(error, name=mount.outer) == "nothing is stored at or below 'blank'"


def test_the_container_advice_names_the_key_the_caller_would_use(tmp_path):
    """The worst of the three faults: advice that produces a silent wrong answer.

    "use list_keys" is only correct when the key it implies is the one the
    caller can actually pass back.
    """
    error = KeyNotFoundError("key-is-a-container", key="python", beneath=2)
    mount = Mount(prefix="ref", store=None)  # type: ignore[arg-type]
    rendered = messages.render(error, name=mount.outer)
    assert "'ref/python'" in rendered
    assert "'python'," not in rendered


def test_the_command_line_only_names_arguments_it_actually_has():
    """A flag in a sentence has to be a flag somebody can type.

    `cli._flag` is a rule rather than a table -- a dest is its long option with
    the dashes turned into underscores -- and this is what keeps the rule
    honest. A template converted to `spell` for an argument only the tools take
    would produce `--against`, and the failure would look exactly like the
    defect the speller exists to fix, one level down.
    """
    options = long_options(cli.argument_parser())

    for filename, lineno, call in _raises():
        named: list[str] = []

        def spell(argument: str, value: object = None, seen: list[str] = named) -> str:
            seen.append(f"--{argument.replace('_', '-')}")
            return cli._flag(argument, value)

        details = {keyword.arg: _stand_in(keyword.arg) for keyword in call.keywords if keyword.arg}
        messages.render(OutrageError(call.args[0].value, **details), spell=spell)
        for flag in named:
            assert flag in options, (
                f"{filename}:{lineno} names {flag}, which the command line has no option for"
            )


def test_no_detail_is_called_spell():
    """`spell` reaches a template as a keyword, so a detail of that name would win.

    The same collision the namer avoids by being positional-only, in the one
    place that argument cannot be positional: adding it to ninety templates
    that do not want it is the churn this shape exists to skip.
    """
    for filename, lineno, call in _raises():
        assert "spell" not in {keyword.arg for keyword in call.keywords}, (
            f"{filename}:{lineno} passes a detail called 'spell', which the "
            f"speller is passed as; call it something else"
        )


def test_the_speller_is_what_makes_one_argument_two_spellings():
    """The namer's rule for the other half: a flag is not what a tool is passed.

    A command line user told to pass `on_conflict='overwrite-unchanged'` is
    told to type something that does not exist. `context/111/findings` 5.
    """
    error = OutrageError("unchanged-since-needed", on_conflict="overwrite-unchanged")

    assert messages.render(error).startswith("on_conflict='overwrite-unchanged' overwrites")
    assert "it needs unchanged_since to measure against" in messages.render(error)

    typed = messages.render(error, spell=cli._flag)
    assert typed.startswith("--on-conflict overwrite-unchanged overwrites")
    assert "it needs --unchanged-since to measure against" in typed
    assert "Pass the time you looked, or --on-conflict overwrite to replace" in typed


def test_a_render_without_a_template_raises_rather_than_guessing():
    with pytest.raises(AssertionError, match="no message template"):
        messages.render(OutrageError("not-a-real-code"))


def test_a_read_only_refusal_still_names_the_key_that_was_asked_for(tmp_path):
    """Raised at the boundary, so it was already right; kept so it stays right."""
    with SqliteStore(tmp_path / "root") as root, SqliteStore(tmp_path / "ref") as ref:
        with MountedStore({"": root, "ref": ref}, read_only=["ref"]) as table:
            with pytest.raises(ReadOnlyMountError) as raised:
                table.resolve("ref/x").writable()
    assert "cannot write 'ref/x'" in messages.render(raised.value)
