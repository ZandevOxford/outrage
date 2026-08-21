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

.PHONY: help strict clean Makefile

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Warnings are errors, and every page is rebuilt: what CI would run.
strict:
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" -W --keep-going -a -E $(SPHINXOPTS) $(O)

clean:
	@rm -rf "$(BUILDDIR)"

%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
