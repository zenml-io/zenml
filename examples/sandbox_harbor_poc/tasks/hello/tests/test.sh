#!/bin/bash
# Check that the agent wrote '42' into /app/answer.txt.
# Reward 1.0 on a clean match, 0.0 otherwise. Writes to /logs/verifier/reward.txt.

set -u
mkdir -p /logs/verifier

answer_file=/app/answer.txt
reward=0.0

if [ -f "$answer_file" ]; then
    contents="$(cat "$answer_file" | tr -d '\n')"
    echo "verifier: /app/answer.txt contents = '$contents'"
    if [ "$contents" = "42" ]; then
        reward=1.0
    fi
else
    echo "verifier: $answer_file not found"
fi

echo "$reward" > /logs/verifier/reward.txt
echo "verifier: reward = $reward"
