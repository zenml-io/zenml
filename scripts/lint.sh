#!/usr/bin/env bash
set -e
set -x
set -o pipefail

# Default source directories
SRC=${1:-"src/zenml tests examples"}
SRC_NO_TESTS=${1:-"src/zenml tests/harness"}
TESTS_EXAMPLES=${1:-"tests examples"}

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
ruff check $SRC_NO_TESTS
# TODO: Fix docstrings in tests and examples and remove the `--extend-ignore D` flag
ruff check $TESTS_EXAMPLES --extend-ignore D --exclude "quickstart.ipynb"

# Flag check for skipping yamlfix
if [ "$OS" = "windows-latest" ]; then
    SKIP_YAMLFIX=true
else
    SKIP_YAMLFIX=false
    for arg in "$@"
    do
        if [ "$arg" = "--no-yamlfix" ]; then
            SKIP_YAMLFIX=true
            break
        fi
    done
fi

# checks for yaml formatting errors
if [ "$SKIP_YAMLFIX" = false ]; then
    yamlfix --check .github tests --exclude "dependabot.yml"
fi

# autoflake replacement: checks for unused imports and variables
ruff check $SRC --select F401,F841 --exclude "__init__.py" --isolated

ruff format $SRC  --check

# check type annotations
mypy $SRC_NO_TESTS
