#!/usr/bin/env bash
set -euo pipefail

REWARD_DIR="/logs/verifier"
mkdir -p "$REWARD_DIR"

if [ ! -f /app/merged.txt ]; then
    echo "FAIL: merged.txt does not exist"
    echo "0" > "$REWARD_DIR/reward.txt"
    exit 0
fi

EXPECTED=$(cat /app/part1.txt /app/part2.txt)
GOT=$(cat /app/merged.txt)

if [ "$GOT" = "$EXPECTED" ]; then
    echo "PASS: merged.txt is correct"
    echo "1" > "$REWARD_DIR/reward.txt"
else
    echo "FAIL: expected '$EXPECTED', got '$GOT'"
    echo "0" > "$REWARD_DIR/reward.txt"
fi
