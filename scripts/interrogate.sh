#!/usr/bin/env bash
set -e
set -x

SRC=${1:-"src/zenml tests"}

# mypy src/zenml
interrogate $SRC -c pyproject.toml --generate-badge docs/interrogate.svg