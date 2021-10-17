#!/usr/bin/env bash
set -e
set -x

SRC=${1:-"src/zenml tests"}

export ZENML_DEBUG=1
# mypy src/zenml
interrogate $SRC -c pyproject.toml --generate-badge docs/interrogate.svg