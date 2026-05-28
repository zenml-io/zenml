#!/usr/bin/env bash
set -euo pipefail

REWARD_DIR="/logs/verifier"
mkdir -p "$REWARD_DIR"

OUTPUT=$(python /app/app.py 2>&1) || true

if [ "$OUTPUT" = "success" ]; then
    echo "PASS: app.py runs and prints 'success'"
    echo "1" > "$REWARD_DIR/reward.txt"
else
    echo "FAIL: expected 'success', got '$OUTPUT'"
    echo "0" > "$REWARD_DIR/reward.txt"
fi
