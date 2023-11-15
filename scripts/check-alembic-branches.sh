#!/bin/bash

# Run the alembic branches command and capture the output
output=$(alembic branches)

# Check if there's any output
if [[ -n "$output" ]]; then
  echo $output
  echo "Warning: Diverging Alembic branches detected."
  exit 1  # Exit with failure status
else
  echo "No diverging Alembic branches detected."
  exit 0  # Exit with success status
fi
