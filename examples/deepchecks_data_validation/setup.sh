#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install deepchecks sklearn
}

pre_run_forced () {
  zenml integration install deepchecks sklearn -f
}