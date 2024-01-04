#!/bin/sh -e
set -x

# Default source directories
SRC=${1:-"src/zenml tests examples docs/mkdocstrings_helper.py scripts"}

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false

# autoflake replacement: removes unused imports and variables
ruff $SRC --select F401,F841 --fix --exclude "__init__.py" --isolated

# sorts imports
ruff $SRC --select I --fix --ignore D
ruff format $SRC

# Flag check for skipping yamlfix
SKIP_YAMLFIX=false
for arg in "$@"
do
    if [ "$arg" = "--no-yamlfix" ]; then
        SKIP_YAMLFIX=true
        break
    fi
done

# standardises / formats CI yaml files
if [ "$SKIP_YAMLFIX" = false ]; then
    yamlfix .github tests
fi
