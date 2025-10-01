#!/usr/bin/env bash
# Quickstart Release Flow Runner
# Orchestrates deployment, training, update, and evaluation for the Quickstart example during release prep.

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
  Runs the Quickstart release validation flow end-to-end:
  - Validates Docker availability
  - Patches the example config's parent_image and requirements to use the branch ref
  - Installs dependencies
  - Prepares a temporary stack with a Docker deployer
  - Deploys the agent (LLM-only), invokes it
  - Trains on the cloud stack via python run.py --train --config
  - Updates the deployment (hybrid) and invokes it
  - Evaluates on the cloud stack via python run.py --evaluate --config

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

# Verify Docker availability
echo "=== Checking Docker availability ==="
if ! command -v docker >/dev/null 2>&1; then
  echo "Error: Docker CLI not found on PATH. Please ensure Docker is installed." >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Error: Docker daemon is not reachable. Please ensure Docker is running." >&2
  exit 1
fi
echo "Docker is available."

# Prepare directories and variables
DIR_PUSHED=0
CLOUD_STACK="${CLOUD}"
TEMP_STACK="temp-qs-${CLOUD}"
DOCKER_DEPLOYER="gh-release-docker"
DEPLOYMENT_NAME="support_agent"
CONFIG="configs/training_${CLOUD}.yaml"
REQS="requirements_${CLOUD}.txt"
PARENT_IMAGE="${PARENT_PREFIX}-${NEW_VERSION}"
ZENML_GIT_SPEC="git+https://github.com/zenml-io/zenml.git@${BRANCH_REF}#egg=zenml[server]"

_cleanup() {
  # Preserve original exit code from the point of trap invocation
  local exit_code=$?
  # Disable recursive trapping inside cleanup
  trap - EXIT
  set +e

  echo "=== Cleanup: tearing down temp resources (exit code: ${exit_code}) ==="
  # Attempt to switch to the temp stack and delete deployment
  zenml stack set "${TEMP_STACK}" >/dev/null 2>&1
  zenml deployment delete "${DEPLOYMENT_NAME}" -y >/dev/null 2>&1

  # Switch back to cloud stack before deleting the temp stack
  zenml stack set "${CLOUD_STACK}" >/dev/null 2>&1
  zenml stack delete "${TEMP_STACK}" -y >/dev/null 2>&1

  # Delete the docker deployer component (best-effort)
  zenml deployer delete "${DOCKER_DEPLOYER}" -y >/dev/null 2>&1

  # Restore original directory if we changed it
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
sed -i -E "s|zenml\\[server\\]==[^[:space:]]*|${ZENML_GIT_SPEC}|g" "${REQS}"

# Install dependencies
echo "=== Installing dependencies from ${REQS} ==="
pip install -r "${REQS}"

# Prepare stacks and deployer
echo "=== Preparing stacks and deployer ==="
echo "Setting active stack to cloud: ${CLOUD_STACK}"
zenml stack set "${CLOUD_STACK}"

echo "Registering docker deployer component: ${DOCKER_DEPLOYER} (idempotent)"
zenml deployer register "${DOCKER_DEPLOYER}" -f docker || true

echo "Copying cloud stack to temp stack: ${TEMP_STACK} (idempotent)"
zenml stack copy "${CLOUD_STACK}" "${TEMP_STACK}" || true

echo "Updating temp stack to use docker deployer"
zenml stack update "${TEMP_STACK}" -D "${DOCKER_DEPLOYER}"

# Phase 1: Deploy LLM-only agent and invoke
echo "=== Phase 1: Deploy agent (LLM-only) and invoke ==="
zenml stack set "${TEMP_STACK}"
zenml pipeline deploy pipelines.support_agent.support_agent -n "${DEPLOYMENT_NAME}" -c configs/agent.yaml

echo "Waiting briefly for deployment readiness..."
sleep 20

echo "Invoking deployed agent (LLM-only)"
zenml deployment invoke "${DEPLOYMENT_NAME}" --text="my card is lost and i need a replacement"

# Phase 2: Train classifier on cloud orchestrator
echo "=== Phase 2: Train classifier on cloud orchestrator ==="
zenml stack set "${CLOUD_STACK}"
python run.py --train --config "${CONFIG}"

# Phase 3: Update deployment to hybrid mode and invoke
echo "=== Phase 3: Update deployment (hybrid) and invoke ==="
zenml stack set "${TEMP_STACK}"
zenml pipeline deploy pipelines.support_agent.support_agent -n "${DEPLOYMENT_NAME}" -c configs/agent.yaml -u

echo "Waiting briefly for updated deployment readiness..."
sleep 20

echo "Invoking updated agent (hybrid)"
zenml deployment invoke "${DEPLOYMENT_NAME}" --text="my card is lost and i need a replacement"

# Phase 4: Evaluate on cloud orchestrator
echo "=== Phase 4: Evaluate on cloud orchestrator ==="
zenml stack set "${CLOUD_STACK}"
python run.py --evaluate --config "${CONFIG}"

echo "=== Quickstart release flow completed ==="
# Normal exit will trigger cleanup via trap, which preserves the 0 exit code
