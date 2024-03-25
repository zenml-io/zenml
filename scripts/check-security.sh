#!/usr/bin/env bash
set -e
set -x
set -o pipefail

SRC=${1:-"src/zenml tests examples"}

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false

bandit -r $SRC -ll \
    --exclude examples/llm_finetuning/scripts/prepare_alpaca.py

