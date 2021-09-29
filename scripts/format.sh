#!/bin/sh -e
set -x

SRC=${1:-"src/zenml tests"}

autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place $SRC --exclude=__init__.py,legacy/*
isort src/zenml $SRC --skip  legacy/
black src/zenml $SRC --exclude legacy/