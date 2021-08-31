#!/usr/bin/env bash
set -e
set -x

mypy zenml
flake8 zenml tests
isort zenml tests scripts --check-only
black zenml tests  --check