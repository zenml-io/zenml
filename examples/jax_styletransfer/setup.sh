#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install jax
}

pre_run_forced () {
  zenml integration install jax -y
}
