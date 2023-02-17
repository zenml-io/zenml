#!/usr/bin/env bash

set -e

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false

# compile the requirements files
python -m piptools compile -o requirements.txt pyproject.toml --resolver=backtracking --generate-hashes

python -m piptools compile --extra dev -o dev-requirements.txt pyproject.toml --resolver=backtracking --generate-hashes
