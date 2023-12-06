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
elif [ "$TEST_TYPE" == "integration" ]; then
    TEST_SRC="tests/integration"
else
    echo "Invalid test type: $TEST_TYPE"
    exit 1
fi

# Run the tests for all groups in parallel
for GROUP in {1..3}; do
    COVERAGE_FILE=".coverage.$TEST_TYPE.$GROUP"
    coverage run -m pytest $TEST_SRC --durations 20 --splits 3 --group $GROUP &
done

# Wait for all background processes to finish
wait

./zen-test environment cleanup $TEST_ENVIRONMENT

# Combine coverage data from all groups
coverage combine $(ls .coverage.*)
coverage report --show-missing
coverage xml

# Clean up individual coverage files
rm -f .coverage.*