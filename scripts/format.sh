#!/bin/sh -e
set -x

SRC=${1:-"src/zenml tests examples docs/mkdocstrings_helper.py"}

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place $SRC --exclude=__init__.py
# sorts imports
ruff $SRC --select I --fix --ignore D
black $SRC
