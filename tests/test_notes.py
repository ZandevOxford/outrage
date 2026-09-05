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

The guards over the real tree were vacuous when they were written, because
nothing emitted a note yet -- and a guard that cannot fail is a guard nobody
has tested. So each one's decision is a function, called both by the test over
the real tree and by a test further down that hands it tables built by hand and
checks it says what it should. They bite over the tree now that every note the
tools give lives here, and the hand-built cases stay: what they check is the
decision, which is the part that would go on passing while the tree changed
under it.
"""

from __future__ import annotations

import ast
import importlib
import pathlib
import re

import pytest

import outrage
from conftest import long_options
from outrage import bulk, cli, cli_messages, keys, messages
from outrage.messages import NoteTable
from outrage.mounts import Mount
from outrage.notes import UNCHECKED_NO_RECORD, UNCHECKED_OTHER_KEY, Note
from outrage.store import OVERWRITE, SKIP
from outrage.store_sqlite import SqliteStore

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
#: and nothing here is about what the value would really be. A note whose
#: detail is counted or listed adds its name here rather than teaching the
#: guard anything about what it means.
_COUNTS = {"failed", "limit", "named", "previous", "remaining", "stored"}
_PLURALS = {"changed", "mounts"}


def _stand_in(detail: str) -> object:
    if detail in _COUNTS:
        return 1
    if detail in _PLURALS:
        return ["a"]
    return "a"


# -- what each guard decides, as a function so it can be shown to bite --------
#
# A guard that cannot fail is a guard nobody has tested, and these were all
# vacuous the day they were written. Each one's decision lives in a function
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
    every one of these notes looked like when they were built in ``server.py``,
    and what writing a new one from memory would produce.
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


# -- what an import has to remark on -----------------------------------------
#
# `bulk.notes_for` is the derivation layer: it decides which situations arose,
# and the table above decides how this reader hears them. These tests read the
# answer's own fields and the answer's own prose in one place and require them
# to agree, which is the shape that would have caught all three of the
# 2026-09-02 defects and did not exist to.


@pytest.fixture
def store(tmp_path):
    with SqliteStore(tmp_path / "store") as opened:
        yield opened


def _imported(**fields) -> bulk.Imported:
    """An import result, with only the fields a test is about spelled out."""
    return bulk.Imported(**({"key": "a", "stored": 10, "previous": None} | fields))


def _heard(imported: bulk.Imported) -> str:
    """Everything the MCP tools would say about ``imported``, as one string."""
    return " ".join(messages.MCP.render(note) for note in bulk.notes_for(imported))


def test_a_verbatim_cross_key_copy_is_not_called_a_no_op(store, tmp_path):
    """The purest of the seven, driven through the real import rather than by hand.

    The library's `unedited` was right and pinned by a test; the sentence built
    on it turned a true claim about *bytes* into a false claim about the write.
    So this asserts the answer's own numbers disagree with a no-op, and then
    that nothing said beside them claims one.
    """
    store.store_document("a", "# The source, which is longer")
    store.store_document("b", "# short")
    source = bulk.export_document(store, "a", tmp_path / "export")
    target = bulk.export_document(store, "b", tmp_path / "export")

    imported = bulk.import_document(
        store, "b", source.path, tmp_path / "export", against=target.path
    )

    assert imported.unedited and imported.copied_from == "a"
    assert imported.previous != imported.stored, "the document at 'b' did change"

    codes = [note.code for note in bulk.notes_for(imported)]
    assert "stored-a-copy" in codes
    assert "edit-matched-nothing" not in codes

    said = _heard(imported)
    assert "the edit changed nothing" not in said
    assert "exported from 'a'" in said


def test_a_clean_round_trip_that_matched_nothing_still_says_so(store, tmp_path):
    """The other half of the same flag: here the file and the write agree."""
    store.store_document("a", "# The document")
    exported = bulk.export_document(store, "a", tmp_path / "export")

    imported = bulk.import_document(store, "a", exported.path, tmp_path / "export")

    assert imported.unedited and imported.copied_from is None
    assert [note.code for note in bulk.notes_for(imported)] == ["edit-matched-nothing"]
    assert "the edit changed nothing" in _heard(imported)


def test_a_write_that_changed_the_document_has_nothing_to_remark_on(store, tmp_path):
    """Silence is the common case, and it comes from there being no situation.

    Worth pinning separately from the guard about *deliberate* silence: this
    one is the derivation finding nothing, which is what should happen on
    almost every write.
    """
    store.store_document("a", "# The document")
    exported = bulk.export_document(store, "a", tmp_path / "export")
    (tmp_path / "export" / exported.path.name).write_text("# The document, edited and longer")

    imported = bulk.import_document(store, "a", exported.path, tmp_path / "export")

    assert bulk.notes_for(imported) == []


def test_the_sentence_about_a_shrink_carries_the_answer_s_own_numbers():
    """Restatement is the first of the three kinds, and the cheapest to check."""
    imported = _imported(stored=0, previous=90)

    (note,) = bulk.notes_for(imported)
    assert note == Note("document-shrank", previous=90, stored=0)
    assert f"from {imported.previous} to {imported.stored} characters" in _heard(imported)


def test_a_note_names_a_key_the_way_the_reader_would_name_it():
    """What `server.py`'s `_note_check` could not do: it hardcoded one spelling.

    Harmless while one front end used it, and wrong the moment the key is
    inside a mounted store -- the same defect the namer was built for on the
    error side, one layer down.
    """
    note, *_ = bulk.notes_for(_imported(unchecked_code=UNCHECKED_NO_RECORD))

    assert "'a'" in messages.MCP.render(note)
    assert "'ref/a'" in messages.MCP.render(note, name=Mount(prefix="ref", store=None).outer)


def test_what_a_write_destroyed_is_said_before_what_it_stored():
    """The order is not arbitrary: the first is the one somebody has to act on."""
    imported = _imported(
        stored=0,
        previous=90,
        overwritten=True,
        changed_at="2026-09-05T10:00:00+00:00",
        unchecked_code=UNCHECKED_NO_RECORD,
    )

    assert [note.code for note in bulk.notes_for(imported)] == [
        "overwrote-a-change",
        "write-not-checked",
        "document-shrank",
    ]


def test_every_note_the_import_path_can_produce_is_worded():
    """The guards say this over the tree; this says it over one operation.

    A situation the derivation can reach and no audience says is a situation
    nobody is ever told about, and the tree guard only notices because the code
    is a literal somewhere. Here the codes come from running the derivation.
    """
    reached = {
        note.code
        for imported in [
            _imported(overwritten=True, changed_at="2026-09-05T10:00:00+00:00"),
            _imported(unchecked_code=UNCHECKED_NO_RECORD),
            _imported(unedited=True),
            _imported(unedited=True, copied_from="a"),
            _imported(stored=0, previous=90),
        ]
        for note in bulk.notes_for(imported)
    }

    assert reached <= set(messages.MCP.sentences())


# -- what a delete, a copy and an export have to remark on -------------------
#
# The same shape as the import tests above: the answer's own fields and the
# answer's own prose read in one place, and required to agree. What these three
# have in common is that every note is about a call that did *less* than it was
# asked -- the counts describe what happened, and nothing in them describes
# what did not.


def _words(notes: list[Note]) -> str:
    """Everything the MCP tools would say about ``notes``, as one string."""
    return " ".join(said for note in notes if (said := messages.MCP.render(note)) is not None)


def _deleted(**facts) -> list[Note]:
    """A delete's notes, with only the facts a test is about spelled out."""
    return bulk.notes_for_delete(
        **({"key": "a", "dry_run": False, "remaining": 0, "mounts_kept": []} | facts)
    )


def _copied(**facts) -> list[Note]:
    """A copy's, likewise. Every default is the call that did all of it."""
    return bulk.notes_for_copy(
        **(
            {
                "landing": "a",
                "dry_run": False,
                "on_conflict": SKIP,
                "unchanged_since": None,
                "changed": [],
                "next_cursor": None,
                "limit": 100,
                "failed": 0,
                "named": 0,
                "stopped": False,
                "mounts_kept": [],
            }
            | facts
        )
    )


def test_a_delete_that_took_all_of_it_has_nothing_to_remark_on():
    assert _deleted() == []


def test_the_keys_a_delete_kept_back_are_counted_in_the_sentence_about_them():
    notes = _deleted(remaining=12)

    assert notes == [Note("keys-kept-below", key="a", remaining=12, dry_run=False)]
    assert "12 key(s) below 'a'" in _words(notes)


def test_a_dry_run_says_what_would_be_kept_rather_than_what_was():
    """One situation in two tenses, which is why ``dry_run`` is a detail.

    Nothing was kept back by a dry run, because nothing was deleted. The
    sentence has to be about the delete it is describing rather than about the
    call that produced it.
    """
    assert "would be kept" in _words(_deleted(remaining=1, dry_run=True))
    assert "were kept" in _words(_deleted(remaining=1))


def test_the_mounts_a_delete_could_not_reach_are_both_counted_and_named():
    """Counted because a caller reads the number, named because it has to act."""
    said = _words(_deleted(mounts_kept=["ref", "docs"]))

    assert "2 read-only mounted store(s) below 'a'" in said
    assert "'ref', 'docs'" in said


def test_a_delete_says_what_it_did_not_do_before_what_it_could_not_do():
    assert [note.code for note in _deleted(dry_run=True, remaining=1, mounts_kept=["ref"])] == [
        "delete-was-a-dry-run",
        "keys-kept-below",
        "mounts-refused-delete",
    ]


def test_a_copy_that_did_all_of_it_has_nothing_to_remark_on():
    assert _copied() == []


def test_the_advice_after_a_dry_run_names_a_conflict_rule_that_takes_a_watermark():
    """`overwrite` beside a watermark is the pairing ``bulk`` refuses.

    So the advice to hand the moment back is only followable under the narrowed
    rule, and unconditional it recommended the call that fails. The situation is
    one note; which rule was asked for is a detail the table words.
    """
    assert "unchanged_since with on_conflict='overwrite-unchanged'" in _words(
        _copied(dry_run=True, on_conflict=OVERWRITE)
    )
    assert "overwrite-unchanged" not in _words(_copied(dry_run=True, on_conflict=SKIP))


def test_a_paged_copy_is_warned_about_the_watermark_only_when_it_has_one():
    """The two halves contradicted each other before they were one sentence.

    A copy carries the source's timestamps, so the page just written is itself
    a change to the target whenever the source is newer -- and a caller told to
    call again with every argument unchanged would be refused by the check they
    were told to keep.
    """
    paged = _words(_copied(next_cursor="a/b", limit=50))
    guarded = _words(_copied(next_cursor="a/b", limit=50, unchanged_since="2026-09-05T10:00:00Z"))

    assert "The limit of 50 stopped this call" in paged
    assert "Except unchanged_since" not in paged
    assert "Except unchanged_since" in guarded


def test_a_sample_of_failures_says_which_of_the_two_numbers_is_the_list():
    """A sample presented as a list is a list that lies, and only sometimes."""
    assert "9 document(s) failed and the first 3 are named" in _words(_copied(failed=9, named=3))
    assert _copied(failed=3, named=3) == [], "nothing is a sample when all of it is named"


def test_the_keys_a_watermark_left_alone_are_counted_against_the_moment():
    said = _words(_copied(changed=["a/b", "a/c"], unchanged_since="2026-09-05T10:00:00Z"))

    assert "2 key(s) changed since '2026-09-05T10:00:00Z'" in said


def test_a_copy_names_a_refusing_mount_the_way_the_reader_would_name_it():
    """The landing key is a key in the reader's namespace, so it is spelled for one.

    The delete's is the caller's own spelling handed back, which needs nothing;
    this one is worked out from the target and a graft, and a reader inside a
    mounted store calls it something longer.
    """
    (note,) = _copied(mounts_kept=["ref"])

    assert "below 'a'" in messages.MCP.render(note)
    assert "below 'ref/a'" in messages.MCP.render(note, name=Mount(prefix="ref", store=None).outer)


def test_a_copy_reports_what_it_did_not_do_in_the_order_a_reader_meets_it():
    """What did not happen at all, what was left behind, where to carry on."""
    everything = _copied(
        dry_run=True,
        unchanged_since="2026-09-05T10:00:00Z",
        changed=["a/b"],
        next_cursor="a/c",
        failed=9,
        named=3,
        stopped=True,
        mounts_kept=["ref"],
    )

    assert [note.code for note in everything] == [
        "copy-was-a-dry-run",
        "keys-changed-since",
        "copy-stopped-at-limit",
        "failures-sampled",
        "copy-stopped-at-conflict",
        "mounts-refused-write",
    ]


def test_an_export_says_what_the_file_it_handed_over_is_for(store, tmp_path):
    """The one note that is not a discovery: what matters is what happens next.

    Driven through the real export rather than built by hand, because the point
    of the note is that a file was written and the caller is expected to come
    back with it.
    """
    store.store_document("a", "# The document")
    exported = bulk.export_document(store, "a", tmp_path / "export")

    assert exported.path.exists()
    assert "call again with its path" in _words(bulk.notes_for_export(exported))


def test_every_note_the_tools_can_reach_is_worded_and_nothing_they_word_is_stranded(
    store, tmp_path
):
    """The strong form of the two tree guards, over situations rather than source.

    The guards read the package and ask whether a code written down somewhere
    is worded and whether a worded code is written down somewhere. Neither can
    tell that a situation is *reachable*: an emit site behind a condition that
    can no longer hold passes both. Here the codes come from running every
    derivation over every situation it has, so an entry the library can no
    longer arrive at is stranded and this says so.
    """
    store.store_document("a", "# The document")

    reached = {
        note.code
        for notes in [
            bulk.notes_for(_imported(overwritten=True, changed_at="2026-09-05T10:00:00Z")),
            bulk.notes_for(_imported(unchecked_code=UNCHECKED_NO_RECORD)),
            bulk.notes_for(_imported(unedited=True)),
            bulk.notes_for(_imported(unedited=True, copied_from="a")),
            bulk.notes_for(_imported(stored=0, previous=90)),
            # `notes_for_checked_write` is not here: it shares its situations
            # with the import path above and reaches no code of its own.
            bulk.notes_for_export(bulk.export_document(store, "a", tmp_path / "export")),
            _deleted(dry_run=True, remaining=1, mounts_kept=["ref"]),
            _copied(
                dry_run=True,
                unchanged_since="2026-09-05T10:00:00Z",
                changed=["a/b"],
                next_cursor="a/c",
                failed=9,
                named=3,
                stopped=True,
                mounts_kept=["ref"],
            ),
        ]
        for note in notes
    }

    assert reached == set(messages.MCP.sentences())


# -- the second audience -----------------------------------------------------
#
# What `cli_messages` is for: the same situations, a different selection. These
# are about the selection itself, which is the axis the note side has and the
# error side does not.


def test_the_command_line_says_less_than_the_tools_and_says_why():
    """The design's call, as a fact about the tables rather than a claim in prose.

    Not an assertion that the command line is *right* to be quiet -- that is
    the reason on each silence, and a person reads those. What this pins is
    that quiet is a decision it made: every code it does not word, it has
    declined by name.
    """
    tools = set(messages.MCP.sentences())
    line = set(cli_messages.CLI.sentences())

    assert line < tools, "the command line is expected to say fewer of them, not more"
    assert set(cli_messages.CLI.silences()) == tools - line
    assert all(cli_messages.CLI.silences().values()), "a silence without a reason"


def test_the_command_line_only_names_flags_somebody_can_type():
    """The note side of what ``test_messages`` guards for errors.

    There the danger is a speller reaching for an argument only the tools take;
    here it is a template writing a flag out by hand, which is what a table
    with no speller is *for*. The failure looks the same to a reader: advice
    naming something that is not on the command line at all.
    """
    options = long_options(cli.argument_parser())

    named = []
    for code, write in cli_messages.CLI.sentences().items():
        details = {name: _stand_in(name) for name in _details_of(code)}
        said = write(keys.displayed, **details)
        for word in re.findall(r"--[a-z][a-z-]*", said):
            named.append(word)
            assert word in options, f"the note {code!r} names {word}, which is not an option"

    # Otherwise a table that stopped naming flags would pass by checking
    # nothing, which is how a guard quietly stops working.
    assert named, "no note named a flag, so this checked nothing"


def _details_of(code: str) -> set[str]:
    """Every detail name an emit site passes with ``code``, read from the source."""
    return {
        word.arg
        for _, _, call in _emits()
        if call.args and getattr(call.args[0], "value", None) == code
        for word in call.keywords
        if word.arg
    }


def test_the_command_line_says_a_shrink_in_its_own_words():
    """The one note it wants more than the tools do, and the numbers are the point."""
    (note,) = bulk.notes_for_write(90, 0)

    assert note == Note("document-shrank", previous=90, stored=0)
    assert "shrank from 90 to 0 characters" in cli_messages.CLI.render(note)


def test_a_write_that_grew_says_nothing_at_either_end():
    assert bulk.notes_for_write(0, 90) == []
    assert bulk.notes_for_write(None, 90) == [], "an unknown previous size is not a shrink"


def test_the_command_line_names_a_refusing_mount_with_its_own_flags():
    """`--recursive` and `--mount-ro`, where the tools' table writes `recursive=true`.

    The whole of what a table per audience buys, in one sentence: nobody has
    to parameterise a flag, because the table already knows who is reading.
    """
    (note,) = bulk.notes_for_delete("a", dry_run=False, remaining=0, mounts_kept=["ref"])
    said = cli_messages.CLI.render(note)

    assert "--recursive" in said and "--mount-ro" in said
    assert "recursive=true" not in said


def test_the_reason_a_write_was_unchecked_is_a_code_by_the_time_a_table_sees_it():
    """Step 5's leak, closed: the parenthesis used to be built in ``bulk``.

    A reader was handed *"not checked against the document (exported from
    'a')"* with the inner half written where no front end could respell it --
    the wording layer's own defect, one level down. Now the note carries the
    code and the key, and each table writes the reason.
    """
    (note,) = bulk.notes_for(_imported(unchecked_code=UNCHECKED_OTHER_KEY, unchecked_from="a"))

    assert note == Note("write-not-checked", key="a", why=UNCHECKED_OTHER_KEY, came_from="a")
    assert "no export record" not in str(note), "the sentence is not in the note"
    assert "(exported from 'a')" in messages.MCP.render(note)


def test_a_write_with_no_record_and_one_from_another_key_read_differently():
    """Two situations behind one flag, which is why the reason is a code at all."""
    (missing,) = bulk.notes_for(_imported(unchecked_code=UNCHECKED_NO_RECORD))
    (other,) = bulk.notes_for(_imported(unchecked_code=UNCHECKED_OTHER_KEY, unchecked_from="b"))

    assert "(no export record)" in messages.MCP.render(missing)
    assert "(exported from 'b')" in messages.MCP.render(other)


def test_the_prose_field_still_says_what_it_always_said():
    """``unchecked`` is public prose and dated; until it goes, it does not move.

    Derived from the code now rather than built where the reason is found, so
    the field and the note cannot come to disagree while both are readable.
    """
    assert bulk.unchecked_prose(UNCHECKED_NO_RECORD, None) == "no export record"
    assert bulk.unchecked_prose(UNCHECKED_OTHER_KEY, "project") == "exported from 'project'"
