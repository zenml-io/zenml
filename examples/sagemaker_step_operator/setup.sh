#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install aws sklearn
}

pre_run_forced () {
  zenml integration install aws sklearn -f
}