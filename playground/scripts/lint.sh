#!/usr/bin/env bash
set -e
set -x

mypy zenml
flake8 zenml tests
black zenml tests  --check
isort zenml tests scripts --check-only