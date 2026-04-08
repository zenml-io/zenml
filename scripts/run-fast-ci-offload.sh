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

# Get the current commit SHA and remote URL for the sandbox git checkout.
COMMIT_SHA=$(git rev-parse HEAD)
REMOTE_URL=$(git remote get-url origin | sed 's|git@github.com:|https://github.com/|')

echo "[offload] Running tests at commit ${COMMIT_SHA:0:12}"

offload run \
    $no_cache_flag \
    --env "ZENML_CI_COMMIT=$COMMIT_SHA" \
    --env "ZENML_CI_REMOTE=$REMOTE_URL" \
    "$@"
