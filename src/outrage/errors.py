"""The one base every failure a caller is meant to see inherits from.

A tuple of exception classes at the front-end boundary has to grow with every
command that raises something new, and one that is missed catches nothing. A
shared base is what stops that, and it is not the same as catching
``Exception``, which would swallow the bugs as well.

The distinction being drawn is not severity. It is whether the failure is
*about the request* - a key that holds nothing, a pattern that does not occur,
a configuration file that will not parse, a store that is not there. Those are
answers, and a front end should render them as one line rather than a
traceback. Anything else reaching the top is a bug in outrage, and a traceback is
the correct output for a bug.

Each subclass keeps the builtin it already inherited, so ``except LookupError``
around a store read goes on working and no existing caller has to change.

**An error carries facts, not prose.** A message is written by the front end,
from a ``code`` and whatever ``details`` that code needs -- see
:mod:`outrage.messages`. The library layers have no business composing a sentence
for a person to read: they do not know who is reading it, and in the one case
that matters they cannot know. A key inside a mounted store is called
``python/nope`` there and ``ref/python/nope`` to anyone outside, so a sentence
built in :mod:`outrage.store` is wrong for the MCP server or wrong for the command
line, and there is no third choice. That was a live defect, not a hypothetical
one, and this is the fix.

``__str__`` is therefore a **developer** rendering, not a message. It names the
class, the code and the details, which is what a traceback or a log wants and
is deliberately not what a user wants: anything that prints an error straight
at somebody now looks wrong when it is read, rather than looking fine and
naming a key that does not exist.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class OutrageError(Exception):
    """A failure a caller asked for and should be told about in a sentence.

    ``code`` names *which* failure, uniquely across the whole codebase, and is
    what :mod:`outrage.messages` renders. ``details`` are the facts that message
    needs, by name.
    """

    def __init__(self, code: str, **details: Any) -> None:
        # Passed to Exception too, so `raise ... from` chains, pickling and
        # anything reading `args` keep working.
        super().__init__(code, details)
        self.code = code
        self.details: Mapping[str, Any] = details

    def __str__(self) -> str:
        inside = ", ".join(f"{name}={value!r}" for name, value in self.details.items())
        return f"{type(self).__name__}({self.code!r}{', ' if inside else ''}{inside})"

    __repr__ = __str__


__all__ = ["OutrageError"]
