#!/bin/sh -e
set -x

rm -rf dist \
rm -rf docs/build \
rm -rf *.egg-info \
rm -rf .tox \
rm -rf .pytest_cache \
rm -rf .mypy_cache \
rm -rf .ipynb_checkpoints