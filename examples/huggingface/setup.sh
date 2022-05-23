#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install huggingface
}

pre_run_forced () {
  zenml integration install huggingface -y
}
