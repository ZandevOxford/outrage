"""What the command line says about a note, which is mostly nothing.

The second wording table. :mod:`outrage.messages` holds the errors both front
ends share and the tools' notes; this holds the command line's, and it is a
separate table rather than a second spelling of that one because the two front
ends are not answering the same question.

**An error must always be reported**, so only its spelling varies between
readers and one table with a speller covers both. **A note is optional**, so
what varies first is *whether it is said at all* -- and this front end says
almost none of them, because it has already said the same thing in its own
report. A tool answers with a structured result, where a count of what was
deleted cannot mention what was kept; a command prints a line per key as it
goes, and the keys it did not touch are visible in what it did not print.

So a table branching on who is reading would carry two meanings in one
template, which is the shape every message defect here has come out of. Two
tables keyed by one vocabulary of codes keep the *situation* shared and the
*sentence* local -- and a sentence local to this file writes ``--recursive``
itself, which is why notes need no speller where errors do.

**Silence is a decision, and it is written down.** Every code this table does
not word is passed to :meth:`~outrage.messages.NoteTable.silent` with a reason,
and ``tests/test_notes.py`` fails if one is neither worded nor silenced. Two
kinds of reason appear below and both are legitimate: the situation cannot
arise on a command line at all, or it can and this report already says so
better. What is not legitimate is an empty table, which reads the same whether
somebody decided or nobody looked.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .messages import Namer, NoteTable

#: What ``outrage`` says about a note, as against what the tools say.
CLI = NoteTable("the command line")


@CLI.template("document-shrank")
def _document_shrank(name: Namer, /, *, previous: int, stored: int, **_: Any) -> str:
    # The one note this front end wants more than the tools do. `outrage get >
    # file`, edit, `outrage set --file` is the documented way to edit a long
    # document from a shell, and the first use of it wrote an empty document
    # over a good one: the write succeeded, the report said how many characters
    # went in, and nothing said how many had been there.
    return (
        f"the document shrank from {previous} to {stored} characters; "
        f"if that was not intended, the previous content is gone"
    )


@CLI.template("mounts-refused-delete")
def _mounts_refused_delete(
    name: Namer, /, *, key: str, mounts: Sequence[str], unwritable: Sequence[str] = (), **_: Any
) -> str:
    # Said here because nothing else on this path can say it. Every other thing
    # a delete leaves behind is a key, and a key is printed or counted; a
    # read-only mount is not a key, so a delete that stops at one prints
    # exactly what a delete that took everything prints.
    #
    # Only a mount read-only by choice is told to drop the flag. A parquet or
    # duckdb store refuses however it is mounted, so the flag is not the reason.
    flagged = [mount for mount in mounts if mount not in unwritable]
    said = [
        f"{len(mounts)} read-only mounted store(s) below {name(key)} refuse a delete: "
        f"{', '.join(mounts)}; --recursive will not reach them either"
    ]
    if flagged:
        said.append(
            f"Mount {', '.join(flagged)} with --mount rather than --mount-ro to delete there too"
        )
    if unwritable:
        one = len(unwritable) == 1
        said.append(
            f"{', '.join(unwritable)} cannot be written however "
            f"{'it is' if one else 'they are'} mounted"
        )
    return ". ".join(said)


# -- and what it means not to say ------------------------------------------
#
# Ordered as the tools' table words them, so the two read side by side.

CLI.silent(
    "overwrote-a-change",
    "no write from here goes past a check: there is no --against, so a write "
    "either happens or is refused by --unchanged-since before it starts",
)
CLI.silent(
    "write-not-checked",
    "the same: a write nobody could check is every write this front end makes, "
    "and a warning on all of them is a warning on none",
)
CLI.silent(
    "edit-matched-nothing",
    "an edit here is the shell's own, between `outrage get` and `outrage set`, "
    "and nothing recorded what came out for the write to be compared against",
)
CLI.silent(
    "stored-a-copy",
    "for the same reason: a file has no record naming the key it came from, so "
    "a copy through the shell is indistinguishable from a write",
)
CLI.silent(
    "delete-was-a-dry-run",
    "`rm --dry-run` prints `would delete` against every key and then the moment "
    "it looked at, which says this in this front end's own flags",
)
CLI.silent(
    "keys-kept-below",
    "the report says it already, in its own words and its own spelling: "
    "`N keys below K remain; --recursive to take them too`",
)
CLI.silent(
    "copy-was-a-dry-run",
    "`copy --dry-run` prints `would write` per key and the watermark to repeat "
    "with, which is this note with a command line's flags in it",
)
CLI.silent(
    "keys-changed-since",
    "every key left alone is printed as it is reached, with `changed since` "
    "against it, and a copy that left one behind exits non-zero",
)
CLI.silent(
    "copy-stopped-at-limit",
    "there is no limit and no cursor here: `outrage copy` copies the whole "
    "selection, and a paged call is a thing only the tools make",
)
CLI.silent(
    "failures-sampled",
    "nothing is sampled: every failure is printed as it happens, with the "
    "reason beside it, which is what streaming the report buys",
)
CLI.silent(
    "copy-stopped-at-conflict",
    "the stopped key is the last line printed and nothing follows it, so what "
    "the copy did not reach is visible in the report rather than inferred",
)
CLI.silent(
    "mounts-refused-write",
    "unlike a delete, a refused write is a failed key: each one is printed with "
    "the refusal that names the mount, so the count is not the only account",
)
CLI.silent(
    "mount-replaced-another",
    "there is nothing to replace: this front end builds its table from scratch "
    "every run, and a mount lives exactly as long as the command",
)
CLI.silent(
    "mount-created-store",
    "dynamic mounting is offered only by the MCP server; startup and command-line "
    "mounts keep their existing report",
)
CLI.silent(
    "mount-shadows-keys",
    "the same table is built each run from flags the caller just typed, and "
    "`outrage mounts` is where what shadows what is read",
)
CLI.silent(
    "unmount-revealed-keys",
    "an unmount here is a `--unmount` on the command being run, so nothing was "
    "shadowed a moment ago for the reveal to be news",
)
CLI.silent(
    "remount-not-permanent",
    "nothing here is permanent to begin with: the table is the flags of one "
    "run, which is why there is no mount tool on this side to warn about",
)
CLI.silent(
    "remount-shipped-is-default",
    "the same reason, and one more: this front end does not carry the shipped "
    "documentation unless `--mount-docs` asked for it, so being mounted by "
    "default is not a fact about this side at all",
)
CLI.silent(
    "unmount-not-permanent",
    "the same reason as the mount it mirrors: `--unmount` here is a flag on the "
    "command being run, and advice about keeping it across a restart would be "
    "advice about the run that just ended",
)
CLI.silent(
    "unmount-of-a-dynamic-mount",
    "there are no dynamic mounts on this side: the table is the flags of one run",
)
CLI.silent(
    "exported-for-editing",
    "there is no round trip through an exported file here; `outrage get > file` "
    "and `outrage set --file` are the shell's, and it holds the path already",
)


__all__ = ["CLI"]
