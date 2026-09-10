"""The published source names nothing in this project's own store.

A comment or docstring in ``src/`` or ``tools/`` is read by someone who has the
repository and not the store, and a docstring is rendered into the published
reference as well, so a key there points at something the reader cannot open.
The argument belongs in the comment; the pointer belongs in ``file_notes``.

This is only the searchable part of that rule. A key written without its
namespace root slips past it, and so does a comment narrating a change rather
than saying why the code is shaped the way it is. ``context/`` is also the key
grammar's own example namespace, so only a thread number the size real ones
have reached counts as a reference; ``context/5/state`` is an example.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent
REFERENCE = re.compile(r"\b(?:plans|issues)/|\bcontext/\d{3,}")


def test_no_store_references_in_published_source():
    found = [
        f"{path.relative_to(ROOT)}:{number}: {line.strip()}"
        for folder in ("src", "tools")
        for path in sorted((ROOT / folder).rglob("*.py"))
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if REFERENCE.search(line)
    ]
    assert not found, "store keys in published source:\n" + "\n".join(found)
