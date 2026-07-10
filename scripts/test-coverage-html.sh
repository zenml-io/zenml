#!/usr/bin/env bash

set -e
set -x

export ZENML_LOGGING_VERBOSITY=debug
export ZENML_ANALYTICS_OPT_IN=false
bash ./scripts/test-coverage-xml.sh
coverage html
