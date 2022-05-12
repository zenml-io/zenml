#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install sklearn slack
}

pre_run_forced () {
  zenml integration install sklearn slack -y
}
