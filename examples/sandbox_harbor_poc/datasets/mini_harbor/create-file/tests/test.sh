#!/usr/bin/env bash
set -euo pipefail

REWARD_DIR="/logs/verifier"
mkdir -p "$REWARD_DIR"

if [ ! -f /app/output.txt ]; then
    echo "FAIL: output.txt does not exist"
    echo "0" > "$REWARD_DIR/reward.txt"
    exit 0
fi

CONTENT=$(cat /app/output.txt)
if [ "$CONTENT" = "hello world" ]; then
    echo "PASS: output.txt contains 'hello world'"
    echo "1" > "$REWARD_DIR/reward.txt"
else
    echo "FAIL: expected 'hello world', got '$CONTENT'"
    echo "0" > "$REWARD_DIR/reward.txt"
fi
