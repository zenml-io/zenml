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
# a half of them busy. Set TEST_LANES to run that many pytest processes ("lanes")
# side by side, splitting the selected tests between them.
TEST_SRC="tests/"${1:-""}
TEST_ENVIRONMENT=${2:-"default"}
TEST_SPLITS=${3:-"1"}
TEST_GROUP=${4:-"1"}
STORE_DURATIONS=${5:-""}
TEST_LANES=${TEST_LANES:-1}

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

# Every shard and lane is a separate pytest process that collects the same tests
# and keeps its own group. pytest-randomly shuffles each process with a seed of its
# own first, and pytest-split breaks ties between equally long tests by that order,
# so unseeded processes disagree about which group a test belongs to: some tests
# then run twice and others never run. One seed per workflow run fixes that.
SEED_ARGS=()
if [ "$TEST_SPLITS" -gt 1 ] || [ "$TEST_LANES" -gt 1 ]; then
    SEED_ARGS=(--randomly-seed="$(( ${GITHUB_RUN_ID:-1} % 4294967296 ))")
fi

# Some macOS ML libraries bundle incompatible OpenMP runtimes. Apply the
# requested runtime override to pytest only: tests/conftest.py removes it from
# the process environment before tests can launch child processes, and it makes
# the arm64e system tools used elsewhere in this script (mktemp, sed) abort.
run_pytest() {
    if [[ -n "${PYTEST_DYLD_INSERT_LIBRARIES:-}" ]]; then
        DYLD_INSERT_LIBRARIES="$PYTEST_DYLD_INSERT_LIBRARIES" coverage run -m pytest "${SEED_ARGS[@]}" "$@"
    else
        coverage run -m pytest "${SEED_ARGS[@]}" "$@"
    fi
}

# Against a shared test server these tests create pipelines in the default
# project and prune docker resources for the whole daemon, so they never run
# next to other lanes. Tests in their own project (the functional ones) can.
SHARED_STATE_PATHS=(tests/integration/examples tests/integration/integrations)

LANE_COUNT=0

# Starts one pytest process in the background: <paths> <splits> <group>
# [pytest args...]. Its output is prefixed with the lane number and its exit code
# is written to $LANE_STATUS_DIR for run_test_lanes to collect.
start_test_lane() {
    local paths=$1 splits=$2 group=$3
    shift 3
    LANE_COUNT=$((LANE_COUNT + 1))
    local lane=$LANE_COUNT
    (
        set +e
        export COVERAGE_FILE=".coverage.lane${lane}"
        # A private deployment root keeps the lanes' client configuration and,
        # without a server, their databases apart. A docker server keeps its
        # state in the running containers, which are already provisioned.
        export ZENML_TEST_DEPLOYMENT_ROOT_PATH="${LANE_ROOT}-lane${lane}"
        if [ "$LANE_SERVER" == "none" ]; then
            ./zen-test environment provision $TEST_ENVIRONMENT || {
                provision_status=$?
                echo "Provisioning failed for test lane ${lane}, not running its tests"
                echo $provision_status > "$LANE_STATUS_DIR/$lane"
                exit
            }
        fi
        # --cleanup-docker is left out on purpose: it prunes containers and
        # images across the whole docker daemon, which would hit other lanes.
        run_pytest $paths --color=yes -vv --durations-path=.test_durations --splits=$splits --group=$group --splitting-algorithm least_duration --environment $TEST_ENVIRONMENT --no-provision "$@" "${PYTEST_RERUN_ARGS[@]}" --instafail
        echo $? > "$LANE_STATUS_DIR/$lane"
    ) 2>&1 | sed -u "s/^/[lane ${lane}] /" &
}

# Lanes are only safe for deployments without a server and for docker servers,
# whose state lives in the running containers. Anything else runs one process.
prepare_test_lanes() {
    local info
    info=$(python - "$TEST_ENVIRONMENT" <<'PY'
import sys

from tests.harness.deployment import BaseTestDeployment
from tests.harness.harness import TestHarness

environment = TestHarness().get_environment_config(sys.argv[1])
print(BaseTestDeployment.get_root_path())
print(environment.deployment.server.value)
PY
)
    LANE_ROOT=$(echo "$info" | head -n 1)
    LANE_SERVER=$(echo "$info" | tail -n 1)
    if [ "$LANE_SERVER" != "none" ] && [ "$LANE_SERVER" != "docker" ]; then
        echo "Test lanes are not supported for a '$LANE_SERVER' server, running one lane"
        TEST_LANES=1
    fi
}

run_test_lanes() {
    LANE_STATUS_DIR=$(mktemp -d)
    local lanes=$TEST_LANES serial_paths=() ignores=() path
    if [ "$LANE_SERVER" != "none" ]; then
        for path in "${SHARED_STATE_PATHS[@]}"; do
            case "$TEST_SRC/" in "$path"/*) lanes=1 ;; esac
            case "$path/" in "$TEST_SRC"/?*)
                serial_paths+=("$path")
                ignores+=("--ignore=$path")
                ;;
            esac
        done
    fi
    if [ ${#serial_paths[@]} -gt 0 ]; then
        start_test_lane "${serial_paths[*]}" "$TEST_SPLITS" "$TEST_GROUP"
        lanes=$((lanes > 1 ? lanes - 1 : 1))
    fi
    local lane
    for ((lane = 1; lane <= lanes; lane++)); do
        # This shard's group is split again between its lanes, so lane i of
        # group g takes group (g - 1) * lanes + i of splits * lanes.
        start_test_lane "$TEST_SRC" "$((TEST_SPLITS * lanes))" "$(((TEST_GROUP - 1) * lanes + lane))" "${ignores[@]}"
    done
    wait

    local failed=0 status
    for ((lane = 1; lane <= LANE_COUNT; lane++)); do
        if [ ! -f "$LANE_STATUS_DIR/$lane" ]; then
            echo "Test lane $lane did not report an exit code"
            failed=1
        elif status=$(cat "$LANE_STATUS_DIR/$lane") && [ "$status" != "0" ]; then
            echo "Test lane $lane failed with exit code $status"
            failed=1
        fi
    done
    return $failed
}

if [ "$TEST_LANES" -gt 1 ] && [ -n "$1" ] && [ "$STORE_DURATIONS" != "store-durations" ]; then
    prepare_test_lanes
fi

# The '-vv' flag enables pytest-clarity output when tests fail.
# Shows errors instantly in logs when test fails.
if [ -n "$1" ]; then
    if [ "$STORE_DURATIONS" == "store-durations" ]; then
        run_pytest $TEST_SRC --color=yes -vv --environment $TEST_ENVIRONMENT --no-provision --cleanup-docker --store-durations --durations-path=.test_durations "${PYTEST_RERUN_ARGS[@]}" --instafail
    elif [ "$TEST_LANES" -gt 1 ]; then
        run_test_lanes
    else
        run_pytest $TEST_SRC --color=yes -vv --durations-path=.test_durations --splits=$TEST_SPLITS --group=$TEST_GROUP --splitting-algorithm least_duration --environment $TEST_ENVIRONMENT --no-provision --cleanup-docker "${PYTEST_RERUN_ARGS[@]}" --instafail
    fi
else
    if [ "$STORE_DURATIONS" == "store-durations" ]; then
        run_pytest tests/unit --color=yes -vv --environment $TEST_ENVIRONMENT --no-provision --store-durations --durations-path=.test_durations "${PYTEST_RERUN_ARGS[@]}" --instafail
        run_pytest tests/integration --color=yes -vv --environment $TEST_ENVIRONMENT --no-provision --cleanup-docker --store-durations --durations-path=.test_durations "${PYTEST_RERUN_ARGS[@]}" --instafail
    else
        run_pytest tests/unit --color=yes -vv --durations-path=.test_durations --splits=$TEST_SPLITS --group=$TEST_GROUP --splitting-algorithm least_duration --environment $TEST_ENVIRONMENT --no-provision "${PYTEST_RERUN_ARGS[@]}" --instafail
        run_pytest tests/integration --color=yes -vv --durations-path=.test_durations --splits=$TEST_SPLITS --group=$TEST_GROUP --splitting-algorithm least_duration --environment $TEST_ENVIRONMENT --no-provision --cleanup-docker "${PYTEST_RERUN_ARGS[@]}" --instafail
    fi
fi

./zen-test environment cleanup $TEST_ENVIRONMENT

coverage combine
coverage report --show-missing
coverage xml
