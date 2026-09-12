"""Decide which copy of ``outrage`` this suite tests, before anything imports it.

``wikiimport`` is a separate distribution that depends on a released
``outrage``, but it is developed here as a sibling of the checkout that
produces it -- and it is the first real consumer of ``ParquetStore.build_part``,
so a run that silently tested an *installed* ``outrage`` instead of the one
beside it would be testing the wrong half of the pair.

That is not hypothetical. Before this file existed the answer came from
whatever editable install happened to be in the environment: the resolved code
was this checkout while its ``dist-info`` still said an older version, so
neither the import nor the dependency pin was a witness to what ran.

By default the suite tests **the sibling checkout**: its ``src`` goes to the
front of the path, ahead of any installed copy. Set ``OUTRAGE_TEST_INSTALLED=1``
to test the installed one instead, which is what a release candidate wants.
This mirrors the repository root's ``conftest.py``, deliberately -- the two
answer the same question for the two distributions, and the switch is spelled
the same way so one environment variable settles both.

``wikiimport`` itself is not handled here. It comes from ``pythonpath`` in
``pyproject.toml``, which is static and always the same answer; only the
question above needs a switch, which is why that one cannot be a setting.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

OUTRAGE_SRC = Path(__file__).resolve().parent.parent / "src"

TEST_INSTALLED = bool(os.environ.get("OUTRAGE_TEST_INSTALLED"))

if not TEST_INSTALLED and OUTRAGE_SRC.is_dir():
    sys.path.insert(0, str(OUTRAGE_SRC))
