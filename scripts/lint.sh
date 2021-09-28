#!/usr/bin/env bash
set -e
set -x

# mypy src/zenml
flake8 src/zenml tests
isort src/zenml tests scripts --check-only
black src/zenml tests  --check
interrogate src/zenml