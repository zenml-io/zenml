#!/bin/sh -e
set -x

autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place zenml tests --exclude=__init__.py
black zenml tests
isort zenml tests
