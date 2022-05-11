#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install xgboost slack
}

pre_run_forced () {
  zenml integration install xgboost slack -y
}
