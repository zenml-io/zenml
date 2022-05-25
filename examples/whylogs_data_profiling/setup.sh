#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install whylogs sklearn
}

pre_run_forced () {
  zenml integration install whylogs sklearn -y
}
