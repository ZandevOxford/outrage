"""What an answer that *worked* has to remark on, carried the way a failure is.

A note is a sentence beside a successful result: the document shrank, a write
went past a check nobody could make, a listing stopped at a mount. Errors have
had a wording layer since the day the two front ends disagreed about what a key
was called; successful answers had none, and everything said about one was
built where it was noticed, in whichever front end happened to be looking.

**That gap is where seven defects came from in two days**, every one of them a
correct write with a wrong sentence beside it and a green suite over both. A
message is a second implementation of the operation's semantics, written in
English, and nothing keeps the two in step -- an ordinary duplicated-logic
defect that does not look like one, because the duplicate is prose.

**Why a note needs a carrier of its own.** An error rides on the exception: it
holds the code, it propagates by itself, and the front end renders it where the
reader is finally known. A note is found on a *success* path, where there is
nothing to raise, so the result object carries it instead -- a list of
:class:`Note`, each a code and the facts that code's sentence needs, exactly
the shape :class:`~outrage.errors.OutrageError` already has.

**A note carries facts, not prose**, for the reason an error does not: the
layer that noticed the situation does not know who is reading, and in this
system it cannot. See :mod:`outrage.messages` for where the sentence is
written, and for why notes are worded per audience while errors are worded once
and spelled twice.

``__str__`` is a **developer** rendering, like an error's and for the same
reason: anything printing a note straight at a person looks wrong when it is
read, rather than looking fine and being a sentence nobody chose.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class Note:
    """One situation worth remarking on, named by ``code`` and carrying its facts.

    ``code`` names *which* remark, uniquely across the whole codebase, and is
    what a table in :mod:`outrage.messages` renders -- or deliberately declines
    to. ``details`` are the facts that sentence needs, by name.

    Equality is by code and details, so a test can say which notes an operation
    produced without reading anybody's prose. There is no hash: a detail is
    whatever the situation held, and some of them are lists.
    """

    def __init__(self, code: str, **details: Any) -> None:
        self.code = code
        self.details: Mapping[str, Any] = details

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Note):
            return NotImplemented
        return self.code == other.code and dict(self.details) == dict(other.details)

    __hash__ = None  # type: ignore[assignment]

    def __str__(self) -> str:
        inside = ", ".join(f"{name}={value!r}" for name, value in self.details.items())
        return f"{type(self).__name__}({self.code!r}{', ' if inside else ''}{inside})"

    __repr__ = __str__


__all__ = ["Note"]
