"""Shared test helpers.

``raises_rendered`` exists because an error no longer carries its own message.
``pytest.raises(cls, match=...)`` matches against ``str(exc)``, which is now a
developer rendering — the class, the code and the details — so a test that
wants to assert what a *person* reads has to render it the way a front end
does. See :mod:`rage.messages`.

Same call shape as ``pytest.raises`` so a test reads the way it did, and it
still yields the ``ExceptionInfo``, so a test that also wants the code or the
details can have them.
"""

from __future__ import annotations

import contextlib
import re
from collections.abc import Iterator
from typing import Any

import pytest

from rage import messages


@contextlib.contextmanager
def raises_rendered(
    error: type[BaseException], match: str | None = None, *, name: Any = None
) -> Iterator[pytest.ExceptionInfo[Any]]:
    """Assert ``error`` is raised, and that its **rendered** message matches.

    ``name`` is passed through to :func:`rage.messages.render`, for the tests
    that care which front end is doing the naming.
    """
    with pytest.raises(error) as raised:
        yield raised

    if match is None:
        return
    rendered = messages.render(raised.value, name=name)
    assert re.search(match, rendered), f"{match!r} does not match {rendered!r}"
