#!/usr/bin/env bash

set -e

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
python -m poetry publish --build --username $PYPI_USERNAME --password $PYPI_PASSWORD