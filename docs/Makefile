# Minimal makefile for Sphinx documentation.
#
# **Run this in an environment that has the project's `docs` extra installed.**
# Every target here needs `sphinx` and `sphinx-markdown-builder`, and `markdown`
# and `documents` write files that are committed, so the environment is part of
# the build rather than a convenience. `environment.yml` names it `outrage`;
# `pip install -e '.[docs]'` is the other way to get one. `check-env` below says
# so when it is missing, rather than leaving Make to report an import error that
# names neither the interpreter nor the package.
#
# PYTHON is whatever the activated environment resolves, and can be overridden:
# make markdown PYTHON=/path/to/python
#
# It was an absolute path into one miniforge environment until 2026-09-05 --
# committed, and correct on exactly one machine -- and the `rage` environment
# until 2026-08-29, before `environment.yml` named `outrage` and before the
# Python floor dropped to 3.12. `reference/env` in the store is that record.

PYTHON        ?= python
SPHINXOPTS    ?=
SPHINXBUILD   ?= $(PYTHON) -m sphinx
SOURCEDIR     = .
BUILDDIR      = _build

.PHONY: help check-env strict markdown documents clean Makefile

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# A sentence rather than a traceback. Both packages are checked because only one
# of them is the obvious one: a build with `sphinx` and no
# `sphinx-markdown-builder` fails on an unknown builder name, several screens in,
# and reads like a broken Makefile rather than a missing install.
check-env:
	@$(PYTHON) -c 'import sphinx, sphinx_markdown_builder' 2>/dev/null || { \
		echo "$(PYTHON) has no sphinx and sphinx-markdown-builder."; \
		echo "Activate the project environment -- environment.yml names it 'outrage' --"; \
		echo "or install the extra:   pip install -e '.[docs]'"; \
		echo "Or name an interpreter: make $(MAKECMDGOALS) PYTHON=/path/to/python"; \
		exit 1; }

# Warnings are errors, and every page is rebuilt: what CI would run.
strict: check-env
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" -W --keep-going -a -E $(SPHINXOPTS) $(O)

# The same pages as markdown, for the API reference that ships in
# `src/outrage/documents/reference`. Written out rather than left to the pattern
# rule below, because two of its flags are load-bearing.
#
# **Its own doctree cache.** `-M` gives every builder the one `_build/doctrees`,
# smartquotes are a parse-time transform, and `smartquotes_excludes` in conf.py
# turns them off for this builder alone -- so a doctree cached by the HTML build
# carries en dashes that this build then writes into the markdown, and the order
# the two were last run in silently decides what is in the file. Found that way:
# `make strict && make markdown` emitted 275 of them.
#
# **Warnings are errors**, for the reason they are on `strict` and one more: a
# node type this builder does not handle is dropped from the output with only a
# warning to say so, which is how every keyword-only `*` went missing once.
#
# `-a -E` because the output is committed, so a run must not depend on what the
# last one left behind.
markdown: check-env
	@$(SPHINXBUILD) -b markdown "$(SOURCEDIR)" "$(BUILDDIR)/markdown" \
		-d "$(BUILDDIR)/doctrees-markdown" -W --keep-going -a -E $(SPHINXOPTS) $(O)

# The whole pipeline that produces `src/outrage/documents`, which is what a
# person actually wants: `markdown` alone leaves the pages in `_build` and the
# shipped tree untouched, and the steps after it were three commands nobody had
# written down anywhere but a test docstring.
#
# The last two sweep the **whole tree**, not the section the render wrote. That
# is deliberate for the indexes: `design` and `cli` are hand-written and their
# `!contents` goes stale on an ordinary edit rather than at a render, so the
# only run that could refresh them is one that does not care which half a
# document is in. `tests/test_shipped.py` is what fails when this has not been
# run; `tools/document_titles.py` skips a title that is already there, and
# `tools/document_contents.py` rewrites an index that has moved.
documents: check-env markdown
	@$(PYTHON) ../tools/render_reference.py "$(BUILDDIR)/markdown" ../src/outrage/documents
	@$(PYTHON) ../tools/document_titles.py ../src/outrage/documents
	@$(PYTHON) ../tools/document_contents.py ../src/outrage/documents

clean:
	@rm -rf "$(BUILDDIR)"

%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
