#!/usr/bin/env bash

set -euo pipefail

if [[ -z "${MODAL_TOKEN_ID:-}" || -z "${MODAL_TOKEN_SECRET:-}" ]]; then
    echo "MODAL_TOKEN_ID and MODAL_TOKEN_SECRET must be set." >&2
    exit 1
fi

python3 scripts/ci/modal_runner.py \
    --suite unit \
    --suite integration \
    --test-environment default \
    --python-version 3.13 \
    --max-sandboxes 40 \
    --skip-slow-examples \
    --local-run-name pre-push \
    "$@"
