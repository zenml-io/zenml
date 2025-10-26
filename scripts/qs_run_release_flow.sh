#!/usr/bin/env bash
# Quickstart Release Flow Runner
# Orchestrates lightweight Quickstart release validation: local and cloud execution.

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/qs_run_release_flow.sh \
    --cloud <aws|azure|gcp> \
    --parent-image <registry/repo:tag-prefix> \
    --new-version <X.Y.Z> \
    [--branch-ref <git ref, e.g. refs/heads/misc/prepare-release-X.Y.Z>]

Description:
  Runs the Quickstart release validation flow:
  - Patches the example config's parent_image and requirements to use the branch ref
  - Installs dependencies
  - Phase 1: Runs the pipeline locally
  - Phase 2: Runs the pipeline on the cloud stack

Notes:
  --branch-ref is optional. If not provided, the script falls back to $GITHUB_REF.
  If neither is available, the script exits with an error.
USAGE
}

# Simple argument parser
CLOUD=""
PARENT_PREFIX=""
NEW_VERSION=""
BRANCH_REF="${BRANCH_REF:-}"  # allow environment override if set externally

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cloud)
      CLOUD="${2:-}"; shift 2;;
    --parent-image)
      PARENT_PREFIX="${2:-}"; shift 2;;
    --new-version)
      NEW_VERSION="${2:-}"; shift 2;;
    --branch-ref)
      BRANCH_REF="${2:-}"; shift 2;;
    -h|--help)
      usage; exit 0;;
    *)
      echo "Error: Unknown argument: $1" >&2
      usage; exit 1;;
  esac
done

# Validate required args
if [[ -z "${CLOUD}" || -z "${PARENT_PREFIX}" || -z "${NEW_VERSION}" ]]; then
  echo "Error: --cloud, --parent-image, and --new-version are required." >&2
  usage
  exit 1
fi

# Determine branch ref
if [[ -z "${BRANCH_REF}" ]]; then
  if [[ -n "${GITHUB_REF:-}" ]]; then
    BRANCH_REF="${GITHUB_REF}"
  else
    echo "Error: --branch-ref not provided and GITHUB_REF is not set. Please supply one of them." >&2
    exit 1
  fi
fi

echo "=== Quickstart Release Flow ==="
echo "Cloud stack:          ${CLOUD}"
echo "Parent image prefix:  ${PARENT_PREFIX}"
echo "New version:          ${NEW_VERSION}"
echo "Git branch ref:       ${BRANCH_REF}"
echo "================================"

# Minimal variables needed for the simplified flow
DIR_PUSHED=0
CLOUD_STACK="${CLOUD}"
CONFIG="configs/training_${CLOUD}.yaml"
REQS="requirements_${CLOUD}.txt"
PARENT_IMAGE="${PARENT_PREFIX}-${NEW_VERSION}"
ZENML_GIT_SPEC="git+https://github.com/zenml-io/zenml.git@${BRANCH_REF}#egg=zenml[server]"
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

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

# Validate required files
if [[ ! -f "${CONFIG}" ]]; then
  echo "Error: Config file not found: ${CONFIG}" >&2
  exit 1
fi
if [[ ! -f "${REQS}" ]]; then
  echo "Error: Requirements file not found: ${REQS}" >&2
  exit 1
fi

# Patch config parent_image
echo "=== Patching parent_image in ${CONFIG} to: ${PARENT_IMAGE} ==="
# Replace the entire parent_image line, preserving indentation
sed -i -E "s|^([[:space:]]*parent_image:).*|\1 \"${PARENT_IMAGE}\"|g" "${CONFIG}"

# Patch requirements to install zenml from the provided branch ref
echo "=== Updating ${REQS}: pinning zenml to branch ref ${BRANCH_REF} ==="
# Replace any line that starts with 'zenml[server]' to make the pin robust to different version operators.
sed -i -E "s|^zenml\\[server\\].*|${ZENML_GIT_SPEC}|g" "${REQS}"

# Install dependencies
echo "=== Installing dependencies from ${REQS} ==="
pip install -r "${REQS}"

# Phase 1: Run the pipeline locally
echo "=== Phase 1: Run pipeline locally ==="
python run.py

# Phase 2: Run on the cloud stack
echo "=== Phase 2: Run pipeline on cloud stack ==="
zenml stack set "${CLOUD_STACK}"
python run.py

echo "=== Quickstart release flow completed ==="
