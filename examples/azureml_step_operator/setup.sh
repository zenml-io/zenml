#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install azure azureml sklearn
}

pre_run_forced () {
  zenml integration install azure azureml sklearn -f
}
