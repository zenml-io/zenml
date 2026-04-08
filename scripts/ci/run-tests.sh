#!/usr/bin/env bash
# Wrapper script for offload sandboxes.
# Fetches the current commit and checks it out before running pytest.
set -e

COMMIT="${ZENML_CI_COMMIT:-}"
REMOTE="${ZENML_CI_REMOTE:-https://github.com/zenml-io/zenml.git}"

if [[ -n "$COMMIT" ]]; then
  git fetch --depth=1 "$REMOTE" "$COMMIT" 2>/dev/null \
    || git fetch --unshallow "$REMOTE" 2>/dev/null \
    || git fetch "$REMOTE" 2>/dev/null
  git checkout --force "$COMMIT"
  # Reinstall zenml from the checked-out source in case src/ changed
  pip install --no-deps -e . -q 2>/dev/null || true
fi

exec python -m pytest "$@"
