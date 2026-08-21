"""The wording layer, and the two halves of it staying in step.

The rule these guard: **the library layers carry facts, the front ends write
sentences.** It is a rule about where code lives, so it is worth checking by
reading the code rather than by exercising every failure — a raise site added
tomorrow with a message baked into it should fail here, not silently reach a
user in whatever shape it was written.

See ``project/reference/planned/error-naming`` for the defect that prompted it.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from rage import keys, messages
from rage.errors import RageError
from rage.mounts import Mount, Mounts, ReadOnlyMountError
from rage.store import KeyNotFoundError
from rage.store_sqlite import SqliteStore

SOURCE = pathlib.Path(messages.__file__).parent
RAGE_ERRORS = {
    "RageError",
    "BackupError",
    "CheckError",
    "ConfigError",
    "ConflictingSourceError",
    "InstallError",
    "InvalidKeyError",
    "KeyNotFoundError",
    "LogError",
    "MountError",
    "PatternNotFoundError",
    "ReadOnlyMountError",
    "SourceMissingError",
    "StoreFileError",
    "UnmappableError",
}


def _raises() -> list[tuple[str, int, ast.Call]]:
    """Every ``raise SomeRageError(...)`` in the package, with where it is."""
    found = []
    for path in sorted(SOURCE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
                continue
            function = node.exc.func
            name = getattr(function, "id", getattr(function, "attr", None))
            if name in RAGE_ERRORS:
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

    An f-string as the code is the shape this catches — it is what every one of
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
        error = RageError(code, **details)
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


def test_a_render_without_a_template_raises_rather_than_guessing():
    with pytest.raises(AssertionError, match="no message template"):
        messages.render(RageError("not-a-real-code"))


def test_a_read_only_refusal_still_names_the_key_that_was_asked_for(tmp_path):
    """Raised at the boundary, so it was already right; kept so it stays right."""
    with SqliteStore(tmp_path / "root") as root, SqliteStore(tmp_path / "ref") as ref:
        with Mounts({"": root, "ref": ref}, read_only=["ref"]) as table:
            with pytest.raises(ReadOnlyMountError) as raised:
                table.resolve("ref/x").writable()
    assert "cannot write 'ref/x'" in messages.render(raised.value)
