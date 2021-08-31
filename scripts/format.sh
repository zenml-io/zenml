#!/bin/sh -e
set -x

autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place zenml tests --exclude=__init__.py,zenml/legacy/*
isort zenml tests --skip  zenml/legacy/
black zenml tests --exclude zenml/legacy/