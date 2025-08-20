# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = python -msphinx
SPHINXPROJ    = lazyscribe
SOURCEDIR     = .
BUILDDIR      = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile clean html dirhtml singlehtml

clean: Makefile
	@$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

html: Makefile
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

dirhtml: Makefile
	@$(SPHINXBUILD) -M dirhtml "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

singlehtml: Makefile
	@$(SPHINXBUILD) -M singlehtml "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
