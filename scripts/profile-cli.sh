#!/bin/bash

# profile-cli.sh - Script to profile ZenML CLI command performance
#
# Usage:
#   ./profile-cli.sh [OPTIONS]
#
# Options:
#   -n, --num-runs NUMBER   Number of runs to average (default: 5)
#   -v, --verbose           Print detailed timing information
#   -o, --output FILE       Output results to a JSON file (default: cli-profile-results.json)
#   -h, --help              Show this help message
#
# Example:
#   ./profile-cli.sh
#   ./profile-cli.sh -n 10 -v
#   ./profile-cli.sh -o my-results.json

set -e

# Default values
NUM_RUNS=5
VERBOSE=false
OUTPUT_FILE="cli-profile-results.json"

# List of commands to profile
# Developers can edit this list directly to add/remove commands
COMMANDS=(
    "zenml stack list"
    "zenml pipeline list"
    "zenml model list"
    "zenml --help"
    "zenml stack --help"
)

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
    -o|--output)
      OUTPUT_FILE="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: ./profile-cli.sh [OPTIONS]"
      echo
      echo "Options:"
      echo "  -n, --num-runs NUMBER   Number of runs to average (default: 5)"
      echo "  -v, --verbose           Print detailed timing information"
      echo "  -o, --output FILE       Output results to a JSON file (default: cli-profile-results.json)"
      echo "  -h, --help              Show this help message"
      echo
      echo "Example:"
      echo "  ./profile-cli.sh"
      echo "  ./profile-cli.sh -n 10 -v"
      echo "  ./profile-cli.sh -o my-results.json"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Run './profile-cli.sh --help' for usage"
      exit 1
      ;;
  esac
done

# Ensure bc is available
if ! command -v bc &> /dev/null; then
  echo "Error: 'bc' command is required but not found"
  exit 1
fi

# Ensure python3 is available
if ! command -v python3 &> /dev/null; then
  echo "Error: python3 is required but not found"
  exit 1
fi

# Function to get high precision time in seconds
get_time_ns() {
  # Use Python for cross-platform high precision timing
  python3 -c 'import time; print(time.time())'
}

# Initialize JSON output
echo "{" > "$OUTPUT_FILE"
echo "  \"profiling_results\": [" >> "$OUTPUT_FILE"

# Display test information
echo "Profiling ${#COMMANDS[@]} commands:"
for cmd in "${COMMANDS[@]}"; do
  echo "  - $cmd"
done
echo "Number of runs per command: $NUM_RUNS"
echo

# Counter for JSON formatting
COMMAND_COUNT=0
TOTAL_COMMANDS=${#COMMANDS[@]}

# Arrays to store results for table display
COMMAND_NAMES=()
AVG_TIMES=()
STD_DEVS=()

# Process each command
for COMMAND in "${COMMANDS[@]}"; do
  echo "Profiling command: $COMMAND"
  
  TOTAL_TIME="0.0"
  TIMES=()

  for i in $(seq 1 $NUM_RUNS); do
    START_TIME=$(get_time_ns)
    eval $COMMAND > /dev/null
    END_TIME=$(get_time_ns)
    
    # Ensure we maintain high precision
    ELAPSED_TIME=$(LC_NUMERIC=C printf "%.6f" $(echo "$END_TIME - $START_TIME" | bc -l))
    TOTAL_TIME=$(LC_NUMERIC=C printf "%.6f" $(echo "$TOTAL_TIME + $ELAPSED_TIME" | bc -l))
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

  # Calculate average with higher precision
  AVG_TIME=$(LC_NUMERIC=C printf "%.6f" $(echo "$TOTAL_TIME / $NUM_RUNS" | bc -l))

  # Calculate standard deviation with higher precision
  if [ $NUM_RUNS -gt 1 ]; then
    SUM_SQUARED_DIFF="0.0"
    for time in "${TIMES[@]}"; do
      DIFF=$(LC_NUMERIC=C printf "%.6f" $(echo "$time - $AVG_TIME" | bc -l))
      SQUARED_DIFF=$(LC_NUMERIC=C printf "%.6f" $(echo "$DIFF * $DIFF" | bc -l))
      SUM_SQUARED_DIFF=$(LC_NUMERIC=C printf "%.6f" $(echo "$SUM_SQUARED_DIFF + $SQUARED_DIFF" | bc -l))
    done
    VARIANCE=$(LC_NUMERIC=C printf "%.6f" $(echo "$SUM_SQUARED_DIFF / ($NUM_RUNS - 1)" | bc -l))
    STD_DEV=$(LC_NUMERIC=C printf "%.6f" $(echo "sqrt($VARIANCE)" | bc -l))
  else
    STD_DEV="0.000000"
  fi
  
  # Store results for table display
  COMMAND_NAMES+=("$COMMAND")
  AVG_TIMES+=("$AVG_TIME")
  STD_DEVS+=("$STD_DEV")

  # Print individual result
  echo "-------------------------------------------"
  echo "Command: $COMMAND"
  echo "Average time: $AVG_TIME seconds"
  echo "Standard deviation: $STD_DEV seconds"
  echo "Number of runs: $NUM_RUNS"
  echo "-------------------------------------------"
  echo

  # Write to JSON file
  echo "    {" >> "$OUTPUT_FILE"
  echo "      \"command\": \"$COMMAND\"," >> "$OUTPUT_FILE"
  echo "      \"avg_time\": $AVG_TIME," >> "$OUTPUT_FILE"
  echo "      \"std_dev\": $STD_DEV," >> "$OUTPUT_FILE"
  echo "      \"num_runs\": $NUM_RUNS," >> "$OUTPUT_FILE"
  echo "      \"runs\": [" >> "$OUTPUT_FILE"
  
  # Add individual run times
  for j in "${!TIMES[@]}"; do
    COMMA=""
    if [ $j -lt $(( ${#TIMES[@]} - 1 )) ]; then
      COMMA=","
    fi
    echo "        ${TIMES[$j]}$COMMA" >> "$OUTPUT_FILE"
  done
  
  echo "      ]" >> "$OUTPUT_FILE"
  
  # Add comma if not the last command
  COMMAND_COUNT=$((COMMAND_COUNT + 1))
  if [ $COMMAND_COUNT -lt $TOTAL_COMMANDS ]; then
    echo "    }," >> "$OUTPUT_FILE"
  else
    echo "    }" >> "$OUTPUT_FILE"
  fi
done

# Close JSON file
echo "  ]," >> "$OUTPUT_FILE"
echo "  \"metadata\": {" >> "$OUTPUT_FILE"
echo "    \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"," >> "$OUTPUT_FILE"
echo "    \"environment\": \"$(uname -s) $(uname -r)\"" >> "$OUTPUT_FILE"
echo "  }" >> "$OUTPUT_FILE"
echo "}" >> "$OUTPUT_FILE"

echo "Results saved to $OUTPUT_FILE"

# Display results table
echo
echo "===================== SUMMARY ====================="
echo "Command                  | Average Time (s) | Std Dev"
echo "--------------------------|-----------------|--------"
for i in "${!COMMAND_NAMES[@]}"; do
  printf "%-25s | %15s | %7s\n" "${COMMAND_NAMES[$i]}" "${AVG_TIMES[$i]}" "${STD_DEVS[$i]}"
done
echo "===================================================" 