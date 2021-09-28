#!/usr/bin/env bash
set -e
set -x

# mypy src/zenml
interrogate src/zenml -c pyproject.toml --generate-badge docs/interrogate.svg