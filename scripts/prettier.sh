#!/usr/bin/env bash
set -e
set -x

SRC=${1:-"src/zenml tests"}
SRC_NO_TESTS=${1:-"src/zenml"}

prettier --write ${SRC}
