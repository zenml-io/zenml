#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install deepchecks
  zenml integration install sklearn
}

pre_run_forced () {
  zenml integration install deepchecks -f
  zenml integration install sklearn -f
}