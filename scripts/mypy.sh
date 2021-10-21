#!/usr/bin/env bash
# Usage:
# `mypy.sh [--install-types]`
# * --install-types: Installs missing type stubs before running mypy

set -e
set -x

if [ "$1" = "--install-types" ]
then
  MYPY_ARGS="--install-types --non-interactive"
fi

SRC="src/zenml"

export ZENML_DEBUG=1
mypy $MYPY_ARGS "$SRC"
