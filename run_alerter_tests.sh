#!/bin/bash

# Script to run all alerter tests with their respective stacks
# Based on the requirements specified in each test file:
# - test_discord_alerter.py: requires `zenml stack set discord`
# - test_slack_alerter.py: requires `zenml stack set local-s3`
# - test_smtp_email_alerter.py: requires `zenml stack set email_alerter`

set -e  # Exit on error

echo "=== ZenML Alerter Test Runner ==="
echo

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run a test with a specific stack
run_test() {
    local stack_name=$1
    local test_file=$2
    local test_name=$3
    
    echo -e "${YELLOW}Running $test_name test...${NC}"
    echo "Setting stack to: $stack_name"
    
    # Set the stack as specified in the test file
    if zenml stack set "$stack_name"; then
        echo -e "${GREEN}✓ Stack '$stack_name' activated${NC}"
    else
        echo -e "${RED}✗ Failed to set stack '$stack_name'${NC}"
        echo "  Please ensure the stack exists: zenml stack list"
        return 1
    fi
    
    # Run the test
    echo "Running test file: $test_file"
    echo "----------------------------------------"
    
    if python "$test_file"; then
        echo -e "${GREEN}✓ $test_name test completed successfully${NC}"
    else
        echo -e "${RED}✗ $test_name test failed${NC}"
        return 1
    fi
    
    echo
    echo "========================================="
    echo
}

# Run all tests
TEST_DIR="test_zone/alerters"

# Test 1: Discord Alerter (requires: zenml stack set discord)
if [ -f "$TEST_DIR/test_discord_alerter.py" ]; then
    run_test "discord" "$TEST_DIR/test_discord_alerter.py" "Discord Alerter"
else
    echo -e "${RED}Discord test file not found: $TEST_DIR/test_discord_alerter.py${NC}"
fi

# Test 2: Slack Alerter (requires: zenml stack set local-s3)
if [ -f "$TEST_DIR/test_slack_alerter.py" ]; then
    run_test "local-s3" "$TEST_DIR/test_slack_alerter.py" "Slack Alerter"
else
    echo -e "${RED}Slack test file not found: $TEST_DIR/test_slack_alerter.py${NC}"
fi

# Test 3: SMTP Email Alerter (requires: zenml stack set email_alerter)
if [ -f "$TEST_DIR/test_smtp_email_alerter.py" ]; then
    run_test "email_alerter" "$TEST_DIR/test_smtp_email_alerter.py" "SMTP Email Alerter"
else
    echo -e "${RED}Email test file not found: $TEST_DIR/test_smtp_email_alerter.py${NC}"
fi

echo
echo "=== All tests completed ===="