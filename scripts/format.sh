#!/bin/sh -e
set -x

SRC=${1:-"src/zenml tests examples docs/mkdocstrings_helper.py scripts"}

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false

# autoflake replacement: removes unused imports and variables
ruff $SRC --select F401,F841 --fix --exclude "__init__.py" --isolated

# sorts imports
ruff $SRC --select I --fix --ignore D
ruff format $SRC

# standardises / formats CI yaml files
yamlfix .github

