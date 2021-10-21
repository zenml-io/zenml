#!/usr/bin/env bash

set -e
set -x

export ZENML_DEBUG=1
bash ./scripts/test-coverage-xml.sh
coverage html