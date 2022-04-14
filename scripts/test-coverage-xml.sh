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
export EVIDENTLY_DISABLE_TELEMETRY=1

# The '-n auto' flag ensures that tests run in parallel on
# all available CPU cores.
# The '-vv' flag enables pytest-clarity output when tests fail.
if [ -n "$1" ]; then
    coverage run -m pytest $TEST_SRC --color=yes -vv
else
    coverage run -m pytest tests/unit --color=yes -vv
    coverage run -m pytest tests/integration --use-virtualenv --color=yes -vv
fi
coverage combine
coverage report --show-missing
coverage xml
