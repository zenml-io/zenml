#!/usr/bin/env bash
set -e
set -x
set -o pipefail

SRC=${1:-"src/zenml tests examples"}
SRC_NO_TESTS=${1:-"src/zenml tests/harness"}

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
flake8 $SRC
autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place $SRC --exclude=__init__.py --check | ( grep -v "No issues detected" || true )
isort $SRC scripts --check-only
black $SRC  --check

# check type annotations
mypy $SRC_NO_TESTS
