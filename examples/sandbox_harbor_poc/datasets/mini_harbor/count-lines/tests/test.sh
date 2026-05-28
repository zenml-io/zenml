#!/usr/bin/env bash
set -euo pipefail

REWARD_DIR="/logs/verifier"
mkdir -p "$REWARD_DIR"

if [ ! -f /app/result.txt ]; then
    echo "FAIL: result.txt does not exist"
    echo "0" > "$REWARD_DIR/reward.txt"
    exit 0
fi

EXPECTED=$(wc -l < /app/input.txt | tr -d ' ')
GOT=$(cat /app/result.txt | tr -d '[:space:]')

if [ "$GOT" = "$EXPECTED" ]; then
    echo "PASS: line count is $GOT"
    echo "1" > "$REWARD_DIR/reward.txt"
else
    echo "FAIL: expected $EXPECTED, got '$GOT'"
    echo "0" > "$REWARD_DIR/reward.txt"
fi
