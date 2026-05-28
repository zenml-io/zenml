#!/usr/bin/env bash
set -euo pipefail

REWARD_DIR="/logs/verifier"
mkdir -p "$REWARD_DIR"

# Run Python assertions; if any fail, the script captures the error
RESULT=$(python -c "
from math_utils import add
assert add(2, 3) == 5, f'add(2,3) returned {add(2,3)}'
assert add(-1, 1) == 0, f'add(-1,1) returned {add(-1,1)}'
print('ok')
" 2>&1) || true

if [ "$RESULT" = "ok" ]; then
    echo "PASS: add() works correctly"
    echo "1" > "$REWARD_DIR/reward.txt"
else
    echo "FAIL: $RESULT"
    echo "0" > "$REWARD_DIR/reward.txt"
fi
