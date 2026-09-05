# Minimal makefile for Sphinx documentation.
#
# The project's interpreter is the `outrage` conda environment, not whatever
# `python` the shell resolves to; PYTHON below is that interpreter and can be
# overridden: make html PYTHON=python
#
# It was the `rage` environment until 2026-08-29, which is the one that existed
# before `environment.yml` named `outrage` and before the Python floor dropped
# to 3.12. That name is retired; `reference/env` in the store is the record.

PYTHON        ?= /Users/john/miniforge3/envs/outrage/bin/python
SPHINXOPTS    ?=
SPHINXBUILD   ?= $(PYTHON) -m sphinx
SOURCEDIR     = .
BUILDDIR      = _build

.PHONY: help strict markdown documents clean Makefile

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Warnings are errors, and every page is rebuilt: what CI would run.
strict:
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
markdown:
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
documents: markdown
	@$(PYTHON) ../tools/render_reference.py "$(BUILDDIR)/markdown" ../src/outrage/documents
	@$(PYTHON) ../tools/document_titles.py ../src/outrage/documents
	@$(PYTHON) ../tools/document_contents.py ../src/outrage/documents

clean:
	@rm -rf "$(BUILDDIR)"

%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
