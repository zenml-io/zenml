#!/usr/bin/env bash

set -e
set -x

# If only unittests are needed call
# test-coverage-xml.sh unit
# For only integration tests call
# test-coverage-xml.sh integration
TEST_SRC="tests/"${1:-""}

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
coverage run -m pytest $TEST_SRC --color=yes -v
coverage combine
coverage report --show-missing
coverage xml
