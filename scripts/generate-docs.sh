#!/bin/sh -e
set -x

SRC=${1:-"src/zenml/"}

export ZENML_DEBUG=1
rm -rf docs/sphinx_docs/_build/ || true
sphinx-apidoc -o docs/sphinx_docs/ $SRC
cd docs/sphinx_docs/
make html