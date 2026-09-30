#!/usr/bin/env bash

set -e
set -x

# If only unittests are needed call
# test-coverage-xml.sh unit
# For only integration tests call
# test-coverage-xml.sh integration
# To store durations, add a fifth argument 'store-durations'
#
# A CI runner has several CPU cores but one test process keeps only about one and
# a half of them busy. To use the rest, set:
# - TEST_LANES: number of pytest processes ("lanes") that split the selected tests.
# - TEST_SERIAL_PATHS: space separated paths that share state with each other
#   through the test server, such as the example tests that create pipelines
#   in the default project and prune docker resources. They run in one extra
#   lane of their own and are left out of the others.
TEST_SRC="tests/"${1:-""}
TEST_ENVIRONMENT=${2:-"default"}
TEST_SPLITS=${3:-"1"}
TEST_GROUP=${4:-"1"}
STORE_DURATIONS=${5:-""}
TEST_LANES=${TEST_LANES:-1}
TEST_SERIAL_PATHS=${TEST_SERIAL_PATHS:-}

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
export ZENML_LOGGING_VERBOSITY=debug
export ZENML_ANALYTICS_OPT_IN=false
export EVIDENTLY_DISABLE_TELEMETRY=1

./zen-test environment provision $TEST_ENVIRONMENT

# Some macOS ML libraries bundle incompatible OpenMP runtimes. Apply the
# requested runtime override when starting pytest; tests/conftest.py removes it
# from the process environment before tests can launch child processes.
if [[ -n "${PYTEST_DYLD_INSERT_LIBRARIES:-}" ]]; then
    export DYLD_INSERT_LIBRARIES="$PYTEST_DYLD_INSERT_LIBRARIES"
fi

LANE_STATUS_DIR=""
lane_count=0

# Starts one pytest process in the background: <paths> <splits> <group>
# [ignore-serial-paths]. Its output is prefixed with the lane number and its exit
# code is written to $LANE_STATUS_DIR so that run_test_lanes can collect it.
start_test_lane() {
    local paths=$1 splits=$2 group=$3 ignore_serial=${4:-no}
    local ignore=() serial_path
    if [ "$ignore_serial" == "yes" ]; then
        for serial_path in $TEST_SERIAL_PATHS; do
            ignore+=("--ignore=$serial_path")
        done
    fi
    lane_count=$((lane_count + 1))
    local lane=$lane_count
    (
        set +e
        export COVERAGE_FILE=".coverage.lane${lane}"
        # A private deployment root keeps the lanes' client configuration and,
        # for local deployments, their databases apart. Server deployments
        # keep their state in the running server, which is already provisioned.
        export ZENML_TEST_DEPLOYMENT_ROOT_PATH="${LANE_ROOT}-lane${lane}"
        if [ "$SHARED_SERVER" == "no" ]; then
            ./zen-test environment provision $TEST_ENVIRONMENT
        fi
        if [ -n "$LANE_DYLD_INSERT_LIBRARIES" ]; then
            export DYLD_INSERT_LIBRARIES="$LANE_DYLD_INSERT_LIBRARIES"
        fi
        # --cleanup-docker is left out on purpose: it prunes containers and
        # images across the whole docker daemon, which would hit other lanes.
        coverage run -m pytest $paths --color=yes -vv --durations-path=.test_durations --splits=$splits --group=$group --splitting-algorithm least_duration --environment $TEST_ENVIRONMENT --no-provision "${ignore[@]}" "${PYTEST_RERUN_ARGS[@]}" --instafail
        echo $? > "$LANE_STATUS_DIR/$lane"
    ) 2>&1 | sed -u "s/^/[lane ${lane}] /" &
}

run_test_lanes() {
    # On macOS an inserted arm64 dylib aborts the arm64e system tools used below
    # (mktemp, sed), so only the pytest processes get it.
    LANE_DYLD_INSERT_LIBRARIES=${DYLD_INSERT_LIBRARIES:-}
    unset DYLD_INSERT_LIBRARIES
    LANE_STATUS_DIR=$(mktemp -d)
    LANE_ROOT=$(python -c "from tests.harness.deployment.base import BaseTestDeployment; print(BaseTestDeployment.get_root_path())")
    # Server environments are named after their server deployment.
    SHARED_SERVER=no
    if [[ "$TEST_ENVIRONMENT" == *server* ]]; then
        SHARED_SERVER=yes
    fi

    if [ -n "$TEST_SERIAL_PATHS" ]; then
        start_test_lane "$TEST_SERIAL_PATHS" "$TEST_SPLITS" "$TEST_GROUP"
    fi
    local lane
    for ((lane = 1; lane <= TEST_LANES; lane++)); do
        start_test_lane "$TEST_SRC" "$((TEST_SPLITS * TEST_LANES))" "$(((TEST_GROUP - 1) * TEST_LANES + lane))" "$([ -n "$TEST_SERIAL_PATHS" ] && echo yes || echo no)"
    done
    wait

    local failed=0 status_file
    for status_file in "$LANE_STATUS_DIR"/*; do
        if [ "$(cat "$status_file")" != "0" ]; then
            echo "Test lane $(basename "$status_file") failed with exit code $(cat "$status_file")"
            failed=1
        fi
    done
    [ "$(ls "$LANE_STATUS_DIR" | wc -l)" -eq "$lane_count" ] || failed=1
    return $failed
}

# The '-vv' flag enables pytest-clarity output when tests fail.
# Shows errors instantly in logs when test fails.
if [ -n "$1" ]; then
    if [ "$STORE_DURATIONS" == "store-durations" ]; then
        coverage run -m pytest $TEST_SRC --color=yes -vv --environment $TEST_ENVIRONMENT --no-provision --cleanup-docker --store-durations --durations-path=.test_durations "${PYTEST_RERUN_ARGS[@]}" --instafail
    elif [ "$TEST_LANES" -gt 1 ] || [ -n "$TEST_SERIAL_PATHS" ]; then
        run_test_lanes
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

if [[ -n "${PYTEST_DYLD_INSERT_LIBRARIES:-}" ]]; then
    unset DYLD_INSERT_LIBRARIES
fi

./zen-test environment cleanup $TEST_ENVIRONMENT

coverage combine
coverage report --show-missing
coverage xml
