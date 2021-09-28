#!/bin/sh -e
set -x

rm -rf docs/sphinx_docs/_build/ || true
sphinx-apidoc -o docs/sphinx_docs/ src/zenml/
cd docs/sphinx_docs/
make html