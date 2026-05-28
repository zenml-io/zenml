#!/usr/bin/env bash
set -euo pipefail

REWARD_DIR="/logs/verifier"
mkdir -p "$REWARD_DIR"

if [ ! -f /app/data.json ]; then
    echo "FAIL: data.json does not exist"
    echo "0" > "$REWARD_DIR/reward.txt"
    exit 0
fi

# Validate JSON and check keys using Python
python3 -c "
import json, sys
with open('/app/data.json') as f:
    d = json.load(f)
assert d.get('name') == 'agent', f'name mismatch: {d.get(\"name\")}'
assert d.get('version') == 1, f'version mismatch: {d.get(\"version\")}'
assert d.get('active') is True, f'active mismatch: {d.get(\"active\")}'
print('All checks passed')
" 2>&1

if [ $? -eq 0 ]; then
    echo "PASS"
    echo "1" > "$REWARD_DIR/reward.txt"
else
    echo "FAIL"
    echo "0" > "$REWARD_DIR/reward.txt"
fi
