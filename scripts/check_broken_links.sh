#!/usr/bin/env bash

# Exit on error
set -e

# Get the directory containing this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Default to docs directory if no argument provided
CHECK_DIR="${1:-docs/book}"

# Convert to absolute path if relative path provided
if [[ ! "$CHECK_DIR" = /* ]]; then
    CHECK_DIR="$SCRIPT_DIR/../$CHECK_DIR"
fi

# Ensure the directory exists
if [ ! -d "$CHECK_DIR" ]; then
    echo "Error: Directory '$CHECK_DIR' does not exist"
    exit 1
fi

# Run the Python script
python "$SCRIPT_DIR/check_broken_links.py" "$CHECK_DIR" 