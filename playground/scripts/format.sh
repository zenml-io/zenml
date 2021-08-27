#!/bin/sh -e
set -x

# maybe add autoflake?
black zenml tests
isort zenml tests
