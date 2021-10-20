#!/usr/bin/env bash
set -e
set -x

SRC=${1:-"src/zenml"}

export ZENML_DEBUG=1
mypy --python-version=3.6 src/zenml