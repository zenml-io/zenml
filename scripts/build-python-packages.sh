#!/bin/bash
set -e
set -x
set -o pipefail

# Build the regular package
uv build

# Build the slim package. There is no support to pass a different pyproject.toml file
# to the build command, so we need to temporarily rename the files.
mv pyproject.toml pyproject-full.toml
mv pyproject-slim.toml pyproject.toml
uv build
mv pyproject.toml pyproject-slim.toml
mv pyproject-full.toml pyproject.toml
