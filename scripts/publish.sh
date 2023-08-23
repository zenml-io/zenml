#!/usr/bin/env bash

set -e

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
poetry publish --build --username __token__ --password $PYPI_PASSWORD
