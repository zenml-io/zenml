#!/usr/bin/env bash
set -e
set -x

SRC=${1:-"src/zenml"}

# mypy src/zenml
interrogate $SRC -c pyproject.toml --generate-badge docs/interrogate.svg