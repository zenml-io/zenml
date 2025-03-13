#!/bin/bash

# profile-cli.sh - Script to profile ZenML CLI command performance
#
# Usage:
#   ./profile-cli.sh [OPTIONS]
#
# Options:
#   -n, --num-runs NUMBER   Number of runs to average (default: 5)
#   -v, --verbose           Print detailed timing information
#   -o, --output FILE       Output results to a JSON file (no output file by default)
#   -t, --timeout SECONDS   Maximum execution time per command in seconds (default: 60)
#   -s, --slow-threshold    Threshold in seconds to mark command as slow (default: 5)
#   -h, --help              Show this help message
#
# Example:
#   ./profile-cli.sh
#   ./profile-cli.sh -n 10 -v
#   ./profile-cli.sh -o my-results.json
#   ./profile-cli.sh -t 30 -s 5

set -e

# Default values
NUM_RUNS=5
VERBOSE=false
OUTPUT_FILE=""  # No output file by default
TIMEOUT_SECONDS=60
SLOW_THRESHOLD=5  # Default threshold for slow commands in seconds

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
    -t|--timeout)
      TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    -s|--slow-threshold)
      SLOW_THRESHOLD="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: ./profile-cli.sh [OPTIONS]"
      echo
      echo "Options:"
      echo "  -n, --num-runs NUMBER   Number of runs to average (default: 5)"
      echo "  -v, --verbose           Print detailed timing information"
      echo "  -o, --output FILE       Output results to a JSON file (no output file by default)"
      echo "  -t, --timeout SECONDS   Maximum execution time per command in seconds (default: 60)"
      echo "  -s, --slow-threshold    Threshold in seconds to mark command as slow (default: 5)"
      echo "  -h, --help              Show this help message"
      echo
      echo "Example:"
      echo "  ./profile-cli.sh"
      echo "  ./profile-cli.sh -n 10 -v"
      echo "  ./profile-cli.sh -o my-results.json"
      echo "  ./profile-cli.sh -t 30 -s 5"
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

# Check if timeout command is available
TIMEOUT_CMD=""
if command -v timeout &> /dev/null; then
  TIMEOUT_CMD="timeout"
elif command -v gtimeout &> /dev/null; then
  # On macOS with coreutils installed
  TIMEOUT_CMD="gtimeout"
else
  echo "Warning: Neither 'timeout' nor 'gtimeout' command found. Timeout functionality will be disabled."
  echo "On macOS, install coreutils with: brew install coreutils"
fi

# Function to get high precision time in seconds
get_time_ns() {
  # Use Python for cross-platform high precision timing
  python3 -c 'import time; print(time.time())'
}

# Initialize JSON output if an output file was specified
if [ -n "$OUTPUT_FILE" ]; then
  echo "{" > "$OUTPUT_FILE"
  echo "  \"profiling_results\": [" >> "$OUTPUT_FILE"
fi

# Display test information
echo "Profiling ${#COMMANDS[@]} commands:"
for cmd in "${COMMANDS[@]}"; do
  echo "  - $cmd"
done
echo "Number of runs per command: $NUM_RUNS"
echo "Timeout per run: $TIMEOUT_SECONDS seconds"
echo "Slow threshold: $SLOW_THRESHOLD seconds"
if [ -n "$OUTPUT_FILE" ]; then
  echo "Results will be saved to: $OUTPUT_FILE"
else
  echo "No output file specified. Results will only be displayed on screen."
fi
echo

# Counter for JSON formatting
COMMAND_COUNT=0
TOTAL_COMMANDS=${#COMMANDS[@]}

# Arrays to store results for table display
COMMAND_NAMES=()
AVG_TIMES=()
STD_DEVS=()
CMD_STATUS=()

# Process each command
for COMMAND in "${COMMANDS[@]}"; do
  echo "Profiling command: $COMMAND"
  
  TOTAL_TIME="0.0"
  TIMES=()
  COMMAND_FAILED=false
  COMMAND_TIMEDOUT=false
  COMMAND_SLOW=false
  ERROR_MESSAGE=""

  for i in $(seq 1 $NUM_RUNS); do
    if [ "$COMMAND_FAILED" = true ] || [ "$COMMAND_TIMEDOUT" = true ]; then
      # Skip remaining runs if command already failed or timed out
      continue
    fi

    START_TIME=$(get_time_ns)
    
    # Execute command with timeout if available
    if [ -n "$TIMEOUT_CMD" ]; then
      # Use set +e to prevent script from exiting if the command times out or fails
      set +e
      $TIMEOUT_CMD $TIMEOUT_SECONDS bash -c "$COMMAND" > /dev/null 2>&1
      EXIT_CODE=$?
      # Restore error handling
      set -e
      
      # Check for timeout (124 is the timeout command's exit code for timeout)
      if [ $EXIT_CODE -eq 124 ]; then
        COMMAND_TIMEDOUT=true
        ERROR_MESSAGE="Command timed out after $TIMEOUT_SECONDS seconds on run $i"
        echo "⏱️ $ERROR_MESSAGE"
        break
      elif [ $EXIT_CODE -ne 0 ]; then
        COMMAND_FAILED=true
        ERROR_MESSAGE="Command failed on run $i (exit code: $EXIT_CODE)"
        echo "❌ $ERROR_MESSAGE"
        break
      fi
    else
      # No timeout command available, just run normally
      # Use set +e to prevent script from exiting if the command fails
      set +e
      eval $COMMAND > /dev/null 2>&1
      EXIT_CODE=$?
      # Restore error handling
      set -e
      
      if [ $EXIT_CODE -ne 0 ]; then
        COMMAND_FAILED=true
        ERROR_MESSAGE="Command failed on run $i (exit code: $EXIT_CODE)"
        echo "❌ $ERROR_MESSAGE"
        break
      fi
    fi
    
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

  if [ "$VERBOSE" = false ] && [ "$COMMAND_FAILED" = false ] && [ "$COMMAND_TIMEDOUT" = false ]; then
    echo
  fi

  # Store command status
  if [ "$COMMAND_TIMEDOUT" = true ]; then
    CMD_STATUS+=("TIMEOUT")
    AVG_TIME="0.000000"
    STD_DEV="0.000000"
    
    # Print timeout result
    echo "-------------------------------------------"
    echo "Command: $COMMAND"
    echo "Status: TIMEOUT"
    echo "Error: $ERROR_MESSAGE"
    echo "-------------------------------------------"
    echo
    
    # Write timeout to JSON file if output file was specified
    if [ -n "$OUTPUT_FILE" ]; then
      echo "    {" >> "$OUTPUT_FILE"
      echo "      \"command\": \"$COMMAND\"," >> "$OUTPUT_FILE"
      echo "      \"status\": \"timeout\"," >> "$OUTPUT_FILE"
      echo "      \"timeout\": $TIMEOUT_SECONDS," >> "$OUTPUT_FILE"
      echo "      \"error\": \"$ERROR_MESSAGE\"" >> "$OUTPUT_FILE"
    fi
  elif [ "$COMMAND_FAILED" = true ]; then
    CMD_STATUS+=("FAILED")
    AVG_TIME="0.000000"
    STD_DEV="0.000000"
    
    # Print failure result
    echo "-------------------------------------------"
    echo "Command: $COMMAND"
    echo "Status: FAILED"
    echo "Error: $ERROR_MESSAGE"
    echo "-------------------------------------------"
    echo
    
    # Write failure to JSON file if output file was specified
    if [ -n "$OUTPUT_FILE" ]; then
      echo "    {" >> "$OUTPUT_FILE"
      echo "      \"command\": \"$COMMAND\"," >> "$OUTPUT_FILE"
      echo "      \"status\": \"failed\"," >> "$OUTPUT_FILE"
      echo "      \"error\": \"$ERROR_MESSAGE\"" >> "$OUTPUT_FILE"
    fi
  else
    # Calculate average with higher precision
    AVG_TIME=$(LC_NUMERIC=C printf "%.6f" $(echo "$TOTAL_TIME / $NUM_RUNS" | bc -l))
    
    # Check if command is slow (average time exceeds the threshold)
    if (( $(echo "$AVG_TIME > $SLOW_THRESHOLD" | bc -l) )); then
      COMMAND_SLOW=true
      CMD_STATUS+=("SLOW")
    else
      CMD_STATUS+=("SUCCESS")
    fi
  
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
    
    # Print success result
    echo "-------------------------------------------"
    echo "Command: $COMMAND"
    if [ "$COMMAND_SLOW" = true ]; then
      echo "Status: SLOW (exceeds $SLOW_THRESHOLD seconds threshold)"
    else
      echo "Status: SUCCESS"
    fi
    echo "Average time: $AVG_TIME seconds"
    echo "Standard deviation: $STD_DEV seconds"
    echo "Number of runs: $NUM_RUNS"
    echo "-------------------------------------------"
    echo
    
    # Write results to JSON file if output file was specified
    if [ -n "$OUTPUT_FILE" ]; then
      echo "    {" >> "$OUTPUT_FILE"
      echo "      \"command\": \"$COMMAND\"," >> "$OUTPUT_FILE"
      if [ "$COMMAND_SLOW" = true ]; then
        echo "      \"status\": \"slow\"," >> "$OUTPUT_FILE"
        echo "      \"slow_threshold\": $SLOW_THRESHOLD," >> "$OUTPUT_FILE"
      else
        echo "      \"status\": \"success\"," >> "$OUTPUT_FILE"
      fi
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
    fi
  fi
  
  # Store results for table display
  COMMAND_NAMES+=("$COMMAND")
  AVG_TIMES+=("$AVG_TIME")
  STD_DEVS+=("$STD_DEV")
  
  # Add comma if not the last command and output file was specified
  if [ -n "$OUTPUT_FILE" ]; then
    COMMAND_COUNT=$((COMMAND_COUNT + 1))
    if [ $COMMAND_COUNT -lt $TOTAL_COMMANDS ]; then
      echo "    }," >> "$OUTPUT_FILE"
    else
      echo "    }" >> "$OUTPUT_FILE"
    fi
  fi
done

# Close JSON file if output file was specified
if [ -n "$OUTPUT_FILE" ]; then
  echo "  ]," >> "$OUTPUT_FILE"
  echo "  \"metadata\": {" >> "$OUTPUT_FILE"
  echo "    \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"," >> "$OUTPUT_FILE"
  echo "    \"environment\": \"$(uname -s) $(uname -r)\"," >> "$OUTPUT_FILE"
  echo "    \"timeout\": $TIMEOUT_SECONDS," >> "$OUTPUT_FILE"
  echo "    \"slow_threshold\": $SLOW_THRESHOLD" >> "$OUTPUT_FILE"
  echo "  }" >> "$OUTPUT_FILE"
  echo "}" >> "$OUTPUT_FILE"

  echo "Results saved to $OUTPUT_FILE"
fi

# Display results table
echo
echo "===================== SUMMARY ====================="
echo "Command                  | Status  | Average Time (s) | Std Dev"
echo "--------------------------|---------|-----------------|--------"
for i in "${!COMMAND_NAMES[@]}"; do
  STATUS_MARKER="✅"
  if [ "${CMD_STATUS[$i]}" = "FAILED" ]; then
    STATUS_MARKER="❌"
  elif [ "${CMD_STATUS[$i]}" = "TIMEOUT" ]; then
    STATUS_MARKER="⏱️"
  elif [ "${CMD_STATUS[$i]}" = "SLOW" ]; then
    STATUS_MARKER="⚠️"
  fi
  printf "%-25s | %s %6s | %15s | %7s\n" "${COMMAND_NAMES[$i]}" "$STATUS_MARKER" "${CMD_STATUS[$i]}" "${AVG_TIMES[$i]}" "${STD_DEVS[$i]}"
done
echo "===================================================" 