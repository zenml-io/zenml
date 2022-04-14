#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install neural_prophet
}

pre_run_forced () {
  zenml integration install neural_prophet -f
}