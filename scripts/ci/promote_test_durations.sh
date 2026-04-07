#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_PATH="${1:-$REPO_ROOT/.modal-cache/test_durations.json}"
TARGET_PATH="${2:-$REPO_ROOT/.test_durations}"

if [[ ! -f "$SOURCE_PATH" ]]; then
    echo "Duration cache not found at $SOURCE_PATH" >&2
    exit 1
fi

python3 - "$SOURCE_PATH" "$TARGET_PATH" <<'PY'
import json
import sys
from pathlib import Path

source_path = Path(sys.argv[1])
target_path = Path(sys.argv[2])

data = json.loads(source_path.read_text(encoding="utf-8"))
if not isinstance(data, dict):
    raise SystemExit(f"Expected JSON object in {source_path}")

normalized = {
    str(node_id): float(duration)
    for node_id, duration in sorted(data.items())
}
target_path.write_text(
    json.dumps(normalized, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(
    f"Wrote {len(normalized)} test durations from {source_path} to {target_path}"
)
PY
