#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install evidently sklearn
}

pre_run_forced () {
  zenml integration install evidently sklearn -y
}
