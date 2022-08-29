#!/usr/bin/env bash
set -e
set -x

DOCSTRING_SRC=${1:-"src/zenml"}

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
interrogate $DOCSTRING_SRC -c pyproject.toml --color
pydocstyle $DOCSTRING_SRC -e --count --convention=google --add-ignore=D403
darglint -v 2 $DOCSTRING_SRC
