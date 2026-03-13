#!/usr/bin/env bash
set -e
set -x

SRC=${1:-"src/zenml"}

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
export DISABLE_DATABASE_MIGRATION=1
rm -rf docs/mkdocs/core_code_docs || true
rm -rf docs/mkdocs/integration_code_docs || true
rm -f docs/mkdocs/index.md || true

python docs/mkdocstrings_helper.py --path $SRC --output_path docs/mkdocs/
cd docs
mkdocs serve