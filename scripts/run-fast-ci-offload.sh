#!/usr/bin/env bash

set -euo pipefail

if [[ -z "${MODAL_TOKEN_ID:-}" || -z "${MODAL_TOKEN_SECRET:-}" ]]; then
    echo "MODAL_TOKEN_ID and MODAL_TOKEN_SECRET must be set." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CACHE_FILE="$REPO_ROOT/.offload-image-cache"
FINGERPRINT_FILE="$REPO_ROOT/.offload-deps-fingerprint"
OUTPUT_DIR="$REPO_ROOT/test-results/modal-fast-ci"
JUNIT_FILE="$OUTPUT_DIR/junit.xml"

current_fingerprint=$(cat \
    "$REPO_ROOT/Dockerfile.ci" \
    "$REPO_ROOT/pyproject.toml" \
    "$REPO_ROOT/scripts/install-zenml-dev.sh" \
    | shasum -a 256 | cut -d' ' -f1)

offload_flags=()
if [[ -f "$FINGERPRINT_FILE" ]]; then
    cached_fingerprint=$(cat "$FINGERPRINT_FILE")
    if [[ "$current_fingerprint" != "$cached_fingerprint" ]]; then
        echo "[offload] Dependencies changed -- rebuilding image (--no-cache)."
        rm -f "$CACHE_FILE"
        offload_flags+=("--no-cache")
    fi
fi
echo "$current_fingerprint" > "$FINGERPRINT_FILE"

rm -f "$JUNIT_FILE"

echo "[offload] Running tests..."

set +e
offload run "${offload_flags[@]}" "$@"
offload_exit_code=$?
set -e

# Clean up per-batch log files -- only keep junit.xml
rm -rf "$OUTPUT_DIR/logs" "$OUTPUT_DIR/junit-parts"

# Print summary
summary_exit_code=0
if [[ -f "$JUNIT_FILE" ]]; then
    echo ""
    echo "=== Test Results ==="
    if python3 "$SCRIPT_DIR/ci/print_junit_summary.py" "$JUNIT_FILE"; then
        :
    else
        summary_exit_code=$?
        echo "[offload] Failed to print JUnit summary for $JUNIT_FILE." >&2
    fi
elif [[ "$offload_exit_code" -eq 0 ]]; then
    echo "[offload] Tests completed but no JUnit report was produced at $JUNIT_FILE." >&2
    summary_exit_code=1
else
    echo "[offload] Tests failed before JUnit report was produced." >&2
fi

if [[ "$offload_exit_code" -ne 0 ]]; then
    exit "$offload_exit_code"
fi

exit "$summary_exit_code"
