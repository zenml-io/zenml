#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install gcp sklearn vertex
}

pre_run_forced () {
  zenml integration install gcp sklearn vertex -f
}