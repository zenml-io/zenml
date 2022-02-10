#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install whylogs
  zenml integration install sklearn
  pip install --upgrade --no-deps --force-reinstall scipy
}

pre_run_forced () {
  zenml integration install whylogs -f
  zenml integration install sklearn -f
  pip install --upgrade --no-deps --force-reinstall scipy
}