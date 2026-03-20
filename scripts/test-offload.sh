#!/usr/bin/env bash
set -e

if ! command -v offload &>/dev/null; then
    echo "offload not found. Install with: cargo install offload" >&2
    exit 1
fi

offload run \
    --env ZENML_DEBUG=1 \
    --env ZENML_ANALYTICS_OPT_IN=false \
    --env EVIDENTLY_DISABLE_TELEMETRY=1 \
    --env ZENML_ENABLE_RICH_TRACEBACK=false \
    --env TOKENIZERS_PARALLELISM=false \
    --env AUTO_OPEN_DASHBOARD=false \
    "$@"
