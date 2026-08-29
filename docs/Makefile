# Minimal makefile for Sphinx documentation.
#
# The project's interpreter is the `rage` conda environment, not whatever
# `python` the shell resolves to; PYTHON below is that interpreter and can be
# overridden: make html PYTHON=python

PYTHON        ?= /Users/john/miniforge3/envs/rage/bin/python
SPHINXOPTS    ?=
SPHINXBUILD   ?= $(PYTHON) -m sphinx
SOURCEDIR     = .
BUILDDIR      = _build

.PHONY: help strict markdown clean Makefile

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

clean:
	@rm -rf "$(BUILDDIR)"

%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
