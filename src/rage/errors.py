"""The one base every failure a caller is meant to see inherits from.

``cli.main`` used to catch a tuple that grew with each command, and
``planned/cli`` recorded the rule for when that stopped being the right shape:
a shared base, rather than catching ``Exception``. The fourth command is where
it came due.

The distinction being drawn is not severity. It is whether the failure is
*about the request* — a key that holds nothing, a pattern that does not occur,
a configuration file that will not parse, a store that is not there. Those are
answers, and a front end should render them as one line rather than a
traceback. Anything else reaching the top is a bug in rage, and a traceback is
the correct output for a bug.

Each subclass keeps the builtin it already inherited, so ``except LookupError``
around a store read goes on working and no existing caller has to change.
"""

from __future__ import annotations


class RageError(Exception):
    """A failure a caller asked for and should be told about in a sentence."""


__all__ = ["RageError"]
