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

echo "[offload] Running tests..."

offload run "${offload_flags[@]}" "$@"
exit_code=$?

# Clean up per-batch log files -- only keep junit.xml
rm -rf "$OUTPUT_DIR/logs" "$OUTPUT_DIR/junit-parts"

# Print summary
if [[ -f "$JUNIT_FILE" ]]; then
    echo ""
    echo "=== Test Results ==="
    python3 "$SCRIPT_DIR/ci/print_junit_summary.py" "$JUNIT_FILE" || true
fi

exit $exit_code
