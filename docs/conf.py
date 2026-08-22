"""Sphinx configuration for the Outrage API documentation.

The docstrings in ``src/outrage`` are already written as reStructuredText, with
``:class:`` and ``:mod:`` roles and ``#:`` comments on module constants, so
autodoc renders them without a translation layer and no docstring-style
extension is needed.
"""

from __future__ import annotations

import sys
from pathlib import Path

# The package is normally installed editable into the project's environment,
# but keep a working build in a bare checkout too.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from outrage import __version__  # noqa: E402

project = "Outrage"
author = "John Reynolds"
copyright = "2026, John Reynolds"
version = __version__
release = __version__

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
]

# Read the modules in the order they are written, so a page follows the file
# rather than the alphabet -- which is what a review wants to follow.
autodoc_member_order = "bysource"
autodoc_typehints = "signature"
autodoc_typehints_format = "short"
autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
    # Dataclass fields and the few methods carrying no docstring of their own.
    # A frozen result type is mostly its fields, so hiding them would leave
    # `Entry` and `Excerpt` documented as a sentence and nothing else.
    #
    # This does not reach module constants: autodoc needs a `#:` comment for
    # those, whatever this says. `__all__` is the statement of what is public,
    # so nothing in it should be missing here -- tests/test_public_api.py keeps
    # that list honest, and a name it admits still needs its own `#:` line.
    "undoc-members": True,
}

# `from __future__ import annotations` makes every annotation a string; this
# keeps dataclass fields and signatures rendering as the names in the source.
autodoc_preserve_defaults = True

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
# Resolved from the network on the first build and cached; a build with no
# network still succeeds, with a warning for each unresolved reference.
intersphinx_timeout = 5

nitpicky = False

exclude_patterns = ["_build"]

html_theme = "furo"
html_title = f"Outrage {version}"
