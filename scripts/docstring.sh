#!/usr/bin/env bash
set -e
set -x

DOCSTRING_SRC=${1:-"src/zenml tests/harness"}

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false

pydoclint $DOCSTRING_SRC
