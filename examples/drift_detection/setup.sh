#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  pip install "evidently<=0.1.40.dev0"
  zenml integration install sklearn
}

pre_run_forced () {
  pip install "evidently<=0.1.40.dev0"
  zenml integration install sklearn -f
}