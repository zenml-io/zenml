#!/usr/bin/env bash

set -e
set -x

# Usage:
# test-coverage-xml.sh [unit|integration] [environment]
# Example to run all groups for unit tests in parallel:
# test-coverage-xml.sh unit default

TEST_TYPE=${1:-"unit"} # "unit" or "integration"
TEST_ENVIRONMENT=${2:-"default"}

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
export EVIDENTLY_DISABLE_TELEMETRY=1

./zen-test environment provision $TEST_ENVIRONMENT

# Define the test source directory and test options based on the test type
TEST_OPTIONS=""
if [ "$TEST_TYPE" == "unit" ]; then
    TEST_SRC="tests/unit"
    # Rename .test_durations to .unit_test_durations to use it only for unit tests
    if [ -f .test_durations ]; then
        mv .test_durations .unit_test_durations
    fi
    TEST_OPTIONS="--durations 20 --splits 6 --group"
elif [ "$TEST_TYPE" == "integration" ]; then
    TEST_SRC="tests/integration"
else
    echo "Invalid test type: $TEST_TYPE"
    exit 1
fi

# Run the tests for all groups in parallel and save PIDs
PIDS=()
LOG_FILES=()
GROUPS=6
for GROUP in $(seq 1 $GROUPS); do
    COVERAGE_FILE=".coverage.$TEST_TYPE.$GROUP"
    LOG_FILE="test_output_$GROUP.log"
    LOG_FILES+=("$LOG_FILE")
    if [ "$TEST_TYPE" == "unit" ]; then
        coverage run -m pytest $TEST_SRC $TEST_OPTIONS $GROUP > "$LOG_FILE" 2>&1 &
    else
        coverage run -m pytest $TEST_SRC > "$LOG_FILE" 2>&1 &
    fi
    PIDS+=($!)
done

# Wait for all background processes to finish and collect exit statuses
EXIT_STATUS=0
for i in "${!PIDS[@]}"; do
    PID=${PIDS[$i]}
    LOG_FILE=${LOG_FILES[$i]}
    if ! wait $PID; then
        EXIT_STATUS=$?
        echo "Test group $((i + 1)) failed. Output:"
        cat "$LOG_FILE"
    fi
done

./zen-test environment cleanup $TEST_ENVIRONMENT

# Combine coverage data from all groups
coverage combine $(ls .coverage.*)
coverage report --show-missing
coverage xml

# Clean up individual coverage files and log files
rm -f .coverage.*
rm -f "${LOG_FILES[@]}"

# Rename .unit_test_durations back to .test_durations if it was used
if [ -f .unit_test_durations ]; then
    mv .unit_test_durations .test_durations
fi

# Exit with a non-zero status if any tests failed
if [ $EXIT_STATUS -ne 0 ]; then
    echo "Some tests failed."
    exit $EXIT_STATUS
fi