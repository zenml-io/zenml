#!/usr/bin/env bash
set -e
set -x

# mypy src/zenml
flake8 src/zenml tests
autoflake src/zenml --check
isort src/zenml tests scripts --check-only
black src/zenml tests  --check
interrogate src/zenml -c pyproject.toml