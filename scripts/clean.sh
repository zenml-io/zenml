#!/bin/sh -e
set -x

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false

rm -rf dist \
rm -rf docs/build \
rm -rf *.egg-info \
rm -rf .tox \
rm -rf .pytest_cache \
rm -rf .mypy_cache \
rm -rf .ipynb_checkpoints