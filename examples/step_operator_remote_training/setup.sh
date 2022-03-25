#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install aws sagemaker sklearn
}

pre_run_forced () {
  zenml integration install aws s3 sagemaker sklearn -f
}
