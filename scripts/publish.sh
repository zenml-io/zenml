#!/usr/bin/env bash

set -e

python -m poetry publish --build --username $PYPI_USERNAME --password $PYPI_PASSWORD