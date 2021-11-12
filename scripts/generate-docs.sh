#!/bin/sh -e
set -x

SRC=${1:-"src/zenml/"}

export ZENML_DEBUG=1
rm -rf docs/sphinx_docs/_build/ || true
rm -rf docs/sphinx_docs/api_reference || true

# only show documented members of a module
export SPHINX_APIDOC_OPTIONS=members,ignore-module-all

sphinx-apidoc --force --separate --no-toc --module-first --templatedir docs/sphinx_docs/_templates -o docs/sphinx_docs/api_reference $SRC
cd docs/sphinx_docs/
make html
