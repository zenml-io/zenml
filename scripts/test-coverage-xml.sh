#!/usr/bin/env bash

set -e
set -x

TEST_SRC=${1:-"tests"}

coverage run -m pytest $TEST_SRC
coverage combine
coverage report --show-missing
coverage xml