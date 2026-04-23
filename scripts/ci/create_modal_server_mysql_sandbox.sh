#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <image-id>" >&2
  exit 1
fi

if [[ -z "${ZENML_MODAL_SERVER_URL:-}" ]]; then
  echo "ZENML_MODAL_SERVER_URL must be set." >&2
  exit 1
fi

image_id="$1"

exec uv run @modal_sandbox.py create "$image_id" \
  --cpu 2 \
  --memory-gb 4 \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --env PYTHONUNBUFFERED=1 \
  --env ZENML_DEBUG=true \
  --env ZENML_ANALYTICS_OPT_IN=false \
  --env AUTO_OPEN_DASHBOARD=false \
  --env ZENML_CLIENT_TEMPLATE_DIR=/opt/zenml-template \
  --env "ZENML_MODAL_SERVER_URL=${ZENML_MODAL_SERVER_URL}"
