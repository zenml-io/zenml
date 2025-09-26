#!/usr/bin/env bash

set -e
set -x

# If only unittests are needed call
# test-coverage-xml.sh unit
# For only integration tests call
# test-coverage-xml.sh integration
# To store durations, add a fifth argument 'store-durations'
TEST_SRC="tests/"${1:-""}
TEST_ENVIRONMENT=${2:-"default"}
TEST_SPLITS=${3:-"1"}
TEST_GROUP=${4:-"1"}
STORE_DURATIONS=${5:-""}

# Control flaky test retries via environment variables.
# - PYTEST_RERUNS: non-negative integer (0 disables reruns), defaults to 3 if unset or invalid.
# - PYTEST_RERUNS_DELAY: non-negative integer delay between reruns in seconds, defaults to 5 if unset or invalid.
# Validation guards against misconfiguration in CI while allowing explicit opt-out with 0.
RERUNS_DEFAULT=3
DELAY_DEFAULT=5

if [[ -n "${PYTEST_RERUNS+x}" ]]; then
    RERUNS="$PYTEST_RERUNS"
else
    RERUNS="$RERUNS_DEFAULT"
fi
if ! [[ "$RERUNS" =~ ^[0-9]+$ ]]; then
    echo "Warning: PYTEST_RERUNS='$RERUNS' is invalid. Falling back to ${RERUNS_DEFAULT}." >&2
    RERUNS="$RERUNS_DEFAULT"
fi

if [[ -n "${PYTEST_RERUNS_DELAY+x}" ]]; then
    RERUNS_DELAY="$PYTEST_RERUNS_DELAY"
else
    RERUNS_DELAY="$DELAY_DEFAULT"
fi
if ! [[ "$RERUNS_DELAY" =~ ^[0-9]+$ ]]; then
    echo "Warning: PYTEST_RERUNS_DELAY='$RERUNS_DELAY' is invalid. Falling back to ${DELAY_DEFAULT}." >&2
    RERUNS_DELAY="$DELAY_DEFAULT"
fi

PYTEST_RERUN_ARGS=(--reruns "$RERUNS" --reruns-delay "$RERUNS_DELAY")

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
export EVIDENTLY_DISABLE_TELEMETRY=1

./zen-test environment provision $TEST_ENVIRONMENT

# The '-vv' flag enables pytest-clarity output when tests fail.
# Shows errors instantly in logs when test fails.
if [ -n "$1" ]; then
    if [ "$STORE_DURATIONS" == "store-durations" ]; then
        coverage run -m pytest $TEST_SRC --color=yes -vv --environment $TEST_ENVIRONMENT --no-provision --cleanup-docker --store-durations --durations-path=.test_durations "${PYTEST_RERUN_ARGS[@]}" --instafail
    else
        coverage run -m pytest $TEST_SRC --color=yes -vv --durations-path=.test_durations --splits=$TEST_SPLITS --group=$TEST_GROUP --splitting-algorithm least_duration --environment $TEST_ENVIRONMENT --no-provision --cleanup-docker "${PYTEST_RERUN_ARGS[@]}" --instafail
    fi
else
    if [ "$STORE_DURATIONS" == "store-durations" ]; then
        coverage run -m pytest tests/unit --color=yes -vv --environment $TEST_ENVIRONMENT --no-provision --store-durations --durations-path=.test_durations "${PYTEST_RERUN_ARGS[@]}" --instafail
        coverage run -m pytest tests/integration --color=yes -vv --environment $TEST_ENVIRONMENT --no-provision --cleanup-docker --store-durations --durations-path=.test_durations "${PYTEST_RERUN_ARGS[@]}" --instafail
    else
        coverage run -m pytest tests/unit --color=yes -vv --durations-path=.test_durations --splits=$TEST_SPLITS --group=$TEST_GROUP --splitting-algorithm least_duration --environment $TEST_ENVIRONMENT --no-provision "${PYTEST_RERUN_ARGS[@]}" --instafail
        coverage run -m pytest tests/integration --color=yes -vv --durations-path=.test_durations --splits=$TEST_SPLITS --group=$TEST_GROUP --splitting-algorithm least_duration --environment $TEST_ENVIRONMENT --no-provision --cleanup-docker "${PYTEST_RERUN_ARGS[@]}" --instafail
    fi
fi

./zen-test environment cleanup $TEST_ENVIRONMENT

coverage combine
coverage report --show-missing
coverage xml
