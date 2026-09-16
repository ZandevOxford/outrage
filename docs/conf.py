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
    # Adds the `markdown` builder and nothing else -- the HTML build is
    # unaffected by its presence. See "The markdown build" at the foot of
    # this file for what that builder needs on top.
    "sphinx_markdown_builder",
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

# **The inventory is committed**, as `python_objects.inv` beside this file, and
# the second element of the pair names it. A path there is read straight off
# disk -- no fetch, no cache entry written or consulted. The target URI stays
# the remote one, because that is what gets written into the links; only the
# inventory is local.
#
# It is committed because the markdown build's output is committed. Fetched
# instead, the inventory arrives through a cache that *expires* after
# `intersphinx_cache_limit` days, so the pages a build writes depend on when it
# last ran rather than on anything in the tree, and upstream moving a URL
# rewrites every link to it under whichever build happens to be the first past
# the expiry. That moved four Python library pages under a reader's feet and
# changed 26 committed pages at once. Committing it also means no target here
# needs the network, which matters under `-W`, where an unresolved reference is
# an error rather than a warning.
#
# `make inventory` in `docs/` refetches it, deliberately and as its own
# reviewable change.
intersphinx_mapping = {"python": ("https://docs.python.org/3", "python_objects.inv")}
# For any remote mapping added above later. The committed inventory reaches no
# network and is not subject to it.
intersphinx_timeout = 5

nitpicky = False

exclude_patterns = ["_build"]

html_theme = "furo"
html_title = f"Outrage {version}"


# ---------------------------------------------------------------------------
# The markdown build
#
# `make markdown` renders the same pages as markdown, for the API reference
# that ships in `src/outrage/documents/reference` and is mounted at
# `outrage/reference`. `context/71` in the outrage store is the design; the two
# settings below are both repairs, and each is here because the build is
# otherwise wrong in a way that does not fail.
# ---------------------------------------------------------------------------

# Smartquotes rewrite every `--` in a docstring as an en dash. That is right
# for HTML and wrong for a file that is committed and read as source, so it is
# switched off **per builder** rather than globally -- the HTML keeps its
# typography. The first two entries are Sphinx's own default, which naming this
# setting at all would otherwise drop.
smartquotes_excludes = {"languages": ["ja"], "builders": ["man", "text", "markdown"]}


def setup(app):
    """Teach the markdown builder the one node it drops silently.

    Sphinx wraps the PEP 3102 keyword-only ``*`` separator in a docutils
    ``abbreviation`` node, carrying the tooltip a reader hovers. The markdown
    builder has no handler for that node, so it warns and emits nothing, and a
    signature comes out as ``f(a, b, , log=None)`` -- a doubled comma, and no
    longer the truth about which parameters are keyword-only. It affected 79
    signatures here.

    The node's child is an ordinary text node, so doing nothing in both
    directions is the whole fix: the default handling was the only thing in the
    way. Written as visitors on the translator rather than as a docutils
    ``unknown_visit`` override, because this repairs one known node and should
    stop compiling if the builder ever grows its own handler with a different
    name.

    Worth knowing beyond this one node: an unhandled node type in that builder
    **loses content without failing the build**, which is why a markdown build
    is worth running under ``-W`` the way `make strict` runs the HTML one.
    """
    from sphinx_markdown_builder.translator import MarkdownTranslator

    def visit_abbreviation(self, node):
        pass

    def depart_abbreviation(self, node):
        pass

    MarkdownTranslator.visit_abbreviation = visit_abbreviation
    MarkdownTranslator.depart_abbreviation = depart_abbreviation
