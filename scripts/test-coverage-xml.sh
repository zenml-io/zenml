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

if [ -n "$1" ]; then
    coverage run -m pytest $TEST_SRC --color=yes
else
    coverage run -m pytest tests/unit --color=yes
    # the following two commands are run separately as our example integration
    # tests mess with the dependencies installed inside the main testing
    # environment which causes tests inside test_integration_stack_components.py
    # to fail. Replace the following two calls by
    # `coverage run -m pytest test/integration --color=yes`
    # once we fix this.
    coverage run -m pytest tests/integration/test_integration_stack_components.py --color=yes --verbosity=8 --full-trace --tb=long --log-level=0
    coverage run -m pytest tests/integration --color=yes --ignore=tests/integration/test_integration_stack_components.py --verbosity=8 --full-trace --tb=long --log-level=0
fi
coverage combine
coverage report --show-missing
coverage xml
