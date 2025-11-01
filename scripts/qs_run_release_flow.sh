#!/usr/bin/env bash
# Quickstart Release Flow Runner
# Orchestrates lightweight Quickstart release validation: local and cloud execution.

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/qs_run_release_flow.sh \
    --cloud <aws|azure|gcp> \
    --new-version <X.Y.Z>

Description:
  Runs the Quickstart release validation flow:
  - Phase 1: Runs the pipeline locally
  - Phase 2: Runs the pipeline on the cloud stack

USAGE
}

# Simple argument parser
CLOUD=""
NEW_VERSION=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cloud)
      CLOUD="${2:-}"; shift 2;;
    --new-version)
      NEW_VERSION="${2:-}"; shift 2;;
    -h|--help)
      usage; exit 0;;
    *)
      echo "Error: Unknown argument: $1" >&2
      usage; exit 1;;
  esac
done

# Validate required args
if [[ -z "${CLOUD}" || -z "${NEW_VERSION}" ]]; then
  echo "Error: --cloud and --new-version are required." >&2
  usage
  exit 1
fi


echo "=== Quickstart Release Flow ==="
echo "Cloud stack:          ${CLOUD}"
echo "================================"

# Minimal variables needed for the simplified flow
DIR_PUSHED=0
CLOUD_STACK="${CLOUD}"

_cleanup() {
  # Preserve original exit code from the point of trap invocation
  local exit_code=$?
  # Disable recursive trapping inside cleanup
  trap - EXIT
  set +e

  # Only restore original directory if we changed it. Nothing else is provisioned in this flow.
  if [[ "${DIR_PUSHED}" -eq 1 ]]; then
    popd >/dev/null 2>&1
    DIR_PUSHED=0
  fi

  # Restore -e and exit with the original status
  set -e
  exit "${exit_code}"
}

trap _cleanup EXIT

echo "=== Switching to examples/quickstart directory ==="
pushd examples/quickstart >/dev/null
DIR_PUSHED=1

# Build parent image
docker build -f docker/zenml-dev.Dockerfile -t zenmldocker/zenml:${NEW_VERSION}-py3.12 .

# Phase 1: Run the pipeline locally
echo "=== Phase 1: Run pipeline locally ==="
python run.py

# Phase 2: Run on the cloud stack
echo "=== Phase 2: Run pipeline on cloud stack ==="

if [[ "${CLOUD}" == "aws" ]]; then
  zenml integration install aws s3 --uv -y
elif [[ "${CLOUD}" == "azure" ]]; then
  zenml integration install azure --uv -y
elif [[ "${CLOUD}" == "gcp" ]]; then
  zenml integration install gcp --uv -y
fi

zenml stack set "${CLOUD_STACK}"
python run.py

echo "=== Quickstart release flow completed ==="
