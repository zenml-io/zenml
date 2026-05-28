#!/usr/bin/env bash
set -euo pipefail

REWARD_DIR="/logs/verifier"
mkdir -p "$REWARD_DIR"

if [ ! -f /app/output.txt ]; then
    echo "FAIL: output.txt does not exist"
    echo "0" > "$REWARD_DIR/reward.txt"
    exit 0
fi

EXPECTED=$(rev < /app/input.txt)
GOT=$(cat /app/output.txt)

if [ "$GOT" = "$EXPECTED" ]; then
    echo "PASS: reversed string is correct"
    echo "1" > "$REWARD_DIR/reward.txt"
else
    echo "FAIL: expected '$EXPECTED', got '$GOT'"
    echo "0" > "$REWARD_DIR/reward.txt"
fi
