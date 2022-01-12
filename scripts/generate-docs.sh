#!/bin/sh -e
set -x

SRC="src/zenml/"
VERSION=""


while :; do
  case "${1-}" in
  -s | --source)
    SRC="${2-}"
    shift
    ;;
  -v | --version)
    VERSION="${2-}"
    shift
    ;;
  -?*) die "Unknown option: $1" ;;
  *) break ;;
  esac
  shift
done


export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
rm -rf docs/sphinx_docs/_build/ || true
rm -rf docs/sphinx_docs/api_reference || true

# only show documented members of a module
export SPHINX_APIDOC_OPTIONS=members,ignore-module-all

if [ -n "$VERSION" ]; then
  sphinx-apidoc --force --separate --no-toc --module-first --templatedir docs/sphinx_docs/_templates -V $VERSION -o docs/sphinx_docs/api_reference $SRC
else
  sphinx-apidoc --force --separate --no-toc --module-first --templatedir docs/sphinx_docs/_templates -o docs/sphinx_docs/api_reference $SRC
fi

cd docs/sphinx_docs/
make html
