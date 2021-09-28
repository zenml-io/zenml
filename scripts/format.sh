#!/bin/sh -e
set -x

autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place src/zenml tests --exclude=__init__.py,legacy/*
isort src/zenml tests --skip  legacy/
black src/zenml tests --exclude legacy/