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

**There are two conftest.py in this repository and they are unrelated.** This
one is six lines of path selection and nothing else. The other,
``tests/conftest.py``, holds the shared test helpers - ``raises_rendered``,
``walk_documents`` and the rest - and no path handling at all.

**This file has to be at the repository root.** pytest auto-loads a
``conftest.py`` from the rootdir and from the directories it collects, so
anywhere else - ``tools/``, say - it simply never runs, and then ``import
outrage`` resolves to whatever is installed. That is not a loud failure: moving
it and running the suite passes 1683 tests against *a different copy of the
package*, and only ``test_the_checkout_is_what_is_under_test`` notices.
Measured on 2026-08-29, which is the second time this question has been asked.

Nor can it become ``pythonpath = ["src"]`` in ``pyproject.toml``, tempting as
one less root file is: that setting is static, and the whole point here is the
``OUTRAGE_TEST_INSTALLED`` switch that the release process needs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"

TEST_INSTALLED = bool(os.environ.get("OUTRAGE_TEST_INSTALLED"))

if not TEST_INSTALLED:
    sys.path.insert(0, str(SRC))
