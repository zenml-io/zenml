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

# Define the test source directory based on the test type
if [ "$TEST_TYPE" == "unit" ]; then
    TEST_SRC="tests/unit"
    mv unit_test_durations .test_durations
elif [ "$TEST_TYPE" == "integration" ]; then
    TEST_SRC="tests/integration"
    mv integeration_test_durations .test_durations
else
    echo "Invalid test type: $TEST_TYPE"
    exit 1
fi

# Run the tests for all groups in parallel and store their PIDs
pids=()
group_statuses=()
for GROUP in {1..4}; do
    COVERAGE_FILE=".coverage.$TEST_TYPE.$GROUP"
    coverage run -m pytest $TEST_SRC --durations 20 --splits 4 --group $GROUP &
    pids+=($!)
    group_statuses+=("pending")
done

# Wait for all background processes to finish and check their exit status
failed_groups=()
for i in "${!pids[@]}"; do
    pid=${pids[$i]}
    wait $pid
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        group_statuses[$i]="failed"
        failed_groups+=($((i + 1))) # Store the group number (1-indexed)
    else
        group_statuses[$i]="passed"
    fi
done

# Report the test results
echo "Test summary:"
for i in "${!group_statuses[@]}"; do
    echo "Group $((i + 1)): ${group_statuses[$i]}"
done

# If there are any failed groups, do the cleanup and exit with code 1
if [ ${#failed_groups[@]} -ne 0 ]; then
    echo "The following test groups failed: ${failed_groups[*]}"
    ./zen-test environment cleanup $TEST_ENVIRONMENT
    exit 1
fi

./zen-test environment cleanup $TEST_ENVIRONMENT

# Combine coverage data from all groups
coverage combine $(ls .coverage.*)
coverage report --show-missing
coverage xml

# Clean up individual coverage files
rm -f .coverage.*