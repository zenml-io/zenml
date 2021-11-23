#!/usr/bin/env bash
set -e
set -x

SRC=${1:-"src/zenml"}

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
# mypy src/zenml
interrogate $SRC -c pyproject.toml --generate-badge docs/interrogate.svg