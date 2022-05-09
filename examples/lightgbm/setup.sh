#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install lightgbm
}

pre_run_forced () {
  zenml integration install lightgbm -y
}
