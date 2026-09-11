"""Turning what the library carries into a sentence for a person.

Two kinds of thing reach a reader as prose, and both arrive here as a code and
its facts rather than as words. A **failure** is an
:class:`~outrage.errors.OutrageError`, raised by the layer that hit it. A
**note** is a :class:`~outrage.notes.Note` on an answer that *worked* -- the
document shrank, the write went past a check nobody could make -- carried on
the result object, because a success path has nothing to raise. Neither is
worded where it was found.

**Why the naming is a parameter.** There are two front ends and the right name
for a key differs between them. The command line opens one store directory and
knows nothing about a mount table, so a key it failed on is called exactly what
the store calls it. The MCP server presents one namespace across several
stores, so the same key has a longer name there -- ``python/nope`` inside the
store mounted at ``ref`` is ``ref/python/nope`` to any caller. A sentence built
where the failure happened is wrong for one of them and there is no third
answer. That was a live defect, not a hypothetical one.

So ``name`` is a function from the key the raising layer used to the key the
reader should see. It defaults to :func:`outrage.keys.displayed`, which is the
right answer for a single store and spells the root ``/`` rather than as the
empty string that reads like a missing value.

An **error's** wording is shared rather than written per front end. Two copies
of the same sentence drift, and the drift is invisible until somebody compares
them.

A **note's** wording is not shared, and the difference is deliberate. Each
audience gets a table of its own -- :data:`MCP` below is the tools' -- because
two front ends should remark on *different* situations and one of them should
often say nothing at all. A front end wanting its own selection brings its own
table rather than a branch inside a template here. So this file is the one
place an error's wording lives, and one of the places a note's does.

The next reader will want to unify the two mechanisms. The reason not to:

    An error **must always be reported**. Whoever catches it has to say
    something, so silence is not an option and only the spelling varies --
    hence one table, and :data:`Speller` for the words that differ between
    readers. A note is **optional by nature**, so *which* notes are said is
    the primary question and the wording is secondary -- hence a table per
    audience, and no speller, because the table already is the audience: a
    command line's note writes ``--unchanged-since`` itself.

Different problems, different shapes.

**Where the advice varies and the spelling does not.** The argument above rests
on only the spelling varying between readers, and there is one place it does
not: a store mounted read-only is remounted by an MCP caller with the ``mount``
tool and by an operator with ``--mount`` at startup, which are two remedies and
not two spellings of one. **The rule, John's call of 2026-09-06: a message
never tells a reader to do something they cannot. Where the remedy differs,
name each of them and say whose it is** -- in the one shared sentence, with no
mechanism for it.

Considered and not taken: a third parameter beside :data:`Namer` and
:data:`Speller` supplying the remedy, and splitting the fact from the advice
into a table per audience the way notes are split. Both are contained changes
and either is still open. The reason for neither *yet* is that there is one
case: of the five templates naming a server startup flag, four have a single
remedy that simply belongs to an operator, and only ``mount-read-only`` has
two. **Revisit when there is a second genuine two-remedy case, or a third front
end** -- at which point the rule below stops being enough, because nothing
enforces it.

Note the shape of the mistake this replaced, since it is easy to make again:
a sentence naming ``--mount-ro`` is not *misspelled* for a tool caller, it is
addressed to somebody else. A speller cannot help, and reaching for one is how
the wrong fix gets built.

What makes the note side safe is the guard in ``tests/test_notes.py`` that the
error side does not need: **silence must be deliberate.** A code an audience
has no sentence for is a failure unless that audience has said, with a reason,
that it means to be quiet about it -- otherwise "this front end is quiet for
now" decays into permanent silence by neglect and nothing ever notices.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import keys
from .errors import OutrageError
from .notes import UNCHECKED_NO_RECORD, Note

# The conflict rules by their constants rather than as literals: a message that
# tells a caller to pass `overwrite-unchanged` is a second place the value is
# written down, and a rename that misses one leaves the sentence naming a
# spelling nothing accepts.
from .store import OVERWRITE, OVERWRITE_UNCHANGED

#: How a key is named when nobody says otherwise: as one store sees it.
Namer = Callable[[str], str]

#: How an *argument* is spelled where the message will be read, and the second
#: half of the same rule :data:`Namer` is the first half of. A key is called
#: something different behind a mount; an argument is called something
#: different at each front end -- ``unchanged_since`` to a tool call and
#: ``--unchanged-since`` to a shell -- and a sentence naming one of them in the
#: other's spelling tells its reader to type something that does not exist.
#: Live testing found exactly that: a command line user told to "Pass
#: on_conflict='overwrite-unchanged'", which is not a flag.
#:
#: Called with the argument's name, and its value where naming the value is
#: what the sentence is about.
Speller = Callable[..., str]

#: Every code, and the sentence it renders to. One flat table keyed by code
#: rather than by exception class, because the class says what *kind* of
#: failure it is and the code says which one -- nine different things are an
#: ``InvalidKeyError`` and each has its own explanation.
#:
#: Each entry takes the namer **positionally** and the details by keyword.
#: Positional-only for the namer is what lets a detail be called ``name`` --
#: ``assets-missing`` has one -- without colliding with it. Missing a detail raises
#: ``KeyError`` here, loudly, rather than rendering a sentence with a hole in
#: it, and ``test_messages.py`` pins that every code raised anywhere has an
#: entry and every entry is raised somewhere.
_TEMPLATES: dict[str, Callable[..., str]] = {}


def template(code: str) -> Callable[[Callable[..., str]], Callable[..., str]]:
    """Register the sentence for ``code``."""

    def register(function: Callable[..., str]) -> Callable[..., str]:
        if code in _TEMPLATES:  # pragma: no cover - a duplicate is a bug, not a case
            raise AssertionError(f"two templates for {code!r}")
        _TEMPLATES[code] = function
        return function

    return register


def keyword(argument: str, value: Any = None) -> str:
    """An argument as a keyword call writes it: what an MCP tool is passed.

    The default, because it is the spelling a library's own argument already
    has -- a sentence naming ``unchanged_since`` is right for anything calling
    Python or the tools, and only a front end whose arguments are spelled some
    other way has to say so.
    """
    return argument if value is None else f"{argument}={value!r}"


def flag(argument: str, value: Any = None) -> str:
    """An argument as a command line writes it: what a person types in a shell.

    ``argparse``'s own convention read backwards: a ``dest`` is its long option
    with the dashes turned into underscores, so the way back is mechanical. It
    is a rule rather than a table because a table is a second place to remember
    a flag, and ``test_messages`` keeps the rule honest by checking every flag a
    message can produce against the parser's own options -- inventing
    ``--against`` for an argument only the tools take would be this same defect
    one level down.

    The defect it exists for: a message spelled for the tools told a command
    line user to "Pass on_conflict='overwrite-unchanged'", which is not
    something anyone can type.

    Here beside :func:`keyword` rather than in :mod:`outrage.cli`, where it was
    written, because two front ends spell flags: the command line, and
    :func:`outrage.server.main`, whose refusals about a bad ``--mount`` go to an
    operator's stderr and not to a tool call.
    """
    written = f"--{argument.replace('_', '-')}"
    return written if value is None else f"{written} {value}"


def render(error: OutrageError, name: Namer | None = None, *, spell: Speller | None = None) -> str:
    """``error`` as one line, named the way ``name`` and ``spell`` say.

    Front ends call this; nothing else should. A code with no template is a
    programming error and raises rather than falling back on something
    plausible -- a message that silently degrades is how a caller ends up
    reading a sentence that is not about their problem.

    ``spell`` reaches a template as a keyword, so only the templates that name
    an argument declare it and the rest go on absorbing it in ``**_``. That is
    why no error detail may be called ``spell``, which ``test_messages`` pins.
    """
    try:
        write = _TEMPLATES[error.code]
    except KeyError:  # pragma: no cover - guarded by test_messages
        raise AssertionError(f"no message template for {error.code!r}") from None
    return write(name or keys.displayed, spell=spell or keyword, **error.details)


def codes() -> Mapping[str, Callable[..., str]]:
    """The whole table, for the test that checks it against the raise sites."""
    return dict(_TEMPLATES)


# -- notes on an answer that worked ---------------------------------------


class NoteTable:
    """What one audience is told about a :class:`~outrage.notes.Note`, if anything.

    A table per audience rather than one table spelled two ways, for the reason
    the module docstring gives: selection is the note side's primary question,
    and a template that branched on who is reading would be one function with
    two meanings -- the shape every message defect this project has had came
    out of, two readings agreeing the day they are written and drifting after.

    Two ways in, and a code must take exactly one of them. :meth:`template`
    says how this audience puts the situation; :meth:`silent` says that this
    audience means not to mention it, and why. A code with neither is the
    failure the guard exists for, because a table that may legitimately be
    quiet cannot otherwise tell a decision from an omission.

    The audience is the whole of the reader's identity here, so there is no
    speller: a table belonging to the command line writes ``--unchanged-since``
    into its own sentence, and nothing has to be parameterised for it.
    """

    def __init__(self, audience: str) -> None:
        #: Who this table words notes for, as a sentence would name them. It
        #: is only ever read by a failure -- here or in the guards -- so it is
        #: a phrase that can be read out in one, not an identifier.
        self.audience = audience
        self._templates: dict[str, Callable[..., str]] = {}
        self._silences: dict[str, str] = {}

    def template(self, code: str) -> Callable[[Callable[..., str]], Callable[..., str]]:
        """Register how this audience says ``code``.

        The function takes the namer **positionally** and the note's details by
        keyword, exactly as :func:`template` does above and for the same
        reason: a detail may be called ``name`` without colliding with it.
        """

        def register(function: Callable[..., str]) -> Callable[..., str]:
            self._claim(code)
            self._templates[code] = function
            return function

        return register

    def silent(self, code: str, reason: str) -> None:
        """Declare that this audience says nothing about ``code``, and why.

        The reason is required and is the point of the call. "Not written yet"
        is a legitimate one; what is not legitimate is the empty set entry that
        reads the same whether somebody decided or nobody looked.
        """
        if not reason:
            raise AssertionError(f"{self.audience} is silent about {code!r} for no stated reason")
        self._claim(code)
        self._silences[code] = reason

    def _claim(self, code: str) -> None:
        """Take ``code`` for this table, refusing a second entry for it."""
        if code in self._templates or code in self._silences:
            # A duplicate is a bug rather than a case: whichever of the two
            # loaded last would decide, silently, whether the reader hears it.
            raise AssertionError(f"{self.audience} already has an entry for note {code!r}")

    def render(self, note: Note, name: Namer | None = None) -> str | None:
        """``note`` as one line for this audience, or ``None`` where it is silent.

        ``None`` is a real answer -- this reader is not told -- and a caller
        drops it. A code this table has never heard of is not that: it raises,
        the way :func:`render` does for an error, because a note quietly lost
        for want of an entry is indistinguishable from one deliberately not
        said, which is the distinction the whole table exists to keep.
        """
        if note.code in self._silences:
            return None
        try:
            write = self._templates[note.code]
        except KeyError:
            raise AssertionError(
                f"{self.audience} has no wording for note {note.code!r} and has "
                f"not declared itself silent about it"
            ) from None
        return write(name or keys.displayed, **note.details)

    def sentences(self) -> Mapping[str, Callable[..., str]]:
        """The codes this audience has words for, for the guards that check them."""
        return dict(self._templates)

    def silences(self) -> Mapping[str, str]:
        """The codes it means not to mention, and why, for the same.

        Kept apart from :meth:`sentences` rather than merged into one table of
        codes, because the guards ask different questions of the two: a code
        nobody has words for anywhere is unreachable, while a code nobody has
        *decided* about is the neglect this design is guarding against.
        """
        return dict(self._silences)


#: What the MCP tools say about a note. The tools' spelling for an argument is
#: the library's own -- see :func:`keyword` -- so this table sits beside the
#: error wording both front ends share rather than in a module of its own.
#:
#: Its entries are the sentences ``server.py`` composed by hand until the notes
#: on one document write moved here; the wording is theirs, and the naming is
#: no longer fixed to one store, since a table renders for whoever is reading.
MCP = NoteTable("the MCP tools")


@MCP.template("overwrote-a-change")
def _overwrote_a_change(name: Namer, /, *, changed_at: str | None, **_: Any) -> str:
    return (
        f"the document had changed since it was exported and has been "
        f"overwritten anyway; what was written at {changed_at} is gone."
    )


@MCP.template("write-not-checked")
def _write_not_checked(
    name: Namer, /, *, key: str, why: str, came_from: str | None = None, **_: Any
) -> str:
    # The reason spelled here rather than handed over ready-made. It arrived as
    # prose from the library until the note layer reached it, which meant a
    # parenthesis written for these tools was put in front of whoever was
    # reading -- the command line included, where nothing could respell it.
    reason = (
        "no export record"
        if why == UNCHECKED_NO_RECORD
        else f"exported from {name(came_from or '')!r}"
    )
    return (
        f"this write was not checked against the document ({reason}), so "
        f"if somebody else had written {name(key)!r} since it was "
        f"exported, their work is now gone."
    )


@MCP.template("edit-matched-nothing")
def _edit_matched_nothing(name: Namer, /, **_: Any) -> str:
    return (
        "the file is identical to what was exported, so the edit changed "
        "nothing; if an edit was intended, it matched nothing."
    )


@MCP.template("stored-a-copy")
def _stored_a_copy(name: Namer, /, *, copied_from: str, **_: Any) -> str:
    # About the file, which is the only thing that did not move, and never
    # about the write: the document at this key did change, and `previous`
    # beside `stored` in the same answer says by how much.
    return (
        f"the file is unchanged since it was exported from "
        f"{name(copied_from)!r}, so this stored a copy of it as it came out; "
        f"if an edit was intended, it matched nothing."
    )


@MCP.template("document-shrank")
def _document_shrank(name: Namer, /, *, previous: int, stored: int, **_: Any) -> str:
    return (
        f"the document shrank from {previous} to {stored} characters; if "
        f"that was not intended, the previous content is gone."
    )


@MCP.template("exported-for-editing")
def _exported_for_editing(name: Namer, /, **_: Any) -> str:
    return "Edit this file in place and call again with its path to store it back."


@MCP.template("delete-was-a-dry-run")
def _delete_was_a_dry_run(name: Namer, /, **_: Any) -> str:
    return (
        "Nothing was deleted; `deleted` is what the delete would have "
        "taken. Pass checked_at back as unchanged_since to refuse the "
        "real delete if anything moves in between."
    )


@MCP.template("keys-kept-below")
def _keys_kept_below(name: Namer, /, *, key: str, remaining: int, dry_run: bool, **_: Any) -> str:
    return (
        f"{remaining} key(s) below {name(key)!r} "
        f"{'would be kept' if dry_run else 'were kept'}; "
        f"pass recursive=true to delete them too"
    )


def _remounting(mounts: Sequence[str], unwritable: Sequence[str], verb: str) -> str:
    """What a caller can do about the mounts a copy or a delete could not reach.

    Two answers, because a mount refuses for one of two reasons. One mounted
    read-only by choice opens to a remount, which is the caller's with the
    `mount` tool and an operator's at startup. A parquet or duckdb store refuses
    whatever it is mounted with, and advice to remount one costs a remount or a
    restart to find out is wrong.
    """
    flagged = [mount for mount in mounts if mount not in unwritable]
    said = []
    if flagged:
        said.append(
            f"Mount {', '.join(repr(mount) for mount in flagged)} again with "
            f"`mount` and `read_only` false to {verb} there too, where this "
            f"server offers that tool; otherwise it is a restart with --mount "
            f"rather than --mount-ro, which is an operator's to do."
        )
    if unwritable:
        one = len(unwritable) == 1
        said.append(
            f"{', '.join(repr(mount) for mount in unwritable)} cannot be written "
            f"however {'it is' if one else 'they are'} mounted, so no remount "
            f"reaches {'it' if one else 'them'}."
        )
    return " ".join(said)


@MCP.template("mounts-refused-delete")
def _mounts_refused_delete(
    name: Namer, /, *, key: str, mounts: Sequence[str], unwritable: Sequence[str] = (), **_: Any
) -> str:
    return (
        f"{len(mounts)} read-only mounted store(s) below {name(key)!r} refuse a "
        f"delete: {', '.join(repr(mount) for mount in mounts)}. Nothing there was "
        f"removed, and `recursive` will not reach it either. "
        f"{_remounting(mounts, unwritable, 'delete')}"
    )


@MCP.template("copy-was-a-dry-run")
def _copy_was_a_dry_run(name: Namer, /, *, overwriting: bool, **_: Any) -> str:
    # The advice has to name a conflict rule that will accept a watermark:
    # `overwrite` beside one is the pairing `bulk` refuses, so unconditionally
    # telling a caller to hand the moment back recommended the call that fails.
    guarded = " with on_conflict='overwrite-unchanged'" if overwriting else ""
    return (
        "Nothing was written; this is what the copy would have done. Pass "
        f"checked_at back as unchanged_since{guarded} to refuse the real "
        "copy if anything moves in between."
    )


@MCP.template("keys-changed-since")
def _keys_changed_since(
    name: Namer, /, *, changed: Sequence[str], unchanged_since: str | None, **_: Any
) -> str:
    return (
        f"{len(changed)} key(s) changed since {unchanged_since!r} "
        f"and were left as they are; they are named in `changed`. Read "
        f"them before deciding whether the copy should still land."
    )


@MCP.template("copy-stopped-at-limit")
def _copy_stopped_at_limit(
    name: Namer, /, *, limit: int, unchanged_since: str | None, **_: Any
) -> str:
    said = (
        f"The limit of {limit} stopped this call and more is left to "
        f"copy; call again with cursor set to next_cursor and every "
        f"other argument unchanged."
    )
    if not unchanged_since:
        return said
    # The watermark is the exception to "unchanged", and the two halves
    # contradicted each other without this.
    return said + (
        " Except unchanged_since, where the source is newer than it: "
        "the page just written carries the source's own timestamps "
        "into the target, so take the moment again from a dry run at "
        "that cursor rather than have it refuse the next call."
    )


@MCP.template("failures-sampled")
def _failures_sampled(name: Namer, /, *, failed: int, named: int, **_: Any) -> str:
    return (
        f"{failed} document(s) failed and the first {named} are named; the rest are only counted."
    )


@MCP.template("copy-stopped-at-conflict")
def _copy_stopped_at_conflict(name: Namer, /, **_: Any) -> str:
    return (
        "on_conflict='stop' ended the copy at a key that was already "
        "stored; nothing after it was copied and next_cursor is not a "
        "way back to it."
    )


@MCP.template("mounts-refused-write")
def _mounts_refused_write(
    name: Namer, /, *, key: str, mounts: Sequence[str], unwritable: Sequence[str] = (), **_: Any
) -> str:
    # "at or below", because the mount that refuses a copy is as often the one
    # the documents are landing *inside* as one standing under the landing
    # zone. Saying only "below" was how the first case went unreported: the
    # question asked of the table could not see upwards, and the sentence
    # written for its answer could not have described it if it had.
    return (
        f"{len(mounts)} read-only mounted store(s) refuse a write at or below "
        f"{name(key)!r}: {', '.join(repr(mount) for mount in mounts)}. Nothing "
        f"lands there. {_remounting(mounts, unwritable, 'copy')}"
    )


@MCP.template("mount-replaced-another")
def _mount_replaced_another(name: Namer, /, *, mount: str, **_: Any) -> str:
    return (
        f"a store was already mounted at {name(mount)!r} and is no longer: a "
        f"mount at a point something holds replaces it, and the table below is "
        f"what the namespace is now."
    )


@MCP.template("mount-created-store")
def _mount_created_store(name: Namer, /, *, mount: str, path: str, **_: Any) -> str:
    return (
        f"no store existed at {path!r}, so a new writable store was created "
        f"and mounted at {name(mount)!r}. Check the file name if an existing "
        f"store was expected."
    )


@MCP.template("mount-shadows-keys")
def _mount_shadows_keys(name: Namer, /, *, mount: str, **_: Any) -> str:
    return (
        f"the store beneath {name(mount)!r} already held keys there, and they "
        f"are unreachable while this is mounted: a mount shadows rather than "
        f"merges, so nothing below the mount point is consulted outside it. "
        f"Unmount to reach them again."
    )


@MCP.template("unmount-revealed-keys")
def _unmount_revealed_keys(name: Namer, /, *, mount: str, **_: Any) -> str:
    return (
        f"the store that answers for {name(mount)!r} now holds keys there. "
        f"They were shadowed by the mount rather than removed by it, so what "
        f"is at that key has changed without anything being written."
    )


# Three templates rather than one, and the split is not decorative. All three
# say the same first thing -- this table lasts as long as the server -- which
# is the one fact about a change a caller cannot work out from the answer,
# since the table handed back looks exactly like the table a restart would
# give. What differs is what to do about it, and one sentence covering all
# three was wrong in two of them: it told a caller who had just *unmounted*
# something to write that very mount into the configuration file, and it told
# a caller who had mounted the shipped manual to write down a store that has
# no `KEY=FILE` spelling at all. Which change this was is known where the note
# is made, so the wording is chosen there rather than hedged here.


@MCP.template("remount-not-permanent")
def _remount_not_permanent(name: Namer, /, *, mount: str, **_: Any) -> str:
    return (
        f"this table lasts as long as this server and no longer. To keep "
        f"{name(mount)!r} across a restart, write it into the mount "
        f"configuration file: nothing here edits one, since a machine rewrite "
        f"is what loses the comments such a file exists for."
    )


@MCP.template("remount-shipped-is-default")
def _remount_shipped_is_default(name: Namer, /, *, mount: str, **_: Any) -> str:
    # Nothing to write down, which is the whole of the news: this is the store
    # outrage ships, it arrives with the server, and the reason it can be
    # mounted by name in the first place is that it lives in `site-packages`
    # and has no spelling as a mount file. Telling this caller to write it into
    # the configuration file named a file they could not name.
    return (
        f"this table lasts as long as this server and no longer, but "
        f"{name(mount)!r} needs nothing written down: it is the store outrage "
        f"ships and is mounted by default, so a restart puts it back."
    )


@MCP.template("unmount-not-permanent")
def _unmount_not_permanent(name: Namer, /, *, mount: str, **_: Any) -> str:
    # The mount configuration file has no unmount to write: its fields are
    # `root-mount`, `mount` and `mount-ro`, and `--unmount` is a command line
    # flag for one run. So the two remedies are of different kinds -- take the
    # entry out of the file, or start the server with the flag -- and the
    # second is an operator's, since a tool caller cannot start the server.
    # Both named, each with whose it is, per the rule at the top of this module.
    #
    # No `spell`, and this is the distinction that rule turns on: `--unmount`
    # here is the *startup* flag, which a tool caller cannot type at all. The
    # `unmount` tool is what they just called, and calling it again is exactly
    # what does not persist. `mount-unmount-unmatched` does take a speller for
    # the same word, and correctly: there the flag and the tool are one
    # argument spelled twice, and either reader can act on their own spelling.
    return (
        f"this table lasts as long as this server and no longer: a restart "
        f"mounts {name(mount)!r} again. There is no unmount to write into the "
        f"mount configuration file, so keeping it away means taking its entry "
        f"out of that file, or, for a mount no file names, starting the server "
        f"with --unmount, which is an operator's to do."
    )


@MCP.template("unmount-of-a-dynamic-mount")
def _unmount_of_a_dynamic_mount(name: Namer, /, *, mount: str, **_: Any) -> str:
    return (
        f"this table lasts as long as this server and no longer, but "
        f"{name(mount)!r} needs nothing written down: it was mounted while this "
        f"server ran rather than when it started, so a restart does not mount "
        f"it again."
    )


# -- store: reading --------------------------------------------------------


@template("key-not-found")
def _key_not_found(name: Namer, /, *, key: str, **_: Any) -> str:
    return f"nothing is stored at or below {name(key)!r}"


@template("key-is-a-container")
def _key_is_a_container(name: Namer, /, *, key: str, beneath: int, **_: Any) -> str:
    # The advice has to name the outer key too. Following it with the inner one
    # asks the store *above* the mount, which holds nothing there -- so the
    # caller gets an empty listing rather than an error and concludes the keys
    # do not exist. That was the worst of the three faults in `error-naming`.
    return (
        f"no content stored at {name(key)!r}, but {beneath} key(s) lie beneath it; "
        f"use list_keys or get_documents to see them"
    )


@template("pattern-not-found")
def _pattern_not_found(
    name: Namer,
    /,
    *,
    key: str,
    pattern: str,
    occurrence: int,
    offset: int,
    byte_offset: int | None = None,
    **_: Any,
) -> str:
    # Named in the unit the caller searched in. A byte-addressed read that was
    # told "at or after offset 400" would go looking for character 400, which
    # is a different place in the document and the sentence's own fault.
    where = "offset" if byte_offset is None else "byte offset"
    position = offset if byte_offset is None else byte_offset
    return (
        f"{pattern!r} does not occur {occurrence + 1} time(s) in {name(key)!r} "
        f"at or after {where} {position}"
    )


@template("pattern-empty")
def _pattern_empty(name: Namer, /, **_: Any) -> str:
    return "a pattern must not be empty; omit it to read from the offset instead"


@template("offsets-both-given")
def _offsets_both_given(
    name: Namer, /, *, key: str, offset: int, byte_offset: int, spell: Speller, **_: Any
) -> str:
    return (
        f"cannot read {name(key)!r} from two places at once: "
        f"{spell('offset', offset)} counts characters and "
        f"{spell('byte_offset', byte_offset)} counts bytes; give one or the other"
    )


@template("search-criteria-count")
def _search_criteria_count(name: Namer, /, *, count: int, **_: Any) -> str:
    return f"a search needs between 1 and 5 criteria, got {count}"


@template("search-combination")
def _search_combination(name: Namer, /, *, combine: str, **_: Any) -> str:
    return f"search combination must be 'any' or 'all', got {combine!r}"


@template("search-scan-limit")
def _search_scan_limit(name: Namer, /, *, scan_limit: int, **_: Any) -> str:
    return f"search scan_limit must be positive, got {scan_limit}"


@template("search-match-mode")
def _search_match_mode(name: Namer, /, *, index: int, match: str, **_: Any) -> str:
    return f"search criterion {index} has unknown match mode {match!r}"


@template("search-target")
def _search_target(name: Namer, /, *, index: int, target: str, **_: Any) -> str:
    return f"search criterion {index} has unknown target {target!r}"


@template("search-pattern-empty")
def _search_pattern_empty(name: Namer, /, *, index: int, **_: Any) -> str:
    return f"search criterion {index} has an empty pattern"


@template("search-document-meta-name")
def _search_document_meta_name(name: Namer, /, *, index: int, **_: Any) -> str:
    return f"search criterion {index} targets a document, so meta_name must be omitted"


@template("search-meta-name-empty")
def _search_meta_name_empty(name: Namer, /, *, index: int, **_: Any) -> str:
    return f"search criterion {index} has an empty meta_name selection"


@template("search-regex-invalid")
def _search_regex_invalid(
    name: Namer, /, *, index: int, pattern: str, reason: str, **_: Any
) -> str:
    return f"search criterion {index} has invalid regex {pattern!r}: {reason}"


# -- store: arguments in transit -------------------------------------------
#
# What ``json-string`` exists to catch, said to the caller who can act on it.
# A model that emitted its own closing scaffolding into a value has to be told
# to send the call again, and told what shape the value should have had; the
# sentence is the entire mechanism, so it is the one thing that must not be
# swallowed.


@template("encoding-not-a-json-string")
def _encoding_not_a_json_string(
    name: Namer, /, *, what: str, encoding: str, reason: str, **_: Any
) -> str:
    return (
        f"{what} is not a valid JSON string literal under encoding {encoding!r}: "
        f"{reason}. Send it as a JSON string, quotes included, with nothing after "
        f"the closing quote."
    )


@template("encoding-not-a-string")
def _encoding_not_a_string(
    name: Namer, /, *, what: str, encoding: str, decoded: str, **_: Any
) -> str:
    return (
        f"{what} decoded to {decoded} under encoding {encoding!r}, not a string. "
        f"Send a JSON string literal, not an object or an array."
    )


# -- store: the store file -------------------------------------------------


@template("store-file-unnamed")
def _store_file_unnamed(name: Namer, /, **_: Any) -> str:
    return "a store file needs a name"


@template("store-file-absolute")
def _store_file_absolute(name: Namer, /, *, filename: str, **_: Any) -> str:
    return (
        f"store file {filename!r} is an absolute path; it names a file "
        f"relative to the store directory, so pass the file alone. The store "
        f"directory is settled once, by --dir where the store is opened, and "
        f"`info` is what reports which one this is."
    )


@template("store-file-escapes")
def _store_file_escapes(name: Namer, /, *, filename: str, **_: Any) -> str:
    return f"store file {filename!r} climbs out of the store directory with '..'"


# -- store: backup ---------------------------------------------------------


@template("backup-unwritable")
def _backup_unwritable(name: Namer, /, *, target: str, reason: str, **_: Any) -> str:
    return f"could not write {target}: {reason}"


@template("backup-is-the-store")
def _backup_is_the_store(name: Namer, /, *, target: str, **_: Any) -> str:
    return f"{target} is the store itself, not a backup of it"


@template("backup-exists")
def _backup_exists(name: Namer, /, *, target: str, **_: Any) -> str:
    return f"{target} already exists; pass overwrite to replace it"


@template("backup-corrupt")
def _backup_corrupt(name: Namer, /, *, target: str, integrity: str, **_: Any) -> str:
    return f"{target} failed its integrity check: {integrity}"


@template("backup-schema-mismatch")
def _backup_schema_mismatch(
    name: Namer, /, *, target: str, found: int, expected: int, **_: Any
) -> str:
    return f"{target} came out at schema {found}, but the store is at {expected}"


@template("backup-incomplete")
def _backup_incomplete(name: Namer, /, *, target: str, differs: str, **_: Any) -> str:
    return (
        f"{target} does not hold what the store holds: {differs}. A concurrent "
        f"write can cause this, so try again before suspecting the copy"
    )


@template("backup-short")
def _backup_short(name: Namer, /, *, target: str, found: int, expected: int, **_: Any) -> str:
    return (
        f"{target} holds {found} documents but the store holds {expected}; "
        f"a concurrent write can cause this, so try again before suspecting the copy"
    )


# -- keys ------------------------------------------------------------------
#
# These name the key **as it was typed**, and deliberately do not put it
# through the namer. Two reasons, and both matter. A key that failed
# validation may not survive being renamed at all -- `mount.outer` parses, so
# rendering the message could raise the very error it is reporting, and an
# error path that fails is the worst one there is. And an invalid key is
# echoed so the caller can compare it against what they sent; a tidied or
# re-prefixed version is a worse answer to "what did I get wrong".
#
# A front end that validates before descending sees the outer spelling here
# anyway, because the outer key is the one it parsed.


@template("key-not-a-string")
def _key_not_a_string(name: Namer, /, *, got: str, **_: Any) -> str:
    return f"key must be a string, got {got}"


@template("key-too-many-segments")
def _key_too_many_segments(name: Namer, /, *, key: str, segments: int, limit: int, **_: Any) -> str:
    return f"key {key!r} has {segments} segments; at most {limit} are allowed"


@template("key-wildcard-not-allowed")
def _key_wildcard_not_allowed(name: Namer, /, *, key: str, **_: Any) -> str:
    return f"key {key!r} may not contain {keys.WILDCARD!r}; it is allowed only when storing"


@template("key-multiple-wildcards")
def _key_multiple_wildcards(name: Namer, /, *, key: str, **_: Any) -> str:
    return f"key {key!r} has more than one {keys.WILDCARD!r} segment"


@template("key-empty-metadata-name")
def _key_empty_metadata_name(name: Namer, /, *, key: str, **_: Any) -> str:
    return f"key {key!r} has no metadata name after {keys.META_PREFIX!r}"


@template("key-segment-too-long")
def _key_segment_too_long(name: Namer, /, *, key: str, what: str, length: int, **_: Any) -> str:
    return (
        f"{what} in key {key!r} is {length} characters; "
        f"at most {keys.MAX_SEGMENT_CHARS} are allowed"
    )


@template("key-segment-bad-character")
def _key_segment_bad_character(
    name: Namer, /, *, key: str, what: str, segment: str, character: str, **_: Any
) -> str:
    return (
        f"{what} {segment!r} in key {key!r} is not valid: it contains "
        f"{character!r}, and a segment may not hold characters below "
        f"{keys.MIN_SEGMENT_CHAR!r}"
    )


@template("key-reserved-segment")
def _key_reserved_segment(name: Namer, /, *, key: str, segment: str, **_: Any) -> str:
    return (
        f"segment {segment!r} in key {key!r} is reserved: a segment beginning "
        f"with {keys.RESERVED_PREFIX!r} names a filter or an operation, and "
        f"{', '.join(sorted(repr(s) for s in keys.RESERVED_SEGMENTS))} are the "
        f"only ones defined"
    )


@template("key-last-not-allowed")
def _key_last_not_allowed(name: Namer, /, *, key: str, **_: Any) -> str:
    return (
        f"key {key!r} may not contain {keys.LAST!r} here; it is resolved "
        f"against the store before a key is parsed"
    )


@template("key-not-below-scope")
def _key_not_below_scope(name: Namer, /, *, key: str, scope: str, **_: Any) -> str:
    return f"key {name(key)} is not at or below {name(scope)}, so it has no reading from there"


@template("key-no-last-child")
def _key_no_last_child(name: Namer, /, *, key: str, parent: str, **_: Any) -> str:
    return f"key {key!r} asks for the last key below {name(parent)}, which has nothing below it"


@template("key-no-wildcard-to-substitute")
def _key_no_wildcard_to_substitute(name: Namer, /, *, key: str, **_: Any) -> str:
    return f"key {key!r} has no {keys.WILDCARD!r} segment to substitute"


# -- a store kept as files -------------------------------------------------


@template("files-not-text")
def _files_not_text(name: Namer, /, *, key: str, path: str, **_: Any) -> str:
    return (
        f"key {name(key)!r} is the file {path!r}, which does not hold UTF-8 "
        f"text: a store holds text, and this is reported rather than mangled "
        f"into some"
    )


# -- bulk import and export ------------------------------------------------


@template("extensions-unknown")
def _extensions_unknown(name: Namer, /, *, extensions: str, known: Any, **_: Any) -> str:
    listed = ", ".join(str(one) for one in known)
    return (
        f"there is no {extensions!r} way of naming a tree's files. There is: "
        f"{listed}. `strip` takes a known extension off a file name to make the "
        f"key, which is how this package writes a tree; `keep` makes the whole "
        f"file name the key, for a bundle whose documents link to each other by "
        f"name."
    )


@template("key-escapes-tree")
def _key_escapes_tree(name: Namer, /, *, key: str, path: str, **_: Any) -> str:
    return (
        f"key {name(key)!r} would be written to {path!r}, which is outside the "
        f"directory it was given: a link along the path leads out of the tree"
    )


@template("key-is-a-symlink")
def _key_is_a_symlink(name: Namer, /, *, key: str, path: str, **_: Any) -> str:
    return (
        f"key {name(key)!r} would be written to {path!r}, which is a symbolic "
        f"link: a link is not a document here, so writing through it would "
        f"replace something this store never held"
    )


@template("key-extension-contradicts-format")
def _key_extension_contradicts_format(
    name: Namer, /, *, key: str, extension: str, format: str, declared: str, **_: Any
) -> str:
    return (
        f"key {name(key)!r} would be stored as {format} in a file its own name "
        f"calls {declared}: this tree keeps extensions, so {extension!r} is "
        f"part of the key and is what any reader of the file will believe. "
        f"Spell the key with the extension the format wants, or store it as "
        f"{declared}."
    )


@template("key-is-a-directory")
def _key_is_a_directory(name: Namer, /, *, key: str, path: str, **_: Any) -> str:
    return (
        f"key {name(key)!r} would be stored at {path!r}, which is already a "
        f"directory in this tree: replacing it with a document would lose the "
        f"keys it holds"
    )


@template("key-below-a-document")
def _key_below_a_document(name: Namer, /, *, key: str, path: str, holder: str, **_: Any) -> str:
    return (
        f"key {name(key)!r} would be written to {path!r}, and {holder!r} in the "
        f"way is a file rather than a directory: the key holding it cannot hold "
        f"children as well, since a name is a file or a directory and not both"
    )


@template("key-segment-is-traversal")
def _key_segment_is_traversal(name: Namer, /, *, key: str, segment: str, **_: Any) -> str:
    return (
        f"key {name(key)!r} has a segment of {segment!r}, which is a legal "
        f"segment and not a path component: it would name a file "
        f"outside the directory being written"
    )


@template("import-source-missing")
def _import_source_missing(name: Namer, /, *, source: str, **_: Any) -> str:
    return f"no directory at {source}"


@template("import-file-missing")
def _import_file_missing(
    name: Namer, /, *, key: str, path: str, given: str, root: str, **_: Any
) -> str:
    missing = f"nothing to store at {name(key)!r}: no file at {path}"
    if os.path.isabs(given):
        return missing
    # A relative path is taken from the export directory, not from wherever the
    # caller is standing, and the joined result is the only thing this sentence
    # would otherwise show: `export/x.md` typed where a person is standing is
    # reported missing from `<the export directory>/export/x.md`, and the
    # doubled segment reads as a bug in the tool rather than as a path taken
    # from somewhere else. Naming the directory is what makes it read as what
    # it is.
    return f"{missing} - {given!r} is relative to the export directory {root}"


@template("import-file-escapes-tree")
def _import_file_escapes_tree(name: Namer, /, *, key: str, path: str, **_: Any) -> str:
    return (
        f"nothing to store at {name(key)!r}: the file at {path} is outside the "
        f"export directory, and only a file exported into it can be stored back"
    )


@template("export-root-unusable")
def _export_root_unusable(name: Namer, /, *, path: str, because: str, **_: Any) -> str:
    # The directory is shared with every other user on the machine, so a name
    # somebody else got to first is refused rather than written into. Saying
    # which of the reasons it was is what makes it fixable: the answers to a
    # stale symbolic link and to a directory of another user's are different.
    return (
        f"cannot export: the export directory {path} cannot be used because "
        f"{because}. Remove it, or set TMPDIR to somewhere this user owns"
    )


def _refused_write(name: Namer, key: str, path: str, storing: str | None) -> tuple[str, str]:
    """How to open a refusal, and how to refer to the file that refused it.

    Three shapes, because the file that *checks* a write and the file that
    *supplies* it stopped being the same thing. Naming one of them as the other
    sends a reader to look at the wrong file, and in the third shape there is
    no file being stored at all -- the content came from the call.
    """
    if storing is None:
        return f"not writing {name(key)!r}", f"{path}, which checks this write,"
    if storing == path:
        return f"not storing {path} at {name(key)!r}", "this file"
    return f"not storing {storing} at {name(key)!r}", f"{path}, which checks it,"


@template("import-stale")
def _import_stale(
    name: Namer,
    /,
    *,
    key: str,
    path: str,
    exported_at: str,
    changed_at: str | None = None,
    storing: str | None = None,
    **_: Any,
) -> str:
    # Both times, because the pair is the whole story and neither half tells
    # it: a document written after this file last matched it is what makes the
    # file stale. "In step with" rather than "exported at" because a successful
    # import renews the record, so the moment is not always the export.
    since = f"written again at {changed_at}" if changed_at else "deleted since"
    lead, checker = _refused_write(name, key, path, storing)
    return (
        f"{lead}: {checker} was last in step with the document at "
        f"{exported_at}, and the document was {since}, so somebody else has "
        f"written it and this write would lose their work. Export it again and "
        f"redo the edit, or repeat the call with overwrite to write it anyway"
    )


@template("write-unchecked")
def _write_unchecked(
    name: Namer,
    /,
    *,
    key: str,
    path: str,
    came_from: str | None = None,
    storing: str | None = None,
    **_: Any,
) -> str:
    # Names the file the caller could have passed instead, because the refusal
    # is useless without it: an agent told only that this is unchecked reaches
    # for `overwrite`, which is the guard being thrown away. The route out that
    # keeps the check has to be the one in the sentence.
    because = (
        "carries no record of having been exported"
        if came_from is None
        else f"was exported from {name(came_from)!r}, not from {name(key)!r}"
    )
    lead, checker = _refused_write(name, key, path, storing)
    return (
        f"{lead}: {checker} {because}, so there is nothing to say whether "
        f"somebody else has written that document since. Export {name(key)!r} "
        f"and pass that file as `against` to check this write, or repeat the "
        f"call with overwrite to write it unchecked"
    )


@template("check-without-write")
def _check_without_write(name: Namer, /, *, key: str, **_: Any) -> str:
    return (
        f"nothing to check at {name(key)!r}: `against` checks a write, and "
        f"omitting `path` exports rather than writes. Pass the file to store, "
        f"or drop `against` to export"
    )


# -- mounts ----------------------------------------------------------------
#
# A mount point is named with `keys.displayed` directly rather than through the
# namer. These are raised while a table is being *built*, or about the table
# itself, so a prefix is already the name the whole namespace uses -- putting
# it through a namer would prefix it a second time.


@template("mount-key-too-deep")
def _mount_key_too_deep(name: Namer, /, *, key: str, mount: str, **_: Any) -> str:
    return (
        f"{keys.displayed(key)!r} in the store mounted at {keys.displayed(mount)!r} has no "
        f"name in this namespace: joined it exceeds "
        f"{keys.MAX_JOINED_SEGMENTS} segments. The store holds a key deeper "
        f"than {keys.MAX_SEGMENTS} segments, which `outrage check` reports; it "
        f"predates that bound and has to be moved before the store can be "
        f"mounted here."
    )


@template("mount-read-only")
def _mount_read_only(name: Namer, /, *, key: str, mount: str, action: str, **_: Any) -> str:
    # One cause reaches here, a mount made read-only by choice. A backend that
    # refuses writes raises `store-read-only`, because `Resolved.writable` asks
    # the store before the configuration, and a lent store raises `mount-lent`,
    # because the table records that it was lent. Neither can be remounted
    # writable, which is this sentence's whole remedy, and an explanation that
    # cannot be the explanation is worse than a shorter sentence.
    #
    # Still no `spell`, and still on purpose, but the reason has moved. A
    # speller turns one argument into each front end's spelling, and
    # `--mount-ro` has none at a tool call: a tool caller cannot start the
    # server. What changed with the `mount` tool is that the two readers now
    # have *different remedies* rather than one remedy spelled two ways, which
    # is a thing the error side does not carry -- an error's wording is shared
    # precisely because only the spelling was ever supposed to vary. So both
    # remedies are named, each qualified by when it is the reader's to take,
    # and no reader is told to type something they cannot.
    return (
        f"cannot {action} {keys.displayed(key)!r}: the store mounted at "
        f"{keys.displayed(mount)!r} was mounted read-only, with --mount-ro or "
        f"by the `mount` tool with `read_only`. Mounting it again writable is "
        f"what changes that: the `mount` tool with `read_only` false, where "
        f"this server offers it, and otherwise --mount rather than --mount-ro "
        f"at startup, which is an operator's to do. The file itself is not "
        f"read-only to anything else."
    )


@template("mount-lent")
def _mount_lent(name: Namer, /, *, key: str, mount: str, action: str, **_: Any) -> str:
    # No remount on offer, which is the difference from `mount-read-only`: a
    # lent store has no spelling as a mount file, and the `mount` tool lends
    # the shipped tree read-only however it is asked.
    return (
        f"cannot {action} {keys.displayed(key)!r}: the store mounted at "
        f"{keys.displayed(mount)!r} was lent to this server already open, as "
        f"the documentation shipped inside outrage is, and is read-only however "
        f"it is mounted: it lives in the installation, and the next upgrade "
        f"would replace anything written there."
    )


@template("mount-root-read-only")
def _mount_root_read_only(name: Namer, /, **_: Any) -> str:
    return (
        "the store at the root cannot be mounted read-only: it is the one "
        "--dir names, and it owns every key no mount claims"
    )


@template("mount-root-not-writable")
def _mount_root_not_writable(name: Namer, /, *, backend: str, **_: Any) -> str:
    # Reached by a command line that opened the store with `--store`, which is
    # already opening it directly, so that cannot be the advice. What made a
    # table of it is other mounts, most often a mounts.toml nobody typed. Only
    # the command line can read a store with nothing else mounted -- the
    # server mounts its shipped documentation whatever it is given -- so that
    # half says whose it is.
    return (
        f"the store at the root is a {backend} store, which cannot be written: "
        f"the root owns every key no mount claims, so nothing would have "
        f"anywhere to go. Mount it at a prefix with --mount-ro instead. To read "
        f"it on its own, the command line opens it with nothing else mounted: "
        f"no --mount of its own, and --no-mount-config where the mounts come "
        f"from mounts.toml."
    )


@template("mount-point-is-metadata")
def _mount_point_is_metadata(name: Namer, /, *, mount: str, **_: Any) -> str:
    return (
        f"cannot mount at {keys.displayed(mount)!r}: a mount point may not "
        f"be metadata, since everything below one is metadata too"
    )


@template("mount-duplicate")
def _mount_duplicate(name: Namer, /, *, mount: str, **_: Any) -> str:
    return f"more than one store is mounted at {keys.displayed(mount)!r}"


@template("mount-read-only-unmatched")
def _mount_read_only_unmatched(name: Namer, /, *, mounts: object, **_: Any) -> str:
    listed = ", ".join(repr(keys.displayed(m)) for m in mounts)  # type: ignore[union-attr]
    return f"nothing is mounted at {listed}, so it cannot be mounted read-only"


@template("mount-table-has-no-root")
def _mount_table_has_no_root(name: Namer, /, **_: Any) -> str:
    return (
        "a mount table needs a store at the root, since it is what owns "
        "every key no other mount claims"
    )


@template("mount-spec-malformed")
def _mount_spec_malformed(name: Namer, /, *, spec: str, delimiter: str = "=", **_: Any) -> str:
    return f"mount {spec!r} is not in KEY{delimiter}FILE form, as in ref{delimiter}reference.sqlite"


@template("mount-spec-has-no-file")
def _mount_spec_has_no_file(name: Namer, /, *, spec: str, **_: Any) -> str:
    return f"mount {spec!r} names no store file"


@template("mount-option-malformed")
def _mount_option_malformed(
    name: Namer, /, *, spec: str, option: str, assignment: str = "=", **_: Any
) -> str:
    return (
        f"{option!r} in mount {spec!r} is not an option: an option after the "
        f"store file is written NAME{assignment}VALUE, as in type{assignment}files"
    )


@template("mount-option-unknown")
def _mount_option_unknown(name: Namer, /, *, spec: str, option: str, known: Any, **_: Any) -> str:
    listed = ", ".join(str(one) for one in known)
    return (
        f"mount {spec!r} sets {option!r}, which is not a mount option. "
        f"There is: {listed}. A comma in the argument starts an option, so a "
        f"store file cannot hold one."
    )


@template("mount-option-repeated")
def _mount_option_repeated(name: Namer, /, *, spec: str, option: str, **_: Any) -> str:
    return f"mount {spec!r} sets {option!r} twice, and only one of them can be meant"


@template("mount-file-unspellable")
def _mount_file_unspellable(name: Namer, /, *, file: str, delimiter: str = ",", **_: Any) -> str:
    return (
        f"the store file {file!r} cannot be named on a command line: a "
        f"{delimiter!r} in a mount argument starts an option, so a store file "
        f"holding one has no spelling that reads back as itself"
    )


@template("mount-spec-at-root")
def _mount_spec_at_root(name: Namer, /, *, spec: str, **_: Any) -> str:
    return f"mount {spec!r} has no mount point; the store at the root is the one --root-mount names"


@template("mount-read-only-missing")
def _mount_read_only_missing(name: Namer, /, *, mount: str, path: str, **_: Any) -> str:
    return (
        f"the read-only mount at {keys.displayed(mount)!r} has no store at "
        f"{path!r}. A read-only mount is not created, since a "
        f"mistyped name would mount as an empty store that no write could "
        f"ever contradict."
    )


@template("documents-not-installed")
def _documents_not_installed(name: Namer, /, *, path: str, **_: Any) -> str:
    return (
        f"the outrage documentation is not in this installation: nothing at "
        f"{path!r}. It ships inside the package, so a missing tree is a build "
        f"that dropped it rather than anything to configure."
    )


# A mount configuration file. Every one of these names the file, because a
# table read from disk is the one kind nobody was looking at when it broke:
# unlike an option, it was written some other day, possibly by somebody else,
# and quite possibly for a different checkout.


@template("mount-unmount-at-root")
def _mount_unmount_at_root(name: Namer, /, **_: Any) -> str:
    return (
        "the store at the root cannot be unmounted: it owns every key no "
        "mount claims, so nothing would answer for them. Starting the server "
        "with --root-mount is how a different store is put there."
    )


@template("mount-nothing-shipped")
def _mount_nothing_shipped(name: Namer, /, *, mount: str, shipped: object, **_: Any) -> str:
    listed = ", ".join(repr(keys.displayed(one)) for one in shipped)  # type: ignore[union-attr]
    return (
        f"outrage ships no store for {keys.displayed(mount)!r}, so there is "
        f"nothing to mount there without a file. It ships one for {listed}; "
        f"anything else is a store file, named relative to the store directory."
    )


@template("mount-shipped-takes-no-type")
def _mount_shipped_takes_no_type(name: Namer, /, *, mount: str, **_: Any) -> str:
    return (
        f"the store outrage ships for {keys.displayed(mount)!r} is opened by "
        f"name and not from a file, so there is no backend to choose: drop "
        f"`type`, or name a file to mount something else there."
    )


@template("mount-shipped-takes-no-extensions")
def _mount_shipped_takes_no_extensions(name: Namer, /, *, mount: str, **_: Any) -> str:
    return (
        f"the store outrage ships for {keys.displayed(mount)!r} is a tree this "
        f"package wrote, and it is read the way it was written: drop "
        f"`extensions`, or name a file to mount something else there."
    )


@template("mount-remount-at-root")
def _mount_remount_at_root(name: Namer, /, **_: Any) -> str:
    return (
        "nothing can be mounted at the root of a running server: it owns "
        "every key no mount claims, and the instructions a connection was "
        "given were built from its readme. Start the server with --root-mount "
        "to put a different store there."
    )


@template("mount-unmount-unmatched")
def _mount_unmount_unmatched(name: Namer, /, *, mount: str, spell: Speller, **_: Any) -> str:
    # The one genuine two-spellings case among the mount messages, and it
    # became one when the `unmount` tool started raising the same code: a
    # server flag and a tool of the same name, one argument spelled twice.
    # Everything else these templates name is a *startup* flag, which has no
    # tool spelling at all -- so it needs different advice rather than a
    # respelling, which is a different problem and is not this.
    return (
        f"nothing is mounted at {keys.displayed(mount)!r}, so {spell('unmount')} "
        f"there removes nothing. Refused rather than passed over, since what a "
        f"mistyped one leaves behind is the mount it was meant to take away."
    )


@template("mount-config-missing")
def _mount_config_missing(name: Namer, /, *, path: str, **_: Any) -> str:
    return f"there is no mount configuration at {path!r}"


@template("mount-config-unreadable")
def _mount_config_unreadable(name: Namer, /, *, path: str, reason: str, **_: Any) -> str:
    return f"the mount configuration at {path!r} could not be read: {reason}"


@template("mount-config-not-toml")
def _mount_config_not_toml(name: Namer, /, *, path: str, reason: str, **_: Any) -> str:
    return f"the mount configuration at {path!r} is not valid TOML: {reason}"


@template("mount-config-unknown-field")
def _mount_config_unknown_field(
    name: Namer, /, *, path: str, fields: object, known: object, **_: Any
) -> str:
    named = ", ".join(repr(field) for field in fields)  # type: ignore[union-attr]
    expected = ", ".join(repr(field) for field in known)  # type: ignore[union-attr]
    return (
        f"the mount configuration at {path!r} sets {named}, which means "
        f"nothing here; it holds {expected} and nothing else"
    )


@template("mount-config-not-a-table")
def _mount_config_not_a_table(name: Namer, /, *, path: str, field: str, got: str, **_: Any) -> str:
    return (
        f"{field!r} in the mount configuration at {path!r} is a {got} rather "
        f'than a table of KEY = "FILE" entries'
    )


@template("mount-config-not-a-file")
def _mount_config_not_a_file(name: Namer, /, *, path: str, field: str, got: str, **_: Any) -> str:
    return (
        f"{field!r} in the mount configuration at {path!r} is a {got} rather "
        f"than the name of a store file"
    )


@template("mount-config-section-is-an-entry")
def _mount_config_section_is_an_entry(
    name: Namer, /, *, path: str, field: str, key: str, **_: Any
) -> str:
    return (
        f"[{field}] in the mount configuration at {path!r} is one entry's "
        f"fields rather than a table of mounts: {key!r} belongs inside an "
        f'entry, as in docs = {{ {key} = "documents", type = "files" }}'
    )


@template("mount-config-unknown-option")
def _mount_config_unknown_option(
    name: Namer, /, *, path: str, field: str, options: object, known: object, **_: Any
) -> str:
    named = ", ".join(repr(option) for option in options)  # type: ignore[union-attr]
    expected = ", ".join(repr(option) for option in known)  # type: ignore[union-attr]
    return (
        f"{field!r} in the mount configuration at {path!r} sets {named}, which "
        f"is not something a mount can say; an entry holds {expected}"
    )


@template("mount-config-no-path")
def _mount_config_no_path(name: Namer, /, *, path: str, field: str, key: str, **_: Any) -> str:
    return (
        f"{field!r} in the mount configuration at {path!r} names no store "
        f"file: an entry written as a table needs {key!r}"
    )


@template("mount-config-duplicate")
def _mount_config_duplicate(name: Namer, /, *, path: str, mount: str, **_: Any) -> str:
    return (
        f"the mount configuration at {path!r} mounts {keys.displayed(mount)!r} "
        f"twice; read-write and read-only mounts share one namespace"
    )


@template("mount-config-unspellable")
def _mount_config_unspellable(
    name: Namer, /, *, path: str, mount: str, delimiter: str, **_: Any
) -> str:
    return (
        f"{mount!r} in the mount configuration at {path!r} cannot be a mount "
        f"point: it holds {delimiter!r}, so it has no --mount spelling, and a "
        f"configuration file is read as the options it stands for"
    )


@template("cursor-outside-subtree")
def _cursor_outside_subtree(name: Namer, /, *, cursor: str, mount: str, key: str, **_: Any) -> str:
    return (
        f"cursor {cursor!r} is not below {keys.displayed(mount)!r}, which is the "
        f"store answering for {keys.displayed(key)!r}"
    )


# -- maintenance, the log, configuration -----------------------------------


@template("check-unreadable")
def _check_unreadable(name: Namer, /, *, path: str, reason: str, **_: Any) -> str:
    return f"cannot read {path}: {reason}"


@template("check-no-store")
def _check_no_store(name: Namer, /, *, path: str, **_: Any) -> str:
    return f"no store at {path}"


@template("log-missing")
def _log_missing(name: Namer, /, *, path: str, **_: Any) -> str:
    return f"no log file at {path}"


@template("log-unreadable")
def _log_unreadable(name: Namer, /, *, path: str, reason: str, **_: Any) -> str:
    return f"cannot read {path}: {reason}"


@template("config-not-json")
def _config_not_json(name: Namer, /, *, path: str, reason: str, **_: Any) -> str:
    return f"{path} is not valid JSON ({reason}); leaving it alone"


@template("config-not-an-object")
def _config_not_an_object(name: Namer, /, *, path: str, **_: Any) -> str:
    return f"{path} does not hold a JSON object; leaving it alone"


@template("config-field-not-an-object")
def _config_field_not_an_object(name: Namer, /, *, path: str, field: str, **_: Any) -> str:
    return f"{path} has a {field!r} that is not an object; leaving it alone"


@template("config-field-not-a-list")
def _config_field_not_a_list(name: Namer, /, *, path: str, field: str, **_: Any) -> str:
    return f"{path} has a {field!r} that is not a list; leaving it alone"


@template("config-server-not-an-object")
def _config_server_not_an_object(name: Namer, /, *, path: str, server: str, **_: Any) -> str:
    return f"{path} has a {server!r} server that is not an object; leaving it alone"


# -- installation ----------------------------------------------------------


@template("template-missing")
def _template_missing(name: Namer, /, *, path: str, **_: Any) -> str:
    return f"packaged template missing at {path}"


@template("template-not-json")
def _template_not_json(name: Namer, /, *, path: str, **_: Any) -> str:
    return f"packaged template at {path} is not valid JSON"


@template("template-hook-count")
def _template_hook_count(name: Namer, /, *, event: str, **_: Any) -> str:
    return f"packaged template must hold exactly one {event} entry"


@template("template-unmarked")
def _template_unmarked(name: Namer, /, *, marker: str, **_: Any) -> str:
    return f"packaged template's command does not carry the {marker!r} marker"


@template("assets-missing")
def _assets_missing(name: Namer, /, *, asset: str, path: str, **_: Any) -> str:
    return f"packaged {asset} missing at {path}"


@template("assets-empty")
def _assets_empty(name: Namer, /, *, asset: str, path: str, **_: Any) -> str:
    return f"packaged {asset} content is empty at {path}"


# -- store: which backend, and what it will not do -------------------------


@template("store-read-only")
def _store_read_only(
    name: Namer, /, *, key: str, path: str, action: str, backend: str, **_: Any
) -> str:
    # Deliberately does *not* offer a flag to drop, which is what separates
    # this from `mount-read-only`: no way of opening a parquet file makes a
    # write to it succeed, and advice that cannot work is worse than none. It
    # reaches a caller through a mount as well as through a bare store --
    # `Resolved.writable` picks between the two refusals by asking the store
    # rather than the configuration.
    #
    # The backend is named by the raise site because the reason differs
    # between the stores that refuse, and so does what to do instead: a
    # sentence about one file written whole is wrong about a directory of them.
    if backend == "duckdb":
        return (
            f"cannot {action} {name(key)!r}: it is in a duckdb store, a directory "
            f"of parquet parts that is read and never written through. No way of "
            f"starting the server allows a write here; a part is added by putting "
            f"a new file in the directory, which `outrage pack` can write. ({path})"
        )
    return (
        f"cannot {action} {name(key)!r}: it is in a {backend} store, which is "
        f"written whole rather than updated in place. No way of starting the "
        f"server allows a write here; build a new one with `outrage pack`. "
        f"({path})"
    )


@template("backend-unavailable")
def _backend_unavailable(
    name: Namer, /, *, filename: str, backend: str, reason: str, **_: Any
) -> str:
    return f"{filename} needs the {backend} backend, which will not load: {reason}"


@template("backend-unknown")
def _backend_unknown(name: Namer, /, *, backend: str, filename: str, known: Any, **_: Any) -> str:
    listed = ", ".join(str(one) for one in known)
    about = f" for {filename!r}" if filename else ""
    return (
        f"there is no {backend!r} backend{about}. The types a mount may ask "
        f"for are: {listed}. Asked for rather than guessed at, so a name "
        f"nobody recognises is refused instead of quietly opening an empty "
        f"store of some other kind."
    )


@template("backend-takes-no-extensions")
def _backend_takes_no_extensions(
    name: Namer, /, *, backend: str, filename: str, extensions: str, **_: Any
) -> str:
    about = f" {filename!r}" if filename else ""
    return (
        f"the {backend} store{about} cannot be asked for {extensions!r} "
        f"extensions: how a file name lines up with a key is a question only a "
        f"directory of files has, one file per key, and this store holds its "
        f"documents as rows. Mount it with `type=files` if it is a tree, or "
        f"drop the option."
    )


@template("parquet-needs-pyarrow")
def _parquet_needs_pyarrow(name: Namer, /, *, reason: str, **_: Any) -> str:
    return (
        f"a parquet store needs pyarrow, which is not installed: {reason}. "
        f"Install it with `pip install 'outrage[parquet]'`."
    )


@template("parquet-store-missing")
def _parquet_store_missing(name: Namer, /, *, path: str, **_: Any) -> str:
    return (
        f"there is no parquet store at {path}. Unlike a SQLite store this one "
        f"is not created empty: it has no write that would fill it, so an "
        f"empty one could only ever read back empty. Build it with `outrage pack`."
    )


@template("parquet-not-a-store")
def _parquet_not_a_store(name: Namer, /, *, path: str, **_: Any) -> str:
    return (
        f"{path} is a parquet file but not an outrage store: it carries no format "
        f"version, so its columns are somebody else's and mean something else"
    )


@template("parquet-format-newer")
def _parquet_format_newer(name: Namer, /, *, path: str, found: int, expected: int, **_: Any) -> str:
    return (
        f"{path} is written in parquet store format {found} and this build "
        f"reads {expected}; it is not migrated in place, so repack it or "
        f"upgrade outrage"
    )


@template("parquet-target-exists")
def _parquet_target_exists(name: Namer, /, *, path: str, **_: Any) -> str:
    return f"{path} already exists; pass --overwrite to replace it"


@template("duckdb-needs-duckdb")
def _duckdb_needs_duckdb(name: Namer, /, *, reason: str, **_: Any) -> str:
    return (
        f"a duckdb store needs duckdb, which is not installed: {reason}. "
        f"Install it with `pip install 'outrage[duckdb]'`."
    )


@template("duckdb-store-missing")
def _duckdb_store_missing(name: Namer, /, *, path: str, **_: Any) -> str:
    return (
        f"there is no directory of parquet parts at {path}. A duckdb store is "
        f"not created empty: nothing writes to it, so an empty one could only "
        f"ever read back empty. Put the parts in a directory and name that."
    )


@template("duckdb-not-a-directory")
def _duckdb_not_a_directory(name: Namer, /, *, path: str, **_: Any) -> str:
    return (
        f"{path} is a file, and a duckdb store is a directory of parquet parts. "
        f"A single parquet file is read by the parquet backend, which its "
        f"extension already chooses: drop `type=duckdb`."
    )


@template("duckdb-no-parts")
def _duckdb_no_parts(name: Namer, /, *, path: str, **_: Any) -> str:
    return (
        f"{path} holds no parquet parts: a part is a file ending .parquet, "
        f"directly inside it and not hidden. An empty directory would mount as "
        f"a store that is simply empty, so it is refused instead."
    )


@template("duckdb-part-unreadable")
def _duckdb_part_unreadable(name: Namer, /, *, path: str, reason: str, **_: Any) -> str:
    return (
        f"a part in {path} cannot be read as parquet, so the directory is not "
        f"opened at all rather than read without it: {reason}"
    )


@template("duckdb-part-not-a-store")
def _duckdb_part_not_a_store(name: Namer, /, *, path: str, **_: Any) -> str:
    return (
        f"{path} is a parquet file but not an outrage store: it carries no format "
        f"version, so its columns are somebody else's and mean something else. "
        f"Every part in the directory has to be one `outrage pack` could have written."
    )


@template("duckdb-mixed-versions")
def _duckdb_mixed_versions(
    name: Namer,
    /,
    *,
    path: str,
    first: str,
    first_version: int,
    other: str,
    other_version: int,
    **_: Any,
) -> str:
    return (
        f"the parts in {path} disagree about their format: {first} is format "
        f"{first_version} and {other} is format {other_version}. Every part "
        f"must be written in one format; repack the older ones."
    )


@template("duckdb-format-newer")
def _duckdb_format_newer(name: Namer, /, *, path: str, found: int, expected: int, **_: Any) -> str:
    return (
        f"the parts in {path} are written in parquet store format {found} and "
        f"this build reads {expected}; upgrade outrage, or repack them with this one"
    )


@template("duckdb-format-older")
def _duckdb_format_older(name: Namer, /, *, path: str, found: int, expected: int, **_: Any) -> str:
    return (
        f"the parts in {path} are written in parquet store format {found}, and a "
        f"duckdb store reads only format {expected}: the older format's metadata "
        f"columns would have to be re-derived from every key. The parquet backend "
        f"still reads a single file of it; repack the parts to read them here."
    )


@template("parquet-build-wildcard")
def _parquet_build_wildcard(name: Namer, /, *, key: str, **_: Any) -> str:
    return (
        f"cannot pack {key!r}: a '?' is allocated by reading the store for a "
        f"free number, and a store being built has nothing to read"
    )


# -- the command line ------------------------------------------------------


@template("content-two-sources")
def _content_two_sources(name: Namer, /, **_: Any) -> str:
    return "give --content or --file, not both"


@template("content-unreadable")
def _content_unreadable(name: Namer, /, *, path: str, reason: str, **_: Any) -> str:
    return f"cannot read {path}: {reason}"


@template("content-missing")
def _content_missing(name: Namer, /, **_: Any) -> str:
    return "nothing to store: pass --content, --file, or pipe it in"


@template("copy-target-inside-source")
def _copy_target_inside_source(name: Namer, /, *, source: str, target: str, **_: Any) -> str:
    return (
        f"cannot copy {name(source)!r} beneath {name(target)!r}: the target is "
        "inside the source subtree, and a streaming copy would read what it just wrote"
    )


@template("copy-source-inside-target")
def _copy_source_inside_target(name: Namer, /, *, source: str, target: str, **_: Any) -> str:
    return (
        f"cannot re-root {name(source)!r} onto {name(target)!r}: the source is "
        "inside the target subtree, so a re-rooted copy would write back into "
        "what it is still reading. Copy it to a key outside the target first"
    )


@template("changed-since")
def _changed_since(
    name: Namer,
    /,
    *,
    spell: Speller,
    key: str,
    action: str,
    unchanged_since: str,
    changed_at: str,
    subtree: bool = True,
    **_: Any,
) -> str:
    # Both moments, because neither half is the story: what makes this a
    # refusal is that one is later than the other. The key named is the one the
    # run was about, not the document that moved -- an aggregate answers with a
    # time and not with a key, which is what makes it cost one query.
    #
    # What was looked at, because a plain delete takes the key and its metadata
    # and nothing else: saying "at or below it" there would send the reader
    # looking through a subtree the guard never asked about.
    moved = "something at or below it" if subtree else "it or its metadata"
    return (
        f"refusing to {action} {name(key)!r}: {moved} was "
        f"written at {changed_at}, after the {unchanged_since} you say you "
        f"looked at, so this would act on work done since. Nothing has been "
        f"changed. Look again and repeat the call with the newer time, or drop "
        f"{spell('unchanged_since')} to go ahead regardless"
    )


@template("unchanged-since-unreadable")
def _unchanged_since_unreadable(
    name: Namer, /, *, spell: Speller, unchanged_since: str, **_: Any
) -> str:
    return (
        f"{spell('unchanged_since')} must be an ISO 8601 timestamp, like "
        f"2026-09-03T10:15:00Z, and {unchanged_since!r} is not one"
    )


@template("unchanged-since-needed")
def _unchanged_since_needed(name: Namer, /, *, spell: Speller, on_conflict: str, **_: Any) -> str:
    return (
        f"{spell('on_conflict', on_conflict)} overwrites only what has not "
        f"changed since you looked, so it needs {spell('unchanged_since')} to "
        f"measure against. Pass the time you looked, or "
        f"{spell('on_conflict', OVERWRITE)} to replace whatever is there"
    )


@template("unchanged-since-unguarded")
def _unchanged_since_unguarded(
    name: Namer, /, *, spell: Speller, unchanged_since: str, **_: Any
) -> str:
    # The trap this exists for: a watermark beside plain `overwrite` reads like
    # a guard and is not one. It would refuse before the copy started and then
    # replace every collision after that, which is the half of the check nobody
    # asked for by itself.
    return (
        f"{spell('on_conflict', OVERWRITE)} replaces what is already there "
        f"whatever {spell('unchanged_since', unchanged_since)} says, so the "
        f"two disagree. Pass {spell('on_conflict', OVERWRITE_UNCHANGED)} to "
        f"keep what changed since, or drop {spell('unchanged_since')} to "
        f"overwrite regardless"
    )


# -- local document ingestion --------------------------------------------


@template("ingest-source-url")
def _ingest_source_url(name: Namer, /, *, source: str, **_: Any) -> str:
    return f"{source!r} is a URL; document ingestion accepts only a local file path"


@template("ingest-source-not-file")
def _ingest_source_not_file(name: Namer, /, *, source: str, reason: str, **_: Any) -> str:
    return f"cannot ingest {source}: it {reason}"


@template("ingest-source-unreadable")
def _ingest_source_unreadable(name: Namer, /, *, source: str, reason: str, **_: Any) -> str:
    return f"cannot read local document {source}: {reason}"


@template("ingest-documents-extra-missing")
def _ingest_documents_extra_missing(name: Namer, /, **_: Any) -> str:
    return "document conversion is not installed; install outrage with the 'documents' extra"


@template("ingest-format-unsupported")
def _ingest_format_unsupported(name: Namer, /, *, source: str, **_: Any) -> str:
    return f"MarkItDown has no converter for {source}"


@template("ingest-converter-dependency-missing")
def _ingest_converter_dependency_missing(
    name: Namer, /, *, source: str, reason: str, **_: Any
) -> str:
    return f"the converter for {source} is missing a dependency: {reason}"


@template("ingest-conversion-failed")
def _ingest_conversion_failed(name: Namer, /, *, source: str, reason: str, **_: Any) -> str:
    return f"MarkItDown could not convert {source}: {reason}"


@template("ingest-target-exists")
def _ingest_target_exists(name: Namer, /, *, spell: Speller, key: str, **_: Any) -> str:
    return (
        f"refusing to replace the document already stored at {name(key)!r}; "
        f"pass {spell('overwrite')} to replace it"
    )


# -- Document contents ---------------------------------------------------


@template("contents-metadata-name")
def _contents_metadata_name(name: Namer, /, *, metadata_name: str, **_: Any) -> str:
    return (
        f"{metadata_name!r} is not a metadata name; pass one non-empty key "
        "segment without the leading '!'"
    )


@template("contents-not-markdown")
def _contents_not_markdown(name: Namer, /, *, key: str, format: str | None, **_: Any) -> str:
    return (
        f"cannot make contents for {name(key)!r}: its format is {format!r}, "
        "not 'markdown' or 'html'"
    )


@template("metadata-format")
def _metadata_format(name: Namer, /, *, key: str, format: str | None, **_: Any) -> str:
    return (
        f"cannot make metadata for {name(key)!r}: its format is {format!r}, "
        "not 'markdown' or 'html'"
    )


@template("metadata-name-conflict")
def _metadata_name_conflict(name: Namer, /, *, metadata_name: str, **_: Any) -> str:
    return (
        f"cannot write contents as {metadata_name!r} while generating a title: "
        "both would be the same '!title' metadata; choose another metadata_name "
        "or set contents or title to false"
    )


__all__ = [
    "MCP",
    "Namer",
    "NoteTable",
    "Speller",
    "codes",
    "flag",
    "keyword",
    "render",
    "template",
]
