#!/usr/bin/env bash

set -e

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
poetry config repositories.test-pypi https://test.pypi.org/legacy/
poetry publish -r testpypi --build --username $PYPI_USERNAME --password $PYPI_PASSWORD
