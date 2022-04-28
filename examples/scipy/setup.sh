#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install scipy
}

pre_run_forced () {
  zenml integration install scipy -f
}