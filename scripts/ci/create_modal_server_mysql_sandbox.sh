#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <modal-sandbox-script> <image-id>" >&2
  exit 1
fi

if [[ -z "${ZENML_MODAL_SERVER_URL:-}" ]]; then
  echo "ZENML_MODAL_SERVER_URL must be set." >&2
  exit 1
fi

if [[ -z "${ZENML_MODAL_SERVER_USERNAME:-}" ]]; then
  echo "ZENML_MODAL_SERVER_USERNAME must be set." >&2
  exit 1
fi

if [[ -z "${ZENML_MODAL_SERVER_PASSWORD:-}" ]]; then
  echo "ZENML_MODAL_SERVER_PASSWORD must be set." >&2
  exit 1
fi

modal_sandbox_script="$1"
image_id="$2"

if [[ "$modal_sandbox_script" == @* ]]; then
  echo "Modal sandbox helper token was not resolved by offload: ${modal_sandbox_script}" >&2
  exit 1
fi

exec uv run "$modal_sandbox_script" create "$image_id" \
  --cpu 2 \
  --memory-gb 4 \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --env PYTHONUNBUFFERED=1 \
  --env ZENML_DEBUG=true \
  --env ZENML_ANALYTICS_OPT_IN=false \
  --env AUTO_OPEN_DASHBOARD=false \
  --env ZENML_CLIENT_TEMPLATE_DIR=/opt/zenml-template \
  --env ZENML_TESTS_AUTO_ISOLATE=1 \
  --env "ZENML_MODAL_SERVER_URL=${ZENML_MODAL_SERVER_URL}" \
  --env "ZENML_MODAL_SERVER_USERNAME=${ZENML_MODAL_SERVER_USERNAME}" \
  --env "ZENML_MODAL_SERVER_PASSWORD=${ZENML_MODAL_SERVER_PASSWORD}"
