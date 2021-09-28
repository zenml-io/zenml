#!/usr/bin/env bash

set -e
set -x

bash ./scripts/test-coverage-xml.sh
coverage html