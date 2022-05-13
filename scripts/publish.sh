#!/usr/bin/env bash

set -e

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
python -m poetry config repositories.test-pypi https://test.pypi.org/legacy/
python -m poetry publish -r testpypi --build --username $PYPI_USERNAME --password $PYPI_PASSWORD