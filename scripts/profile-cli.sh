#!/bin/bash

# profile-cli.sh - Script to profile ZenML CLI command performance
#
# Usage:
#   ./profile-cli.sh [OPTIONS] COMMAND
#
# Options:
#   -n, --num-runs NUMBER   Number of runs to average (default: 5)
#   -v, --verbose           Print detailed timing information
#   -h, --help              Show this help message
#
# Example:
#   ./profile-cli.sh "zenml stack list"
#   ./profile-cli.sh -n 10 "zenml pipeline list"

set -e

# Default values
NUM_RUNS=5
VERBOSE=false
COMMAND=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -n|--num-runs)
      NUM_RUNS="$2"
      shift 2
      ;;
    -v|--verbose)
      VERBOSE=true
      shift
      ;;
    -h|--help)
      echo "Usage: ./profile-cli.sh [OPTIONS] COMMAND"
      echo
      echo "Options:"
      echo "  -n, --num-runs NUMBER   Number of runs to average (default: 5)"
      echo "  -v, --verbose           Print detailed timing information"
      echo "  -h, --help              Show this help message"
      echo
      echo "Example:"
      echo "  ./profile-cli.sh \"zenml stack list\""
      echo "  ./profile-cli.sh -n 10 \"zenml pipeline list\""
      exit 0
      ;;
    *)
      COMMAND="$1"
      shift
      ;;
  esac
done

# Check if command is provided
if [ -z "$COMMAND" ]; then
  echo "Error: No command specified"
  echo "Run './profile-cli.sh --help' for usage"
  exit 1
fi

# Ensure bc is available
if ! command -v bc &> /dev/null; then
  echo "Error: 'bc' command is required but not found"
  exit 1
fi

# Run the profiling
echo "Profiling command: $COMMAND"
echo "Number of runs: $NUM_RUNS"

TOTAL_TIME=0
TIMES=()

for i in $(seq 1 $NUM_RUNS); do
  START_TIME=$(date +%s.%N)
  eval $COMMAND > /dev/null
  END_TIME=$(date +%s.%N)
  
  ELAPSED_TIME=$(echo "$END_TIME - $START_TIME" | bc)
  TOTAL_TIME=$(echo "$TOTAL_TIME + $ELAPSED_TIME" | bc)
  TIMES+=($ELAPSED_TIME)
  
  if [ "$VERBOSE" = true ]; then
    echo "Run $i: $ELAPSED_TIME seconds"
  else
    echo -n "."
  fi
done

if [ "$VERBOSE" = false ]; then
  echo
fi

# Calculate average
AVG_TIME=$(echo "scale=3; $TOTAL_TIME / $NUM_RUNS" | bc)

# Calculate standard deviation
if [ $NUM_RUNS -gt 1 ]; then
  SUM_SQUARED_DIFF=0
  for time in "${TIMES[@]}"; do
    DIFF=$(echo "$time - $AVG_TIME" | bc)
    SQUARED_DIFF=$(echo "$DIFF * $DIFF" | bc)
    SUM_SQUARED_DIFF=$(echo "$SUM_SQUARED_DIFF + $SQUARED_DIFF" | bc)
  done
  VARIANCE=$(echo "scale=6; $SUM_SQUARED_DIFF / ($NUM_RUNS - 1)" | bc)
  STD_DEV=$(echo "scale=3; sqrt($VARIANCE)" | bc)
else
  STD_DEV="0.000"
fi

# Print results
echo "-------------------------------------------"
echo "Command: $COMMAND"
echo "Average time: $AVG_TIME seconds"
echo "Standard deviation: $STD_DEV seconds"
echo "Number of runs: $NUM_RUNS"
echo "-------------------------------------------"

# Export variables for GitHub Actions if running in GH Actions
if [ -n "$GITHUB_ENV" ]; then
  echo "AVG_TIME=$AVG_TIME" >> $GITHUB_ENV
  echo "STD_DEV=$STD_DEV" >> $GITHUB_ENV
fi

# Return the average time (for use in scripts)
echo $AVG_TIME 