#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install sklearn azureml
}

pre_run_forced () {
  zenml integration install sklearn azureml -f
}