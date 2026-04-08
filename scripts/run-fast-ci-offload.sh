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

# Compute a fingerprint of files that affect the dependency image.
current_fingerprint=$(cat \
    "$REPO_ROOT/Dockerfile.ci" \
    "$REPO_ROOT/pyproject.toml" \
    "$REPO_ROOT/scripts/install-zenml-dev.sh" \
    2>/dev/null | shasum -a 256 | cut -d' ' -f1)

no_cache_flag=""
if [[ -f "$FINGERPRINT_FILE" ]]; then
    cached_fingerprint=$(cat "$FINGERPRINT_FILE")
    if [[ "$current_fingerprint" != "$cached_fingerprint" ]]; then
        echo "[offload] Dependencies changed -- rebuilding image (--no-cache)."
        rm -f "$CACHE_FILE"
        no_cache_flag="--no-cache"
    fi
fi
echo "$current_fingerprint" > "$FINGERPRINT_FILE"

echo "[offload] Running tests..."

offload run $no_cache_flag "$@"
exit_code=$?

# Clean up per-batch log files -- only keep junit.xml
rm -rf "$OUTPUT_DIR/logs" "$OUTPUT_DIR/junit-parts" 2>/dev/null

# Print summary from junit.xml
if [[ -f "$OUTPUT_DIR/junit.xml" ]]; then
    echo ""
    echo "=== Test Results ==="
    # Extract stats from junit.xml
    python3 -c "
import xml.etree.ElementTree as ET, sys
tree = ET.parse('$OUTPUT_DIR/junit.xml')
root = tree.getroot()
tests = int(root.get('tests', 0))
failures = int(root.get('failures', 0))
errors = int(root.get('errors', 0))
time_s = float(root.get('time', 0))
passed = tests - failures - errors
print(f'Total: {tests}  Passed: {passed}  Failed: {failures}  Errors: {errors}  Time: {time_s:.1f}s')
if failures or errors:
    print()
    print('Failed tests:')
    for ts in root.iter('testsuite'):
        for tc in ts.iter('testcase'):
            fail = tc.find('failure')
            err = tc.find('error')
            if fail is not None:
                print(f'  FAIL  {tc.get(\"name\", \"?\")}')
                msg = fail.get('message', '')[:200]
                if msg: print(f'        {msg}')
            elif err is not None:
                print(f'  ERROR {tc.get(\"name\", \"?\")}')
                msg = err.get('message', '')[:200]
                if msg: print(f'        {msg}')
" 2>/dev/null || true
fi

exit $exit_code
