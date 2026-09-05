"""The note side of the wording layer, and the five things that keep it honest.

The rule these guard is the one ``test_messages.py`` guards for errors -- **the
library layers carry facts, the wording tables write sentences** -- plus one
the error side does not need and cannot have:

    **Silence must be deliberate.** A note code an audience has no sentence for
    is a failure, unless that audience has said with a reason that it means to
    say nothing.

An error must always be reported, so there is no such thing as an audience that
declines to mention one. A note is optional by nature: the command line is
expected to start out saying almost none of them. Without this guard "quiet for
now" and "nobody ever looked" are the same empty table, and the first decays
into the second with nothing to notice. With it, adding a note code forces a
one-line decision per front end, and an audience's silences are a readable list
of what it has chosen not to say.

Like ``test_messages.py`` these are rules about where code lives, so they are
checked by reading the source: a note emitted tomorrow with its sentence baked
in should fail here rather than reach a reader in whatever shape it was written.

**Nothing emits a note yet**, which is the point of landing this first -- no
caller is moved, so nothing can regress. The guards over the real tree are
therefore vacuous today and would stay silent if they were wrong, so each one's
decision is a function tested below against tables built by hand. That is what
this step is for: finding out whether the guards are workable before any
sentence depends on them.
"""

from __future__ import annotations

import ast
import importlib
import pathlib

import pytest

import outrage
from outrage import keys
from outrage.messages import NoteTable
from outrage.notes import Note

SOURCE = pathlib.Path(outrage.__file__).parent

MODULES = sorted(path.stem for path in SOURCE.glob("*.py") if not path.stem.startswith("_"))


def _audiences() -> list[NoteTable]:
    """Every note table the package defines, found rather than listed.

    A list here would be a second place to remember an audience, and the way it
    fails is silent: a table missing from it is checked by nothing, which is
    exactly the state the guards exist to make impossible. Found by identity so
    that a table re-exported by its front end is one audience, not two.
    """
    tables: dict[int, NoteTable] = {}
    for module in MODULES:
        for value in vars(importlib.import_module(f"outrage.{module}")).values():
            if isinstance(value, NoteTable):
                tables.setdefault(id(value), value)
    return sorted(tables.values(), key=lambda table: table.audience)


AUDIENCES = _audiences()


def _emits() -> list[tuple[str, int, ast.Call]]:
    """Every ``Note(...)`` built in the package, with where it is."""
    found = []
    for path in sorted(SOURCE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if getattr(node.func, "id", getattr(node.func, "attr", None)) == "Note":
                found.append((path.name, node.lineno, node))
    return found


def _emitted_codes() -> set[str]:
    return {
        call.args[0].value
        for _, _, call in _emits()
        if call.args and isinstance(call.args[0], ast.Constant)
    }


#: Stand-in details by shape rather than by meaning, as ``test_messages.py``
#: does it: a count has to survive arithmetic and a plural has to be iterable,
#: and nothing here is about what the value would really be. Both start empty
#: because nothing emits a note yet; a note whose detail is counted or listed
#: adds its name here rather than teaching the guard about its meaning.
_COUNTS: set[str] = set()
_PLURALS: set[str] = set()


def _stand_in(detail: str) -> object:
    if detail in _COUNTS:
        return 1
    if detail in _PLURALS:
        return ["a"]
    return "a"


# -- what each guard decides, as a function so it can be shown to bite --------
#
# The four guards below are vacuous over today's tree, and a guard that cannot
# fail is a guard nobody has tested. Each one's decision lives in a function
# here, the test over the real tree calls it, and a test further down calls the
# same function with tables built by hand and checks it says so.


def _codes_no_audience_says(emitted: set[str], audiences: list[NoteTable]) -> set[str]:
    """Codes something emits that every audience is silent about, or has no entry for.

    Not the same as being silent in one place. A note nobody words anywhere is
    heard by nobody, so the work of noticing the situation is spent for nothing
    -- either a table should say it or the emit site should go.
    """
    said: set[str] = set()
    for table in audiences:
        said |= set(table.sentences())
    return emitted - said


def _entries_nothing_emits(emitted: set[str], audiences: list[NoteTable]) -> dict[str, set[str]]:
    """Per audience, the entries -- sentences and silences alike -- that are stale.

    A silence counts. "We do not mention that" about a situation that can no
    longer arise is as much a stale claim as a sentence nothing can produce,
    and it is the more misleading of the two because it reads as a decision.
    """
    stale = {}
    for table in audiences:
        left = (set(table.sentences()) | set(table.silences())) - emitted
        if left:
            stale[table.audience] = left
    return stale


def _codes_neither_said_nor_silent(
    emitted: set[str], audiences: list[NoteTable]
) -> dict[str, set[str]]:
    """Per audience, the emitted codes it has made no decision about at all.

    The invented guard, and the one the command line's deliberate quiet depends
    on: an audience with nothing to say has to say so.
    """
    missing = {}
    for table in audiences:
        left = emitted - set(table.sentences()) - set(table.silences())
        if left:
            missing[table.audience] = left
    return missing


# -- the guards over the real tree -------------------------------------------


def test_a_note_table_is_defined_somewhere_to_be_guarded():
    """Otherwise every guard below passes by finding nothing to check.

    The discovery is by import and isinstance, so a wording module nobody
    imports is a wording module these tests never see.
    """
    assert AUDIENCES, "no NoteTable found in the package; the guards below check nothing"


def test_every_emit_names_a_code_that_is_a_literal():
    """A computed code is a code no table can be checked against."""
    for filename, lineno, call in _emits():
        assert call.args, f"{filename}:{lineno} builds a Note without a code"
        first = call.args[0]
        assert isinstance(first, ast.Constant) and isinstance(first.value, str), (
            f"{filename}:{lineno} passes a computed first argument; "
            f"a code must be a literal so this test can find it"
        )


def test_no_emit_site_composes_a_sentence():
    """The rule itself: facts go in, prose does not.

    An f-string as the code is the shape this catches, because it is what
    ``server.py``'s fourteen notes look like today and what writing a new one
    from memory would produce.
    """
    for filename, lineno, call in _emits():
        assert not isinstance(call.args[0], ast.JoinedStr), (
            f"{filename}:{lineno} builds its sentence where the situation was "
            f"found; pass a code and details, and put the wording in a table"
        )
        assert len(call.args) == 1, (
            f"{filename}:{lineno} passes more than a code positionally; "
            f"details are keyword arguments"
        )


def test_every_emitted_code_is_said_by_some_audience():
    unheard = _codes_no_audience_says(_emitted_codes(), AUDIENCES)
    assert not unheard, f"notes no audience ever says: {sorted(unheard)}"


def test_every_entry_in_a_table_is_emitted_somewhere():
    stale = _entries_nothing_emits(_emitted_codes(), AUDIENCES)
    assert not stale, f"entries for notes nothing emits: {stale}"


def test_every_code_is_either_said_or_explicitly_silent_per_audience():
    undecided = _codes_neither_said_nor_silent(_emitted_codes(), AUDIENCES)
    assert not undecided, (
        f"notes these audiences have made no decision about: {undecided}. "
        f"Give each a sentence, or call silent() with a reason"
    )


def test_every_template_renders_from_the_details_its_emit_site_passes():
    """Rendering must not be the thing that fails when nothing has gone wrong.

    Worse here than on the error side: this one runs on a *successful*
    operation, so a template reaching for a detail its emit site does not pass
    turns a write that worked into a traceback.
    """
    for filename, lineno, call in _emits():
        code = call.args[0].value
        details = {word.arg: _stand_in(word.arg) for word in call.keywords if word.arg}
        for table in AUDIENCES:
            if code not in table.sentences():
                continue
            rendered = table.render(Note(code, **details))
            assert isinstance(rendered, str) and rendered, (
                f"{filename}:{lineno} renders nothing for {table.audience}"
            )


# -- the machinery, on tables built by hand ----------------------------------


def _table() -> NoteTable:
    return NoteTable("a reader")


def test_a_table_words_a_note_from_its_details():
    table = _table()

    @table.template("shrank")
    def _shrank(name, /, *, previous, stored, **_):
        return f"the document shrank from {previous} to {stored} characters"

    assert table.render(Note("shrank", previous=90, stored=0)) == (
        "the document shrank from 90 to 0 characters"
    )


def test_a_silent_code_renders_as_nothing_rather_than_as_a_sentence():
    table = _table()
    table.silent("shrank", "the command line already prints both sizes")

    assert table.render(Note("shrank", previous=90, stored=0)) is None
    assert table.silences() == {"shrank": "the command line already prints both sizes"}


def test_silence_needs_a_reason():
    """An empty reason is the state the guard exists to distinguish."""
    with pytest.raises(AssertionError, match="for no stated reason"):
        _table().silent("shrank", "")


def test_a_code_a_table_has_never_heard_of_raises_rather_than_going_quiet():
    """The one place ``None`` would be the wrong answer.

    Returning nothing would make an unregistered code and a deliberate silence
    identical at runtime, which is the whole distinction the table keeps.
    """
    with pytest.raises(AssertionError, match="has no wording for note 'shrank'"):
        _table().render(Note("shrank"))


def test_a_code_cannot_have_two_entries_in_one_table():
    """Including one of each kind: saying it and not saying it are not both true."""
    table = _table()
    table.silent("shrank", "not written yet")

    with pytest.raises(AssertionError, match="already has an entry"):
        table.template("shrank")(lambda name, /, **_: "x")
    with pytest.raises(AssertionError, match="already has an entry"):
        table.silent("shrank", "still not written")


def test_the_namer_reaches_a_note_the_way_it_reaches_an_error():
    """A note names a key for whoever is reading, exactly as an error does.

    ``_note_check`` in ``server.py`` hardcodes ``keys.displayed`` today, which
    is the latent form of the defect the error side already fixed: harmless
    only because one front end uses it. The default here is the same answer,
    for a reader who has not said they are somewhere else.
    """
    table = _table()

    @table.template("unchecked")
    def _unchecked(name, /, *, key, **_):
        return f"the write to {name(key)!r} was not checked"

    note = Note("unchecked", key=keys.ROOT)
    assert table.render(note) == "the write to '/' was not checked"
    assert table.render(note, name=lambda key: f"ref/{key}") == (
        "the write to 'ref/' was not checked"
    )


def test_a_detail_may_be_called_name():
    """Which is why the namer is positional-only, as it is for an error."""
    table = _table()

    @table.template("mount")
    def _mount(namer, /, *, name, **_):
        return f"stopped at the mount {name!r}"

    assert table.render(Note("mount", name="ref")) == "stopped at the mount 'ref'"


def test_a_table_hands_out_copies_rather_than_its_own_tables():
    table = _table()
    table.silent("shrank", "not written yet")

    table.sentences()["invented"] = lambda name, /, **_: "x"
    table.silences()["invented"] = "x"

    assert table.render(Note("shrank")) is None
    with pytest.raises(AssertionError, match="has no wording"):
        table.render(Note("invented"))


# -- the guards, shown to bite -----------------------------------------------


def _said(audience: str, *codes: str) -> NoteTable:
    table = NoteTable(audience)
    for code in codes:
        table.template(code)(lambda name, /, **_: "something")
    return table


def test_a_note_every_audience_is_quiet_about_is_reported_as_unheard():
    """Silent everywhere is not the same as silent here: nobody is ever told."""
    quiet = NoteTable("the command line")
    quiet.silent("shrank", "not written yet")
    tools = NoteTable("the MCP tools")
    tools.silent("shrank", "not written yet either")

    assert _codes_no_audience_says({"shrank"}, [quiet, tools]) == {"shrank"}
    assert _codes_no_audience_says({"shrank"}, [_said("the MCP tools", "shrank"), quiet]) == set()


def test_an_entry_for_a_note_nothing_emits_is_reported_per_audience():
    tools = _said("the MCP tools", "shrank", "gone")
    line = NoteTable("the command line")
    line.silent("gone", "nobody has decided what this should say")

    stale = _entries_nothing_emits({"shrank"}, [line, tools])
    assert stale == {"the MCP tools": {"gone"}, "the command line": {"gone"}}


def test_a_note_an_audience_has_not_decided_about_is_reported():
    """The invented guard, which is the one this step exists to try out."""
    tools = _said("the MCP tools", "shrank")
    line = NoteTable("the command line")

    assert _codes_neither_said_nor_silent({"shrank"}, [tools, line]) == {
        "the command line": {"shrank"}
    }

    line.silent("shrank", "the command line prints both sizes already")
    assert _codes_neither_said_nor_silent({"shrank"}, [tools, line]) == {}


def test_a_template_reaching_for_a_detail_its_emit_site_does_not_pass_fails():
    """What the render guard catches, on a table where it can actually happen."""
    table = _table()

    @table.template("shrank")
    def _shrank(name, /, *, previous, stored, **_):
        return f"the document shrank from {previous} to {stored} characters"

    with pytest.raises(TypeError):
        table.render(Note("shrank", previous=90))
