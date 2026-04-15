#!/usr/bin/env bash
# Focused local helper for docstring checks only.
# CI runs pydoclint through scripts/lint.sh instead.
set -e
set -x

DOCSTRING_SRC=${1:-"src/zenml tests/harness"}

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false

pydoclint $DOCSTRING_SRC
