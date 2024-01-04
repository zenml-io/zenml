#!/usr/bin/env bash
set -e
set -x
set -o pipefail

SRC=${1:-"src/zenml tests examples"}
SRC_NO_TESTS=${1:-"src/zenml tests/harness"}
TESTS_EXAMPLES=${1:-"tests examples"}

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
ruff $SRC_NO_TESTS
# TODO: Fix docstrings in tests and examples and remove the `--extend-ignore D` flag
ruff $TESTS_EXAMPLES --extend-ignore D

# checks for yaml formatting errors
yamlfix --check -v .github

# autoflake replacement: checks for unused imports and variables
ruff $SRC --select F401,F841 --exclude "__init__.py" --isolated

ruff format $SRC  --check

# check type annotations
mypy $SRC_NO_TESTS
