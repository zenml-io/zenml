#!/usr/bin/env bash

set -e
set -x

measure_stage() {
    local stage="$1"
    shift
    local started_at
    local finished_at
    local elapsed

    started_at=$(date +%s)
    "$@"
    finished_at=$(date +%s)
    elapsed=$((finished_at - started_at))
    echo "CI_TIMING ${stage} ${elapsed}"
}

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
DURATIONS_FILE=".test_durations"

if ! [[ "$TEST_SPLITS" =~ ^[0-9]+$ ]] || [[ "$TEST_SPLITS" -lt 1 ]]; then
    echo "Warning: TEST_SPLITS='$TEST_SPLITS' is invalid. Falling back to 1." >&2
    TEST_SPLITS=1
fi

if ! [[ "$TEST_GROUP" =~ ^[0-9]+$ ]] || [[ "$TEST_GROUP" -lt 1 ]] || [[ "$TEST_GROUP" -gt "$TEST_SPLITS" ]]; then
    echo "Warning: TEST_GROUP='$TEST_GROUP' is invalid for TEST_SPLITS='$TEST_SPLITS'. Falling back to 1." >&2
    TEST_GROUP=1
fi

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
DURATIONS_ARGS=()
SPLIT_ARGS=()

if [[ "$STORE_DURATIONS" == "store-durations" ]]; then
    DURATIONS_ARGS=(--store-durations --durations-path="$DURATIONS_FILE")
elif [[ "$TEST_SPLITS" -gt 1 ]]; then
    if [[ -s "$DURATIONS_FILE" ]]; then
        DURATIONS_ARGS=(--durations-path="$DURATIONS_FILE")
        SPLIT_ARGS=(--splits="$TEST_SPLITS" --group="$TEST_GROUP" --splitting-algorithm least_duration)
    else
        echo "Warning: $DURATIONS_FILE is missing or empty. Falling back to duration_based_chunks splitting." >&2
        SPLIT_ARGS=(--splits="$TEST_SPLITS" --group="$TEST_GROUP" --splitting-algorithm duration_based_chunks)
    fi
fi

run_pytest() {
    local target="$1"
    shift
    local extra_args=("$@")

    coverage run -m pytest "$target" --color=yes -vv \
        "${DURATIONS_ARGS[@]}" \
        "${SPLIT_ARGS[@]}" \
        --environment "$TEST_ENVIRONMENT" \
        --no-provision \
        "${extra_args[@]}" \
        "${PYTEST_RERUN_ARGS[@]}" \
        --instafail
}

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
export EVIDENTLY_DISABLE_TELEMETRY=1

measure_stage provision ./zen-test environment provision "$TEST_ENVIRONMENT"

# The '-vv' flag enables pytest-clarity output when tests fail.
# Shows errors instantly in logs when test fails.
if [ -n "$1" ]; then
    measure_stage pytest_targeted run_pytest "$TEST_SRC" --cleanup-docker
else
    measure_stage pytest_unit run_pytest tests/unit
    measure_stage pytest_integration run_pytest tests/integration --cleanup-docker
fi

measure_stage cleanup ./zen-test environment cleanup "$TEST_ENVIRONMENT"

if [[ "${CI_SKIP_COVERAGE_XML:-false}" == "true" ]]; then
    echo "CI_TIMING coverage_skipped 0"
    echo "Skipping coverage combine/report/xml because CI_SKIP_COVERAGE_XML=true"
else
    measure_stage coverage_combine coverage combine
    measure_stage coverage_report coverage report --show-missing
    measure_stage coverage_xml coverage xml
fi
