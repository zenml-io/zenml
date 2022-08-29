#!/usr/bin/env bash
set -e
set -x

SRC=${1:-"src/zenml tests examples"}
SRC_NO_TESTS=${1:-"src/zenml"}

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
flake8 $SRC
autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place $SRC --exclude=__init__.py --check
isort $SRC scripts --check-only
black $SRC  --check

# check type annotations
mypy $SRC_NO_TESTS
