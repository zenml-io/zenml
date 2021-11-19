#!/usr/bin/env bash

set -e
set -x

TEST_SRC=${1:-"tests"}

export ZENML_DEBUG=1
coverage run -m pytest $TEST_SRC --color=yes
coverage combine
coverage report --show-missing
coverage xml
