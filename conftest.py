"""Decide which copy of ``outrage`` the suite tests, before anything imports it.

This file exists because the answer used to depend on the environment and was
never stated. ``import outrage`` resolved to whatever was installed, so a run
in an environment holding a released build tested *that* and reported it as a
pass on the checkout - which is how 0.1.0 shipped a defect the suite could not
have caught. It is loaded before ``tests/conftest.py``, and so before any test
module, which is the only place this can be settled.

By default the suite tests **this checkout**: ``src`` goes to the front of the
path, ahead of any installed copy. Set ``OUTRAGE_TEST_INSTALLED=1`` to test the
installed one instead - which is worth doing against a release candidate, and
is the other half of the same question.

``tests/test_packaging.py`` asserts which of the two is in force, so a run
always says what it tested rather than leaving it to be inferred.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"

TEST_INSTALLED = bool(os.environ.get("OUTRAGE_TEST_INSTALLED"))

if not TEST_INSTALLED:
    sys.path.insert(0, str(SRC))
